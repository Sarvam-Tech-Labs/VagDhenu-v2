# -*- coding: utf-8 -*-
"""
Meter identification and verifier tests — ported from Prasadam's
lib/__tests__/sanskrit-meter-identification.test.ts.

Includes the catalog round-trip: every one of the 128 catalog rows is written
out as a scannable verse and must be recovered by the identifier with its
checker passing. That single test exercises the syllabifier, the analyser, the
maker, and both verifiers against the whole catalog.
"""

import copy
import unittest

from src.chandas.authorities import authority_evidence_for
from src.chandas.catalog import (
    CLASSICAL_VARNA_METERS,
    ClassicalVarnaMeterSpec,
    meter_by_id,
    validate_chandas_catalog,
)
from src.chandas.identification import identify_sanskrit_meter
from src.chandas.meter_verifier import verify_sanskrit_meter_identification
from src.chandas.types import SanskritMeterMismatch, SanskritMeterSource
from src.chandas.verse_analysis import analyze_sanskrit_verse

BG_15_15 = "\n".join(
    [
        "sarvasya cāhaṁ hṛdi sanniviṣṭo",
        "mattaḥ smṛtir jñānam apohanaṁ ca",
        "vedaiś ca sarvair aham eva vedyo",
        "vedāntakṛd vedavid eva cāham",
    ]
)

BG_15_15_DEVA = "\n".join(
    [
        "सर्वस्य चाहं हृदि सन्निविष्टो",
        "मत्तः स्मृतिर्ज्ञानमपोहनं च ।",
        "वेदैश्च सर्वैरहमेव वेद्यो",
        "वेदान्तकृद्वेदविदेव चाहम् ॥ १५ ॥",
    ]
)

BG_2_47 = (
    "karmaṇy evādhikāras te\nmā phaleṣu kadācana\n"
    "mā karmaphalahetur bhūr\nmā te saṅgo ’stv akarmaṇi"
)

SANKHYA_KARIKA_1 = (
    "duḥkhatrayābhighātāj jijñāsā tadapaghātake hetau\n"
    "dṛṣṭe sāpārthā cen naikāntātyantato ’bhāvāt"
)

GAYATRI = "tat savitur vareṇyaṃ\nbhargo devasya dhīmahi\ndhiyo yo naḥ pracodayāt"

MEGHADUTA_1 = "\n".join(
    [
        "kaścit kāntāvirahaguruṇā svādhikārapramattaḥ "
        "śāpenāstaṃgamitamahimā varṣabhogyeṇa bhartuḥ",
        "yakṣaś cakre janakatanayāsnānapuṇyodakeṣu "
        "snigdhacchāyātaruṣu vasatiṃ rāmagiryāśrameṣu",
    ]
)


def analyze(text):
    result = analyze_sanskrit_verse(text, script="iast", boundary_mode="lines")
    assert result.ok, "; ".join(item.message for item in result.diagnostics)
    assert result.verification.status == "verified"
    return result


def written_pattern(pattern: str) -> str:
    """Renders a G/L pattern as a scannable line of kā / ka syllables."""
    return " ".join("kā" if weight == "G" else "ka" for weight in pattern)


def four_pada_patterns(spec: ClassicalVarnaMeterSpec):
    if len(spec.pada_patterns) == 1:
        return [spec.pada_patterns[0]] * 4
    if len(spec.pada_patterns) == 2:
        return [
            spec.pada_patterns[0],
            spec.pada_patterns[1],
            spec.pada_patterns[0],
            spec.pada_patterns[1],
        ]
    return list(spec.pada_patterns)


def issue_codes(verification):
    return [issue.code for issue in verification.issues]


