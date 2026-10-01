# -*- coding: utf-8 -*-
"""
End-to-End Verification Test Suite for Sanskrit Prosody & TTS Audio Routing.
Tests authentic classical verses across all 15 reference bank meters,
unrecorded surrogate meters, multiple Indic scripts, and punctuation variations.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import chandas_bridge
from indic_transliteration import sanscript

BANK_PATH = os.path.join(SRC, "reference_bank", "bank.json")
with open(BANK_PATH, encoding="utf-8") as _f:
    BANK = json.load(_f)
BANK_DIR = os.path.dirname(BANK_PATH)


class TestChandasEndToEnd(unittest.TestCase):
    def _assert_valid_bank_resolution(self, res, expected_bank_key=None):
        """Verifies that the returned result maps to an existing WAV on disk."""
        self.assertTrue(res["identified"], f"Failed to identify meter: {res}")
        bank_key = res["bank_key"]
        if expected_bank_key:
            self.assertEqual(bank_key, expected_bank_key)
        self.assertIn(bank_key, BANK, f"Bank key '{bank_key}' not in bank.json")
        wav_file = os.path.join(BANK_DIR, BANK[bank_key]["wav"])
        self.assertTrue(os.path.isfile(wav_file), f"WAV file missing on disk: {wav_file}")

    # ── 1. ALL 15 BANK METERS TESTED ON AUTHENTIC VERSES ────────────────────

    def test_01_anustubh_bank_verse(self):
        v = "सन्ततं चिन्तयेत् कण्ठं भास्वत्कौस्तुभभासकम् । वैकुण्ठस्याखिला वेदा उद्गीर्यन्तेऽनिशं यतः ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "anuṣṭubh (śloka)")
        self._assert_valid_bank_resolution(res, "anuṣṭubh")

    def test_02_pramanika_bank_verse(self):
        v = "अशीतिकोटियूथपं पुरःसराष्टकायुतम् । अनेकहेतिसङ्कुलं कपीन्द्रमावृणोद् बलम् ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self._assert_valid_bank_resolution(res, "pramāṇikā")

    def test_03_vasantatilaka_bank_verse(self):
        v = "तेनोदितोऽथ सुदृढं पुनरागतेन वज्रोपमं शरममूमुचदिन्द्रसूनौ ॥ रामाज्ञयैव लतया रविजे विभक्ते वायोः सुतेन रघुपेण शरे प्रमुक्ते ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "vasantatilakā")
        self._assert_valid_bank_resolution(res, "vasantatilakā")

    def test_04_upajati_kumarasambhava(self):
        v = "अनन्तरत्नप्रभवस्य यस्य हिमं न सौभाग्यविलोपि जातम् । एको हि दोषो गुणसन्निपाते निमज्जतीन्दोः किरणेष्विवाङ्कः ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertIn("upajāti", res["name"])
        self._assert_valid_bank_resolution(res, "upajāti")

    def test_05_indravajra_sakuntalam(self):
        v = "अर्थो हि कन्या परकीय एव तामद्य संप्रेष्य परिग्रहीतुः । जातो ममायं विशदः प्रकामं प्रत्यर्पितन्यास इवान्तरात्मा ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "indravajrā")
        self._assert_valid_bank_resolution(res, "indravajrā")

    def test_06_upendravajra_bank_verse(self):
        v = "निरीक्ष्य नित्यं चतुरः कुमारान् पिता मुदं सन्ततमाप चोच्चम् । विशेषतो राममुखेन्दुबिम्बमवेक्ष्य राजा कृतकृत्य आसीत् ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "upendravajrā")
        self._assert_valid_bank_resolution(res, "upendravajrā")

    def test_07_vamshastha_kiratarjuniyam(self):
        v = "श्रियः कुरूणामधिपस्य पालनीं प्रजासु वृत्तिं यमयुङ्क्त वेदितुम् । स वर्णिलिङ्गी विदितः समाययौ युधिष्ठिरं द्वैतवने वनेचरः ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "vaṃśastha")
        self._assert_valid_bank_resolution(res, "vaṃśastha")

    def test_08_rathoddhata_bank_verse(self):
        v = "वासुदेवमिह वासुदेवतासत्कलामभिननन्द तं जनः । वासुदेवमिति वासुदेवसन्नामकं विविधलीलमर्भकम् ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "rathoddhatā")
        self._assert_valid_bank_resolution(res, "rathoddhatā")

    def test_09_shalini_bank_verse(self):
        v = "दुष्टात्माऽसौ भद्रमेकाकिनं यः क्षेप्तुं हेतुः सौख्यदाख्यं बभूव । हर्यंशोऽयं तं न चक्षाम भूयस्तोके सन्ने सूकरं केसरीव ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "śālinī")
        self._assert_valid_bank_resolution(res, "śālinī")

    def test_10_indravamsha_pure_verse(self):
        v = "शृङ्गारसिन्धुं स भुजङ्गशायिनं श्रीरङ्गवासं कृतमङ्गलं सताम् । शृङ्गारसिन्धुं स भुजङ्गशायिनं श्रीरङ्गवासं कृतमङ्गलं सताम् ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "indravaṃśā")
        self._assert_valid_bank_resolution(res, "indravaṃśā")

    def test_11_drutavilambita_bank_verse(self):
        v = "निगमसन्मणिदीपगणोऽभवत्तदुरुवाग्गणपङ्कनिगूढभाः । अविदुषामिति संकरताकरः स किल संकर इत्यभिशुश्रुवे ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "drutavilambita")
        self._assert_valid_bank_resolution(res, "drutavilambita")

    def test_12_bhujangaprayata_bank_verse(self):
        v = "महानन्दतीर्थस्य ये भाष्यभावं मनोवाग्भिरावर्तयन्ते स्वशक्त्या । सुराद्या नरान्ता मुकुन्दप्रसादादिमं मोक्षमेते भजन्ते सदेति ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "bhujaṅgaprayāta")
        self._assert_valid_bank_resolution(res, "bhujaṅgaprayāta")

    def test_13_malini_sakuntalam(self):
        v = "सरसिजमनुविद्धं शैवलेनापि रम्यं मलिनमपि हिमांशोर्लक्ष्म लक्ष्मीं तनोति । इयमधिकमनोज्ञा वल्कलेनापि तन्वी किमिव हि मधुराणां मण्डनं नाकृतीनाम् ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "mālinī")
        self._assert_valid_bank_resolution(res, "mālinī")

    def test_14_shardulavikridita_sarasvati(self):
        v = "या कुन्देन्दुतुषारहारधवला या शुभ्रवस्त्रावृता या वीणावरदण्डमण्डितकरा या श्वेतपद्मासना । या ब्रह्माच्युतशङ्करप्रभृतिभिर्देवैः सदा वन्दिता सा मां पातु सरस्वती भगवती निःशेषजाड्यापहा ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "śārdūlavikrīḍita")
        self._assert_valid_bank_resolution(res, "śārdūlavikrīḍita")

    def test_15_sragdhara_bank_verse(self):
        v = "देवार्च्यस्यापि पुत्रादृषिगणसहितात् प्राप्य पूजां प्रयातः शैलेशं चित्रकूटं कतिपयदिवसान्यत्र मोदन्नुवास ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "sragdharā")
        self._assert_valid_bank_resolution(res, "sragdharā")

    # ── 2. UNRECORDED SURROGATE METERS ROUTED TO VALID AUDIO ────────────────

    def test_16_mandakranta_meghaduta_surrogate(self):
        v = "कश्चित्कान्ताविरहगुरुणा स्वाधिकारात्प्रमत्तः शापेनास्तङ्गमितमहिमा वर्षभोग्येण भर्तुः । यक्षश्चक्रे जनकतनयास्नानपुण्योदकेषु स्निग्धच्छायातरुषु वसतिं रामगिर्याश्रमेषु ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "mandākrāntā")
        self.assertTrue(res["is_surrogate"])
        self._assert_valid_bank_resolution(res, "vasantatilakā")

    def test_17_shikharini_soundaryalahari_surrogate(self):
        v = "शिवः शक्त्या युक्तो यदि भवति शक्तः प्रभवितुं न चेदेवं देवो न खलु कुशलः स्पन्दितुमपि । अतस्त्वामारोध्यां हरिहरविरिञ्चादिभिरपि प्रणन्तुं स्तोतुं वा कथमकृतपुण्यः प्रभवति ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "śikhariṇī")
        self.assertTrue(res["is_surrogate"])
        self._assert_valid_bank_resolution(res, "mālinī")

    def test_18_totaka_totakastakam_surrogate(self):
        v = "विदिताखिलशास्त्रसुधाजलधे महितोपनिषत्कथितार्थनिधे । हृदये कलये विमलं चरणं भव शङ्कर देशिक मे शरणम् ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["name"], "toṭaka")
        self.assertTrue(res["is_surrogate"])
        self._assert_valid_bank_resolution(res, "bhujaṅgaprayāta")

    # ── 3. MULTI-SCRIPT AND PUNCTUATION EDGE CASES ──────────────────────────

    def test_19_kannada_script_stotram(self):
        v = sanscript.transliterate(
            "गुरुर्ब्रह्मा गुरुर्विष्णुः गुरुर्देवो महेश्वरः । गुरुः साक्षात् परं ब्रह्म तस्मै श्रीगुरवे नमः ॥",
            sanscript.DEVANAGARI,
            sanscript.KANNADA
        )
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["bank_key"], "anuṣṭubh")

    def test_20_telugu_script_stotram(self):
        v = sanscript.transliterate(
            "सरस्वति नमस्तुभ्यं वरदे कामरूपिणि । विद्यारम्भं करिष्यामि सिद्धिर्भवतु मे सदा ॥",
            sanscript.DEVANAGARI,
            sanscript.TELUGU
        )
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["bank_key"], "anuṣṭubh")

    def test_21_unpunctuated_continuous_verse(self):
        v = "धर्मक्षेत्रेकुरुक्षेत्रेसमवेतायुयुत्सवःमामकाःपाण्डवाश्चैवकिमकुर्वतसञ्जय"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["bank_key"], "anuṣṭubh")

    def test_22_hemistich_2padas_anustubh(self):
        v = "वागर्थाविव संपृक्तौ वागर्थप्रतिपत्तये । जगतः पितरौ वन्दे पार्वतीपरमेश्वरौ ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertEqual(res["bank_key"], "anuṣṭubh")

    # ── 4. SMART PĀDA SEGMENTATION TESTS ────────────────────────────────────

    def test_23_smart_split_unpunctuated_anustubh(self):
        from render_core import split_padas
        v = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय"
        padas = split_padas(v)
        self.assertEqual(len(padas), 2)
        self.assertEqual(padas[0], "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः")
        self.assertEqual(padas[1], "मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय")

    def test_24_smart_split_unpunctuated_upajati(self):
        from render_core import split_padas
        v = "अवैदिकं माध्यमिकं निरस्तं निरीक्ष्य तत्पक्षसुपक्षपाती तमेव पक्षं प्रतिपादुकोऽसौ न्यरूरुपन्मार्गमिहानुरूपम्"
        padas = split_padas(v)
        self.assertEqual(len(padas), 2)
        self.assertEqual(padas[0], "अवैदिकं माध्यमिकं निरस्तं निरीक्ष्य तत्पक्षसुपक्षपाती")
        self.assertEqual(padas[1], "तमेव पक्षं प्रतिपादुकोऽसौ न्यरूरुपन्मार्गमिहानुरूपम्")

    def test_25_smart_split_punctuated_preserved(self):
        from render_core import split_padas
        v = "सन्ततं चिन्तयेत् कण्ठं भास्वत्कौस्तुभभासकम् । वैकुण्ठस्याखिला वेदा उद्गीर्यन्तेऽनिशं यतः ॥"
        padas = split_padas(v)
        self.assertEqual(len(padas), 2)
        self.assertEqual(padas[0], "सन्ततं चिन्तयेत् कण्ठं भास्वत्कौस्तुभभासकम्")
        self.assertEqual(padas[1], "वैकुण्ठस्याखिला वेदा उद्गीर्यन्तेऽनिशं यतः")


if __name__ == "__main__":
    unittest.main()
