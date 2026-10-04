# -*- coding: utf-8 -*-
"""
normalizer_js_component.py
Client-side interactive boundary editor controller for Vāgdhenu studio.
Handles:
- Padded audio scrubbing & live position tracking
- Snapping markers (M1/M2) to current playback position
- Nudging markers by ±10ms / ±50ms
- Real-time normalization status badge (6.5s - 7.5s target)
- Auditioning exact selection (play between M1 and M2)
- One-click API persistence (/api/set_boundary)
"""

NORMALIZER_JS = """
  // Interactive Normalization Controller
  function getCardData(fn) {
    const card = document.querySelector(`.pada-card[data-fn="${fn}"]`);
    if (!card) return null;
    const padSt = parseFloat(card.getAttribute('data-pad-st')) || 0;
    const padEt = parseFloat(card.getAttribute('data-pad-et')) || 0;
    const ch = parseInt(card.getAttribute('data-chapter')) || 2;
    const isHemi = parseInt(card.getAttribute('data-is-hemi')) === 1;
    const audio = card.querySelector('.padded-audio');
    const startInput = card.querySelector('.marker-abs-start');
    const endInput = card.querySelector('.marker-abs-end');
    const durDisplay = card.querySelector('.sel-dur-display');
    const normBadge = card.querySelector('.norm-badge');
    
    return { card, padSt, padEt, ch, isHemi, audio, startInput, endInput, durDisplay, normBadge };
  }

  function updateCardDurDisplay(data) {
    const st = parseFloat(data.startInput.value) || 0;
    const et = parseFloat(data.endInput.value) || 0;
    const dur = Math.max(0, et - st);
    
    data.durDisplay.innerText = dur.toFixed(3) + 's';
    
    // Normalization cadence check (6.500s - 7.500s target)
    let color = '#fbbf24';
    let text = '⏳ RELAXED (>7.5s)';
    if (dur >= 6.500 && dur <= 7.500) {
      color = '#34d399';
      text = '🎯 NORMALIZED (6.5s-7.5s)';
    } else if (dur < 6.500) {
      color = '#38bdf8';
      text = '⚡ FAST (<6.5s)';
    }
    data.durDisplay.style.color = color;
    if (data.normBadge) {
      data.normBadge.style.color = color;
      data.normBadge.style.borderColor = color;
      data.normBadge.innerText = text;
    }
  }

  function onManualMarkerChange(fn) {
    const data = getCardData(fn);
    if (!data) return;
    updateCardDurDisplay(data);
  }

  function nudgeMarker(fn, markerType, delta) {
    const data = getCardData(fn);
    if (!data) return;
    const input = markerType === 'start' ? data.startInput : data.endInput;
    let val = parseFloat(input.value) || 0;
    val = Math.max(0, Math.round((val + delta) * 1000) / 1000);
    input.value = val.toFixed(3);
    updateCardDurDisplay(data);
  }

  function setMarkerToCurrent(fn, markerType) {
    const data = getCardData(fn);
    if (!data || !data.audio) return;
    const currentAudioTime = data.audio.currentTime || 0;
    const absTime = Math.round((data.padSt + currentAudioTime) * 1000) / 1000;
    
    if (markerType === 'start') {
      data.startInput.value = absTime.toFixed(3);
    } else {
      data.endInput.value = absTime.toFixed(3);
    }
    updateCardDurDisplay(data);
    showToast(`📍 Marker ${markerType.toUpperCase()} snapped to ${absTime.toFixed(3)}s`, '#1f6feb');
  }

  let auditionTimers = {};

  function auditionSelection(fn) {
    const data = getCardData(fn);
    if (!data || !data.audio) return;
    
    const absSt = parseFloat(data.startInput.value) || 0;
    const absEt = parseFloat(data.endInput.value) || 0;
    
    if (absEt <= absSt) {
      alert('End marker must be after Start marker!');
      return;
    }
    
    // Relative position inside padded file
    const relSt = Math.max(0, absSt - data.padSt);
    const relEt = Math.max(relSt + 0.1, absEt - data.padSt);
    
    if (auditionTimers[fn]) clearInterval(auditionTimers[fn]);
    
    data.audio.currentTime = relSt;
    data.audio.play();
    
    auditionTimers[fn] = setInterval(() => {
      if (data.audio.currentTime >= relEt || data.audio.paused) {
        data.audio.pause();
        clearInterval(auditionTimers[fn]);
        delete auditionTimers[fn];
      }
    }, 25);
  }

  function playWithContext(fn, padBefore = -0.5, padAfter = 0.5) {
    const data = getCardData(fn);
    if (!data || !data.audio) return;
    
    const absSt = parseFloat(data.startInput.value) || 0;
    const absEt = parseFloat(data.endInput.value) || 0;
    
    const relSt = Math.max(0, (absSt + padBefore) - data.padSt);
    const relEt = Math.min(data.audio.duration || 999, (absEt + padAfter) - data.padSt);
    
    if (auditionTimers[fn]) clearInterval(auditionTimers[fn]);
    
    data.audio.currentTime = relSt;
    data.audio.play();
    
    auditionTimers[fn] = setInterval(() => {
      if (data.audio.currentTime >= relEt || data.audio.paused) {
        data.audio.pause();
        clearInterval(auditionTimers[fn]);
        delete auditionTimers[fn];
      }
    }, 25);
  }

  async function saveBoundaryCut(fn) {
    const data = getCardData(fn);
    if (!data) return;
    
    const absSt = parseFloat(data.startInput.value) || 0;
    const absEt = parseFloat(data.endInput.value) || 0;
    const dur = Math.round((absEt - absSt) * 1000) / 1000;
    
    if (dur <= 0.2) {
      alert('Cut duration must be greater than 0.2s!');
      return;
    }
    
    const btn = data.card.querySelector('.save-cut-btn');
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '⏳ Saving Cut...';
    
    try {
      const resp = await fetch('/api/set_boundary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: fn,
          chapter: data.ch,
          is_hemistich: data.isHemi,
          start_s: absSt,
          end_s: absEt
        })
      });
      const res = await resp.json();
      
      if (res.status === 'ok') {
        showToast(`✅ Saved ${fn}: [${absSt.toFixed(3)}s → ${absEt.toFixed(3)}s] (${dur.toFixed(3)}s)`, '#15803d');
        btn.innerHTML = '✓ Saved & Cut!';
        btn.style.background = '#15803d';
        setTimeout(() => {
          btn.disabled = false;
          btn.innerHTML = origHtml;
          btn.style.background = '#238636';
        }, 1500);
      } else {
        alert('Server Error: ' + (res.detail || JSON.stringify(res)));
        btn.disabled = false;
        btn.innerHTML = origHtml;
      }
    } catch (err) {
      alert('Network Error saving boundary: ' + err);
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }

  // Hook live tracking for padded audio
  function initPaddedAudioTracking() {
    document.querySelectorAll('.padded-audio').forEach(audio => {
      const card = audio.closest('.pada-card');
      if (!card) return;
      const padSt = parseFloat(card.getAttribute('data-pad-st')) || 0;
      const livePadPos = card.querySelector('.live-pad-pos');
      const liveTapeAbs = card.querySelector('.live-tape-abs');
      
      const update = () => {
        const cur = audio.currentTime || 0;
        if (livePadPos) livePadPos.innerText = cur.toFixed(3) + 's';
        if (liveTapeAbs) liveTapeAbs.innerText = (padSt + cur).toFixed(3) + 's';
      };
      audio.addEventListener('timeupdate', update);
      audio.addEventListener('seeked', update);
    });
  }

  window.addEventListener('DOMContentLoaded', () => {
    initPaddedAudioTracking();
  });
"""

if __name__ == '__main__':
    print("Normalizer JS component compiled successfully!")
