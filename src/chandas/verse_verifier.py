# -*- coding: utf-8 -*-
"""
Maker–checker pass over a syllable analysis.

Ported from Prasadam's lib/sanskrit-verse-verifier.ts.

This implementation deliberately does NOT call the production line scanner or
the one-akṣara classifier: it independently tokenizes normalized IAST,
reconstructs syllables, derives context, applies the weight rules, and
recomputes every aggregate before comparing the maker's output. A disagreement
means the verse analysis is not safe to present.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple, Union

from .core import AKSARA_RULES, AksaraParts, Weight
from .normalizer import iast_to_devanagari

METHOD = (
    "independent phoneme walk: recompute segmentation, context, weight, and "
    "totals from normalized IAST"
)

LONG_VOWELS = ("ai", "au", "ā", "ī", "ū", "ṝ", "ḹ", "e", "o")
SHORT_VOWELS = ("a", "i", "u", "ṛ", "ḷ")
VOWELS = LONG_VOWELS + SHORT_VOWELS
MARKS = ("m̐", "ṁ", "ṃ", "ḥ", "ẖ", "ḫ")
DIGRAPHS = ("kh", "gh", "ch", "jh", "ṭh", "ḍh", "th", "dh", "ph", "bh")
CONSONANTS = DIGRAPHS + tuple("kgṅcjñṭḍṇtdnpbmyrlvśṣsh") + ("ḻ",)
TRANSPARENT = frozenset([" ", "\t", "-", "’", "'", "|", "।", "॥"])


@dataclass
class _VerifyPhoneme:
    kind: str  # "vowel" | "consonant" | "mark" | "pluta"
    text: str
    long: bool = False


@dataclass
class _ExpectedSyllable:
    iast: str
    parts: AksaraParts
    weight: Weight
    matras: int
    rule: str
    reason: str
    anceps: bool
    pluta: bool
    next_iast: str


@dataclass
class _BuildingSyllable:
    onset: str
    vowel: str
    vowel_long: bool
    mark: str = ""
    coda: str = ""
    following_onset: int = 0
    pluta: bool = False


@dataclass
class _State:
    checks: int = 0
    issues: List = field(default_factory=list)


def _match_at(text: str, at: int, options: Sequence[str]) -> Optional[str]:
    for option in options:
        if text.startswith(option, at):
            return option
    return None


def _tokenize(text: str) -> Union[List[_VerifyPhoneme], str]:
    phonemes: List[_VerifyPhoneme] = []
    at = 0
    while at < len(text):
        if text[at] in TRANSPARENT:
            at += 1
            continue
        if text[at] in ("3", "३"):
            phonemes.append(_VerifyPhoneme("pluta", "3"))
            at += 1
            continue
        vowel = _match_at(text, at, VOWELS)
        if vowel:
            phonemes.append(_VerifyPhoneme("vowel", vowel, long=vowel in LONG_VOWELS))
            at += len(vowel)
            continue
        mark = _match_at(text, at, MARKS)
        if mark:
            phonemes.append(_VerifyPhoneme("mark", mark))
            at += len(mark)
            continue
        consonant = _match_at(text, at, CONSONANTS)
        if consonant:
            phonemes.append(_VerifyPhoneme("consonant", consonant))
            at += len(consonant)
            continue
        return f"unknown character {text[at]!r}"
    return phonemes


def _consonant_count(text: str) -> Optional[int]:
    count = 0
    at = 0
    while at < len(text):
        consonant = _match_at(text, at, CONSONANTS)
        if not consonant:
            return None
        count += 1
        at += len(consonant)
    return count


def _attach_vowel(
    syllables: List[_BuildingSyllable], onset: str, vowel: _VerifyPhoneme
) -> Optional[str]:
    size = _consonant_count(onset)
    if size is None:
        return "unparseable consonant onset"
    if syllables:
        syllables[-1].following_onset = size
    syllables.append(
        _BuildingSyllable(onset=onset, vowel=vowel.text, vowel_long=vowel.long)
    )
    return None


def _attach_mark(
    syllables: List[_BuildingSyllable], onset: str, text: str
) -> Optional[str]:
    if not syllables:
        return "mark before any vowel"
    current = syllables[-1]
    if onset != "" or current.mark != "":
        return "mark does not attach directly to one vowel"
    current.mark = text
    return None


def _attach_pluta(
    syllables: List[_BuildingSyllable], onset: str, previous_kind: Optional[str]
) -> Optional[str]:
    if not syllables or onset != "" or previous_kind != "vowel":
        return "pluta does not follow a vowel"
    current = syllables[-1]
    if current.pluta:
        return "multiple pluta markers on one syllable"
    current.pluta = True
    return None


def _build_syllables(
    phonemes: Sequence[_VerifyPhoneme],
) -> Union[List[_BuildingSyllable], str]:
    syllables: List[_BuildingSyllable] = []
    onset = ""
    previous_kind: Optional[str] = None
    for phoneme in phonemes:
        error: Optional[str] = None
        if phoneme.kind == "consonant":
            onset += phoneme.text
        elif phoneme.kind == "vowel":
            error = _attach_vowel(syllables, onset, phoneme)
            onset = ""
        elif phoneme.kind == "mark":
            error = _attach_mark(syllables, onset, phoneme.text)
        elif phoneme.kind == "pluta":
            error = _attach_pluta(syllables, onset, previous_kind)
        if error:
            return error
        previous_kind = phoneme.kind
    if syllables and onset != "":
        syllables[-1].coda = onset
    return syllables


def _weigh(syllable: _BuildingSyllable) -> Tuple[AksaraParts, Weight, int, str, str, bool]:
    weight: Weight = "laghu"
    matras = 1
    rule = "hrasva-laghu"
    if syllable.pluta:
        weight, matras, rule = "guru", 3, "pluta-guru"
    elif syllable.vowel_long:
        weight, matras, rule = "guru", 2, "dirgha-guru"
    elif syllable.mark != "":
        weight, matras, rule = "guru", 2, "mark-guru"
    elif syllable.coda != "":
        weight, matras, rule = "guru", 2, "closed-guru"
    elif syllable.following_onset >= 2:
        weight, matras, rule = "guru", 2, "position-guru"
    parts = AksaraParts(
        onset=syllable.onset,
        vowel=syllable.vowel,
        mark=syllable.mark,
        coda=syllable.coda,
    )
    reason = f"{weight} — {AKSARA_RULES[rule].plain} ({AKSARA_RULES[rule].sutra})"
    return parts, weight, matras, rule, reason, syllable.pluta


def _syllable_text(syllable: _BuildingSyllable) -> str:
    vowel = syllable.vowel + ("3" if syllable.pluta else "")
    return syllable.onset + vowel + syllable.mark + syllable.coda


def _expected_pada(text: str) -> Union[List[_ExpectedSyllable], str]:
    tokens = _tokenize(text)
    if isinstance(tokens, str):
        return tokens
    built = _build_syllables(tokens)
    if isinstance(built, str):
        return built
    if not built:
        return "no vowels"
    texts = [_syllable_text(s) for s in built]
    expected: List[_ExpectedSyllable] = []
    for index, syllable in enumerate(built):
        parts, weight, matras, rule, reason, pluta = _weigh(syllable)
        expected.append(
            _ExpectedSyllable(
                iast=texts[index],
                parts=parts,
                weight=weight,
                matras=matras,
                rule=rule,
                reason=reason,
                pluta=pluta,
                anceps=index == len(built) - 1,
                next_iast="".join(texts[index + 1:]),
            )
        )
    return expected


def _issue(state: _State, code: str, message: str, pada_index=None, position=None) -> None:
    from .verse_analysis import SanskritVerificationIssue

    state.issues.append(
        SanskritVerificationIssue(
            code=code, message=message, pada_index=pada_index, position=position
        )
    )


def _check(
    state: _State,
    condition: bool,
    code: str,
    message: str,
    pada_index=None,
    position=None,
) -> None:
    state.checks += 1
    if not condition:
        _issue(state, code, message, pada_index, position)


def _same_parts(left: AksaraParts, right: AksaraParts) -> bool:
    return (
        left.onset == right.onset
        and left.vowel == right.vowel
        and left.mark == right.mark
        and left.coda == right.coda
    )


def _point_at(source: str, offset: int) -> Tuple[int, int]:
    line = 1
    column = 1
    at = 0
    while at < offset:
        if source[at] == "\r":
            if at + 1 < len(source) and source[at + 1] == "\n":
                at += 1
            line += 1
            column = 1
        elif source[at] == "\n":
            line += 1
            column = 1
        else:
            column += 1
        at += 1
    return line, column


def _check_syllable(
    state: _State,
    actual,
    expected: _ExpectedSyllable,
    source: str,
    global_index: int,
    pada_index: int,
    position: int,
    script: str,
) -> None:
    from .verse_analysis import SanskritSourceSpan

    at = f"pada {pada_index + 1}, syllable {position + 1}"

    def verify(condition: bool, code: str, message: str) -> None:
        _check(state, condition, code, f"{at}: {message}", pada_index, position)

    verify(actual.index == global_index, "INDEX_MISMATCH", "global index differs")
    verify(actual.pada_index == pada_index, "PADA_INDEX_MISMATCH", "pada index differs")
    verify(actual.position == position, "POSITION_MISMATCH", "position differs")
    verify(actual.iast == expected.iast, "TEXT_MISMATCH", "IAST differs")
    verify(_same_parts(actual.parts, expected.parts), "PARTS_MISMATCH", "structural parts differ")
    verify(actual.weight == expected.weight, "WEIGHT_MISMATCH", "weight differs")
    verify(actual.matras == expected.matras, "MATRAS_MISMATCH", "matras differ")
    verify(actual.rule == expected.rule, "RULE_MISMATCH", "deciding rule differs")
    verify(actual.reason == expected.reason, "REASON_MISMATCH", "reason differs")
    verify(actual.anceps == expected.anceps, "ANCEPS_MISMATCH", "anceps differs")
    verify(actual.pluta == expected.pluta, "PLUTA_MISMATCH", "pluta differs")
    verify(
        actual.context.next_iast == expected.next_iast,
        "CONTEXT_MISMATCH",
        "following context differs",
    )
    verify(
        actual.context.pada_final == expected.anceps,
        "FINAL_CONTEXT_MISMATCH",
        "pada-final context differs",
    )
    deva = iast_to_devanagari(expected.iast).replace("3", "३")
    verify(actual.devanagari == deva, "DEVA_MISMATCH", "Devanāgarī rendering differs")
    verify(
        actual.text == (expected.iast if script == "iast" else deva),
        "DISPLAY_MISMATCH",
        "preferred display differs",
    )
    valid_bounds = (
        actual.span.start >= 0
        and actual.span.end > actual.span.start
        and actual.span.end <= len(source)
    )
    verify(valid_bounds, "SPAN_BOUNDS_INVALID", "source span is outside the input")
    if valid_bounds:
        verify(
            actual.source == source[actual.span.start:actual.span.end],
            "SOURCE_MISMATCH",
            "source slice differs",
        )
        start_line, start_column = _point_at(source, actual.span.start)
        end_line, end_column = _point_at(source, actual.span.end)
        recomputed = SanskritSourceSpan(
            start=actual.span.start,
            end=actual.span.end,
            line=start_line,
            column=start_column,
            end_line=end_line,
            end_column=end_column,
        )
        verify(actual.span == recomputed, "SPAN_LOCATION_MISMATCH", "line/column differs")


def verify_sanskrit_verse_analysis(analysis):
    """Rechecks a syllable analysis end to end. Returns a verification record."""
    from .verse_analysis import (
        SanskritVerseTotals,
        SanskritVerseVerification,
    )

    if not analysis.ok:
        return SanskritVerseVerification(
            status="not-run", checked_syllables=0, checks=0, method=METHOD, issues=[]
        )

    state = _State()
    totals = SanskritVerseTotals()
    global_index = 0

    for pada_index, pada in enumerate(analysis.padas):
        expected = _expected_pada(pada.normalized_iast)
        if isinstance(expected, str):
            _issue(
                state,
                "CHECKER_PARSE_FAILED",
                f"Pada {pada_index + 1}: {expected}",
                pada_index,
            )
            continue
        _check(
            state,
            pada.index == pada_index,
            "PADA_ORDER_MISMATCH",
            f"Pada {pada_index + 1}: index differs",
            pada_index,
        )
        _check(
            state,
            len(pada.syllables) == len(expected),
            "PADA_COUNT_MISMATCH",
            f"Pada {pada_index + 1}: syllable count differs",
            pada_index,
        )
        pattern = "".join("G" if s.weight == "guru" else "L" for s in expected)
        _check(
            state,
            pada.pattern == pattern,
            "PATTERN_MISMATCH",
            f"Pada {pada_index + 1}: pattern differs",
            pada_index,
        )
        _check(
            state,
            pada.matras == sum(s.matras for s in expected),
            "PADA_MATRAS_MISMATCH",
            f"Pada {pada_index + 1}: matras differ",
            pada_index,
        )
        for position, item in enumerate(expected):
            if position >= len(pada.syllables):
                continue
            _check_syllable(
                state,
                pada.syllables[position],
                item,
                analysis.source_text,
                global_index,
                pada_index,
                position,
                analysis.script,
            )
            global_index += 1
        totals.padas += 1
        totals.syllables += len(expected)
        totals.laghu += sum(1 for s in expected if s.weight == "laghu")
        totals.guru += sum(1 for s in expected if s.weight == "guru")
        totals.matras += sum(s.matras for s in expected)

    _check(
        state,
        analysis.totals == totals,
        "TOTALS_MISMATCH",
        "Verse totals differ from independent recomputation",
    )
    _check(
        state,
        len(analysis.syllables) == totals.syllables,
        "FLAT_COUNT_MISMATCH",
        "Flattened syllable count differs",
    )
    _check(
        state,
        analysis.normalized_text
        == "\n".join(pada.normalized_iast for pada in analysis.padas),
        "NORMALIZED_TEXT_MISMATCH",
        "Normalized verse text differs from its padas",
    )
    flattened = [s for pada in analysis.padas for s in pada.syllables]
    for index, syllable in enumerate(analysis.syllables):
        _check(
            state,
            index < len(flattened) and syllable.iast == flattened[index].iast,
            "FLAT_SYLLABLE_MISMATCH",
            f"Flattened syllable {index + 1} differs",
        )

    return SanskritVerseVerification(
        status="verified" if not state.issues else "failed",
        checked_syllables=global_index,
        checks=state.checks,
        method=METHOD,
        issues=state.issues,
    )
