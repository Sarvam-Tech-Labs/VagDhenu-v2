# -*- coding: utf-8 -*-
"""
Verse-level syllable analysis: pāda-boundary resolution, per-syllable scansion
with source spans, diagnostics, and a maker–checker verification pass.

Ported from Prasadam's lib/sanskrit-verse-analysis.ts.

Offsets: TypeScript reports UTF-16 code-unit offsets; this port reports Python
code-point offsets. Every character the engine accepts (Devanāgarī, IAST Latin
with its combining marks) is in the BMP, so the two coincide.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Union

from .core import (
    AKSARA_RULES,
    Aksara,
    AksaraContext,
    AksaraJudgement,
    AksaraParts,
    ChandasError,
    Weight,
    classify_aksara_iast,
    deva_chant_lines,
    syllabify_iast_line,
)
from .normalizer import devanagari_to_iast, iast_to_devanagari

SanskritScript = str          # "iast" | "devanagari"
PadaBoundaryMode = str        # "auto" | "lines" | "dandas" | "single"
SanskritPadaBoundary = str    # "newline" | "danda" | "end"
DiagnosticSeverity = str      # "error" | "warning" | "info"

VERIFIER_METHOD = (
    "independent phoneme walk: recompute segmentation, context, weight, and "
    "totals from normalized IAST"
)


@dataclass(frozen=True)
class SanskritSourceSpan:
    """Code-point offsets into the exact `source_text` supplied by the caller."""

    start: int
    end: int
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(frozen=True)
class SanskritDiagnostic:
    code: str
    severity: DiagnosticSeverity
    message: str
    span: Optional[SanskritSourceSpan] = None


@dataclass(frozen=True)
class SanskritSyllableContext:
    #: Canonical IAST remaining in this pāda after the syllable.
    next_iast: str
    pada_final: bool


@dataclass
class AnalyzedSanskritSyllable:
    #: Zero-based index across the complete analysis.
    index: int
    #: Zero-based pāda and position indices.
    pada_index: int
    position: int
    #: Preferred display in the detected/requested input script.
    text: str
    iast: str
    devanagari: str
    #: Exact source substring covered by `span`.
    source: str
    span: SanskritSourceSpan
    #: Canonical IAST structural decomposition.
    parts: AksaraParts
    weight: Weight
    matras: int
    rule: str
    reason: str
    anceps: bool
    pluta: bool
    context: SanskritSyllableContext
    #: Set only after the independent checker recomputes this syllable.
    verified: bool = False


@dataclass
class AnalyzedSanskritPada:
    index: int
    source: str
    span: SanskritSourceSpan
    normalized_iast: str
    syllables: List[AnalyzedSanskritSyllable]
    pattern: str
    matras: int
    boundary: SanskritPadaBoundary


@dataclass
class SanskritVerseTotals:
    padas: int = 0
    syllables: int = 0
    laghu: int = 0
    guru: int = 0
    matras: int = 0


@dataclass(frozen=True)
class SanskritVerificationIssue:
    code: str
    message: str
    pada_index: Optional[int] = None
    position: Optional[int] = None


@dataclass
class SanskritVerseVerification:
    status: str  # "verified" | "failed" | "not-run"
    checked_syllables: int
    checks: int
    method: str
    issues: List[SanskritVerificationIssue]


@dataclass
class SanskritVerseAnalysis:
    ok: bool
    source_text: str
    script: Optional[SanskritScript]
    boundary_mode: PadaBoundaryMode
    normalized_text: str
    padas: List[AnalyzedSanskritPada]
    syllables: List[AnalyzedSanskritSyllable]
    totals: SanskritVerseTotals
    diagnostics: List[SanskritDiagnostic]
    verification: SanskritVerseVerification


# --- character inventories ------------------------------------------------

IAST_VOWELS = ("ai", "au", "ā", "ī", "ū", "ṝ", "ḹ", "e", "o", "a", "i", "u", "ṛ", "ḷ")
IAST_TRANSPARENT = frozenset([" ", "\t", "-", "’", "'", "|", "।", "॥"])
JOINERS = frozenset(["‌", "‍", "﻿"])
DASHES = frozenset(["‐", "‑", "‒", "–", "—", "−"])
QUOTES = frozenset(["‘", "’", "ʼ", "ʻ", "´", "`"])
IGNORED_PUNCTUATION = frozenset(
    ["।", "॥", "|", ",", ";", "!", "?", "…", ".", "(", ")", "[", "]", "{", "}",
     '"', "“", "”"]
)

_DIGIT = re.compile(r"[\d०-९]")
_ONLY_DIGITS_AND_SPACE = re.compile(r"^[\s\d०-९]+$")
_DANDA_END = re.compile(r"[।॥|]$")
_ONLY_DANDAS = re.compile(r"^[।॥|]*$")


# --- source spans ---------------------------------------------------------


def _point_at(source: str, offset: int) -> Tuple[int, int]:
    line = 1
    column = 1
    i = 0
    while i < offset:
        if source[i] == "\r":
            if i + 1 < len(source) and source[i + 1] == "\n":
                i += 1
            line += 1
            column = 1
        elif source[i] == "\n":
            line += 1
            column = 1
        else:
            column += 1
        i += 1
    return line, column


def source_span(source: str, start: int, end: int) -> SanskritSourceSpan:
    from_line, from_column = _point_at(source, start)
    to_line, to_column = _point_at(source, end)
    return SanskritSourceSpan(
        start=start,
        end=end,
        line=from_line,
        column=from_column,
        end_line=to_line,
        end_column=to_column,
    )


@dataclass
class _OffsetMap:
    start: int
    end: int


@dataclass
class _MappedText:
    text: str = ""
    map: List[_OffsetMap] = field(default_factory=list)


@dataclass
class _RawPada:
    start: int
    end: int
    boundary: SanskritPadaBoundary


def _trim_range(source: str, start: int, end: int) -> _OffsetMap:
    frm, to = start, end
    while frm < to and source[frm].isspace():
        frm += 1
    while to > frm and source[to - 1].isspace():
        to -= 1
    return _OffsetMap(frm, to)


# --- pāda splitting -------------------------------------------------------


def _resolve_boundary_mode(source: str, requested: Optional[PadaBoundaryMode]) -> PadaBoundaryMode:
    if requested and requested != "auto":
        return requested
    if re.search(r"\r\n|[\r\n]", source):
        return "lines"
    if re.search(r"[।॥|]", source):
        return "dandas"
    return "single"


def _split_at_matches(source: str, pattern: re.Pattern, boundary: str) -> List[_RawPada]:
    padas: List[_RawPada] = []
    start = 0
    for match in pattern.finditer(source):
        at = match.start()
        rng = _trim_range(source, start, at)
        if rng.end > rng.start:
            padas.append(_RawPada(rng.start, rng.end, boundary))
        start = at + len(match.group(0))
    tail = _trim_range(source, start, len(source))
    if tail.end > tail.start:
        padas.append(_RawPada(tail.start, tail.end, "end"))
    return padas


def _is_boundary_metadata_line(source: str, pada: _RawPada) -> bool:
    text = source[pada.start:pada.end]
    if not _ONLY_DIGITS_AND_SPACE.match(text):
        return False
    return bool(_DANDA_END.search(source[:pada.start].rstrip()))


def _raw_padas(source: str, mode: PadaBoundaryMode) -> List[_RawPada]:
    if mode == "lines":
        return [
            pada
            for pada in _split_at_matches(source, re.compile(r"\r\n|\r|\n"), "newline")
            if not _is_boundary_metadata_line(source, pada)
        ]
    if mode == "dandas":
        return [
            pada
            for pada in _split_at_matches(source, re.compile(r"[।॥]+|\|+"), "danda")
            if not _ONLY_DIGITS_AND_SPACE.match(source[pada.start:pada.end])
        ]
    rng = _trim_range(source, 0, len(source))
    return [_RawPada(rng.start, rng.end, "end")] if rng.end > rng.start else []


# --- script detection -----------------------------------------------------


def _has_devanagari_letter(text: str) -> bool:
    for char in text:
        code = ord(char)
        if (
            (0x0904 <= code <= 0x0939)
            or (0x0958 <= code <= 0x0961)
            or (0x0972 <= code <= 0x097F)
        ):
            return True
    return False


def _has_latin_letter(text: str) -> bool:
    return bool(re.search(r"[A-Za-zÀ-ɏḀ-ỿ]", text))


def _detected_script(source: str) -> Optional[str]:
    deva = _has_devanagari_letter(source) or "ॐ" in source
    latin = _has_latin_letter(source)
    if deva and latin:
        return "mixed"
    if deva:
        return "devanagari"
    if latin:
        return "iast"
    return None


_AMBIGUOUS_ASCII = re.compile(r"(?:aa|ii|uu|chh|sh|\.r|r\^i|~n)", re.IGNORECASE)


def _note_ambiguous_ascii_transliteration(
    source: str, script: Optional[SanskritScript], diagnostics: List[SanskritDiagnostic]
) -> None:
    if script != "iast":
        return
    match = _AMBIGUOUS_ASCII.search(source)
    if not match:
        return
    diagnostics.append(
        SanskritDiagnostic(
            code="AMBIGUOUS_ASCII_TRANSLITERATION",
            severity="error",
            message=(
                "This looks like informal ASCII, ITRANS, or Harvard-Kyoto "
                "transliteration. Convert it to proper IAST or Devanāgarī; "
                "silently guessing a transliteration scheme would corrupt the "
                "scansion."
            ),
            span=source_span(source, match.start(), match.end()),
        )
    )


def _resolve_script(
    source: str, requested: Optional[str], diagnostics: List[SanskritDiagnostic]
) -> Optional[SanskritScript]:
    detected = _detected_script(source)
    wanted = requested if requested and requested != "auto" else None
    if detected == "mixed":
        diagnostics.append(
            SanskritDiagnostic(
                code="MIXED_SCRIPTS",
                severity="error",
                message=(
                    "Mixed Devanāgarī and Latin-script Sanskrit is not accepted "
                    "in one analysis."
                ),
            )
        )
        return None
    if wanted and detected and wanted != detected:
        diagnostics.append(
            SanskritDiagnostic(
                code="SCRIPT_MISMATCH",
                severity="error",
                message=f"The input is {detected}, but {wanted} was requested.",
            )
        )
        return None
    if not detected:
        diagnostics.append(
            SanskritDiagnostic(
                code="SCRIPT_UNDETECTED",
                severity="error",
                message="No Sanskrit letters were found in the input.",
            )
        )
    return wanted or detected


# --- normalization with offset mapping ------------------------------------


def _append_mapped(target: _MappedText, value: str, mapping: _OffsetMap) -> None:
    target.text += value
    for _ in value:
        target.map.append(_OffsetMap(mapping.start, mapping.end))


def _append_space(target: _MappedText, mapping: _OffsetMap) -> None:
    if target.text.endswith(" "):
        target.map[-1].end = mapping.end
        return
    _append_mapped(target, " ", mapping)


def _nfc_mapped(raw: str, absolute_start: int) -> Tuple[_MappedText, bool]:
    mapped = _MappedText()
    changed = False
    i = 0
    while i < len(raw):
        start = i
        i += 1
        while i < len(raw) and unicodedata.category(raw[i]).startswith("M"):
            i += 1
        original = raw[start:i]
        normalized = unicodedata.normalize("NFC", original)
        if normalized != original:
            changed = True
        _append_mapped(
            mapped, normalized, _OffsetMap(absolute_start + start, absolute_start + i)
        )
    return mapped, changed


def _mapped_slice(inp: _MappedText, start: int, end: int) -> _MappedText:
    return _MappedText(text=inp.text[start:end], map=inp.map[start:end])


def _trim_mapped(inp: _MappedText) -> _MappedText:
    start = 0
    end = len(inp.text)
    while start < end and inp.text[start] == " ":
        start += 1
    while end > start and inp.text[end - 1] == " ":
        end -= 1
    return _mapped_slice(inp, start, end)


def _source_map_at(inp: _MappedText, at: int) -> _OffsetMap:
    return inp.map[at] if 0 <= at < len(inp.map) else _OffsetMap(0, 0)


_DEVA_VOWEL_CODEPOINTS = frozenset(
    [
        0x0904, 0x0905, 0x0906, 0x0907, 0x0908, 0x0909, 0x090A, 0x090B, 0x0960,
        0x090C, 0x0961, 0x090F, 0x0910, 0x0913, 0x0914, 0x093E, 0x093F, 0x0940,
        0x0941, 0x0942, 0x0943, 0x0944, 0x0962, 0x0963, 0x0947, 0x0948, 0x094B,
        0x094C,
    ]
)


def _is_deva_consonant(char: str) -> bool:
    if not char:
        return False
    code = ord(char)
    return (0x0915 <= code <= 0x0939) or (0x0958 <= code <= 0x095F)


def _is_deva_pluta_site(text: str, at: int) -> bool:
    previous = text[at - 1] if at > 0 else ""
    if not previous:
        return False
    return ord(previous) in _DEVA_VOWEL_CODEPOINTS or _is_deva_consonant(previous)


def _is_iast_pluta_site(text: str, at: int) -> bool:
    before = text[:at].lower()
    return any(before.endswith(vowel) for vowel in IAST_VOWELS)


def _is_pluta_digit(text: str, at: int, script: SanskritScript) -> bool:
    if text[at] not in ("3", "३"):
        return False
    return (
        _is_deva_pluta_site(text, at)
        if script == "devanagari"
        else _is_iast_pluta_site(text, at)
    )


def _is_verse_number_at(text: str, at: int) -> bool:
    start = at
    end = at
    while start > 0 and _DIGIT.match(text[start - 1]):
        start -= 1
    while end < len(text) and _DIGIT.match(text[end]):
        end += 1
    before = text[:start].rstrip()
    after = text[end:].strip()
    return bool(_DANDA_END.search(before)) and bool(_ONLY_DANDAS.match(after))


@dataclass
class _NormalizedCharacter:
    value: str
    length: int
    map: _OffsetMap
    ignored: Optional[str] = None


def _normalized_character(
    inp: _MappedText, at: int, script: SanskritScript
) -> _NormalizedCharacter:
    char = inp.text[at]
    mapping = _source_map_at(inp, at)

    if char in JOINERS:
        return _NormalizedCharacter("", 1, mapping, "formatting")
    if char.isspace():
        return _NormalizedCharacter(" ", 1, mapping)
    if char in DASHES:
        return _NormalizedCharacter("-", 1, mapping)
    if char in QUOTES:
        return _NormalizedCharacter("’", 1, mapping)

    if _DIGIT.match(char):
        if _is_pluta_digit(inp.text, at, script):
            return _NormalizedCharacter("3", 1, mapping)
        if _is_verse_number_at(inp.text, at):
            return _NormalizedCharacter("", 1, mapping, "number")
        return _NormalizedCharacter("", 1, mapping, "invalid-number")

    if script == "devanagari" and char == ":":
        return _NormalizedCharacter("ः", 1, mapping)
    if char in IGNORED_PUNCTUATION or char == ":":
        return _NormalizedCharacter("", 1, mapping, "punctuation")

    lowered = char.lower() if script == "iast" else char
    return _NormalizedCharacter(lowered, 1, mapping)


def _diagnostic_once(
    diagnostics: List[SanskritDiagnostic],
    code: str,
    message: str,
    source: str,
    mapping: _OffsetMap,
    severity: DiagnosticSeverity = "info",
) -> None:
    if any(item.code == code for item in diagnostics):
        return
    diagnostics.append(
        SanskritDiagnostic(
            code=code,
            severity=severity,
            message=message,
            span=source_span(source, mapping.start, mapping.end),
        )
    )


def _note_candrabindu_convention(
    mapped: _MappedText, diagnostics: List[SanskritDiagnostic], source: str
) -> None:
    at = -1
    for index, char in enumerate(mapped.text):
        if char in ("ँ", "̐"):
            at = index
            break
    if at < 0:
        return
    _diagnostic_once(
        diagnostics,
        "CANDRABINDU_CONVENTION",
        (
            "Candrabindu nasalization is treated as guru by this engine; that "
            "metrical treatment is convention-sensitive."
        ),
        source,
        _source_map_at(mapped, at),
        "warning",
    )


def _note_normalization(
    ignored: Optional[str],
    diagnostics: List[SanskritDiagnostic],
    source: str,
    mapping: _OffsetMap,
) -> None:
    if ignored == "invalid-number":
        diagnostics.append(
            SanskritDiagnostic(
                code="UNEXPECTED_NUMBER",
                severity="error",
                message=(
                    "A number is valid only as a vowel's pluta marker or as "
                    "trailing verse metadata."
                ),
                span=source_span(source, mapping.start, mapping.end),
            )
        )
    elif ignored == "formatting":
        _diagnostic_once(
            diagnostics,
            "FORMATTING_MARK_IGNORED",
            "Invisible shaping marks were ignored for analysis.",
            source,
            mapping,
        )
    elif ignored == "number":
        _diagnostic_once(
            diagnostics,
            "VERSE_NUMBER_IGNORED",
            "A verse number was ignored for analysis.",
            source,
            mapping,
        )
    elif ignored == "punctuation":
        _diagnostic_once(
            diagnostics,
            "PUNCTUATION_IGNORED",
            "Non-metrical punctuation was ignored for analysis.",
            source,
            mapping,
        )


def _normalize_mapped(
    raw: str,
    absolute_start: int,
    script: SanskritScript,
    source: str,
    diagnostics: List[SanskritDiagnostic],
) -> _MappedText:
    nfc, changed = _nfc_mapped(raw, absolute_start)
    if changed:
        _diagnostic_once(
            diagnostics,
            "UNICODE_NORMALIZED",
            "Unicode combining sequences were normalized to NFC for analysis.",
            source,
            _OffsetMap(absolute_start, absolute_start + len(raw)),
        )
    _note_candrabindu_convention(nfc, diagnostics, source)
    result = _MappedText()
    at = 0
    while at < len(nfc.text):
        normalized = _normalized_character(nfc, at, script)
        _note_normalization(normalized.ignored, diagnostics, source, normalized.map)
        if normalized.value == " ":
            _append_space(result, normalized.map)
        elif normalized.value != "":
            _append_mapped(result, normalized.value, normalized.map)
        at += normalized.length
    return _trim_mapped(result)


# --- pluta extraction and akṣara location ---------------------------------


@dataclass
class _PlutaMarker:
    compact_offset: int
    source: _OffsetMap


@dataclass
class _LocatedAksara:
    compact_start: int
    compact_end: int
    source: _OffsetMap


def _remove_mapped_pluta(inp: _MappedText) -> Tuple[_MappedText, List[_PlutaMarker]]:
    scan = _MappedText()
    markers: List[_PlutaMarker] = []
    compact_offset = 0
    for i, char in enumerate(inp.text):
        if char == "3":
            markers.append(_PlutaMarker(compact_offset, _source_map_at(inp, i)))
            continue
        _append_mapped(scan, char, _source_map_at(inp, i))
        if char not in IAST_TRANSPARENT:
            compact_offset += 1
    return scan, markers


def _remove_plain_pluta(
    text: str, source_markers: Sequence[_OffsetMap]
) -> Tuple[str, List[_PlutaMarker]]:
    scan = ""
    compact_offset = 0
    source_index = 0
    markers: List[_PlutaMarker] = []
    for char in text:
        if char in ("3", "३"):
            markers.append(
                _PlutaMarker(
                    compact_offset,
                    source_markers[source_index]
                    if source_index < len(source_markers)
                    else _OffsetMap(0, 0),
                )
            )
            source_index += 1
            continue
        scan += char
        if char not in IAST_TRANSPARENT:
            compact_offset += len(char)
    return scan, markers


def _significant_units(inp: _MappedText) -> List[Tuple[str, _OffsetMap]]:
    return [
        (char, _source_map_at(inp, i))
        for i, char in enumerate(inp.text)
        if char not in IAST_TRANSPARENT
    ]


def _range_of(maps: Sequence[_OffsetMap]) -> _OffsetMap:
    return _OffsetMap(min(m.start for m in maps), max(m.end for m in maps))


def _locate_iast_aksaras(
    inp: _MappedText, aksaras: Sequence[Aksara]
) -> Optional[List[_LocatedAksara]]:
    significant = _significant_units(inp)
    compact = "".join(value for value, _ in significant)
    if compact != "".join(a.text for a in aksaras):
        return None
    located: List[_LocatedAksara] = []
    taken = 0
    for aksara in aksaras:
        compact_start = taken
        compact_end = compact_start + len(aksara.text)
        maps = [m for _, m in significant[compact_start:compact_end]]
        located.append(_LocatedAksara(compact_start, compact_end, _range_of(maps)))
        taken = compact_end
    return located


def _deva_marker_maps(inp: _MappedText) -> List[_OffsetMap]:
    return [_source_map_at(inp, i) for i, char in enumerate(inp.text) if char == "3"]


def _deva_without_pluta(inp: _MappedText) -> _MappedText:
    result = _MappedText()
    for i, char in enumerate(inp.text):
        if char != "3":
            _append_mapped(result, char, _source_map_at(inp, i))
    return result


def _locate_deva_aksaras(inp: _MappedText, count: int) -> Optional[List[_LocatedAksara]]:
    aligned = deva_chant_lines([inp.text], [count])
    if not aligned:
        return None
    clusters = [c for pada in aligned for word in pada for c in word.clusters]
    located: List[_LocatedAksara] = []
    cursor = 0
    compact_start = 0
    for cluster in clusters:
        start = inp.text.find(cluster, cursor)
        if start < 0:
            return None
        end = start + len(cluster)
        located.append(
            _LocatedAksara(compact_start, compact_start + 1, _range_of(inp.map[start:end]))
        )
        compact_start += 1
        cursor = end
    return located


def _markers_for_aksara(
    markers: Sequence[_PlutaMarker], located: _LocatedAksara
) -> List[_PlutaMarker]:
    return [
        marker
        for marker in markers
        if located.compact_start < marker.compact_offset <= located.compact_end
    ]


def _expand_for_marker(rng: _OffsetMap, marker: Optional[_PlutaMarker]) -> _OffsetMap:
    if not marker:
        return rng
    return _OffsetMap(
        min(rng.start, marker.source.start), max(rng.end, marker.source.end)
    )


def _canonical_aksara_locations(aksaras: Sequence[Aksara]) -> List[_LocatedAksara]:
    located: List[_LocatedAksara] = []
    taken = 0
    for aksara in aksaras:
        compact_start = taken
        taken += len(aksara.text)
        located.append(_LocatedAksara(compact_start, taken, _OffsetMap(0, 0)))
    return located


# --- pāda construction ----------------------------------------------------


@dataclass
class _PreparedPada:
    canonical_iast: str
    scan_iast: str
    markers: List[_PlutaMarker]
    source_locations: List[_LocatedAksara]
    canonical_locations: List[_LocatedAksara]


def _add_error(
    diagnostics: List[SanskritDiagnostic],
    code: str,
    message: str,
    source: str,
    rng: Optional[Union[_OffsetMap, _RawPada]] = None,
) -> None:
    span = source_span(source, rng.start, rng.end) if rng else None
    diagnostics.append(
        SanskritDiagnostic(code=code, severity="error", message=message, span=span)
    )


def _scan_pada_iast(
    scan_iast: str, raw: _RawPada, source: str, diagnostics: List[SanskritDiagnostic]
) -> Optional[List[Aksara]]:
    try:
        aksaras = syllabify_iast_line(scan_iast)
        if aksaras:
            return aksaras
        _add_error(
            diagnostics,
            "NO_SYLLABLES",
            "This segment contains no Sanskrit vowel.",
            source,
            raw,
        )
    except ChandasError as error:
        message = str(error).replace("chandas: ", "", 1)
        _add_error(
            diagnostics,
            "UNSUPPORTED_INPUT",
            f"The segment cannot be scanned: {message}",
            source,
            raw,
        )
    return None


def _prepare_iast_pada(
    mapped: _MappedText,
    aksaras: Sequence[Aksara],
    diagnostics: List[SanskritDiagnostic],
    source: str,
    raw: _RawPada,
) -> Optional[_PreparedPada]:
    scan, markers = _remove_mapped_pluta(mapped)
    source_locations = _locate_iast_aksaras(scan, aksaras)
    if source_locations is None:
        _add_error(
            diagnostics,
            "INVALID_PHONEME_ORDER",
            (
                "The source cannot be partitioned into valid metrical syllables "
                "without reordering signs."
            ),
            source,
            raw,
        )
        return None
    return _PreparedPada(
        canonical_iast=mapped.text,
        scan_iast=scan.text,
        markers=markers,
        source_locations=source_locations,
        canonical_locations=_canonical_aksara_locations(aksaras),
    )


def _prepare_deva_pada(
    mapped: _MappedText,
    aksaras: Sequence[Aksara],
    diagnostics: List[SanskritDiagnostic],
    source: str,
    raw: _RawPada,
) -> Optional[_PreparedPada]:
    marker_maps = _deva_marker_maps(mapped)
    canonical_iast = devanagari_to_iast(mapped.text).replace("३", "3")
    scan, markers = _remove_plain_pluta(canonical_iast, marker_maps)
    if len(markers) != len(marker_maps):
        _add_error(
            diagnostics,
            "PLUTA_MAPPING_FAILED",
            "A pluta marker could not be mapped across scripts.",
            source,
            raw,
        )
        return None
    source_locations = _locate_deva_aksaras(_deva_without_pluta(mapped), len(aksaras))
    if source_locations is None:
        _add_error(
            diagnostics,
            "DEVANAGARI_ALIGNMENT_FAILED",
            "The Devanāgarī clusters do not align one-to-one with the metrical syllables.",
            source,
            raw,
        )
        return None
    return _PreparedPada(
        canonical_iast=canonical_iast,
        scan_iast=scan,
        markers=markers,
        source_locations=source_locations,
        canonical_locations=_canonical_aksara_locations(aksaras),
    )


def _marker_for_unit(
    markers: Sequence[_PlutaMarker],
    location: _LocatedAksara,
    diagnostics: List[SanskritDiagnostic],
    source: str,
    raw: _RawPada,
) -> Optional[_PlutaMarker]:
    found = _markers_for_aksara(markers, location)
    if len(found) <= 1:
        return found[0] if found else None
    _add_error(
        diagnostics,
        "MULTIPLE_PLUTA_MARKERS",
        "One syllable cannot carry more than one pluta marker.",
        source,
        raw,
    )
    return None


def _marked_aksara_text(
    aksara: Aksara,
    marker: Optional[_PlutaMarker],
    location: _LocatedAksara,
    diagnostics: List[SanskritDiagnostic],
    source: str,
) -> Optional[str]:
    if not marker:
        return aksara.text
    base = classify_aksara_iast(aksara.text)
    if not base.valid:
        return None
    expected = len(base.parts.onset) + len(base.parts.vowel)
    actual = marker.compact_offset - location.compact_start
    if actual == expected:
        return aksara.text[:expected] + "3" + aksara.text[expected:]
    _add_error(
        diagnostics,
        "MISPLACED_PLUTA_MARKER",
        "Pluta 3/३ must follow its vowel directly, before a mark or closing consonant.",
        source,
        marker.source,
    )
    return None


def _display_devanagari(iast: str) -> str:
    return iast_to_devanagari(iast).replace("3", "३")


def _judge_made_aksara(
    text: str,
    next_iast: str,
    pada_final: bool,
    scanner: Aksara,
    diagnostics: List[SanskritDiagnostic],
    source: str,
    rng: _OffsetMap,
) -> Optional[AksaraJudgement]:
    judged = classify_aksara_iast(
        text, AksaraContext(next=next_iast, pada_final=pada_final)
    )
    if not judged.valid:
        _add_error(diagnostics, "AKSARA_REJECTED", judged.reason, source, rng)
        return None
    if not judged.pluta and judged.weight != scanner.weight:
        _add_error(
            diagnostics,
            "WEIGHT_ENGINE_DISAGREEMENT",
            (
                f"The line scanner says {scanner.weight}, but the rule classifier "
                f"says {judged.weight}."
            ),
            source,
            rng,
        )
        return None
    return judged


def _make_pada_syllables(
    aksaras: Sequence[Aksara],
    prepared: _PreparedPada,
    script: SanskritScript,
    source: str,
    raw: _RawPada,
    pada_index: int,
    global_start: int,
    diagnostics: List[SanskritDiagnostic],
) -> Optional[List[AnalyzedSanskritSyllable]]:
    texts: List[Optional[str]] = []
    for index, aksara in enumerate(aksaras):
        location = prepared.canonical_locations[index]
        marker = _marker_for_unit(prepared.markers, location, diagnostics, source, raw)
        texts.append(
            _marked_aksara_text(aksara, marker, location, diagnostics, source)
        )
    if any(text is None for text in texts):
        return None
    complete: List[str] = [t for t in texts if t is not None]

    syllables: List[AnalyzedSanskritSyllable] = []
    for position in range(len(aksaras)):
        pada_final = position == len(aksaras) - 1
        next_iast = "".join(complete[position + 1:])
        marker = _marker_for_unit(
            prepared.markers,
            prepared.canonical_locations[position],
            diagnostics,
            source,
            raw,
        )
        rng = _expand_for_marker(prepared.source_locations[position].source, marker)
        judged = _judge_made_aksara(
            complete[position],
            next_iast,
            pada_final,
            aksaras[position],
            diagnostics,
            source,
            rng,
        )
        if not judged:
            return None
        text = complete[position]
        devanagari = _display_devanagari(text)
        syllables.append(
            AnalyzedSanskritSyllable(
                index=global_start + position,
                pada_index=pada_index,
                position=position,
                text=text if script == "iast" else devanagari,
                iast=text,
                devanagari=devanagari,
                source=source[rng.start:rng.end],
                span=source_span(source, rng.start, rng.end),
                parts=judged.parts,
                weight=judged.weight,
                matras=judged.matras,
                rule=judged.rule,
                reason=judged.reason,
                anceps=bool(judged.anceps),
                pluta=bool(judged.pluta),
                context=SanskritSyllableContext(next_iast=next_iast, pada_final=pada_final),
                verified=False,
            )
        )
    return syllables


def _canonical_and_scan(mapped: _MappedText, script: SanskritScript) -> Tuple[str, str]:
    if script == "iast":
        scan, _ = _remove_mapped_pluta(mapped)
        return mapped.text, scan.text
    canonical_iast = devanagari_to_iast(mapped.text).replace("३", "3")
    scan, _ = _remove_plain_pluta(canonical_iast, [])
    return canonical_iast, scan


def _make_pada(
    raw: _RawPada,
    script: SanskritScript,
    source: str,
    pada_index: int,
    global_start: int,
    diagnostics: List[SanskritDiagnostic],
) -> Optional[Tuple[AnalyzedSanskritPada, List[AnalyzedSanskritSyllable]]]:
    raw_text = source[raw.start:raw.end]
    mapped = _normalize_mapped(raw_text, raw.start, script, source, diagnostics)
    if mapped.text == "":
        return None
    canonical_iast, scan_iast = _canonical_and_scan(mapped, script)
    aksaras = _scan_pada_iast(scan_iast, raw, source, diagnostics)
    if not aksaras:
        return None
    prepared = (
        _prepare_iast_pada(mapped, aksaras, diagnostics, source, raw)
        if script == "iast"
        else _prepare_deva_pada(mapped, aksaras, diagnostics, source, raw)
    )
    if not prepared:
        return None
    syllables = _make_pada_syllables(
        aksaras, prepared, script, source, raw, pada_index, global_start, diagnostics
    )
    if not syllables:
        return None
    pada = AnalyzedSanskritPada(
        index=pada_index,
        source=raw_text,
        span=source_span(source, raw.start, raw.end),
        normalized_iast=canonical_iast,
        syllables=syllables,
        pattern="".join("G" if s.weight == "guru" else "L" for s in syllables),
        matras=sum(s.matras for s in syllables),
        boundary=raw.boundary,
    )
    return pada, syllables


def _verse_totals(padas: Sequence[AnalyzedSanskritPada]) -> SanskritVerseTotals:
    syllables = [s for pada in padas for s in pada.syllables]
    return SanskritVerseTotals(
        padas=len(padas),
        syllables=len(syllables),
        laghu=sum(1 for s in syllables if s.weight == "laghu"),
        guru=sum(1 for s in syllables if s.weight == "guru"),
        matras=sum(s.matras for s in syllables),
    )


def _not_run_verification() -> SanskritVerseVerification:
    return SanskritVerseVerification(
        status="not-run",
        checked_syllables=0,
        checks=0,
        method=VERIFIER_METHOD,
        issues=[],
    )


def _make_all_padas(
    source: str,
    script: SanskritScript,
    boundary_mode: PadaBoundaryMode,
    diagnostics: List[SanskritDiagnostic],
) -> List[AnalyzedSanskritPada]:
    padas: List[AnalyzedSanskritPada] = []
    syllable_count = 0
    for raw in _raw_padas(source, boundary_mode):
        made = _make_pada(raw, script, source, len(padas), syllable_count, diagnostics)
        if not made:
            continue
        pada, syllables = made
        padas.append(pada)
        syllable_count += len(syllables)
    return padas


def _ensure_verse_present(
    padas: Sequence[AnalyzedSanskritPada], diagnostics: List[SanskritDiagnostic]
) -> None:
    script_missing = any(item.code == "SCRIPT_UNDETECTED" for item in diagnostics)
    if padas or script_missing:
        return
    diagnostics.append(
        SanskritDiagnostic(
            code="EMPTY_VERSE",
            severity="error",
            message="No analyzable Sanskrit syllables were found.",
        )
    )


def _has_errors(diagnostics: Sequence[SanskritDiagnostic]) -> bool:
    return any(item.severity == "error" for item in diagnostics)


def analyze_sanskrit_verse(
    source_text: str,
    script: Optional[str] = "auto",
    boundary_mode: Optional[PadaBoundaryMode] = "auto",
) -> SanskritVerseAnalysis:
    """
    Analyzes arbitrary Sanskrit verse input without storing or mutating it.

    Explicit `lines` mode treats each non-empty line as one pāda; `dandas`
    treats each daṇḍa-delimited segment as one pāda; `single` scans one pāda.
    `auto` prefers written newlines, then daṇḍas, then a single segment.
    """
    # Imported here: the verifier imports this module's types.
    from .verse_verifier import verify_sanskrit_verse_analysis

    diagnostics: List[SanskritDiagnostic] = []
    resolved_mode = _resolve_boundary_mode(source_text, boundary_mode or "auto")
    resolved_script = _resolve_script(source_text, script or "auto", diagnostics)
    padas = (
        _make_all_padas(source_text, resolved_script, resolved_mode, diagnostics)
        if resolved_script
        else []
    )
    _note_ambiguous_ascii_transliteration(source_text, resolved_script, diagnostics)
    _ensure_verse_present(padas, diagnostics)

    syllables = [s for pada in padas for s in pada.syllables]
    analysis = SanskritVerseAnalysis(
        ok=False,
        source_text=source_text,
        script=resolved_script,
        boundary_mode=resolved_mode,
        normalized_text="\n".join(pada.normalized_iast for pada in padas),
        padas=padas,
        syllables=syllables,
        totals=_verse_totals(padas) if padas else SanskritVerseTotals(),
        diagnostics=diagnostics,
        verification=_not_run_verification(),
    )
    if not resolved_script or _has_errors(diagnostics):
        return analysis

    analysis.ok = True
    verification = verify_sanskrit_verse_analysis(analysis)
    if verification.status != "verified":
        analysis.ok = False
        analysis.diagnostics = diagnostics + [
            SanskritDiagnostic(
                code="INDEPENDENT_VERIFICATION_FAILED",
                severity="error",
                message=(
                    "The independently recomputed syllable analysis did not agree "
                    "with the maker."
                ),
            )
        ]
        analysis.verification = verification
        return analysis

    for syllable in analysis.syllables:
        syllable.verified = True
    analysis.verification = verification
    return analysis
