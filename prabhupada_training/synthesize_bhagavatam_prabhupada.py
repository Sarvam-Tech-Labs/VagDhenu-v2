import os
import sys
import json
import time
import numpy as np
import soundfile as sf
import torch
import torchaudio
import onnxruntime as ort

os.environ["OMP_NUM_THREADS"] = "36"
torch.set_num_threads(36)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "BigVGAN"))
from render_core import Renderer
import prep_text as PT

out_dir = "/home/ubuntu/vagdhenu/demo/static/synthesis"
os.makedirs(out_dir, exist_ok=True)

# 1. Setup Su-śrotā ONNX for zero-prompt verification
model_dir = '/home/ubuntu/vagdhenu/models/sushrota'
prep = ort.InferenceSession(f'{model_dir}/preprocessor.onnx')
asr = ort.InferenceSession(f'{model_dir}/sushrota_sanskrit_ctc_int8.onnx')
with open(f'{model_dir}/sanskrit_vocab.json') as f:
    sushrota_vocab = json.load(f)
resampler_sushrota = torchaudio.transforms.Resample(orig_freq=24000, new_freq=16000)

def transcribe_sushrota(audio_24k):
    t_chunk = torch.from_numpy(audio_24k).float().unsqueeze(0)
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

def run_synthesis(checkpoint_path=None):
    if checkpoint_path is None:
        final_ckpt = "/home/ubuntu/vagdhenu/prabhupada_training/checkpoints_gold/prabhupada_gold_final.pt"
        latest_ckpt = "/home/ubuntu/vagdhenu/prabhupada_training/checkpoints_gold/prabhupada_gold_latest.pt"
        checkpoint_path = final_ckpt if os.path.exists(final_ckpt) else latest_ckpt
        
    print(f"Loading Prabhupāda Fine-Tuned Checkpoint: {checkpoint_path}...")
    
    r = Renderer(
        voice_path=checkpoint_path,
        voc_path='/home/ubuntu/vagdhenu/models/voc_bigvgan_EMA_2026-06-11.pth',
        bank_path='/home/ubuntu/vagdhenu/src/reference_bank/bank.json',
        device='cpu',
        vocoder_type='bigvgan', # Highest fidelity vocoder
        nfe=32,
        speed=0.92
    )
    
    verses = [
        {
            "id": "sb_01_02_04",
            "title": "Śrīmad-Bhāgavatam 1.2.4 (Maṅgalācaraṇa)",
            "meter": "prabhupada_anustubh",
            "padas": [
                {"deva": "नारायणं नमस्कृत्य", "iast": "nārāyaṇaṁ namaskṛtya"},
                {"deva": "नरं चैव नरोत्तमम्", "iast": "naraṁ caiva narottamam"},
                {"deva": "देवीं सरस्वतीं व्यासं", "iast": "devīṁ sarasvatīṁ vyāsaṁ"},
                {"deva": "ततो जयमुदीरयेत्", "iast": "tato jayam udīrayet"}
            ],
            "translation": "Before reciting this Śrīmad-Bhāgavatam, which is the very means of conquest, one should offer respectful obeisances unto the Personality of Godhead, Nārāyaṇa, unto Nara-nārāyaṇa Ṛṣi, the supermost human being, unto mother Sarasvatī, the goddess of learning, and unto Śrīla Vyāsadeva, the author."
        },
        {
            "id": "sb_01_02_17",
            "title": "Śrīmad-Bhāgavatam 1.2.17 (Śṛṇvatāṁ Sva-kathāḥ Kṛṣṇaḥ)",
            "meter": "prabhupada_anustubh",
            "padas": [
                {"deva": "शृण्वतां स्वकथाः कृष्णः", "iast": "śṛṇvatāṁ sva-kathāḥ kṛṣṇaḥ"},
                {"deva": "पुण्यश्रवणकीर्तनः", "iast": "puṇya-śravaṇa-kīrtanaḥ"},
                {"deva": "हृद्यन्तःस्थो ह्यभद्राणि", "iast": "hṛdy antaḥ-stho hy abhadrāṇi"},
                {"deva": "विधुनोति सुहृत्सताम्", "iast": "vidhunoti suhṛt satām"}
            ],
            "translation": "Śrī Kṛṣṇa, the Personality of Godhead, who is the Paramātmā in everyone's heart and the benefactor of the truthful devotee, cleanses desire for material enjoyment from the heart of the devotee who has developed the urge to hear His messages, which are in themselves virtuous when properly heard and chanted."
        },
        {
            "id": "sb_01_01_01_invoc",
            "title": "Śrīmad-Bhāgavatam 1.1.1 (Pranāma)",
            "meter": "prabhupada_anustubh",
            "padas": [
                {"deva": "ॐ नमो भगवते वासुदेवाय", "iast": "oṁ namo bhagavate vāsudevāya"}
            ],
            "translation": "O my Lord, Śrī Kṛṣṇa, son of Vasudeva, O all-pervading Personality of Godhead, I offer my respectful obeisances unto You."
        }
    ]
    
    results = []
    
    for v in verses:
        print(f"\n=========================================================================")
        print(f"=== Synthesizing {v['title']} in Prabhupāda's Voice ===")
        print(f"=========================================================================")
        
        pada_audios = []
        sr = 24000
        
        for p_idx, p in enumerate(v['padas']):
            t0 = time.time()
            text_input = p['deva']
            print(f"  Rendering Pāda {p_idx+1}: {p['deva']} ({p['iast']})...", end="", flush=True)
            
            # Synthesize single pada
            _sr, audio = r.render_one(text_input, meter=v['meter'], speed=0.92, nfe=32)
            sr = _sr
            dur = len(audio) / sr
            
            # Save individual pada audio
            pada_fn = f"{v['id']}_pada_{p_idx+1}.wav"
            pada_path = os.path.join(out_dir, pada_fn)
            sf.write(pada_path, audio, sr)
            
            # Transcribe with Su-śrotā CTC
            ctc_txt = transcribe_sushrota(audio)
            
            p['audio_fn'] = pada_fn
            p['duration_s'] = round(dur, 2)
            p['sushrota_ctc'] = ctc_txt
            pada_audios.append(audio)
            
            print(f" Done ({dur:.2f}s in {time.time()-t0:.1f}s) | CTC: {ctc_txt}")
            
        # Stitch full verse with natural inter-pāda cadences (0.45s breath gap)
        gap_samples = int(0.45 * sr)
        gap = np.zeros(gap_samples, dtype=np.float32)
        
        full_audio_parts = []
        for i, a in enumerate(pada_audios):
            full_audio_parts.append(a)
            if i < len(pada_audios) - 1:
                full_audio_parts.append(gap)
                
        full_audio = np.concatenate(full_audio_parts)
        full_dur = len(full_audio) / sr
        
        full_fn = f"{v['id']}_complete.wav"
        full_path = os.path.join(out_dir, full_fn)
        sf.write(full_path, full_audio, sr)
        
        # Verify full verse with Su-śrotā CTC
        full_ctc = transcribe_sushrota(full_audio)
        print(f"\n---> Full Verse Audio: {full_path} ({full_dur:.2f}s)")
        print(f"---> Su-śrotā CTC Verification: {full_ctc}")
        
        v['complete_audio_fn'] = full_fn
        v['total_duration_s'] = round(full_dur, 2)
        v['complete_sushrota_ctc'] = full_ctc
        results.append(v)

    # Save synthesis manifest
    manifest_path = os.path.join(out_dir, "synthesis_manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\nSynthesis manifest saved to {manifest_path}")
    return results

if __name__ == "__main__":
    ckpt = sys.argv[1] if len(sys.argv) > 1 else None
    run_synthesis(ckpt)
