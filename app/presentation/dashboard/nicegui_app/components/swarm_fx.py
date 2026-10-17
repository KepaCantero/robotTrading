"""Light, calm theme for the Agent Swarm page.

Popular/official pattern for finance configuration tools (Stripe/Google
style): soft gray canvas, white cards, one teal accent, green/amber/red
reserved exclusively for status. Plain language, progressive disclosure,
quiet motion. Also ships an optional muted sound-cue synth (off by
default).
"""

from __future__ import annotations

from nicegui import ui

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #f8f4ea;      /* warm cream canvas  */
  --card: #fffdf6;    /* warm card          */
  --line: #e7dfcc;
  --line-hi: #d8cdb4;
  --tx: #3e3a31;
  --tx2: #6f6858;
  --tx3: #948b77;
  --run: #2e7d74;     /* soft teal — running (AA on cream) */
  --ok: #3e7d4f;      /* sage      — done (AA)              */
  --warn: #93672a;    /* honey     — warnings (AA)          */
  --bad: #ab4f3f;     /* terracotta — failure (AA)          */
  --accent: #557f63;
  --tint-run: #e8f3ee;
  --tint-ok: #eef5e7;
  --tint-bad: #f9ece6;
}

/* The swarm page fills the content area edge-to-edge with warm cream. */
.light-sheet {
  padding: 22px 24px 28px 24px;
  min-height: calc(100vh - 90px);
  font-family: 'Inter', 'Segoe UI', sans-serif;
  color: var(--tx);
}

.panel {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
}

.page-title { font-size: 1.5rem; font-weight: 700; color: var(--tx); margin: 0; }
.page-sub { color: var(--tx2); font-size: .95rem; margin-top: 2px; }

.lbl {
  font-size: 11px; font-weight: 600; letter-spacing: .1em;
  text-transform: uppercase; color: var(--tx3);
}
.help { font-size: 12.5px; color: var(--tx2); line-height: 1.4; }

.hotkey-hint {
  font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: var(--tx3);
  border: 1px solid var(--line); border-radius: 6px; padding: 4px 10px;
  white-space: nowrap; background: var(--card);
}

/* ── status chip (global run state) ───────────────────────────────── */
.state-chip {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 600; padding: 6px 14px; border-radius: 999px;
  border: 1px solid var(--line); color: var(--tx2); background: var(--card);
}
.state-chip .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--tx3); }
.state-chip.running { color: var(--run); border-color: color-mix(in srgb, var(--run) 32%, var(--card)); background: var(--tint-run); }
.state-chip.running .dot { background: var(--run); animation: dot-pulse 1.2s ease-in-out infinite; }
.state-chip.done { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 30%, var(--card)); background: var(--tint-ok); }
.state-chip.done .dot { background: var(--ok); }
.state-chip.bad { color: var(--bad); border-color: color-mix(in srgb, var(--bad) 32%, var(--card)); background: var(--tint-bad); }
.state-chip.bad .dot { background: var(--bad); }
@keyframes dot-pulse { 0%,100% { opacity: .35; } 50% { opacity: 1; } }

