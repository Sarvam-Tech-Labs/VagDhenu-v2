import os
import sys
import json
import soundfile as sf
import numpy as np

sys.path.insert(0, '/home/ubuntu/vagdhenu/src')
import prep_text as PT
from safe_meter_slicer import slice_track_meter_aware

track_path = '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/clean_tracks/2118_Bg_01_Recitation_of_Bhagavad-gita_Chapter_One.wav'
out_dir = '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/safe_slices_meter_ch1'
os.makedirs(out_dir, exist_ok=True)

slices, sr = slice_track_meter_aware(track_path, min_verse_dur=4.2, max_verse_dur=14.0)
print(f"Total slices extracted from Chapter 1: {len(slices)}")

# Let's write them cleanly named
slice_records = []
for idx, (st, et, dur, chunk) in enumerate(slices):
    fn = f"ch1_slice_{idx:03d}.wav"
    out_p = os.path.join(out_dir, fn)
    sf.write(out_p, chunk, sr)
    slice_records.append({
        "index": idx,
        "filename": fn,
        "path": out_p,
        "start_s": round(st, 2),
        "end_s": round(et, 2),
        "duration_s": round(dur, 2)
    })

with open('/home/ubuntu/vagdhenu/prabhupada_training/ch1_slice_records.json', 'w') as f:
    json.dump(slice_records, f, indent=2)

print("Saved ch1_slice_records.json with all slice metadata.")
