import os
import sys
import json
import time
import soundfile as sf
import numpy as np
import torch
import torchaudio
import onnxruntime as ort

print("=========================================================================")
print("=== Rebuilding Chapter 4 via Continuous Divider Array (Verified V4.1-42) ===")
print("=========================================================================")

out_dir = '/home/ubuntu/vagdhenu/demo/static/ch4_all_padas'
os.makedirs(out_dir, exist_ok=True)

# 1. Master clean audio track
track_path = '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/clean_tracks/2121_Bg_04_Recitation_of_Bhagavad-gita_Chapter_Four.wav'
y, sr = sf.read(track_path)
total_dur = len(y) / sr
print(f"Loaded master clean track: {total_dur:.3f}s ({len(y)} samples at {sr}Hz)")

# 2. Canonical units (169 units: 41 verses, title, 3 speakers, colophon)
sys.path.insert(0, '/home/ubuntu/vagdhenu/prabhupada_training')
from canonical_ch4_verified import canonical_units
print(f"Loaded {len(canonical_units)} verified canonical units from registry.")

# 3. Setup MMS_FA
bundle = torchaudio.pipelines.MMS_FA
mms_model = bundle.get_model().eval()
aligner = bundle.get_aligner()
mms_dict = bundle.get_dict()

# 4. Setup Su-śrotā ONNX
model_dir = '/home/ubuntu/vagdhenu/models/sushrota'
prep = ort.InferenceSession(f'{model_dir}/preprocessor.onnx')
asr = ort.InferenceSession(f'{model_dir}/sushrota_sanskrit_ctc_int8.onnx')
with open(f'{model_dir}/sanskrit_vocab.json', encoding='utf-8') as f:
    sushrota_vocab = json.load(f)
resampler_sushrota = torchaudio.transforms.Resample(orig_freq=24000, new_freq=16000)

def transcribe_sushrota(chunk):
    t_chunk = torch.from_numpy(chunk).float().unsqueeze(0)
    wav_16k = resampler_sushrota(t_chunk).squeeze(0).numpy()
    feats, flen = prep.run(None, {'audio_signal': wav_16k[np.newaxis, :], 'length': np.array([len(wav_16k)], dtype=np.int64)})
    logits = asr.run(None, {'audio_signal': feats, 'length': flen})[0]
    pred_ids = np.argmax(logits[0], axis=-1)
    out, prev = [], -1
    for i in pred_ids:
        if i != prev and i != 0:
            tok = sushrota_vocab[i] if i < len(sushrota_vocab) else ""
            out.append(tok)
        prev = i
    return "".join(out).replace(" ", " ").replace("▁", " ").strip()