class TestClassicalChandasCatalog(unittest.TestCase):
    def test_has_validated_provenance_and_promised_coverage(self):
        validation = validate_chandas_catalog()
        self.assertTrue(validation.valid)
        self.assertEqual(validation.errors, ())
        self.assertEqual(len(CLASSICAL_VARNA_METERS), 128)
        counts = {
            kind: sum(1 for m in CLASSICAL_VARNA_METERS if m.kind == kind)
            for kind in ("sama-vrtta", "ardhasama-vrtta", "visama-vrtta", "dandaka")
        }
        self.assertEqual(
            counts,
            {
                "sama-vrtta": 94,
                "ardhasama-vrtta": 13,
                "visama-vrtta": 11,
                "dandaka": 10,
            },
        )

    def test_can_recover_every_catalog_row_from_its_scanned_form(self):
        failures = []
        for spec in CLASSICAL_VARNA_METERS:
            verse = "\n".join(written_pattern(p) for p in four_pada_patterns(spec))
            analysis = analyze(verse)
            result = identify_sanskrit_meter(analysis, tradition="classical")
            own = next(
                (
                    c
                    for c in result.candidates
                    if c.id == spec.id and c.match_type == "exact"
                ),
                None,
            )
            if not own or result.verification.status != "verified":
                failures.append(
                    f"{spec.id}: {result.status}/{result.verification.status}; "
                    + ",".join(issue_codes(result.verification))
                )
        self.assertEqual(failures, [])


