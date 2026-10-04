import os
import sys
import time
import uuid
import json
import re
import numpy as np
import soundfile as sf
import torch
import torchaudio
import onnxruntime as ort
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from indic_transliteration import sanscript

os.environ["OMP_NUM_THREADS"] = "36"
torch.set_num_threads(36)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)
sys.path.insert(0, os.path.join(ROOT, "BigVGAN"))
from render_core import Renderer
import prep_text as PT

# Output directory for user-generated renders
RENDERS_DIR = os.path.join(HERE, "static", "live_renders")
os.makedirs(RENDERS_DIR, exist_ok=True)

# Path to verified working Prabhupāda model (3-chapter clean corpus, 15 epochs)
CHECKPOINT_PATH = os.path.join(ROOT, "prabhupada_training", "checkpoints_gold", "prabhupada_gold_epoch_15.pt")
VOCODER_PATH = os.path.join(ROOT, "models", "voc_bigvgan_EMA_2026-06-11.pth")
BANK_PATH = os.path.join(SRC, "reference_bank", "bank.json")

print("[INIT] Loading Su-śrotā Sanskrit CTC ASR...")
model_dir = os.path.join(ROOT, "models", "sushrota")
prep = ort.InferenceSession(os.path.join(model_dir, "preprocessor.onnx"))
asr = ort.InferenceSession(os.path.join(model_dir, "sushrota_sanskrit_ctc_int8.onnx"))
with open(os.path.join(model_dir, "sanskrit_vocab.json"), encoding="utf-8") as f:
    sushrota_vocab = json.load(f)
resampler_sushrota = torchaudio.transforms.Resample(orig_freq=24000, new_freq=16000)

def transcribe_sushrota(audio_24k):
    try:
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
    except Exception as e:
        return f"[ASR Error: {e}]"

print(f"[INIT] Loading Prabhupāda Gold DiT Checkpoint: {CHECKPOINT_PATH}...")
RENDERER = Renderer(
    voice_path=CHECKPOINT_PATH,
    voc_path=VOCODER_PATH,
    bank_path=BANK_PATH,
    device="cpu",
    vocoder_type="bigvgan",
    nfe=32,
    speed=0.92
)
print("[INIT] Prabhupāda DiT Model Warm and Ready for Instant Live Inference!")

