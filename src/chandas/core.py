# -*- coding: utf-8 -*-
"""
Chandas (prosody) engine: deterministic akṣara segmentation, syllable weight,
and meter identification over IAST verse lines.

Ported from the Prasadam / Bhakta Bandhu TypeScript engine (lib/chandas.ts).
The rules, citations, and honesty policy below are carried over verbatim; only
the language changed.

Śāstric basis (each rule verified against the sources):
- Weight rules = Piṅgala, Chandaḥśāstra 1.9–1.13 with Halāyudha's
  Mṛtasañjīvanī: hrasva = laghu (1.9 gṛ l), before a conjunct — and, per the
  bhāṣya's ādi-extension, before anusvāra/visarga/jihvāmūlīya/upadhmānīya —
  = guru (1.11 dhrādiparaḥ), dīrgha = guru (1.12 he), a guru counts as two
  laghus (1.13 lau saḥ). Same rules at Pāṇini A. 1.4.10–12 and
  Vṛttaratnākara 1.9.
- Pāda-final anceps = CS 1.10 (g ante) with VR 1.9's "vā pādānte"; Halāyudha
  reads the option as vyavasthita-vibhāṣā (fixed per meter, never a free
  coin-flip) — computationally: flag it, let the template decide.
- Count-only meters = the glau adhikāra (CS 1.14): where no pattern is taught,
  syllables are "guru or laghu as they occur" (Halāyudha on 2.4) — the
  śāstric ground for identifying anuṣṭubh by count alone.

Honesty rules baked in:
- Metrical syllables cross word and hyphen boundaries ("yat sūrayaḥ" →
  ya·tsū·ra·yaḥ) — that is how the meter actually scans.
- The pāda-final syllable is anceps by convention: flagged, shown, and ignored
  when matching patterns — never silently "corrected".
- Meter identification only ever answers from the catalog or says
  "unidentified" — no guessing. (The hre/pre mute+liquid licence — VR 1.10
  "kvacid", CK v.19 — is deliberately NOT implemented: the best poets avoid
  it; a verse that fails strict scansion is a data question, not a licence to
  soften the rules silently.)
- Unknown characters raise, never skip.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Sequence, Tuple, Union

from .normalizer import devanagari_to_iast, iast_to_devanagari

Weight = Literal["laghu", "guru"]


class ChandasError(ValueError):
    """Raised when input cannot be scanned. Never swallowed silently."""


@dataclass
class Aksara:
    """One metrical syllable as scanned (may span word boundaries)."""

    text: str
    weight: Weight
    #: Pāda-final: metrically anceps by convention; matching ignores it.
    anceps: bool = False


@dataclass
class MeterResult:
    label: str
    identified: bool
    syllables_per_pada: Optional[int] = None
    note: Optional[str] = None
    #: Caesura position (syllables), when the meter defines one.
    yati: Optional[int] = None
    #: Gaṇa-chunked glyph template ("——— ◡◡— … ‖ …"), when pattern-defined.
    template: Optional[str] = None


# IAST phoneme inventory, longest-match first inside each class.
LONG_VOWELS: Tuple[str, ...] = ("ai", "au", "ā", "ī", "ū", "ṝ", "ḹ", "e", "o")
SHORT_VOWELS: Tuple[str, ...] = ("a", "i", "u", "ṛ", "ḷ")
VOWELS: Tuple[str, ...] = LONG_VOWELS + SHORT_VOWELS

# U+0310 combining candrabindu (m̐) decomposes to "m" + mark; match it first.
# Guru-makers per Halāyudha on CS 1.11: anusvāra, visarga, and the two rare
# visarga variants jihvāmūlīya (ẖ, before k/kh) and upadhmānīya (ḫ, before
# p/ph). Candrabindu carries no weight rule anywhere in the śāstra (verified
# gap) — treating it as an anusvāra-class guru-maker is engine convention,
# following universal practice for m̐ in ISO-romanized texts.
NASAL_MARKS: Tuple[str, ...] = ("m̐", "ṁ", "ṃ", "ḥ", "ẖ", "ḫ")

CONSONANT_DIGRAPHS: Tuple[str, ...] = (
    "kh", "gh", "ch", "jh", "ṭh", "ḍh", "th", "dh", "ph", "bh",
)
CONSONANTS: Tuple[str, ...] = (
    CONSONANT_DIGRAPHS + tuple("kgṅcjñṭḍṇtdnpbmyrlvśṣsh") + ("ḻ",)
)

#: Ignored for scansion: spaces and hyphens are transparent; avagraha is a
#: written elision mark; daṇḍas terminate lines in some sources.
#: Skipped by the scanner without becoming a phoneme. The combining
#: candrabindu is here because an anunasika vowel is still one vowel and
#: still light: nasality is not weight, so it must not be read as a mark
#: the way anusvara is. Skipping it also keeps every phoneme offset
#: pointing into the original string, which the it-samjna analysis in
#: src/astadhyayi/itsamjna.py relies on to locate 1.3.2 marks.
TRANSPARENT = frozenset(
    [" ", "	", "-", "’", "'", "|", "।", "॥", "̐"]
)


@dataclass
class Phoneme:
    kind: Literal["vowel", "mark", "consonant"]
    text: str
    start: int
    long: bool = False


def _match_at(line: str, i: int, options: Sequence[str]) -> Optional[str]:
    for option in options:
        if line.startswith(option, i):
            return option
    return None


def scan_phonemes(line: str) -> List[Phoneme]:
    phonemes: List[Phoneme] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch in TRANSPARENT:
            i += 1
            continue
        vowel = _match_at(line, i, VOWELS)
        if vowel:
            phonemes.append(
                Phoneme("vowel", vowel, i, long=vowel in LONG_VOWELS)
            )
            i += len(vowel)
            continue
        mark = _match_at(line, i, NASAL_MARKS)
        if mark:
            phonemes.append(Phoneme("mark", mark, i))
            i += len(mark)
            continue
        consonant = _match_at(line, i, CONSONANTS)
        if consonant:
            phonemes.append(Phoneme("consonant", consonant, i))
            i += len(consonant)
            continue
        raise ChandasError(
            f'chandas: unknown character "{ch}" (U+{ord(ch):04x}) in "{line}"'
        )
    return phonemes


@dataclass
class _SylInfo:
    text: str
    long: bool
    marked: bool
    onset_after: int
    #: Offset in `line` where this syllable's onset (or vowel) begins.
    start: int
    #: Offset in `line` where this syllable's vowel begins.
    vowel_start: int


def _cluster_size(onset: str) -> int:
    """Counts consonant phonemes in an onset string (digraphs = one)."""
    count = 0
    i = 0
    while i < len(onset):
        consonant = _match_at(onset, i, CONSONANTS)
        if not consonant:
            raise ChandasError(f'chandas: unparseable onset "{onset}"')
        count += 1
        i += len(consonant)
    return count


def _scan_syllables(line: str) -> Tuple[List[_SylInfo], str]:
    """
    Groups phonemes into syllables: onset* + vowel + mark?; trailing
    consonants after the last vowel attach to the final syllable.
    """
    phonemes = scan_phonemes(line)
    syllables: List[_SylInfo] = []
    onset = ""
    onset_start = -1
    for p in phonemes:
        if p.kind == "consonant":
            if onset == "":
                onset_start = p.start
            onset += p.text
            continue
        if p.kind == "vowel":
            if syllables:
                syllables[-1].onset_after = _cluster_size(onset)
            syllables.append(
                _SylInfo(
                    text=onset + p.text,
                    long=p.long,
                    marked=False,
                    onset_after=0,
                    start=p.start if onset == "" else onset_start,
                    vowel_start=p.start,
                )
            )
            onset = ""
            onset_start = -1
            continue
        # Nasal mark: belongs to the syllable just closed.
        if not syllables:
            raise ChandasError(f'chandas: mark "{p.text}" before any vowel in "{line}"')
        syllables[-1].text += p.text
        syllables[-1].marked = True
    if syllables and onset:
        syllables[-1].text += onset
    return syllables, onset


def _syllable_weights(syllables: Sequence[_SylInfo], trailing: str) -> List[Weight]:
    weights: List[Weight] = []
    for i, s in enumerate(syllables):
        last = i == len(syllables) - 1
        closed_final = last and len(trailing) > 0
        heavy = s.long or s.marked or s.onset_after >= 2 or closed_final
        weights.append("guru" if heavy else "laghu")
    return weights


def syllabify_iast_line(line: str) -> List[Aksara]:
    """
    Segments one pāda line of IAST into metrical akṣaras with weights.

    Weight (classical rule): guru iff long vowel, OR the vowel carries
    anusvāra/visarga/candrabindu, OR ≥2 consonants follow before the next
    vowel, OR the line ends in a consonant after it (closed final syllable).
    """
    syllables, trailing = _scan_syllables(line)
    if not syllables:
        return []
    weights = _syllable_weights(syllables, trailing)
    return [
        Aksara(text=s.text, weight=weights[i], anceps=(i == len(syllables) - 1))
        for i, s in enumerate(syllables)
    ]


# --- IAST word annotation ------------------------------------------------


@dataclass
class IastPiece:
    #: Verbatim substring of the word (hyphens/avagraha included).
    text: str
    #: Present when this piece carries a metrical syllable's vowel.
    weight: Optional[Weight] = None
    anceps: bool = False


@dataclass
class IastWord:
    pieces: List[IastPiece]


_CUT_LETTER = re.compile(r"[a-zāīūṛṝḷḹṁṃḥśṣñṅṇṭḍ]")


def annotate_iast_line(line: str) -> List[IastWord]:
    """
    Maps a pāda line's metrical scansion back onto its words: each word is
    split into verbatim substrings ("pieces") at the syllable-onset offsets
    that fall inside it, and the piece containing a syllable's VOWEL carries
    that syllable's weight. Cross-word syllables ("yat sūrayaḥ" → ya·tsū…)
    therefore mark the vowel-bearing piece only — the stranded consonant tail
    of the previous word stays unmarked, and no word's spelling is ever
    altered (pieces always concatenate to the exact word).
    """
    syllables, trailing = _scan_syllables(line)
    weights = _syllable_weights(syllables, trailing)

    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", line)]

    result: List[IastWord] = []
    for start, end in words:
        # Cut points inside this word: each syllable's start offset, snapped so
        # a piece is never phoneme-less (a leading avagraha stays attached).
        cuts = [
            s.start
            for s in syllables
            if start < s.start < end and _CUT_LETTER.search(line[start:s.start])
        ]
        bounds = [start, *cuts, end]
        pieces: List[IastPiece] = []
        for b in range(len(bounds) - 1):
            frm, to = bounds[b], bounds[b + 1]
            index = next(
                (i for i, s in enumerate(syllables) if frm <= s.vowel_start < to),
                -1,
            )
            if index >= 0:
                pieces.append(
                    IastPiece(
                        text=line[frm:to],
                        weight=weights[index],
                        anceps=(index == len(syllables) - 1),
                    )
                )
            else:
                pieces.append(IastPiece(text=line[frm:to]))
        result.append(IastWord(pieces=pieces))
    return result


def yati_word_boundary(line: str, yati: int) -> Optional[int]:
    """
    The word index after which a meter's yati (caesura) falls in this line,
    or None when the yati splits a word — honesty by absence: no cue where a
    breath would be wrong. A word-final consonant welded by sandhi into the
    next syllable (itarataś·cārtheṣv) does NOT block the yati: reciters
    breathe at the written word boundary there, exactly as the tradition
    prescribes for śārdūlavikrīḍita's 12 + 7.
    """
    annotated = annotate_iast_line(line)
    count = 0
    for w, word in enumerate(annotated):
        count += sum(1 for p in word.pieces if p.weight is not None)
        # A "yati" after the final word is no caesura at all.
        if count == yati:
            return w if w < len(annotated) - 1 else None
        if count > yati:
            return None
    return None


def split_iast_word_head(word: str) -> Tuple[str, str]:
    """
    Splits an IAST word into its first akṣara (head) and the rest (tail) for
    the memorize-mode hint. A leading avagraha stays with the head (it is
    rendered text). A word with no vowel is returned whole as the head.
    """
    i = 0
    while i < len(word) and word[i] in ("’", "'"):
        i += 1
    while True:
        consonant = _match_at(word, i, CONSONANTS)
        if not consonant:
            break
        i += len(consonant)
    vowel = _match_at(word, i, VOWELS)
    if not vowel:
        return word, ""
    i += len(vowel)
    mark = _match_at(word, i, NASAL_MARKS)
    if mark:
        i += len(mark)
    return word[:i], word[i:]


# --- Devanāgarī orthographic clusters ------------------------------------

# An independent vowel (or ॐ) with marks, or a conjunct chain
# (consonant+virāma)* + consonant (+nukta) + optional vowel sign + optional
# nasal mark. Splitting only at a cluster boundary keeps complex-text shaping
# identical across the two spans.
# Written with explicit escapes: the consonant class is the two ranges
# U+0915–U+0939 (ka–ha) and U+0958–U+095F (qa–yya, the precomposed nukta
# letters), and U+093C is the combining nukta. Spelling them literally invites
# the source file's own normalization to turn क़ into क + nukta, which would
# silently break the class into a bad range.
_DEVA_CONSONANT_CLASS = "[क-हक़-य़]"
_NUKTA = "़"
_VIRAMA = "्"
_DEVA_MARKS = "[ँ-ः]"
_DEVA_VOWEL_SIGNS = "[ा-ौॢॣ]"
_DEVA_INDEPENDENT_VOWELS = "[ऄ-औॠॡ]"

DEVA_CLUSTER = re.compile(
    "^(?:ॐ"
    f"|{_DEVA_INDEPENDENT_VOWELS}{_DEVA_MARKS}?"
    f"|(?:{_DEVA_CONSONANT_CLASS}{_NUKTA}?{_VIRAMA})*"
    f"{_DEVA_CONSONANT_CLASS}{_NUKTA}?"
    f"{_DEVA_VOWEL_SIGNS}?{_DEVA_MARKS}?)"
)

DEVA_LONG_SIGNS = re.compile("[ाीूॄॣेैोौ]|[आईऊॠॡएऐओऔ]|ॐ")
DEVA_RING_SIGNS = re.compile("[ंँः]")


@dataclass
class DevaCluster:
    #: Verbatim substring of the word — always a complete orthographic cluster.
    text: str
    #: Carries a long vowel — the mouth must hold it ("stretch").
    stretch: bool = False
    #: Word-final inherent `a` — voice it (the Hindi schwa-deletion site).
    keel: bool = False
    #: Carries anusvāra/candrabindu/visarga — let it ring.
    ring: bool = False


def annotate_deva_word(word: str) -> List[DevaCluster]:
    """
    Splits a Devanāgarī word into its orthographic clusters and flags the
    three mouth-action sites (long-vowel stretch, word-final inherent-a keel,
    nasal/visarga ring). Cluster boundaries are the same shaping-safe cuts
    split_deva_word_head uses, so complex-text rendering is never disturbed.
    Fail-safe: unparseable text is returned as one unflagged cluster (nothing
    marked is safer than something wrong).
    """
    texts: List[str] = []
    rest = word
    while rest:
        # Avagraha is an elision sign, not a cluster: it rides the cluster
        # before it (यतोऽन्वयाद् → …तोऽ…), keeping the following conjuncts
        # individually markable.
        if rest.startswith("ऽ") and texts:
            texts[-1] += "ऽ"
            rest = rest[1:]
            continue
        match = DEVA_CLUSTER.match(rest)
        if not match or not match.group(0):
            texts.append(rest)
            break
        text = match.group(0)
        # A dangling word-final virāma belongs to the last cluster.
        if rest[len(text):] == "्":
            text += "्"
        texts.append(text)
        rest = rest[len(text):]

    clusters: List[DevaCluster] = []
    for i, text in enumerate(texts):
        last = i == len(texts) - 1
        ring = bool(DEVA_RING_SIGNS.search(text))
        stretch = bool(DEVA_LONG_SIGNS.search(text))
        # Inherent `a`: a consonant-based final cluster with no vowel sign, no
        # virāma, and no ring mark — the exact site Hindi reading habits drop.
        keel = (
            last
            and not ring
            and bool(re.match("^[क-ह]", text))
            and not re.search("[ा-ौॢॣ्]", text)
        )
        clusters.append(DevaCluster(text=text, stretch=stretch, keel=keel, ring=ring))
    return clusters


def split_deva_word_head(word: str) -> Tuple[str, str]:
    """
    Splits a Devanāgarī word after its first orthographic cluster. Fail-safe:
    if the word doesn't start with a recognizable cluster, it is returned
    whole as the head (the word simply stays visible in hints — honest and
    shaping-safe, never a broken conjunct).
    """
    match = DEVA_CLUSTER.match(word)
    if not match or not match.group(0):
        return word, ""
    head = match.group(0)
    rest = word[len(head):]
    if rest == "्":
        return word, ""
    return head, rest


def _clean_deva_line(line: str) -> str:
    """
    Display-normalizes a witness Devanāgarī line for scansion: some sources
    encode visarga as an ASCII colon; daṇḍas and verse numbers are
    punctuation, not syllables.
    """
    out = re.sub(r"([ऀ-ॿ]) ?:", r"\1ः", line)
    out = re.sub(r"[।॥०-९]", " ", out)
    out = re.sub(r"[‐‑‒–—−-]", " ", out)
    return re.sub(r"\s+", " ", out.strip())


def _leading_avagraha_cluster(word: str) -> Optional[Tuple[str, str]]:
    following = DEVA_CLUSTER.match(word[1:])
    if not following or not following.group(0):
        return None
    return "ऽ" + following.group(0), word[1 + len(following.group(0)):]


def _deva_word_chant_clusters(word: str) -> Optional[List[str]]:
    """
    Tokenizes a Devanāgarī word into metrical display units: orthographic
    clusters, with the avagraha and any vowel-less trailing consonant merged
    into the preceding cluster (mirroring the IAST rule that a trailing
    consonant attaches to the last syllable: sva·rāṭ, never sva·rā·ṭ). The
    units concatenate back to the exact word — nothing is fabricated.
    None on unparseable input (fail into the IAST-only view, never guess).
    """
    clusters: List[str] = []
    rest = word
    if rest.startswith("ऽ"):
        leading = _leading_avagraha_cluster(rest)
        if not leading:
            return None
        clusters.append(leading[0])
        rest = leading[1]
    while rest:
        if rest.startswith("ऽ"):
            if not clusters:
                return None
            clusters[-1] += "ऽ"
            rest = rest[1:]
            continue
        match = DEVA_CLUSTER.match(rest)
        if not match or not match.group(0):
            return None
        text = match.group(0)
        rest = rest[len(text):]
        if rest == "्":
            # Word-final consonant with virāma: carries no vowel, so it
            # belongs to the previous syllable's cluster.
            text += "्"
            rest = ""
            if clusters:
                clusters[-1] += text
                continue
        clusters.append(text)
    return clusters or None


@dataclass
class DevaChantWord:
    """Clusters of one written word (or its fragment, when a pāda boundary
    falls inside a sandhi weld the witness prints solid)."""

    clusters: List[str]


def _padas_per_deva_line(deva_line_count: int, pada_count: int) -> Optional[int]:
    """The two printed shapes the witness uses: one pāda per Devanāgarī line,
    or two (vedabase prints anuṣṭubh as half-verse lines)."""
    if pada_count == deva_line_count:
        return 1
    if pada_count == deva_line_count * 2:
        return 2
    return None


def _chunk_deva_line_into_padas(
    line: str, counts: Sequence[int]
) -> Optional[List[List[DevaChantWord]]]:
    words: List[List[str]] = []
    for token in _clean_deva_line(line).split(" "):
        if token == "":
            continue
        clusters = _deva_word_chant_clusters(token)
        if clusters is None:
            return None
        words.append(clusters)
    total = sum(len(w) for w in words)
    if total != sum(counts):
        return None
    padas: List[List[DevaChantWord]] = []
    wi = 0
    ci = 0
    for count in counts:
        pada: List[DevaChantWord] = []
        need = count
        while need > 0:
            word = words[wi]
            take = min(need, len(word) - ci)
            pada.append(DevaChantWord(clusters=word[ci:ci + take]))
            need -= take
            ci += take
            if ci == len(word):
                wi += 1
                ci = 0
        padas.append(pada)
    return padas


def deva_chant_lines(
    deva_lines: Sequence[str], pada_syllable_counts: Sequence[int]
) -> Optional[List[List[DevaChantWord]]]:
    """
    Slices the witness's Devanāgarī lines into per-pāda groups of written
    words, each word a run of orthographic clusters aligned 1:1 with the IAST
    metrical scan (`pada_syllable_counts` = syllables per IAST pāda line).
    None whenever the two scripts cannot be aligned exactly (count mismatch,
    unknown sign, unexpected line shape) — the caller falls back to the
    IAST-only view rather than guessing.
    """
    per_line = _padas_per_deva_line(len(deva_lines), len(pada_syllable_counts))
    if per_line is None:
        return None
    result: List[List[DevaChantWord]] = []
    for li, line in enumerate(deva_lines):
        counts = pada_syllable_counts[li * per_line:(li + 1) * per_line]
        padas = _chunk_deva_line_into_padas(line, counts)
        if padas is None:
            return None
        result.extend(padas)
    return result


def deva_yati_word_boundary(line: str, yati: int) -> Optional[int]:
    """
    Devanāgarī counterpart of yati_word_boundary: the token index (in the
    witness line's own space-split rendering) after which the meter's yati
    falls, counting metrical syllables through the orthographic clusters.
    Daṇḍa and verse-number tokens count zero syllables; a "boundary" followed
    only by punctuation is line-end, not a caesura.
    """
    tokens = [t for t in re.split(r"\s+", line) if t]
    count = 0
    for w, token in enumerate(tokens):
        cleaned = _clean_deva_line(token)
        if cleaned == "":
            continue
        clusters = _deva_word_chant_clusters(cleaned)
        if clusters is None:
            return None
        count += len(clusters)
        if count == yati:
            text_follows = any(_clean_deva_line(t) != "" for t in tokens[w + 1:])
            return w if text_follows else None
        if count > yati:
            return None
    return None


@dataclass
class DevaYatiInWord:
    #: Token index (space-split, as the witness line renders) of the word the
    #: yati falls inside.
    word_index: int
    #: Cluster index within that word after which the breath tick renders
    #: (avagraha attached to its host, final virāma merged back).
    cluster_index: int


def deva_yati_in_word(line: str, yati: int) -> Optional[DevaYatiInWord]:
    """
    Where the meter's yati falls INSIDE a written word — the sandhi-welded
    case deva_yati_word_boundary honestly refuses. Returns the exact cluster
    to tick after, or None when the yati sits at a word boundary (the widened
    space handles it), at line end, or cannot be counted.
    """
    tokens = [t for t in re.split(r"\s+", line) if t]
    count = 0
    for w, token in enumerate(tokens):
        cleaned = _clean_deva_line(token)
        if cleaned == "":
            continue
        clusters = _deva_word_chant_clusters(cleaned)
        if clusters is None:
            return None
        if count + len(clusters) > yati:
            into_word = yati - count
            return DevaYatiInWord(w, into_word - 1) if into_word > 0 else None
        count += len(clusters)
        if count == yati:
            return None
    return None


# --- akṣara validator + weight classifier --------------------------------


@dataclass
class AksaraParts:
    """
    Consonants before the vowel (the onset — may be a whole conjunct). All
    parts come back in the script you asked in: classify_aksara_iast answers
    in IAST, classify_aksara_deva in Devanāgarī (त् + अ + ः).
    """

    onset: str = ""
    vowel: str = ""
    #: Anusvāra/visarga-class rider (ṁ ṃ ḥ m̐ ẖ ḫ / ं ः ँ) or "".
    mark: str = ""
    #: Trailing consonants: the giver asserts a CLOSED syllable (line-final
    #: or the first limb of a conjunct).
    coda: str = ""


@dataclass
class AksaraContext:
    #: What follows the syllable (next syllable / rest of the line), in the
    #: same script as the syllable; "" = a pause follows. Resolves
    #: guru-by-position. None = unknown.
    next: Optional[str] = None
    #: The syllable stands at pāda end — anceps by convention
    #: (CS 1.10 gante · VR 1.9 vā pādānte).
    pada_final: bool = False


@dataclass
class AksaraJudgement:
    valid: bool
    reason: str
    #: The syllable as judged, in the script it was given in.
    text: str = ""
    parts: AksaraParts = field(default_factory=AksaraParts)
    weight: Optional[Weight] = None
    #: laghu = 1, guru = 2, pluta = 3 (CS 1.13 lau saḥ).
    matras: Optional[int] = None
    #: Which rule decided (see AKSARA_RULES for the citations).
    rule: Optional[str] = None
    #: True for a short open unmarked syllable judged WITHOUT context:
    #: a following conjunct would make it guru by position.
    position_sensitive: bool = False
    #: Set when context.pada_final: the final counts as either.
    anceps: bool = False
    pluta: bool = False


@dataclass(frozen=True)
class AksaraRule:
    plain: str
    sutra: str


#: The deciding rules with their verified citations (Piṅgala CS 1.9–1.13 and
#: Pāṇini 1.4.10–12 both sighted verbatim).
AKSARA_RULES: Dict[str, AksaraRule] = {
    "dirgha-guru": AksaraRule(
        plain="its vowel is long — the mouth holds it for two counts",
        sutra="CS 1.12 he · Pāṇini 1.4.12 dīrghaṁ ca",
    ),
    "mark-guru": AksaraRule(
        plain="it carries anusvāra/visarga — the ring of sound adds a count",
        sutra="CS 1.11 dhrādiparaḥ (Halāyudha's ādi-extension) · VR 1.9 sānusvāro visargāntaḥ",
    ),
    "closed-guru": AksaraRule(
        plain="it is closed by a consonant — the closure takes the second count",
        sutra="CS 1.11 · Pāṇini 1.4.11 saṁyoge guru",
    ),
    "position-guru": AksaraRule(
        plain="a conjunct follows — the mouth braces for it, adding a count",
        sutra="CS 1.11 dhrādiparaḥ · Pāṇini 1.4.11 saṁyoge guru",
    ),
    "hrasva-laghu": AksaraRule(
        plain="a short open unmarked syllable — one count",
        sutra="CS 1.9 gṛ l · Pāṇini 1.4.10 hrasvaṁ laghu",
    ),
    # The 3-mātrā duration is śāstra (P. 1.2.27); the guru CLASS is inference
    # — chandas is binary and its rule verses never mention pluta, but a vowel
    # that is not hrasva cannot scan laghu. Vedic / recitational notation.
    "pluta-guru": AksaraRule(
        plain="a protracted (pluta) vowel of three counts — not short, so it can only scan heavy",
        sutra="Pāṇini 1.2.27 ūkālo 'j jhrasva-dīrgha-plutaḥ",
    ),
}


@dataclass
class _ParsedAksara:
    parts: AksaraParts
    vowel_long: bool


def _parse_aksara(text: str, show) -> Union[_ParsedAksara, str]:
    """
    Structural walk: onset* → vowel → mark? → coda*. Any other order (or
    vowel count ≠ 1) is not a single akṣara. Returns a reason string on
    failure.
    """
    try:
        phonemes = scan_phonemes(text)
    except ChandasError as error:
        return str(error).replace("chandas: ", "", 1)
    vowels = [p for p in phonemes if p.kind == "vowel"]
    if not vowels:
        mark = next((p for p in phonemes if p.kind == "mark"), None)
        if mark:
            return (
                f'"{show(mark.text)}" without a vowel — anusvāra and visarga are '
                "ayogavāha, nija-svara-vivarjitāḥ ('devoid of their own vowel', "
                "Amoghānandinī Śikṣā 2.4–5): they ride a vowel, never stand alone"
            )
        return (
            "no vowel — a consonant cannot sound alone (vyañjanaṁ svareṇa "
            "sasvaram, VPr 1.107); every akṣara has exactly one svara at its "
            "core (svaro 'kṣaram, VPr 1.99)"
        )
    if len(vowels) > 1:
        split = "·".join(show(a.text) for a in syllabify_iast_line(text))
        return (
            f"contains {len(vowels)} vowels — one svara, one akṣara (VPr 1.99), "
            f"so that is {len(vowels)} syllables, not one (splits as {split})"
        )
    return _assemble_parts(phonemes, show)


def _assemble_parts(phonemes: Sequence[Phoneme], show) -> Union[_ParsedAksara, str]:
    """Walks the (single-vowel) phoneme sequence into onset/vowel/mark/coda,
    rejecting any ordering the definition forbids."""
    parts = AksaraParts()
    vowel_long = False
    for p in phonemes:
        if p.kind == "consonant":
            if parts.vowel == "":
                parts.onset += p.text
            else:
                parts.coda += p.text
            continue
        if p.kind == "vowel":
            parts.vowel = p.text
            vowel_long = p.long
            continue
        # mark: anusvāra/visarga attach directly to the vowel they follow
        # (visarjanīyānusvārau bhajete pūrvam akṣaram, RPr 18.18).
        if parts.vowel == "":
            return (
                f'"{show(p.text)}" before any vowel — anusvāra and visarga are '
                "ayogavāha: they ride a vowel, never stand without one"
            )
        if parts.coda != "" or parts.mark != "":
            return f'"{show(p.text)}" must attach directly to the vowel (RPr 18.18)'
        parts.mark = p.text
    return _ParsedAksara(parts=parts, vowel_long=vowel_long)


#: In-line transparent signs for position counting: word spaces, hyphens, and
#: the written avagraha — guru-by-position crosses these (yat sūrayaḥ scans
#: ya·tsū). A daṇḍa is a real pause and stops the count.
ONSET_TRANSPARENT = frozenset([" ", "\t", "-", "’", "'"])


def _leading_onset_size(next_text: str) -> int:
    """How many consonants open the following text (digraphs = one)."""
    count = 0
    i = 0
    while i < len(next_text):
        if next_text[i] in ONSET_TRANSPARENT:
            i += 1
            continue
        consonant = _match_at(next_text, i, CONSONANTS)
        if not consonant:
            break
        count += 1
        i += len(consonant)
    return count


def _judged(
    parts: AksaraParts,
    text: str,
    context: Optional[AksaraContext],
    pluta: bool,
    weight: Weight,
    matras: int,
    rule: str,
    position_sensitive: bool,
) -> AksaraJudgement:
    return AksaraJudgement(
        valid=True,
        text=text,
        parts=parts,
        weight=weight,
        matras=matras,
        rule=rule,
        reason=f"{weight} — {AKSARA_RULES[rule].plain} ({AKSARA_RULES[rule].sutra})",
        position_sensitive=position_sensitive,
        anceps=bool(context and context.pada_final),
        pluta=pluta,
    )


def _weigh_aksara(
    parsed: _ParsedAksara,
    pluta: bool,
    context: Optional[AksaraContext],
    text: str,
) -> AksaraJudgement:
    parts, vowel_long = parsed.parts, parsed.vowel_long

    def make(weight: Weight, matras: int, rule: str, sensitive: bool) -> AksaraJudgement:
        return _judged(parts, text, context, pluta, weight, matras, rule, sensitive)

    if pluta:
        return make("guru", 3, "pluta-guru", False)
    if vowel_long:
        return make("guru", 2, "dirgha-guru", False)
    if parts.mark != "":
        return make("guru", 2, "mark-guru", False)
    if parts.coda != "":
        return make("guru", 2, "closed-guru", False)
    # Short, open, unmarked: laghu by nature (hrasvaṁ laghu) — position can
    # override, so resolve against context when given, else flag it.
    if context is None or context.next is None:
        return make("laghu", 1, "hrasva-laghu", True)
    if _leading_onset_size(context.next) >= 2:
        return make("guru", 2, "position-guru", False)
    return make("laghu", 1, "hrasva-laghu", False)


def _is_devanagari(text: str) -> bool:
    """Any code point in the Devanagari (U+0900-097F) or Vedic Extensions
    (U+1CD0-1CFF) blocks."""
    for ch in text:
        cp = ord(ch)
        if (0x0900 <= cp <= 0x097F) or (0x1CD0 <= cp <= 0x1CFF):
            return True
    return False


_LATIN_LETTER_RANGES = ((0x41, 0x5A), (0x61, 0x7A), (0x00C0, 0x024F), (0x1E00, 0x1EFF))


def _has_latin_letter(text: str) -> bool:
    return any(
        lo <= ord(ch) <= hi for ch in text for lo, hi in _LATIN_LETTER_RANGES
    )


def _barred_aksara_input(text: str) -> Optional[AksaraJudgement]:
    """Empty / broken input checks shared by both script entries."""
    if text == "":
        return AksaraJudgement(valid=False, reason="empty input")
    if re.search(r"[\s\-|।॥]", text):
        return AksaraJudgement(
            valid=False,
            reason=(
                "contains a break (space/hyphen/daṇḍa) — a syllable is one connected "
                "piece of sound; use the line scanner for longer text"
            ),
        )
    return None


def _classify_iast_core(
    text_in: str, context: Optional[AksaraContext], show
) -> AksaraJudgement:
    """The shared core: judges normalized IAST, quoting fragments through
    `show` so each script entry speaks its own script."""
    # Pluta: the protracted vowel is written with a following ३/3
    # (Whitney §78: "marked by a following figure 3: thus, आ३ ā3").
    markers = [m.start() for m in re.finditer("[3३]", text_in)]
    if len(markers) > 1:
        return AksaraJudgement(
            valid=False, reason="a syllable can carry only one pluta (३) marker"
        )
    pluta = len(markers) == 1
    marker_at = markers[0] if pluta else -1
    text = text_in[:marker_at] + text_in[marker_at + 1:] if pluta else text_in

    parsed = _parse_aksara(text, show)
    if isinstance(parsed, str):
        return AksaraJudgement(valid=False, reason=parsed)
    vowel_end = len(parsed.parts.onset) + len(parsed.parts.vowel)
    if pluta and marker_at != vowel_end:
        return AksaraJudgement(
            valid=False,
            reason=(
                "pluta (३) must follow the vowel directly, before any mark or "
                "closing consonant"
            ),
        )
    return _weigh_aksara(parsed, pluta, context, text)


def classify_aksara_iast(
    input_text: str, context: Optional[AksaraContext] = None
) -> AksaraJudgement:
    """
    Validates whether `input_text` is one well-formed akṣara and classifies
    its weight — the prātiśākhya definition made executable:

      akṣara = onset-consonants* + ONE vowel + (anusvāra/visarga)? + coda*

      VPr 1.99–1.101  svaro 'kṣaram · sahādyair vyañjanaiḥ · uttaraiś
                      cāvasitaiḥ — the vowel IS the syllable; preceding
                      consonants join it; so do trailing ones at a pause.
      VPr 1.107       vyañjanaṁ svareṇa sasvaram — a consonant sounds only
                      through a vowel (TPr 21.1: it is the vowel's limb).
      RPr 18.18       visarjanīyānusvārau bhajete pūrvam akṣaram — the marks
                      belong to the vowel they follow.

    This entry reads IAST only (a bare-consonant input like "k" is honestly
    rejected: no svara, no syllable). A short open unmarked syllable judged
    WITHOUT context is laghu with position_sensitive=True, because the śāstra
    decides that case from what follows, and honesty beats a guess.
    """
    text = re.sub(r"[’']", "", input_text.strip())
    barred = _barred_aksara_input(text)
    if barred:
        return barred
    if _is_devanagari(text):
        return AksaraJudgement(
            valid=False,
            reason="Devanāgarī input — this checker reads IAST; use classify_aksara_deva",
        )
    return _classify_iast_core(text, context, lambda iast: iast)


def classify_aksara_deva(
    input_text: str, context: Optional[AksaraContext] = None
) -> AksaraJudgement:
    """
    The Devanāgarī twin of classify_aksara_iast: same definition, same weight
    rules, but it reads संस्कृत input and answers in it. Internally the
    verdict is computed on the IAST rendering (one engine, one truth); only
    the display is script-faithful.
    """
    text = re.sub(r"[ऽ’']", "", input_text.strip())
    barred = _barred_aksara_input(text)
    if barred:
        return barred
    if not _is_devanagari(text):
        return AksaraJudgement(
            valid=False,
            reason="no Devanāgarī here — this checker reads Devanāgarī; use classify_aksara_iast",
        )
    if _has_latin_letter(text):
        return AksaraJudgement(
            valid=False, reason="mixed scripts — give the syllable in one script at a time"
        )
    judged = _classify_iast_core(
        devanagari_to_iast(text), _deva_context(context), iast_to_devanagari
    )
    if not judged.valid:
        return judged
    judged.text = re.sub("[3३]", "", text)
    judged.parts = _deva_parts(judged.parts)
    return judged


def _deva_context(context: Optional[AksaraContext]) -> Optional[AksaraContext]:
    """Renders context.next into IAST when it was given in Devanāgarī."""
    if context is None or context.next is None or not _is_devanagari(context.next):
        return context
    return AksaraContext(next=devanagari_to_iast(context.next), pada_final=context.pada_final)


def _deva_parts(parts: AksaraParts) -> AksaraParts:
    """Renders judged IAST parts back into Devanāgarī: bare consonants keep
    their halanta (त्, त्स्), the vowel shows its independent form (अ, ऊ),
    marks come back as their signs (ं, ः)."""
    def show(iast: str) -> str:
        return "" if iast == "" else iast_to_devanagari(iast)

    return AksaraParts(
        onset=show(parts.onset),
        vowel=show(parts.vowel),
        mark=show(parts.mark),
        coda=show(parts.coda),
    )


def classify_aksara(
    input_text: str, context: Optional[AksaraContext] = None
) -> AksaraJudgement:
    """Convenience router: detects the script and delegates."""
    return (
        classify_aksara_deva(input_text, context)
        if _is_devanagari(input_text)
        else classify_aksara_iast(input_text, context)
    )


# --- the compact catalog + line identifier -------------------------------


@dataclass(frozen=True)
class MeterSpec:
    name: str
    syllables: int
    #: G/L per position; final position is anceps and never compared.
    pattern: Optional[str] = None
    #: Caesura: pause after this many syllables. Only set where the tradition
    #: is unambiguous (e.g. śārdūlavikrīḍita's sūryāśvaiḥ = 12 + 7); meters
    #: without a firm single yati carry none — honesty by absence.
    yati: Optional[int] = None


#: The classical sama-vṛtta catalog this compact identifier answers from (plus
#: count-based anuṣṭubh). Patterns are the gaṇa definitions; the pāda-final
#: position is anceps. The full 121-meter catalog lives in catalog.py.
METER_CATALOG: Tuple[MeterSpec, ...] = (
    MeterSpec("indravajrā", 11, "GGLGGLLGLGG"),
    MeterSpec("upendravajrā", 11, "LGLGGLLGLGG"),
    MeterSpec("vaṁśastha", 12, "LGLGGLLGLGLG"),
    # ta-ta-ja-ra (Chandaḥ-kaustubha v.62) — vaṁśastha's pair: they differ
    # only in the first syllable, and the Bhāgavatam freely mixes their pādas
    # (the jagatī upajāti below).
    MeterSpec("indravaṁśā", 12, "GGLGGLLGLGLG"),
    MeterSpec("drutavilambita", 12, "LLLGLLGLLGLG"),
    MeterSpec("vasantatilakā", 14, "GGLGLLLGLLGLGG"),
    MeterSpec("mālinī", 15, "LLLLLLGGGLGGLGG"),
    MeterSpec("śikhariṇī", 17, "LGGGGGLLLLLGGLLLG"),
    MeterSpec("mandākrāntā", 17, "GGGGLLLLLGGLGGLGG"),
    MeterSpec("hariṇī", 17, "LLLLLGGGGLGLLLGLG"),
    MeterSpec("śārdūlavikrīḍita", 19, "GGGLLGLGLLLGGGLGGLG", yati=12),
    MeterSpec("sragdharā", 21, "GGGGLGGLLLLLLGGLGGLGG"),
)


def meter_template(spec: MeterSpec) -> Optional[str]:
    """
    Renders a pattern-defined meter as its glyph template, chunked into gaṇa
    triplets (the tradition's own hummable grouping), with the yati as a
    visible ‖ gap and the chant-legend * on the anceps final. None for
    count-only meters (anuṣṭubh) — no template is honest there.
    """
    if not spec.pattern:
        return None
    glyphs = ["—" if c == "G" else "◡" for c in spec.pattern]
    glyphs[-1] += "*"
    segments = (
        [glyphs[: spec.yati], glyphs[spec.yati:]] if spec.yati else [glyphs]
    )
    rendered = []
    for segment in segments:
        groups = ["".join(segment[i:i + 3]) for i in range(0, len(segment), 3)]
        rendered.append(" ".join(groups))
    return " ‖ ".join(rendered)


def _line_matches(line: Sequence[Aksara], spec: MeterSpec) -> bool:
    if len(line) != spec.syllables:
        return False
    if not spec.pattern:
        return True
    for i in range(len(line) - 1):
        want = "guru" if spec.pattern[i] == "G" else "laghu"
        if line[i].weight != want:
            return False
    return True  # final position anceps


_INVOCATION_NOTE = "opening invocation/address line excluded from the meter"


def _by_name(name: str) -> MeterSpec:
    return next(s for s in METER_CATALOG if s.name == name)


#: Upajāti classes: pādas freely mixing two sibling meters. The canonical
#: triṣṭubh case is indravajrā/upendravajrā; Baladeva Vidyābhūṣaṇa's bhāṣya on
#: Chandaḥ-kaustubha v.42 extends the same prastāra principle to the jagatī
#: pair vaṁśastha(vila)/indravaṁśā — the mix the Bhāgavatam uses constantly.
#: Pure quatrains never reach these (the exact catalog match runs first).
UPAJATI_FAMILIES: Tuple[Tuple[str, Tuple[MeterSpec, ...]], ...] = (
    ("upajāti", (_by_name("indravajrā"), _by_name("upendravajrā"))),
    (
        "upajāti (vaṁśastha–indravaṁśā)",
        (_by_name("vaṁśastha"), _by_name("indravaṁśā")),
    ),
)


def _spec_result(spec: MeterSpec, note: Optional[str]) -> MeterResult:
    return MeterResult(
        label=spec.name,
        identified=True,
        syllables_per_pada=spec.syllables,
        note=note,
        yati=spec.yati,
        template=meter_template(spec),
    )


def identify_meter(lines: Sequence[Sequence[Aksara]]) -> MeterResult:
    """
    Identifies the meter of a verse from its scanned pāda lines.

    Rules: all lines of 8 syllables → anuṣṭubh (by count — the śloka's vipulā
    variants make a fixed signature dishonest); otherwise the LAST FOUR lines
    must agree on one catalog meter (an extra leading line — oṁ invocations,
    vocative addresses — is noted, not force-fitted); otherwise unidentified.
    """
    if not lines:
        return MeterResult(label="unidentified", identified=False)

    if all(len(line) == 8 for line in lines):
        return MeterResult(
            label="anuṣṭubh (śloka)", identified=True, syllables_per_pada=8
        )

    if len(lines) >= 4:
        quatrain = lines[-4:]
        note = _INVOCATION_NOTE if len(lines) > 4 else None
        if all(len(line) == 8 for line in quatrain):
            return MeterResult(
                label="anuṣṭubh (śloka)",
                identified=True,
                syllables_per_pada=8,
                note=note,
            )
        match = next(
            (
                spec
                for spec in METER_CATALOG
                if all(_line_matches(line, spec) for line in quatrain)
            ),
            None,
        )
        if match:
            return _spec_result(match, note)
        family = next(
            (
                f
                for f in UPAJATI_FAMILIES
                if all(
                    any(_line_matches(line, spec) for spec in f[1])
                    for line in quatrain
                )
            ),
            None,
        )
        if family:
            return MeterResult(
                label=family[0],
                identified=True,
                syllables_per_pada=family[1][0].syllables,
                note=note,
            )

    return MeterResult(label="unidentified", identified=False)
