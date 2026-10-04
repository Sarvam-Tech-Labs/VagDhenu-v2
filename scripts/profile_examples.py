# -*- coding: utf-8 -*-
"""
profile_examples.py — Detailed stage-by-stage latency profiler across the 6 UI sample shlokas
and 3 speed/quality modes on 24-OCPU AMD Genoa hardware.
"""

import os
import sys
import time
import json
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
BIGVGAN_DIR = os.path.join(ROOT, "BigVGAN")

if SRC not in sys.path: sys.path.insert(0, SRC)
if BIGVGAN_DIR not in sys.path: sys.path.insert(0, BIGVGAN_DIR)

from indic_transliteration import sanscript as _S
from render_core import Renderer, split_padas, detect_meter_key, PT, _satva, _danda_fix, _visarga_ksha, _anusvara_m, _hna_metathesis, _vocalic_l, n_aksharas, _ends_halant, SR, gate
from chandas_bridge import analyze_verse_meter
from f5_tts.infer.utils_infer import infer_process
from concurrent.futures import ThreadPoolExecutor

MODELS_DIR = os.path.join(ROOT, "models")
BANK  = os.path.join(SRC, "reference_bank", "bank.json")
VOCAB = os.path.join(MODELS_DIR, "vocab.txt")
VOICE = os.path.join(MODELS_DIR, "voice_steer_ema_2026-06-17.pt")
VOC   = os.path.join(MODELS_DIR, "voc_bigvgan_EMA_2026-06-11.pth")

# Load Renderer
renderer = Renderer(VOICE, VOC, BANK, device="cpu", vocab_file=VOCAB, nfe=8, num_workers=2, use_bf16=True)

_MAL = ("हठलुठ दल घिष्टोत्कण्ठदष्टोष्ठ विद्युत्\nसटशठ कठिनोरः पीठभित्सुष्ठुनिष्ठाम् ।\n"
        "पठतिनुतव कण्ठाधिष्ठ घोरान्त्रमाला\nदह दह नरसिंहासह्यवीर्याहितं मे ॥")
_KAR = "कराग्रे वसते लक्ष्मीः करमध्ये सरस्वती ।\nकरमूले तु गोविन्दः प्रभाते करदर्शनम् ॥"

def _tx(d, sch):
    return d if sch == _S.DEVANAGARI else _S.transliterate(d, _S.DEVANAGARI, sch)

SAMPLES = [
    ("Kṛṣṇa — Vasudevasutaṃ (Devanagari)", "वसुदेवसुतं देवं कंसचाणूरमर्दनम् ।\nदेवकीपरमानन्दं कृष्णं वन्दे जगद्गुरुम् ॥", _S.DEVANAGARI, "__auto__"),
    ("Viṣṇu — Śuklāmbaradharaṃ (Devanagari)", "शुक्लाम्बरधरं विष्णुं शशिवर्णं चतुर्भुजम् ।\nप्रसन्नवदनं ध्यायेत् सर्वविघ्नोपशान्तये ॥", _S.DEVANAGARI, "__auto__"),
    ("Narasiṃha — retroflex tongue-twister (mālinī)", _MAL, _S.DEVANAGARI, "mālinī"),
    ("Karāgre vasate — jihvāmūlīya + upadhmānīya", _KAR, _S.DEVANAGARI, "__auto__"),
    ("Guru — Gururbrahmā (Kannada script)", "गुरुर्ब्रह्मा गुरुर्विष्णुः गुरुर्देवो महेश्वरः ।\nगुरुः साक्षात् परं ब्रह्म तस्मै श्रीगुरवे नमः ॥", _S.KANNADA, "__auto__"),
    ("Sarasvatī — Namastubhyaṃ (Telugu script)", "सरस्वति नमस्तुभ्यं वरदे कामरूपिणि ।\nविद्यारम्भं करिष्यामि सिद्धिर्भवतु मे सदा ॥", _S.TELUGU, "__auto__"),
]

MODES = [
    ("⚡ Fast (NFE=8)", 8),
    ("🚀 High Quality (NFE=16)", 16),
    ("💎 Studio Fidelity (NFE=32)", 32),
]

