# -*- coding: utf-8 -*-
"""
Core chandas engine tests — ported from Prasadam's lib/__tests__/chandas.test.ts.

These are the acceptance harness for the Python port: the same verses, the
same expected scansions, so a divergence between the two implementations shows
up here rather than in the UI.
"""

import unittest

from src.chandas.core import (
    METER_CATALOG,
    MeterSpec,
    annotate_deva_word,
    annotate_iast_line,
    classify_aksara,
    classify_aksara_deva,
    classify_aksara_iast,
    AksaraContext,
    ChandasError,
    identify_meter,
    meter_template,
    split_deva_word_head,
    split_iast_word_head,
    syllabify_iast_line,
    yati_word_boundary,
)

# SB 1.1.1, first metrical pāda — the śārdūlavikrīḍita reference line.
PADA = "janmādy asya yato ’nvayād itarataś cārtheṣv abhijñaḥ svarāṭ"


def weights(aksaras):
    return "".join("G" if a.weight == "guru" else "L" for a in aksaras)


def texts(aksaras):
    return "·".join(a.text for a in aksaras)


class TestSyllabifyIastLine(unittest.TestCase):
    def test_scans_sb_111_first_pada_as_19_sardula_syllables(self):
        aksaras = syllabify_iast_line(PADA)
        self.assertEqual(len(aksaras), 19)
        self.assertEqual(weights(aksaras), "GGGLLGLGLLLGGGLGGLG")

    def test_crosses_word_boundaries(self):
        aksaras = syllabify_iast_line("yat sūrayaḥ")
        self.assertEqual(texts(aksaras), "ya·tsū·ra·yaḥ")
        # ya heavy by position, yaḥ by visarga
        self.assertEqual(weights(aksaras), "GGLG")

    def test_treats_diphthongs_as_long(self):
        aksaras = syllabify_iast_line("naimiṣe")
        self.assertEqual(texts(aksaras), "nai·mi·ṣe")
        self.assertEqual(weights(aksaras), "GLG")

    def test_anusvara_closes_a_syllable_heavy(self):
        aksaras = syllabify_iast_line("satyaṁ paraṁ dhīmahi")
        self.assertEqual(texts(aksaras), "sa·tyaṁ·pa·raṁ·dhī·ma·hi")
        self.assertEqual(weights(aksaras), "GGLGGLL")

    def test_attaches_line_final_consonants_and_flags_anceps(self):
        aksaras = syllabify_iast_line(PADA)
        self.assertEqual(aksaras[-1].text, "rāṭ")
        self.assertTrue(aksaras[-1].anceps)
        self.assertTrue(all(not a.anceps for a in aksaras[:-1]))

    def test_hyphens_are_transparent(self):
        self.assertEqual(
            texts(syllabify_iast_line("tejo-vāri-mṛdāṁ")), "te·jo·vā·ri·mṛ·dāṁ"
        )

    def test_throws_on_unknown_characters(self):
        with self.assertRaises(ChandasError) as ctx:
            syllabify_iast_line("janmādy 2")
        self.assertIn('unknown character "2"', str(ctx.exception))

    def test_jihvamuliya_and_upadhmaniya_are_visarga_class(self):
        self.assertEqual(
            [a.weight for a in syllabify_iast_line("taẖ karoti")],
            ["guru", "laghu", "guru", "laghu"],
        )
        self.assertEqual(syllabify_iast_line("taḫ pibati")[0].weight, "guru")


class TestSplitIastWordHead(unittest.TestCase):
    def test_takes_onset_plus_first_vowel_plus_mark(self):
        self.assertEqual(split_iast_word_head("janmādy"), ("ja", "nmādy"))
        self.assertEqual(split_iast_word_head("dhīmahi"), ("dhī", "mahi"))
        self.assertEqual(split_iast_word_head("satyaṁ"), ("sa", "tyaṁ"))
        self.assertEqual(split_iast_word_head("oṁ"), ("oṁ", ""))

    def test_keeps_leading_avagraha_with_head(self):
        self.assertEqual(split_iast_word_head("’nvayād"), ("’nva", "yād"))

    def test_returns_vowelless_token_whole(self):
        self.assertEqual(split_iast_word_head("t"), ("t", ""))


class TestSplitDevaWordHead(unittest.TestCase):
    def test_splits_after_first_cluster_never_mid_conjunct(self):
        self.assertEqual(split_deva_word_head("जन्माद्य्"), ("ज", "न्माद्य्"))
        self.assertEqual(split_deva_word_head("धीमहि"), ("धी", "महि"))
        self.assertEqual(split_deva_word_head("श्रीमद्"), ("श्री", "मद्"))
        self.assertEqual(split_deva_word_head("अस्य"), ("अ", "स्य"))

    def test_keeps_single_cluster_word_whole(self):
        self.assertEqual(split_deva_word_head("ॐ"), ("ॐ", ""))
        self.assertEqual(split_deva_word_head("च"), ("च", ""))

    def test_carries_marks_with_owning_cluster(self):
        self.assertEqual(split_deva_word_head("तं"), ("तं", ""))
        self.assertEqual(split_deva_word_head("सत्यं"), ("स", "त्यं"))
        self.assertEqual(split_deva_word_head("नमः"), ("न", "मः"))


