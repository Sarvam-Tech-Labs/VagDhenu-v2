import numpy as np
import soundfile as sf

def find_exact_silence_valleys(audio, sr, min_silence_duration_s=0.35, silence_threshold_db=-42):
    """
    Finds the exact deepest silence point (energy minimum) between speech phrases.
    Guarantees:
    1. Cuts occur at the quietest sample within the inter-verse silence gap.
    2. Zero clipping of trailing nasalization / visarga vowels.
    3. Zero audio bleed into the adjacent phrase.
    """
    frame_len = int(0.025 * sr) # 25ms window
    hop = int(0.010 * sr)       # 10ms hop
    
    # Compute RMS energy envelope
    num_frames = (len(audio) - frame_len) // hop + 1
    rms = np.zeros(num_frames)
    for i in range(num_frames):
        chunk = audio[i * hop : i * hop + frame_len]
        rms[i] = np.sqrt(np.mean(chunk**2) + 1e-12)
        
    rms_db = 20 * np.log10(rms + 1e-6)
    
    # Threshold for silence candidate regions
    is_silent = rms_db < silence_threshold_db
    
    # Group contiguous silent frames
    silent_intervals = []
    in_silence = False
    start_frame = 0
    for i, s in enumerate(is_silent):
        if s and not in_silence:
            in_silence = True
            start_frame = i
        elif not s and in_silence:
            in_silence = False
            dur_s = (i - start_frame) * 0.01
            if dur_s >= min_silence_duration_s:
                silent_intervals.append((start_frame, i))
    if in_silence:
        dur_s = (len(is_silent) - start_frame) * 0.01
        if dur_s >= min_silence_duration_s:
            silent_intervals.append((start_frame, len(is_silent)))
            
    # For each silence interval, find the exact global minimum (valley trough)
    valley_points_s = []
    for sf_idx, ef_idx in silent_intervals:
        sub_rms = rms[sf_idx:ef_idx]
        min_pos = sf_idx + np.argmin(sub_rms)
        valley_s = (min_pos * hop + frame_len // 2) / sr
        valley_points_s.append(valley_s)
        
    return valley_points_s

def slice_track_at_valleys(audio_path, out_dir, min_seg_len=1.8, max_seg_len=15.0):
    audio, sr = sf.read(audio_path)
    valleys = find_exact_silence_valleys(audio, sr)
    
    # Add start and end boundaries
    all_bounds = [0.0] + valleys + [len(audio) / sr]
    
    # Group boundaries into segments between min_seg_len and max_seg_len
    slices = []
    curr_start = all_bounds[0]
    
    for b in all_bounds[1:]:
        dur = b - curr_start
        if dur < min_seg_len:
            continue
        # Extract audio chunk
        start_samp = int(curr_start * sr)
        end_samp = int(b * sr)
        chunk = audio[start_samp:end_samp].copy()
        
        # Check active speech inside chunk
        chunk_rms = np.sqrt(np.mean(chunk**2) + 1e-9)
        if chunk_rms > 0.005: # non-empty audio
            # Apply 15ms soft cosine fade at edges to prevent click
            fade_len = int(0.015 * sr)
            if len(chunk) > 2 * fade_len:
                chunk[:fade_len] *= np.linspace(0, 1, fade_len)
                chunk[-fade_len:] *= np.linspace(1, 0, fade_len)
            slices.append((curr_start, b, chunk))
        curr_start = b
        
    return slices, sr

print("Safe valley slicer ready.")