/* progress bar */
.prog-track { height: 8px; border-radius: 999px; background: #ece5d3; overflow: hidden; }
.prog-fill { height: 100%; width: 0%; border-radius: 999px;
  background: var(--run); transition: width .5s cubic-bezier(.2,.8,.3,1); }
.prog-fill.full { background: var(--ok); }

/* ── pipeline steps ───────────────────────────────────────────────── */
.pstep {
  display: flex; gap: 12px; align-items: flex-start;
  padding: 9px 12px; border-radius: 10px; border: 1px solid transparent;
  cursor: pointer; transition: background .2s ease, border-color .2s ease;
}
.pstep:hover { background: #f6f1e4; border-color: var(--line); }
.pstep.running { background: var(--tint-run); border-color: color-mix(in srgb, var(--run) 30%, var(--card)); }
.pstep.done { background: var(--tint-ok); }
.pstep.failed { background: var(--tint-bad); }
.pstep.skipped { opacity: .45; }

.pnum {
  width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600; background: #eef2f7; color: var(--tx2);
  transition: all .3s ease;
}
.pstep.running .pnum { background: var(--run); color: #fff; }
.pstep.done .pnum { background: var(--ok); color: #fff; }
.pstep.failed .pnum { background: var(--bad); color: #fff; }

.pstep-name { font-size: 14px; font-weight: 600; color: var(--tx); line-height: 1.25; }
.pstep-desc { font-size: 12px; color: var(--tx2); line-height: 1.35; }
.pstep-meta { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--tx3);
  margin-left: auto; flex-shrink: 0; padding-top: 2px; }
.pstep-meta.ok { color: var(--ok); }
.pstep-meta.bad { color: var(--bad); }

/* ── result card ──────────────────────────────────────────────────── */
.verdict {
  font-size: 22px; font-weight: 700; letter-spacing: .02em;
  padding: 10px 22px; border-radius: 12px; display: inline-block;
  animation: verdict-in .3s ease;
}
.verdict.ok  { color: var(--ok);  background: var(--tint-ok);  border: 1px solid color-mix(in srgb, var(--ok) 35%, var(--card)); }
.verdict.mid { color: var(--warn); background: #f7efdd; border: 1px solid color-mix(in srgb, var(--warn) 35%, var(--card)); }
.verdict.bad { color: var(--bad); background: var(--tint-bad); border: 1px solid color-mix(in srgb, var(--bad) 35%, var(--card)); }
@keyframes verdict-in { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; } }

.metric-tile { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; }
.metric-tile .k { font-size: 11px; color: var(--tx3); font-weight: 600; }
.metric-tile .v { font-size: 18px; font-weight: 700; color: var(--tx); margin-top: 2px; }

/* ── execution log (technical detail) ─────────────────────────────── */
.term-line { font-family: 'JetBrains Mono', monospace; font-size: 11.5px;
  line-height: 1.55; white-space: normal; }
.term-ts { color: var(--tx3); }
.term-info { color: var(--tx2); }
.term-good { color: var(--ok); }
.term-warn { color: var(--warn); }
.term-bad  { color: var(--bad); }
.term-neutral { color: var(--tx2); }
.term-caret::after { content: '▍'; animation: caret 1.1s step-end infinite; color: var(--run); }
@keyframes caret { 50% { opacity: 0; } }

/* The dashboard shell is dark; while the swarm page is mounted, the whole
   chrome goes light seamlessly (:has() un-applies automatically on leave). */
body:has(.light-sheet) { background: var(--bg); }
body:has(.light-sheet) .q-page,
body:has(.light-sheet) .q-page-container { background: var(--bg) !important; }
body:has(.light-sheet) .q-header {
  background: #efe8d7 !important;
  border-bottom: 1px solid var(--line);
}
body:has(.light-sheet) .q-header .text-h6 { color: var(--tx); }
body:has(.light-sheet) .q-header .text-caption { color: var(--tx2); }
body:has(.light-sheet) .q-drawer {
  background: #f3eee1 !important;
  border-right: 1px solid var(--line) !important;
}
body:has(.light-sheet) .q-drawer .text-h5 { color: var(--tx); }
body:has(.light-sheet) .q-drawer .text-white { color: var(--tx2) !important; }
body:has(.light-sheet) .q-drawer .text-white:hover { color: var(--run); }
body:has(.light-sheet) .q-separator { background: var(--line); }

/* ── ambient light blobs (calm, slow) ─────────────────────────────── */
.light-sheet {
  position: relative; overflow: hidden;
  background: transparent; border-radius: 0;
}
.blob { position: absolute; border-radius: 50%; filter: blur(70px);
  pointer-events: none; opacity: .5; z-index: 0; }
.blob-a { width: 420px; height: 420px; top: -140px; right: -80px;
  background: radial-gradient(circle, rgba(95,143,133,.14), transparent 65%);
  animation: blob-drift-a 26s ease-in-out infinite alternate; }
.blob-b { width: 360px; height: 360px; bottom: -120px; left: -100px;
  background: radial-gradient(circle, rgba(128,163,120,.11), transparent 65%);
  animation: blob-drift-b 32s ease-in-out infinite alternate; }
.blob-c { width: 300px; height: 300px; top: 40%; left: 55%;
  background: radial-gradient(circle, rgba(194,145,63,.08), transparent 65%);
  animation: blob-drift-a 40s ease-in-out infinite alternate-reverse; }
@keyframes blob-drift-a { from { transform: translate(0,0) scale(1); } to { transform: translate(-60px, 50px) scale(1.15); } }
@keyframes blob-drift-b { from { transform: translate(0,0) scale(1); } to { transform: translate(70px, -40px) scale(1.1); } }
.light-sheet > *:not(.blob) { position: relative; z-index: 1; }

/* ── motion upgrades ──────────────────────────────────────────────── */
.pstep.running .pnum { animation: pnum-ripple 1.6s ease-out infinite; }
@keyframes pnum-ripple {
  0%   { box-shadow: 0 0 0 0 rgba(95,143,133,.35); }
  70%  { box-shadow: 0 0 0 12px rgba(95,143,133,0); }
  100% { box-shadow: 0 0 0 0 rgba(95,143,133,0); }
}
.pstep.done .pnum { animation: pnum-pop .45s cubic-bezier(.2,2,.4,1); }
@keyframes pnum-pop { 0% { transform: scale(.6); } 60% { transform: scale(1.18); } 100% { transform: scale(1); } }
.pstep.failed .pnum { animation: pnum-shake .4s ease; }
@keyframes pnum-shake { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-3px)} 75%{transform:translateX(3px)} }
.pstep { animation: step-in .35s ease both; }
@keyframes step-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

.prog-fill { position: relative; overflow: hidden; }
.prog-fill::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.45), transparent);
  background-size: 50% 100%; animation: prog-shimmer 1.8s linear infinite;
}
@keyframes prog-shimmer { from { background-position: -150% 0; } to { background-position: 250% 0; } }

