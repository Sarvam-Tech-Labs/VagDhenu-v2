import os
import sys
import json
import time
import torch
from torch.utils.data import Dataset, DataLoader
from f5_tts.infer.utils_infer import load_model
from f5_tts.model import DiT
from f5_tts.model.dataset import collate_fn
from f5_tts.model.modules import MelSpec
import soundfile as sf
import torchaudio

print("=========================================================================")
print("=== Vāgdhenu — Google Colab Tesla T4 GPU High-Speed Fine-Tuning ========")
print("=========================================================================")

MANIFEST_PATH = "/content/prabhupada_corpus/manifest.json"
DATA_ROOT = "/content/prabhupada_corpus"
VOCAB_PATH = "/content/prabhupada_corpus/vocab.txt"
BASE_CHECKPOINT = "/content/voice_armA_ema_2026-06-11.pt"
OUTPUT_DIR = "/content/checkpoints_gpu"
os.makedirs(OUTPUT_DIR, exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
if not torch.cuda.is_available():
    raise RuntimeError("CUDA device not found on Colab GPU VM!")

class CachedPrabhupadaDataset(Dataset):
    def __init__(self, manifest, data_root, target_sr=24000, max_duration=10.0):
        self.target_sr = target_sr
        self.max_frames = int(max_duration * 93.75)  # 10s ~ 938 frames
        mel_spec_fn = MelSpec(
            n_fft=1024,
            hop_length=256,
            win_length=1024,
            n_mel_channels=100,
            target_sample_rate=24000,
            mel_spec_type="vocos"
        )
        print(f"Pre-caching mel-spectrograms from {len(manifest)} items (max duration {max_duration}s)...")
        t0 = time.time()
        self.cached = []
        skipped_long = 0
        for i, item in enumerate(manifest):
            try:
                wav_path = os.path.join(data_root, item['audio_path'])
                wav, sr = torchaudio.load(wav_path)
                dur = wav.shape[-1] / sr
                if dur > max_duration:
                    skipped_long += 1
                    continue
                if wav.shape[0] > 1:
                    wav = wav.mean(dim=0, keepdim=True)
                if sr != self.target_sr:
                    wav = torchaudio.transforms.Resample(sr, self.target_sr)(wav)
                mel = mel_spec_fn(wav).squeeze(0)  # [100, frames]
                if mel.shape[-1] > self.max_frames:
                    mel = mel[:, :self.max_frames]
                self.cached.append({
                    "mel_spec": mel,
                    "text": item['text']
                })
            except Exception as e:
                if i < 5:
                    print(f"Warning: skipped {item.get('audio_path')}: {e}")
        elapsed = time.time() - t0
        print(f"Cached {len(self.cached)} pure pāda items (filtered {skipped_long} long/colophon items) in {elapsed:.2f}s ({elapsed/len(self.cached)*1000:.1f}ms/item). Ready for ultra-fast GPU training.")

    def __len__(self):
        return len(self.cached)

    def __getitem__(self, idx):
        return self.cached[idx]

def train():
    with open(MANIFEST_PATH, encoding='utf-8') as f:
        manifest = json.load(f)
    print(f"Total training samples in manifest: {len(manifest)}")
    
    dataset = CachedPrabhupadaDataset(manifest, DATA_ROOT, max_duration=10.0)
    batch_size = 2
    accum_steps = 2
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=2,
        pin_memory=True,
        drop_last=True
    )
    
    print("Initializing IndicF5 DiT model and loading base checkpoint...")
    CFG = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
    cfm = load_model(
        DiT,
        CFG,
        ckpt_path=BASE_CHECKPOINT,
        mel_spec_type="vocos",
        vocab_file=VOCAB_PATH,
        device="cuda"
    )
    cfm = cfm.to(device="cuda", dtype=torch.float32)
    cfm.train()
    
    optimizer = torch.optim.AdamW(cfm.transformer.parameters(), lr=2e-5, weight_decay=1e-2)
    
    total_epochs = 10
    steps_per_epoch = len(dataloader)
    total_steps = total_epochs * steps_per_epoch
    print(f"\nStarting GPU Fine-Tuning (Batch: {batch_size}, Accum: {accum_steps}, Effective: {batch_size*accum_steps})")
    print(f"Total: {total_epochs} Epochs, {steps_per_epoch} forward passes/epoch, {total_steps} total forward passes...")
    start_time = time.time()
    step = 0
    
    for epoch in range(1, total_epochs + 1):
        epoch_start = time.time()
        epoch_loss = 0.0
        n_batches = 0
        optimizer.zero_grad()
        
        for batch_idx, batch in enumerate(dataloader):
            text_inputs = batch["text"]
            mel_spec = batch["mel"].permute(0, 2, 1).to(device="cuda", dtype=torch.float32, non_blocking=True)  # [b, frames, 100]
            mel_lengths = batch["mel_lengths"].to(device="cuda", dtype=torch.long, non_blocking=True)
            
            try:
                loss, cond, pred = cfm(mel_spec, text=text_inputs, lens=mel_lengths)
                scaled_loss = loss / accum_steps
                scaled_loss.backward()
            except torch.OutOfMemoryError:
                print(f"\n[Warning] OOM caught at step {step}, skipping batch to preserve training...", flush=True)
                torch.cuda.empty_cache()
                optimizer.zero_grad()
                continue
            
            step += 1
            epoch_loss += loss.item()
            n_batches += 1
            
            if (batch_idx + 1) % accum_steps == 0 or (batch_idx + 1) == len(dataloader):
                torch.nn.utils.clip_grad_norm_(cfm.transformer.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad()
            
            if step % 50 == 0 or step == total_steps:
                elapsed = time.time() - start_time
                ms_per_step = (elapsed / step) * 1000
                rem_steps = total_steps - step
                rem_time_min = (rem_steps * (elapsed / step)) / 60
                vram_used = torch.cuda.memory_reserved(0) / (1024**2)
                print(f"[Epoch {epoch:02d}/{total_epochs:02d} | Step {step:05d}/{total_steps}] Loss: {loss.item():.4f} | Avg: {epoch_loss/n_batches:.4f} | VRAM: {vram_used:.0f}MB | {ms_per_step:.0f}ms/step | ETA: {rem_time_min:.1f}m", flush=True)
                
            if step % 200 == 0:
                torch.cuda.empty_cache()
                
        # Epoch Checkpoint
        epoch_dur = time.time() - epoch_start
        avg_loss = epoch_loss / max(1, n_batches)
        print(f"\n=== Completed Epoch {epoch}/{total_epochs} in {epoch_dur:.1f}s | Avg Loss: {avg_loss:.4f} ===", flush=True)
        
        # Save every epoch checkpoint
        ckpt_save_p = os.path.join(OUTPUT_DIR, f"prabhupada_gold_epoch_{epoch:02d}.pt")
        latest_p = "/content/prabhupada_gold_gpu_latest.pt"
        state_to_save = {
            "model_state_dict": cfm.state_dict(),
            "ema_model_state_dict": {f"ema_model.{k}": v for k, v in cfm.state_dict().items()},
            "epoch": epoch,
            "step": step,
            "loss": avg_loss
        }
        torch.save(state_to_save, ckpt_save_p)
        torch.save(state_to_save, latest_p)
        print(f"Saved Checkpoint: {ckpt_save_p} and updated latest model.")
            
    # Final Checkpoint
    final_p = "/content/prabhupada_gold_gpu_final.pt"
    torch.save({
        "model_state_dict": cfm.state_dict(),
        "ema_model_state_dict": {f"ema_model.{k}": v for k, v in cfm.state_dict().items()},
        "total_epochs": total_epochs,
        "total_steps": step
    }, final_p)
    print(f"\nTraining Complete! Final Gold Model saved to: {final_p}")
    print("=========================================================================")

if __name__ == "__main__":
    train()
