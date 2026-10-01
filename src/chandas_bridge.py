# -*- coding: utf-8 -*-
"""
chandas_bridge.py — High-precision Sanskrit Chandas Engine for Vāgdhenu TTS.

Bridges VyakaranaBandhu's authentic Sanskrit prosody engine (128+ meters,
Anuṣṭubh/Śloka Pathyā & Vipulā rules, Upajāti families, Jāti, etc.)
with Vāgdhenu's TTS audio synthesis pipeline.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import prep_text as PT

# Relative or absolute package import support
try:
    from .chandas import meter_summary
    from .chandas.catalog import CLASSICAL_VARNA_METERS
    from .chandas.verse_analysis import analyze_sanskrit_verse
except ImportError:
    try:
        from chandas import meter_summary
        from chandas.catalog import CLASSICAL_VARNA_METERS
        from chandas.verse_analysis import analyze_sanskrit_verse
    except ImportError:
        from src.chandas import meter_summary
        from src.chandas.catalog import CLASSICAL_VARNA_METERS
        from src.chandas.verse_analysis import analyze_sanskrit_verse


# Canonical meters having dedicated WAV recordings in vagdhenu reference_bank
BANK_RECORDED_METERS = {
    "anuṣṭubh": "anuṣṭubh",
    "pramāṇikā": "pramāṇikā",
    "indravajrā": "indravajrā",
    "upendravajrā": "upendravajrā",
    "upajāti": "upajāti",
    "rathoddhatā": "rathoddhatā",
    "śālinī": "śālinī",
    "vaṃśastha": "vaṃśastha",
    "indravaṃśā": "indravaṃśā",
    "drutavilambita": "drutavilambita",
    "bhujaṅgaprayāta": "bhujaṅgaprayāta",
    "vasantatilakā": "vasantatilakā",
    "mālinī": "mālinī",
    "śārdūlavikrīḍita": "śārdūlavikrīḍita",
    "sragdharā": "sragdharā",
}

# Normalization map from identified catalog names to bank keys
NAME_TO_BANK = {
    "anuṣṭubh": "anuṣṭubh",
    "anuṣṭubh (śloka)": "anuṣṭubh",
    "anustubh": "anuṣṭubh",
    "śloka": "anuṣṭubh",
    "pramāṇikā": "pramāṇikā",
    "pramanika": "pramāṇikā",
    "pañcacāmara": "pramāṇikā",
    "pancacamara": "pramāṇikā",
    "indravajrā": "indravajrā",
    "indravajra": "indravajrā",
    "upendravajrā": "upendravajrā",
    "upendravajra": "upendravajrā",
    "upajāti": "upajāti",
    "upajati": "upajāti",
    "rathoddhatā": "rathoddhatā",
    "rathoddhata": "rathoddhatā",
    "śālinī": "śālinī",
    "shalini": "śālinī",
    "vaṃśastha": "vaṃśastha",
    "vamshastha": "vaṃśastha",
    "indravaṃśā": "indravaṃśā",
    "indravamsha": "indravaṃśā",
    "drutavilambita": "drutavilambita",
    "bhujaṅgaprayāta": "bhujaṅgaprayāta",
    "bhujangaprayata": "bhujaṅgaprayāta",
    "vasantatilakā": "vasantatilakā",
    "vasantatilaka": "vasantatilakā",
    "mālinī": "mālinī",
    "malini": "mālinī",
    "śārdūlavikrīḍita": "śārdūlavikrīḍita",
    "shardulavikridita": "śārdūlavikrīḍita",
    "sragdharā": "sragdharā",
    "sragdhara": "sragdharā",
}

# Surrogate fallback mapping for meters recognized by VyakaranaBandhu
# but not having a dedicated WAV recording in reference_bank.
# Mapped based on syllable count, tempo, and gaṇa cadence.
METER_SURROGATES = {
    # 8 syllables / pada
    "vidyunmālā": "anuṣṭubh",
    "māṇavakākrīḍā": "anuṣṭubh",
    "samānī": "pramāṇikā",
    "pañcacāmara": "pramāṇikā",
    # 11 syllables / pada (Triṣṭubh class)
    "dodhaka": "upajāti",
    "svāgatā": "rathoddhatā",
    "vātormī": "śālinī",
    "bhadrikā": "upajāti",
    "mottanaka": "upajāti",
    # 12 syllables / pada (Jagatī class)
    "toṭaka": "bhujaṅgaprayāta",
    "candravartma": "drutavilambita",
    "jaloddhatagati": "vaṃśastha",
    "tāmarasa": "vaṃśastha",
    "vaiśvadevī": "indravaṃśā",
    "pramitākṣarā": "drutavilambita",
    # 13 syllables / pada
    "praharṣiṇī": "vasantatilakā",
    "rucirā": "vasantatilakā",
    "mattamayūra": "vasantatilakā",
    # 14 syllables / pada
    "aparājitā": "vasantatilakā",
    "praharaṇakalitā": "vasantatilakā",
    # 15 syllables / pada
    "śaśikalā": "mālinī",
    "maṇiguṇanikara": "mālinī",
    # 17 syllables / pada (Atyaṣṭi class)
    "śikhariṇī": "mālinī",
    "mandākrāntā": "vasantatilakā",
    "hariṇī": "mālinī",
    "pṛthvī": "vasantatilakā",
    "narkuṭaka": "mālinī",
    # 19 syllables / pada
    "meghavipruṣitā": "śārdūlavikrīḍita",
    # 21+ syllables / pada
    "suvadanā": "sragdharā",
    "aśvalalita": "sragdharā",
}

DEFAULT_FALLBACK = "vasantatilakā"

# Pre-sort sama-vṛtta meters by pattern length descending
_SORTED_VARNA_METERS = sorted(
    [m for m in CLASSICAL_VARNA_METERS if m.kind == "sama-vrtta"],
    key=lambda m: max(len(p) for p in m.pada_patterns),
    reverse=True,
)


def _clean_deva_for_scansion(text: str) -> str:
    """Normalize and clean text for scansion without losing danda structure."""
    d = PT.to_deva(text)
    # Map Vedic/regional retroflex ळ to regular ल for prosodic scansion
    d = d.replace("ळ", "ल")
    # Strip western / devanagari digits, quotes, parentheses
    d = re.sub(r'[\d\u0966-\u096F"\'“”‘’()[\]{}<>]', '', d)
    # Normalize spaces around dandas
    d = re.sub(r'\s*([।॥|])\s*', r' \1 ', d)
    return d.strip()


def _match_exact_sama_varna(pattern: str, terminal_licence: bool = True) -> Optional[Tuple[str, int]]:
    """
    Match scanned L/G pattern against classical sama-vṛttas for 1, 2, 3, or 4 padas.
    Checks longer meters first (21 down to 8) to avoid substring collisions.
    Returns (meter_name, pada_length) or None.
    """
    n = len(pattern)
    if n == 0:
        return None
    for m in _SORTED_VARNA_METERS:
        for p in m.pada_patterns:
            plen = len(p)
            if plen > 0 and n in (plen, 2 * plen, 3 * plen, 4 * plen):
                num_p = n // plen
                match = True
                for i in range(num_p):
                    sub = pattern[i * plen : (i + 1) * plen]
                    if terminal_licence:
                        if sub[:-1] != p[:-1]:
                            match = False
                            break
                    else:
                        if sub != p:
                            match = False
                            break
                if match:
                    return (m.name, plen)
    return None


def analyze_verse_meter(text: str) -> Dict[str, Any]:
    """
    Run deep meter identification on the input text.
    Handles 4-pāda verses, 2-pāda hemistichs, and single pādas.
    """
    if not text or not text.strip():
        return {
            "identified": False,
            "name": "",
            "bank_key": DEFAULT_FALLBACK,
            "is_surrogate": True,
            "kind": "unknown",
            "subtypes": [],
            "padas": [],
            "syllables_per_pada": None,
            "total_syllables": 0,
            "raw_summary": {},
        }

    clean_deva = _clean_deva_for_scansion(text)
    
    # 1. First run scansion
    meter_name: Optional[str] = None
    kind = "unknown"
    subtypes: List[str] = []
    summary: Dict[str, Any] = {}
    syl_count: Optional[int] = None
    total_syl = 0

    analysis = None
    try:
        analysis = analyze_sanskrit_verse(clean_deva)
        if analysis and analysis.syllables:
            total_syl = len(analysis.syllables)
            pat = ''.join('G' if s.weight == 'guru' else 'L' for s in analysis.syllables)
            varna_res = _match_exact_sama_varna(pat)
            if varna_res:
                meter_name, syl_count = varna_res
                kind = "sama-vrtta"
    except Exception:
        pass

    # 2. If not matched by exact sama-varna, run full meter_summary
    # (handles Śloka/Anuṣṭubh Pathyā/Vipulā, Jāti, Upajāti, Vedic)
    if not meter_name:
        try:
            summary = meter_summary(clean_deva)
            if summary.get("name"):
                meter_name = summary.get("name")
                kind = summary.get("kind", "unknown")
                subtypes = summary.get("subtypes") or []
                syl_count = (summary.get("count_class") or {}).get("syllables_per_pada")
                total_syl = (summary.get("totals") or {}).get("syllables", total_syl)
        except Exception:
            pass

    # 3. If still unverified and syllables suggest a hemistich (e.g. 16, 22, 24, 28, 30, 38, 42),
    # try hemistich doubling
    if not meter_name:
        try:
            doubled_text = clean_deva.rstrip(' ।॥|') + ' । ' + clean_deva.lstrip(' ।॥|') + ' ॥'
            doubled_summary = meter_summary(doubled_text)
            d_name = doubled_summary.get("name")
            if d_name and d_name != "vegavatī":
                meter_name = d_name
                kind = doubled_summary.get("kind", kind)
                subtypes = doubled_summary.get("subtypes") or subtypes
                summary = doubled_summary
                syl_count = (doubled_summary.get("count_class") or {}).get("syllables_per_pada")
        except Exception:
            pass

    # 4. If still unverified on mixed verses, test the first hemistich
    if not meter_name and analysis and len(analysis.padas) >= 2:
        try:
            p0_pat = ''.join('G' if s.weight == 'guru' else 'L' for s in analysis.padas[0].syllables)
            varna_p0 = _match_exact_sama_varna(p0_pat)
            if varna_p0:
                meter_name, syl_count = varna_p0
                kind = "sama-vrtta"
            else:
                first_hemi = analysis.padas[0].source
                hemi_summary = meter_summary(first_hemi)
                if hemi_summary.get("name"):
                    meter_name = hemi_summary.get("name")
                    kind = hemi_summary.get("kind", kind)
                    subtypes = hemi_summary.get("subtypes") or subtypes
                    summary = hemi_summary
        except Exception:
            pass

    identified = bool(meter_name)
    bank_key = None
    is_surrogate = False

    if identified and meter_name:
        norm_name = meter_name.lower().strip()
        # Handle Upajāti family routing
        if norm_name.startswith("upajāti") or norm_name.startswith("upajati"):
            # Check 12-syllable Upajāti vs 11-syllable Upajāti
            if any(term in norm_name for term in ("vaṃśastha", "vamsastha", "indravaṃśā", "indravamsha")) or syl_count == 12:
                bank_key = "vaṃśastha"
            else:
                bank_key = "upajāti"
        elif norm_name in NAME_TO_BANK:
            bank_key = NAME_TO_BANK[norm_name]
        elif norm_name in METER_SURROGATES:
            bank_key = METER_SURROGATES[norm_name]
            is_surrogate = True
        else:
            for k, bk in NAME_TO_BANK.items():
                if k in norm_name:
                    bank_key = bk
                    break
            if not bank_key:
                for k, bk in METER_SURROGATES.items():
                    if k in norm_name:
                        bank_key = bk
                        is_surrogate = True
                        break

    # Syllable-count based surrogate if still unassigned
    if not bank_key and syl_count:
        if syl_count == 8:
            bank_key = "anuṣṭubh"
        elif syl_count == 11:
            bank_key = "upajāti"
        elif syl_count == 12:
            bank_key = "vaṃśastha"
        elif syl_count == 14:
            bank_key = "vasantatilakā"
        elif syl_count == 15:
            bank_key = "mālinī"
        elif syl_count == 17:
            bank_key = "vasantatilakā"
            is_surrogate = True
        elif syl_count == 19:
            bank_key = "śārdūlavikrīḍita"
        elif syl_count == 21:
            bank_key = "sragdharā"

    if not bank_key:
        bank_key = DEFAULT_FALLBACK
        is_surrogate = True

    # Pāda text extraction
    extracted_padas = []
    if summary and summary.get("padas"):
        for p in summary["padas"]:
            deva_pada = p.get("deva")
            if deva_pada:
                extracted_padas.append(deva_pada.strip())
    elif analysis and syl_count and len(analysis.syllables) >= syl_count:
        syls = analysis.syllables
        n_padas = len(syls) // syl_count
        for i in range(n_padas):
            p_syls = syls[i * syl_count : (i + 1) * syl_count]
            start = p_syls[0].span.start
            end = p_syls[-1].span.end
            extracted_padas.append(clean_deva[start:end].strip())

    return {
        "identified": identified,
        "name": meter_name or ("anuṣṭubh" if bank_key == "anuṣṭubh" else ""),
        "bank_key": bank_key,
        "is_surrogate": is_surrogate,
        "kind": kind,
        "subtypes": subtypes,
        "padas": extracted_padas,
        "syllables_per_pada": syl_count,
        "total_syllables": total_syl,
        "raw_summary": summary,
    }


def smart_split_padas(text: str) -> List[str]:
    """
    Intelligently segment a Sanskrit verse into natural chant units (hemistichs / pādas).
    
    Architectural Philosophy: Prosody-First with Hybrid Punctuation Alignment
    1. Runs phonemic scansion and meter identification FIRST to understand the verse's
       classical metric structure (e.g. 8-syl Anuṣṭubh, 11-syl Upajāti, 14-syl Vasantatilakā,
       19-syl Śārdūlavikrīḍita).
    2. Maps to optimal chant units matching Vāgdhenu's reference bank cadences:
       - 8-syllable meters (Anuṣṭubh): 16-syllable hemistichs (2 per 32-syl shloka)
       - 11/12/14-syllable meters: 22/24/28-syllable hemistichs (or single pādas if half-verse)
       - 15/17/19/21-syllable meters: 15/17/19/21-syllable pādas
    3. Hybrid Punctuation Alignment:
       - If user punctuation (daṇḍas/newlines) already cleanly divides the verse into the
         expected number of chant units, respects the user's explicit boundaries.
       - If user pasted 4 lines for an Anuṣṭubh or Upajāti shloka, automatically groups
         them into 2 hemistichs (Pādas 1+2, Pādas 3+4) to prevent awkward 4-pause staccato chanting.
       - If user text is continuous, unpunctuated, or has broken formatting, cleanly segments
         at exact metric akṣara code-point spans.
    4. Falls back gracefully to standard daṇḍa/line splitting if meter is completely unknown (prose).
    """
    if not text or not text.strip():
        return []

    clean = text.strip()
    clean_deva = _clean_deva_for_scansion(clean)

    # 1. Scansion and meter identification
    m_info = analyze_verse_meter(clean)
    syl_count = m_info.get("syllables_per_pada")

    analysis = None
    try:
        analysis = analyze_sanskrit_verse(clean_deva)
    except Exception:
        pass

    syls = analysis.syllables if (analysis and analysis.syllables) else []
    total = len(syls)

    # Collect any explicit pieces present in input
    explicit_pieces = []
    for line in text.replace("॥", "।").replace("|", "।").splitlines():
        for seg in line.split("।"):
            seg = seg.strip()
            if seg:
                explicit_pieces.append(seg)

    # 2. If scansion succeeded and we have a recognizable metric shape
    if total >= 8:
        seg_syl = None
        if syl_count == 8:
            # Anuṣṭubh: 16 syllables (hemistich = 2 padas) for standard 32-syl shlokas
            seg_syl = 16 if total >= 24 else 8
        elif syl_count in (11, 12, 14):
            # 4-pāda Triṣṭubh / Jagatī / Śakvarī: group into 2 hemistichs (2 * syl_count)
            if total >= syl_count * 3:
                seg_syl = syl_count * 2
            else:
                seg_syl = syl_count
        elif syl_count == 15:
            # Mālinī: 15 syllables per pada (or 30 if full 60-syllable verse)
            if total in (29, 30, 31):
                seg_syl = 15
            elif total in (59, 60, 61):
                seg_syl = 30
            else:
                seg_syl = 15
        elif syl_count in (17, 19, 21):
            # Long classical meters: single pāda per chant unit
            seg_syl = syl_count
        elif total in (31, 32, 33):
            seg_syl = 16
        elif total in (43, 44, 45):
            seg_syl = 22
        elif total in (47, 48, 49):
            seg_syl = 24
        elif total in (55, 56, 57):
            seg_syl = 28

        if seg_syl and total >= seg_syl * 1.4:
            expected_n_pieces = round(total / seg_syl)

            # If user already formatted into the exact expected number of chant units
            if len(explicit_pieces) == expected_n_pieces:
                return explicit_pieces

            # If user pasted 4 lines for a 2-hemistich meter (e.g. Anuṣṭubh or Upajāti), pair them!
            if len(explicit_pieces) == 4 and expected_n_pieces == 2:
                return [
                    explicit_pieces[0] + " " + explicit_pieces[1],
                    explicit_pieces[2] + " " + explicit_pieces[3]
                ]

            # Otherwise (continuous unpunctuated text or mismatched linebreaks), segment by akṣara spans
            pieces = []
            n_segs = total // seg_syl
            for i in range(n_segs):
                sub = syls[i * seg_syl : (i + 1) * seg_syl]
                st = sub[0].span.start
                en = sub[-1].span.end
                pieces.append(clean_deva[st:en].strip())
            rem = syls[n_segs * seg_syl :]
            if rem:
                pieces.append(clean_deva[rem[0].span.start : rem[-1].span.end].strip())

            if len(pieces) >= 2:
                return pieces

    # 3. Fallback for unscannable / prose text
    return explicit_pieces or ([text.strip()] if text.strip() else [])


def detect_meter_key(text: str) -> str:
    """
    Drop-in replacement for Vāgdhenu's detect_meter_key(text).
    Returns the resolved bank key (e.g. 'anuṣṭubh', 'śālinī', 'vasantatilakā')
    or empty string '' if unrecognized, allowing caller to handle fallback.
    """
    res = analyze_verse_meter(text)
    if res["identified"]:
        return res["bank_key"]
    return ""
