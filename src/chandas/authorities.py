# -*- coding: utf-8 -*-
"""
Root (mūla) + commentary (bhāṣya) citation registry for meter rules.

Ported from Prasadam's lib/sanskrit-meter-authorities.ts. Only the rules whose
root and bhāṣya have BOTH been separately keyed in appear here; everything
else is honestly reported as catalog-only, which keeps it out of the
"identified" verdict tier.
"""

from __future__ import annotations

from typing import Dict, Tuple

from .types import (
    SanskritMeterAuthorityCitation,
    SanskritMeterAuthorityEvidence,
    SanskritMeterAuthorityPair,
    SanskritMeterSource,
    SanskritMeterTradition,
)

PINGALA_URL = (
    "https://sa.wikisource.org/wiki/"
    "%E0%A4%9B%E0%A4%A8%E0%A5%8D%E0%A4%A6%E0%A4%83%E0%A4%B6%E0%A4%BE"
    "%E0%A4%B8%E0%A5%8D%E0%A4%A4%E0%A5%8D%E0%A4%B0%E0%A4%AE%E0%A5%8D"
)
CK_URL = "https://vidyabhusanaproject.blogspot.com/2013/06/chandah-kaustubha-release.html"


INDRAVAJRA_PAIRS: Tuple[SanskritMeterAuthorityPair, ...] = (
    SanskritMeterAuthorityPair(
        id="pingala-halayudha-indravajra",
        tradition="general-chandas",
        label="Piṅgala root + Halāyudha bhāṣya",
        root=SanskritMeterAuthorityCitation(
            role="root",
            author="Piṅgala",
            work="Chandaḥsūtra / Chandaḥśāstra",
            locator="6.15",
            url=PINGALA_URL,
            statement="indravajrā tau jagau g",
            supports=("name", "ta-ta-ja-G-G pattern"),
        ),
        bhasya=SanskritMeterAuthorityCitation(
            role="bhasya",
            author="Halāyudha",
            work="Mṛtasañjīvanī",
            locator="on Chandaḥsūtra 6.15",
            url=PINGALA_URL,
            statement="two ta-gaṇas, one ja-gaṇa, and two gurus in each pāda",
            statement_language="en",
            supports=("expanded pattern", "Indravajrā identification"),
        ),
        note=(
            "This is the general classical witness, not a Vedic verdict. "
            "Halāyudha's discussion of 1.10 does not grant unrestricted "
            "final-weight choice."
        ),
    ),
    SanskritMeterAuthorityPair(
        id="chandah-kaustubha-baladeva-indravajra",
        tradition="gaudiya",
        label="Gauḍīya root + Baladeva bhāṣya",
        root=SanskritMeterAuthorityCitation(
            role="root",
            author="Rādhā-Dāmodara Gosvāmī",
            work="Chandaḥ-kaustubha",
            locator="Second Ray, v. 40",
            url=CK_URL,
            statement="ekādaśākṣarā triṣṭup … syād indravajrā yadi tau jagau gaḥ",
            supports=("11-akṣara triṣṭubh class", "name", "ta-ta-ja-G-G pattern"),
        ),
        bhasya=SanskritMeterAuthorityCitation(
            role="bhasya",
            author="Baladeva Vidyābhūṣaṇa",
            work="Chandaḥ-kaustubha-bhāṣya",
            locator="on Second Ray, v. 40",
            url=CK_URL,
            statement="tagaṇa-dvayaṃ jagaṇo guru-dvayaṃ ca",
            supports=("two ta-gaṇas", "one ja-gaṇa", "two final gurus"),
        ),
        note=(
            "The pair separately defines sama-vṛtta at First Ray 23–24; CK 1.19 "
            "with Baladeva permits both directions of final-weight adjustment by "
            "intention."
        ),
    ),
)

