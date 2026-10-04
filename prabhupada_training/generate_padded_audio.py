# -*- coding: utf-8 -*-
"""
generate_padded_audio.py
Extracts +/- 2.0s padded audio context around each hemistich unit
from the de-hissed master tape, preserving exact sample rate and 100% bit fidelity.
"""

import os
import json
import soundfile as sf
from concurrent.futures import ProcessPoolExecutor

MASTERS = {
    1: '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/clean_tracks_dehissed/2118_Bg_01_Recitation_of_Bhagavad-gita_Chapter_One.wav',
    2: '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/clean_tracks_dehissed/2119_Bg_02_Recitation_of_Bhagavad-gita_Chapter_Two.wav',
    3: '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/clean_tracks_dehissed/2120_Bg_03_Recitation_of_Bhagavad-gita_Chapter_Three.wav'
}

PAD_S = 2.0

def process_chapter(ch):
    master_path = MASTERS[ch]
    data, sr = sf.read(master_path)
    total_len = len(data)
    total_dur = total_len / sr
    
    hemi_manifest_path = f'/home/ubuntu/vagdhenu/demo/static/ch{ch}_all_padas/hemistichs/manifest.json'
    out_dir = f'/home/ubuntu/vagdhenu/demo/static/ch{ch}_all_padas/hemistichs_padded'
    os.makedirs(out_dir, exist_ok=True)
    
    with open(hemi_manifest_path, 'r', encoding='utf-8') as f:
        items = json.load(f)
        
    print(f"[CH{ch}] Processing {len(items)} padded units from master ({total_dur:.1f}s)...")
    
    for it in items:
        fn = it['filename']
        t_st = it['divider_start_s']
        t_et = it['divider_end_s']
        
        # Padded window
        pad_st = max(0.0, t_st - PAD_S)
        pad_et = min(total_dur, t_et + PAD_S)
        
        s_idx = int(round(pad_st * sr))
        e_idx = int(round(pad_et * sr))
        
        slice_data = data[s_idx:e_idx]
        out_fn = os.path.join(out_dir, fn)
        sf.write(out_fn, slice_data, sr)
        
    print(f"[CH{ch}] Successfully created all {len(items)} padded WAV files in {out_dir}!")

if __name__ == '__main__':
    for ch in [1, 2, 3]:
        process_chapter(ch)