.metric-tile { animation: tile-in .5s ease both; }
@keyframes tile-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

.run-btn {
  background: linear-gradient(135deg, #6aa17b, #4f8a72) !important;
  font-weight: 600; letter-spacing: .03em;
  transition: transform .15s ease, box-shadow .2s ease !important;
  box-shadow: 0 2px 8px rgba(106,161,123,.28);
}
.run-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(106,161,123,.38); }
.run-btn:disabled { transform: none; box-shadow: none; }

/* ── accessibility: visible focus + reduced motion ────────────────── */
.light-sheet :focus-visible,
.q-drawer :focus-visible,
.q-header :focus-visible {
  outline: 2px solid var(--run);
  outline-offset: 2px;
  border-radius: 6px;
}
.doc-tile:focus-visible, .desk-hit:focus-visible, .pnode:focus-visible {
  outline: 2px solid var(--run);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* ── docs & help tiles ────────────────────────────────────────────── */
.doc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.doc-tile {
  display: flex; flex-direction: column; gap: 2px;
  padding: 10px 12px; border: 1px solid var(--line); border-radius: 10px;
  background: var(--card); text-decoration: none;
  transition: transform .15s ease, border-color .2s, box-shadow .2s;
}
.doc-tile:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
  box-shadow: 0 4px 12px rgba(106, 161, 123, .16);
}
.doc-tile .dt-icon { font-size: 18px; line-height: 1; }
.doc-tile .dt-name { font-size: 13px; font-weight: 600; color: var(--tx); }
.doc-tile .dt-sub { font-size: 11px; color: var(--tx3); }