class TestIdentifySanskritMeter(unittest.TestCase):
    def test_classifies_bg_15_15_with_paired_witnesses(self):
        analysis = analyze(BG_15_15)
        result = identify_sanskrit_meter(analysis, tradition="auto")

        self.assertEqual(result.status, "identified")
        self.assertTrue(result.identified)
        self.assertEqual([len(p.syllables) for p in analysis.padas], [11, 11, 11, 11])

        primary = result.primary
        self.assertEqual(primary.id, "indravajra")
        self.assertEqual(primary.name, "indravajrā")
        self.assertEqual(primary.kind, "sama-vrtta")
        self.assertEqual(primary.match_type, "exact")
        self.assertEqual(primary.distance, 0)
        self.assertEqual(primary.terminal_policy, "short-to-guru")

        classification = primary.classification
        self.assertEqual(classification.domain_label, "laukika / classical chandas")
        self.assertEqual(classification.system, "varna-vrtta")
        self.assertEqual(classification.count_class.name, "triṣṭubh")
        self.assertEqual(classification.count_class.syllables_per_pada, 11)
        self.assertEqual(classification.count_class.scope, "classical-akshara")
        self.assertEqual(
            classification.symmetry, "sama-vṛtta — all four pādas use one rule"
        )
        self.assertEqual(classification.specific_form, "indravajrā")
        self.assertEqual(classification.gana_formula, "ta · ta · ja · G · G")

        self.assertEqual(primary.authority.coverage, "dual-root-bhasya")
        self.assertEqual(
            [p.observed_pattern for p in primary.padas],
            ["GGLGGLLGLGG", "GGLGGLLGLGL", "GGLGGLLGLGG", "GGLGGLLGLGG"],
        )
        self.assertEqual(
            [p.final_anceps_used for p in primary.padas], [False, True, False, False]
        )
        self.assertEqual(len(primary.authority.pairs), 2)
        self.assertEqual(
            [pair.tradition for pair in primary.authority.pairs],
            ["general-chandas", "gaudiya"],
        )
        self.assertTrue(
            all(
                pair.root.role == "root" and pair.bhasya.role == "bhasya"
                for pair in primary.authority.pairs
            )
        )
        self.assertFalse(any(c.id == "vedic-tristubh" for c in result.candidates))
        self.assertFalse(any(c.id == "upajati-tristubh" for c in result.candidates))
        self.assertEqual(result.verification.status, "verified")

    def test_gives_the_same_bg_15_15_verdict_from_devanagari(self):
        analysis = analyze_sanskrit_verse(
            BG_15_15_DEVA, script="devanagari", boundary_mode="lines"
        )
        self.assertTrue(
            analysis.ok, "; ".join(item.message for item in analysis.diagnostics)
        )
        result = identify_sanskrit_meter(analysis, tradition="auto")
        self.assertEqual(result.primary.id, "indravajra")
        self.assertEqual(result.primary.match_type, "exact")
        self.assertEqual(
            [p.observed_pattern for p in result.primary.padas],
            ["GGLGGLLGLGG", "GGLGGLLGLGL", "GGLGGLLGLGG", "GGLGGLLGLGG"],
        )
        self.assertEqual(result.verification.status, "verified")

    def test_identifies_mandakranta_and_infers_padas_inside_half_lines(self):
        analysis = analyze(MEGHADUTA_1)
        result = identify_sanskrit_meter(analysis, tradition="classical")

        self.assertEqual(result.status, "provisional")
        self.assertFalse(result.identified)
        self.assertEqual(result.primary.id, "mandakranta")
        self.assertEqual(result.primary.name, "mandākrāntā")
        self.assertEqual(result.primary.match_type, "exact")
        self.assertEqual(result.primary.boundary_transformations, 2)
        self.assertEqual(result.primary.authority.coverage, "catalog-only")
        self.assertEqual(result.verification.status, "verified")
        self.assertEqual(result.verification.issues, [])
        self.assertEqual(len(result.primary.padas), 4)
        self.assertEqual(
            [p.observed_pattern for p in result.primary.padas],
            [
                "GGGGLLLLLGGLGGLGG",
                "GGGGLLLLLGGLGGLGG",
                "GGGGLLLLLGGLGGLGG",
                "GGGGLLLLLGGLGGLGL",
            ],
        )

    def test_recognizes_pathya_anustubh_by_cadence(self):
        result = identify_sanskrit_meter(analyze(BG_2_47), tradition="classical")
        self.assertEqual(result.primary.id, "anustubh-sloka")
        self.assertEqual(result.primary.name, "anuṣṭubh (śloka)")
        self.assertEqual(result.primary.match_type, "exact")
        self.assertEqual(
            list(result.primary.subtypes),
            ["pathyā", "even-pāda cadence", "pathyā", "even-pāda cadence"],
        )
        self.assertEqual(result.primary.authority.coverage, "catalog-only")
        self.assertEqual(result.status, "provisional")
        self.assertFalse(result.identified)
        self.assertEqual(result.verification.status, "verified")

    def test_labels_broken_cadence_only_class_compatible(self):
        verse = "\n".join([written_pattern("LLLLLLLL")] * 4)
        result = identify_sanskrit_meter(analyze(verse), tradition="classical")
        self.assertEqual(result.primary.id, "anustubh-sloka")
        self.assertEqual(result.primary.match_type, "class-compatible")
        self.assertEqual(result.status, "provisional")
        self.assertFalse(result.identified)
        self.assertGreater(result.primary.distance, 0)
        self.assertIn("cadence rules failed", " ".join(result.primary.notes))

    def test_identifies_arya_with_quarter_matras(self):
        result = identify_sanskrit_meter(
            analyze(SANKHYA_KARIKA_1), tradition="classical"
        )
        self.assertEqual(result.primary.id, "arya")
        self.assertEqual(result.primary.name, "āryā")
        self.assertEqual(result.primary.kind, "jati")
        self.assertEqual(result.primary.match_type, "exact")
        self.assertEqual(
            list(result.primary.subtypes),
            ["12 mātrās", "18 mātrās", "12 mātrās", "15 mātrās"],
        )
        self.assertEqual(result.primary.authority.coverage, "catalog-only")
        self.assertEqual(result.status, "provisional")
        self.assertEqual(result.verification.status, "verified")

    def test_reports_nicrt_gayatri_only_as_vedic_count_class(self):
        result = identify_sanskrit_meter(analyze(GAYATRI), tradition="vedic")
        self.assertEqual(result.primary.id, "vedic-gayatri-nicrt-pada-1")
        self.assertEqual(result.primary.name, "nicṛt gāyatrī")
        self.assertEqual(result.primary.kind, "vedic")
        self.assertEqual(result.primary.match_type, "class-compatible")
        self.assertEqual(result.primary.evidence, "count-only")
        self.assertEqual(result.primary.authority.coverage, "secondary-only")
        self.assertEqual(result.status, "provisional")
        self.assertFalse(result.identified)
        self.assertIn(
            "not a classical fixed-pattern verdict", " ".join(result.primary.notes)
        )
        self.assertEqual(result.verification.status, "verified")

    def test_recognizes_a_non_alternating_upajati_mixture(self):
        indravajra = meter_by_id("indravajra")
        upendravajra = meter_by_id("upendravajra")
        patterns = [
            indravajra.pada_patterns[0],
            indravajra.pada_patterns[0],
            upendravajra.pada_patterns[0],
            indravajra.pada_patterns[0],
        ]
        result = identify_sanskrit_meter(
            analyze("\n".join(written_pattern(p) for p in patterns)),
            tradition="classical",
        )
        self.assertEqual(result.primary.id, "upajati-tristubh")
        self.assertEqual(result.primary.kind, "upajati")
        self.assertEqual(result.primary.match_type, "exact")
        self.assertEqual(result.status, "identified")
        self.assertTrue(result.identified)
        self.assertEqual(
            list(result.primary.subtypes),
            ["indravajrā", "indravajrā", "upendravajrā", "indravajrā"],
        )

    def test_does_not_guess_between_akhyanaki_and_the_upajati_family(self):
        spec = meter_by_id("akhyanaki")
        result = identify_sanskrit_meter(
            analyze("\n".join(written_pattern(p) for p in four_pada_patterns(spec))),
            tradition="classical",
        )
        self.assertEqual(result.status, "ambiguous")
        self.assertFalse(result.identified)
        self.assertEqual(
            [c.id for c in result.candidates[:2]], ["akhyanaki", "upajati-tristubh"]
        )
        self.assertIn("no catalog-order guess", " ".join(result.diagnostics))

    def test_keeps_a_one_pada_match_as_insufficient_evidence(self):
        spec = meter_by_id("mandakranta")
        result = identify_sanskrit_meter(
            analyze(written_pattern(spec.pada_patterns[0])), tradition="classical"
        )
        self.assertEqual(result.status, "insufficient-evidence")
        self.assertFalse(result.identified)
        self.assertEqual(result.primary.id, "mandakranta")
        self.assertEqual(result.primary.match_type, "partial")
        self.assertEqual(result.primary.evidence, "fragment")

    def test_shows_a_one_weight_error_only_as_a_near_diagnostic(self):
        spec = meter_by_id("mandakranta")
        base = spec.pada_patterns[0]
        changed = ("L" if base[0] == "G" else "G") + base[1:]
        result = identify_sanskrit_meter(
            analyze("\n".join(written_pattern(p) for p in [changed, base, base, base])),
            tradition="classical",
            include_near=True,
        )
        self.assertEqual(result.status, "unidentified")
        self.assertFalse(result.identified)
        self.assertTrue(
            any(
                c.id == "mandakranta" and c.match_type == "near" and c.distance == 1
                for c in result.candidates
            )
        )


