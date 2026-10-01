# -*- coding: utf-8 -*-
"""
Meter taxonomy: where a matched rule sits in the classical/Vedic hierarchy.

Ported from Prasadam's lib/sanskrit-meter-classification.ts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

from .types import (
    SanskritMeterClassification,
    SanskritMeterCountClass,
    SanskritMeterKind,
    SanskritMeterTradition,
)

CLASSICAL_COUNT_CLASSES: Dict[int, str] = {
    1: "uktā",
    2: "atyuktā",
    3: "madhyā",
    4: "pratiṣṭhā",
    5: "supratiṣṭhā",
    6: "gāyatrī",
    7: "uṣṇih",
    8: "anuṣṭubh",
    9: "bṛhatī",
    10: "paṅkti",
    11: "triṣṭubh",
    12: "jagatī",
    13: "atijagatī",
    14: "śakvarī",
    15: "atiśakvarī",
    16: "aṣṭi",
    17: "atyaṣṭi",
    18: "dhṛti",
    19: "atidhṛti",
    20: "kṛti",
    21: "prakṛti",
    22: "ākṛti",
    23: "vikṛti",
    24: "saṅkṛti",
    25: "atikṛti",
    26: "utkṛti",
}

GANA_NAMES: Dict[str, str] = {
    "y": "ya",
    "m": "ma",
    "t": "ta",
    "r": "ra",
    "j": "ja",
    "b": "bha",
    "n": "na",
    "s": "sa",
    "G": "G",
    "L": "L",
}

SYMMETRY_LABELS: Dict[SanskritMeterKind, str] = {
    "sama-vrtta": "sama-vṛtta — all four pādas use one rule",
    "ardhasama-vrtta": "ardhasama-vṛtta — pādas 1/3 and 2/4 pair",
    "visama-vrtta": "viṣama-vṛtta — the four pādas have distinct rules",
    "dandaka": "daṇḍaka",
    "upajati": "upajāti — member rules mix by pāda",
    "sloka": "śloka / vaktra structure",
}


@dataclass
class MeterClassificationInput:
    id: str
    name: str
    kind: SanskritMeterKind
    tradition: SanskritMeterTradition
    pada_lengths: Sequence[int]
    gana_patterns: Optional[Sequence[str]] = None
    yati: Optional[Sequence[int]] = None


_SKIP_SYMBOL = re.compile(r"[\s_·-]")


def _gana_formula(patterns: Optional[Sequence[str]]) -> Optional[str]:
    if not patterns:
        return None
    return " / ".join(
        " · ".join(
            GANA_NAMES.get(symbol, symbol)
            for symbol in pattern
            if not _SKIP_SYMBOL.match(symbol)
        )
        for pattern in patterns
    )


def _common_pada_length(lengths: Sequence[int]) -> Optional[int]:
    if not lengths:
        return None
    first = lengths[0]
    return first if all(length == first for length in lengths) else None


def _vedic_classification(inp: MeterClassificationInput) -> SanskritMeterClassification:
    length = _common_pada_length(inp.pada_lengths)
    return SanskritMeterClassification(
        domain_label="Vedic chandas",
        system="vedic-chandas",
        system_label="Vedic chandas — provisional count/cadence analysis",
        count_class=(
            SanskritMeterCountClass(name=inp.name, syllables_per_pada=length, scope="vedic")
            if length
            else None
        ),
        specific_form=inp.name,
        cautions=(
            "A count match alone is not a Vedic metrical identification; accent, "
            "cadence, resolution, and the textual witness remain necessary.",
        ),
    )


def _matra_classification(inp: MeterClassificationInput) -> SanskritMeterClassification:
    return SanskritMeterClassification(
        domain_label="laukika / classical chandas",
        system="matra-jati",
        system_label="mātrā / jāti — time-unit based",
        specific_form=inp.name,
        cautions=(),
    )


def _yati_statement_for(inp: MeterClassificationInput) -> Optional[str]:
    if inp.id == "indravajra":
        return (
            "No internal yati is prescribed in the audited Indravajrā defining "
            "verses; pause naturally at the pāda boundary."
        )
    if not inp.yati:
        return None
    return (
        f"Recorded internal yati after syllable {' and '.join(str(y) for y in inp.yati)}; "
        "compound-aware validation remains advisory."
    )


def _varna_classification(inp: MeterClassificationInput) -> SanskritMeterClassification:
    length = _common_pada_length(inp.pada_lengths)
    count_name = None if length is None else CLASSICAL_COUNT_CLASSES.get(length)
    count_class = (
        SanskritMeterCountClass(
            name=count_name, syllables_per_pada=length, scope="classical-akshara"
        )
        if count_name and length
        else None
    )
    caution: Tuple[str, ...] = (
        (
            "Triṣṭubh here is the classical eleven-akṣara count class; this does not "
            "by itself identify a Vedic Triṣṭubh verse.",
        )
        if length == 11
        else ()
    )
    return SanskritMeterClassification(
        domain_label="laukika / classical chandas",
        system="varna-vrtta",
        system_label="varṇa-vṛtta — syllable and weight based",
        count_class=count_class,
        symmetry=SYMMETRY_LABELS.get(inp.kind),
        specific_form=inp.name,
        gana_formula=_gana_formula(inp.gana_patterns),
        yati_statement=_yati_statement_for(inp),
        cautions=caution,
    )


def classification_for(inp: MeterClassificationInput) -> SanskritMeterClassification:
    if inp.tradition == "vedic":
        return _vedic_classification(inp)
    if inp.kind in ("jati", "matra-vrtta"):
        return _matra_classification(inp)
    return _varna_classification(inp)
