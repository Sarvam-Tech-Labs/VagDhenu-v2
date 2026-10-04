# -*- coding: utf-8 -*-
"""
normalization_ui_component.py
Renders the non-destructive +/-2s normalization workspace with:
- Dual boundary markers (Marker 1 & Marker 2)
- Visual SVG audio waveform of the +/-2s padded audio
- Play Selection / Stop Button
- Target indicator badge (6.5s - 7.5s)
- Live absolute tape timing & relative offsets
- Persistent manual normalization badge
"""

def generate_norm_workspace_html(ch_num, fn, t_st, t_et, dur, is_normalized=False, peaks=None):
    pad_s = 2.0
    pad_st = max(0.0, t_st - pad_s)
    # Relative offset of current verse start within the padded audio
    init_rel_st = t_st - pad_st
    init_rel_et = init_rel_st + dur
    pad_total_dur = dur + (2.0 * pad_s)
    
    norm_saved_badge = '<span class="norm-saved-badge" style="background:#0f382a; color:#34d399; border:1px solid #059669; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:bold;">✨ MANUALLY NORMALIZED</span>' if is_normalized else '<span class="norm-saved-badge" style="display:none; background:#0f382a; color:#34d399; border:1px solid #059669; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:bold;">✨ MANUALLY NORMALIZED</span>'
    ws_border = "#059669" if is_normalized else "#1f2937"
    
    if 6.5 <= dur <= 7.5:
        initial_status_text = "✅ Normalized (6.5s - 7.5s)"
        initial_status_bg = "#064e3b"
        initial_status_color = "#34d399"
        initial_status_border = "#059669"
    elif dur < 6.5:
        initial_status_text = f"⚠️ Fast ({dur:.2f}s &lt; 6.5s)"
        initial_status_bg = "#451a1a"
        initial_status_color = "#fca5a5"
        initial_status_border = "#7f1d1d"
    else:
        initial_status_text = f"⚠️ Extended ({dur:.2f}s &gt; 7.5s)"
        initial_status_bg = "#451a03"
        initial_status_color = "#fdba74"
        initial_status_border = "#9a3412"

    # SVG Waveform generation
    svg_bars = []
    if peaks and len(peaks) > 0:
        n_bars = len(peaks)
        svg_w = 720
        svg_h = 50
        bar_w = max(1.6, (svg_w / n_bars) - 0.8)
        mid_y = svg_h / 2.0
        for i, val in enumerate(peaks):
            x = i * (svg_w / n_bars)
            amp = float(val)
            if amp > 0.05:
                # Active speech/chanting
                bar_h = max(3.0, amp * (svg_h * 0.90))
                fill_color = "#38bdf8" if amp > 0.25 else "#64748b"
            else:
                # Tape silence / pause floor
                bar_h = 1.5
                fill_color = "#1e293b"
            y = mid_y - (bar_h / 2.0)
            svg_bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="0.8" fill="{fill_color}" class="wf-bar" data-idx="{i}"/>')
    svg_content = "".join(svg_bars)

    # Initial marker percentage positions on the waveform
    st_pct = (init_rel_st / pad_total_dur) * 100.0 if pad_total_dur > 0 else 0.0
    et_pct = (init_rel_et / pad_total_dur) * 100.0 if pad_total_dur > 0 else 100.0

    html = f"""
    <!-- NON-DESTRUCTIVE NORMALIZATION WORKSPACE (+/- 2.0s PADDED CONTEXT) -->
    <div class="norm-workspace" data-fn="{fn}" data-ch="{ch_num}" data-pad-st="{pad_st:.3f}" data-orig-abs-st="{t_st:.3f}" data-orig-abs-et="{t_et:.3f}" data-init-rel-st="{init_rel_st:.3f}" data-init-rel-et="{init_rel_et:.3f}" data-pad-dur="{pad_total_dur:.3f}" style="margin-top: 14px; background: #0b0f14; border: 1px solid {ws_border}; border-radius: 8px; padding: 12px 14px;">
      
      <!-- Header with Status Badges -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 13px; font-weight: bold; color: #38bdf8;">🎛️ Normalization Workspace</span>
          <span style="font-size: 11px; background: #1e293b; color: #94a3b8; padding: 2px 6px; border-radius: 4px; font-family: monospace;">±2.0s Context Added</span>
          {norm_saved_badge}
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <span class="norm-status-badge" style="font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 12px; background: {initial_status_bg}; color: {initial_status_color}; border: 1px solid {initial_status_border};">{initial_status_text}</span>
          <span style="font-size: 12px; font-family: monospace; color: #c9d1d9;">Span: <b class="norm-selected-dur" style="color: #fbbf24;">{dur:.3f}s</b></span>
        </div>
      </div>
      
      <!-- Padded Audio Player & Audition / Cue / Pause / Reset / Save Controls -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 12px;">
        <audio class="norm-audio" preload="none" src="hemistichs_padded/{fn}?v={pad_total_dur:.3f}" style="height: 32px; flex: 1;"></audio>
        <div style="display: flex; gap: 6px; align-items: center;">
          <button type="button" class="norm-btn-play" onclick="playNormSelection('{fn}')" style="background: #1e3a5f; border: 1px solid #2563eb; color: #bfdbfe; padding: 6px 11px; border-radius: 6px; cursor: pointer; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;" title="Play entire cut from Marker 1 to Marker 2">▶️ Full Cut</button>
          <button type="button" class="norm-btn-play-st-cue" onclick="playStartToCueNorm('{fn}')" style="background: #1e3a5f; border: 1px solid #38bdf8; color: #bae6fd; padding: 6px 11px; border-radius: 6px; cursor: pointer; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;" title="Play from Start (Marker 1) to Middle Cue">▶️ Start→Cue</button>
          <button type="button" class="norm-btn-play-cue-et" onclick="playCueToEndNorm('{fn}')" style="background: #3b2a05; border: 1px solid #d97706; color: #fde68a; padding: 6px 11px; border-radius: 6px; cursor: pointer; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;" title="Play from Middle Cue to End (Marker 2)">▶️ Cue→End</button>
          <button type="button" class="norm-btn-pause" onclick="togglePauseResumeNorm('{fn}')" style="background: #1f2937; border: 1px solid #374151; color: #e5e7eb; padding: 6px 11px; border-radius: 6px; cursor: pointer; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">⏸️ Pause</button>
          <button type="button" class="norm-btn-reset-left" onclick="resetNormMarker('{fn}', 'start')" style="background: #1e293b; border: 1px solid #0284c7; color: #7dd3fc; padding: 6px 9px; border-radius: 6px; cursor: pointer; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;" title="Reset left marker (Marker 1) to original start">🔄 Reset Left</button>
          <button type="button" class="norm-btn-reset-right" onclick="resetNormMarker('{fn}', 'end')" style="background: #1e293b; border: 1px solid #dc2626; color: #fca5a5; padding: 6px 9px; border-radius: 6px; cursor: pointer; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;" title="Reset right marker (Marker 2) to original end">🔄 Reset Right</button>
          <button type="button" class="norm-btn-save" onclick="saveNormBoundary('{fn}', {ch_num})" style="background: #064e3b; border: 1px solid #059669; color: #a7f3d0; padding: 6px 13px; border-radius: 6px; cursor: pointer; font-size: 11px; font-weight: bold; display: inline-flex; align-items: center; gap: 4px;">💾 Save Cut</button>
        </div>
      </div>

      <!-- VISUAL AUDIO WAVEFORM DISPLAY WITH DUAL MARKER OVERLAYS & PERSISTENT CUE ANCHOR -->
      <div class="waveform-container" style="position: relative; height: 54px; background: #030712; border: 1px solid #1e293b; border-radius: 6px; overflow: hidden; margin-bottom: 8px; cursor: crosshair;" onclick="onWaveformClick(event, '{fn}')">
        <!-- SVG Waveform -->
        <svg viewBox="0 0 700 50" preserveAspectRatio="none" style="width: 100%; height: 100%; display: block;">
          {svg_content}
        </svg>

        <!-- Selected Region Highlight (Between M1 and M2) -->
        <div class="wf-region-highlight" style="position: absolute; top: 0; bottom: 0; left: {st_pct:.2f}%; width: {et_pct - st_pct:.2f}%; background: rgba(56, 189, 248, 0.15); border-left: 2px solid #38bdf8; border-right: 2px solid #f87171; pointer-events: none; transition: left 0.05s, width 0.05s;"></div>

        <!-- Marker 1 Flag (Start) -->
        <div class="wf-flag-m1" style="position: absolute; top: 2px; left: {st_pct:.2f}%; transform: translateX(-50%); background: #0284c7; color: #ffffff; font-size: 9px; font-family: monospace; font-weight: bold; padding: 1px 4px; border-radius: 3px; pointer-events: none; z-index: 5;">M1</div>

        <!-- Cue Anchor Flag (Middle Scrub Anchor - Amber) -->
        <div class="wf-flag-cue" style="position: absolute; top: 2px; left: {st_pct:.2f}%; transform: translateX(-50%); background: #b45309; color: #ffffff; font-size: 9px; font-family: monospace; font-weight: bold; padding: 1px 4px; border-radius: 3px; pointer-events: none; z-index: 6;">CUE</div>

        <!-- Marker 2 Flag (End) -->
        <div class="wf-flag-m2" style="position: absolute; top: 2px; left: {et_pct:.2f}%; transform: translateX(-50%); background: #dc2626; color: #ffffff; font-size: 9px; font-family: monospace; font-weight: bold; padding: 1px 4px; border-radius: 3px; pointer-events: none; z-index: 5;">M2</div>

        <!-- Playhead Scrub Line -->
        <div class="wf-playhead" style="position: absolute; top: 0; bottom: 0; left: 0%; width: 2px; background: #fbbf24; display: none; pointer-events: none; z-index: 10;"></div>
      </div>
      
      <!-- Interactive Dual Marker Control Box -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; background: #030712; padding: 10px 12px; border-radius: 6px; border: 1px solid #111827; font-size: 11px; font-family: monospace;">
        
        <!-- START MARKER (M1) -->
        <div style="display: flex; flex-direction: column; gap: 4px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: #38bdf8; font-weight: bold;">📍 Marker 1 (Start)</span>
            <button type="button" onclick="setMarkerLive('{fn}', 'start')" style="background: #111827; border: 1px solid #374151; color: #9ca3af; padding: 1px 6px; border-radius: 4px; cursor: pointer; font-size: 10px;">Set to Live Pos</button>
          </div>
          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="color: #6b7280;">Abs:</span>
            <input type="number" step="0.01" class="norm-abs-st" value="{t_st:.3f}" onchange="onManualInputChange('{fn}')" style="width: 75px; background: #1f2937; border: 1px solid #374151; color: #f3f4f6; padding: 2px 4px; border-radius: 4px; font-family: monospace; font-size: 11px;">
            <span style="color: #6b7280;">Rel:</span>
            <span class="norm-rel-st" style="color: #38bdf8; font-weight: bold;">+{init_rel_st:.3f}s</span>
            <div style="display: flex; gap: 2px; margin-left: auto;">
              <button type="button" onclick="nudgeMarker('{fn}', 'start', -0.05)" style="background: #1f2937; border: 1px solid #374151; color: #9ca3af; padding: 1px 5px; border-radius: 3px; cursor: pointer;">-50ms</button>
              <button type="button" onclick="nudgeMarker('{fn}', 'start', 0.05)" style="background: #1f2937; border: 1px solid #374151; color: #9ca3af; padding: 1px 5px; border-radius: 3px; cursor: pointer;">+50ms</button>
            </div>
          </div>
        </div>
        
        <!-- END MARKER (M2) -->
        <div style="display: flex; flex-direction: column; gap: 4px; border-left: 1px solid #1f2937; padding-left: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: #f87171; font-weight: bold;">📍 Marker 2 (End)</span>
            <button type="button" onclick="setMarkerLive('{fn}', 'end')" style="background: #111827; border: 1px solid #374151; color: #9ca3af; padding: 1px 6px; border-radius: 4px; cursor: pointer; font-size: 10px;">Set to Live Pos</button>
          </div>
          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="color: #6b7280;">Abs:</span>
            <input type="number" step="0.01" class="norm-abs-et" value="{t_et:.3f}" onchange="onManualInputChange('{fn}')" style="width: 75px; background: #1f2937; border: 1px solid #374151; color: #f3f4f6; padding: 2px 4px; border-radius: 4px; font-family: monospace; font-size: 11px;">
            <span style="color: #6b7280;">Rel:</span>
            <span class="norm-rel-et" style="color: #f87171; font-weight: bold;">+{init_rel_et:.3f}s</span>
            <div style="display: flex; gap: 2px; margin-left: auto;">
              <button type="button" onclick="nudgeMarker('{fn}', 'end', -0.05)" style="background: #1f2937; border: 1px solid #374151; color: #9ca3af; padding: 1px 5px; border-radius: 3px; cursor: pointer;">-50ms</button>
              <button type="button" onclick="nudgeMarker('{fn}', 'end', 0.05)" style="background: #1f2937; border: 1px solid #374151; color: #9ca3af; padding: 1px 5px; border-radius: 3px; cursor: pointer;">+50ms</button>
            </div>
          </div>
        </div>
        
      </div>
      
      <!-- Interactive Scrub Timeline / Visual Triple-Slider (Start, Middle Scrub, End) -->
      <div style="margin-top: 8px; position: relative;">
        <!-- Marker 1 Slider (Start - Blue) -->
        <input type="range" class="norm-slider-st" min="0" max="{pad_total_dur:.3f}" step="0.01" value="{init_rel_st:.3f}" oninput="onSliderMove('{fn}', 'start', this.value)" style="width: 100%; accent-color: #38bdf8; cursor: pointer;" title="Marker 1 (Start)">
        <!-- Middle Playhead Scrub Slider (Amber) -->
        <input type="range" class="norm-slider-mid" min="0" max="{pad_total_dur:.3f}" step="0.01" value="{init_rel_st:.3f}" oninput="onMiddleScrubMove('{fn}', this.value)" onchange="onMiddleScrubChange('{fn}', this.value)" style="width: 100%; accent-color: #fbbf24; cursor: pointer; margin-top: -6px;" title="Middle Scrub Playhead (Jump anywhere)">
        <!-- Marker 2 Slider (End - Red) -->
        <input type="range" class="norm-slider-et" min="0" max="{pad_total_dur:.3f}" step="0.01" value="{init_rel_et:.3f}" oninput="onSliderMove('{fn}', 'end', this.value)" style="width: 100%; accent-color: #f87171; cursor: pointer; margin-top: -6px;" title="Marker 2 (End)">
        
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #6b7280; font-family: monospace; margin-top: 2px;">
          <span>0.0s (Tape: {pad_st:.2f}s)</span>
          <span style="display: flex; gap: 8px; align-items: center;">
            <span style="color: #fbbf24;">Scrub: <b class="norm-mid-pos">+{init_rel_st:.2f}s</b></span>
            <span style="color: #34d399;">Selection: <b class="norm-dur-label">{dur:.2f}s</b></span>
          </span>
          <span>{pad_total_dur:.2f}s (Tape: {t_et+pad_s:.2f}s)</span>
        </div>
      </div>
      
    </div>
    """
    return html

