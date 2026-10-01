# -*- coding: utf-8 -*-
"""
Shared meter-identification value types.

Ported from Prasadam's lib/sanskrit-meter-types.ts. TypeScript's "absent
optional property" is represented as ``None`` throughout; ``to_dict`` drops
None-valued keys so the JSON the API emits has the same shape the TypeScript
engine produces.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Dict, List, Optional, Tuple

# --- string enums (kept as plain strings, exactly as the TS unions are) ---

SanskritMeterStatus = str
# "identified" | "provisional" | "ambiguous" | "unidentified"
# | "insufficient-evidence" | "invalid-analysis"

SanskritMeterKind = str
# "sama-vrtta" | "ardhasama-vrtta" | "visama-vrtta" | "dandaka" | "upajati"
# | "sloka" | "jati" | "matra-vrtta" | "vedic"

SanskritMeterTradition = str          # "classical" | "vedic"
SanskritMeterMatchType = str          # "exact" | "class-compatible" | "near" | "partial"
SanskritMeterAuthorityTradition = str  # "general-chandas" | "gaudiya" | "vedic"
SanskritMeterAuthorityCoverage = str
# "dual-root-bhasya" | "single-root-bhasya" | "catalog-only" | "secondary-only"


def to_dict(value: Any) -> Any:
    """
    Recursively converts dataclasses to dicts, dropping keys whose value is
    None so an absent optional renders as an absent key (TypeScript parity).
    Tuples become lists so the result is JSON-serializable.
    """
    if is_dataclass(value) and not isinstance(value, type):
        out: Dict[str, Any] = {}
        for f in fields(value):
            item = getattr(value, f.name)
            if item is None:
                continue
            out[f.name] = to_dict(item)
        return out
    if isinstance(value, (list, tuple)):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {k: to_dict(v) for k, v in value.items()}
    return value


@dataclass(frozen=True)
class SanskritMeterSource:
    work: str
    locator: str
    url: Optional[str] = None
    note: Optional[str] = None


@dataclass(frozen=True)
class SanskritMeterAuthorityCitation:
    role: str  # "root" | "bhasya"
    author: str
    work: str
    locator: str
    #: A short source-language formula, not a modern interpretive expansion.
    statement: str
    supports: Tuple[str, ...]
    url: Optional[str] = None
    statement_language: Optional[str] = None  # "sa-Latn" | "en"


@dataclass(frozen=True)
class SanskritMeterAuthorityPair:
    id: str
    tradition: SanskritMeterAuthorityTradition
    label: str
    root: SanskritMeterAuthorityCitation
    bhasya: SanskritMeterAuthorityCitation
    note: Optional[str] = None


@dataclass(frozen=True)
class SanskritMeterAuthorityEvidence:
    coverage: SanskritMeterAuthorityCoverage
    pairs: Tuple[SanskritMeterAuthorityPair, ...]
    note: str


@dataclass(frozen=True)
class SanskritMeterCountClass:
    name: str
    syllables_per_pada: int
    scope: str  # "classical-akshara" | "vedic"


@dataclass(frozen=True)
class SanskritMeterClassification:
    domain_label: str
    system: str  # "varna-vrtta" | "matra-jati" | "vedic-chandas"
    system_label: str
    specific_form: str
    cautions: Tuple[str, ...]
    count_class: Optional[SanskritMeterCountClass] = None
    symmetry: Optional[str] = None
    #: Traditional gaṇa expression, retained alongside the expanded G/L rule.
    gana_formula: Optional[str] = None
    yati_statement: Optional[str] = None


@dataclass(frozen=True)
class SanskritMeterMismatch:
    pada_index: int
    position: int
    expected: str  # "G" | "L"
    observed: str  # "G" | "L"
    #: Zero-based index in the analyzer's flattened syllable array.
    syllable_index: int


@dataclass
class SanskritMeterPadaEvidence:
    pada_index: int
    source_unit_index: int
    syllable_start: int
    syllable_end: int
    observed_pattern: str
    mismatches: List[SanskritMeterMismatch]
    final_anceps_used: bool
    expected_pattern: Optional[str] = None
    member_name: Optional[str] = None


@dataclass
class SanskritMeterCandidate:
    id: str
    name: str
    aliases: Tuple[str, ...]
    kind: SanskritMeterKind
    tradition: SanskritMeterTradition
    match_type: SanskritMeterMatchType
    #: Deterministic edit cost. Zero means the stated rule matched.
    distance: int
    #: Number of inferred pāda boundaries inserted inside supplied units.
    boundary_transformations: int
    evidence: str  # "full-verse" | "extended-stanza" | "count-only" | "fragment"
    padas: List[SanskritMeterPadaEvidence]
    source: SanskritMeterSource
    notes: Tuple[str, ...]
    classification: Optional[SanskritMeterClassification] = None
    authority: Optional[SanskritMeterAuthorityEvidence] = None
    terminal_policy: Optional[str] = None
    template: Optional[str] = None
    yati: Optional[Tuple[int, ...]] = None
    subtypes: Optional[Tuple[str, ...]] = None


@dataclass(frozen=True)
class SanskritMeterVerificationIssue:
    code: str
    message: str
    candidate_id: Optional[str] = None
    pada_index: Optional[int] = None
    position: Optional[int] = None


@dataclass
class SanskritMeterVerification:
    status: str  # "verified" | "failed" | "not-run"
    checks: int
    method: str
    issues: List[SanskritMeterVerificationIssue]


@dataclass
class SanskritMeterIdentification:
    requested_tradition: str  # "auto" | "classical" | "vedic"
    status: SanskritMeterStatus
    identified: bool
    candidates: List[SanskritMeterCandidate]
    observed_unit_patterns: List[str]
    diagnostics: List[str]
    verification: SanskritMeterVerification
    catalog_size: int
    primary: Optional[SanskritMeterCandidate] = None
