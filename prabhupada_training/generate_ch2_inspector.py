import os
import json

ch2_dir = '/home/ubuntu/vagdhenu/demo/static/ch2_all_padas'
exclusions_path = '/home/ubuntu/vagdhenu/prabhupada_training/curated_exclusions.json'

exclusions = {}
if os.path.exists(exclusions_path):
    try:
        with open(exclusions_path, 'r', encoding='utf-8') as f:
            exclusions = json.load(f)
    except Exception:
        exclusions = {}

# Load Single Padas
with open(os.path.join(ch2_dir, 'manifest.json'), encoding='utf-8') as f:
    pada_items = json.load(f)

# Load Combined Hemistichs
with open(os.path.join(ch2_dir, 'hemistichs', 'manifest.json'), encoding='utf-8') as f:
    hemi_items = json.load(f)

pada_total_dur = sum(it['duration_exact_s'] for it in pada_items)
pada_gold_count = sum(1 for it in pada_items if it.get('is_gold'))
pada_excluded_count = sum(1 for it in pada_items if it['filename'] in exclusions)

hemi_total_dur = sum(it['duration'] for it in hemi_items)
hemi_gold_count = sum(1 for it in hemi_items if it.get('is_gold'))
hemi_excluded_count = sum(1 for it in hemi_items if it['filename'] in exclusions)

from gita_prosody import batch_analyze_manifest
from normalization_ui_component import generate_norm_workspace_html, NORM_JAVASCRIPT

norm_log_path = '/home/ubuntu/vagdhenu/prabhupada_training/normalized_boundaries.json'
norm_log = {}
if os.path.exists(norm_log_path):
    try:
        with open(norm_log_path, 'r', encoding='utf-8') as f:
            norm_log = json.load(f)
    except Exception:
        norm_log = {}

# Load precomputed waveform peaks for hemistichs
peaks_path = os.path.join(ch2_dir, 'hemistichs_padded', 'peaks.json')
peaks_map = {}
if os.path.exists(peaks_path):
    try:
        with open(peaks_path, 'r', encoding='utf-8') as f:
            peaks_map = json.load(f)
    except Exception:
        peaks_map = {}

# Analyze prosody (meter and syllables) utilizing multi-core CPU
pada_prosody = batch_analyze_manifest(pada_items, is_hemi=False, max_workers=32)
hemi_prosody = batch_analyze_manifest(hemi_items, is_hemi=True, max_workers=32)