app = FastAPI(title="Vāgdhenu — Prabhupāda Live Chanting Studio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Mount static asset routes
app.mount("/ch1", StaticFiles(directory=os.path.join(HERE, "static", "ch1_all_padas"), html=True), name="ch1")
app.mount("/ch2", StaticFiles(directory=os.path.join(HERE, "static", "ch2_all_padas"), html=True), name="ch2")
app.mount("/ch3", StaticFiles(directory=os.path.join(HERE, "static", "ch3_all_padas"), html=True), name="ch3")
app.mount("/ch4", StaticFiles(directory=os.path.join(HERE, "static", "ch4_all_padas"), html=True), name="ch4")
app.mount("/ch5", StaticFiles(directory=os.path.join(HERE, "static", "ch5_all_padas"), html=True), name="ch5")
app.mount("/ch6", StaticFiles(directory=os.path.join(HERE, "static", "ch6_all_padas"), html=True), name="ch6")
app.mount("/ch7", StaticFiles(directory=os.path.join(HERE, "static", "ch7_all_padas"), html=True), name="ch7")
app.mount("/ch8", StaticFiles(directory=os.path.join(HERE, "static", "ch8_all_padas"), html=True), name="ch8")
app.mount("/ch9", StaticFiles(directory=os.path.join(HERE, "static", "ch9_all_padas"), html=True), name="ch9")
app.mount("/ch10", StaticFiles(directory=os.path.join(HERE, "static", "ch10_all_padas"), html=True), name="ch10")
app.mount("/ch11", StaticFiles(directory=os.path.join(HERE, "static", "ch11_all_padas"), html=True), name="ch11")
app.mount("/synthesis", StaticFiles(directory=os.path.join(HERE, "static", "synthesis"), html=True), name="synthesis")
app.mount("/renders", StaticFiles(directory=RENDERS_DIR), name="renders")
app.mount("/hiss_test", StaticFiles(directory=os.path.join(HERE, "static", "hiss_test"), html=True), name="hiss_test")

PRESETS = [
    {
        "id": "sb_1_2_4",
        "title": "Anuṣṭubh (8s) • SB 1.2.4",
        "meter": "prabhupada_anustubh",
        "deva": "नारायणं नमस्कृत्य नरं चैव नरोत्तमम् ।\nदेवीं सरस्वतीं व्यासं ततो जयमुदीरयेत् ॥",
        "iast": "nārāyaṇaṁ namaskṛtya naraṁ caiva narottamam\ndevīṁ sarasvatīṁ vyāsaṁ tato jayam udīrayet",
        "trans": "Before reciting this Śrīmad-Bhāgavatam, which is the very means of conquest, one should offer respectful obeisances unto the Personality of Godhead, Nārāyaṇa, unto Nara-nārāyaṇa Ṛṣi, unto mother Sarasvatī, and unto Śrīla Vyāsadeva."
    },
    {
        "id": "sb_1_2_6",
        "title": "Upajāti (11s) • SB 1.2.6",
        "meter": "upajāti",
        "deva": "स वै पुंसां परो धर्मो यतो भक्तिरधोक्षजे ।\nअहैतुक्यप्रतिहता ययात्मा सम्प्रसीदति ॥",
        "iast": "sa vai puṁsāṁ paro dharmo yato bhaktir adhokṣaje\nahaituky apratihatā yayātmā samprasīdati",
        "trans": "The supreme occupation [dharma] for all humanity is that by which men can attain to loving devotional service unto the transcendent Lord. Such devotional service must be unmotivated and uninterrupted to completely satisfy the self."
    },
    {
        "id": "bs_5_29",
        "title": "Vasantatilakā (14s) • BS 5.29",
        "meter": "vasantatilakā",
        "deva": "चिन्तामणिप्रकरसद्मसु कल्पवृक्ष-लक्षावृतेषु सुरभीरभिपालयन्तम् ।\nलक्ष्मीसहस्रशतसम्भ्रमसेव्यमानं गोविन्दमादिपुरुषं तमहं भजामि ॥",
        "iast": "cintāmaṇi-prakara-sadmasu kalpa-vṛkṣa-lakṣāvṛteṣu surabhīr abhipālayantam\nlakṣmī-sahasra-śata-sambhrama-sevyamānaṁ govindam ādi-puruṣaṁ tam ahaṁ bhajāmi",
        "trans": "I worship Govinda, the primeval Lord, the first progenitor, who is tending the cows, yielding all desire, in abodes built with spiritual gems, surrounded by millions of purpose trees, always served with great reverence and affection by hundreds of thousands of lakṣmīs or gopīs."
    },
    {
        "id": "mukunda_3",
        "title": "Mālinī (15s) • Mukunda-mālā 3",
        "meter": "mālinī",
        "deva": "जयतु जयतु देवो देवकीनन्दनोऽयं जयतु जयतु कृष्णो वृष्णिवंशप्रदीपः ।\nजयतु जयतु मेघश्यामलः कोमलाङ्गो जयतु जयतु पृथ्वीभारनाशो मुकुन्दः ॥",
        "iast": "jayatu jayatu devo devakī-nandano 'yaṁ jayatu jayatu kṛṣṇo vṛṣṇi-vaṁśa-pradīpaḥ\njayatu jayatu megha-śyāmalaḥ komalāṅgo jayatu jayatu pṛthvī-bhāra-nāśo mukundaḥ",
        "trans": "All glories to this divine son of Devakī! All glories to Kṛṣṇa, the illuminator of the Vṛṣṇi dynasty! All glories to the soft-limbed Lord with cloud-dark complexion! All glories to Mukunda, who lifts the burden of the earth!"
    },
    {
        "id": "totaka_1",
        "title": "Bhujaṅgaprayāta (12s) • Toṭakāṣṭakam",
        "meter": "bhujaṅgaprayāta",
        "deva": "विदिताखिलशास्त्रसुधाजलधे महितोपनिषत्कथितार्थनिधे ।\nहृदये कलये विमलं चरणं भव शङ्कर देशिक मे शरणम् ॥",
        "iast": "viditākhila-śāstra-sudhā-jaladhe mahitopaniṣat-kathitārtha-nidhe\nhṛdaye kalaye vimalaṁ caraṇaṁ bhava śaṅkara deśika me śaraṇam",
        "trans": "O ocean of the nectar of all scriptures! O treasure-chest of the esoteric knowledge of the great Upaniṣads! In my heart I meditate upon your immaculate lotus feet; be my refuge, O master Śaṅkara!"
    },
    {
        "id": "jagannatha_1",
        "title": "Śārdūlavikrīḍita (19s) • Jagannāthāṣṭakam",
        "meter": "śārdūlavikrīḍita",
        "deva": "कदाचित् कालिन्दीतटविपिनसङ्गीततरलो मुदाभीरीनारीवदनकमलास्वादमधुपः ।\nरमाशम्भुब्रह्मामरपतिगणेशार्चितपदो जगन्नाथः स्वामी नयनपथगामी भवतु मे ॥",
        "iast": "kadācit kālindī-taṭa-vipina-saṅgīta-taralo mudābhīrī-nārī-vadana-kamalāsvāda-madhupaḥ\nramā-śambhu-brahmāmara-pati-gaṇeśārcita-pado jagannāthaḥ svāmī nayana-patha-gāmī bhavatu me",
        "trans": "Sometimes in great happiness He plays His flute in the groves beside the Yamunā river. Like a bumblebee, He tastes the lotus-faces of the gopīs. His feet are worshipped by Lakṣmī, Śiva, Brahmā, Indra, and Gaṇeśa. May that Jagannātha Svāmī be the object of my vision!"
    },
    {
        "id": "gitagovinda_1",
        "title": "Sragdharā (21s) • Gītā-govinda 1.1",
        "meter": "sragdharā",
        "deva": "मेघैर्मेदुरमम्बरं वनभुवः श्यामास्तमालद्रुमैर् नक्तं भीरुरयं त्वमेव तदिमं राधे गृहं प्रापय ।\nइत्थं नन्दनिदेशतश्चलितयोः प्रत्यध्वकुञ्जद्रुमं राधामाधवयोर्जयन्ति यमुनाकूले रहःकेलयः ॥",
        "iast": "meghair meduram ambaraṁ vana-bhuvaḥ śyāmās tamāla-drumair naktaṁ bhīrur ayaṁ tvam eva tad imaṁ rādhe gṛhaṁ prāpaya\nitthaṁ nanda-nideśataś calitayoḥ praty-adhva-kuñja-drumaṁ rādhā-mādhavayor jayanti yamunā-kūle rahaḥ-kelayaḥ",
        "trans": "The sky is thick with clouds; the woodlands are dark with tamāla trees; this boy Kṛṣṇa fears the night; O Rādhā, take Him home! Thus guided by Nanda's order, along each pathway grove, all glories to the secret loving pastimes of Rādhā and Mādhava on Yamunā's shore!"
    },
    {
        "id": "bg_18_66",
        "title": "Gītā 18.66 (Surrender)",
        "meter": "prabhupada_anustubh",
        "deva": "सर्वधर्मान्परित्यज्य मामेकं शरणं व्रज ।\nअहं त्वां सर्वपापेभ्यो मोक्षयिष्यामि मा शुचः ॥",
        "iast": "sarva-dharmān parityajya mām ekaṁ śaraṇaṁ vraja\nahaṁ tvāṁ sarva-pāpebhyo mokṣayiṣyāmi mā śucaḥ",
        "trans": "Abandon all varieties of religion and just surrender unto Me. I shall deliver you from all sinful reactions. Do not fear."
    },
    {
        "id": "mahamantra",
        "title": "Hare Kṛṣṇa Mahā-mantra",
        "meter": "prabhupada_anustubh",
        "deva": "हरे कृष्ण हरे कृष्ण कृष्ण कृष्ण हरे हरे ।\nहरे राम हरे राम राम राम हरे हरे ॥",
        "iast": "hare kṛṣṇa hare kṛṣṇa kṛṣṇa kṛṣṇa hare hare\nhare rāma hare rāma rāma rāma hare hare",
        "trans": "The supreme transcendental vibration for the deliverance of all conditioned souls in the age of Kali."
    }
]

class SynthRequest(BaseModel):
    text: str
    meter: Optional[str] = "prabhupada_anustubh"
    speed: Optional[float] = 0.92
    nfe: Optional[int] = 32
    vocoder: Optional[str] = "bigvgan"

class ExcludeRequest(BaseModel):
    filename: str
    excluded: bool
    reason: Optional[str] = "Manual review (English / repetition / non-scriptural speech)"

EXCLUSIONS_PATH = os.path.join(ROOT, "prabhupada_training", "curated_exclusions.json")

def load_exclusions():
    if os.path.exists(EXCLUSIONS_PATH):
        try:
            with open(EXCLUSIONS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_exclusions(data):
    with open(EXCLUSIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def sync_manifest_exclusion(filename: str, excluded: bool):
    """Sync is_excluded flag to static manifests if file exists."""
    for ch_idx in range(1, 19):
        ch_dir = os.path.join(HERE, "static", f"ch{ch_idx}_all_padas")
        if not os.path.exists(ch_dir):
            continue
        for sub_p in ["manifest.json", os.path.join("hemistichs", "manifest.json")]:
            m_path = os.path.join(ch_dir, sub_p)
            if os.path.exists(m_path):
                try:
                    with open(m_path, "r", encoding="utf-8") as f:
                        items = json.load(f)
                    changed = False
                    for it in items:
                        if it.get("filename") == filename:
                            it["is_excluded"] = excluded
                            changed = True
                            break
                    if changed:
                        with open(m_path, "w", encoding="utf-8") as f:
                            json.dump(items, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"[EXCLUDE SYNC ERROR] {m_path}: {e}")

@app.get("/api/exclusions")
def get_exclusions():
    return JSONResponse(load_exclusions())

@app.post("/api/exclude")
def toggle_exclusion(req: ExcludeRequest):
    data = load_exclusions()
    if req.excluded:
        data[req.filename] = {
            "excluded": True,
            "reason": req.reason or "Excluded by manual review",
            "timestamp": time.time()
        }
    else:
        if req.filename in data:
            del data[req.filename]
    save_exclusions(data)
    sync_manifest_exclusion(req.filename, req.excluded)
    return JSONResponse({
        "status": "ok",
        "filename": req.filename,
        "excluded": req.excluded,
        "total_excluded": len(data)
    })

@app.get("/api/normalized_boundaries")
def get_normalized_boundaries():
    norm_log_path = os.path.join(ROOT, "prabhupada_training", "normalized_boundaries.json")
    if os.path.exists(norm_log_path):
        try:
            with open(norm_log_path, "r", encoding="utf-8") as f:
                return JSONResponse(json.load(f))
        except Exception:
            return JSONResponse({})
    return JSONResponse({})

class SaveBoundaryRequest(BaseModel):
    filename: str
    chapter: int
    abs_start_s: float
    abs_end_s: float

@app.post("/api/save_boundary")
def save_boundary(req: SaveBoundaryRequest):
    """
    Saves updated absolute boundaries for a unit, re-slices the audio from the de-hissed master,
    and updates the manifests while storing absolute markers.
    """
    ch = req.chapter
    fn = req.filename
    st_abs = round(float(req.abs_start_s), 3)
    et_abs = round(float(req.abs_end_s), 3)
    dur = round(et_abs - st_abs, 3)
    
    if dur <= 0:
        raise HTTPException(status_code=400, detail="Invalid duration: end must be greater than start")
        
    master_path = os.path.join(ROOT, "prabhupada_training", "processed_corpus", "clean_tracks_dehissed", f"21{17+ch:02d}_Bg_{ch:02d}_Recitation_of_Bhagavad-gita_Chapter_{['One','Two','Three'][ch-1]}.wav")
    if not os.path.exists(master_path):
        raise HTTPException(status_code=404, detail=f"Master track not found for Chapter {ch}")
        
    # Read slice from master
    data, sr = sf.read(master_path)
    s_idx = int(round(st_abs * sr))
    e_idx = int(round(et_abs * sr))
    sliced_audio = data[s_idx:e_idx]
    
    # Write to hemistich audio path
    ch_dir = os.path.join(HERE, "static", f"ch{ch}_all_padas")
    out_wav = os.path.join(ch_dir, "hemistichs", fn)
    sf.write(out_wav, sliced_audio, sr)
    
    # Update hemistich manifest
    manifest_path = os.path.join(ch_dir, "hemistichs", "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        for it in items:
            if it.get("filename") == fn:
                it["divider_start_s"] = st_abs
                it["divider_end_s"] = et_abs
                it["duration"] = dur
                it["manual_normalized"] = True
                it["norm_abs_start_s"] = st_abs
                it["norm_abs_end_s"] = et_abs
                break
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
            
    # Also log to normalized_boundaries.json for absolute tracking
    norm_log_path = os.path.join(ROOT, "prabhupada_training", "normalized_boundaries.json")
    norm_log = {}
    if os.path.exists(norm_log_path):
        try:
            with open(norm_log_path, "r", encoding="utf-8") as f:
                norm_log = json.load(f)
        except Exception:
            norm_log = {}
    norm_log[fn] = {
        "chapter": ch,
        "filename": fn,
        "abs_start_s": st_abs,
        "abs_end_s": et_abs,
        "duration_s": dur,
        "timestamp": time.time()
    }
    with open(norm_log_path, "w", encoding="utf-8") as f:
        json.dump(norm_log, f, indent=2, ensure_ascii=False)
        
    return JSONResponse({
        "status": "ok",
        "filename": fn,
        "abs_start_s": st_abs,
        "abs_end_s": et_abs,
        "duration_s": dur
    })


def normalize_input_text(raw_text: str):
    """Detect script, convert Roman/IAST to clean Devanagari if needed, and split into padas."""
    t = raw_text.strip()
    # Check if text contains Latin letters
    has_latin = bool(re.search(r'[a-zA-Z]', t))
    if has_latin:
        # Convert IAST to Devanagari
        try:
            deva = sanscript.transliterate(t, sanscript.IAST, sanscript.DEVANAGARI).replace("ꣳ", "ं")
        except Exception:
            deva = t
    else:
        deva = t
        
    # Split on danda, double danda, or newline
    lines = []
    for line in deva.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Split on dandas
        subparts = [p.strip() for p in re.split(r'[।॥|]', line) if p.strip()]
        for sp in subparts:
            # remove verse numbers like 1.2.4 or 18.66 or digits
            clean = re.sub(r'[\d०-९\.\(\)\[\]]+', '', sp).strip()
            if clean:
                lines.append(clean)
                
    return lines, deva

@app.get("/api/presets")
def get_presets():
    return JSONResponse(PRESETS)

@app.post("/api/synthesize")
def synthesize_verse(req: SynthRequest):
    t_start = time.time()
    raw_text = req.text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")
        
    padas, deva_text = normalize_input_text(raw_text)
    if not padas:
        raise HTTPException(status_code=400, detail="No readable Sanskrit padas found in input.")
        
    meter_key = req.meter or "prabhupada_anustubh"
    speed = float(req.speed) if req.speed else 0.92
    nfe = int(req.nfe) if req.nfe else 32
    vocoder = req.vocoder if req.vocoder in ("bigvgan", "vocos") else "bigvgan"
    
    sr = 24000
    pada_audios = []
    padas_res = []
    
    unique_id = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"
    
    for idx, p in enumerate(padas):
        t0 = time.time()
        # Render single pada
        _sr, audio = RENDERER.render_one(p, meter=meter_key, speed=speed, nfe=nfe, vocoder=vocoder)
        sr = _sr
        dur = len(audio) / sr
        
        # Save individual pada audio
        p_fn = f"render_{unique_id}_pada_{idx+1}.wav"
        p_path = os.path.join(RENDERS_DIR, p_fn)
        sf.write(p_path, audio, sr)
        
        # Transcribe with Su-śrotā CTC
        ctc_txt = transcribe_sushrota(audio)
        
        padas_res.append({
            "index": idx + 1,
            "text": p,
            "duration_s": round(dur, 2),
            "audio_url": f"/renders/{p_fn}",
            "sushrota_ctc": ctc_txt,
            "latency_s": round(time.time() - t0, 2)
        })
        pada_audios.append(audio)
        
    # Stitch complete verse with 450ms breath pause
    gap_samples = int(0.45 * sr)
    gap = np.zeros(gap_samples, dtype=np.float32)
    
    full_parts = []
    for i, a in enumerate(pada_audios):
        full_parts.append(a)
        if i < len(pada_audios) - 1:
            full_parts.append(gap)
            
    complete_audio = np.concatenate(full_parts)
    complete_dur = len(complete_audio) / sr
    
    full_fn = f"render_{unique_id}_complete.wav"
    full_path = os.path.join(RENDERS_DIR, full_fn)
    sf.write(full_path, complete_audio, sr)
    
    complete_ctc = transcribe_sushrota(complete_audio)
    total_latency = round(time.time() - t_start, 2)
    
    return JSONResponse({
        "status": "success",
        "render_id": unique_id,
        "input_raw": raw_text,
        "input_deva": deva_text,
        "meter": meter_key,
        "vocoder": vocoder,
        "speed": speed,
        "nfe": nfe,
        "total_duration_s": round(complete_dur, 2),
        "total_latency_s": total_latency,
        "complete_audio_url": f"/renders/{full_fn}",
        "complete_sushrota_ctc": complete_ctc,
        "padas": padas_res
    })

@app.get("/", response_class=HTMLResponse)
@app.get("/live", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def live_studio_page():
    html_file = os.path.join(HERE, "static", "live_studio.html")
    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8082
    print(f"Starting Prabhupāda Live Chanting Studio on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