class TestMeterVerifierRejectsForgeries(unittest.TestCase):
    """The checker must catch tampering without consulting the maker."""

    def test_cannot_promote_an_incompletely_sourced_exact_match(self):
        spec = meter_by_id("mandakranta")
        analysis = analyze(
            "\n".join(written_pattern(p) for p in four_pada_patterns(spec))
        )
        made = identify_sanskrit_meter(analysis, tradition="classical")
        self.assertEqual(made.status, "provisional")
        self.assertFalse(made.identified)

        forged = copy.deepcopy(made)
        forged.status = "identified"
        forged.identified = True
        checked = verify_sanskrit_meter_identification(
            analysis, forged, made.requested_tradition
        )
        self.assertEqual(checked.status, "failed")
        self.assertIn("STATUS_MISMATCH", issue_codes(checked))
        self.assertIn("IDENTIFIED_FLAG_MISMATCH", issue_codes(checked))

    def test_detects_tampering_with_an_observed_pattern(self):
        analysis = analyze(BG_2_47)
        made = identify_sanskrit_meter(analysis, tradition="classical")
        changed = copy.deepcopy(made)
        changed.candidates[0].padas[0].observed_pattern = "GGGGGGGG"
        changed.primary = changed.candidates[0]
        checked = verify_sanskrit_meter_identification(
            analysis, changed, made.requested_tradition
        )
        self.assertEqual(checked.status, "failed")
        self.assertIn("OBSERVED_PATTERN_CHANGED", issue_codes(checked))

    def test_rejects_forged_catalog_targets_and_paired_witness_records(self):
        analysis = analyze(BG_15_15)
        made = identify_sanskrit_meter(analysis, tradition="auto")
        changed = copy.deepcopy(made)
        changed.candidates[0].padas[0].expected_pattern = (
            "L" + changed.candidates[0].padas[0].observed_pattern[1:]
        )
        pair = changed.candidates[0].authority.pairs[0]
        forged_root = type(pair.root)(
            role=pair.root.role,
            author=pair.root.author,
            work=pair.root.work,
            locator="forged locus",
            statement=pair.root.statement,
            supports=pair.root.supports,
            url=pair.root.url,
            statement_language=pair.root.statement_language,
        )
        forged_pair = type(pair)(
            id=pair.id,
            tradition=pair.tradition,
            label=pair.label,
            root=forged_root,
            bhasya=pair.bhasya,
            note=pair.note,
        )
        changed.candidates[0].authority = type(changed.candidates[0].authority)(
            coverage=changed.candidates[0].authority.coverage,
            pairs=(forged_pair,) + tuple(changed.candidates[0].authority.pairs[1:]),
            note=changed.candidates[0].authority.note,
        )
        changed.primary = changed.candidates[0]
        checked = verify_sanskrit_meter_identification(
            analysis, changed, made.requested_tradition
        )
        self.assertEqual(checked.status, "failed")
        self.assertIn("CANONICAL_PATTERN_CHANGED", issue_codes(checked))
        self.assertIn("AUTHORITY_REGISTRY_CHANGED", issue_codes(checked))

    def test_rejects_forged_classification_fields(self):
        analysis = analyze(BG_15_15)
        made = identify_sanskrit_meter(analysis, tradition="auto")
        forgery = copy.deepcopy(made)
        cls = forgery.candidates[0].classification
        forgery.candidates[0].classification = type(cls)(
            domain_label=cls.domain_label,
            system=cls.system,
            system_label=cls.system_label,
            specific_form=cls.specific_form,
            cautions=cls.cautions,
            count_class=type(cls.count_class)(
                name="gāyatrī",
                syllables_per_pada=cls.count_class.syllables_per_pada,
                scope=cls.count_class.scope,
            ),
            symmetry=cls.symmetry,
            gana_formula=cls.gana_formula,
            yati_statement=cls.yati_statement,
        )
        forgery.primary = forgery.candidates[0]
        checked = verify_sanskrit_meter_identification(
            analysis, forgery, made.requested_tradition
        )
        self.assertEqual(checked.status, "failed")
        self.assertIn("CLASSIFICATION_CHANGED", issue_codes(checked))

    def test_rejects_a_detached_primary_object(self):
        analysis = analyze(BG_15_15)
        made = identify_sanskrit_meter(analysis, tradition="auto")
        forgery = copy.deepcopy(made)
        forgery.primary = copy.deepcopy(forgery.candidates[0])
        forgery.primary.name = "forged meter"
        checked = verify_sanskrit_meter_identification(
            analysis, forgery, made.requested_tradition
        )
        self.assertEqual(checked.status, "failed")
        self.assertIn("PRIMARY_MISMATCH", issue_codes(checked))

    def test_cannot_promote_a_fragment_into_a_full_identification(self):
        spec = meter_by_id("mandakranta")
        analysis = analyze(written_pattern(spec.pada_patterns[0]))
        made = identify_sanskrit_meter(analysis, tradition="classical")
        forged = copy.deepcopy(made)
        forged.candidates[0].match_type = "exact"
        forged.candidates[0].evidence = "full-verse"
        forged.primary = forged.candidates[0]
        forged.status = "identified"
        forged.identified = True
        checked = verify_sanskrit_meter_identification(
            analysis, forged, made.requested_tradition
        )
        self.assertEqual(checked.status, "failed")
        self.assertIn("MATCH_TYPE_MISMATCH", issue_codes(checked))
        self.assertIn("FIXED_EVIDENCE_MISMATCH", issue_codes(checked))

    def test_cannot_suppress_an_independently_matched_exact_result(self):
        analysis = analyze(BG_15_15)
        made = identify_sanskrit_meter(analysis, tradition="auto")
        forged = copy.deepcopy(made)
        forged.candidates = []
        forged.primary = None
        forged.status = "unidentified"
        forged.identified = False
        checked = verify_sanskrit_meter_identification(
            analysis, forged, made.requested_tradition
        )
        self.assertEqual(checked.status, "failed")
        self.assertIn("EXPECTED_CANDIDATE_OMITTED", issue_codes(checked))

    def test_rejects_forged_display_notes_yati_template_and_subtypes(self):
        analysis = analyze(BG_15_15)
        made = identify_sanskrit_meter(analysis, tradition="auto")
        forged = copy.deepcopy(made)
        forged.candidates[0].notes = ("forged claim",)
        forged.candidates[0].yati = (5,)
        forged.candidates[0].template = "forged template"
        forged.candidates[0].subtypes = ("forged subtype",)
        forged.primary = forged.candidates[0]
        checked = verify_sanskrit_meter_identification(
            analysis, forged, made.requested_tradition
        )
        self.assertEqual(checked.status, "failed")
        for code in (
            "FIXED_NOTES_CHANGED",
            "YATI_CHANGED",
            "TEMPLATE_CHANGED",
            "FIXED_SUBTYPES_CHANGED",
        ):
            self.assertIn(code, issue_codes(checked))

    def test_cannot_suppress_sloka_jati_upajati_or_vedic_results(self):
        indravajra = meter_by_id("indravajra")
        upendravajra = meter_by_id("upendravajra")
        upajati_verse = "\n".join(
            written_pattern(p)
            for p in [
                indravajra.pada_patterns[0],
                indravajra.pada_patterns[0],
                upendravajra.pada_patterns[0],
                indravajra.pada_patterns[0],
            ]
        )
        cases = [
            (analyze(BG_2_47), "classical"),
            (analyze(SANKHYA_KARIKA_1), "classical"),
            (analyze(upajati_verse), "classical"),
            (analyze(GAYATRI), "vedic"),
        ]
        for analysis, tradition in cases:
            made = identify_sanskrit_meter(analysis, tradition=tradition)
            forged = copy.deepcopy(made)
            forged.candidates = []
            forged.primary = None
            forged.status = "unidentified"
            forged.identified = False
            checked = verify_sanskrit_meter_identification(
                analysis, forged, made.requested_tradition
            )
            self.assertEqual(checked.status, "failed")
            self.assertIn("EXPECTED_CANDIDATE_OMITTED", issue_codes(checked))

    def test_rejects_identity_and_provenance_forgeries_per_rule_family(self):
        indravajra = meter_by_id("indravajra")
        upendravajra = meter_by_id("upendravajra")
        upajati_verse = "\n".join(
            written_pattern(p)
            for p in [
                indravajra.pada_patterns[0],
                indravajra.pada_patterns[0],
                upendravajra.pada_patterns[0],
                indravajra.pada_patterns[0],
            ]
        )
        cases = [
            ("sloka", analyze(BG_2_47), "classical"),
            ("jati", analyze(SANKHYA_KARIKA_1), "classical"),
            ("upajati", analyze(upajati_verse), "classical"),
            ("vedic", analyze(GAYATRI), "vedic"),
        ]
        for family, analysis, tradition in cases:
            made = identify_sanskrit_meter(analysis, tradition=tradition)
            forged = copy.deepcopy(made)
            candidate = forged.candidates[0]
            candidate.name = "forged meter"
            candidate.aliases = ("forged alias",)
            cls = candidate.classification
            candidate.classification = type(cls)(
                domain_label=cls.domain_label,
                system=cls.system,
                system_label=cls.system_label,
                specific_form="forged meter",
                cautions=cls.cautions,
                count_class=cls.count_class,
                symmetry=cls.symmetry,
                gana_formula=cls.gana_formula,
                yati_statement=cls.yati_statement,
            )
            candidate.source = SanskritMeterSource(
                work="Forged Root", locator="9.99", url="https://evil.example"
            )
            candidate.authority = authority_evidence_for(
                candidate.id, candidate.tradition, candidate.source
            )
            if family == "upajati":
                candidate.terminal_policy = "fixed"
            else:
                candidate.notes = ("forged note",)
                candidate.yati = (3,)
                candidate.template = "forged template"
                candidate.subtypes = ("forged subtype",)
                candidate.padas[0].expected_pattern = "GGGGGGGG"
                candidate.padas[0].mismatches = [
                    SanskritMeterMismatch(
                        pada_index=0,
                        position=0,
                        expected="G",
                        observed="L",
                        syllable_index=0,
                    )
                ]
                candidate.padas[0].final_anceps_used = True
            forged.primary = candidate

            checked = verify_sanskrit_meter_identification(
                analysis, forged, made.requested_tradition
            )
            self.assertEqual(checked.status, "failed", family)
            codes = issue_codes(checked)
            self.assertIn("RULE_FAMILY_IDENTITY_CHANGED", codes, family)
            self.assertIn("RULE_FAMILY_PROVENANCE_CHANGED", codes, family)
            if family == "upajati":
                self.assertIn("UPAJATI_TERMINAL_POLICY_CHANGED", codes, family)
            else:
                self.assertIn("RULE_FAMILY_DISPLAY_RULE_CHANGED", codes, family)
                self.assertIn("RULE_FAMILY_PADA_EVIDENCE_CHANGED", codes, family)


if __name__ == "__main__":
    unittest.main()
