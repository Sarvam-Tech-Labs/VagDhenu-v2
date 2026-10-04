import json
import soundfile as sf
import os
import sys

sys.path.insert(0, '/home/ubuntu/vagdhenu/src')
import prep_text as PT

with open('/home/ubuntu/vagdhenu/prabhupada_training/gita_verses.json') as f:
    gita = json.load(f)

ch1_verses = [v for v in gita if v['chapter_number'] == 1]
print(f"Total Gita Chapter 1 verses in DB: {len(ch1_verses)}")

# Load slice records
with open('/home/ubuntu/vagdhenu/prabhupada_training/ch1_slice_records.json') as f:
    slices = json.load(f)
print(f"Total slices in Chapter 1: {len(slices)}")

# Let's inspect ch1_mapping from align_bg1_perfect.py
from align_bg1_perfect import ch1_mapping
print(f"Total reference mapped units in Chapter 1: {len(ch1_mapping)}")
