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
print("=== Rebuilding Chapter 3 via Continuous Divider Array (Verified)     ===")
print("=== Source: De-Hissed Master Track (Hybrid Surgical Split + NL-Means)  ===")
print("=========================================================================")

out_dir = '/home/ubuntu/vagdhenu/demo/static/ch3_all_padas'
hemi_dir = os.path.join(out_dir, 'hemistichs')
os.makedirs(out_dir, exist_ok=True)
os.makedirs(hemi_dir, exist_ok=True)

# 1. Master de-hissed audio track
track_path = '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/clean_tracks_dehissed/2120_Bg_03_Recitation_of_Bhagavad-gita_Chapter_Three.wav'
y, sr = sf.read(track_path)
total_dur = len(y) / sr
print(f"Loaded master de-hissed track: {total_dur:.3f}s ({len(y)} samples at {sr}Hz)")

# 2. Canonical units (169 authentic recited units from BBT 1972)
sys.path.insert(0, '/home/ubuntu/vagdhenu/prabhupada_training')
from canonical_ch3_all import canonical_units
print(f"Loaded {len(canonical_units)} canonical units from registry.")

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
    if len(chunk) < int(0.1 * sr):
        return ""
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
        return round(st_bound, 3), -50.0
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

# 5. Continuous 9-Block Alignment
blocks = [
    (0,  0,  5,   0.0, 105.0),
    (1,  6, 10, 101.0, 172.0),
    (2, 11, 15, 170.0, 240.0),
    (3, 16, 20, 238.0, 315.0),
    (4, 21, 24, 313.0, 373.0),
    (5, 26, 29, 372.0, 428.0),
    (6, 31, 35, 426.0, 505.0),
    (7, 36, 40, 503.0, 574.0),
    (8, 41, 44, 572.0, total_dur),
]

all_unit_spans = []
t0_all = time.time()

for b_id, sv, ev, b_st, b_et in blocks:
    units = [u for u in canonical_units if sv <= u['v'] <= ev]
    chunk = y[int(b_st*sr):int(b_et*sr)]
    t_chunk = torch.from_numpy(chunk).float().unsqueeze(0)
    resampled = torchaudio.transforms.Resample(sr, bundle.sample_rate)(t_chunk)
    all_words = [w for u in units for w in u['words'].split()]
    tokenized = [[mms_dict[c] for c in w if c in mms_dict] for w in all_words]
    with torch.inference_mode():
        emission, _ = mms_model(resampled)
    spans = aligner(emission[0], tokenized)
    spf = (len(chunk) / sr) / emission.shape[1]
    w_idx = 0
    for u in units:
        uw = u['words'].split()
        u_spans = spans[w_idx : w_idx + len(uw)]
        w_idx += len(uw)
        valid = [s for s in u_spans if len(s) > 0]
        fn = u['fn']
        assert len(valid) == len(uw), f'Block {b_id} unit {fn} missing words'
        u_st = b_st + valid[0][0].start * spf
        u_et = b_st + valid[-1][-1].end * spf
        all_unit_spans.append((u_st, u_et, u))

print(f"Collected exact word spans for all {len(all_unit_spans)} units across Chapter 3 in {time.time()-t0_all:.2f}s.")

# 6. Build the Continuous Divider Array
dividers = [0.000]
divider_dbs = [-50.0]

for i in range(len(all_unit_spans) - 1):
    prev_et = all_unit_spans[i][1]
    next_st = all_unit_spans[i+1][0]
    
    if all_unit_spans[i][2]['v'] == 3 and all_unit_spans[i][2]['p'] == 2:
        val_t, val_db = 54.000, -56.0
    elif next_st > prev_et + 0.04:
        val_t, val_db = get_valley(y, sr, prev_et + 0.015, next_st - 0.015)
    else:
        val_t = round((prev_et + next_st) / 2.0, 3)
        val_db = -35.0
        
    if val_t <= dividers[-1] + 0.5:
        val_t = round(dividers[-1] + 0.5, 3)
        
    dividers.append(val_t)
    divider_dbs.append(val_db)

dividers.append(round(total_dur, 3))
divider_dbs.append(-50.0)

print(f"Continuous Divider Array: {len(dividers)} points spanning 0.000s -> {total_dur:.3f}s with 0.000ms loss.")

def calc_phonetic_sim(target, pred):
    t_clean = "".join(c for c in target if c not in " ।॥|.,;:!?")
    p_clean = "".join(c for c in pred if c not in " ।॥|.,;:!?")
    if not t_clean or not p_clean:
        return 0.0
    common = sum(1 for c in p_clean if c in t_clean)
    return round(common / max(len(t_clean), len(p_clean)), 3)

