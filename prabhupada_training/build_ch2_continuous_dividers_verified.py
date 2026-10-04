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
print("=== Rebuilding Chapter 2 via Continuous Divider Array (Verified V2.1-72) ===")
print("=== Source: De-Hissed Master Track (Hybrid Surgical Split + NL-Means)  ===")
print("=========================================================================")

out_dir = '/home/ubuntu/vagdhenu/demo/static/ch2_all_padas'
hemi_dir = os.path.join(out_dir, 'hemistichs')
os.makedirs(out_dir, exist_ok=True)
os.makedirs(hemi_dir, exist_ok=True)

# 1. Master de-hissed audio track
track_path = '/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/clean_tracks_dehissed/2119_Bg_02_Recitation_of_Bhagavad-gita_Chapter_Two.wav'
y, sr = sf.read(track_path)
total_dur = len(y) / sr
print(f"Loaded master de-hissed track: {total_dur:.3f}s ({len(y)} samples at {sr}Hz)")

# 2. Canonical units (292 verified authentic units from BBT 1972)
sys.path.insert(0, '/home/ubuntu/vagdhenu/prabhupada_training')
from canonical_ch2_all import canonical_units
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

# 5. Continuous 14-Block Alignment
blocks = [
    (0,  0,  5,   0.0, 105.0),
    (1,  6, 10,  92.0, 198.0),
    (2, 11, 15, 185.0, 270.0),
    (3, 16, 20, 258.0, 345.0),
    (4, 21, 25, 330.0, 422.0),
    (5, 26, 30, 410.0, 495.0),
    (6, 31, 35, 482.0, 564.0),
    (7, 36, 40, 561.0, 638.0),
    (8, 41, 45, 625.0, 700.0),
    (9, 46, 50, 685.0, 762.0),
    (10, 51, 55, 750.0, 825.0),
    (11, 56, 60, 812.0, 885.0),
    (12, 61, 65, 870.0, 945.0),
    (13, 66, 72, 932.0, min(1030.3, total_dur)),
]

all_unit_spans = []
t0_all = time.time()

for b_id, start_v, end_v, b_st, b_et in blocks:
    units = [u for u in canonical_units if start_v <= u['v'] <= end_v]
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

print(f"Collected exact word spans for all {len(all_unit_spans)} units across Chapter 2 in {time.time()-t0_all:.2f}s.")

# 6. Build the Continuous Divider Array T = [t_0, t_1, ..., t_292]
dividers = [0.000]
divider_dbs = [-50.0]