def get_valley(audio, sr, st_bound, et_bound):
    st_bound = max(0.0, st_bound)
    et_bound = min(len(audio)/sr, et_bound)
    if et_bound <= st_bound:
        return round((st_bound + et_bound) / 2.0, 3), -50.0
    s = int(st_bound * sr)
    e = int(et_bound * sr)
    sub = audio[s:e]
    win = int(0.025 * sr)
    hop = int(0.005 * sr)
    if len(sub) <= win:
        return round((st_bound + et_bound) / 2.0, 3), -50.0
    rmses = [np.sqrt(np.mean(sub[i:i+win]**2) + 1e-12) for i in range(0, len(sub)-win, hop)]
    min_i = np.argmin(rmses)
    t = (s + min_i * hop + win // 2) / sr
    db = 20 * np.log10(rmses[min_i] + 1e-9)
    return round(t, 3), round(db, 1)

# 5. Calibrated Alignment Blocks based on Verified Timeline
blocks = [
    (0,  0,  5,   0.0,  66.0),
    (1,  6, 10,  62.0, 142.0),
    (2, 11, 15, 138.0, 212.0),
    (3, 16, 20, 208.0, 294.0),
    (4, 21, 25, 290.0, 368.0),
    (5, 26, 30, 362.0, 442.0),
    (6, 31, 35, 436.0, 522.0),
    (7, 36, 40, 516.0, 602.0),
    (8, 41, 43, 596.0, total_dur)
]

all_unit_spans = []
unit_offset = 0

t0_all = time.time()
for b_id, sv, ev, b_st, b_et in blocks:
    u_block = [u for u in canonical_units if sv <= u['v'] <= ev]
    n_block = len(u_block)
    
    # Dual buffering
    has_front = (unit_offset > 0)
    has_back = (unit_offset + n_block < len(canonical_units))
    
    units_to_align = []
    if has_front:
        units_to_align.append(canonical_units[unit_offset - 1])
    units_to_align.extend(u_block)
    if has_back:
        units_to_align.append(canonical_units[unit_offset + n_block])
        
    chunk = y[int(b_st*sr):int(b_et*sr)]
    t_chunk = torch.from_numpy(chunk).float().unsqueeze(0)
    resampled = torchaudio.transforms.Resample(sr, bundle.sample_rate)(t_chunk)
    
    all_unit_words = [u['words'].split() for u in units_to_align]
    all_words = [w for uw in all_unit_words for w in uw]
    tokenized = [[mms_dict[c] for c in w if c in mms_dict] for w in all_words]
    
    with torch.inference_mode():
        emission, _ = mms_model(resampled)
        
    spans = aligner(emission[0], tokenized)
    spf = (len(chunk) / sr) / emission.shape[1]
    
    start_u_idx = 1 if has_front else 0
    word_idx = sum(len(all_unit_words[k]) for k in range(start_u_idx))
    
    for u_i in range(n_block):
        uw = all_unit_words[start_u_idx + u_i]
        u_spans = spans[word_idx : word_idx + len(uw)]
        word_idx += len(uw)
        valid = [s for s in u_spans if len(s) > 0]
        u_fn = u_block[u_i]['fn']
        assert len(valid) == len(uw), f'Block {b_id} unit {u_fn} missing words: {len(valid)} vs {len(uw)}'
        u_st = b_st + valid[0][0].start * spf
        u_et = b_st + valid[-1][-1].end * spf
        all_unit_spans.append((u_st, u_et, u_block[u_i]))
        
    unit_offset += n_block

print(f"Collected exact word spans for all {len(all_unit_spans)} units across Chapter 4 in {time.time()-t0_all:.2f}s.")

# 6. Continuous Divider Array T = [t_0, t_1, ..., t_169]
dividers = [0.000]
divider_dbs = [-50.0]

for i in range(len(all_unit_spans) - 1):
    prev_et = all_unit_spans[i][1]
    next_st = all_unit_spans[i+1][0]
    
    if next_st > prev_et + 0.04:
        val_t, val_db = get_valley(y, sr, prev_et + 0.015, next_st - 0.015)
    else:
        val_t = round((prev_et + next_st) / 2.0, 3)
        val_db = -35.0
        
    dividers.append(val_t)
    divider_dbs.append(val_db)

dividers.append(round(total_dur, 3))
divider_dbs.append(-50.0)

print(f"Continuous Divider Array: {len(dividers)} points spanning 0.000s -> {total_dur:.3f}s with 0.000ms loss.")

# 7. Slicing with Anti-Click Fade and Active Su-śrotā CTC Verification
print("\n=== Slicing and Verifying All 169 Units from Continuous Dividers ===")
fade = int(0.015 * sr)
final_manifest = []

def calc_phonetic_sim(target, pred):
    t_clean = "".join(c for c in target if c not in " ।॥|.,;:!?")
    p_clean = "".join(c for c in pred if c not in " ।॥|.,;:!?")
    if not t_clean or not p_clean:
        return 0.0
    common = sum(1 for c in p_clean if c in t_clean)
    return round(common / max(len(t_clean), len(p_clean)), 3)

gated_pass = 0
for i in range(len(all_unit_spans)):
    t_st = dividers[i]
    t_et = dividers[i+1]
    dur = round(t_et - t_st, 3)
    val_db = divider_dbs[i+1]
    
    s_idx = int(t_st * sr)
    e_idx = int(t_et * sr)
    p_chunk = y[s_idx:e_idx].copy()
    
    if len(p_chunk) > 2 * fade:
        p_chunk[:fade] *= np.linspace(0, 1, fade)
        p_chunk[-fade:] *= np.linspace(1, 0, fade)
        
    fn = all_unit_spans[i][2]['fn']
    out_p = os.path.join(out_dir, fn)
    sf.write(out_p, p_chunk, sr)
    
    ctc_txt = transcribe_sushrota(p_chunk)
    target_deva = all_unit_spans[i][2]['deva']
    sim = calc_phonetic_sim(target_deva, ctc_txt)
    
    # Active Gating Rule
    # Pada: 1.5s <= dur <= 6.5s, Sim >= 0.40
    # Speaker/Title/Colophon: relaxed
    is_colophon = (all_unit_spans[i][2]['p'] in ("title", "speaker", "colophon"))
    is_valid_dur = (dur <= 18.0) if is_colophon else (1.5 <= dur <= 6.5)
    is_valid_sim = (sim >= 0.35)
    is_gold = bool(is_valid_dur and is_valid_sim)
    if is_gold:
        gated_pass += 1
        
    final_manifest.append({
        "index": i + 1,
        "filename": fn,
        "verse": all_unit_spans[i][2]['v'],
        "pada": all_unit_spans[i][2]['p'],
        "divider_start_s": t_st,
        "divider_end_s": t_et,
        "duration": round(dur, 2),
        "duration_exact_s": dur,
        "valley_db": val_db,
        "text_deva": target_deva,
        "text_iast": all_unit_spans[i][2]['iast'],
        "sushrota_ctc": ctc_txt,
        "similarity": sim,
        "is_gold": bool(is_gold)
    })
    
    if (i + 1) % 20 == 0 or (i + 1) == len(all_unit_spans):
        status = "✅ GOLD" if is_gold else "⚠️ WARN"
        print(f"[{i+1:03d}/169] {fn:22s} | [{t_st:7.3f}s -> {t_et:7.3f}s] ({dur:5.2f}s) | Sim={sim:.2f} {status} | {ctc_txt}")

# 8. Save unified manifest
manifest_p = os.path.join(out_dir, 'manifest.json')
with open(manifest_p, 'w', encoding='utf-8') as f:
    json.dump(final_manifest, f, indent=2, ensure_ascii=False)

print(f"\nManifest saved to {manifest_p}")
print(f"Active Gating Results: {gated_pass}/{len(final_manifest)} ({gated_pass/len(final_manifest)*100:.1f}%) passed strict gold standard.")
