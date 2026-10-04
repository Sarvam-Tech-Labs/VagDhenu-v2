import os
import sys
import glob
import json
import soundfile as sf
import numpy as np

def extract_safe_slice(audio, sr, start_s, end_s, pad_head_s=0.08, pad_tail_s=0.25):
    """
    Extract slice with:
    - 80ms head safety buffer (never cut the initial consonant/plosive)
    - 250ms tail safety buffer (preserve full nasalization/visarga fade-out)
    - 15ms cosine soft fade-in and fade-out to prevent pop/click transients
    """
    start_sample = max(0, int((start_s - pad_head_s) * sr))
    end_sample = min(len(audio), int((end_s + pad_tail_s) * sr))
    
    chunk = audio[start_sample:end_sample].copy()
    
    # 15ms cosine fade
    fade_len = int(0.015 * sr)
    if len(chunk) > 2 * fade_len:
        chunk[:fade_len] *= np.linspace(0, 1, fade_len)
        chunk[-fade_len:] *= np.linspace(1, 0, fade_len)
        
    return chunk

print("Safe boundary slicer defined.")
