import os
import sys
import glob
import json
import torch
import torchaudio
import soundfile as sf
import numpy as np
from indic_transliteration import sanscript

sys.path.insert(0, '/home/ubuntu/vagdhenu/src')
import prep_text as PT

print("=== Building Clean Prabhupada Gita Dataset ===")
# Load Gita Verses
with open('/home/ubuntu/vagdhenu/prabhupada_training/gita_verses.json') as f:
    verses_raw = json.load(f)

# In Prabhupada's Bhagavad Gita As It Is edition:
# BG 1.28: dṛṣṭvemaṁ svajanaṁ kṛṣṇa yuyutsuṁ samupasthitam
# BG 1.29: sīdanti mama gātrāṇi mukhaṁ ca pariśuṣyati / vepathuś ca śarīre me romaharṣaś ca jāyate
# BG 1.30: gāṇḍīvaṁ sraṁsate hastāt tvak caiva paridahyate / na ca śaknomy avasthātuṁ bhramatīva ca me manaḥ

print(f"Total verse entries: {len(verses_raw)}")