class TestAnnotateIastLine(unittest.TestCase):
    def test_pieces_concatenate_exactly_to_their_words(self):
        for line in (PADA, "tejo-vāri-mṛdāṁ yathā vinimayo yatra tri-sargo ’mṛṣā"):
            words = [w for w in line.split() if w]
            annotated = annotate_iast_line(line)
            self.assertEqual(len(annotated), len(words))
            for wi, word in enumerate(annotated):
                self.assertEqual("".join(p.text for p in word.pieces), words[wi])

    def test_marks_one_piece_per_syllable_with_agreeing_weights(self):
        annotated = annotate_iast_line(PADA)
        marked = [p for word in annotated for p in word.pieces if p.weight]
        scanned = syllabify_iast_line(PADA)
        self.assertEqual(len(marked), len(scanned))
        for i, piece in enumerate(marked):
            self.assertEqual(piece.weight, scanned[i].weight)
        self.assertTrue(marked[-1].anceps)

    def test_cross_word_syllable_marks_the_vowel_bearing_piece(self):
        yat, surayah = annotate_iast_line("yat sūrayaḥ")
        self.assertEqual([p.text for p in yat.pieces], ["ya", "t"])
        self.assertEqual(yat.pieces[0].weight, "guru")
        self.assertIsNone(yat.pieces[1].weight)
        self.assertEqual(surayah.pieces[0].text, "sū")
        self.assertEqual(surayah.pieces[0].weight, "guru")

    def test_keeps_leading_avagraha_attached_to_first_piece(self):
        words = annotate_iast_line("yato ’nvayād")
        self.assertEqual(words[1].pieces[0].text, "’nva")
        self.assertEqual(words[1].pieces[0].text, split_iast_word_head("’nvayād")[0])


class TestYatiWordBoundary(unittest.TestCase):
    def test_finds_sardula_12_plus_7_break(self):
        self.assertEqual(yati_word_boundary(PADA, 12), 4)

    def test_returns_none_when_the_yati_splits_a_word(self):
        self.assertIsNone(yati_word_boundary(PADA, 3))

    def test_returns_none_when_the_count_lands_at_line_end(self):
        self.assertIsNone(yati_word_boundary("oṁ namo bhagavate vāsudevāya", 12))


class TestMeterTemplate(unittest.TestCase):
    def test_renders_sardulavikridita_with_yati_gap_and_anceps_star(self):
        spec = next(s for s in METER_CATALOG if s.name == "śārdūlavikrīḍita")
        self.assertEqual(meter_template(spec), "——— ◡◡— ◡—◡ ◡◡— ‖ ——◡ ——◡ —*")

    def test_renders_drutavilambita_without_a_yati_gap(self):
        spec = next(s for s in METER_CATALOG if s.name == "drutavilambita")
        self.assertEqual(meter_template(spec), "◡◡◡ —◡◡ —◡◡ —◡—*")

    def test_returns_none_for_count_only_meters(self):
        self.assertIsNone(meter_template(MeterSpec(name="anuṣṭubh", syllables=8)))


class TestAnnotateDevaWord(unittest.TestCase):
    def test_clusters_concatenate_exactly_to_the_word(self):
        for word in ("जन्माद्यस्य", "यतोऽन्वयादितरतश्चार्थेष्वभिज्ञः", "स्वराट्", "ॐ"):
            self.assertEqual(
                "".join(c.text for c in annotate_deva_word(word)), word
            )

    def test_flags_long_vowels_for_stretch(self):
        clusters = annotate_deva_word("वासुदेवाय")
        self.assertEqual(
            [c.stretch for c in clusters], [True, False, True, True, False]
        )

    def test_keels_only_the_word_final_inherent_a(self):
        vasudevaya = annotate_deva_word("वासुदेवाय")
        self.assertEqual(vasudevaya[-1].text, "य")
        self.assertTrue(vasudevaya[-1].keel)
        self.assertFalse(annotate_deva_word("स्वराट्")[-1].keel)
        self.assertFalse(annotate_deva_word("धीमहि")[-1].keel)
        self.assertFalse(annotate_deva_word("नमः")[-1].keel)

    def test_rings_anusvara_and_visarga_carriers(self):
        namah = annotate_deva_word("नमः")
        self.assertEqual(namah[1].text, "मः")
        self.assertTrue(namah[1].ring)
        satyam = annotate_deva_word("सत्यं")
        self.assertEqual(satyam[1].text, "त्यं")
        self.assertTrue(satyam[1].ring)

    def test_treats_om_as_a_single_held_cluster(self):
        clusters = annotate_deva_word("ॐ")
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].text, "ॐ")
        self.assertTrue(clusters[0].stretch)
        self.assertFalse(clusters[0].keel)

    def test_attaches_avagraha_to_host_and_keeps_marking_beyond(self):
        word = "यतोऽन्वयादितरतश्चार्थेष्वभिज्ञः"
        clusters = annotate_deva_word(word)
        self.assertEqual("".join(c.text for c in clusters), word)
        self.assertEqual(len(clusters), 13)
        self.assertEqual(clusters[1].text, "तोऽ")
        self.assertTrue(clusters[1].stretch)
        self.assertEqual(clusters[12].text, "ज्ञः")
        self.assertTrue(clusters[12].ring)