for i in range(len(all_unit_spans) - 1):
    prev_et = all_unit_spans[i][1]
    next_st = all_unit_spans[i+1][0]
    
    if all_unit_spans[i][2]['v'] == 5 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 98.500, -56.8
    elif all_unit_spans[i][2]['v'] == 6 and all_unit_spans[i][2]['p'] == 2:
        val_t, val_db = 110.000, -58.0
    elif all_unit_spans[i][2]['v'] == 10 and all_unit_spans[i][2]['p'] == 4:
        # Verse 2.10 ends at 188.5s, followed by silence until 190.5s where speaker tag begins
        val_t, val_db = 189.500, -58.0
    elif all_unit_spans[i][2]['v'] == 11 and all_unit_spans[i][2].get('is_speaker'):
        # Speaker tag ends at 191.4s, followed by silence until 193.4s where Verse 2.11 starts
        val_t, val_db = 192.500, -55.0
    elif all_unit_spans[i][2]['v'] == 14 and all_unit_spans[i][2]['p'] == 2:
        val_t, val_db = 242.200, -58.0
    elif all_unit_spans[i][2]['v'] == 15 and all_unit_spans[i][2]['p'] == 4:
        # Verse 2.15 ends at 262.7s, followed by silence until 264.4s where nāsato begins
        val_t, val_db = 263.500, -57.5
    elif all_unit_spans[i][2]['v'] == 18 and all_unit_spans[i][2]['p'] == 2:
        val_t, val_db = 299.000, -55.0
    elif all_unit_spans[i][2]['v'] == 20 and all_unit_spans[i][2]['p'] == 2:
        val_t, val_db = 329.000, -58.0
    elif all_unit_spans[i][2]['v'] == 20 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 338.750, -56.0
    elif all_unit_spans[i][2]['v'] == 24 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 399.000, -56.0
    elif all_unit_spans[i][2]['v'] == 25 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 415.000, -56.0
    elif all_unit_spans[i][2]['v'] == 28 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 456.250, -56.0
    elif all_unit_spans[i][2]['v'] == 29 and all_unit_spans[i][2]['p'] == 2:
        val_t, val_db = 466.250, -56.0
    elif all_unit_spans[i][2]['v'] == 30 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 489.500, -56.0
    elif all_unit_spans[i][2]['v'] == 35 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 563.750, -56.0
    elif all_unit_spans[i][2]['v'] == 40 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 632.000, -56.0
    elif all_unit_spans[i][2]['v'] == 50 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 756.350, -56.0
    elif all_unit_spans[i][2]['v'] == 55 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 820.500, -56.0
    elif all_unit_spans[i][2]['v'] == 64 and all_unit_spans[i][2]['p'] == 2:
        val_t, val_db = 923.250, -56.0
    elif all_unit_spans[i][2]['v'] == 65 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 942.350, -56.0
    elif all_unit_spans[i][2]['v'] == 68 and all_unit_spans[i][2]['p'] == 2:
        val_t, val_db = 974.400, -56.0
    elif all_unit_spans[i][2]['v'] == 69 and all_unit_spans[i][2]['p'] == 4:
        val_t, val_db = 998.500, -56.0
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
print("\n=== Slicing and Verifying All 292 Single Pāda Units ===")
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
    
    if (i + 1) % 35 == 0 or (i + 1) == len(all_unit_spans):
        status = "✅ GOLD" if is_gold else "⚠️ WARN"
        print(f"[{i+1:03d}/292] {fn:22s} | [{t_st:7.3f}s -> {t_et:7.3f}s] ({dur:5.2f}s) | Sim={sim:.2f} {status} | {ctc_txt}")

# Save Tier 1 manifest
manifest_p = os.path.join(out_dir, 'manifest.json')
with open(manifest_p, 'w', encoding='utf-8') as f:
    json.dump(pada_manifest, f, indent=2, ensure_ascii=False)
print(f"Tier 1 Pāda Manifest saved ({gated_pass}/{len(pada_manifest)} Gold Pass).")

# 8. Slicing Tier 2: Two Pādas Combined (Hemistichs)
print("\n=== Slicing and Verifying Tier 2: Two Pādas Combined (Hemistichs) ===")
hemi_manifest = []
i = 0
h_idx = 1
hemi_gold = 0

while i < len(pada_manifest):
    curr = pada_manifest[i]
    if curr['pada'] in ('title', 'speaker', 'colophon'):
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
        fn = f'bg_02_{v_num:02d}_line_{p1}_{p2}.wav'
        deva = f"{u[0]['text_deva']} {u[1]['text_deva']}"
        iast = f"{u[0]['text_iast']} {u[1]['text_iast']}"
        p_tag = f"{p1}+{p2}"
    else:
        fn = u[0]['filename'].replace('pada_', 'line_')
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
    
    if h_idx % 25 == 0 or h_idx == 1:
        print(f"H[{h_idx:03d}] {fn:24s} | [{t_st:7.3f}s -> {t_et:7.3f}s] ({dur:5.2f}s) | Sim={sim:.2f} {'✅ GOLD' if is_gold else '⚠️ WARN'} | {ctc}")
    h_idx += 1

hemi_manifest_p = os.path.join(hemi_dir, 'manifest.json')
with open(hemi_manifest_p, 'w', encoding='utf-8') as f:
    json.dump(hemi_manifest, f, indent=2, ensure_ascii=False)
print(f"Tier 2 Hemistich Manifest saved ({hemi_gold}/{len(hemi_manifest)} Gold Pass).")

print(f"\n=======================================================")
print(f"=== Chapter 2 Dual-Tier Rebuild Complete! ===")
print(f"Single Pādas:  {len(pada_manifest)} units ({gated_pass}/{len(pada_manifest)} Gold - {gated_pass/len(pada_manifest)*100:.1f}%)")
print(f"2-Pāda Combos: {len(hemi_manifest)} units ({hemi_gold}/{len(hemi_manifest)} Gold - {hemi_gold/len(hemi_manifest)*100:.1f}%)")
print(f"=======================================================")
