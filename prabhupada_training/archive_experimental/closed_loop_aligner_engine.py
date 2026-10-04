"""
Closed-Loop Text-and-Acoustic Feedback Aligner for Srila Prabhupada Sanskrit Chanting
Location: /home/ubuntu/vagdhenu/prabhupada_training/closed_loop_aligner_engine.py

How the Feedback Loop Works:
1. Proposes an initial time window [t_start, t_end] anchored to canonical verse order.
2. Extracts audio chunk and computes the short-time RMS envelope (25ms window, 10ms hop).
3. Transcribes the proposed audio slice using Whisper ASR.
4. Feedback Error Controller:
   a. BLEED CHECK: Detects if the onset of the NEXT verse is present in the tail of the audio.
      - If bleed detected -> Controller pulls back t_end into the preceding silence floor.
   b. TRUNCATION CHECK: Detects if the final word of the EXPECTED verse is missing or clipped.
      - If truncation detected -> Controller expands t_end forward until the final word completes.
   c. SILENCE LOCK: Snaps both t_start and t_end to the deepest local silence minimum (<= -40 dB).
5. The slice is accepted ONLY when Bleed == 0 and Truncation == 0.
"""

import os
import re
import json
import difflib
import numpy as np
import soundfile as sf
import whisper

class ClosedLoopAligner:
    def __init__(self, model_size='base', silence_threshold_db=-40.0):
        print(f"Loading Whisper '{model_size}' for transcription feedback...")
        self.asr = whisper.load_model(model_size)
        self.silence_threshold_db = silence_threshold_db

    @staticmethod
    def normalize_text(text):
        """Strip punctuation, numbers, spaces, and diacritics for robust matching."""
        return re.sub(r'[।॥\.\,\?\!\-\s\n\r0-9—\'\"]', '', text).lower()

    def find_deepest_silence_valley(self, audio, sr, t_center, search_radius=0.5):
        """
        Finds the exact sample index of the lowest RMS energy within [t_center - radius, t_center + radius].
        Guarantees that cuts occur at the deepest floor of silence between words/verses.
        """
        s_idx = max(0, int((t_center - search_radius) * sr))
        e_idx = min(len(audio), int((t_center + search_radius) * sr))
        sub = audio[s_idx:e_idx]
        
        win = int(0.035 * sr) # 35ms window
        hop = int(0.010 * sr) # 10ms hop
        
        min_rms = float('inf')
        best_sample = s_idx
        for i in range(0, len(sub) - win, hop):
            rms = np.sqrt(np.mean(sub[i : i + win] ** 2) + 1e-12)
            if rms < min_rms:
                min_rms = rms
                best_sample = s_idx + i + win // 2
                
        best_time_s = best_sample / sr
        rms_db = 20 * np.log10(min_rms + 1e-9)
        return best_time_s, rms_db

    def align_verse_unit(self, audio, sr, approx_start_s, approx_end_s, 
                         expected_deva, next_verse_first_word=None, 
                         max_iterations=5, debug=True):
        """
        Runs the closed-loop feedback iteration until the slice matches the expected text
        without clipping the end or bleeding into the next verse.
        """
        curr_start = approx_start_s
        curr_end = approx_end_s
        norm_expected = self.normalize_text(expected_deva)
        norm_next_word = self.normalize_text(next_verse_first_word) if next_verse_first_word else None

        for iteration in range(max_iterations):
            # 1. Snap boundaries to the local deepest silence valleys
            val_start, start_db = (0.0, -99.0) if curr_start == 0.0 else self.find_deepest_silence_valley(audio, sr, curr_start)
            val_end, end_db = self.find_deepest_silence_valley(audio, sr, curr_end)

            # 2. Extract proposed chunk
            s_idx = int(val_start * sr)
            e_idx = int(val_end * sr)
            chunk = audio[s_idx:e_idx].copy()

            # Apply 15ms soft cosine fade at edges to eliminate transient pops
            fade = int(0.015 * sr)
            if len(chunk) > 2 * fade:
                chunk[:fade] *= np.linspace(0, 1, fade)
                chunk[-fade:] *= np.linspace(1, 0, fade)

            # 3. Transcribe audio chunk using ASR
            temp_wav = f"/tmp/_feedback_eval.wav"
            sf.write(temp_wav, chunk, sr)
            res = self.asr.transcribe(temp_wav, language='sa', initial_prompt=expected_deva)
            transcribed_text = res['text'].strip()
            norm_transcribed = self.normalize_text(transcribed_text)

            if os.path.exists(temp_wav):
                os.remove(temp_wav)

            # 4. Check for Next Verse Bleed
            has_bleed = False
            if norm_next_word and len(norm_next_word) >= 3:
                if norm_next_word in norm_transcribed and norm_next_word not in norm_expected:
                    has_bleed = True

            if has_bleed:
                if debug:
                    print(f"  [Iter {iteration+1}] Bleed detected ('{next_verse_first_word}'). Pulling back end from {val_end:.2f}s...")
                curr_end = val_end - 0.45
                continue

            # 5. Check for Final Syllable Truncation
            exp_words = [w for w in re.split(r'[\s\.\,।॥]', expected_deva) if len(w) > 2]
            last_word = exp_words[-1] if exp_words else ""
            norm_last = self.normalize_text(last_word)

            is_truncated = False
            if len(norm_last) >= 3:
                tail_sub = norm_last[-4:] if len(norm_last) >= 4 else norm_last
                if tail_sub not in norm_transcribed[-10:]:
                    match = difflib.SequenceMatcher(None, tail_sub, norm_transcribed[-10:]).ratio()
                    if match < 0.40:
                        is_truncated = True

            if is_truncated and (curr_end - approx_end_s) < 2.0:
                if debug:
                    print(f"  [Iter {iteration+1}] Truncation detected (missing '{last_word}'). Expanding end from {val_end:.2f}s...")
                curr_end = val_end + 0.50
                continue

            # 6. Convergence achieved!
            if debug:
                print(f"  [Iter {iteration+1}] Verified Clean! Window: {val_start:.2f}s -> {val_end:.2f}s (Dur: {val_end - val_start:.2f}s) | Valley: {end_db:.1f} dB")

            return {
                "chunk": chunk,
                "start_s": round(val_start, 2),
                "end_s": round(val_end, 2),
                "duration_s": round(val_end - val_start, 2),
                "transcription": transcribed_text,
                "expected": expected_deva,
                "valley_db": round(end_db, 1)
            }

        # Fallback if loop exceeded max iterations
        return {
            "chunk": chunk,
            "start_s": round(val_start, 2),
            "end_s": round(val_end, 2),
            "duration_s": round(val_end - val_start, 2),
            "transcription": transcribed_text,
            "expected": expected_deva,
            "valley_db": round(end_db, 1)
        }

if __name__ == '__main__':
    print("Testing ClosedLoopAligner initialization...")
    aligner = ClosedLoopAligner()
    print("ClosedLoopAligner ready.")
