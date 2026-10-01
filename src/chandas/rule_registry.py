# -*- coding: utf-8 -*-
"""
Non-catalog rule families: upajāti pairs, the śloka rule, the āryā/gīti jāti
family, and the Vedic count classes — each with its cited source.

Ported from Prasadam's lib/sanskrit-meter-rule-registry.ts.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Tuple

from .types import SanskritMeterSource

SanskritAryaHalfKind = str  # "first" | "second" | "aryagiti"


@dataclass(frozen=True)
class SanskritUpajatiRuleSpec:
    id: str
    name: str
    member_ids: Tuple[str, str]
    source: SanskritMeterSource


@dataclass(frozen=True)
class SanskritJatiRuleSpec:
    id: str
    name: str
    quarter_matras: Tuple[int, int, int, int]
    half_kinds: Tuple[SanskritAryaHalfKind, SanskritAryaHalfKind]
    source: SanskritMeterSource


@dataclass(frozen=True)
class SanskritVedicRuleSpec:
    id: str
    name: str
    pada_lengths: Tuple[int, ...]
    source: SanskritMeterSource


VR_SOURCE = SanskritMeterSource(
    work="Kedārabhaṭṭa, Vṛttaratnākara",
    locator="chapters 2–5",
    url="https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/5_poetry/1_chandas/kedvratu.htm",
)

CK_SOURCE = SanskritMeterSource(
    work=(
        "Rādhā-Dāmodara Gosvāmī, Chandaḥ-kaustubha, with Baladeva Vidyābhūṣaṇa's bhāṣya"
    ),
    locator="Rays 2–7",
    url="https://vidyabhusanaproject.blogspot.com/2013/06/chandah-kaustubha-release.html",
)

VEDIC_SOURCE = SanskritMeterSource(
    work="E. V. Arnold, Vedic Metre in its Historical Development",
    locator="§§19–38 (count classes and cadence cautions)",
    url="https://archive.org/details/vedicmetreinitsh00arnouoft",
    note=(
        "Vedic identification is count-compatible only; restoration and cadence "
        "require a Vedic witness."
    ),
)


@dataclass(frozen=True)
class SlokaRule:
    id: str
    name: str
    aliases: Tuple[str, ...]
    source: SanskritMeterSource


SLOKA_RULE = SlokaRule(
    id="anustubh-sloka",
    name="anuṣṭubh (śloka)",
    aliases=("vaktra",),
    source=replace(VR_SOURCE, locator="2.21–30 (vaktra, pathyā, and vipulā rules)"),
)

UPAJATI_FAMILIES: Tuple[SanskritUpajatiRuleSpec, ...] = (
    SanskritUpajatiRuleSpec(
        id="upajati-tristubh",
        name="upajāti (indravajrā–upendravajrā)",
        member_ids=("indravajra", "upendravajra"),
        source=replace(VR_SOURCE, locator="3.28–31"),
    ),
    SanskritUpajatiRuleSpec(
        id="upajati-jagati",
        name="upajāti (vaṃśastha–indravaṃśā)",
        member_ids=("vamsastha", "indravamsa"),
        source=replace(
            CK_SOURCE,
            locator="Second Ray, vv. 61–62; mixed-pāda principle in the bhāṣya",
        ),
    ),
)

_JATI_SOURCE = replace(VR_SOURCE, locator="2.1–11 (āryā and gīti families)")

JATI_SPECS: Tuple[SanskritJatiRuleSpec, ...] = (
    SanskritJatiRuleSpec(
        id="arya",
        name="āryā",
        quarter_matras=(12, 18, 12, 15),
        half_kinds=("first", "second"),
        source=_JATI_SOURCE,
    ),
    SanskritJatiRuleSpec(
        id="giti",
        name="gīti",
        quarter_matras=(12, 18, 12, 18),
        half_kinds=("first", "first"),
        source=_JATI_SOURCE,
    ),
    SanskritJatiRuleSpec(
        id="upagiti",
        name="upagīti",
        quarter_matras=(12, 15, 12, 15),
        half_kinds=("second", "second"),
        source=_JATI_SOURCE,
    ),
    SanskritJatiRuleSpec(
        id="udgiti",
        name="udgīti",
        quarter_matras=(12, 15, 12, 18),
        half_kinds=("second", "first"),
        source=_JATI_SOURCE,
    ),
    SanskritJatiRuleSpec(
        id="aryagiti",
        name="āryāgīti",
        quarter_matras=(12, 20, 12, 20),
        half_kinds=("aryagiti", "aryagiti"),
        source=_JATI_SOURCE,
    ),
)

VEDIC_SPECS: Tuple[SanskritVedicRuleSpec, ...] = (
    SanskritVedicRuleSpec("vedic-gayatri", "gāyatrī", (8, 8, 8), VEDIC_SOURCE),
    SanskritVedicRuleSpec("vedic-usnih", "uṣṇih", (8, 8, 12), VEDIC_SOURCE),
    SanskritVedicRuleSpec("vedic-anustubh", "Vedic anuṣṭubh", (8, 8, 8, 8), VEDIC_SOURCE),
    SanskritVedicRuleSpec("vedic-brhati", "bṛhatī", (8, 8, 12, 8), VEDIC_SOURCE),
    SanskritVedicRuleSpec("vedic-pankti", "paṅkti", (8, 8, 8, 8, 8), VEDIC_SOURCE),
    SanskritVedicRuleSpec("vedic-tristubh", "Vedic triṣṭubh", (11, 11, 11, 11), VEDIC_SOURCE),
    SanskritVedicRuleSpec("vedic-jagati", "Vedic jagatī", (12, 12, 12, 12), VEDIC_SOURCE),
)

UPAJATI_BY_ID: Dict[str, SanskritUpajatiRuleSpec] = {
    spec.id: spec for spec in UPAJATI_FAMILIES
}
JATI_BY_ID: Dict[str, SanskritJatiRuleSpec] = {spec.id: spec for spec in JATI_SPECS}
VEDIC_BY_ID: Dict[str, SanskritVedicRuleSpec] = {spec.id: spec for spec in VEDIC_SPECS}
