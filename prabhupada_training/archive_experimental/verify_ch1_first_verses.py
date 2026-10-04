import whisper
import soundfile as sf
import difflib

model = whisper.load_model('base')

for i in range(5):
    p = f"/home/ubuntu/vagdhenu/prabhupada_training/processed_corpus/safe_slices_ch1/bg01_safe_{i:04d}.wav"
    d, sr = sf.read(p)
    res = model.transcribe(p, language='sa')
    print(f"Slice {i} ({len(d)/sr:.2f}s): {res['text'].strip()}")