/* ── step track (replaces the list) ───────────────────────────────── */
.now-panel {
  border: 1px solid var(--line); border-radius: 10px;
  background: var(--card); padding: 10px 14px;
  transition: border-color .3s ease, background .3s ease;
}
.now-panel[data-state="running"] { border-color: color-mix(in srgb, var(--run) 35%, var(--line)); background: var(--tint-run); }
.now-panel[data-state="done"]    { border-color: color-mix(in srgb, var(--ok) 32%, var(--line)); background: var(--tint-ok); }
.now-panel[data-state="bad"]     { border-color: color-mix(in srgb, var(--bad) 35%, var(--line)); background: var(--tint-bad); }
.now-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--tx3); flex-shrink: 0; }
.now-panel[data-state="running"] .now-dot { background: var(--run); animation: dot-pulse 1.2s ease-in-out infinite; }
.now-panel[data-state="done"] .now-dot { background: var(--ok); }
.now-panel[data-state="bad"] .now-dot { background: var(--bad); }
.now-title { font-size: 15px; font-weight: 600; color: var(--tx); line-height: 1.3; }

.track-wrap { overflow-x: auto; padding: 6px 2px 2px 2px; }
.track-row { gap: 0; min-width: 560px; }
.pnode {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border: 2px solid var(--line-hi); background: var(--card);
  cursor: pointer; position: relative;
  transition: border-color .3s ease, background .3s ease, transform .15s ease;
}
.pnode:hover { transform: scale(1.12); }
.pnode-num {
  font-family: 'JetBrains Mono', monospace; font-size: 12.5px; font-weight: 500;
  color: var(--tx2);
}
.pnode.n-done { border-color: var(--ok); background: var(--ok); }
.pnode.n-done .pnode-num { color: #fffdf6; }
.pnode.n-running { border-color: var(--run); background: var(--card);
  animation: node-pulse 1.6s ease-out infinite; }
.pnode.n-running .pnode-num { color: var(--run); font-weight: 700; }
@keyframes node-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(95,143,133,.35); }
  70%  { box-shadow: 0 0 0 10px rgba(95,143,133,0); }
  100% { box-shadow: 0 0 0 0 rgba(95,143,133,0); }
}
.pnode.n-failed { border-color: var(--bad); background: var(--bad); }
.pnode.n-failed .pnode-num { color: #fffdf6; }
.pnode.n-skipped { opacity: .4; }

.t-connector { flex: 1 1 0; height: 3px; border-radius: 2px; background: var(--line);
  transition: background .45s ease; min-width: 14px; }
.t-connector.filled { background: var(--ok); }

.swarm-json {
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; line-height: 1.5;
  white-space: pre-wrap; word-break: break-word;
  color: #4a4536; background: #f4eeda;
  border: 1px solid var(--line); border-radius: 8px;
  padding: 12px; margin: 0; max-height: 420px; overflow: auto;
}
"""

JS = r"""
window.swarmFX = (function () {
  let audioOn = false, actx = null;

  function ensureAudio() {
    if (!actx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) actx = new AC();
    }
    if (actx && actx.state === 'suspended') actx.resume();
    return actx;
  }
  function tone(freq, dur, type, vol, when) {
    if (!audioOn) return;
    const context = ensureAudio(); if (!context) return;
    const t0 = context.currentTime + (when || 0);
    const o = context.createOscillator(), g = context.createGain();
    o.type = type || 'sine'; o.frequency.setValueAtTime(freq, t0);
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(vol || 0.03, t0 + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    o.connect(g); g.connect(context.destination);
    o.start(t0); o.stop(t0 + dur + 0.05);
  }
  const sounds = {
    start()  { tone(392, 0.16, 'sine', 0.03); tone(523, 0.2, 'sine', 0.025, 0.08); },
    stage()  { tone(523, 0.06, 'sine', 0.018); },
    complete()  { [523, 659, 784].forEach((f, k) => tone(f, 0.22, 'sine', 0.028, k * 0.11)); },
    fail()   { tone(196, 0.28, 'sine', 0.03); tone(147, 0.34, 'sine', 0.025, 0.1); },
    tick()   { tone(700, 0.03, 'sine', 0.01); },
  };

  return {
    sounds,
    setAudio(on) { audioOn = !!on; if (on) ensureAudio(); },
    get audioOn() { return audioOn; },
  };
})();
"""


def install() -> None:
    """Inject the light theme + optional audio cues."""
    ui.add_css(CSS)
    ui.add_body_html(f"<script>{JS}</script>")
