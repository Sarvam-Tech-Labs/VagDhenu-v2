import os
import json
import tarfile

print("=========================================================================")
print("=== Packaging Prabhupāda Gold Corpus for Google Colab GPU Training =====")
print("=========================================================================")

pkg_dir = "/home/ubuntu/vagdhenu/prabhupada_training/colab_package"
os.makedirs(pkg_dir, exist_ok=True)
audio_dir = os.path.join(pkg_dir, "audio")
os.makedirs(audio_dir, exist_ok=True)

manifest_src = "/home/ubuntu/vagdhenu/prabhupada_training/gold_manifest.json"
with open(manifest_src, encoding="utf-8") as f:
    items = json.load(f)

print(f"Loaded {len(items)} items from master gold manifest.")

colab_manifest = []
for item in items:
    src_wav = item['audio_path']
    rel_fn = f"ch{item['chapter']:02d}_{item['filename']}"
    dst_wav = os.path.join(audio_dir, rel_fn)
    
    if not os.path.exists(dst_wav):
        os.symlink(src_wav, dst_wav)
        
    colab_manifest.append({
        "audio_path": f"audio/{rel_fn}",
        "chapter": item['chapter'],
        "verse": item['verse'],
        "pada": item['pada'],
        "duration": item['duration'],
        "text": item['text'],
        "text_deva": item['text_deva'],
        "text_iast": item['text_iast'],
        "sushrota_ctc": item['sushrota_ctc']
    })

colab_man_p = os.path.join(pkg_dir, "manifest.json")
with open(colab_man_p, "w", encoding="utf-8") as f:
    json.dump(colab_manifest, f, indent=2, ensure_ascii=False)

print(f"Colab manifest written to {colab_man_p}")

# Copy vocab
os.system(f"cp /home/ubuntu/vagdhenu/src/reference_bank/vocab.txt {pkg_dir}/vocab.txt")

# Create tar.gz archive
archive_path = "/home/ubuntu/vagdhenu/prabhupada_training/prabhupada_gold_corpus.tar.gz"
print(f"Creating archive {archive_path}...")
with tarfile.open(archive_path, "w:gz", dereference=True) as tar:
    tar.add(pkg_dir, arcname="prabhupada_corpus")

size_mb = os.path.getsize(archive_path) / (1024 * 1024)
print(f"Successfully packaged Prabhupāda Gold Corpus: {size_mb:.1f} MB -> {archive_path}")
print("=========================================================================")
