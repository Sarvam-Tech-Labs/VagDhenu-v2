# -*- coding: utf-8 -*-
"""
interactive_normalizer_card.py
Renders the interactive manual normalization audio editor card.
Provides:
- ±2.0s context padded audio track
- Absolute tape timing markers (M1 absolute start, M2 absolute end)
- Live duration delta (M2 - M1) with target normalization indicator (6.5s - 7.5s)
- Drag/Input boundary adjustments with fine nudge buttons (±10ms, ±50ms)
- Audition selection (play between M1 and M2)
- One-click Save Boundary directly updating the master audio cut and manifests.
"""

def render_interactive_normalizer_card(it, pros, chapter_num, is_hemi=False, exclusions=None):
    if exclusions is None:
        exclusions = {}
        
    idx = it['index']
    fn = it['filename']
    dur = it.get('duration_exact_s', it.get('duration', 0.0))
    t_st = float(it['divider_start_s'])
    t_et = float(it['divider_end_s'])
    deva = it['text_deva']
    iast = it['text_iast']
    ctc = it.get('sushrota_ctc', '')
    sim = it.get('similarity', 0.0)
    is_gold = it.get('is_gold', False)
    v = it['verse']
    p = it.get('pada', it.get('pada_combo', ''))
    
    padded_fn = it.get('padded_filename', f"{'hemistichs/' if is_hemi else ''}padded/{fn}")
    pad_st = float(it.get('padded_start_s', max(0.0, t_st - 2.0)))
    pad_et = float(it.get('padded_end_s', t_et + 2.0))
    pad_dur = float(it.get('padded_duration_s', pad_et - pad_st))
    
    loc_st = float(it.get('local_marker_start_s', t_st - pad_st))
    loc_et = float(it.get('local_marker_end_s', t_et - pad_st))
    
    meter_name = pros.get('meter', 'chandas')
    n_syl = pros.get('syllables', 0)
    weights = pros.get('weights', '')
    
    is_excluded = fn in exclusions
    card_class = "pada-card is-excluded" if is_excluded else "pada-card is-included"
    card_border = "#ea580c" if is_excluded else ("#30363d" if is_gold else "#7f1d1d")
    card_bg = "#1a120c" if is_excluded else "#161b22"
    
    status_badge = '<span class="status-badge" style="background:#064e3b; color:#34d399; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:bold; border:1px solid #059669;">GOLD PASS</span>' if is_gold else '<span class="status-badge" style="background:#451a1a; color:#f87171; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:bold; border:1px solid #7f1d1d;">REVIEW</span>'
    excluded_badge_display = "inline-block" if is_excluded else "none"
    btn_text = "↩️ Include in Training" if is_excluded else "🚫 Exclude from Training"
    btn_style = "background:#262c36; border:1px solid #485363; color:#93c5fd;" if is_excluded else "background:#301b1b; border:1px solid #7f1d1d; color:#fca5a5;"
    
    tier_label = f"Verse {chapter_num}.{v} (Pādas {p})" if is_hemi else f"Verse {chapter_num}.{v} (Pada {p})"
    
    # Target 6.5s - 7.5s status for Anustubh hemistichs
    is_target = (6.500 <= dur <= 7.500)
    norm_color = "#34d399" if is_target else ("#38bdf8" if dur < 6.5 else "#fbbf24")
    norm_badge = "🎯 NORMALIZED (6.5s-7.5s)" if is_target else ("⚡ FAST (<6.5s)" if dur < 6.5 else "⏳ RELAXED (>7.5s)")

    card = f"""
    <div class="{card_class}" data-fn="{fn}" data-chapter="{chapter_num}" data-is-hemi="{1 if is_hemi else 0}" data-pad-st="{pad_st:.3f}" data-pad-et="{pad_et:.3f}" style="background:{card_bg}; border:1px solid {card_border}; border-radius:8px; padding:16px; margin-bottom:16px; transition:all 0.2s;">
      
      <!-- HEADER -->
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-weight:bold; color:#f1c40f; font-size:15px;">#{idx:03d} • {tier_label}</span>
          <span style="color:#8b949e; font-size:12px; font-family:monospace;">{fn}</span>
          <span class="norm-badge" style="background:#21262d; border:1px solid {norm_color}; color:{norm_color}; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:bold;">{norm_badge}</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="excluded-badge" style="display:{excluded_badge_display}; background:#7c2d12; color:#fed7aa; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:bold; border:1px solid #ea580c;">🚫 EXCLUDED FROM TRAINING</span>
          <span class="gold-badge-container">{status_badge}</span>
          <button class="exclude-toggle-btn" onclick="toggleExclude('{fn}', this)" style="{btn_style} padding:4px 10px; border-radius:6px; cursor:pointer; font-size:11px; font-weight:600;">{btn_text}</button>
        </div>
      </div>
      
      <!-- TEXT -->
      <div style="font-size:18px; font-weight:600; color:#f0f6fc; margin-bottom:4px;">{deva}</div>
      <div style="font-size:13px; color:#8b949e; font-style:italic; margin-bottom:12px;">{iast}</div>
      
      <!-- METRICS & PROSODY -->
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
      </div>
      
      <!-- INTERACTIVE MANUAL NORMALIZER AUDIO SUITE -->
      <div style="background:#0b0e14; border:1px solid #21262d; border-radius:6px; padding:12px; margin-top:8px;">
        
        <!-- Padded Audio Track Header -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:13px; font-weight:bold; color:#58a6ff;">🎧 Padded Master Context (±2.0s Pad)</span>
            <span style="font-size:11px; color:#8b949e;">[{pad_st:.3f}s → {pad_et:.3f}s]</span>
          </div>
          <div style="font-size:12px; font-family:monospace;">
            Selected Duration: <b class="sel-dur-display" style="color:{norm_color}; font-size:14px;">{dur:.3f}s</b>
          </div>
        </div>

        <!-- Audio Player Element (plays padded audio) -->
        <audio class="padded-audio" controls preload="none" src="{padded_fn}" style="height:32px; width:100%; margin-bottom:8px;"></audio>
        
        <!-- Live Scrubber Info Bar -->
        <div style="display:flex; justify-content:space-between; align-items:center; background:#161b22; padding:5px 10px; border-radius:4px; font-size:11px; font-family:monospace; margin-bottom:10px;">
          <span>⏱️ Padded Player Pos: <b class="live-pad-pos" style="color:#58a6ff;">0.000s</b> / <b style="color:#8b949e;">{pad_dur:.3f}s</b></span>
          <span>📍 Master Tape Absolute Pos: <b class="live-tape-abs" style="color:#34d399;">{pad_st:.3f}s</b></span>
        </div>

        <!-- Marker Adjustment Controls -->
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; background:#161b22; padding:10px; border-radius:6px; border:1px solid #30363d; margin-bottom:10px;">
          
          <!-- Marker 1: START -->
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <span style="font-size:12px; font-weight:bold; color:#38bdf8;">🚩 Marker 1 (Start Cut)</span>
              <button onclick="setMarkerToCurrent('{fn}', 'start')" style="background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:2px 6px; border-radius:4px; font-size:11px; cursor:pointer;" title="Set Marker 1 to current playback position">🎯 Snap to Current</button>
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="font-size:11px; color:#8b949e;">Absolute:</span>
              <input type="number" step="0.01" class="marker-abs-start" value="{t_st:.3f}" onchange="onManualMarkerChange('{fn}')" style="background:#0d1117; border:1px solid #30363d; color:#38bdf8; font-weight:bold; font-family:monospace; padding:4px 6px; border-radius:4px; width:85px;">
              <span style="font-size:11px; color:#8b949e;">s</span>
              <div style="display:flex; gap:2px; margin-left:auto;">
                <button onclick="nudgeMarker('{fn}', 'start', -0.05)" style="background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:2px 5px; border-radius:3px; font-size:10px; cursor:pointer;">-50ms</button>
                <button onclick="nudgeMarker('{fn}', 'start', -0.01)" style="background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:2px 5px; border-radius:3px; font-size:10px; cursor:pointer;">-10ms</button>
                <button onclick="nudgeMarker('{fn}', 'start', 0.01)" style="background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:2px 5px; border-radius:3px; font-size:10px; cursor:pointer;">+10ms</button>
                <button onclick="nudgeMarker('{fn}', 'start', 0.05)" style="background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:2px 5px; border-radius:3px; font-size:10px; cursor:pointer;">+50ms</button>
              </div>
            </div>
          </div>

          <!-- Marker 2: END -->
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <span style="font-size:12px; font-weight:bold; color:#f87171;">🏁 Marker 2 (End Cut)</span>
              <button onclick="setMarkerToCurrent('{fn}', 'end')" style="background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:2px 6px; border-radius:4px; font-size:11px; cursor:pointer;" title="Set Marker 2 to current playback position">🎯 Snap to Current</button>
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="font-size:11px; color:#8b949e;">Absolute:</span>
              <input type="number" step="0.01" class="marker-abs-end" value="{t_et:.3f}" onchange="onManualMarkerChange('{fn}')" style="background:#0d1117; border:1px solid #30363d; color:#f87171; font-weight:bold; font-family:monospace; padding:4px 6px; border-radius:4px; width:85px;">
              <span style="font-size:11px; color:#8b949e;">s</span>
              <div style="display:flex; gap:2px; margin-left:auto;">
                <button onclick="nudgeMarker('{fn}', 'end', -0.05)" style="background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:2px 5px; border-radius:3px; font-size:10px; cursor:pointer;">-50ms</button>
                <button onclick="nudgeMarker('{fn}', 'end', -0.01)" style="background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:2px 5px; border-radius:3px; font-size:10px; cursor:pointer;">-10ms</button>
                <button onclick="nudgeMarker('{fn}', 'end', 0.01)" style="background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:2px 5px; border-radius:3px; font-size:10px; cursor:pointer;">+10ms</button>
                <button onclick="nudgeMarker('{fn}', 'end', 0.05)" style="background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:2px 5px; border-radius:3px; font-size:10px; cursor:pointer;">+50ms</button>
              </div>
            </div>
          </div>
        </div>

        <!-- ACTION BUTTONS BAR -->
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="display:flex; gap:8px;">
            <button onclick="auditionSelection('{fn}')" style="background:#1f6feb; border:1px solid #388bfd; color:#fff; padding:6px 14px; border-radius:6px; cursor:pointer; font-size:12px; font-weight:bold; display:flex; align-items:center; gap:5px;">
              ▶️ Audition Cut (M1 → M2)
            </button>
            <button onclick="playWithContext('{fn}', -0.5, 0.5)" style="background:#21262d; border:1px solid #30363d; color:#c9d1d9; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:12px;">
              🔍 Audition With Context (±0.5s)
            </button>
          </div>
          
          <button class="save-cut-btn" onclick="saveBoundaryCut('{fn}')" style="background:#238636; border:1px solid #2ea043; color:#fff; padding:6px 16px; border-radius:6px; cursor:pointer; font-size:12px; font-weight:bold; display:flex; align-items:center; gap:6px;">
            💾 Save Normalization & Cut WAV
          </button>
        </div>

      </div>
    </div>
    """
    return card
