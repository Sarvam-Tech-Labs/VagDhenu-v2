import numpy as np
import soundfile as sf
import os
import json

def find_robust_interverse_valleys(audio, sr, min_silence_s=0.60, silence_threshold_db=-40.0):
    """
    Finds TRUE inter-verse boundaries:
    - Rejects short intra-verse breath pauses (< 0.60s)
    - Detects genuine silence floors (<= -40 dB)
    - Slices at the exact global energy minimum (valley trough) inside the pause
    """
    frame_len = int(0.025 * sr) # 25ms
    hop = int(0.010 * sr)       # 10ms
    
    num_frames = (len(audio) - frame_len) // hop + 1
    rms = np.zeros(num_frames)
    for i in range(num_frames):
        chunk = audio[i * hop : i * hop + frame_len]
        rms[i] = np.sqrt(np.mean(chunk**2) + 1e-12)
        
    rms_db = 20 * np.log10(rms + 1e-6)
    is_silent = rms_db < silence_threshold_db
    
    silent_intervals = []
    in_silence = False
    start_frame = 0
    for i, s in enumerate(is_silent):
        if s and not in_silence:
            in_silence = True
            start_frame = i
        elif not s and in_silence:
            in_silence = False
            dur_s = (i - start_frame) * 0.010
            if dur_s >= min_silence_s:
                silent_intervals.append((start_frame, i))
    if in_silence:
        dur_s = (len(is_silent) - start_frame) * 0.010
        if dur_s >= min_silence_s:
            silent_intervals.append((start_frame, len(is_silent)))
            
    valleys = []
    for sf_idx, ef_idx in silent_intervals:
        sub_rms = rms[sf_idx:ef_idx]
        min_pos = sf_idx + np.argmin(sub_rms)
        valleys.append((min_pos * hop + frame_len // 2) / sr)
        
    return valleys

def slice_track_meter_aware(audio_path, min_verse_dur=4.2, max_verse_dur=14.0):
    audio, sr = sf.read(audio_path)
    valleys = find_robust_interverse_valleys(audio, sr, min_silence_s=0.60, silence_threshold_db=-38.0)
    
    all_bounds = [0.0] + valleys + [len(audio) / sr]
    
    slices = []
    curr_start = all_bounds[0]
    
    for b in all_bounds[1:]:
        dur = b - curr_start
        # If segment is too short to be a full half-verse (unless near end), keep accumulating
        if dur < min_verse_dur:
            continue
            
        start_samp = int(curr_start * sr)
        end_samp = int(b * sr)
        chunk = audio[start_samp:end_samp].copy()
        
        # Check active energy
        chunk_rms = np.sqrt(np.mean(chunk**2) + 1e-9)
        if chunk_rms > 0.008:
            # 15ms soft cosine fade at zero crossings
            fade_len = int(0.015 * sr)
            if len(chunk) > 2 * fade_len:
                chunk[:fade_len] *= np.linspace(0, 1, fade_len)
                chunk[-fade_len:] *= np.linspace(1, 0, fade_len)
            slices.append((curr_start, b, dur, chunk))
        curr_start = b
        
    return slices, sr

print("Safe meter-aware slicer created.")