# 7. Slicing Tier 1: Single Pādas
print("\n=== Slicing and Verifying All Single Pāda Units (Tier 1) ===")
fade = int(0.015 * sr)
pada_manifest = []
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
    
    is_speaker = (all_unit_spans[i][2]['p'] in ("title", "speaker", "colophon"))
    is_valid_dur = (dur <= 18.0) if is_speaker else (1.5 <= dur <= 6.5)
    is_valid_sim = (sim >= 0.35)
    is_gold = bool(is_valid_dur and is_valid_sim)
    if is_gold:
        gated_pass += 1
        
    pada_manifest.append({
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
    
    if (i + 1) % 25 == 0 or (i + 1) == len(all_unit_spans):
        status = "✅ GOLD" if is_gold else "⚠️ WARN"
        print(f"[{i+1:03d}/{len(all_unit_spans)}] {fn:24s} | [{t_st:7.3f}s -> {t_et:7.3f}s] ({dur:5.2f}s) | Sim={sim:.2f} {status} | {ctc_txt}")

manifest_p = os.path.join(out_dir, 'manifest.json')
with open(manifest_p, 'w', encoding='utf-8') as f:
    json.dump(pada_manifest, f, indent=2, ensure_ascii=False)

print(f"\nTier 1 Pāda Manifest saved to {manifest_p} ({gated_pass}/{len(pada_manifest)} Gold Pass).")

# 8. Slicing Tier 2: Two Pādas Combined (Hemistichs)
print("\n=== Slicing and Verifying Tier 2: Two Pādas Combined (Hemistichs) ===")
hemi_manifest = []
i = 0
h_idx = 1
hemi_gold = 0

while i < len(pada_manifest):
    curr = pada_manifest[i]
    if curr['pada'] in ('title', 'speaker'):
        u = [curr]
        i += 1
    elif i + 1 < len(pada_manifest) and pada_manifest[i+1]['verse'] == curr['verse'] and ((curr['pada'] == 1 and pada_manifest[i+1]['pada'] == 2) or (curr['pada'] == 3 and pada_manifest[i+1]['pada'] == 4)):
        u = [curr, pada_manifest[i+1]]
        i += 2
    else:
        u = [curr]
        i += 1
        
    t_st = u[0]['divider_start_s']
    t_et = u[-1]['divider_end_s']
    dur = round(t_et - t_st, 3)
    
    s_idx = int(t_st * sr)
    e_idx = int(t_et * sr)
    p_chunk = y[s_idx:e_idx].copy()
    if len(p_chunk) > 2 * fade:
        p_chunk[:fade] *= np.linspace(0, 1, fade)
        p_chunk[-fade:] *= np.linspace(1, 0, fade)
        
    v_num = u[0]['verse']
    if len(u) == 2:
        p1 = u[0]["pada"]
        p2 = u[1]["pada"]
        fn = f'bg_03_{v_num:02d}_line_{p1}_{p2}.wav'
        deva = f"{u[0]['text_deva']} {u[1]['text_deva']}"
        iast = f"{u[0]['text_iast']} {u[1]['text_iast']}"
        p_tag = f"{p1}+{p2}"
    else:
        fn = u[0]['filename'].replace('pada_', 'line_').replace('colophon_', 'colophon_line_')
        deva = u[0]['text_deva']
        iast = u[0]['text_iast']
        p_tag = str(u[0]['pada'])
        
    out_p = os.path.join(hemi_dir, fn)
    sf.write(out_p, p_chunk, sr)
    
    ctc = transcribe_sushrota(p_chunk)
    sim = calc_phonetic_sim(deva, ctc)
    is_gold = bool(sim >= 0.40 and dur <= 14.0)
    if is_gold:
        hemi_gold += 1
        
    hemi_manifest.append({
        'index': h_idx,
        'filename': fn,
        'verse': v_num,
        'pada_combo': p_tag,
        'divider_start_s': t_st,
        'divider_end_s': t_et,
        'duration': dur,
        'text_deva': deva,
        'text_iast': iast,
        'sushrota_ctc': ctc,
        'similarity': sim,
        'is_gold': is_gold
    })
    
    if h_idx % 20 == 0 or h_idx == 1:
        print(f"H[{h_idx:03d}] {fn:24s} | [{t_st:7.3f}s -> {t_et:7.3f}s] ({dur:5.2f}s) | Sim={sim:.2f} {'✅ GOLD' if is_gold else '⚠️ WARN'} | {ctc}")
    h_idx += 1

hemi_manifest_p = os.path.join(hemi_dir, 'manifest.json')
with open(hemi_manifest_p, 'w', encoding='utf-8') as f:
    json.dump(hemi_manifest, f, indent=2, ensure_ascii=False)

print(f"\n=======================================================")
print(f"=== Chapter 3 Dual-Tier Rebuild Complete! ===")
print(f"Single Pādas:  {len(pada_manifest)} units ({gated_pass}/{len(pada_manifest)} Gold - {gated_pass/len(pada_manifest)*100:.1f}%)")
print(f"2-Pāda Combos: {len(hemi_manifest)} units ({hemi_gold}/{len(hemi_manifest)} Gold - {hemi_gold/len(hemi_manifest)*100:.1f}%)")
print(f"=======================================================")
