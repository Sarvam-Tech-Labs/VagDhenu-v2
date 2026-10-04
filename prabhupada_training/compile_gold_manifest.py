import os
import sys
import json

sys.path.insert(0, '/home/ubuntu/vagdhenu/src')
import prep_text as PT

print("=========================================================================")
print("=== Compiling Master Gold Prabhupāda Dataset (Chapters 1, 2, 3) =======")
print("=========================================================================")

chapters = [
    (1, '/home/ubuntu/vagdhenu/demo/static/ch1_all_padas'),
    (2, '/home/ubuntu/vagdhenu/demo/static/ch2_all_padas'),
    (3, '/home/ubuntu/vagdhenu/demo/static/ch3_all_padas'),
    (4, '/home/ubuntu/vagdhenu/demo/static/ch4_all_padas'),
    (5, '/home/ubuntu/vagdhenu/demo/static/ch5_all_padas'),
    (6, '/home/ubuntu/vagdhenu/demo/static/ch6_all_padas'),
    (7, '/home/ubuntu/vagdhenu/demo/static/ch7_all_padas'),
    (8, '/home/ubuntu/vagdhenu/demo/static/ch8_all_padas'),
    (9, '/home/ubuntu/vagdhenu/demo/static/ch9_all_padas'),
    (10, '/home/ubuntu/vagdhenu/demo/static/ch10_all_padas'),
    (11, '/home/ubuntu/vagdhenu/demo/static/ch11_all_padas'),
]

gold_entries = []
total_dur = 0.0

for ch_num, ch_dir in chapters:
    man_p = os.path.join(ch_dir, 'manifest.json')
    if not os.path.exists(man_p):
        raise FileNotFoundError(f"Manifest not found for Chapter {ch_num}: {man_p}")
        
    with open(man_p, encoding='utf-8') as f:
        items = json.load(f)
        
    print(f"Loading Chapter {ch_num}: {len(items)} units from {ch_dir}...")
    
    for item in items:
        wav_path = os.path.join(ch_dir, item['filename'])
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"Audio file missing: {wav_path}")
            
        dur = item.get('duration_exact_s', item.get('duration', 0.0))
        total_dur += dur
        
        deva = item.get('text_deva', '')
        iast = item.get('text_iast', '')
        
        # Convert to model text using Vāgdhenu's exact champion pipeline
        kannada_model_txt = PT.model_text(deva)
        
        gold_entries.append({
            "audio_path": wav_path,
            "filename": item['filename'],
            "chapter": ch_num,
            "verse": item.get('verse', 0),
            "pada": item.get('pada', 0),
            "duration": dur,
            "text": kannada_model_txt,
            "text_deva": deva,
            "text_iast": iast,
            "sushrota_ctc": item.get('sushrota_ctc', ''),
            "divider_start_s": item.get('divider_start_s', 0.0),
            "divider_end_s": item.get('divider_end_s', 0.0)
        })

out_p = '/home/ubuntu/vagdhenu/prabhupada_training/gold_manifest.json'
with open(out_p, 'w', encoding='utf-8') as f:
    json.dump(gold_entries, f, indent=2, ensure_ascii=False)

print(f"\nSuccessfully compiled Master Gold Dataset:")
print(f"  Total units: {len(gold_entries)}")
print(f"  Total audio duration: {total_dur:.2f}s ({total_dur/60:.2f} minutes, {total_dur/3600:.2f} hours)")
print(f"  Target Manifest: {out_p}")
print("=========================================================================")
