# -*- coding: utf-8 -*-
"""
Meter identification over a verified syllable analysis.

Ported from Prasadam's lib/sanskrit-meter-identification.ts.

Exact varṇa matches are tried before rule-based śloka/jāti and count-based
Vedic families. Near matches are suggestions only and can never become a
verdict.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .authorities import authority_evidence_for
from .catalog import (
    CLASSICAL_VARNA_METERS,
    ChandasSourceRef,
    ClassicalVarnaMeterSpec,
)
from .classification import MeterClassificationInput, classification_for
from .rule_registry import (
    CK_SOURCE,
    JATI_SPECS,
    SLOKA_RULE,
    UPAJATI_FAMILIES,
    VEDIC_SPECS,
    VR_SOURCE,
    SanskritJatiRuleSpec,
    SanskritUpajatiRuleSpec,
    SanskritVedicRuleSpec,
)
from .types import (
    SanskritMeterCandidate,
    SanskritMeterIdentification,
    SanskritMeterMismatch,
    SanskritMeterPadaEvidence,
    SanskritMeterSource,
    SanskritMeterVerification,
)

NOT_RUN = SanskritMeterVerification(
    status="not-run",
    checks=0,
    method="independent meter-pattern recomputation",
    issues=[],
)

MATRA_SHAPES = frozenset(["GG", "GLL", "LGL", "LLG", "LLLL"])


@dataclass
class _PadaSlice:
    source_unit_index: int
    syllables: List


def pattern_of(syllables: Sequence) -> str:
    return "".join("G" if s.weight == "guru" else "L" for s in syllables)


def normalized_spec_patterns(spec: ClassicalVarnaMeterSpec) -> Tuple[str, ...]:
    if len(spec.pada_patterns) == 1:
        return tuple([spec.pada_patterns[0]] * 4)
    if len(spec.pada_patterns) == 2:
        return (
            spec.pada_patterns[0],
            spec.pada_patterns[1],
            spec.pada_patterns[0],
            spec.pada_patterns[1],
        )
    return spec.pada_patterns


def _grounded_candidate(
    candidate: SanskritMeterCandidate,
    gana_patterns: Optional[Sequence[str]] = None,
) -> SanskritMeterCandidate:
    candidate.classification = classification_for(
        MeterClassificationInput(
            id=candidate.id,
            name=candidate.name,
            kind=candidate.kind,
            tradition=candidate.tradition,
            pada_lengths=[p.syllable_end - p.syllable_start for p in candidate.padas],
            gana_patterns=list(gana_patterns) if gana_patterns else None,
            yati=list(candidate.yati) if candidate.yati else None,
        )
    )
    candidate.authority = authority_evidence_for(
        candidate.id, candidate.tradition, candidate.source
    )
    return candidate


def split_units_by_syllable_lengths(
    analysis, lengths: Sequence[int]
) -> Optional[List[_PadaSlice]]:
    slices: List[_PadaSlice] = []
    expected_index = 0
    for unit in analysis.padas:
        local_start = 0
        while local_start < len(unit.syllables):
            if expected_index >= len(lengths):
                return None
            length = lengths[expected_index]
            if local_start + length > len(unit.syllables):
                return None
            slices.append(
                _PadaSlice(
                    source_unit_index=unit.index,
                    syllables=unit.syllables[local_start:local_start + length],
                )
            )
            local_start += length
            expected_index += 1
    return slices if expected_index == len(lengths) else None


def split_units_by_matras(analysis, targets: Sequence[int]) -> Optional[List[_PadaSlice]]:
    slices: List[_PadaSlice] = []
    target_index = 0
    for unit in analysis.padas:
        local_start = 0
        while local_start < len(unit.syllables):
            if target_index >= len(targets):
                return None
            target = targets[target_index]
            total = 0
            local_end = local_start
            while local_end < len(unit.syllables) and total < target:
                total += unit.syllables[local_end].matras
                local_end += 1
            if total != target:
                return None
            slices.append(
                _PadaSlice(
                    source_unit_index=unit.index,
                    syllables=unit.syllables[local_start:local_end],
                )
            )
            local_start = local_end
            target_index += 1
    return slices if target_index == len(targets) else None


def source_for(spec_source: ChandasSourceRef) -> SanskritMeterSource:
    known_url = (
        VR_SOURCE.url
        if "Vṛttaratnākara" in spec_source.work
        else CK_SOURCE.url
        if "Chandaḥ-kaustubha" in spec_source.work
        else None
    )
    return SanskritMeterSource(
        work=spec_source.work,
        locator=spec_source.locator,
        url=known_url,
        note=spec_source.note,
    )


def mismatch_evidence(
    slice_: _PadaSlice, expected: str, pada_index: int, terminal_policy: str
) -> SanskritMeterPadaEvidence:
    observed = pattern_of(slice_.syllables)
    mismatches: List[SanskritMeterMismatch] = []
    final_anceps_used = False
    for position in range(len(expected)):
        if position < len(observed) and observed[position] == expected[position]:
            continue
        observed_char = observed[position] if position < len(observed) else ""
        terminal_licence = position == len(expected) - 1 and (
            terminal_policy == "bidirectional"
            or (
                terminal_policy == "short-to-guru"
                and expected[position] == "G"
                and observed_char == "L"
            )
        )
        if terminal_licence:
            final_anceps_used = True
            continue
        mismatches.append(
            SanskritMeterMismatch(
                pada_index=pada_index,
                position=position,
                expected=expected[position],
                observed=observed_char,
                syllable_index=(
                    slice_.syllables[position].index
                    if position < len(slice_.syllables)
                    else -1
                ),
            )
        )
    return SanskritMeterPadaEvidence(
        pada_index=pada_index,
        source_unit_index=slice_.source_unit_index,
        syllable_start=slice_.syllables[0].index,
        syllable_end=slice_.syllables[-1].index + 1,
        observed_pattern=observed,
        expected_pattern=expected,
        mismatches=mismatches,
        final_anceps_used=final_anceps_used,
    )


def template_for(patterns: Sequence[str]) -> Optional[str]:
    if not all(pattern == patterns[0] for pattern in patterns):
        return None
    return " ".join(
        ("—" if weight == "G" else "◡") + ("*" if index == len(patterns[0]) - 1 else "")
        for index, weight in enumerate(patterns[0])
    )


def _varna_candidate(
    analysis, spec: ClassicalVarnaMeterSpec
) -> Optional[SanskritMeterCandidate]:
    expected = normalized_spec_patterns(spec)
    if len(expected) != 4:
        return None
    slices = split_units_by_syllable_lengths(analysis, [len(p) for p in expected])
    if not slices:
        return None
    padas = [
        mismatch_evidence(slice_, expected[index], index, spec.terminal_policy)
        for index, slice_ in enumerate(slices)
    ]
    distance = sum(len(pada.mismatches) for pada in padas)
    if spec.terminal_policy == "short-to-guru":
        notes = (
            "A naturally laghu pāda-final syllable may fill the final guru position "
            "where flagged.",
        )
    elif spec.final_anceps:
        notes = ("Pāda-final weight was tested with the stored bidirectional terminal licence.",)
    else:
        notes = ()
    return _grounded_candidate(
        SanskritMeterCandidate(
            id=spec.id,
            name=spec.name,
            aliases=spec.aliases,
            kind=spec.kind,
            tradition="classical",
            match_type="exact" if distance == 0 else "near",
            distance=distance,
            boundary_transformations=max(0, len(slices) - len(analysis.padas)),
            evidence="full-verse",
            padas=padas,
            source=source_for(spec.source),
            terminal_policy=spec.terminal_policy,
            template=template_for(expected),
            yati=spec.yati[0] if spec.yati else None,
            notes=notes,
        ),
        spec.gana_patterns,
    )


def _exact_pattern_match(slice_: _PadaSlice, expected: str, terminal_policy: str) -> bool:
    return not mismatch_evidence(slice_, expected, 0, terminal_policy).mismatches


def _upajati_candidate(
    analysis, family: SanskritUpajatiRuleSpec
) -> Optional[SanskritMeterCandidate]:
    members = [
        spec
        for spec in (
            next((s for s in CLASSICAL_VARNA_METERS if s.id == mid), None)
            for mid in family.member_ids
        )
        if spec
    ]
    if len(members) != 2 or any(len(m.pada_patterns) != 1 for m in members):
        return None
    length = len(members[0].pada_patterns[0])
    if len(members[1].pada_patterns[0]) != length:
        return None
    slices = split_units_by_syllable_lengths(analysis, [length] * 4)
    if not slices:
        return None

    chosen = [
        next(
            (
                m
                for m in members
                if _exact_pattern_match(slice_, m.pada_patterns[0], m.terminal_policy)
            ),
            None,
        )
        for slice_ in slices
    ]
    if any(member is None for member in chosen):
        return None
    if all(member.id == chosen[0].id for member in chosen):
        return None
    padas = []
    for index, slice_ in enumerate(slices):
        evidence = mismatch_evidence(
            slice_, chosen[index].pada_patterns[0], index, chosen[index].terminal_policy
        )
        evidence.member_name = chosen[index].name
        padas.append(evidence)
    uniform = all(m.terminal_policy == chosen[0].terminal_policy for m in chosen)
    return _grounded_candidate(
        SanskritMeterCandidate(
            id=family.id,
            name=family.name,
            aliases=(),
            kind="upajati",
            tradition="classical",
            match_type="exact",
            distance=0,
            boundary_transformations=max(0, 4 - len(analysis.padas)),
            evidence="full-verse",
            padas=padas,
            source=family.source,
            terminal_policy=chosen[0].terminal_policy if uniform else "bidirectional",
            subtypes=tuple(m.name for m in chosen),
            notes=("Each pāda independently matched one of the two named upajāti members.",),
        ),
        [m.gana_patterns[0] for m in chosen],
    )


def odd_sloka_subtype(pattern: str) -> str:
    middle = pattern[1:7]
    close = pattern[3:7]
    if pattern[4:7] == "LGG":
        return "pathyā"
    if middle == "GLGGGG":
        return "ma-vipulā"
    if middle in ("GLGGLL", "GGGGLL"):
        return "bha-vipulā"
    if close == "GLLL":
        return "na-vipulā"
    if close == "GGLG":
        return "ra-vipulā"
    return "unclassified odd-pāda cadence"


def sloka_subtype(pattern: str, pada_index: int) -> Tuple[str, List[str]]:
    problems: List[str] = []
    if pattern[1:3] == "LL":
        problems.append("syllables 2–3 are both laghu")
    if pada_index % 2 == 1:
        if pattern[1:4] == "GLG":
            problems.append("an even pāda has prohibited ra-gaṇa at 2–4")
        if pattern[4:7] != "LGL":
            problems.append("an even pāda lacks the required LGL cadence at 5–7")
        return "even-pāda cadence", problems
    subtype = odd_sloka_subtype(pattern)
    if subtype.startswith("unclassified"):
        problems.append("the odd-pāda cadence is not pathyā or a supported vipulā")
    return subtype, problems


def _sloka_candidate(analysis) -> Optional[SanskritMeterCandidate]:
    if any(len(unit.syllables) % 8 != 0 for unit in analysis.padas):
        return None
    pada_count = sum(len(unit.syllables) // 8 for unit in analysis.padas)
    if pada_count < 4 or pada_count % 2 != 0:
        return None
    slices = split_units_by_syllable_lengths(analysis, [8] * pada_count)
    if not slices:
        return None
    scans = [
        sloka_subtype(pattern_of(slice_.syllables), index)
        for index, slice_ in enumerate(slices)
    ]
    distance = sum(len(problems) for _, problems in scans)
    if distance == 0:
        notes = ("All pādas satisfy the implemented pathyā/vipulā and even-cadence rules.",)
    else:
        notes = (
            "The 8-syllable count is compatible with anuṣṭubh, but one or more "
            "classical cadence rules failed.",
            *(
                f"Pāda {index + 1}: {problem}."
                for index, (_, problems) in enumerate(scans)
                for problem in problems
            ),
        )
    return _grounded_candidate(
        SanskritMeterCandidate(
            id=SLOKA_RULE.id,
            name=SLOKA_RULE.name,
            aliases=SLOKA_RULE.aliases,
            kind="sloka",
            tradition="classical",
            match_type="exact" if distance == 0 else "class-compatible",
            distance=distance,
            boundary_transformations=max(0, len(slices) - len(analysis.padas)),
            evidence="full-verse" if pada_count == 4 else "extended-stanza",
            padas=[
                SanskritMeterPadaEvidence(
                    pada_index=index,
                    source_unit_index=slice_.source_unit_index,
                    syllable_start=slice_.syllables[0].index,
                    syllable_end=slice_.syllables[-1].index + 1,
                    observed_pattern=pattern_of(slice_.syllables),
                    mismatches=[],
                    final_anceps_used=False,
                )
                for index, slice_ in enumerate(slices)
            ],
            source=SLOKA_RULE.source,
            subtypes=tuple(subtype for subtype, _ in scans),
            notes=notes,
        )
    )


def groups_by_targets(syllables: Sequence, targets: Sequence[int]) -> Optional[List[str]]:
    groups: List[str] = []
    start = 0
    for target in targets:
        total = 0
        end = start
        while end < len(syllables) and total < target:
            total += syllables[end].matras
            end += 1
        if total != target:
            return None
        groups.append(pattern_of(syllables[start:end]))
        start = end
    return groups if start == len(syllables) else None


def arya_half_problems(syllables: Sequence, kind: str) -> List[str]:
    if kind == "first":
        targets = [4, 4, 4, 4, 4, 4, 4, 2]
    elif kind == "second":
        targets = [4, 4, 4, 4, 4, 1, 4, 2]
    else:
        targets = [4, 4, 4, 4, 4, 4, 4, 4]
    groups = groups_by_targets(syllables, targets)
    if not groups:
        return ["mātrās do not fall on the required gaṇa boundaries"]
    problems: List[str] = []
    for index, group in enumerate(groups):
        if targets[index] == 4 and group not in MATRA_SHAPES:
            problems.append(f"gaṇa {index + 1} is not caturmātrika")
        if index % 2 == 0 and group == "LGL":
            problems.append(f"odd gaṇa {index + 1} is prohibited ja-gaṇa")
    if kind in ("first", "aryagiti") and groups[5] not in ("LGL", "LLLL"):
        problems.append("the sixth gaṇa is neither ja-gaṇa nor four laghus")
    if kind != "aryagiti" and groups[-1] != "G":
        problems.append("the final half-gaṇa is not one guru")
    return problems


def _jati_candidate(
    analysis, spec: SanskritJatiRuleSpec
) -> Optional[SanskritMeterCandidate]:
    slices = split_units_by_matras(analysis, spec.quarter_matras)
    if not slices or len(slices) != 4:
        return None
    halves = [
        slices[0].syllables + slices[1].syllables,
        slices[2].syllables + slices[3].syllables,
    ]
    problems = [
        f"Half {index + 1}: {problem}"
        for index, half in enumerate(halves)
        for problem in arya_half_problems(half, spec.half_kinds[index])
    ]
    return _grounded_candidate(
        SanskritMeterCandidate(
            id=spec.id,
            name=spec.name,
            aliases=(),
            kind="jati",
            tradition="classical",
            match_type="exact" if not problems else "near",
            distance=len(problems),
            boundary_transformations=max(0, 4 - len(analysis.padas)),
            evidence="full-verse",
            padas=[
                SanskritMeterPadaEvidence(
                    pada_index=index,
                    source_unit_index=slice_.source_unit_index,
                    syllable_start=slice_.syllables[0].index,
                    syllable_end=slice_.syllables[-1].index + 1,
                    observed_pattern=pattern_of(slice_.syllables),
                    mismatches=[],
                    final_anceps_used=False,
                )
                for index, slice_ in enumerate(slices)
            ],
            source=spec.source,
            subtypes=tuple(f"{matras} mātrās" for matras in spec.quarter_matras),
            notes=(
                ("Mātrā totals and internal āryā-family gaṇa rules agree.",)
                if not problems
                else tuple(problems)
            ),
        )
    )


def _vedic_candidate(
    analysis,
    spec: SanskritVedicRuleSpec,
    lengths: Sequence[int],
    subtype: Optional[str] = None,
    variant_pada_index: Optional[int] = None,
) -> Optional[SanskritMeterCandidate]:
    slices = split_units_by_syllable_lengths(analysis, lengths)
    if not slices:
        return None
    variant_id = "nicrt" if subtype == "nicṛt" else subtype
    candidate_id = (
        f"{spec.id}-{variant_id}-pada-{variant_pada_index + 1}"
        if subtype and variant_pada_index is not None
        else spec.id
    )
    return _grounded_candidate(
        SanskritMeterCandidate(
            id=candidate_id,
            name=f"{subtype} {spec.name}" if subtype else spec.name,
            aliases=(),
            kind="vedic",
            tradition="vedic",
            match_type="class-compatible",
            distance=0,
            boundary_transformations=max(0, len(slices) - len(analysis.padas)),
            evidence="count-only",
            padas=[
                SanskritMeterPadaEvidence(
                    pada_index=index,
                    source_unit_index=slice_.source_unit_index,
                    syllable_start=slice_.syllables[0].index,
                    syllable_end=slice_.syllables[-1].index + 1,
                    observed_pattern=pattern_of(slice_.syllables),
                    mismatches=[],
                    final_anceps_used=False,
                )
                for index, slice_ in enumerate(slices)
            ],
            source=spec.source,
            subtypes=(f"pāda counts {' + '.join(str(n) for n in lengths)}",),
            notes=(
                "This is a Vedic count-class match, not a classical fixed-pattern verdict.",
                "Accent, cadence, resolution, and metrically restored vowels require a "
                "Vedic edition or pada-pāṭha.",
            ),
        )
    )


def _vedic_candidates(analysis) -> List[SanskritMeterCandidate]:
    candidates: List[SanskritMeterCandidate] = []
    for spec in VEDIC_SPECS:
        exact = _vedic_candidate(analysis, spec, spec.pada_lengths)
        if exact:
            candidates.append(exact)
            continue
        for index in range(len(spec.pada_lengths)):
            for delta, subtype in ((-1, "nicṛt"), (1, "bhurik")):
                lengths = list(spec.pada_lengths)
                lengths[index] += delta
                variant = _vedic_candidate(analysis, spec, lengths, subtype, index)
                if variant:
                    candidates.append(variant)
    return candidates


def _partial_sama_candidates(analysis) -> List[SanskritMeterCandidate]:
    if not analysis.padas or len(analysis.padas) > 2:
        return []
    result: List[SanskritMeterCandidate] = []
    for spec in CLASSICAL_VARNA_METERS:
        if spec.kind != "sama-vrtta" or len(spec.pada_patterns) != 1:
            continue
        expected = spec.pada_patterns[0]
        if any(len(unit.syllables) != len(expected) for unit in analysis.padas):
            continue
        padas = [
            mismatch_evidence(
                _PadaSlice(unit.index, unit.syllables), expected, index, spec.terminal_policy
            )
            for index, unit in enumerate(analysis.padas)
        ]
        if sum(len(pada.mismatches) for pada in padas) != 0:
            continue
        result.append(
            _grounded_candidate(
                SanskritMeterCandidate(
                    id=spec.id,
                    name=spec.name,
                    aliases=spec.aliases,
                    kind=spec.kind,
                    tradition="classical",
                    match_type="partial",
                    distance=0,
                    boundary_transformations=0,
                    evidence="fragment",
                    padas=padas,
                    source=source_for(spec.source),
                    terminal_policy=spec.terminal_policy,
                    template=template_for([expected]),
                    yati=spec.yati[0] if spec.yati else None,
                    notes=(
                        "The supplied fragment is compatible, but a complete "
                        "four-pāda verse was not present.",
                    ),
                ),
                spec.gana_patterns,
            )
        )
    return result


# --- ranking --------------------------------------------------------------


def match_rank(candidate: SanskritMeterCandidate) -> int:
    return {"exact": 0, "class-compatible": 1, "partial": 2}.get(candidate.match_type, 3)


def evidence_rank(candidate: SanskritMeterCandidate) -> int:
    return {"full-verse": 0, "extended-stanza": 1, "count-only": 2}.get(
        candidate.evidence, 3
    )


def _sort_key(candidate: SanskritMeterCandidate):
    return (
        match_rank(candidate),
        evidence_rank(candidate),
        candidate.distance,
        candidate.boundary_transformations,
        1 if candidate.tradition == "vedic" else 0,
        candidate.id,
    )


def compare_candidates(left: SanskritMeterCandidate, right: SanskritMeterCandidate) -> int:
    lk, rk = _sort_key(left), _sort_key(right)
    return -1 if lk < rk else (1 if lk > rk else 0)


def same_rank(left: SanskritMeterCandidate, right: SanskritMeterCandidate) -> bool:
    return (
        match_rank(left) == match_rank(right)
        and evidence_rank(left) == evidence_rank(right)
        and left.distance == right.distance
        and left.boundary_transformations == right.boundary_transformations
        and left.tradition == right.tradition
    )


def identification_status(
    primary: Optional[SanskritMeterCandidate], tied_count: int
) -> str:
    if not primary:
        return "unidentified"
    if primary.match_type == "partial":
        return "insufficient-evidence"
    if primary.match_type == "near":
        return "unidentified"
    if tied_count > 1:
        return "ambiguous"
    complete_exact_rule = primary.match_type == "exact" and primary.evidence in (
        "full-verse",
        "extended-stanza",
    )
    return (
        "identified"
        if complete_exact_rule and primary.authority.coverage == "dual-root-bhasya"
        else "provisional"
    )


def _identification_diagnostics(
    primary: Optional[SanskritMeterCandidate], status: str, tied_count: int
) -> List[str]:
    if not primary:
        return ["No exact catalog or count-class match was found."]
    if status == "ambiguous":
        return [
            f"{tied_count} candidates have equal evidence; no catalog-order guess was made."
        ]
    if status == "insufficient-evidence":
        return [
            "A compatible pāda fragment was found, but the complete stanza is "
            "required for identification."
        ]
    if status == "provisional":
        if primary.tradition == "vedic":
            return [
                "This is Vedic count-class compatibility only, not a full meter "
                "identification. An applicable Vedic mūla–bhāṣya pair, accent, "
                "cadence, and edition-aware textual witness are not yet attached; "
                "Chandaḥ-kaustubha supplies no Vedic counterpart."
            ]
        if primary.authority.coverage != "dual-root-bhasya":
            return [
                "The pattern matches computationally, but paired mūla–bhāṣya "
                "evidence is not yet keyed in both the general and Gauḍīya lanes. "
                "This is not a fully grounded identification."
            ]
        return [
            "The supplied text is structurally compatible, but it does not satisfy "
            "the evidence policy for a fully grounded identification."
        ]
    if primary.match_type == "near":
        return [
            "No exact match was found; the closest same-length candidates are shown "
            "as diagnostics only."
        ]
    return []


def _attach_meter_verification(
    analysis, result: SanskritMeterIdentification
) -> SanskritMeterIdentification:
    from .meter_verifier import verify_sanskrit_meter_identification

    verification = verify_sanskrit_meter_identification(
        analysis, result, result.requested_tradition
    )
    if verification.status != "failed":
        result.verification = verification
        return result
    result.status = "invalid-analysis"
    result.identified = False
    result.diagnostics = result.diagnostics + [
        "The independent meter checker found an internal inconsistency, so no "
        "verdict is shown."
    ]
    result.verification = verification
    return result


def _finalize_result(
    analysis,
    candidates: List[SanskritMeterCandidate],
    catalog_size: int,
    requested_tradition: str,
) -> SanskritMeterIdentification:
    candidates.sort(key=_sort_key)
    primary = candidates[0] if candidates else None
    tied = [c for c in candidates if same_rank(c, primary)] if primary else []
    status = identification_status(primary, len(tied))
    result = SanskritMeterIdentification(
        requested_tradition=requested_tradition,
        status=status,
        identified=status == "identified",
        primary=primary,
        candidates=candidates,
        observed_unit_patterns=[pattern_of(unit.syllables) for unit in analysis.padas],
        diagnostics=_identification_diagnostics(primary, status, len(tied)),
        verification=NOT_RUN,
        catalog_size=catalog_size,
    )
    return _attach_meter_verification(analysis, result)


def _invalid_result(
    analysis, catalog_size: int, requested_tradition: str
) -> SanskritMeterIdentification:
    reason = (
        "Meter identification requires a successful syllable analysis."
        if not analysis.ok
        else "Meter identification requires the syllable maker–checker to pass first."
    )
    return SanskritMeterIdentification(
        requested_tradition=requested_tradition,
        status="invalid-analysis",
        identified=False,
        candidates=[],
        observed_unit_patterns=[pattern_of(unit.syllables) for unit in analysis.padas],
        diagnostics=[reason],
        verification=NOT_RUN,
        catalog_size=catalog_size,
    )


def _classical_candidates(analysis, include_near: bool) -> List[SanskritMeterCandidate]:
    varna = [
        candidate
        for candidate in (_varna_candidate(analysis, spec) for spec in CLASSICAL_VARNA_METERS)
        if candidate
    ]
    exact_varna = [c for c in varna if c.match_type == "exact"]
    upajatis = [
        candidate
        for candidate in (_upajati_candidate(analysis, f) for f in UPAJATI_FAMILIES)
        if candidate
    ]
    sloka = _sloka_candidate(analysis)
    jatis = [
        candidate
        for candidate in (_jati_candidate(analysis, spec) for spec in JATI_SPECS)
        if candidate
    ]
    exact_jatis = [c for c in jatis if c.match_type == "exact"]
    candidates = [*exact_varna, *upajatis, *([sloka] if sloka else []), *exact_jatis]
    no_exact = not exact_varna and not sloka and not exact_jatis
    if not no_exact or not include_near:
        return candidates
    near = sorted(
        (c for c in [*varna, *jatis] if c.match_type == "near"), key=_sort_key
    )[:3]
    return [*candidates, *near]


def _candidates_for_tradition(
    analysis, tradition: str, include_near: bool
) -> List[SanskritMeterCandidate]:
    candidates = [] if tradition == "vedic" else _classical_candidates(analysis, include_near)
    has_exact_classical = any(
        c.tradition == "classical" and c.match_type == "exact" for c in candidates
    )
    if tradition == "vedic" or (tradition == "auto" and not has_exact_classical):
        candidates.extend(_vedic_candidates(analysis))
    if not candidates and tradition != "vedic":
        candidates.extend(_partial_sama_candidates(analysis))
    return candidates


def identify_sanskrit_meter(
    analysis, tradition: str = "auto", include_near: bool = True
) -> SanskritMeterIdentification:
    """
    Identifies a Sanskrit metre without mutating the syllable analysis. Exact
    varṇa matches are tried before rule-based śloka/jāti and count-based Vedic
    families. Near matches are suggestions only and can never become a verdict.
    """
    catalog_size = (
        len(CLASSICAL_VARNA_METERS)
        + len(UPAJATI_FAMILIES)
        + len(JATI_SPECS)
        + len(VEDIC_SPECS)
        + 1
    )
    if not analysis.ok or analysis.verification.status != "verified":
        return _invalid_result(analysis, catalog_size, tradition)
    candidates = _candidates_for_tradition(analysis, tradition, include_near)
    return _finalize_result(analysis, candidates, catalog_size, tradition)
