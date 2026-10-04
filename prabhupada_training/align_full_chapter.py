"""Whole-chapter MMS forced alignment.

Usage: align_full_chapter.py <registry_module> <track.wav> <out.json>

Emissions are computed in overlapping 60 s windows (hop 50 s, window starts are
multiples of 320 samples so frame grids line up) and stitched, then ONE forced
alignment is run over the full chapter transcript. No hand-picked block windows.
"""
import sys, json, importlib
import numpy as np, soundfile as sf, torch, torchaudio

reg_mod, track, out_json = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, '/home/ubuntu/vagdhenu/prabhupada_training')
units = importlib.import_module(reg_mod).canonical_units

bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model().eval()
aligner = bundle.get_aligner()
mdict = bundle.get_dict()
TSR = bundle.sample_rate  # 16000

y, sr = sf.read(track)
total_dur = len(y) / sr
y16 = torchaudio.transforms.Resample(sr, TSR)(torch.from_numpy(y).float().unsqueeze(0))
n = y16.shape[1]
WIN, HOP = 60 * TSR, 50 * TSR            # both multiples of 320
MARGIN_F = 5 * 50                         # drop 5 s (250 frames) at inner edges

pieces = []
start = 0
while True:
    seg = y16[:, start:start + WIN]
    with torch.inference_mode():
        em, _ = model(seg)
    em = em[0]
    f0 = start // 320
    last = start + WIN >= n
    lo = 0 if start == 0 else MARGIN_F
    hi = em.shape[0] if last else MARGIN_F + HOP // 320
    pieces.append((f0 + lo, em[lo:hi]))
    print(f'window start={start/TSR:.0f}s frames kept {lo}..{hi}', flush=True)
    if last:
        break
    start += HOP

total_frames = pieces[-1][0] + pieces[-1][1].shape[0]
emission = torch.zeros(total_frames, pieces[0][1].shape[1])
filled = np.zeros(total_frames, bool)
for f0, em in pieces:
    emission[f0:f0 + em.shape[0]] = em
    filled[f0:f0 + em.shape[0]] = True
assert filled.all(), 'gap in stitched emissions'
spf = total_dur / total_frames

words = [w for u in units for w in u['words'].split()]
tok = [[mdict[c] for c in w if c in mdict] for w in words]
spans = aligner(emission, tok)

res, wi = [], 0
for u in units:
    uw = u['words'].split()
    sp = spans[wi:wi + len(uw)]
    wi += len(uw)
    valid = [s for s in sp if len(s) > 0]
    assert len(valid) == len(uw), f"{u['fn']} missing word spans"
    st = valid[0][0].start * spf
    et = valid[-1][-1].end * spf
    res.append({'fn': u['fn'], 'v': u['v'], 'p': u['p'], 'start': st, 'end': et,
                'nchars': sum(len(w) for w in uw)})
json.dump({'total_dur': total_dur, 'units': res}, open(out_json, 'w'), indent=1)
print('saved', out_json, len(res), 'units')