NORM_JAVASCRIPT = """
  // --- NORMALIZATION WORKSPACE SCRIPT ---
  function getNormWorkspace(fn) {
    return document.querySelector(`.norm-workspace[data-fn="${fn}"]`);
  }

  function updateNormDisplay(ws) {
    const padSt = parseFloat(ws.dataset.padSt);
    const padDur = parseFloat(ws.dataset.padDur);
    const absStInput = ws.querySelector('.norm-abs-st');
    const absEtInput = ws.querySelector('.norm-abs-et');
    const relStEl = ws.querySelector('.norm-rel-st');
    const relEtEl = ws.querySelector('.norm-rel-et');
    const sliderSt = ws.querySelector('.norm-slider-st');
    const sliderEt = ws.querySelector('.norm-slider-et');
    const durEl = ws.querySelector('.norm-selected-dur');
    const durLbl = ws.querySelector('.norm-dur-label');
    const badge = ws.querySelector('.norm-status-badge');

    let absSt = parseFloat(absStInput.value) || 0;
    let absEt = parseFloat(absEtInput.value) || 0;

    if (absEt < absSt) {
      absEt = absSt + 0.1;
      absEtInput.value = absEt.toFixed(3);
    }

    const relSt = Math.max(0, absSt - padSt);
    const relEt = Math.max(0, absEt - padSt);
    const dur = absEt - absSt;

    relStEl.innerText = '+' + relSt.toFixed(3) + 's';
    relEtEl.innerText = '+' + relEt.toFixed(3) + 's';
    sliderSt.value = relSt.toFixed(3);
    sliderEt.value = relEt.toFixed(3);

    durEl.innerText = dur.toFixed(3) + 's';
    if (durLbl) durLbl.innerText = dur.toFixed(2) + 's';

    // Update Waveform Visual Overlays
    const region = ws.querySelector('.wf-region-highlight');
    const flagM1 = ws.querySelector('.wf-flag-m1');
    const flagM2 = ws.querySelector('.wf-flag-m2');
    if (region && flagM1 && flagM2 && padDur > 0) {
      const stPct = (relSt / padDur) * 100.0;
      const etPct = (relEt / padDur) * 100.0;
      region.style.left = stPct.toFixed(2) + '%';
      region.style.width = Math.max(0, etPct - stPct).toFixed(2) + '%';
      flagM1.style.left = stPct.toFixed(2) + '%';
      flagM2.style.left = etPct.toFixed(2) + '%';
    }

    // Normalization status indicator (6.5s - 7.5s)
    if (dur >= 6.5 && dur <= 7.5) {
      badge.innerText = '✅ Normalized (6.5s - 7.5s)';
      badge.style.background = '#064e3b';
      badge.style.color = '#34d399';
      badge.style.borderColor = '#059669';
    } else if (dur < 6.5) {
      badge.innerText = `⚠️ Fast (${dur.toFixed(2)}s < 6.5s)`;
      badge.style.background = '#451a1a';
      badge.style.color = '#fca5a5';
      badge.style.borderColor = '#7f1d1d';
    } else {
      badge.innerText = `⚠️ Extended (${dur.toFixed(2)}s > 7.5s)`;
      badge.style.background = '#451a03';
      badge.style.color = '#fdba74';
      badge.style.borderColor = '#9a3412';
    }
  }

  function onSliderMove(fn, marker, val) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const padSt = parseFloat(ws.dataset.padSt);
    const relVal = parseFloat(val);
    const absVal = padSt + relVal;

    if (marker === 'start') {
      ws.querySelector('.norm-abs-st').value = absVal.toFixed(3);
    } else {
      ws.querySelector('.norm-abs-et').value = absVal.toFixed(3);
    }
    updateNormDisplay(ws);
  }

  function onMiddleScrubMove(fn, val) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const relVal = parseFloat(val);
    const padDur = parseFloat(ws.dataset.padDur);
    const midPosEl = ws.querySelector('.norm-mid-pos');
    if (midPosEl) midPosEl.innerText = '+' + relVal.toFixed(2) + 's';

    const cueFlag = ws.querySelector('.wf-flag-cue');
    if (cueFlag && padDur > 0) {
      cueFlag.style.left = ((relVal / padDur) * 100.0).toFixed(2) + '%';
    }

    const playhead = ws.querySelector('.wf-playhead');
    if (playhead && padDur > 0) {
      playhead.style.display = 'block';
      playhead.style.left = ((relVal / padDur) * 100.0).toFixed(2) + '%';
    }

    const audio = ws.querySelector('.norm-audio');
    if (audio) {
      audio.currentTime = relVal;
    }
  }

  function onMiddleScrubChange(fn, val) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const audio = ws.querySelector('.norm-audio');
    const relVal = parseFloat(val);
    if (audio) {
      audio.currentTime = relVal;
      isAuditionPaused = true;
      const pauseBtn = ws.querySelector('.norm-btn-pause');
      if (pauseBtn) {
        pauseBtn.innerHTML = '▶️ Resume';
        pauseBtn.style.background = '#2563eb';
        pauseBtn.style.borderColor = '#3b82f6';
        pauseBtn.style.color = '#ffffff';
      }
    }
  }

  function resetNormMarker(fn, marker) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    stopNormSelection(fn);
    if (marker === 'start') {
      const origSt = parseFloat(ws.dataset.origAbsSt);
      if (!isNaN(origSt)) ws.querySelector('.norm-abs-st').value = origSt.toFixed(3);
      showToast(`🔄 Reset Marker 1 (Left) for ${fn}`, '#0284c7');
    } else {
      const origEt = parseFloat(ws.dataset.origAbsEt);
      if (!isNaN(origEt)) ws.querySelector('.norm-abs-et').value = origEt.toFixed(3);
      showToast(`🔄 Reset Marker 2 (Right) for ${fn}`, '#dc2626');
    }
    updateNormDisplay(ws);
  }

  function onManualInputChange(fn) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    updateNormDisplay(ws);
  }

  function nudgeMarker(fn, marker, delta) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const input = marker === 'start' ? ws.querySelector('.norm-abs-st') : ws.querySelector('.norm-abs-et');
    let val = parseFloat(input.value) || 0;
    val = Math.max(0, val + delta);
    input.value = val.toFixed(3);
    updateNormDisplay(ws);
  }

  function setMarkerLive(fn, marker) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const audio = ws.querySelector('.norm-audio');
    if (!audio) return;
    const padSt = parseFloat(ws.dataset.padSt);
    const liveAbs = padSt + audio.currentTime;

    if (marker === 'start') {
      ws.querySelector('.norm-abs-st').value = liveAbs.toFixed(3);
    } else {
      ws.querySelector('.norm-abs-et').value = liveAbs.toFixed(3);
    }
    updateNormDisplay(ws);
    showToast(`Marker ${marker.toUpperCase()} set to live tape pos: ${liveAbs.toFixed(3)}s`, '#1f6feb');
  }

  function onWaveformClick(e, fn) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const container = ws.querySelector('.waveform-container');
    const rect = container.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickPct = Math.max(0, Math.min(1, clickX / rect.width));
    const padDur = parseFloat(ws.dataset.padDur);
    const padSt = parseFloat(ws.dataset.padSt);
    const clickedRelTime = clickPct * padDur;
    const clickedAbsTime = padSt + clickedRelTime;

    const absSt = parseFloat(ws.querySelector('.norm-abs-st').value);
    const absEt = parseFloat(ws.querySelector('.norm-abs-et').value);

    // Snap to whichever marker is closer
    const distToSt = Math.abs(clickedAbsTime - absSt);
    const distToEt = Math.abs(clickedAbsTime - absEt);

    if (distToSt < distToEt) {
      ws.querySelector('.norm-abs-st').value = clickedAbsTime.toFixed(3);
      showToast(`📍 Marker 1 moved to waveform position: ${clickedAbsTime.toFixed(3)}s`, '#0284c7');
    } else {
      ws.querySelector('.norm-abs-et').value = clickedAbsTime.toFixed(3);
      showToast(`📍 Marker 2 moved to waveform position: ${clickedAbsTime.toFixed(3)}s`, '#dc2626');
    }
    updateNormDisplay(ws);
  }

  let activeAuditionInterval = null;
  let activeAudioPlaying = null;
  let isAuditionPaused = false;

  function togglePauseResumeNorm(fn) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const audio = ws.querySelector('.norm-audio');
    const pauseBtn = ws.querySelector('.norm-btn-pause');
    if (!audio) return;

    if (!audio.paused) {
      // It is currently playing -> PAUSE IT
      if (activeAuditionInterval) {
        clearInterval(activeAuditionInterval);
        activeAuditionInterval = null;
      }
      audio.pause();
      isAuditionPaused = true;
      if (pauseBtn) {
        pauseBtn.innerHTML = '▶️ Resume';
        pauseBtn.style.background = '#2563eb';
        pauseBtn.style.borderColor = '#3b82f6';
        pauseBtn.style.color = '#ffffff';
      }
    } else {
      // It is currently paused -> RESUME IT from current position
      resumeNormSelection(fn);
    }
  }

  function stopNormSelection(fn) {
    if (activeAuditionInterval) {
      clearInterval(activeAuditionInterval);
      activeAuditionInterval = null;
    }
    isAuditionPaused = false;
    const ws = getNormWorkspace(fn);
    if (ws) {
      const audio = ws.querySelector('.norm-audio');
      if (audio) {
        audio.pause();
      }
      const playhead = ws.querySelector('.wf-playhead');
      if (playhead) playhead.style.display = 'none';
      const pauseBtn = ws.querySelector('.norm-btn-pause');
      if (pauseBtn) {
        pauseBtn.innerHTML = '⏸️ Pause';
        pauseBtn.style.background = '#1f2937';
        pauseBtn.style.borderColor = '#374151';
        pauseBtn.style.color = '#e5e7eb';
      }
    }
    if (activeAudioPlaying) {
      activeAudioPlaying.pause();
      activeAudioPlaying = null;
    }
  }

  function playNormSelection(fn) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const audio = ws.querySelector('.norm-audio');
    const padSt = parseFloat(ws.dataset.padSt);
    const padDur = parseFloat(ws.dataset.padDur);
    const absSt = parseFloat(ws.querySelector('.norm-abs-st').value);
    const absEt = parseFloat(ws.querySelector('.norm-abs-et').value);
    const playhead = ws.querySelector('.wf-playhead');

    const relSt = Math.max(0, absSt - padSt);
    const relEt = Math.max(0, absEt - padSt);

    if (activeAuditionInterval) {
      clearInterval(activeAuditionInterval);
      activeAuditionInterval = null;
    }

    // Play Full Cut ALWAYS starts strictly from the beginning of Marker 1
    audio.currentTime = relSt;
    isAuditionPaused = false;
    activeAudioPlaying = audio;

    if (playhead) {
      playhead.style.display = 'block';
      playhead.style.left = ((relSt / padDur) * 100.0).toFixed(2) + '%';
    }

    const pauseBtn = ws.querySelector('.norm-btn-pause');
    if (pauseBtn) {
      pauseBtn.innerHTML = '⏸️ Pause';
      pauseBtn.style.background = '#1f2937';
      pauseBtn.style.borderColor = '#374151';
      pauseBtn.style.color = '#e5e7eb';
    }

    audio.play();

    activeAuditionInterval = setInterval(() => {
      if (audio.currentTime >= relEt || audio.paused) {
        if (!isAuditionPaused) {
          stopNormSelection(fn);
        }
      } else if (padDur > 0 && playhead) {
        // Sweep the playhead across waveform without moving the user's fixed middle slider
        const currPct = (audio.currentTime / padDur) * 100.0;
        playhead.style.left = currPct.toFixed(2) + '%';
      }
    }, 25);
  }

  function playStartToCueNorm(fn) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const audio = ws.querySelector('.norm-audio');
    const padDur = parseFloat(ws.dataset.padDur);
    const padSt = parseFloat(ws.dataset.padSt);
    const absSt = parseFloat(ws.querySelector('.norm-abs-st').value);
    const relSt = Math.max(0, absSt - padSt);
    const midSlider = ws.querySelector('.norm-slider-mid');
    const cuePos = midSlider ? parseFloat(midSlider.value) : relSt;
    const targetEnd = Math.max(relSt + 0.05, cuePos);
    const playhead = ws.querySelector('.wf-playhead');

    if (activeAuditionInterval) {
      clearInterval(activeAuditionInterval);
      activeAuditionInterval = null;
    }

    // Play from Marker 1 (Start) up to the Middle Cue position
    audio.currentTime = relSt;
    isAuditionPaused = false;
    activeAudioPlaying = audio;

    if (playhead) {
      playhead.style.display = 'block';
      playhead.style.left = ((relSt / padDur) * 100.0).toFixed(2) + '%';
    }

    const pauseBtn = ws.querySelector('.norm-btn-pause');
    if (pauseBtn) {
      pauseBtn.innerHTML = '⏸️ Pause';
      pauseBtn.style.background = '#1f2937';
      pauseBtn.style.borderColor = '#374151';
      pauseBtn.style.color = '#e5e7eb';
    }

    audio.play();

    activeAuditionInterval = setInterval(() => {
      if (audio.currentTime >= targetEnd || audio.paused) {
        if (!isAuditionPaused) {
          stopNormSelection(fn);
        }
      } else if (padDur > 0 && playhead) {
        const currPct = (audio.currentTime / padDur) * 100.0;
        playhead.style.left = currPct.toFixed(2) + '%';
      }
    }, 25);
  }

  function playCueToEndNorm(fn) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const audio = ws.querySelector('.norm-audio');
    const padDur = parseFloat(ws.dataset.padDur);
    const padSt = parseFloat(ws.dataset.padSt);
    const absEt = parseFloat(ws.querySelector('.norm-abs-et').value);
    const relEt = Math.max(0, absEt - padSt);
    const midSlider = ws.querySelector('.norm-slider-mid');
    const cuePos = midSlider ? parseFloat(midSlider.value) : 0;
    const playhead = ws.querySelector('.wf-playhead');

    if (activeAuditionInterval) {
      clearInterval(activeAuditionInterval);
      activeAuditionInterval = null;
    }

    // Play from the Middle Cue position up to Marker 2 (End)
    audio.currentTime = cuePos;
    isAuditionPaused = false;
    activeAudioPlaying = audio;

    if (playhead) {
      playhead.style.display = 'block';
      playhead.style.left = ((cuePos / padDur) * 100.0).toFixed(2) + '%';
    }

    const pauseBtn = ws.querySelector('.norm-btn-pause');
    if (pauseBtn) {
      pauseBtn.innerHTML = '⏸️ Pause';
      pauseBtn.style.background = '#1f2937';
      pauseBtn.style.borderColor = '#374151';
      pauseBtn.style.color = '#e5e7eb';
    }

    audio.play();

    activeAuditionInterval = setInterval(() => {
      if (audio.currentTime >= relEt || audio.paused) {
        if (!isAuditionPaused) {
          stopNormSelection(fn);
        }
      } else if (padDur > 0 && playhead) {
        const currPct = (audio.currentTime / padDur) * 100.0;
        playhead.style.left = currPct.toFixed(2) + '%';
      }
    }, 25);
  }

  function resumeNormSelection(fn) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const audio = ws.querySelector('.norm-audio');
    const padSt = parseFloat(ws.dataset.padSt);
    const padDur = parseFloat(ws.dataset.padDur);
    const absSt = parseFloat(ws.querySelector('.norm-abs-st').value);
    const absEt = parseFloat(ws.querySelector('.norm-abs-et').value);
    const playhead = ws.querySelector('.wf-playhead');

    const relSt = Math.max(0, absSt - padSt);
    const relEt = Math.max(0, absEt - padSt);

    if (activeAuditionInterval) {
      clearInterval(activeAuditionInterval);
      activeAuditionInterval = null;
    }

    // If current time is out of the selection bounds, restart from relSt
    if (audio.currentTime < relSt || audio.currentTime >= relEt) {
      audio.currentTime = relSt;
    }
    isAuditionPaused = false;
    activeAudioPlaying = audio;

    if (playhead) {
      playhead.style.display = 'block';
      playhead.style.left = ((audio.currentTime / padDur) * 100.0).toFixed(2) + '%';
    }

    const pauseBtn = ws.querySelector('.norm-btn-pause');
    if (pauseBtn) {
      pauseBtn.innerHTML = '⏸️ Pause';
      pauseBtn.style.background = '#1f2937';
      pauseBtn.style.borderColor = '#374151';
      pauseBtn.style.color = '#e5e7eb';
    }

    audio.play();

    activeAuditionInterval = setInterval(() => {
      if (audio.currentTime >= relEt || audio.paused) {
        if (!isAuditionPaused) {
          stopNormSelection(fn);
        }
      } else if (padDur > 0 && playhead) {
        const currPct = (audio.currentTime / padDur) * 100.0;
        playhead.style.left = currPct.toFixed(2) + '%';
      }
    }, 25);
  }

  async function saveNormBoundary(fn, ch) {
    const ws = getNormWorkspace(fn);
    if (!ws) return;
    const absSt = parseFloat(ws.querySelector('.norm-abs-st').value);
    const absEt = parseFloat(ws.querySelector('.norm-abs-et').value);
    const dur = absEt - absSt;

    const btn = ws.querySelector('.norm-btn-save');
    btn.disabled = true;
    btn.innerText = 'Saving...';

    try {
      const resp = await fetch('/api/save_boundary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: fn,
          chapter: ch,
          abs_start_s: absSt,
          abs_end_s: absEt
        })
      });
      const data = await resp.json();
      if (data.status === 'ok') {
        showToast(`✅ Saved ${fn}: [${absSt.toFixed(3)}s → ${absEt.toFixed(3)}s] (${dur.toFixed(3)}s)`, '#059669');
        btn.innerText = '✅ Saved';
        setTimeout(() => { btn.innerText = '💾 Save Cut'; btn.disabled = false; }, 2000);

        // --- INSTANT LIVE UI UPDATE ---
        const badgeEl = ws.querySelector('.norm-saved-badge');
        if (badgeEl) badgeEl.style.display = 'inline-block';
        ws.style.borderColor = '#059669';

        const card = ws.closest('.pada-card');
        if (card) {
          // 1. Update the main card audio player with cache-busting timestamp
          const mainAudio = card.querySelector('audio:not(.norm-audio)');
          if (mainAudio) {
            const baseSrc = mainAudio.src.split('?')[0];
            mainAudio.src = `${baseSrc}?v=${dur.toFixed(3)}&t=${Date.now()}`;
          }
          // 2. Update the span [start -> end] (duration) label
          const spanLabel = card.querySelector('span[style*="font-family:monospace"][style*="font-weight:600"]');
          if (spanLabel) {
            spanLabel.innerHTML = `[${absSt.toFixed(3)}s → ${absEt.toFixed(3)}s] <span style="color:#f1c40f;">(${dur.toFixed(3)}s)</span>`;
          }
          // 3. Update the audio-total-dur display
          const totalDurEl = card.querySelector('.audio-total-dur');
          if (totalDurEl) {
            totalDurEl.innerText = dur.toFixed(3) + 's';
          }
          // 4. Update the tape-pos baseline
          const tapePosEl = card.querySelector('.tape-pos');
          if (tapePosEl) {
            tapePosEl.innerText = absSt.toFixed(3) + 's';
          }
        }
      } else {
        throw new Error(data.detail || 'Save failed');
      }
    } catch (e) {
      showToast(`❌ Error saving boundary: ${e.message}`, '#dc2626');
      btn.innerText = '💾 Save Cut';
      btn.disabled = false;
    }
  }

  // --- HYDRATE SAVED NORMALIZATION CUTS ON PAGE LOAD ---
  async function hydrateNormalizedBoundaries() {
    try {
      const resp = await fetch('/api/normalized_boundaries');
      if (!resp.ok) return;
      const savedMap = await resp.json();
      
      for (const [fn, info] of Object.entries(savedMap)) {
        const ws = getNormWorkspace(fn);
        if (!ws) continue;
        
        // Show badge & emerald border
        const badgeEl = ws.querySelector('.norm-saved-badge');
        if (badgeEl) badgeEl.style.display = 'inline-block';
        ws.style.borderColor = '#059669';
        
        // Update marker values
        if (info.abs_start_s !== undefined) {
          ws.querySelector('.norm-abs-st').value = info.abs_start_s.toFixed(3);
        }
        if (info.abs_end_s !== undefined) {
          ws.querySelector('.norm-abs-et').value = info.abs_end_s.toFixed(3);
        }
        updateNormDisplay(ws);
      }
    } catch (e) {
      console.warn("Could not load normalized boundaries:", e);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hydrateNormalizedBoundaries);
  } else {
    hydrateNormalizedBoundaries();
  }
"""

if __name__ == '__main__':
    print("Normalization UI component compiled successfully!")
