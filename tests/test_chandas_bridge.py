# -*- coding: utf-8 -*-
import unittest
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import chandas_bridge
from indic_transliteration import sanscript


class TestChandasBridge(unittest.TestCase):
    def test_gita_anustubh(self):
        v = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः । मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertTrue(res["identified"])
        self.assertEqual(res["bank_key"], "anuṣṭubh")
        self.assertEqual(chandas_bridge.detect_meter_key(v), "anuṣṭubh")

    def test_kannada_script_transliteration(self):
        v = sanscript.transliterate(
            "गुरुर्ब्रह्मा गुरुर्विष्णुः गुरुर्देवो महेश्वरः । गुरुः साक्षात् परं ब्रह्म तस्मै श्रीगुरवे नमः ॥",
            sanscript.DEVANAGARI,
            sanscript.KANNADA
        )
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertTrue(res["identified"])
        self.assertEqual(res["bank_key"], "anuṣṭubh")

    def test_shalini_bank_meter(self):
        v = "दुष्टात्माऽसौ भद्रमेकाकिनं यः क्षेप्तुं हेतुः सौख्यदाख्यं बभूव । हर्यंशोऽयं तं न चक्षाम भूयस्तोके सन्ने सूकरं केसरीव ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertTrue(res["identified"])
        self.assertEqual(res["name"], "śālinī")
        self.assertEqual(res["bank_key"], "śālinī")

    def test_bhujangaprayata_bank_meter(self):
        v = "महानन्दतीर्थस्य ये भाष्यभावं मनोवाग्भिरावर्तयन्ते स्वशक्त्या । सुराद्या नरान्ता मुकुन्दप्रसादादिमं मोक्षमेते भजन्ते सदेति ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertTrue(res["identified"])
        self.assertEqual(res["name"], "bhujaṅgaprayāta")
        self.assertEqual(res["bank_key"], "bhujaṅgaprayāta")

    def test_drutavilambita_bank_meter(self):
        v = "निगमसन्मणिदीपगणोऽभवत्तदुरुवाग्गणपङ्कनिगूढभाः । अविदुषामिति संकरताकरः स किल संकर इत्यभिशुश्रुवे ॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertTrue(res["identified"])
        self.assertEqual(res["name"], "drutavilambita")
        self.assertEqual(res["bank_key"], "drutavilambita")

    def test_malini_tongue_twister(self):
        v = ("हठलुठ दल घिष्टोत्कण्ठदष्टोष्ठ विद्युत्\n"
             "सटशठ कठिनोरः पीठभित्सुष्ठुनिष्ठाम् ।\n"
             "पठतिनुतव कण्ठाधिष्ठ घोरान्त्रमाला\n"
             "दह दह नरसिंहासह्यवीर्याहितं मे ॥")
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertTrue(res["identified"])
        self.assertEqual(res["name"], "mālinī")
        self.assertEqual(res["bank_key"], "mālinī")

    def test_sragdhara_hemistich(self):
        v = "देवार्च्यस्यापि पुत्रादृषिगणसहितात् प्राप्य पूजां प्रयातः शैलेशं चित्रकूटं कतिपयदिवसान्यत्र मोदन्नुवास॥"
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertTrue(res["identified"])
        self.assertEqual(res["name"], "sragdharā")
        self.assertEqual(res["bank_key"], "sragdharā")

    def test_shardulavikridita(self):
        v = ("विद्योरुद्युतिधीरतारकतिरस्कारे पतङ्गायितो दुर्वादीभकुतर्ककुम्भदलने सिंहप्रबर्हायितः । "
             "लोलालोककलोकदृक्कुमुदिनीसंह्लादनेऽब्जायितः संसन्मण्डलमण्डनायितवपुः स्वानन्दतीर्थो बभौ ॥")
        res = chandas_bridge.analyze_verse_meter(v)
        self.assertTrue(res["identified"])
        self.assertEqual(res["name"], "śārdūlavikrīḍita")
        self.assertEqual(res["bank_key"], "śārdūlavikrīḍita")


if __name__ == "__main__":
    unittest.main()
