import os
import json

ch4_dir = '/home/ubuntu/vagdhenu/demo/static/ch4_all_padas'
manifest_p = os.path.join(ch4_dir, 'manifest.json')
with open(manifest_p, encoding='utf-8') as f:
    items = json.load(f)

total_dur = sum(it['duration_exact_s'] for it in items)
gold_count = sum(1 for it in items if it['is_gold'])
total_units = len(items)

cards_html = []
for it in items:
    idx = it['index']
    fn = it['filename']
    dur = it['duration_exact_s']
    t_st = it['divider_start_s']
    t_et = it['divider_end_s']
    val_db = it['valley_db']
    deva = it['text_deva']
    iast = it['text_iast']
    ctc = it['sushrota_ctc']
    sim = it.get('similarity', 0.0)
    is_gold = it.get('is_gold', False)
    v = it['verse']
    p = it['pada']
    
    status_badge = '<span style="background:#064e3b; color:#34d399; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:bold; border:1px solid #059669;">GOLD PASS</span>' if is_gold else '<span style="background:#451a1a; color:#f87171; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:bold; border:1px solid #7f1d1d;">REVIEW</span>'
    
    card = f"""
    <div class="pada-card" style="background:#161b22; border:1px solid {'#30363d' if is_gold else '#7f1d1d'}; border-radius:8px; padding:16px; margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <div>
          <span style="font-weight:bold; color:#f1c40f; font-size:15px;">#{idx:03d} • Verse 4.{v} (Pada {p})</span>
          <span style="color:#8b949e; font-size:12px; margin-left:8px;">{fn}</span>
        </div>
        <div>
          {status_badge}
        </div>
      </div>
      
      <div style="font-size:18px; font-weight:600; color:#f0f6fc; margin-bottom:4px;">{deva}</div>
      <div style="font-size:13px; color:#8b949e; font-style:italic; margin-bottom:12px;">{iast}</div>
      
      <div style="background:#0d1117; border-radius:6px; padding:10px 12px; margin-bottom:12px; font-size:13px;">
        <span style="color:#58a6ff; font-weight:bold;">Su-śrotā CTC:</span> <span style="color:#c9d1d9;">{ctc}</span>
        <span style="float:right; color:{'#34d399' if sim>=0.4 else '#f87171'}; font-weight:bold;">Phonetic Sim: {sim*100:.1f}%</span>
      </div>
      
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <audio controls preload="none" src="{fn}" style="height:32px; width:65%;"></audio>
        <span style="font-size:12px; color:#8b949e;">[{t_st:.3f}s → {t_et:.3f}s] ({dur:.2f}s | Val={val_db:.1f}dB)</span>
      </div>
    </div>
    """
    cards_html.append(card)

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Bhagavad Gita Chapter 4 - Verified Gold Continuous Divider Corpus ({total_units} Units)</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 24px; max-width: 1000px; margin: 0 auto; }}
  .header {{ text-align: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #30363d; }}
  h1 {{ color: #f1c40f; margin-bottom: 6px; font-size: 26px; }}
  .stats-bar {{ display: flex; justify-content: center; gap: 16px; margin-top: 12px; flex-wrap: wrap; }}
  .stat-pill {{ background: #161b22; border: 1px solid #30363d; padding: 6px 14px; border-radius: 16px; font-size: 13px; }}
  .stat-pill span {{ color: #58a6ff; font-weight: bold; }}
  .nav-btn {{ background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 500; margin-right: 8px; }}
  .nav-btn:hover {{ border-color: #58a6ff; color: #ffffff; }}
</style>
</head>
<body>

<div class="header">
  <div style="margin-bottom: 16px;">
    <a href="/" class="nav-btn">🎙️ Live Studio</a>
    <a href="/ch1/" class="nav-btn">Ch 1</a>
    <a href="/ch2/" class="nav-btn">Ch 2</a>
    <a href="/ch3/" class="nav-btn">Ch 3</a>
    <a href="/ch4/" class="nav-btn" style="border-color:#f1c40f; color:#f1c40f;">Ch 4 (Verified)</a>
  </div>
  <h1>Bhagavad-gītā Chapter 4 — Verified Gold Slices</h1>
  <div style="color: #8b949e; font-size: 14px;">Strict Zero-Loss Continuous Divider Alignment with Active Su-śrotā CTC Phonetic Gating</div>
  <div class="stats-bar">
    <div class="stat-pill">Total Units: <span>{total_units}</span></div>
    <div class="stat-pill">Total Track Duration: <span>{total_dur:.2f}s ({total_dur/60:.2f} min)</span></div>
    <div class="stat-pill">Gold Pass Rate: <span style="color:#34d399;">{gold_count}/{total_units} ({gold_count/total_units*100:.1f}%)</span></div>
    <div class="stat-pill">Boundary Loss: <span style="color:#34d399;">0.000 ms</span></div>
    <div class="stat-pill">Omitted Verses: <span style="color:#f87171;">4.3, 4.13 (Not recited)</span></div>
  </div>
</div>

<div class="cards-list">
  {"".join(cards_html)}
</div>

</body>
</html>
"""

out_html = os.path.join(ch4_dir, 'index.html')
with open(out_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"Inspector HTML written to {out_html}")
