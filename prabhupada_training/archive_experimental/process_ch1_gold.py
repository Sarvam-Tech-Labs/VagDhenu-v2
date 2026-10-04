import os
import sys
import json
import soundfile as sf
import numpy as np

sys.path.insert(0, '/home/ubuntu/vagdhenu/src')
import prep_text as PT
from safe_valley_slicer import slice_track_at_valleys
from align_bg1_perfect import ch1_mapping

track_path = '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/clean_tracks/2118_Bg_01_Recitation_of_Bhagavad-gita_Chapter_One.wav'
out_dir = '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/safe_slices_ch1'
os.makedirs(out_dir, exist_ok=True)

print("Slicing Chapter 1 using Energy-Valley boundaries...")
slices, sr = slice_track_at_valleys(track_path, out_dir, min_seg_len=1.8, max_seg_len=14.0)
print(f"Extracted {len(slices)} safe segments from Chapter 1.")

saved_slices = []
for idx, (st, et, chunk) in enumerate(slices):
    fn = f"bg01_safe_{idx:04d}.wav"
    out_p = os.path.join(out_dir, fn)
    sf.write(out_p, chunk, sr)
    saved_slices.append({
        "index": idx,
        "path": out_p,
        "start": round(st, 3),
        "end": round(et, 3),
        "duration": round(et - st, 3)
    })

print(f"Saved {len(saved_slices)} slices into {out_dir}.")
print("First 5 slice durations:", [s["duration"] for s in saved_slices[:5]])