def profile_single_run(name, text, raw_meter, nfe_step, seed=60):
    t_start = time.perf_counter()

    # Step 1: Transliteration & Meter Detection
    t0 = time.perf_counter()
    if raw_meter == "__auto__":
        m_info = analyze_verse_meter(text)
        detected_meter = m_info.get("bank_key", "anuṣṭubh")
        meter_name = m_info.get("name", detected_meter)
    else:
        detected_meter = raw_meter
        meter_name = raw_meter
    t_meter = time.perf_counter() - t0

    # Step 2: Prosody-First Pāda Segmentation
    t0 = time.perf_counter()
    padas = split_padas(text)
    t_segment = time.perf_counter() - t0

    # Step 3: Text Preprocessing & Prime Matching
    t0 = time.perf_counter()
    ref_audio, ref_t, ref_sps, ref_len = renderer._get_ref(detected_meter)
    spd = renderer.speed

    def _basetext(p):
        return PT.model_text_sandhi(p, echo_final=False)
    PIECES = [_basetext(p) for p in padas]
    PIECES = [_satva(x) for x in PIECES]
    PIECES = [_danda_fix(_visarga_ksha(_anusvara_m(x))) for x in PIECES]
    PIECES = [_hna_metathesis(x) for x in PIECES]
    PIECES = [_vocalic_l(x) for x in PIECES]
    NSYLL = [n_aksharas(x) for x in PIECES]
    GAPS = [np.zeros(int(renderer.gap*SR) + (int(renderer.gap_halant*SR) if _ends_halant(_p) else 0),
                     dtype=np.float32) for _p in PIECES]
    t_prep = time.perf_counter() - t0

    # Step 4: Flow Matching DiT Inference (Concurrent pāda synthesis)
    t0 = time.perf_counter()
    per_pada_dit = []
    per_pada_bvgan = []
    
    def _worker(item):
        idx, p = item
        torch.set_num_threads(12)
        _fixd = (ref_len + NSYLL[idx]*ref_sps) if (ref_sps > 0 and NSYLL) else None
        
        td0 = time.perf_counter()
        with torch.inference_mode():
            with torch.autocast("cpu", dtype=torch.bfloat16):
                w, sr, _ = infer_process(ref_audio, ref_t, p, renderer.cfm, renderer.cap,
                                         mel_spec_type="vocos", speed=spd, nfe_step=nfe_step,
                                         cfg_strength=renderer.cfg, device="cpu", fix_duration=_fixd)
        dit_time = time.perf_counter() - td0
        last_mel = getattr(renderer.cap.local, "last", renderer.cap.last).copy()

        tv0 = time.perf_counter()
        y = renderer._bvgan(last_mel)
        mx = np.abs(y).max()
        if mx > 1: y = y/mx*0.97
        bvgan_time = time.perf_counter() - tv0

        return idx, y, dit_time, bvgan_time

    with ThreadPoolExecutor(max_workers=min(2, len(PIECES))) as ex:
        results = list(ex.map(_worker, enumerate(PIECES)))
    results.sort(key=lambda x: x[0])
    t_synth_wall = time.perf_counter() - t0

    bseg = [r[1] for r in results]
    dit_times = [r[2] for r in results]
    bvgan_times = [r[3] for r in results]

    # Step 5: Stitching & Gating
    t0 = time.perf_counter()
    _slp = PT.align_slp1(padas[0])
    fric = bool(_slp) and _slp[0] in ("S", "z", "s", "h")
    halant = _ends_halant(PIECES[-1])
    final = renderer._stitch(bseg, GAPS, fric=fric, halant=halant)
    t_stitch = time.perf_counter() - t0

    total_latency = time.perf_counter() - t_start
    audio_dur = len(final) / SR

    return {
        "example": name,
        "meter_name": meter_name,
        "bank_key": detected_meter,
        "num_padas": len(PIECES),
        "nfe": nfe_step,
        "t_meter_ms": round(t_meter * 1000, 1),
        "t_segment_ms": round(t_segment * 1000, 1),
        "t_prep_ms": round(t_prep * 1000, 1),
        "t_dit_wall_s": round(max(dit_times), 2),
        "t_bvgan_wall_s": round(max(bvgan_times), 2),
        "t_stitch_ms": round(t_stitch * 1000, 1),
        "total_latency_s": round(total_latency, 2),
        "audio_dur_s": round(audio_dur, 2),
        "rtf": round(total_latency / audio_dur, 2)
    }

def main():
    print(f"{'='*100}")
    print("VĀGDHENU STAGE-BY-STAGE LATENCY PROFILING (24 OCPU / 48 vCPU AMD GENOA)")
    print(f"{'='*100}\n")

    all_results = []
    for mode_name, nfe in MODES:
        print(f"\n--- MODE: {mode_name} (seed=60) ---")
        for label, d, sc, m in SAMPLES:
            text = _tx(d, sc)
            res = profile_single_run(label, text, m, nfe, seed=60)
            all_results.append(res)
            print(f"[{res['bank_key']:15s}] {label[:35]:35s} | DiT: {res['t_dit_wall_s']:4.2f}s | BigVGAN: {res['t_bvgan_wall_s']:4.2f}s | Total: {res['total_latency_s']:5.2f}s | Audio: {res['audio_dur_s']:4.1f}s | RTF: {res['rtf']:4.2f}")

    with open("profiling_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print("\nSaved full results to profiling_results.json")

if __name__ == "__main__":
    main()
