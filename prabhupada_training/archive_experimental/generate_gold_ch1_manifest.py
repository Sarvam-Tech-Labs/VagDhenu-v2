import os
import sys
import json
import soundfile as sf
import numpy as np

sys.path.insert(0, '/home/ubuntu/vagdhenu/src')
import prep_text as PT
from align_bg1_perfect import ch1_mapping

# Track path
track_path = '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/clean_tracks/2118_Bg_01_Recitation_of_Bhagavad-gita_Chapter_One.wav'
y, sr = sf.read(track_path)
print(f"Loaded track 1: {len(y)/sr:.2f}s at {sr}Hz")

out_dir = '/home/ubuntu/vagdhenu/prabhupada_training/gold_ch1_slices'
os.makedirs(out_dir, exist_ok=True)

# Slices from all_slices directory
slices_dir = '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/all_slices'

gold_manifest = []

# Map the exact verified slice indices
# Let's inspect the exact audio slices for the 95 units
# For each unit in ch1_mapping:
# (index, deva_text, iast_text, chapter, verse)
# Slice indices in all_slices correspond sequentially to the chanting pauses:
# 0000 -> Unit 0 (Dharmakshetre...)
# 0001 -> Unit 1 (Māmakāḥ...)
# 0002 -> Unit 2 (Sanjaya uvāca dṛṣṭvā tu...)
# 0003 -> Unit 3 (Vyūḍhaṁ duryodhanas tadā...)
# 0004 -> Unit 4 (Ācāryam upasaṅgamya...)
# ...
# 0093 -> Unit 57 (Sīdanti mama gātrāṇi...)
# 0094 -> Unit 58 (Vepathuś ca śarīre me...)
# 0095 -> Unit 58 (Romaharṣaś ca jāyate...)
# 0096 -> Unit 59 (Gāṇḍīvaṁ sraṁsate hastāt...)
# 0097 -> Unit 60 (Na ca śaknomy avasthātuṁ...)

print("Building gold dataset with exact Kannada transliteration...")
