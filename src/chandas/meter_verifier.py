# -*- coding: utf-8 -*-
"""
Independent re-check of a meter verdict.

Ported from Prasadam's lib/sanskrit-meter-verifier.ts.

This checker deliberately does not call the maker's matching or ranking
helpers: it resolves the canonical catalog rules itself, recomputes evidence
and ranking, and validates authority-role integrity. A failed check means the
verdict is not safe to present as an identification, even if the underlying
syllable analysis remains valid.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

from .authorities import authority_evidence_for
from .catalog import CLASSICAL_VARNA_METERS, ClassicalVarnaMeterSpec
from .classification import MeterClassificationInput, classification_for
from .rule_registry import (
    CK_SOURCE,
    JATI_BY_ID,
    JATI_SPECS,
    SLOKA_RULE,
    UPAJATI_BY_ID,
    UPAJATI_FAMILIES,
    VEDIC_BY_ID,
    VEDIC_SPECS,
    VR_SOURCE,
    SanskritVedicRuleSpec,
)
from .types import (
    SanskritMeterCandidate,
    SanskritMeterIdentification,
    SanskritMeterMismatch,
    SanskritMeterSource,
    SanskritMeterVerification,
    SanskritMeterVerificationIssue,
)

METHOD = (
    "independent meter checker: resolve canonical catalog rules, recompute "
    "evidence and ranking, and validate authority-role integrity"
)

MATRA_GROUPS = frozenset(["GG", "GLL", "LGL", "LLG", "LLLL"])
DUAL_WITNESS_IDS = frozenset(["indravajra", "upendravajra", "upajati-tristubh"])

_VEDIC_SUFFIX = re.compile(r"-(?:nicrt|nicṛt|bhurik)(?:-pada-[1-9][0-9]*)?$")


@dataclass
class _FixedRule:
    pattern: str
    terminal_policy: str


@dataclass
class _CheckState:
    checks: int = 0
    issues: List[SanskritMeterVerificationIssue] = field(default_factory=list)


def _check(
    state: _CheckState,
    condition: bool,
    code: str,
    message: str,
    candidate_id: Optional[str] = None,
    pada_index: Optional[int] = None,
    position: Optional[int] = None,
) -> None:
    state.checks += 1
    if not condition:
        state.issues.append(
            SanskritMeterVerificationIssue(
                code=code,
                message=message,
                candidate_id=candidate_id,
                pada_index=pada_index,
                position=position,
            )
        )


def _pattern_of(syllables: Sequence) -> str:
    return "".join("G" if s.weight == "guru" else "L" for s in syllables)


def _same_mismatch(left: SanskritMeterMismatch, right: SanskritMeterMismatch) -> bool:
    return (
        left.pada_index == right.pada_index
        and left.position == right.position
        and left.expected == right.expected
        and left.observed == right.observed
        and left.syllable_index == right.syllable_index
    )


def _terminal_licence_applies(
    rule: _FixedRule, expected: str, observed: str, position: int
) -> bool:
    if position != len(expected) - 1:
        return False
    if rule.terminal_policy == "bidirectional":
        return True
    return (
        rule.terminal_policy == "short-to-guru"
        and expected[position] == "G"
        and position < len(observed)
        and observed[position] == "L"
    )


def _normalized_spec_patterns(spec: ClassicalVarnaMeterSpec) -> Tuple[str, ...]:
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


def _canonical_template(patterns: Sequence[str]) -> Optional[str]:
    if not all(pattern == patterns[0] for pattern in patterns):
        return None
    return " ".join(
        ("—" if weight == "G" else "◡") + ("*" if index == len(patterns[0]) - 1 else "")
        for index, weight in enumerate(patterns[0])
    )


def _expected_fixed_notes(
    spec: ClassicalVarnaMeterSpec, is_fragment: bool
) -> Tuple[str, ...]:
    if is_fragment:
        return (
            "The supplied fragment is compatible, but a complete four-pāda verse "
            "was not present.",
        )
    if spec.terminal_policy == "short-to-guru":
        return (
            "A naturally laghu pāda-final syllable may fill the final guru position "
            "where flagged.",
        )
    return (
        ("Pāda-final weight was tested with the stored bidirectional terminal licence.",)
        if spec.final_anceps
        else ()
    )


def _fixed_pada_checks(
    state: _CheckState,
    candidate: SanskritMeterCandidate,
    pada_index: int,
    syllables: Sequence,
    rule: _FixedRule,
) -> int:
    pada = candidate.padas[pada_index]
    expected = rule.pattern
    _check(
        state,
        pada.expected_pattern == expected,
        "CANONICAL_PATTERN_CHANGED",
        f"{candidate.name}, pāda {pada_index + 1}: the claimed target differs from "
        "the catalog rule.",
        candidate.id,
        pada_index,
    )
    observed = _pattern_of(syllables)
    _check(
        state,
        len(expected) == len(observed),
        "PATTERN_LENGTH_MISMATCH",
        f"{candidate.name}, pāda {pada_index + 1}: expected and observed patterns "
        "have different lengths.",
        candidate.id,
        pada_index,
    )
    recomputed: List[SanskritMeterMismatch] = []
    anceps_used = False
    for position in range(min(len(expected), len(observed))):
        if expected[position] == observed[position]:
            continue
        if _terminal_licence_applies(rule, expected, observed, position):
            anceps_used = True
            continue
        recomputed.append(
            SanskritMeterMismatch(
                pada_index=pada_index,
                position=position,
                expected=expected[position],
                observed=observed[position],
                syllable_index=(
                    syllables[position].index if position < len(syllables) else -1
                ),
            )
        )
    _check(
        state,
        pada.final_anceps_used == anceps_used,
        "ANCEPS_EVIDENCE_MISMATCH",
        f"{candidate.name}, pāda {pada_index + 1}: the final-anceps flag does not "
        "describe the observed final weight.",
        candidate.id,
        pada_index,
    )
    evidence_matches = len(recomputed) == len(pada.mismatches) and all(
        _same_mismatch(mismatch, pada.mismatches[index])
        for index, mismatch in enumerate(recomputed)
    )
    _check(
        state,
        evidence_matches,
        "MISMATCH_EVIDENCE_CHANGED",
        f"{candidate.name}, pāda {pada_index + 1}: mismatch evidence did not survive "
        "independent recomputation.",
        candidate.id,
        pada_index,
    )
    return len(recomputed)


@dataclass
class _CanonicalMetadata:
    id: str
    name: str
    aliases: Tuple[str, ...]
    kind: str
    tradition: str
    source: SanskritMeterSource


def _same_source(left: SanskritMeterSource, right: SanskritMeterSource) -> bool:
    return (
        left.work == right.work
        and left.locator == right.locator
        and left.url == right.url
        and left.note == right.note
    )


def _canonical_identity_checks(
    state: _CheckState, candidate: SanskritMeterCandidate, expected: _CanonicalMetadata
) -> None:
    _check(
        state,
        candidate.id == expected.id
        and candidate.name == expected.name
        and candidate.kind == expected.kind
        and candidate.tradition == expected.tradition
        and tuple(candidate.aliases) == tuple(expected.aliases),
        "RULE_FAMILY_IDENTITY_CHANGED",
        f"{candidate.id}: name, kind, tradition, or aliases differ from the "
        "canonical rule family.",
        candidate.id,
    )
    _check(
        state,
        _same_source(candidate.source, expected.source),
        "RULE_FAMILY_PROVENANCE_CHANGED",
        f"{candidate.name}: source work, locator, URL, or note differs from the "
        "canonical registry.",
        candidate.id,
    )


def _empty_pada_rule_evidence_checks(
    state: _CheckState, candidate: SanskritMeterCandidate
) -> None:
    for pada_index, pada in enumerate(candidate.padas):
        _check(
            state,
            pada.expected_pattern is None
            and not pada.mismatches
            and pada.final_anceps_used is False
            and pada.member_name is None,
            "RULE_FAMILY_PADA_EVIDENCE_CHANGED",
            f"{candidate.name}, pāda {pada_index + 1}: a count/cadence rule acquired "
            "fabricated fixed-pattern evidence.",
            candidate.id,
            pada_index,
        )


def _absent_fixed_display_fields_checks(
    state: _CheckState, candidate: SanskritMeterCandidate
) -> None:
    _check(
        state,
        candidate.terminal_policy is None
        and candidate.template is None
        and candidate.yati is None,
        "RULE_FAMILY_DISPLAY_RULE_CHANGED",
        f"{candidate.name}: an unregistered terminal policy, template, or yati was added.",
        candidate.id,
    )


def _fixed_display_metadata_checks(
    state: _CheckState, candidate: SanskritMeterCandidate, spec: ClassicalVarnaMeterSpec
) -> None:
    patterns = _normalized_spec_patterns(spec)
    is_fragment = spec.kind == "sama-vrtta" and len(candidate.padas) < 4
    _check(
        state,
        candidate.template == _canonical_template(patterns),
        "TEMPLATE_CHANGED",
        f"{candidate.name}: the rendered weight template differs from the catalog rule.",
        candidate.id,
    )
    _check(
        state,
        candidate.yati == (spec.yati[0] if spec.yati else None),
        "YATI_CHANGED",
        f"{candidate.name}: displayed yati metadata differs from the catalog entry.",
        candidate.id,
    )
    _check(
        state,
        candidate.subtypes is None,
        "FIXED_SUBTYPES_CHANGED",
        f"{candidate.name}: a fixed catalog meter cannot acquire unregistered "
        "subtype labels.",
        candidate.id,
    )
    _check(
        state,
        tuple(candidate.notes) == _expected_fixed_notes(spec, is_fragment),
        "FIXED_NOTES_CHANGED",
        f"{candidate.name}: displayed rule notes differ from the independently "
        "derived notes.",
        candidate.id,
    )


def _upajati_display_metadata_checks(
    state: _CheckState, candidate: SanskritMeterCandidate
) -> None:
    member_names = tuple(pada.member_name for pada in candidate.padas)
    _check(
        state,
        tuple(candidate.subtypes or ()) == member_names,
        "UPAJATI_SUBTYPES_CHANGED",
        f"{candidate.name}: displayed member sequence differs from its pāda evidence.",
        candidate.id,
    )
    _check(
        state,
        candidate.template is None and candidate.yati is None,
        "UPAJATI_DISPLAY_RULE_CHANGED",
        f"{candidate.name}: unregistered template or yati metadata was added.",
        candidate.id,
    )
    _check(
        state,
        tuple(candidate.notes)
        == ("Each pāda independently matched one of the two named upajāti members.",),
        "UPAJATI_NOTES_CHANGED",
        f"{candidate.name}: displayed rule notes differ from the independently "
        "derived note.",
        candidate.id,
    )


def _upajati_rules_for(
    state: _CheckState, candidate: SanskritMeterCandidate
) -> Optional[List[_FixedRule]]:
    family = UPAJATI_BY_ID.get(candidate.id)
    members = [
        spec
        for spec in (
            next((s for s in CLASSICAL_VARNA_METERS if s.id == mid), None)
            for mid in (family.member_ids if family else ())
        )
        if spec
    ]
    _check(
        state,
        len(members) == 2,
        "UNKNOWN_UPAJATI_RULE",
        f"{candidate.name}: the checker has no canonical member pair for this upajāti.",
        candidate.id,
    )
    if not family or len(members) != 2:
        return None
    _canonical_identity_checks(
        state,
        candidate,
        _CanonicalMetadata(
            id=family.id,
            name=family.name,
            aliases=(),
            kind="upajati",
            tradition="classical",
            source=family.source,
        ),
    )
    rules: List[_FixedRule] = []
    for index, pada in enumerate(candidate.padas):
        stated_name = pada.member_name or (
            candidate.subtypes[index]
            if candidate.subtypes and index < len(candidate.subtypes)
            else None
        )
        member = next((item for item in members if item.name == stated_name), None)
        _check(
            state,
            member is not None,
            "UPAJATI_MEMBER_CHANGED",
            f"{candidate.name}, pāda {index + 1}: the stated member is not in the "
            "canonical pair.",
            candidate.id,
            index,
        )
        rules.append(
            _FixedRule(member.pada_patterns[0], member.terminal_policy)
            if member
            else _FixedRule("", "fixed")
        )
    member_names = [
        pada.member_name
        or (
            candidate.subtypes[index]
            if candidate.subtypes and index < len(candidate.subtypes)
            else None
        )
        for index, pada in enumerate(candidate.padas)
    ]
    _check(
        state,
        len(set(member_names)) > 1,
        "UPAJATI_NOT_MIXED",
        f"{candidate.name}: a pure four-pāda member must not be relabelled upajāti.",
        candidate.id,
    )
    uniform_policy = rules[0].terminal_policy if rules else None
    expected_policy = (
        uniform_policy
        if all(rule.terminal_policy == uniform_policy for rule in rules)
        else "bidirectional"
    )
    _check(
        state,
        candidate.terminal_policy == expected_policy,
        "UPAJATI_TERMINAL_POLICY_CHANGED",
        f"{candidate.name}: terminal-weight policy differs from the selected member rules.",
        candidate.id,
    )
    _upajati_display_metadata_checks(state, candidate)
    return rules


def _catalog_rules_for(
    state: _CheckState, candidate: SanskritMeterCandidate
) -> Optional[List[_FixedRule]]:
    spec = next((item for item in CLASSICAL_VARNA_METERS if item.id == candidate.id), None)
    _check(
        state,
        spec is not None,
        "UNKNOWN_FIXED_RULE",
        f"{candidate.name}: the checker cannot resolve this fixed meter in the catalog.",
        candidate.id,
    )
    if not spec:
        return None
    _check(
        state,
        candidate.name == spec.name
        and candidate.kind == spec.kind
        and candidate.tradition == "classical"
        and tuple(candidate.aliases) == tuple(spec.aliases),
        "CATALOG_IDENTITY_CHANGED",
        f"{candidate.id}: name, kind, or tradition differs from the catalog entry.",
        candidate.id,
    )
    expected_url = (
        VR_SOURCE.url
        if "Vṛttaratnākara" in spec.source.work
        else CK_SOURCE.url
        if "Chandaḥ-kaustubha" in spec.source.work
        else None
    )
    _check(
        state,
        candidate.source.work == spec.source.work
        and candidate.source.locator == spec.source.locator
        and candidate.source.note == spec.source.note
        and candidate.source.url == expected_url,
        "CATALOG_PROVENANCE_CHANGED",
        f"{candidate.name}: catalog work or locator was changed.",
        candidate.id,
    )
    _check(
        state,
        candidate.terminal_policy == spec.terminal_policy,
        "TERMINAL_POLICY_CHANGED",
        f"{candidate.name}: the terminal-weight policy differs from the catalog entry.",
        candidate.id,
    )
    _fixed_display_metadata_checks(state, candidate, spec)
    return [
        _FixedRule(pattern, spec.terminal_policy)
        for pattern in _normalized_spec_patterns(spec)[: len(candidate.padas)]
    ]


def _fixed_rules_for(
    state: _CheckState, candidate: SanskritMeterCandidate
) -> Optional[List[_FixedRule]]:
    return (
        _upajati_rules_for(state, candidate)
        if candidate.kind == "upajati"
        else _catalog_rules_for(state, candidate)
    )


def _fixed_pattern_checks(
    state: _CheckState, candidate: SanskritMeterCandidate, slices: Sequence[Sequence]
) -> None:
    rules = _fixed_rules_for(state, candidate)
    if not rules or len(rules) != len(candidate.padas):
        _check(
            state,
            False,
            "FIXED_RULE_SHAPE_MISMATCH",
            f"{candidate.name}: canonical rule count differs from its pāda evidence.",
            candidate.id,
        )
        return
    distance = sum(
        _fixed_pada_checks(
            state,
            candidate,
            pada_index,
            slices[pada_index] if pada_index < len(slices) else [],
            rules[pada_index],
        )
        for pada_index in range(len(candidate.padas))
    )
    _check(
        state,
        candidate.distance == distance,
        "DISTANCE_MISMATCH",
        f"{candidate.name}: stated distance {candidate.distance} differs from "
        f"recomputed distance {distance}.",
        candidate.id,
    )
    is_fragment = candidate.kind == "sama-vrtta" and len(candidate.padas) < 4
    expected_match_type = "partial" if is_fragment else ("exact" if distance == 0 else "near")
    _check(
        state,
        candidate.match_type == expected_match_type,
        "MATCH_TYPE_MISMATCH",
        f"{candidate.name}: {candidate.match_type} is inconsistent with its "
        "fixed-pattern distance.",
        candidate.id,
    )
    _check(
        state,
        candidate.evidence == ("fragment" if is_fragment else "full-verse"),
        "FIXED_EVIDENCE_MISMATCH",
        f"{candidate.name}: fragment/full-verse evidence is inconsistent with the "
        "supplied pādas.",
        candidate.id,
    )


# --- rule families (śloka / jāti / Vedic) ---------------------------------


def _odd_sloka_subtype(pattern: str) -> str:
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


def _sloka_scan(pattern: str, pada_index: int) -> Tuple[str, List[str]]:
    problems: List[str] = []
    if pattern[1:3] == "LL":
        problems.append("syllables 2–3 are both laghu")
    if pada_index % 2 == 1:
        if pattern[1:4] == "GLG":
            problems.append("an even pāda has prohibited ra-gaṇa at 2–4")
        if pattern[4:7] != "LGL":
            problems.append("an even pāda lacks the required LGL cadence at 5–7")
        return "even-pāda cadence", problems
    subtype = _odd_sloka_subtype(pattern)
    if subtype == "unclassified odd-pāda cadence":
        problems.append("the odd-pāda cadence is not pathyā or a supported vipulā")
    return subtype, problems


def _sloka_problems(pattern: str, pada_index: int) -> int:
    return len(_sloka_scan(pattern, pada_index)[1])


def _group_patterns(syllables: Sequence, targets: Sequence[int]) -> Optional[List[str]]:
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
        groups.append(_pattern_of(syllables[start:end]))
        start = end
    return groups if start == len(syllables) else None


def _arya_problem_messages(syllables: Sequence, kind: str) -> List[str]:
    if kind == "first":
        targets = [4, 4, 4, 4, 4, 4, 4, 2]
    elif kind == "second":
        targets = [4, 4, 4, 4, 4, 1, 4, 2]
    else:
        targets = [4, 4, 4, 4, 4, 4, 4, 4]
    groups = _group_patterns(syllables, targets)
    if not groups:
        return ["mātrās do not fall on the required gaṇa boundaries"]
    problems: List[str] = []
    for index, group in enumerate(groups):
        if targets[index] == 4 and group not in MATRA_GROUPS:
            problems.append(f"gaṇa {index + 1} is not caturmātrika")
        if index % 2 == 0 and group == "LGL":
            problems.append(f"odd gaṇa {index + 1} is prohibited ja-gaṇa")
    if kind in ("first", "aryagiti") and groups[5] not in ("LGL", "LLLL"):
        problems.append("the sixth gaṇa is neither ja-gaṇa nor four laghus")
    if kind != "aryagiti" and groups[-1] != "G":
        problems.append("the final half-gaṇa is not one guru")
    return problems


def _arya_problems(syllables: Sequence, kind: str) -> int:
    return len(_arya_problem_messages(syllables, kind))


def _sloka_checks(
    state: _CheckState, candidate: SanskritMeterCandidate, slices: Sequence[Sequence]
) -> None:
    _canonical_identity_checks(
        state,
        candidate,
        _CanonicalMetadata(
            id=SLOKA_RULE.id,
            name=SLOKA_RULE.name,
            aliases=SLOKA_RULE.aliases,
            kind="sloka",
            tradition="classical",
            source=SLOKA_RULE.source,
        ),
    )
    _empty_pada_rule_evidence_checks(state, candidate)
    _absent_fixed_display_fields_checks(state, candidate)
    valid_lengths = (
        len(slices) >= 4
        and len(slices) % 2 == 0
        and all(len(slice_) == 8 for slice_ in slices)
    )
    _check(
        state,
        valid_lengths,
        "SLOKA_SHAPE_MISMATCH",
        f"{candidate.name}: śloka needs an even set of 8-syllable pādas.",
        candidate.id,
    )
    scans = [
        _sloka_scan(_pattern_of(slice_), index) for index, slice_ in enumerate(slices)
    ]
    distance = sum(len(problems) for _, problems in scans)
    _check(
        state,
        distance == candidate.distance,
        "SLOKA_DISTANCE_MISMATCH",
        f"{candidate.name}: cadence diagnostics changed.",
        candidate.id,
    )
    _check(
        state,
        candidate.match_type == ("exact" if distance == 0 else "class-compatible"),
        "SLOKA_MATCH_TYPE_MISMATCH",
        f"{candidate.name}: cadence status is inconsistent with the recomputed rules.",
        candidate.id,
    )
    _check(
        state,
        candidate.evidence == ("full-verse" if len(slices) == 4 else "extended-stanza"),
        "SLOKA_EVIDENCE_CHANGED",
        f"{candidate.name}: full/extended stanza evidence differs from the recomputed "
        "pāda count.",
        candidate.id,
    )
    _check(
        state,
        tuple(candidate.subtypes or ()) == tuple(subtype for subtype, _ in scans),
        "SLOKA_SUBTYPES_CHANGED",
        f"{candidate.name}: displayed pathyā/vipulā labels differ from the recomputed "
        "cadences.",
        candidate.id,
    )
    if distance == 0:
        expected_notes = (
            "All pādas satisfy the implemented pathyā/vipulā and even-cadence rules.",
        )
    else:
        expected_notes = (
            "The 8-syllable count is compatible with anuṣṭubh, but one or more "
            "classical cadence rules failed.",
            *(
                f"Pāda {index + 1}: {problem}."
                for index, (_, problems) in enumerate(scans)
                for problem in problems
            ),
        )
    _check(
        state,
        tuple(candidate.notes) == expected_notes,
        "SLOKA_NOTES_CHANGED",
        f"{candidate.name}: displayed cadence notes differ from independent recomputation.",
        candidate.id,
    )


def _jati_checks(
    state: _CheckState, candidate: SanskritMeterCandidate, slices: Sequence[Sequence]
) -> None:
    rule = JATI_BY_ID.get(candidate.id)
    _check(
        state,
        rule is not None,
        "UNKNOWN_JATI_RULE",
        f"{candidate.name}: the checker has no rule for this jāti.",
        candidate.id,
    )
    if not rule or len(slices) != 4:
        return
    _canonical_identity_checks(
        state,
        candidate,
        _CanonicalMetadata(
            id=rule.id,
            name=rule.name,
            aliases=(),
            kind="jati",
            tradition="classical",
            source=rule.source,
        ),
    )
    _empty_pada_rule_evidence_checks(state, candidate)
    _absent_fixed_display_fields_checks(state, candidate)
    totals = [sum(s.matras for s in slice_) for slice_ in slices]
    _check(
        state,
        all(total == rule.quarter_matras[index] for index, total in enumerate(totals)),
        "JATI_MATRA_MISMATCH",
        f"{candidate.name}: quarter mātrā totals differ from "
        f"{' + '.join(str(m) for m in rule.quarter_matras)}.",
        candidate.id,
    )
    halves = [list(slices[0]) + list(slices[1]), list(slices[2]) + list(slices[3])]
    problems = [
        f"Half {index + 1}: {problem}"
        for index, half in enumerate(halves)
        for problem in _arya_problem_messages(half, rule.half_kinds[index])
    ]
    distance = len(problems)
    _check(
        state,
        distance == candidate.distance,
        "JATI_DISTANCE_MISMATCH",
        f"{candidate.name}: internal gaṇa diagnostics changed.",
        candidate.id,
    )
    _check(
        state,
        candidate.match_type == ("exact" if distance == 0 else "near"),
        "JATI_MATCH_TYPE_MISMATCH",
        f"{candidate.name}: jāti match type is inconsistent with its rule distance.",
        candidate.id,
    )
    _check(
        state,
        candidate.evidence == "full-verse",
        "JATI_EVIDENCE_CHANGED",
        f"{candidate.name}: āryā-family rule must retain full-verse evidence.",
        candidate.id,
    )
    _check(
        state,
        tuple(candidate.subtypes or ())
        == tuple(f"{matras} mātrās" for matras in rule.quarter_matras),
        "JATI_SUBTYPES_CHANGED",
        f"{candidate.name}: displayed quarter-mātrā totals differ from the canonical rule.",
        candidate.id,
    )
    expected_notes = (
        ("Mātrā totals and internal āryā-family gaṇa rules agree.",)
        if not problems
        else tuple(problems)
    )
    _check(
        state,
        tuple(candidate.notes) == expected_notes,
        "JATI_NOTES_CHANGED",
        f"{candidate.name}: displayed āryā-family diagnostics differ from recomputation.",
        candidate.id,
    )


@dataclass
class _ObservedVedicForm:
    counts: List[int]
    valid_count: bool
    expected_id: str
    expected_name: str


def _observed_vedic_form(
    rule: SanskritVedicRuleSpec, slices: Sequence[Sequence]
) -> _ObservedVedicForm:
    counts = [len(slice_) for slice_ in slices]
    changes = [
        (count - rule.pada_lengths[index], index)
        for index, count in enumerate(counts)
        if index < len(rule.pada_lengths) and count - rule.pada_lengths[index] != 0
    ]
    length_mismatch = len(counts) != len(rule.pada_lengths)
    variant = changes[0] if len(changes) == 1 and changes[0][0] in (-1, 1) else None
    valid_count = not length_mismatch and (not changes or variant is not None)
    if not variant:
        return _ObservedVedicForm(counts, valid_count, rule.id, rule.name)
    delta, index = variant
    subtype_id = "nicrt" if delta == -1 else "bhurik"
    subtype_name = "nicṛt" if delta == -1 else "bhurik"
    return _ObservedVedicForm(
        counts,
        valid_count,
        f"{rule.id}-{subtype_id}-pada-{index + 1}",
        f"{subtype_name} {rule.name}",
    )


def _vedic_checks(
    state: _CheckState, candidate: SanskritMeterCandidate, slices: Sequence[Sequence]
) -> None:
    base_id = _VEDIC_SUFFIX.sub("", candidate.id)
    rule = VEDIC_BY_ID.get(base_id)
    _check(
        state,
        rule is not None,
        "UNKNOWN_VEDIC_CLASS",
        f"{candidate.name}: the checker has no Vedic count class.",
        candidate.id,
    )
    if not rule:
        return
    observed = _observed_vedic_form(rule, slices)
    _canonical_identity_checks(
        state,
        candidate,
        _CanonicalMetadata(
            id=observed.expected_id,
            name=observed.expected_name,
            aliases=(),
            kind="vedic",
            tradition="vedic",
            source=rule.source,
        ),
    )
    _empty_pada_rule_evidence_checks(state, candidate)
    _absent_fixed_display_fields_checks(state, candidate)
    counts_text = " + ".join(str(count) for count in observed.counts)
    _check(
        state,
        observed.valid_count,
        "VEDIC_COUNT_MISMATCH",
        f"{candidate.name}: pāda counts {counts_text} do not agree with the stated "
        "Vedic class.",
        candidate.id,
    )
    _check(
        state,
        candidate.match_type == "class-compatible" and candidate.evidence == "count-only",
        "VEDIC_EVIDENCE_OVERSTATED",
        f"{candidate.name}: a Vedic count class must remain class-compatible/count-only.",
        candidate.id,
    )
    _check(
        state,
        candidate.distance == 0,
        "VEDIC_DISTANCE_CHANGED",
        f"{candidate.name}: count-class candidates must retain zero pattern-edit distance.",
        candidate.id,
    )
    _check(
        state,
        tuple(candidate.subtypes or ()) == (f"pāda counts {counts_text}",),
        "VEDIC_SUBTYPES_CHANGED",
        f"{candidate.name}: displayed pāda counts differ from the independently "
        "sliced text.",
        candidate.id,
    )
    _check(
        state,
        tuple(candidate.notes)
        == (
            "This is a Vedic count-class match, not a classical fixed-pattern verdict.",
            "Accent, cadence, resolution, and metrically restored vowels require a "
            "Vedic edition or pada-pāṭha.",
        ),
        "VEDIC_NOTES_CHANGED",
        f"{candidate.name}: Vedic scope cautions differ from the canonical count-only "
        "wording.",
        candidate.id,
    )


def _rule_family_checks(
    state: _CheckState, candidate: SanskritMeterCandidate, slices: Sequence[Sequence]
) -> None:
    if candidate.id == SLOKA_RULE.id:
        _sloka_checks(state, candidate, slices)
        return
    if candidate.id in JATI_BY_ID:
        _jati_checks(state, candidate, slices)
        return
    if _VEDIC_SUFFIX.sub("", candidate.id) in VEDIC_BY_ID:
        _vedic_checks(state, candidate, slices)
        return
    _check(
        state,
        False,
        "UNKNOWN_RULE_FAMILY",
        f"{candidate.name}: checker cannot resolve the claimed non-fixed rule family.",
        candidate.id,
    )


# --- classification + authority integrity ---------------------------------


def _expected_system_for(candidate: SanskritMeterCandidate) -> str:
    if candidate.tradition == "vedic":
        return "vedic-chandas"
    if candidate.kind in ("jati", "matra-vrtta"):
        return "matra-jati"
    return "varna-vrtta"


def _classification_ganas(candidate: SanskritMeterCandidate) -> Optional[List[str]]:
    spec = next((item for item in CLASSICAL_VARNA_METERS if item.id == candidate.id), None)
    if spec:
        return list(spec.gana_patterns)
    family = UPAJATI_BY_ID.get(candidate.id)
    if not family:
        return None
    members = [
        item
        for item in (
            next((s for s in CLASSICAL_VARNA_METERS if s.id == mid), None)
            for mid in family.member_ids
        )
        if item
    ]
    result: List[str] = []
    for index, pada in enumerate(candidate.padas):
        member_name = pada.member_name or (
            candidate.subtypes[index]
            if candidate.subtypes and index < len(candidate.subtypes)
            else None
        )
        member = next((item for item in members if item.name == member_name), None)
        result.append(member.gana_patterns[0] if member else "")
    return result


def _reconstructed_classification(
    candidate: SanskritMeterCandidate, slices: Sequence[Sequence]
):
    spec = next((item for item in CLASSICAL_VARNA_METERS if item.id == candidate.id), None)
    gana_patterns = _classification_ganas(candidate)
    inp = MeterClassificationInput(
        id=spec.id if spec else candidate.id,
        name=spec.name if spec else candidate.name,
        kind=spec.kind if spec else candidate.kind,
        tradition="classical" if spec else candidate.tradition,
        pada_lengths=[len(slice_) for slice_ in slices],
        gana_patterns=gana_patterns,
        yati=list(spec.yati[0]) if spec and spec.yati else None,
    )
    return classification_for(inp)


def _classification_checks(
    state: _CheckState, candidate: SanskritMeterCandidate, slices: Sequence[Sequence]
) -> None:
    _check(
        state,
        candidate.classification == _reconstructed_classification(candidate, slices),
        "CLASSIFICATION_CHANGED",
        f"{candidate.name}: the full classification hierarchy differs from independent "
        "reconstruction.",
        candidate.id,
    )
    _check(
        state,
        candidate.classification.system == _expected_system_for(candidate),
        "CLASSIFICATION_SYSTEM_MISMATCH",
        f"{candidate.name}: the classification system does not agree with the matched "
        "rule family.",
        candidate.id,
    )
    _check(
        state,
        candidate.classification.specific_form == candidate.name,
        "SPECIFIC_FORM_MISMATCH",
        f"{candidate.name}: the classification hierarchy changed its specific form.",
        candidate.id,
    )
    if candidate.classification.count_class:
        counts = [len(slice_) for slice_ in slices]
        _check(
            state,
            bool(counts)
            and all(
                count == candidate.classification.count_class.syllables_per_pada
                for count in counts
            ),
            "COUNT_CLASS_MISMATCH",
            f"{candidate.name}: the stated akṣara count class does not match every pāda.",
            candidate.id,
        )


def _authority_pair_checks(state: _CheckState, candidate: SanskritMeterCandidate) -> None:
    for pair in candidate.authority.pairs:
        _check(
            state,
            pair.root.role == "root" and pair.bhasya.role == "bhasya",
            "AUTHORITY_ROLES_MISSING",
            f"{candidate.name}: an authority pair must keep mūla and bhāṣya as "
            "separate records.",
            candidate.id,
        )
        _check(
            state,
            bool(
                pair.root.work
                and pair.root.locator
                and pair.bhasya.work
                and pair.bhasya.locator
            ),
            "AUTHORITY_LOCATOR_MISSING",
            f"{candidate.name}: an authority pair is missing a work or exact locator.",
            candidate.id,
        )


def _dual_authority_check(state: _CheckState, candidate: SanskritMeterCandidate) -> None:
    if candidate.id not in DUAL_WITNESS_IDS:
        return
    traditions = {pair.tradition for pair in candidate.authority.pairs}
    _check(
        state,
        candidate.authority.coverage == "dual-root-bhasya"
        and "general-chandas" in traditions
        and "gaudiya" in traditions,
        "DUAL_AUTHORITY_INCOMPLETE",
        f"{candidate.name}: the audited rule requires both Piṅgala–Halāyudha and "
        "Gauḍīya root–bhāṣya pairs.",
        candidate.id,
    )


def _scholarship_checks(
    state: _CheckState, candidate: SanskritMeterCandidate, slices: Sequence[Sequence]
) -> None:
    registered = authority_evidence_for(
        candidate.id, candidate.tradition, candidate.source
    )
    _check(
        state,
        candidate.authority == registered,
        "AUTHORITY_REGISTRY_CHANGED",
        f"{candidate.name}: cited authority evidence differs from the reviewed registry.",
        candidate.id,
    )
    _classification_checks(state, candidate, slices)
    _authority_pair_checks(state, candidate)
    _dual_authority_check(state, candidate)


def _candidate_checks(
    state: _CheckState, analysis, candidate: SanskritMeterCandidate
) -> None:
    _check(
        state,
        bool(candidate.padas),
        "EMPTY_CANDIDATE",
        f"{candidate.name}: candidate has no pāda evidence.",
        candidate.id,
    )
    slices: List[List] = []
    previous_end = 0
    for pada_index, pada in enumerate(candidate.padas):
        valid_range = (
            isinstance(pada.syllable_start, int)
            and isinstance(pada.syllable_end, int)
            and pada.syllable_start >= 0
            and pada.syllable_end > pada.syllable_start
            and pada.syllable_end <= len(analysis.syllables)
        )
        _check(
            state,
            valid_range,
            "EVIDENCE_RANGE_INVALID",
            f"{candidate.name}, pāda {pada_index + 1}: syllable range is outside the "
            "analysis.",
            candidate.id,
            pada_index,
        )
        slice_ = (
            analysis.syllables[pada.syllable_start:pada.syllable_end]
            if valid_range
            else []
        )
        slices.append(slice_)
        _check(
            state,
            pada.pada_index == pada_index,
            "PADA_INDEX_MISMATCH",
            f"{candidate.name}: pāda evidence is not sequential.",
            candidate.id,
            pada_index,
        )
        _check(
            state,
            pada.syllable_start == previous_end,
            "EVIDENCE_NOT_CONTIGUOUS",
            f"{candidate.name}, pāda {pada_index + 1}: evidence leaves a gap or overlaps.",
            candidate.id,
            pada_index,
        )
        previous_end = pada.syllable_end
        _check(
            state,
            bool(slice_)
            and all(s.pada_index == pada.source_unit_index for s in slice_),
            "SOURCE_UNIT_MISMATCH",
            f"{candidate.name}, pāda {pada_index + 1}: source-unit provenance changed.",
            candidate.id,
            pada_index,
        )
        _check(
            state,
            _pattern_of(slice_) == pada.observed_pattern,
            "OBSERVED_PATTERN_CHANGED",
            f"{candidate.name}, pāda {pada_index + 1}: observed pattern differs from "
            "the syllable analysis.",
            candidate.id,
            pada_index,
        )
    _check(
        state,
        previous_end == len(analysis.syllables),
        "EVIDENCE_INCOMPLETE",
        f"{candidate.name}: candidate evidence does not cover the complete supplied text.",
        candidate.id,
    )
    _check(
        state,
        candidate.boundary_transformations
        == max(0, len(candidate.padas) - len(analysis.padas)),
        "BOUNDARY_COUNT_MISMATCH",
        f"{candidate.name}: inferred-boundary count is inconsistent with its evidence.",
        candidate.id,
    )

    _scholarship_checks(state, candidate, slices)

    if candidate.kind in (
        "sama-vrtta",
        "ardhasama-vrtta",
        "visama-vrtta",
        "dandaka",
        "upajati",
    ):
        _fixed_pattern_checks(state, candidate, slices)
    else:
        _rule_family_checks(state, candidate, slices)


# --- ranking recomputation ------------------------------------------------


def _match_rank(candidate: SanskritMeterCandidate) -> int:
    return {"exact": 0, "class-compatible": 1, "partial": 2}.get(candidate.match_type, 3)


def _evidence_rank(candidate: SanskritMeterCandidate) -> int:
    return {"full-verse": 0, "extended-stanza": 1, "count-only": 2}.get(
        candidate.evidence, 3
    )


def _key(candidate: SanskritMeterCandidate):
    return (
        _match_rank(candidate),
        _evidence_rank(candidate),
        candidate.distance,
        candidate.boundary_transformations,
        1 if candidate.tradition == "vedic" else 0,
        candidate.id,
    )


def _same_evidence_rank(left: SanskritMeterCandidate, right: SanskritMeterCandidate) -> bool:
    return (
        _match_rank(left) == _match_rank(right)
        and _evidence_rank(left) == _evidence_rank(right)
        and left.distance == right.distance
        and left.boundary_transformations == right.boundary_transformations
        and left.tradition == right.tradition
    )


def _can_verify(analysis) -> bool:
    return analysis.ok and analysis.verification.status == "verified"


def _unit_patterns_match(analysis, identification: SanskritMeterIdentification) -> bool:
    recomputed = [_pattern_of(pada.syllables) for pada in analysis.padas]
    return recomputed == list(identification.observed_unit_patterns)


def _split_analysis_by_lengths(analysis, lengths: Sequence[int]) -> Optional[List[List]]:
    slices: List[List] = []
    length_index = 0
    for unit in analysis.padas:
        local_start = 0
        while local_start < len(unit.syllables):
            if length_index >= len(lengths):
                return None
            length = lengths[length_index]
            if local_start + length > len(unit.syllables):
                return None
            slices.append(unit.syllables[local_start:local_start + length])
            local_start += length
            length_index += 1
    return slices if length_index == len(lengths) else None


def _slice_matches_rule(slice_: Sequence, pattern: str, terminal_policy: str) -> bool:
    observed = _pattern_of(slice_)
    if len(observed) != len(pattern):
        return False
    rule = _FixedRule(pattern, terminal_policy)
    return all(
        weight == observed[position]
        or _terminal_licence_applies(rule, pattern, observed, position)
        for position, weight in enumerate(pattern)
    )


def _independently_matched_fixed_ids(analysis) -> List[str]:
    ids: List[str] = []
    for spec in CLASSICAL_VARNA_METERS:
        patterns = _normalized_spec_patterns(spec)
        slices = _split_analysis_by_lengths(analysis, [len(p) for p in patterns])
        if not slices:
            continue
        if all(
            _slice_matches_rule(slice_, patterns[index], spec.terminal_policy)
            for index, slice_ in enumerate(slices)
        ):
            ids.append(spec.id)
    return ids


def _independently_matched_upajati_ids(analysis) -> List[str]:
    ids: List[str] = []
    for family in UPAJATI_FAMILIES:
        members = [
            spec
            for spec in (
                next((s for s in CLASSICAL_VARNA_METERS if s.id == mid), None)
                for mid in family.member_ids
            )
            if spec
        ]
        if len(members) != 2:
            continue
        length = len(members[0].pada_patterns[0])
        slices = _split_analysis_by_lengths(analysis, [length] * 4)
        if not slices:
            continue
        chosen = [
            next(
                (
                    index
                    for index, member in enumerate(members)
                    if _slice_matches_rule(
                        slice_, member.pada_patterns[0], member.terminal_policy
                    )
                ),
                -1,
            )
            for slice_ in slices
        ]
        if all(index >= 0 for index in chosen) and len(set(chosen)) > 1:
            ids.append(family.id)
    return ids


def _independent_sloka(analysis) -> Tuple[bool, bool]:
    if any(len(unit.syllables) % 8 != 0 for unit in analysis.padas):
        return False, False
    pada_count = sum(len(unit.syllables) // 8 for unit in analysis.padas)
    if pada_count < 4 or pada_count % 2 != 0:
        return False, False
    slices = _split_analysis_by_lengths(analysis, [8] * pada_count)
    if not slices:
        return False, False
    distance = sum(
        _sloka_problems(_pattern_of(slice_), index) for index, slice_ in enumerate(slices)
    )
    return True, distance == 0


def _split_analysis_by_matras(analysis, targets: Sequence[int]) -> Optional[List[List]]:
    slices: List[List] = []
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
            slices.append(unit.syllables[local_start:local_end])
            local_start = local_end
            target_index += 1
    return slices if target_index == len(targets) else None


def _independently_matched_jati_ids(analysis) -> List[str]:
    ids: List[str] = []
    for rule in JATI_SPECS:
        slices = _split_analysis_by_matras(analysis, rule.quarter_matras)
        if not slices or len(slices) != 4:
            continue
        halves = [list(slices[0]) + list(slices[1]), list(slices[2]) + list(slices[3])]
        distance = sum(
            _arya_problems(half, rule.half_kinds[index]) for index, half in enumerate(halves)
        )
        if distance == 0:
            ids.append(rule.id)
    return ids


def _independently_matched_partial_ids(analysis) -> List[str]:
    if not analysis.padas or len(analysis.padas) > 2:
        return []
    ids: List[str] = []
    for spec in CLASSICAL_VARNA_METERS:
        if spec.kind != "sama-vrtta" or len(spec.pada_patterns) != 1:
            continue
        pattern = spec.pada_patterns[0]
        if all(
            len(unit.syllables) == len(pattern)
            and _slice_matches_rule(unit.syllables, pattern, spec.terminal_policy)
            for unit in analysis.padas
        ):
            ids.append(spec.id)
    return ids


def _independently_matched_vedic_ids(analysis) -> List[str]:
    ids: List[str] = []
    for rule in VEDIC_SPECS:
        base = rule.pada_lengths
        if _split_analysis_by_lengths(analysis, base):
            ids.append(rule.id)
            continue
        for index in range(len(base)):
            for delta, subtype in ((-1, "nicrt"), (1, "bhurik")):
                lengths = list(base)
                lengths[index] += delta
                if _split_analysis_by_lengths(analysis, lengths):
                    ids.append(f"{rule.id}-{subtype}-pada-{index + 1}")
    return ids


def _independent_classical_requirements(analysis) -> Tuple[List[str], bool]:
    fixed = _independently_matched_fixed_ids(analysis)
    upajati = _independently_matched_upajati_ids(analysis)
    jati = _independently_matched_jati_ids(analysis)
    sloka_required, sloka_exact = _independent_sloka(analysis)
    ids = [*fixed, *upajati, *jati, *(["anustubh-sloka"] if sloka_required else [])]
    return ids, bool(fixed or upajati or jati or sloka_exact)


def _require_candidate_ids(
    state: _CheckState, actual_ids, expected_ids: Sequence[str]
) -> None:
    for expected_id in expected_ids:
        _check(
            state,
            expected_id in actual_ids,
            "EXPECTED_CANDIDATE_OMITTED",
            f"An independently matched rule ({expected_id}) is missing from the "
            "candidate list.",
            expected_id,
        )


def _candidate_completeness_checks(
    state: _CheckState,
    analysis,
    identification: SanskritMeterIdentification,
    expected_tradition: str,
) -> None:
    actual_ids = {candidate.id for candidate in identification.candidates}
    classical_ids, classical_has_exact = _independent_classical_requirements(analysis)
    vedic_ids = _independently_matched_vedic_ids(analysis)
    if expected_tradition != "vedic":
        _require_candidate_ids(state, actual_ids, classical_ids)
    if expected_tradition == "vedic" or (
        expected_tradition == "auto" and not classical_has_exact
    ):
        _require_candidate_ids(state, actual_ids, vedic_ids)
    maker_would_try_partial = (
        expected_tradition != "vedic"
        and not classical_ids
        and (expected_tradition == "classical" or not vedic_ids)
    )
    if maker_would_try_partial:
        _require_candidate_ids(state, actual_ids, _independently_matched_partial_ids(analysis))


def _candidate_list_checks(
    state: _CheckState, analysis, identification: SanskritMeterIdentification
) -> None:
    ids = set()
    for candidate in identification.candidates:
        _check(
            state,
            candidate.id not in ids,
            "DUPLICATE_CANDIDATE_ID",
            f"Candidate id {candidate.id} is repeated.",
            candidate.id,
        )
        ids.add(candidate.id)
        _candidate_checks(state, analysis, candidate)
    for index, candidate in enumerate(identification.candidates[1:]):
        _check(
            state,
            _key(identification.candidates[index]) <= _key(candidate),
            "CANDIDATES_OUT_OF_ORDER",
            "Candidates are not in deterministic evidence order.",
            candidate.id,
        )


def _primary_matches(identification: SanskritMeterIdentification) -> bool:
    if not identification.candidates:
        return identification.primary is None
    return identification.primary is identification.candidates[0] or (
        identification.primary == identification.candidates[0]
    )


def _expected_status(candidates: Sequence[SanskritMeterCandidate]) -> str:
    if not candidates:
        return "unidentified"
    first = candidates[0]
    if first.match_type == "near":
        return "unidentified"
    if first.match_type == "partial":
        return "insufficient-evidence"
    tied = [c for c in candidates if _same_evidence_rank(c, first)]
    if len(tied) > 1:
        return "ambiguous"
    complete_exact_rule = first.match_type == "exact" and first.evidence in (
        "full-verse",
        "extended-stanza",
    )
    return (
        "identified"
        if complete_exact_rule and first.authority.coverage == "dual-root-bhasya"
        else "provisional"
    )


def verify_sanskrit_meter_identification(
    analysis, identification: SanskritMeterIdentification, expected_tradition: str
) -> SanskritMeterVerification:
    """
    Rechecks a meter verdict without calling the maker's matching or ranking
    helpers. A failed checker means the verdict is not safe to present as an
    identification, even if the original syllable analysis remains valid.
    """
    state = _CheckState()
    if not _can_verify(analysis):
        return SanskritMeterVerification(
            status="not-run", checks=0, method=METHOD, issues=[]
        )

    _check(
        state,
        _unit_patterns_match(analysis, identification),
        "UNIT_PATTERNS_CHANGED",
        "The identification's input patterns differ from the verified syllable analysis.",
    )
    _check(
        state,
        identification.requested_tradition == expected_tradition,
        "REQUESTED_TRADITION_CHANGED",
        "The identification's recorded tradition differs from the checker input.",
    )
    _candidate_completeness_checks(state, analysis, identification, expected_tradition)
    _candidate_list_checks(state, analysis, identification)
    _check(
        state,
        _primary_matches(identification),
        "PRIMARY_MISMATCH",
        "The primary candidate is not the first ranked candidate.",
    )
    status = _expected_status(identification.candidates)
    _check(
        state,
        identification.status == status,
        "STATUS_MISMATCH",
        f"Identification status {identification.status} should be {status}.",
    )
    _check(
        state,
        identification.identified == (status == "identified"),
        "IDENTIFIED_FLAG_MISMATCH",
        "The identified flag disagrees with the recomputed status.",
    )
    return SanskritMeterVerification(
        status="verified" if not state.issues else "failed",
        checks=state.checks,
        method=METHOD,
        issues=state.issues,
    )
