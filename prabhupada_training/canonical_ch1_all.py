import re

# Complete canonical pāda definitions for Bhagavad Gita Chapter 1 (Verses 1.1 to 1.47)
# All 47 verses in Anuṣṭubh meter (8 syllables per pāda, 4 pādas per verse)
# plus the 3 recited speaker tags:
# - Verse 1.2: Sanjaya uvāca
# - Verse 1.24: Sanjaya uvāca
# - Verse 1.28: Arjuna uvāca (uvāca)
# - Verse 1.47: Sanjaya uvāca

canonical_units = [
    # --- Verse 1.1 ---
    {"fn": "bg_01_01_pada_1.wav", "v": 1, "p": 1, "deva": "धर्मक्षेत्रे कुरुक्षेत्रे", "iast": "dharma-kṣetre kuru-kṣetre", "words": "dharmaksetre kuruksetre"},
    {"fn": "bg_01_01_pada_2.wav", "v": 1, "p": 2, "deva": "समवेता युयुत्सवः", "iast": "samavetā yuyutsavaḥ", "words": "samaveta yuyutsavah"},
    {"fn": "bg_01_01_pada_3.wav", "v": 1, "p": 3, "deva": "मामकाः पाण्डवाश्चैव", "iast": "māmakāḥ pāṇḍavāś caiva", "words": "mamakah pandavas caiva"},
    {"fn": "bg_01_01_pada_4.wav", "v": 1, "p": 4, "deva": "किमकुर्वत सञ्जय", "iast": "kim akurvata sañjaya", "words": "kim akurvata sanjaya"},

    # --- Verse 1.2 ---
    {"fn": "bg_01_02_speaker.wav", "v": 2, "p": "speaker", "deva": "सञ्जय उवाच", "iast": "sañjaya uvāca", "words": "sanjaya uvaca"},
    {"fn": "bg_01_02_pada_1.wav", "v": 2, "p": 1, "deva": "दृष्ट्वा तु पाण्डवानीकं", "iast": "dṛṣṭvā tu pāṇḍavānīkaṁ", "words": "drstva tu pandavanikam"},
    {"fn": "bg_01_02_pada_2.wav", "v": 2, "p": 2, "deva": "व्यूढं दुर्योधनस्तदा", "iast": "vyūḍhaṁ duryodhanas tadā", "words": "vyudham duryodhanas tada"},
    {"fn": "bg_01_02_pada_3.wav", "v": 2, "p": 3, "deva": "आचार्यमुपसङ्गम्य", "iast": "ācāryam upasaṅgamya", "words": "acaryam upasangamya"},
    {"fn": "bg_01_02_pada_4.wav", "v": 2, "p": 4, "deva": "राजा वचनमब्रवीत्", "iast": "rājā vacanam abravīt", "words": "raja vacanam abravit"},

    # --- Verse 1.3 ---
    {"fn": "bg_01_03_pada_1.wav", "v": 3, "p": 1, "deva": "पश्यैतां पाण्डुपुत्राणाम्", "iast": "paśyaitāṁ pāṇḍu-putrāṇām", "words": "pasyaitam panduputranam"},
    {"fn": "bg_01_03_pada_2.wav", "v": 3, "p": 2, "deva": "आचार्य महतीं चमूम्", "iast": "ācārya mahatīṁ camūm", "words": "acarya mahatim camum"},
    {"fn": "bg_01_03_pada_3.wav", "v": 3, "p": 3, "deva": "व्यूढां द्रुपदपुत्रेण", "iast": "vyūḍhāṁ drupada-putreṇa", "words": "vyudham drupadaputrena"},
    {"fn": "bg_01_03_pada_4.wav", "v": 3, "p": 4, "deva": "तव शिष्येण धीमता", "iast": "tava śiṣyeṇa dhīmatā", "words": "tava sisyena dhimata"},

    # --- Verse 1.4 ---
    {"fn": "bg_01_04_pada_1.wav", "v": 4, "p": 1, "deva": "अत्र शूरा महेष्वासा", "iast": "atra śūrā maheṣv-āsā", "words": "atra sura mahesvasa"},
    {"fn": "bg_01_04_pada_2.wav", "v": 4, "p": 2, "deva": "भीमार्जुनसमा युधि", "iast": "bhīmārjuna-samā yudhi", "words": "bhimarjunasama yudhi"},
    {"fn": "bg_01_04_pada_3.wav", "v": 4, "p": 3, "deva": "युयुधानो विराटश्च", "iast": "yuyudhāno virāṭaś ca", "words": "yuyudhano viratas ca"},
    {"fn": "bg_01_04_pada_4.wav", "v": 4, "p": 4, "deva": "द्रुपदश्च महारथः", "iast": "drupadaś ca mahā-rathaḥ", "words": "drupadas ca maharathah"},

    # --- Verse 1.5 ---
    {"fn": "bg_01_05_pada_1.wav", "v": 5, "p": 1, "deva": "धृष्टकेतुश्चेकितानः", "iast": "dhṛṣṭaketuś cekitānaḥ", "words": "dhrstaketus cekitanah"},
    {"fn": "bg_01_05_pada_2.wav", "v": 5, "p": 2, "deva": "काशिराजश्च वीर्यवान्", "iast": "kāśirājaś ca vīryavān", "words": "kasirajas ca viryavan"},
    {"fn": "bg_01_05_pada_3.wav", "v": 5, "p": 3, "deva": "पुरुजित्कुन्तिभोजश्च", "iast": "purujit kuntibhojaś ca", "words": "purujit kuntibhojas ca"},
    {"fn": "bg_01_05_pada_4.wav", "v": 5, "p": 4, "deva": "शैब्यश्च नरपुङ्गवः", "iast": "śaibyaś ca nara-puṅgavaḥ", "words": "saibyas ca narapungavah"},

    # --- Verse 1.6 ---
    {"fn": "bg_01_06_pada_1.wav", "v": 6, "p": 1, "deva": "युधामन्युश्च विक्रान्त", "iast": "yudhāmanyuś ca vikrānta", "words": "yudhamanyus ca vikranta"},
    {"fn": "bg_01_06_pada_2.wav", "v": 6, "p": 2, "deva": "उत्तमौजाश्च वीर्यवान्", "iast": "uttamaujāś ca vīryavān", "words": "uttamaujas ca viryavan"},
    {"fn": "bg_01_06_pada_3.wav", "v": 6, "p": 3, "deva": "सौभद्रो द्रौपदेयाश्च", "iast": "saubhadro draupadeyāś ca", "words": "saubhadro draupadeyas ca"},
    {"fn": "bg_01_06_pada_4.wav", "v": 6, "p": 4, "deva": "सर्व एव महारथाः", "iast": "sarva eva mahā-rathāḥ", "words": "sarva eva maharathah"},

    # --- Verse 1.7 ---
    {"fn": "bg_01_07_pada_1.wav", "v": 7, "p": 1, "deva": "अस्माकं तु विशिष्टा ये", "iast": "asmākaṁ tu viśiṣṭā ye", "words": "asmakam tu visista ye"},
    {"fn": "bg_01_07_pada_2.wav", "v": 7, "p": 2, "deva": "तान्निबोध द्विजोत्तम", "iast": "tān nibodha dvijottama", "words": "tan nibodha dvijottama"},
    {"fn": "bg_01_07_pada_3.wav", "v": 7, "p": 3, "deva": "नायका मम सैन्यस्य", "iast": "nāyakā mama sainyasya", "words": "nayaka mama sainyasya"},
    {"fn": "bg_01_07_pada_4.wav", "v": 7, "p": 4, "deva": "संज्ञार्थं तान्ब्रवीमि ते", "iast": "saṁjñārthaṁ tān bravīmi te", "words": "samjnartham tan bravimi te"},

    # --- Verse 1.8 ---
    {"fn": "bg_01_08_pada_1.wav", "v": 8, "p": 1, "deva": "भवान्भीष्मश्च कर्णश्च", "iast": "bhavān bhīṣmaś ca karṇaś ca", "words": "bhavan bhismas ca karnas ca"},
    {"fn": "bg_01_08_pada_2.wav", "v": 8, "p": 2, "deva": "कृपश्च समितिञ्जयः", "iast": "kṛpaś ca samitiṁ-jayaḥ", "words": "krpas ca samitinjayah"},
    {"fn": "bg_01_08_pada_3.wav", "v": 8, "p": 3, "deva": "अश्वत्थामा विकर्णश्च", "iast": "aśvatthāmā vikarṇaś ca", "words": "asvatthama vikarnas ca"},
    {"fn": "bg_01_08_pada_4.wav", "v": 8, "p": 4, "deva": "सौमदत्तिस्तथैव च", "iast": "saumadattis tathaiva ca", "words": "saumadattis tathaiva ca"},

    # --- Verse 1.9 ---
    {"fn": "bg_01_09_pada_1.wav", "v": 9, "p": 1, "deva": "अन्ये च बहवः शूरा", "iast": "anye ca bahavaḥ śūrā", "words": "anye ca bahavah sura"},
    {"fn": "bg_01_09_pada_2.wav", "v": 9, "p": 2, "deva": "मदर्थे त्यक्तजीविताः", "iast": "mad-arthe tyakta-jīvitāḥ", "words": "madarthe tyaktajivitah"},
    {"fn": "bg_01_09_pada_3.wav", "v": 9, "p": 3, "deva": "नानाशास्त्रप्रहरणाः", "iast": "nānā-śastra-praharaṇāḥ", "words": "nanasastrapraharanah"},
    {"fn": "bg_01_09_pada_4.wav", "v": 9, "p": 4, "deva": "सर्वे युद्धविशारदाः", "iast": "sarve yuddha-viśāradāḥ", "words": "sarve yuddhavisaradah"},

    # --- Verse 1.10 ---
    {"fn": "bg_01_10_pada_1.wav", "v": 10, "p": 1, "deva": "अपर्याप्तं तदस्माकं", "iast": "aparyāptaṁ tad asmākaṁ", "words": "aparyaptam tad asmakam"},
    {"fn": "bg_01_10_pada_2.wav", "v": 10, "p": 2, "deva": "बलं भीष्माभिरक्षितम्", "iast": "balaṁ bhīṣmābhirakṣitam", "words": "balam bhismabhiraksitam"},
    {"fn": "bg_01_10_pada_3.wav", "v": 10, "p": 3, "deva": "पर्याप्तं त्विदमेतेषां", "iast": "paryāptaṁ tv idam eteṣāṁ", "words": "paryaptam tv idam etesam"},
    {"fn": "bg_01_10_pada_4.wav", "v": 10, "p": 4, "deva": "बलं भीमाभिरक्षितम्", "iast": "balaṁ bhīmābhirakṣitam", "words": "balam bhimabhiraksitam"},

    # --- Verse 1.11 ---
    {"fn": "bg_01_11_pada_1.wav", "v": 11, "p": 1, "deva": "अयनेषु च सर्वेषु", "iast": "ayaneṣu ca sarveṣu", "words": "ayanesu ca sarvesu"},
    {"fn": "bg_01_11_pada_2.wav", "v": 11, "p": 2, "deva": "यथाभागमवस्थिताः", "iast": "yathā-bhāgam avasthitāḥ", "words": "yathabhagam avasthitah"},
    {"fn": "bg_01_11_pada_3.wav", "v": 11, "p": 3, "deva": "भीष्ममेवाभिरक्षन्तु", "iast": "bhīṣmam evābhirakṣantu", "words": "bhismam evabhiraksantu"},
    {"fn": "bg_01_11_pada_4.wav", "v": 11, "p": 4, "deva": "भवन्तः सर्व एव हि", "iast": "bhavantaḥ sarva eva hi", "words": "bhavantah sarva eva hi"},

    # --- Verse 1.12 ---
    {"fn": "bg_01_12_pada_1.wav", "v": 12, "p": 1, "deva": "तस्य सञ्जनयन्हर्षं", "iast": "tasya sañjanayan harṣaṁ", "words": "tasya sanjanayan harsam"},
    {"fn": "bg_01_12_pada_2.wav", "v": 12, "p": 2, "deva": "कुरुवृद्धः पितामहः", "iast": "kuru-vṛddhaḥ pitāmahaḥ", "words": "kuru vrddhah pitamahah"},
    {"fn": "bg_01_12_pada_3.wav", "v": 12, "p": 3, "deva": "सिंहनादं विनद्योच्चैः", "iast": "siṁha-nādaṁ vinadyoccaiḥ", "words": "simhanadam vinadyoccaih"},
    {"fn": "bg_01_12_pada_4.wav", "v": 12, "p": 4, "deva": "शङ्खं दध्मौ प्रतापवान्", "iast": "śaṅkhaṁ dadhmau pratāpavān", "words": "sankham dadhmau pratapavan"},

    # --- Verse 1.13 ---
    {"fn": "bg_01_13_pada_1.wav", "v": 13, "p": 1, "deva": "ततः शङ्खाश्च भेर्यश्च", "iast": "tataḥ śaṅkhāś ca bheryaś ca", "words": "tatah sankhas ca bheryas ca"},
    {"fn": "bg_01_13_pada_2.wav", "v": 13, "p": 2, "deva": "पणवानकगोमुखाः", "iast": "paṇavānaka-gomukhāḥ", "words": "panavanaka gomukhah"},
    {"fn": "bg_01_13_pada_3.wav", "v": 13, "p": 3, "deva": "सहसैवाभ्यहन्यन्त", "iast": "sahasaivābhyahanyanta", "words": "sahasaivabhyahanyanta"},
    {"fn": "bg_01_13_pada_4.wav", "v": 13, "p": 4, "deva": "स शब्दस्तुमुलोऽभवत्", "iast": "sa śabdas tumulo 'bhavat", "words": "sa sabdas tumulo bhavat"},

    # --- Verse 1.14 ---
    {"fn": "bg_01_14_pada_1.wav", "v": 14, "p": 1, "deva": "ततः श्वेतैर्हयैर्युक्ते", "iast": "tataḥ śvetair hayair yukte", "words": "tatah svetair hayair yukte"},
    {"fn": "bg_01_14_pada_2.wav", "v": 14, "p": 2, "deva": "महति स्यन्दने स्थितौ", "iast": "mahati syandane sthitau", "words": "mahati syandane sthitau"},
    {"fn": "bg_01_14_pada_3.wav", "v": 14, "p": 3, "deva": "माधवः पाण्डवश्चैव", "iast": "mādhavaḥ pāṇḍavaś caiva", "words": "madhavah pandavas caiva"},
    {"fn": "bg_01_14_pada_4.wav", "v": 14, "p": 4, "deva": "दिव्यौ शङ्खौ प्रदध्मतुः", "iast": "divyau śaṅkhau pradadhmatuḥ", "words": "divyau sankhau pradadhmatuh"},

    # --- Verse 1.15 ---
    {"fn": "bg_01_15_pada_1.wav", "v": 15, "p": 1, "deva": "पाञ्चजन्यं हृषीकेशो", "iast": "pāñcajanyaṁ hṛṣīkeśo", "words": "pancajanyam hrsikeso"},
    {"fn": "bg_01_15_pada_2.wav", "v": 15, "p": 2, "deva": "देवदत्तं धनञ्जयः", "iast": "devadattaṁ dhanañjayaḥ", "words": "devadattam dhananjayah"},
    {"fn": "bg_01_15_pada_3.wav", "v": 15, "p": 3, "deva": "पौण्ड्रं दध्मौ महाशङ्खं", "iast": "pauṇḍraṁ dadhmau mahā-śaṅkhaṁ", "words": "paundram dadhmau mahasankham"},
    {"fn": "bg_01_15_pada_4.wav", "v": 15, "p": 4, "deva": "भीमकर्मा वृकोदरः", "iast": "bhīma-karmā vṛkodaraḥ", "words": "bhimakarma vrkodarah"},

    # --- Verse 1.16 ---
    {"fn": "bg_01_16_pada_1.wav", "v": 16, "p": 1, "deva": "अनन्तविजयं राजा", "iast": "anantavijayaṁ rājā", "words": "anantavijayam raja"},
    {"fn": "bg_01_16_pada_2.wav", "v": 16, "p": 2, "deva": "कुन्तीपुत्रो युधिष्ठिरः", "iast": "kuntī-putro yudhiṣṭhiraḥ", "words": "kuntiputro yudhisthirah"},
    {"fn": "bg_01_16_pada_3.wav", "v": 16, "p": 3, "deva": "नकुलः सहदेवश्च", "iast": "nakulaḥ sahadevaś ca", "words": "nakulah sahadevas ca"},
    {"fn": "bg_01_16_pada_4.wav", "v": 16, "p": 4, "deva": "सुघोषमणिपुष्पकौ", "iast": "sughoṣa-maṇipuṣpakau", "words": "sughosamanipuspakau"},

    # --- Verse 1.17 ---
    {"fn": "bg_01_17_pada_1.wav", "v": 17, "p": 1, "deva": "काश्यश्च परमेष्वासः", "iast": "kāśyaś ca parameṣv-āsaḥ", "words": "kasyas ca paramesvasah"},
    {"fn": "bg_01_17_pada_2.wav", "v": 17, "p": 2, "deva": "शिखण्डी च महारथः", "iast": "śikhaṇḍī ca mahā-rathaḥ", "words": "sikhandi ca maharathah"},
    {"fn": "bg_01_17_pada_3.wav", "v": 17, "p": 3, "deva": "धृष्टद्युम्नो विराटश्च", "iast": "dhṛṣṭadyumno virāṭaś ca", "words": "dhrstadyumno viratas ca"},
    {"fn": "bg_01_17_pada_4.wav", "v": 17, "p": 4, "deva": "सात्यकिश्चापराजितः", "iast": "sātyakiś cāparājitaḥ", "words": "satyakis caparajitah"},

    # --- Verse 1.18 ---
    {"fn": "bg_01_18_pada_1.wav", "v": 18, "p": 1, "deva": "द्रुपदो द्रौपदेयाश्च", "iast": "drupado draupadeyāś ca", "words": "drupado draupadeyas ca"},
    {"fn": "bg_01_18_pada_2.wav", "v": 18, "p": 2, "deva": "सर्वशः पृथिवीपते", "iast": "sarvaśaḥ pṛthivī-pate", "words": "sarvasah prthivipate"},
    {"fn": "bg_01_18_pada_3.wav", "v": 18, "p": 3, "deva": "सौभद्रश्च महाबाहुः", "iast": "saubhadraś ca mahā-bāhuḥ", "words": "saubhadras ca mahabahuh"},
    {"fn": "bg_01_18_pada_4.wav", "v": 18, "p": 4, "deva": "शङ्खान्दध्मुः पृथक्पृथक्", "iast": "śaṅkhān dadhmuḥ pṛthak pṛthak", "words": "sankhan dadhmuh prthak prthak"},

    # --- Verse 1.19 ---
    {"fn": "bg_01_19_pada_1.wav", "v": 19, "p": 1, "deva": "स घोषो धार्तराष्ट्राणां", "iast": "sa ghoṣo dhārtarāṣṭrāṇāṁ", "words": "sa ghoso dhartarastranam"},
    {"fn": "bg_01_19_pada_2.wav", "v": 19, "p": 2, "deva": "हृदयानि व्यदारयत्", "iast": "hṛdayāni vyadārayat", "words": "hrdayani vyadarayat"},
    {"fn": "bg_01_19_pada_3.wav", "v": 19, "p": 3, "deva": "नभश्च पृथिवीं चैव", "iast": "nabhaś ca pṛthivīṁ caiva", "words": "nabhas ca prthivim caiva"},
    {"fn": "bg_01_19_pada_4.wav", "v": 19, "p": 4, "deva": "तुमुलो व्यनुनादयन्", "iast": "tumulo 'byanunādayan", "words": "tumulo byanunadayan"},

    # --- Verse 1.20 ---
    {"fn": "bg_01_20_pada_1.wav", "v": 20, "p": 1, "deva": "अथ व्यवस्थितान्दृष्ट्वा", "iast": "atha vyavasthitān dṛṣṭvā", "words": "atha vyavasthitan drstva"},
    {"fn": "bg_01_20_pada_2.wav", "v": 20, "p": 2, "deva": "धार्तराष्ट्रान्कपिध्वजः", "iast": "dhārtarāṣṭrān kapi-dhvajaḥ", "words": "dhartarastran kapidhvajah"},
    {"fn": "bg_01_20_pada_3.wav", "v": 20, "p": 3, "deva": "प्रवृत्ते शस्त्रसम्पाते", "iast": "pravṛtte śastra-sampāte", "words": "pravrtte sastrasampate"},
    {"fn": "bg_01_20_pada_4.wav", "v": 20, "p": 4, "deva": "धनुरुद्यम्य पाण्डवः", "iast": "dhanur udyamya pāṇḍavaḥ", "words": "dhanur udyamya pandavah"},

    # --- Verse 1.21 ---
    {"fn": "bg_01_21_pada_1.wav", "v": 21, "p": 1, "deva": "हृषीकेशं तदा वाक्यम्", "iast": "hṛṣīkeśaṁ tadā vākyam", "words": "hrsikesam tada vakyam"},
    {"fn": "bg_01_21_pada_2.wav", "v": 21, "p": 2, "deva": "इदमाह महीपते", "iast": "idam āha mahī-pate", "words": "idam aha mahipate"},
    {"fn": "bg_01_21_pada_3.wav", "v": 21, "p": 3, "deva": "सेनयोरुभयोर्मध्ये", "iast": "senayor ubhayor madhye", "words": "senayor ubhayor madhye"},
    {"fn": "bg_01_21_pada_4.wav", "v": 21, "p": 4, "deva": "रथं स्थापय मेऽच्युत", "iast": "rathaṁ sthāpaya me 'cyuta", "words": "ratham sthapaya me cyuta"},

    # --- Verse 1.22 ---
    {"fn": "bg_01_22_pada_1.wav", "v": 22, "p": 1, "deva": "यावदेतान्निरिक्षेऽहं", "iast": "yāvad etān nirīkṣe 'haṁ", "words": "yavad etan nirikse ham"},
    {"fn": "bg_01_22_pada_2.wav", "v": 22, "p": 2, "deva": "योद्धुकामानवस्थितान्", "iast": "yoddhu-kāmān avasthitān", "words": "yoddhukaman avasthitan"},
    {"fn": "bg_01_22_pada_3.wav", "v": 22, "p": 3, "deva": "कैर्मया सह योद्धव्यम्", "iast": "kair mayā saha yoddhavyam", "words": "kair maya saha yoddhavyam"},
    {"fn": "bg_01_22_pada_4.wav", "v": 22, "p": 4, "deva": "अस्मिन् रणसमुद्यमे", "iast": "asmin raṇa-samudyame", "words": "asmin rana samudyame"},

    # --- Verse 1.23 ---
    {"fn": "bg_01_23_pada_1.wav", "v": 23, "p": 1, "deva": "योत्स्यमानानवेक्षेऽहं", "iast": "yotsyamānān avekṣe 'haṁ", "words": "yotsyamanan avekse ham"},
    {"fn": "bg_01_23_pada_2.wav", "v": 23, "p": 2, "deva": "य एतेऽत्र समागताः", "iast": "ya ete 'tra samāgatāḥ", "words": "ya ete tra samagatah"},
    {"fn": "bg_01_23_pada_3.wav", "v": 23, "p": 3, "deva": "धार्तराष्ट्रस्य दुर्बुद्धेः", "iast": "dhārtarāṣṭrasya durbuddher", "words": "dhartarastrasya durbuddher"},
    {"fn": "bg_01_23_pada_4.wav", "v": 23, "p": 4, "deva": "युद्धे प्रियचिकीर्षवः", "iast": "yuddhe priya-cikīrṣavaḥ", "words": "yuddhe priyacikirsavah"},

    # --- Verse 1.24 ---
    {"fn": "bg_01_24_speaker.wav", "v": 24, "p": "speaker", "deva": "सञ्जय उवाच", "iast": "sañjaya uvāca", "words": "sanjaya uvaca"},
    {"fn": "bg_01_24_pada_1.wav", "v": 24, "p": 1, "deva": "एवमुक्तो हृषीकेशो", "iast": "evam ukto hṛṣīkeśo", "words": "evam ukto hrsikeso"},
    {"fn": "bg_01_24_pada_2.wav", "v": 24, "p": 2, "deva": "गुडाकेशेन भारत", "iast": "guḍākeśena bhārata", "words": "gudakesena bharata"},
    {"fn": "bg_01_24_pada_3.wav", "v": 24, "p": 3, "deva": "सेनयोरुभयोर्मध्ये", "iast": "senayor ubhayor madhye", "words": "senayor ubhayor madhye"},
    {"fn": "bg_01_24_pada_4.wav", "v": 24, "p": 4, "deva": "स्थापयित्वा रथोत्तमम्", "iast": "sthāpayitvā rathottamam", "words": "sthapayitva rathottamam"},

    # --- Verse 1.25 ---
    {"fn": "bg_01_25_pada_1.wav", "v": 25, "p": 1, "deva": "भीष्मद्रोणप्रमुखतः", "iast": "bhīṣma-droṇa-pramukhataḥ", "words": "bhismadronapramukhatah"},
    {"fn": "bg_01_25_pada_2.wav", "v": 25, "p": 2, "deva": "सर्वेषां च महीक्षिताम्", "iast": "sarveṣāṁ ca mahī-kṣitām", "words": "sarvesam ca mahiksitam"},
    {"fn": "bg_01_25_pada_3.wav", "v": 25, "p": 3, "deva": "उवाच पार्थ पश्यैतान्", "iast": "uvāca pārtha paśyaitān", "words": "uvaca partha pasyaitan"},
    {"fn": "bg_01_25_pada_4.wav", "v": 25, "p": 4, "deva": "समवेतान्कुरूनिति", "iast": "samavetān kurūn iti", "words": "samavetan kurun iti"},

    # --- Verse 1.26 (Prabhupada recited padas c and d) ---
    {"fn": "bg_01_26_pada_1.wav", "v": 26, "p": 1, "deva": "आचार्यान्मातुलान्भ्रातॄन्", "iast": "ācāryān mātulān bhrātṝn", "words": "acaryan matulan bhratrn"},
    {"fn": "bg_01_26_pada_2.wav", "v": 26, "p": 2, "deva": "पुत्रान्पौत्रान्सखींस्तथा", "iast": "putrān pautrān sakhīṁs tathā", "words": "putran pautran sakhims tatha"},

    # --- Verse 1.27 ---
    {"fn": "bg_01_27_pada_1.wav", "v": 27, "p": 1, "deva": "श्वशुरान्सुहृदश्चैव", "iast": "śvaśurān suhṛdaś caiva", "words": "svasuran suhrdas caiva"},
    {"fn": "bg_01_27_pada_2.wav", "v": 27, "p": 2, "deva": "सेनयोरुभयोरपि", "iast": "senayor ubhayor api", "words": "senayor ubhayor api"},
    {"fn": "bg_01_27_pada_3.wav", "v": 27, "p": 3, "deva": "तान्समीक्ष्य स कौन्तेयः", "iast": "tān samīkṣya sa kaunteyaḥ", "words": "tan samiksya sa kaunteyah"},
    {"fn": "bg_01_27_pada_4.wav", "v": 27, "p": 4, "deva": "सर्वान्बन्धूनवस्थितान्", "iast": "sarvān bandhūn avasthitān", "words": "sarvan bandhun avasthitan"},

    # --- Verse 1.28 ---
    {"fn": "bg_01_28_pada_1.wav", "v": 28, "p": 1, "deva": "कृपया परयाविष्टो", "iast": "kṛpayā parayāviṣṭo", "words": "krpaya parayavisto"},
    {"fn": "bg_01_28_pada_2.wav", "v": 28, "p": 2, "deva": "विषीदन्निदमब्रवीत्", "iast": "viṣīdann idam abravīt", "words": "visidann idam abravit"},
    {"fn": "bg_01_28_speaker.wav", "v": 28, "p": "speaker", "deva": "अर्जुन उवाच", "iast": "arjuna uvāca", "words": "uvaca"},
    {"fn": "bg_01_28_pada_3.wav", "v": 28, "p": 3, "deva": "दृष्ट्वेमं स्वजनं कृष्ण", "iast": "dṛṣṭvemaṁ svajanaṁ kṛṣṇa", "words": "drstvemam svajanam krsna"},
    {"fn": "bg_01_28_pada_4.wav", "v": 28, "p": 4, "deva": "युयुत्सुं समुपस्थितम्", "iast": "yuyutsuṁ samupasthitam", "words": "yuyutsum samupasthitam"},

    # --- Verse 1.29 ---
    {"fn": "bg_01_29_pada_1.wav", "v": 29, "p": 1, "deva": "सीदन्ति मम गात्राणि", "iast": "sīdanti mama gātrāṇi", "words": "sidanti mama gatrani"},
    {"fn": "bg_01_29_pada_2.wav", "v": 29, "p": 2, "deva": "मुखं च परिशुष्यति", "iast": "mukhaṁ ca pariśuṣyati", "words": "mukham ca parisusyati"},
    {"fn": "bg_01_29_pada_3.wav", "v": 29, "p": 3, "deva": "वेपथुश्च शरीरे मे", "iast": "vepathuś ca śarīre me", "words": "vepathus ca sarire me"},
    {"fn": "bg_01_29_pada_4.wav", "v": 29, "p": 4, "deva": "रोमहर्षश्च जायते", "iast": "romaharṣaś ca jāyate", "words": "romaharsas ca jayate"},

    # --- Verse 1.30 ---
    {"fn": "bg_01_30_pada_1.wav", "v": 30, "p": 1, "deva": "गाण्डीवं स्रंसते हस्तात्", "iast": "gāṇḍīvaṁ sraṁsate hastāt", "words": "gandivam sramsate hastat"},
    {"fn": "bg_01_30_pada_2.wav", "v": 30, "p": 2, "deva": "त्वक्चैव परिदह्यते", "iast": "tvak caiva paridahyate", "words": "tvak caiva paridahyate"},
    {"fn": "bg_01_30_pada_3.wav", "v": 30, "p": 3, "deva": "न च शक्नोम्यवस्थातुं", "iast": "na ca śaknomy avasthātuṁ", "words": "na ca saknomy avasthatum"},
    {"fn": "bg_01_30_pada_4.wav", "v": 30, "p": 4, "deva": "भ्रमतीव च मे मनः", "iast": "bhramatīva ca me manaḥ", "words": "bhramativa ca me manah"},

    # --- Verse 1.31 ---
    {"fn": "bg_01_31_pada_1.wav", "v": 31, "p": 1, "deva": "निमित्तानि च पश्यामि", "iast": "nimittāni ca paśyāmi", "words": "nimittani ca pasyami"},
    {"fn": "bg_01_31_pada_2.wav", "v": 31, "p": 2, "deva": "विपरीतानि केशव", "iast": "viparītāni keśava", "words": "viparítani kesava"},
    {"fn": "bg_01_31_pada_3.wav", "v": 31, "p": 3, "deva": "न च श्रेयोऽनुपश्यामि", "iast": "na ca śreyo 'nupaśyāmi", "words": "na ca sreyo nupasyami"},
    {"fn": "bg_01_31_pada_4.wav", "v": 31, "p": 4, "deva": "हत्वा स्वजनमाहवे", "iast": "hatvā svajanam āhave", "words": "hatva svajanam ahave"},

    # --- Verse 1.32 ---
    {"fn": "bg_01_32_pada_1.wav", "v": 32, "p": 1, "deva": "न काङ्क्षे विजयं कृष्ण", "iast": "na kāṅkṣe vijayaṁ kṛṣṇa", "words": "na kankse vijayam krsna"},
    {"fn": "bg_01_32_pada_2.wav", "v": 32, "p": 2, "deva": "न च राज्यं सुखानि च", "iast": "na ca rājyaṁ sukhāni ca", "words": "na ca rajyam sukhani ca"},
    {"fn": "bg_01_32_pada_3.wav", "v": 32, "p": 3, "deva": "किं नो राज्येन गोविन्द", "iast": "kiṁ no rājyena govinda", "words": "kim no rajyena govinda"},
    {"fn": "bg_01_32_pada_4.wav", "v": 32, "p": 4, "deva": "किं भोगैर्जीवितेन वा", "iast": "kiṁ bhogair jīvitena vā", "words": "kim bhogair jivitena va"},

    # --- Verse 1.33 ---
    {"fn": "bg_01_33_pada_1.wav", "v": 33, "p": 1, "deva": "येषामर्थे काङ्क्षितं नो", "iast": "yeṣām arthe kāṅkṣitaṁ no", "words": "yesam arthe kanksitam no"},
    {"fn": "bg_01_33_pada_2.wav", "v": 33, "p": 2, "deva": "राज्यं भोगाः सुखानि च", "iast": "rājyaṁ bhogāḥ sukhāni ca", "words": "rajyam bhogah sukhani ca"},
    {"fn": "bg_01_33_pada_3.wav", "v": 33, "p": 3, "deva": "त इमेऽवस्थिता युद्धे", "iast": "ta ime 'vasthitā yuddhe", "words": "ta ime vasthita yuddhe"},
    {"fn": "bg_01_33_pada_4.wav", "v": 33, "p": 4, "deva": "प्राणांस्त्यक्त्वा धनानि च", "iast": "prāṇāṁs tyaktvā dhanāni ca", "words": "pranams tyaktva dhanani ca"},

    # --- Verse 1.34 ---
    {"fn": "bg_01_34_pada_1.wav", "v": 34, "p": 1, "deva": "आचार्याः पितरः पुत्राः", "iast": "ācāryāḥ pitaraḥ putrāḥ", "words": "acaryah pitarah putrah"},
    {"fn": "bg_01_34_pada_2.wav", "v": 34, "p": 2, "deva": "तथैव च पितामहाः", "iast": "tathaiva ca pitāmahāḥ", "words": "tathaiva ca pitamahah"},
    {"fn": "bg_01_34_pada_3.wav", "v": 34, "p": 3, "deva": "मातुलाः श्वशुराः पौत्राः", "iast": "mātulāḥ śvaśurāḥ pautrāḥ", "words": "matulah svasurah pautrah"},
    {"fn": "bg_01_34_pada_4.wav", "v": 34, "p": 4, "deva": "श्यालाः सम्बन्धिनस्तथा", "iast": "śyālāḥ sambandhinas tathā", "words": "syalah sambandhinas tatha"},

    # --- Verse 1.35 ---
    {"fn": "bg_01_35_pada_1.wav", "v": 35, "p": 1, "deva": "एतान्न हन्तुमिच्छामि", "iast": "etān na hantum icchāmi", "words": "etan na hantum icchami"},
    {"fn": "bg_01_35_pada_2.wav", "v": 35, "p": 2, "deva": "घ्नतोऽपि मधुसूदन", "iast": "ghnato 'pi madhusūdana", "words": "ghnato pi madhusudana"},
    {"fn": "bg_01_35_pada_3.wav", "v": 35, "p": 3, "deva": "अपि त्रैलोक्यराज्यस्य", "iast": "api trailokya-rājyasya", "words": "api trailokyarajyasya"},
    {"fn": "bg_01_35_pada_4.wav", "v": 35, "p": 4, "deva": "हेतोः किं नु महीकृते", "iast": "hetoḥ kiṁ nu mahī-kṛte", "words": "hetoh kim nu mahikrte"},

    # --- Verse 1.36 ---
    {"fn": "bg_01_36_pada_1.wav", "v": 36, "p": 1, "deva": "निहत्य धार्तराष्ट्रान्नः", "iast": "nihatya dhārtarāṣṭrān naḥ", "words": "nihatya dhartarastran nah"},
    {"fn": "bg_01_36_pada_2.wav", "v": 36, "p": 2, "deva": "का प्रीतिः स्याज्जनार्दन", "iast": "kā prītiḥ syāj janārdana", "words": "ka pritih syaj janardana"},
    {"fn": "bg_01_36_pada_3.wav", "v": 36, "p": 3, "deva": "पापमेवाश्रयेदस्मान्", "iast": "pāpam evāśrayed asmān", "words": "papam evasrayed asman"},
    {"fn": "bg_01_36_pada_4.wav", "v": 36, "p": 4, "deva": "हत्वैतानाततायिनः", "iast": "hatvaitān ātatāyinaḥ", "words": "hatvaitan atatayinah"},

    # --- Verse 1.37 ---
    {"fn": "bg_01_37_pada_1.wav", "v": 37, "p": 1, "deva": "तस्मान्नार्हा वयं हन्तुं", "iast": "tasmān nārhā vayaṁ hantuṁ", "words": "tasman narha vayam hantum"},
    {"fn": "bg_01_37_pada_2.wav", "v": 37, "p": 2, "deva": "धार्तराष्ट्रान्सबान्धवान्", "iast": "dhārtarāṣṭrān sa-bāndhavān", "words": "dhartarastran sabandhavan"},
    {"fn": "bg_01_37_pada_3.wav", "v": 37, "p": 3, "deva": "स्वजनं हि कथं हत्वा", "iast": "svajanaṁ hi kathaṁ hatvā", "words": "svajanam hi katham hatva"},
    {"fn": "bg_01_37_pada_4.wav", "v": 37, "p": 4, "deva": "सुखिनः स्याम माधव", "iast": "sukhinaḥ syāma mādhava", "words": "sukhinah syama madhava"},

    # --- Verse 1.38 ---
    {"fn": "bg_01_38_pada_1.wav", "v": 38, "p": 1, "deva": "यद्यप्येते न पश्यन्ति", "iast": "yady apy ete na paśyanti", "words": "yady apy ete na pasyanti"},
    {"fn": "bg_01_38_pada_2.wav", "v": 38, "p": 2, "deva": "लोभोपहतचेतसः", "iast": "lobhopahata-cetasaḥ", "words": "lobhopahatacetasah"},
    {"fn": "bg_01_38_pada_3.wav", "v": 38, "p": 3, "deva": "कुलक्षयकृतं दोषं", "iast": "kula-kṣaya-kṛtaṁ doṣaṁ", "words": "kulaksayakrtam dosam"},
    {"fn": "bg_01_38_pada_4.wav", "v": 38, "p": 4, "deva": "मित्रद्रोहे च पातकम्", "iast": "mitra-drohe ca pātakam", "words": "mitradrohe ca patakam"},

    # --- Verse 1.39 ---
    {"fn": "bg_01_39_pada_1.wav", "v": 39, "p": 1, "deva": "कथं न ज्ञेयमस्माभिः", "iast": "kathaṁ na jñeyam asmābhiḥ", "words": "katham na jneyam asmabhih"},
    {"fn": "bg_01_39_pada_2.wav", "v": 39, "p": 2, "deva": "पापादस्मान्निवर्तितुम्", "iast": "pāpād asmān nivartitum", "words": "papad asman nivartitum"},
    {"fn": "bg_01_39_pada_3.wav", "v": 39, "p": 3, "deva": "कुलक्षयकृतं दोषं", "iast": "kula-kṣaya-kṛtaṁ doṣaṁ", "words": "kulaksayakrtam dosam"},
    {"fn": "bg_01_39_pada_4.wav", "v": 39, "p": 4, "deva": "प्रपश्यद्भिर्जनार्दन", "iast": "prapaśyadbhir janārdana", "words": "prapasyadbhir janardana"},

    # --- Verse 1.40 ---
    {"fn": "bg_01_40_pada_1.wav", "v": 40, "p": 1, "deva": "कुलक्षये प्रणश्यन्ति", "iast": "kula-kṣaye praṇaśyanti", "words": "kulaksaye pranasyanti"},
    {"fn": "bg_01_40_pada_2.wav", "v": 40, "p": 2, "deva": "कुलधर्माः सनातनाः", "iast": "kula-dharmāḥ sanātanāḥ", "words": "kuladharmah sanatanah"},
    {"fn": "bg_01_40_pada_3.wav", "v": 40, "p": 3, "deva": "धर्मे नष्टे कुलं कृत्स्नम्", "iast": "dharme naṣṭe kulaṁ kṛtsnam", "words": "dharme naste kulam krtsnam"},
    {"fn": "bg_01_40_pada_4.wav", "v": 40, "p": 4, "deva": "अधर्मोऽभिभवत्युत", "iast": "adharmo 'bhibhavaty uta", "words": "adharmo bhibhavaty uta"},

    # --- Verse 1.41 ---
    {"fn": "bg_01_41_pada_1.wav", "v": 41, "p": 1, "deva": "अधर्माभिभवात्कृष्ण", "iast": "adharmābhibhavāt kṛṣṇa", "words": "adharmabhibhavat krsna"},
    {"fn": "bg_01_41_pada_2.wav", "v": 41, "p": 2, "deva": "प्रदुष्यन्ति कुलस्त्रियः", "iast": "praduṣyanti kula-striyaḥ", "words": "pradusyanti kulastriyah"},
    {"fn": "bg_01_41_pada_3.wav", "v": 41, "p": 3, "deva": "स्त्रीषु दुष्टासु वार्ष्णेय", "iast": "strīṣu duṣṭāsu vārṣṇeya", "words": "strisu dustasu varsneya"},
    {"fn": "bg_01_41_pada_4.wav", "v": 41, "p": 4, "deva": "जायते वर्णसङ्करः", "iast": "jāyate varṇa-saṅkaraḥ", "words": "jayate varnasankarah"},

    # --- Verse 1.42 ---
    {"fn": "bg_01_42_pada_1.wav", "v": 42, "p": 1, "deva": "सङ्करो नरकायैव", "iast": "saṅkaro narakāyaiva", "words": "sankaro narakayaiva"},
    {"fn": "bg_01_42_pada_2.wav", "v": 42, "p": 2, "deva": "कुलघ्नानां कुलस्य च", "iast": "kula-ghnānāṁ kulasya ca", "words": "kulaghnanam kulasya ca"},
    {"fn": "bg_01_42_pada_3.wav", "v": 42, "p": 3, "deva": "पतन्ति पितरो ह्येषां", "iast": "patanti pitaro hy eṣāṁ", "words": "patanti pitaro hy esam"},
    {"fn": "bg_01_42_pada_4.wav", "v": 42, "p": 4, "deva": "लुप्तपिण्डोदकक्रियाः", "iast": "lupta-piṇḍodaka-kriyāḥ", "words": "luptapindodakakriyah"},

    # --- Verse 1.43 ---
    {"fn": "bg_01_43_pada_1.wav", "v": 43, "p": 1, "deva": "दोषैरेतैः कुलघ्नानां", "iast": "doṣair etaiḥ kula-ghnānāṁ", "words": "dosair etaih kulaghnanam"},
    {"fn": "bg_01_43_pada_2.wav", "v": 43, "p": 2, "deva": "वर्णसङ्करकारकैः", "iast": "varṇa-saṅkara-kārakaiḥ", "words": "varnasankarakarakaih"},
    {"fn": "bg_01_43_pada_3.wav", "v": 43, "p": 3, "deva": "उत्साद्यन्ते जातिधर्माः", "iast": "utsādyante jāti-dharmāḥ", "words": "utsadyante jatidharmah"},
    {"fn": "bg_01_43_pada_4.wav", "v": 43, "p": 4, "deva": "कुलधर्माश्च शाश्वताः", "iast": "kula-dharmāś ca śāśvatāḥ", "words": "kuladharmas ca sasvatah"},

    # --- Verse 1.44 ---
    {"fn": "bg_01_44_pada_1.wav", "v": 44, "p": 1, "deva": "उत्सन्नकुलधर्माणां", "iast": "utsanna-kula-dharmāṇāṁ", "words": "utsannakuladharmanam"},
    {"fn": "bg_01_44_pada_2.wav", "v": 44, "p": 2, "deva": "मनुष्याणां जनार्दन", "iast": "manuṣyāṇāṁ janārdana", "words": "manusyanam janardana"},
    {"fn": "bg_01_44_pada_3.wav", "v": 44, "p": 3, "deva": "नरकेऽनियतं वासो", "iast": "narake 'niyataṁ vāso", "words": "narake niyatam vaso"},
    {"fn": "bg_01_44_pada_4.wav", "v": 44, "p": 4, "deva": "भवतीत्यनुशुश्रुम", "iast": "bhavatīty anuśuśruma", "words": "bhavatity anususruma"},

    # --- Verse 1.45 ---
    {"fn": "bg_01_45_pada_1.wav", "v": 45, "p": 1, "deva": "अहो बत महत्पापं", "iast": "aho bata mahat pāpaṁ", "words": "aho bata mahat papam"},
    {"fn": "bg_01_45_pada_2.wav", "v": 45, "p": 2, "deva": "कर्तुं व्यवसिता वयम्", "iast": "kartuṁ vyavasitā vayam", "words": "kartum vyavasita vayam"},
    {"fn": "bg_01_45_pada_3.wav", "v": 45, "p": 3, "deva": "यद्राज्यसुखलोभेन", "iast": "yad rājya-sukha-lobhena", "words": "yad rajyasukhalobhena"},
    {"fn": "bg_01_45_pada_4.wav", "v": 45, "p": 4, "deva": "हन्तुं स्वजनमुद्यताः", "iast": "hantuṁ svajanam udyatāḥ", "words": "hantum svajanam udyatah"},

    # --- Verse 1.46 ---
    {"fn": "bg_01_46_pada_1.wav", "v": 46, "p": 1, "deva": "यदि मामप्रतीकारम्", "iast": "yadi mām apratīkāram", "words": "yadi mam apratikaram"},
    {"fn": "bg_01_46_pada_2.wav", "v": 46, "p": 2, "deva": "अशस्त्रं शस्त्रपाणयः", "iast": "aśastraṁ śastra-pāṇayaḥ", "words": "asastram sastrapanayah"},
    {"fn": "bg_01_46_pada_3.wav", "v": 46, "p": 3, "deva": "धार्तराष्ट्रा रणे हन्युः", "iast": "dhārtarāṣṭrā raṇe hanyus", "words": "dhartarastra rane hanyus"},
    {"fn": "bg_01_46_pada_4.wav", "v": 46, "p": 4, "deva": "तन्मे क्षेमतरं भवेत्", "iast": "tan me kṣemataraṁ bhavet", "words": "tan me ksemataram bhavet"},

    # --- Verse 1.47 ---
    {"fn": "bg_01_47_speaker.wav", "v": 47, "p": "speaker", "deva": "सञ्जय उवाच", "iast": "sañjaya uvāca", "words": "sanjaya uvaca"},
    {"fn": "bg_01_47_pada_1.wav", "v": 47, "p": 1, "deva": "एवमुक्त्वार्जुनः सङ्ख्ये", "iast": "evam uktvārjunaḥ saṅkhye", "words": "evam uktvarjunah sankhye"},
    {"fn": "bg_01_47_pada_2.wav", "v": 47, "p": 2, "deva": "रथोपस्थ उपाविशत्", "iast": "rathopastha upāviśat", "words": "rathopastha upavisat"},
    {"fn": "bg_01_47_pada_3.wav", "v": 47, "p": 3, "deva": "विसृज्य सशरं चापं", "iast": "visṛjya sa-śaraṁ cāpaṁ", "words": "visrjya sasaram capam"},
    {"fn": "bg_01_47_pada_4.wav", "v": 47, "p": 4, "deva": "शोकसंविग्नमानसः", "iast": "śoka-saṁvigna-mānasaḥ", "words": "sokasamvignamanasah"},

    # --- Chapter 1 Colophon (Puṣpikā) ---
    {"fn": "bg_01_48_colophon_1.wav", "v": 48, "p": 1, "deva": "ॐ तत्सदिति श्रीमद्भगवद्गीतासूपनिषत्सु", "iast": "oṁ tat sad iti śrīmad-bhagavad-gītāsūpaniṣatsu", "words": "om tat sad iti srimad bhagavad gitasupanisatsu"},
    {"fn": "bg_01_48_colophon_2.wav", "v": 48, "p": 2, "deva": "ब्रह्मविद्यायां योगशास्त्रे", "iast": "brahma-vidyāyāṁ yoga-śāstre", "words": "brahma vidyayam yoga sastre"},
    {"fn": "bg_01_48_colophon_3.wav", "v": 48, "p": 3, "deva": "श्रीकृष्णार्जुनसंवादे", "iast": "śrī-kṛṣṇārjuna-saṁvāde", "words": "sri krsnarjuna samvade"},
    {"fn": "bg_01_48_colophon_4.wav", "v": 48, "p": 4, "deva": "अर्जुनविषादयोगो नाम प्रथमोऽध्यायः", "iast": "arjuna-viṣāda-yogo nāma prathamo 'dhyāyaḥ", "words": "arjuna visada yogo nama prathamo dhyayah"}
]

print(f"Total canonical units defined: {len(canonical_units)}")
v_counts = {}
for u in canonical_units:
    v = u['v']
    v_counts[v] = v_counts.get(v, 0) + 1
print(f"Total verses covered: {len(v_counts)} (min={min(v_counts.keys())}, max={max(v_counts.keys())})")