UPENDRAVAJRA_PAIRS: Tuple[SanskritMeterAuthorityPair, ...] = (
    SanskritMeterAuthorityPair(
        id="pingala-halayudha-upendravajra",
        tradition="general-chandas",
        label="Piṅgala root + Halāyudha bhāṣya",
        root=SanskritMeterAuthorityCitation(
            role="root",
            author="Piṅgala",
            work="Chandaḥsūtra / Chandaḥśāstra",
            locator="6.16",
            url=PINGALA_URL,
            statement="upendravajrā jatau jagau g",
            supports=("name", "ja-ta-ja-G-G pattern"),
        ),
        bhasya=SanskritMeterAuthorityCitation(
            role="bhasya",
            author="Halāyudha",
            work="Mṛtasañjīvanī",
            locator="on Chandaḥsūtra 6.16",
            url=PINGALA_URL,
            statement="the first ta-gaṇa of Indravajrā is replaced by ja-gaṇa",
            statement_language="en",
            supports=("ja-ta-ja-G-G pattern",),
        ),
        note=(
            "The normalized root formula is recoverable from the printed sūtra "
            "index; the corresponding body leaf is missing or OCR-garbled in the "
            "searchable HTML witness."
        ),
    ),
    SanskritMeterAuthorityPair(
        id="chandah-kaustubha-baladeva-upendravajra",
        tradition="gaudiya",
        label="Gauḍīya root + Baladeva bhāṣya",
        root=SanskritMeterAuthorityCitation(
            role="root",
            author="Rādhā-Dāmodara Gosvāmī",
            work="Chandaḥ-kaustubha",
            locator="Second Ray, v. 41",
            url=CK_URL,
            statement="upendravajrā jata-jās tato gau",
            supports=("name", "ja-ta-ja-G-G pattern"),
        ),
        bhasya=SanskritMeterAuthorityCitation(
            role="bhasya",
            author="Baladeva Vidyābhūṣaṇa",
            work="Chandaḥ-kaustubha-bhāṣya",
            locator="on Second Ray, v. 41",
            url=CK_URL,
            statement="ja-gaṇa, ta-gaṇa, ja-gaṇa, and two gurus",
            statement_language="en",
            supports=("expanded pattern", "Upendravajrā identification"),
        ),
    ),
)

UPAJATI_PAIRS: Tuple[SanskritMeterAuthorityPair, ...] = (
    SanskritMeterAuthorityPair(
        id="pingala-halayudha-upajati",
        tradition="general-chandas",
        label="Piṅgala root + Halāyudha bhāṣya",
        root=SanskritMeterAuthorityCitation(
            role="root",
            author="Piṅgala",
            work="Chandaḥsūtra / Chandaḥśāstra",
            locator="6.17",
            url=PINGALA_URL,
            statement="ādyantāv upajātayaḥ",
            supports=("mixed Indravajrā–Upendravajrā family",),
        ),
        bhasya=SanskritMeterAuthorityCitation(
            role="bhasya",
            author="Halāyudha",
            work="Mṛtasañjīvanī",
            locator="on Chandaḥsūtra 6.17",
            url=PINGALA_URL,
            statement="mixing the two member pādas yields fourteen prastāra forms",
            statement_language="en",
            supports=("mixed membership", "fourteen non-pure forms"),
        ),
    ),
    SanskritMeterAuthorityPair(
        id="chandah-kaustubha-baladeva-upajati",
        tradition="gaudiya",
        label="Gauḍīya root + Baladeva bhāṣya",
        root=SanskritMeterAuthorityCitation(
            role="root",
            author="Rādhā-Dāmodara Gosvāmī",
            work="Chandaḥ-kaustubha",
            locator="Second Ray, v. 42",
            url=CK_URL,
            statement="anantarodīrita-lakṣma-bhājau pādau yadīyāv upajātayas tāḥ",
            supports=("mixed member-pāda definition",),
        ),
        bhasya=SanskritMeterAuthorityCitation(
            role="bhasya",
            author="Baladeva Vidyābhūṣaṇa",
            work="Chandaḥ-kaustubha-bhāṣya",
            locator="on Second Ray, v. 42",
            url=CK_URL,
            statement="Indravajrā and Upendravajrā pādas combine as fourteen upajātis",
            statement_language="en",
            supports=("mixed membership", "exclusion of the two pure endpoints"),
        ),
    ),
)

_PAIRED_BY_ID: Dict[str, Tuple[SanskritMeterAuthorityPair, ...]] = {
    "indravajra": INDRAVAJRA_PAIRS,
    "upendravajra": UPENDRAVAJRA_PAIRS,
    "upajati-tristubh": UPAJATI_PAIRS,
}


def authority_evidence_for(
    meter_id: str, tradition: SanskritMeterTradition, source: SanskritMeterSource
) -> SanskritMeterAuthorityEvidence:
    pairs = _PAIRED_BY_ID.get(meter_id)
    if pairs:
        return SanskritMeterAuthorityEvidence(
            coverage="dual-root-bhasya",
            pairs=pairs,
            note=(
                "The rule is independently paired in the general Piṅgala–Halāyudha "
                "and Gauḍīya Chandaḥ-kaustubha–Baladeva traditions."
            ),
        )
    if tradition == "vedic":
        return SanskritMeterAuthorityEvidence(
            coverage="secondary-only",
            pairs=(),
            note=(
                "Only a modern count-class control is attached here. A Vedic root, "
                "traditional commentary, accent, cadence, and edition-aware witness "
                "are still required for a full verdict."
            ),
        )
    return SanskritMeterAuthorityEvidence(
        coverage="catalog-only",
        pairs=(),
        note=(
            f"The computational rule is traceable to {source.work}, but its root and "
            "bhāṣya have not yet both been separately keyed into the authority registry."
        ),
    )