def build_cards(items, prosody_list, is_hemi=False):
    cards = []
    for it, pros in zip(items, prosody_list):
        idx = it['index']
        fn = it['filename']
        dur = it.get('duration_exact_s', it.get('duration', 0.0))
        t_st = it['divider_start_s']
        t_et = it['divider_end_s']
        val_db = it.get('valley_db', -35.0)
        deva = it['text_deva']
        iast = it['text_iast']
        ctc = it['sushrota_ctc']
        sim = it.get('similarity', 0.0)
        is_gold = it.get('is_gold', False)
        v = it['verse']
        p = it.get('pada', it.get('pada_combo', ''))
        
        meter_name = pros.get('meter', 'chandas')
        n_syl = pros.get('syllables', 0)
        weights = pros.get('weights', '')
        
        is_excluded = fn in exclusions
        
        audio_src = f"hemistichs/{fn}" if is_hemi else fn
        tier_label = f"Verse 2.{v} (Pādas {p})" if is_hemi else f"Verse 2.{v} (Pada {p})"
        
        card_class = "pada-card is-excluded" if is_excluded else "pada-card is-included"
        card_border = "#ea580c" if is_excluded else ("#30363d" if is_gold else "#7f1d1d")
        card_bg = "#1a120c" if is_excluded else "#161b22"
        
        status_badge = '<span class="status-badge" style="background:#064e3b; color:#34d399; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:bold; border:1px solid #059669;">GOLD PASS</span>' if is_gold else '<span class="status-badge" style="background:#451a1a; color:#f87171; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:bold; border:1px solid #7f1d1d;">REVIEW</span>'
        
        excluded_badge_display = "inline-block" if is_excluded else "none"
        btn_text = "↩️ Include in Training" if is_excluded else "🚫 Exclude from Training"
        btn_style = "background:#262c36; border:1px solid #485363; color:#93c5fd;" if is_excluded else "background:#301b1b; border:1px solid #7f1d1d; color:#fca5a5;"
        
        card = f"""
        <div class="{card_class}" data-fn="{fn}" style="background:{card_bg}; border:1px solid {card_border}; border-radius:8px; padding:16px; margin-bottom:12px; transition:all 0.2s;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <div>
              <span style="font-weight:bold; color:#f1c40f; font-size:15px;">#{idx:03d} • {tier_label}</span>
              <span style="color:#8b949e; font-size:12px; margin-left:8px; font-family:monospace;">{fn}</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="excluded-badge" style="display:{excluded_badge_display}; background:#7c2d12; color:#fed7aa; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:bold; border:1px solid #ea580c;">🚫 EXCLUDED FROM TRAINING</span>
              <span class="gold-badge-container">{status_badge}</span>
              <button class="exclude-toggle-btn" onclick="toggleExclude('{fn}', this)" style="{btn_style} padding:4px 10px; border-radius:6px; cursor:pointer; font-size:11px; font-weight:600;">{btn_text}</button>
            </div>
          </div>
          
          <div style="font-size:18px; font-weight:600; color:#f0f6fc; margin-bottom:4px;">{deva}</div>
          <div style="font-size:13px; color:#8b949e; font-style:italic; margin-bottom:12px;">{iast}</div>
          
          <div style="background:#0d1117; border-radius:6px; padding:10px 12px; margin-bottom:12px; font-size:13px; display:flex; flex-direction:column; gap:6px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div><span style="color:#58a6ff; font-weight:bold;">Su-śrotā CTC:</span> <span style="color:#c9d1d9;">{ctc}</span></div>
              <span style="color:{'#34d399' if sim>=0.4 else '#f87171'}; font-weight:bold;">Phonetic Sim: {sim*100:.1f}%</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #21262d; padding-top:6px; font-size:12px;">
              <div>
                <span style="color:#e3b341; font-weight:bold;">🎼 Poetic Meter:</span> <span style="color:#f0f6fc; font-weight:600;">{meter_name}</span>
              </div>
              <div>
                <span style="color:#a371f7; font-weight:bold;">🔤 Syllables:</span> <span style="color:#7ee787; font-weight:bold; font-family:monospace;">{n_syl} akṣaras</span>
                <span style="color:#8b949e; margin-left:8px; font-family:monospace; font-size:11px;" title="Laghu (L) / Guru (G) scansion">[{weights}]</span>
              </div>
            </div>
          <div style="display:flex; flex-direction:column; gap:6px; margin-top:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <audio controls preload="none" src="{audio_src}?v={dur:.3f}" style="height:32px; width:70%;"></audio>
              <span style="font-size:12px; color:#8b949e; font-family:monospace; font-weight:600;">[{t_st:.3f}s → {t_et:.3f}s] <span style="color:#f1c40f;">({dur:.3f}s)</span></span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; background:#0d1117; padding:4px 10px; border-radius:4px; font-size:11px; font-family:monospace; color:#8b949e;">
              <span>⏱️ Live Pos: <b class="live-pos" style="color:#58a6ff;">0.000s</b> / <b class="audio-total-dur" style="color:#f1c40f;">{dur:.3f}s</b></span>
              <span>Tape Time: <b class="tape-pos" style="color:#34d399;">{t_st:.3f}s</b></span>
            </div>
          </div>
          
          {generate_norm_workspace_html(2, fn, t_st, t_et, dur, is_normalized=(fn in norm_log or it.get('manual_normalized', False)), peaks=peaks_map.get(fn, [])) if is_hemi else ""}
        </div>
        """
        cards.append(card)
    return ''.join(cards)

from prosody_summary_component import compute_meter_aggregations, generate_prosody_summary_html

pada_cards_html = build_cards(pada_items, pada_prosody, is_hemi=False)
hemi_cards_html = build_cards(hemi_items, hemi_prosody, is_hemi=True)

# Generate interactive prosody summary components
hemi_stats = compute_meter_aggregations(hemi_items, hemi_prosody)
pada_stats = compute_meter_aggregations(pada_items, pada_prosody)

