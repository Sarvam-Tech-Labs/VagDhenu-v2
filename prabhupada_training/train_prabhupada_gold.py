import os
import sys
import json
import time
import torch
from torch.utils.data import Dataset, DataLoader
from f5_tts.infer.utils_infer import load_model
from f5_tts.model import DiT
from f5_tts.model.dataset import collate_fn
import soundfile as sf
import torchaudio

os.environ["OMP_NUM_THREADS"] = "48"
os.environ["MKL_NUM_THREADS"] = "48"
torch.set_num_threads(48)

MANIFEST_PATH = "/home/ubuntu/vagdhenu/prabhupada_training/gold_manifest.json"
VOCAB_PATH = "/home/ubuntu/vagdhenu/src/reference_bank/vocab.txt"
BASE_CHECKPOINT = "/home/ubuntu/vagdhenu/models/voice_armA_ema_2026-06-11.pt"
OUTPUT_DIR = "/home/ubuntu/vagdhenu/prabhupada_training/checkpoints_gold"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class CachedPrabhupadaDataset(Dataset):
    def __init__(self, manifest, target_sr=24000):
        self.target_sr = target_sr
        from f5_tts.model.modules import MelSpec
        mel_spec_fn = MelSpec(
            n_fft=1024,
            hop_length=256,
            win_length=1024,
            n_mel_channels=100,
            target_sample_rate=24000,
            mel_spec_type="vocos"
        )
        print(f"Pre-caching {len(manifest)} mel-spectrograms directly in RAM...")
        t0 = time.time()
        self.cached = []
        for i, item in enumerate(manifest):
            try:
                wav, sr = torchaudio.load(item['audio_path'])
                if wav.shape[0] > 1:
                    wav = wav.mean(dim=0, keepdim=True)
                if sr != self.target_sr:
                    wav = torchaudio.transforms.Resample(sr, self.target_sr)(wav)
                mel = mel_spec_fn(wav).squeeze(0)  # [100, frames]
                self.cached.append({
                    "mel_spec": mel,
                    "text": item['text']
                })
            except Exception as e:
                print(f"Warning: skipped {item.get('audio_path')}: {e}")
        elapsed = time.time() - t0
        print(f"Cached {len(self.cached)} items in {elapsed:.2f}s ({elapsed/len(self.cached)*1000:.1f}ms/item). Ready for zero-I/O training.")

    def __len__(self):
        return len(self.cached)

    def __getitem__(self, idx):
        return self.cached[idx]

def train():
    print("=========================================================================")
    print("=== Phase 3: Fine-Tuning Vāgdhenu DiT on Prabhupāda Gold Corpus ======")
    print("=========================================================================")
    print(f"Loading manifest from {MANIFEST_PATH}...")
    with open(MANIFEST_PATH, encoding='utf-8') as f:
        manifest = json.load(f)
    print(f"Total training samples: {len(manifest)}")
    
    dataset = CachedPrabhupadaDataset(manifest)
    dataloader = DataLoader(
        dataset,
        batch_size=4,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=0,
        drop_last=True
    )
    
    print("Initializing IndicF5 DiT model...")
    CFG = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
    cfm = load_model(DiT, CFG, mel_spec_type="vocos", vocab_file=VOCAB_PATH, device="cpu")
    
    print(f"Loading base weights from {BASE_CHECKPOINT}...")
    ckpt = torch.load(BASE_CHECKPOINT, map_location="cpu", weights_only=False)
    if "ema_model_state_dict" in ckpt:
        sd = {k.replace("ema_model.", ""): v for k, v in ckpt["ema_model_state_dict"].items() if k not in ("initted", "step")}
    elif "model_state_dict" in ckpt:
        sd = {k.replace("ema_model.", ""): v for k, v in ckpt["model_state_dict"].items() if k not in ("initted", "step")}
    else:
        sd = ckpt
    cfm.load_state_dict(sd, strict=False)
    cfm.train()
    
    optimizer = torch.optim.AdamW(cfm.transformer.parameters(), lr=1.5e-5, weight_decay=1e-2)
    
    total_epochs = 15
    steps_per_epoch = len(dataloader)
    total_steps = total_epochs * steps_per_epoch
    print(f"\nStarting Gold Fine-Tuning ({total_epochs} Epochs, {steps_per_epoch} steps/epoch, {total_steps} total steps)...")
    start_time = time.time()
    step = 0
    
    for epoch in range(1, total_epochs + 1):
        epoch_start = time.time()
        epoch_loss = 0.0
        n_batches = 0
        
        for batch in dataloader:
            optimizer.zero_grad()
            text_inputs = batch["text"]
            mel_spec = batch["mel"].permute(0, 2, 1)  # [b, frames, 100]
            mel_lengths = batch["mel_lengths"]
            
            with torch.autocast(device_type="cpu", dtype=torch.bfloat16):
                loss, cond, pred = cfm(mel_spec, text=text_inputs, lens=mel_lengths)
                
            loss.backward()
            torch.nn.utils.clip_grad_norm_(cfm.transformer.parameters(), 1.0)
            optimizer.step()
            
            step += 1
            epoch_loss += loss.item()
            n_batches += 1
            
            if step % 20 == 0 or step == total_steps:
                elapsed = time.time() - start_time
                ms_per_step = (elapsed / step) * 1000
                rem_steps = total_steps - step
                rem_time_min = (rem_steps * (elapsed / step)) / 60
                print(f"[Epoch {epoch:02d}/{total_epochs:02d} | Step {step:04d}/{total_steps}] Loss: {loss.item():.4f} | Avg: {epoch_loss/n_batches:.4f} | {ms_per_step:.0f}ms/step | ETA: {rem_time_min:.1f}m", flush=True)
                
        # Epoch Checkpoint
        epoch_dur = time.time() - epoch_start
        avg_loss = epoch_loss / max(1, n_batches)
        print(f"\n=== Completed Epoch {epoch}/{total_epochs} in {epoch_dur:.1f}s | Avg Loss: {avg_loss:.4f} ===", flush=True)
        
        state_to_save = {
            "model_state_dict": cfm.state_dict(),
            "ema_model_state_dict": {f"ema_model.{k}": v for k, v in cfm.state_dict().items()},
            "epoch": epoch,
            "step": step,
            "loss": avg_loss
        }
        
        save_path = os.path.join(OUTPUT_DIR, f"prabhupada_gold_epoch_{epoch}.pt")
        latest_path = os.path.join(OUTPUT_DIR, "prabhupada_gold_latest.pt")
        torch.save(state_to_save, save_path)
        torch.save(state_to_save, latest_path)
        print(f"--> Saved checkpoint: {save_path}", flush=True)

    final_path = os.path.join(OUTPUT_DIR, "prabhupada_gold_final.pt")
    torch.save(state_to_save, final_path)
    print(f"\n=========================================================================")
    print(f"=== Fine-Tuning Completed Successfully in {(time.time()-start_time)/60:.1f} minutes ===")
    print(f"=== Final Model Checkpoint Saved: {final_path} ===")
    print("=========================================================================")

if __name__ == "__main__":
    train()
