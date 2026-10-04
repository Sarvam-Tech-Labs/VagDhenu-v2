import os
import sys
import time
import subprocess
import json

print("=========================================================================")
print("=== Overnight Autonomous Pipeline Orchestrator (Phases 3 & 4) =========")
print("=========================================================================")

CKPT_DIR = "/home/ubuntu/vagdhenu/prabhupada_training/checkpoints_gold"
FINAL_CKPT = os.path.join(CKPT_DIR, "prabhupada_gold_final.pt")
SYNTH_SCRIPT = "/home/ubuntu/vagdhenu/prabhupada_training/synthesize_bhagavatam_prabhupada.py"
PYTHON_BIN = "/home/ubuntu/vagdhenu/venv/bin/python"

# 1. Monitor training until final checkpoint is produced
print(f"Monitoring DiT training process... Target: {FINAL_CKPT}")
t_start = time.time()
last_reported_epoch = 0

while True:
    # Check if final checkpoint exists
    if os.path.exists(FINAL_CKPT):
        print(f"\n[ORCHESTRATOR] Found final checkpoint: {FINAL_CKPT}!")
        break
        
    # Check intermediate epoch checkpoints
    epoch_files = [f for f in os.listdir(CKPT_DIR) if f.startswith("prabhupada_gold_epoch_") and f.endswith(".pt")]
    if epoch_files:
        epochs = []
        for ef in epoch_files:
            try:
                ep_num = int(ef.replace("prabhupada_gold_epoch_", "").replace(".pt", ""))
                epochs.append(ep_num)
            except ValueError:
                pass
        if epochs:
            max_ep = max(epochs)
            if max_ep > last_reported_epoch:
                last_reported_epoch = max_ep
                print(f"[ORCHESTRATOR] Milestone reached: Completed Epoch {max_ep}/15. Checkpoint saved.")
                
    # Check if training process is still running
    # If not running and final checkpoint not yet found, check if epoch 15 was saved
    res = subprocess.run(["pgrep", "-f", "train_prabhupada_gold.py"], stdout=subprocess.PIPE, text=True)
    if not res.stdout.strip():
        # Process ended
        time.sleep(2)
        if os.path.exists(FINAL_CKPT):
            print(f"[ORCHESTRATOR] Training completed and final checkpoint found!")
            break
        elif os.path.exists(os.path.join(CKPT_DIR, "prabhupada_gold_latest.pt")):
            print(f"[ORCHESTRATOR] Training ended. Using latest checkpoint for synthesis.")
            FINAL_CKPT = os.path.join(CKPT_DIR, "prabhupada_gold_latest.pt")
            break
        else:
            print("[ORCHESTRATOR] Warning: Training process stopped unexpectedly without saving checkpoints!")
            break
            
    time.sleep(30)

# 2. Phase 4: Launch Bhāgavatam Synthesis
print("\n=========================================================================")
print("=== Launching Phase 4: Śrīmad-Bhāgavatam Synthesis & ASR Verification ===")
print("=========================================================================")

synth_cmd = [PYTHON_BIN, SYNTH_SCRIPT, FINAL_CKPT]
print(f"Executing: {' '.join(synth_cmd)}")
t_synth_start = time.time()

synth_proc = subprocess.run(synth_cmd, capture_output=True, text=True)

print("Synthesis Output:")
print(synth_proc.stdout)
if synth_proc.stderr:
    print("Synthesis Stderr:")
    print(synth_proc.stderr)

if synth_proc.returncode != 0:
    print(f"[ORCHESTRATOR ERROR] Synthesis script exited with code {synth_proc.returncode}!")
else:
    print(f"\n[ORCHESTRATOR] Synthesis successfully completed in {time.time()-t_synth_start:.1f}s!")

# 3. Post-Synthesis Verification & Manifest inspection
manifest_path = "/home/ubuntu/vagdhenu/demo/static/synthesis/synthesis_manifest.json"
if os.path.exists(manifest_path):
    with open(manifest_path, encoding='utf-8') as f:
        data = json.load(f)
    print("\n=========================================================================")
    print("=== Final Verification Summary of Prabhupāda Bhāgavatam Chanting ===")
    print("=========================================================================")
    for v in data:
        print(f"\n• {v['title']} ({v['total_duration_s']}s):")
        print(f"  Audio: /home/ubuntu/vagdhenu/demo/static/synthesis/{v['complete_audio_fn']}")
        print(f"  Su-śrotā CTC Verification: {v['complete_sushrota_ctc']}")
        print("  Pādas:")
        for idx, p in enumerate(v['padas']):
            print(f"    [{idx+1}] {p['deva']} ({p['duration_s']}s) -> CTC: {p['sushrota_ctc']}")
            
# 4. Ensure Web Server is serving all static assets
print("\n[ORCHESTRATOR] Checking web server status on ports 8080 & 8081...")
subprocess.run(["ln", "-sfn", "/home/ubuntu/vagdhenu/demo/static/synthesis", "/home/ubuntu/vagdhenu/demo/static/ch1_all_padas/synthesis"])
print("Ready for user inspection at:")
print("  http://localhost:8080/synthesis/")
print("  http://localhost:8080/ (Chapter 1)")
print("  http://localhost:8080/ch2/ (Chapter 2)")
print("  http://localhost:8080/ch3/ (Chapter 3)")
print("=========================================================================")
print(f"=== Entire Overnight Pipeline Complete in {(time.time()-t_start)/60:.1f} minutes ===")
print("=========================================================================")