hemi_prosody_summary_html = generate_prosody_summary_html(hemi_stats, tier_name="Two-Pāda Units")
pada_prosody_summary_html = generate_prosody_summary_html(pada_stats, tier_name="Single Pāda Units")

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chapter 2 Dual-Tier Inspector & Curation Studio</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 24px; max-width: 980px; margin: 0 auto; }}
  h1 {{ color: #f1c40f; font-size: 24px; margin-bottom: 6px; }}
  .tabs {{ display: flex; justify-content: space-between; align-items: center; margin: 20px 0 10px 0; border-bottom: 1px solid #30363d; padding-bottom: 12px; }}
  .tier-buttons {{ display: flex; gap: 8px; }}
  .filter-buttons {{ display: flex; gap: 6px; }}
  .tab-btn {{ background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; }}
  .tab-btn:hover {{ background: #30363d; color: #fff; }}
  .tab-btn.active {{ background: #1f6feb; border-color: #388bfd; color: #fff; }}
  .filter-btn {{ background: #161b22; border: 1px solid #30363d; color: #8b949e; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.2s; }}
  .filter-btn:hover {{ background: #21262d; color: #c9d1d9; }}
  .filter-btn.active {{ background: #238636; border-color: #2ea043; color: #fff; }}
  .filter-btn.active-warn {{ background: #b45309; border-color: #d97706; color: #fff; }}
  .metrics {{ display: flex; gap: 16px; margin: 16px 0 24px 0; }}
  .metric-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 18px; flex: 1; }}
  .metric-val {{ font-size: 22px; font-weight: bold; color: #f0f6fc; }}
  .metric-lbl {{ font-size: 12px; color: #8b949e; text-transform: uppercase; margin-top: 2px; }}
  audio {{ outline: none; }}
  .tab-pane {{ display: none; }}
  .tab-pane.active {{ display: block; }}
  
  /* Filter state visibility */
  .filter-included-only .is-excluded {{ display: none !important; }}
  .filter-excluded-only .is-included {{ display: none !important; }}
  
  #toast {{
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #1f6feb;
    color: #fff;
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    opacity: 0;
    transform: translateY(10px);
    transition: all 0.25s ease;
    z-index: 9999;
  }}
  #toast.show {{
    opacity: 1;
    transform: translateY(0);
  }}
</style>
<script>
  let currentFilter = 'all';

  function switchTab(tabId) {{
    document.querySelectorAll('.tier-buttons .tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.getElementById('btn-' + tabId).classList.add('active');
    document.getElementById('pane-' + tabId).classList.add('active');
    applyFilter(currentFilter);
    updateCounts();
  }}

  function setFilter(mode) {{
    currentFilter = mode;
    document.querySelectorAll('.filter-btn').forEach(b => {{
      b.classList.remove('active');
      b.classList.remove('active-warn');
    }});
    const activeBtn = document.getElementById('flt-' + mode);
    if (activeBtn) {{
      if (mode === 'excluded') activeBtn.classList.add('active-warn');
      else activeBtn.classList.add('active');
    }}
    applyFilter(mode);
  }}

  function applyFilter(mode) {{
    const activePane = document.querySelector('.tab-pane.active');
    if (!activePane) return;
    activePane.classList.remove('filter-included-only', 'filter-excluded-only');
    if (mode === 'included') activePane.classList.add('filter-included-only');
    else if (mode === 'excluded') activePane.classList.add('filter-excluded-only');
  }}

  function showToast(msg, bg) {{
    const t = document.getElementById('toast');
    t.innerText = msg;
    t.style.background = bg || '#1f6feb';
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
  }}

  async function toggleExclude(fn, btn) {{
    const card = btn.closest('.pada-card');
    const isCurrentlyExcluded = card.classList.contains('is-excluded');
    const newExcluded = !isCurrentlyExcluded;
    
    btn.disabled = true;
    btn.innerText = "Saving...";
    
    try {{
      const resp = await fetch('/api/exclude', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ filename: fn, excluded: newExcluded }})
      }});
      const res = await resp.json();
      
      if (res.status === 'ok') {{
        const exclBadge = card.querySelector('.excluded-badge');
        if (newExcluded) {{
          card.classList.remove('is-included');
          card.classList.add('is-excluded');
          card.style.background = '#1a120c';
          card.style.borderColor = '#ea580c';
          exclBadge.style.display = 'inline-block';
          btn.innerText = '↩️ Include in Training';
          btn.style.background = '#262c36';
          btn.style.borderColor = '#485363';
          btn.style.color = '#93c5fd';
          showToast('🚫 Excluded: ' + fn, '#c2410c');
        }} else {{
          card.classList.remove('is-excluded');
          card.classList.add('is-included');
          card.style.background = '#161b22';
          card.style.borderColor = '#30363d';
          exclBadge.style.display = 'none';
          btn.innerText = '🚫 Exclude from Training';
          btn.style.background = '#301b1b';
          btn.style.borderColor = '#7f1d1d';
          btn.style.color = '#fca5a5';
          showToast('✅ Restored to Training: ' + fn, '#15803d');
        }}
        updateCounts();
        applyFilter(currentFilter);
      }}
    }} catch (err) {{
      alert('Error updating exclusion: ' + err);
      btn.innerText = isCurrentlyExcluded ? '↩️ Include in Training' : '🚫 Exclude from Training';
    }} finally {{
      btn.disabled = false;
    }}
  }}

  function updateCounts() {{
    const activePane = document.querySelector('.tab-pane.active');
    if (!activePane) return;
    const all = activePane.querySelectorAll('.pada-card').length;
    const excl = activePane.querySelectorAll('.pada-card.is-excluded').length;
    const incl = all - excl;
    
    const exclCounter = activePane.querySelector('.metric-excluded-val');
    if (exclCounter) exclCounter.innerText = excl;
    const readyCounter = activePane.querySelector('.metric-ready-val');
    if (readyCounter) readyCounter.innerText = incl;
    
    document.getElementById('flt-all-count').innerText = all;
    document.getElementById('flt-ready-count').innerText = incl;
    document.getElementById('flt-excl-count').innerText = excl;
  }}
  
  document.addEventListener('DOMContentLoaded', async () => {{
    try {{
      const resp = await fetch('/api/exclusions');
      const data = await resp.json();
      document.querySelectorAll('.pada-card').forEach(card => {{
        const fn = card.getAttribute('data-fn');
        const isExcl = Boolean(data[fn]);
        const btn = card.querySelector('.exclude-toggle-btn');
        const exclBadge = card.querySelector('.excluded-badge');
        if (isExcl) {{
          card.classList.remove('is-included');
          card.classList.add('is-excluded');
          card.style.background = '#1a120c';
          card.style.borderColor = '#ea580c';
          if (exclBadge) exclBadge.style.display = 'inline-block';
          if (btn) {{
            btn.innerText = '↩️ Include in Training';
            btn.style.background = '#262c36';
            btn.style.borderColor = '#485363';
            btn.style.color = '#93c5fd';
          }}
        }} else {{
          card.classList.remove('is-excluded');
          card.classList.add('is-included');
          card.style.background = '#161b22';
          card.style.borderColor = '#30363d';
          if (exclBadge) exclBadge.style.display = 'none';
          if (btn) {{
            btn.innerText = '🚫 Exclude from Training';
            btn.style.background = '#301b1b';
            btn.style.borderColor = '#7f1d1d';
            btn.style.color = '#fca5a5';
          }}
        }}
      }});
    }} catch (e) {{
      console.warn('Could not sync live exclusions:', e);
    }}
    updateCounts();
    applyFilter(currentFilter);

    // Live audio position tracker
    document.querySelectorAll('audio').forEach(audio => {{
      const card = audio.closest('.pada-card');
      if (!card) return;
      const livePos = card.querySelector('.live-pos');
      const tapePos = card.querySelector('.tape-pos');
      const metaSpan = card.querySelector('span[style*="font-family:monospace"]');
      let baseSt = 0;
      if (metaSpan) {{
        const m = metaSpan.innerText.match(/\[([0-9.]+)s/);
        if (m) baseSt = parseFloat(m[1]) || 0;
      }}
      
      const totalDurEl = card.querySelector('.audio-total-dur');
      
      const onMetadata = () => {{
        if (audio.duration && !isNaN(audio.duration)) {{
          if (totalDurEl) totalDurEl.innerText = audio.duration.toFixed(3) + 's';
        }}
      }};
      audio.addEventListener('loadedmetadata', onMetadata);
      audio.addEventListener('canplay', onMetadata);
      if (audio.duration && !isNaN(audio.duration)) onMetadata();

      const updateTime = () => {{
        if (livePos) livePos.innerText = audio.currentTime.toFixed(3) + 's';
        if (tapePos) tapePos.innerText = (baseSt + audio.currentTime).toFixed(3) + 's';
        if (audio.duration && !isNaN(audio.duration) && totalDurEl) {{
          totalDurEl.innerText = audio.duration.toFixed(3) + 's';
        }}
      }};

      audio.addEventListener('timeupdate', updateTime);
      audio.addEventListener('seeked', updateTime);
      audio.addEventListener('ended', () => {{
        if (livePos && audio.duration) livePos.innerText = audio.duration.toFixed(3) + 's';
        if (tapePos && audio.duration) tapePos.innerText = (baseSt + audio.duration).toFixed(3) + 's';
        if (totalDurEl && audio.duration) totalDurEl.innerText = audio.duration.toFixed(3) + 's';
      }});
    }});
  }});

  {NORM_JAVASCRIPT}
</script>
</head>
<body>

<div id="toast"></div>

<h1>📖 Bhagavad-gītā Chapter 2 — Dual-Tier Inspector & Curation Studio</h1>
<div style="color: #8b949e; font-size: 14px; margin-bottom: 16px;">
  <b>Golden Text Source:</b> 1972 Macmillan BBT Master Text (Authentic Sanskrit Devanagari & Academic IAST)<br>
  <b>Master Audio:</b> 24kHz De-Hissed Master (Hybrid Surgical Split + NL-Means: 0-3.2kHz 100% bit-exact)<br>
  <b>Continuous Alignment:</b> 293 divider points spanning 0.000s → {pada_total_dur:.1f}s with 0.000ms loss
</div>

<div class="tabs">
  <div class="tier-buttons">
    <button id="btn-hemi" class="tab-btn active" onclick="switchTab('hemi')">✨ Two Pādas Combined ({len(hemi_items)} Units • ~6.7s Cadence)</button>
    <button id="btn-pada" class="tab-btn" onclick="switchTab('pada')">🔍 Single Pāda by Pāda ({len(pada_items)} Units • ~3.5s Cadence)</button>
  </div>
  <div class="filter-buttons">
    <button id="flt-all" class="filter-btn active" onclick="setFilter('all')">All (<span id="flt-all-count">{len(hemi_items)}</span>)</button>
    <button id="flt-included" class="filter-btn" onclick="setFilter('included')">Ready for Training (<span id="flt-ready-count">{len(hemi_items)-hemi_excluded_count}</span>)</button>
    <button id="flt-excluded" class="filter-btn" onclick="setFilter('excluded')">🚫 Excluded (<span id="flt-excl-count">{hemi_excluded_count}</span>)</button>
  </div>
</div>

<!-- HEMISTICH PANE (2-PADAS COMBINED) -->
<div id="pane-hemi" class="tab-pane active">
  <div class="metrics">
    <div class="metric-card">
      <div class="metric-val">{len(hemi_items)}</div>
      <div class="metric-lbl">Total 2-Pāda Units</div>
    </div>
    <div class="metric-card">
      <div class="metric-val metric-ready-val" style="color: #34d399;">{len(hemi_items)-hemi_excluded_count}</div>
      <div class="metric-lbl">Active Training Set</div>
    </div>
    <div class="metric-card">
      <div class="metric-val metric-excluded-val" style="color: #ea580c;">{hemi_excluded_count}</div>
      <div class="metric-lbl">Excluded from Training</div>
    </div>
    <div class="metric-card">
      <div class="metric-val" style="color: #f1c40f;">~6.7s</div>
      <div class="metric-lbl">Average Unit Duration</div>
    </div>
  </div>
  {hemi_prosody_summary_html}
  {hemi_cards_html}
</div>

<!-- SINGLE PADA PANE -->
<div id="pane-pada" class="tab-pane">
  <div class="metrics">
    <div class="metric-card">
      <div class="metric-val">{len(pada_items)}</div>
      <div class="metric-lbl">Total 1-Pāda Units</div>
    </div>
    <div class="metric-card">
      <div class="metric-val metric-ready-val" style="color: #34d399;">{len(pada_items)-pada_excluded_count}</div>
      <div class="metric-lbl">Active Training Set</div>
    </div>
    <div class="metric-card">
      <div class="metric-val metric-excluded-val" style="color: #ea580c;">{pada_excluded_count}</div>
      <div class="metric-lbl">Excluded from Training</div>
    </div>
    <div class="metric-card">
      <div class="metric-val" style="color: #f1c40f;">~3.5s</div>
      <div class="metric-lbl">Average Unit Duration</div>
    </div>
  </div>
  {pada_prosody_summary_html}
  {pada_cards_html}
</div>

</body>
</html>
"""

out_html = os.path.join(ch2_dir, 'index.html')
with open(out_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"Dual-Tier Chapter 2 Inspector & Curation Studio successfully generated at {out_html}")
