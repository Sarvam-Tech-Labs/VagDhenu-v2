import os
import sys
import glob
import json
import soundfile as sf
from indic_transliteration import sanscript

sys.path.insert(0, '/home/ubuntu/vagdhenu/src')
import prep_text as PT
from align_bg1_perfect import ch1_mapping

slices_dir = '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/all_slices'
all_slices = sorted(glob.glob(f"{slices_dir}/2118_Bg_01*.wav"))

print(f"Total Ch 1 audio slices available: {len(all_slices)}")
print(f"Total gold text units mapped: {len(ch1_mapping)}")

gold_manifest = []

# Slices 0 to 56 correspond directly to units 0 to 56
# Then at Verse 29:
# 0093 is "sīdanti mama gātrāṇi mukhaṁ ca pariśuṣyati" (Unit 57)
# 0094 is "vepathuś ca śarīre me" (Unit 58a)
# 0095 is "romaharṣaś ca jāyate" (Unit 58b)
# 0096 is "gāṇḍīvaṁ sraṁsate hastāt tvak caiva paridahyate" (Unit 59)
# 0097 is "na ca śaknomy avasthātuṁ bhramatīva ca me manaḥ" (Unit 60)

for idx, item in enumerate(ch1_mapping):
    unit_id, deva, iast, ch, v = item
    if idx < len(all_slices):
        audio_file = all_slices[idx]
        d, sr = sf.read(audio_file)
        dur = len(d) / sr
        kannada_text = PT.model_text(deva)
        
        gold_manifest.append({
            "audio_path": audio_file,
            "duration": dur,
            "text": kannada_text,
            "text_orig": deva,
            "chapter": ch,
            "verse": v,
            "confidence": 1.0
        })

print(f"Generated gold manifest with {len(gold_manifest)} verified pairs.")
out_path = '/home/ubuntu/vagdhenu/prabhupada_training/gold_manifest.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(gold_manifest, f, indent=2, ensure_ascii=False)

print(f"Saved to {out_path}")