class TestIdentifyMeterFromLines(unittest.TestCase):
    @staticmethod
    def scan(lines):
        return [syllabify_iast_line(line) for line in lines]

    def test_identifies_anustubh_by_count_alone(self):
        line = "karmaṇy evādhikāras te"
        result = identify_meter(self.scan([line] * 4))
        self.assertEqual(result.label, "anuṣṭubh (śloka)")
        self.assertTrue(result.identified)
        self.assertEqual(result.syllables_per_pada, 8)

    def test_returns_unidentified_for_a_quatrain_matching_nothing(self):
        cooked = identify_meter(self.scan(["kā kā kā"] * 4))
        self.assertFalse(cooked.identified)
        self.assertEqual(cooked.label, "unidentified")

    def test_returns_unidentified_for_empty_input(self):
        self.assertFalse(identify_meter([]).identified)

    def test_identifies_pure_indravamsa_and_keeps_vamsastha_distinct(self):
        indravamsa = self._written("GGLGGLLGLGLG")
        vamsastha = self._written("LGLGGLLGLGLG")
        self.assertEqual(identify_meter(self.scan([indravamsa] * 4)).label, "indravaṁśā")
        self.assertEqual(identify_meter(self.scan([vamsastha] * 4)).label, "vaṁśastha")

    def test_identifies_the_jagati_upajati_when_the_two_mix(self):
        indravamsa = self._written("GGLGGLLGLGLG")
        vamsastha = self._written("LGLGGLLGLGLG")
        result = identify_meter(
            self.scan([indravamsa, vamsastha, indravamsa, vamsastha])
        )
        self.assertEqual(result.label, "upajāti (vaṁśastha–indravaṁśā)")
        self.assertTrue(result.identified)
        self.assertEqual(result.syllables_per_pada, 12)

    @staticmethod
    def _written(pattern: str) -> str:
        return " ".join("kā" if w == "G" else "ka" for w in pattern)


class TestClassifyAksara(unittest.TestCase):
    def test_judges_a_marked_syllable_guru_with_its_rule(self):
        judged = classify_aksara_iast("taḥ")
        self.assertTrue(judged.valid)
        self.assertEqual(judged.weight, "guru")
        self.assertEqual(judged.matras, 2)
        self.assertEqual(judged.rule, "mark-guru")

    def test_short_open_unmarked_is_laghu_and_position_sensitive_without_context(self):
        judged = classify_aksara_iast("ka")
        self.assertTrue(judged.valid)
        self.assertEqual(judged.weight, "laghu")
        self.assertTrue(judged.position_sensitive)

    def test_resolves_guru_by_position_when_context_is_given(self):
        judged = classify_aksara_iast("ka", AksaraContext(next="ṣṇa"))
        self.assertEqual(judged.weight, "guru")
        self.assertEqual(judged.rule, "position-guru")
        self.assertFalse(judged.position_sensitive)

    def test_rejects_a_bare_consonant(self):
        judged = classify_aksara_iast("k")
        self.assertFalse(judged.valid)
        self.assertIn("no vowel", judged.reason)

    def test_rejects_a_standalone_mark(self):
        judged = classify_aksara_iast("ṁ")
        self.assertFalse(judged.valid)
        self.assertIn("ayogavāha", judged.reason)

    def test_rejects_two_vowels_as_two_syllables(self):
        judged = classify_aksara_iast("kara")
        self.assertFalse(judged.valid)
        self.assertIn("2 vowels", judged.reason)

    def test_devanagari_entry_answers_in_devanagari(self):
        judged = classify_aksara_deva("तः")
        self.assertTrue(judged.valid)
        self.assertEqual(judged.text, "तः")
        self.assertEqual(judged.parts.onset, "त्")
        self.assertEqual(judged.parts.vowel, "अ")
        self.assertEqual(judged.parts.mark, "ः")
        self.assertEqual(judged.weight, "guru")

    def test_conjunct_onset_in_devanagari(self):
        judged = classify_aksara_deva("त्सू")
        self.assertTrue(judged.valid)
        self.assertEqual(judged.parts.onset, "त्स्")
        self.assertEqual(judged.parts.vowel, "ऊ")
        self.assertEqual(judged.weight, "guru")
        self.assertEqual(judged.rule, "dirgha-guru")

    def test_pluta_counts_three_matras(self):
        judged = classify_aksara("आ३")
        self.assertTrue(judged.valid)
        self.assertEqual(judged.matras, 3)
        self.assertEqual(judged.rule, "pluta-guru")
        self.assertTrue(judged.pluta)

    def test_router_picks_the_script(self):
        self.assertTrue(classify_aksara("ka").valid)
        self.assertTrue(classify_aksara("क").valid)


if __name__ == "__main__":
    unittest.main()
