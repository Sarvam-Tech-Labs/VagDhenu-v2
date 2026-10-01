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

    identified = bool(meter_name)
    bank_key = None
    is_surrogate = False

    if identified and meter_name:
        norm_name = meter_name.lower().strip()
        if norm_name.startswith("upajāti") or norm_name.startswith("upajati"):
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
        # Slice by syllable count if summary had no padas
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
