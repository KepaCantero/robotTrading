"""Animated office-floor scene for the Agent Swarm page.

The 10 CAPA 2 components become workers at their desks (flat, friendly
vector people): they breathe and blink while idle, lean in and type while
their step runs, pop a green check when done, and a paper document glides
from desk to desk following the pipeline. Pure SVG + CSS animation driven
by status classes — no canvas loop, buttery and cheap.
"""

from __future__ import annotations

import json
from typing import Callable

from nicegui import ui

from app.presentation.dashboard.nicegui_app.components.agent_card import STEP_TITLES  # noqa: E402
from app.services.agent_swarm.executor import AGENT_SPECS

# ── geometry ──────────────────────────────────────────────────────────────────
# viewBox 1000x420; two rows of five desks, pipeline order left→right.
_ROW_Y = [178, 372]  # desk top-edge y per row
_CX = [112, 300, 488, 676, 864]

SKINS = ["#f2c9a4", "#e8b48c", "#c98d5f", "#f4d3b3", "#a96f44"]
SHIRTS = [
    "#5aa7b8",
    "#7fb98b",
    "#cfa95e",
    "#8fa8c9",
    "#b38fc9",
    "#6fb3a8",
    "#d3a86b",
    "#9db4d0",
    "#c98d8d",
    "#8fc9b0",
]
HAIRS = ["#3a3a3a", "#5b4632", "#1f2937", "#7a5c3e", "#4b5563"]

SHORT = {
    "t11": "Check inputs",
    "t21": "Profile",
    "t31": "Tune modules",
    "t41": "Backtest",
    "t51": "Validate",
    "t61": "Recommend",
    "t71": "Allocate",
    "t81": "Risk",
    "t91": "Report",
    "t101": "Decide",
}


def _worker_group(agent_id: str, index: int, cx: float, desk_y: float) -> str:
    """One worker behind their desk; status classes drive all animation."""
    skin = SKINS[index % len(SKINS)]
    shirt = SHIRTS[index % len(SHIRTS)]
    hair = HAIRS[index % len(HAIRS)]
    delay = (index * 0.37) % 2.4
    # worker sits behind the desk, head above desk level
    head_cy = desk_y - 52
    body_y = desk_y - 34
    return f"""
    <g id="w-{agent_id}" class="worker w-idle"
       style="animation-delay:{delay:.2f}s">
      <!-- chair back -->
      <rect x="{cx - 22}" y="{body_y - 6}" width="44" height="40" rx="10"
            fill="#ded5c2" stroke="#cfc4ac" stroke-width="1.5"/>
      <!-- body -->
      <rect class="body" x="{cx - 17}" y="{body_y}" width="34" height="42" rx="12"
            fill="{shirt}"/>
      <!-- head -->
      <circle class="head" cx="{cx}" cy="{head_cy}" r="13" fill="{skin}"/>
      <path class="hair" d="M {cx - 13} {head_cy - 3} a 13 13 0 0 1 26 0 v -3
               a 13 10 0 0 0 -26 0 z" fill="{hair}"/>
      <g class="face">
        <circle class="eye" cx="{cx - 4.5}" cy="{head_cy}" r="1.6" fill="#4a4536"
                style="animation-delay:{delay:.2f}s"/>
        <circle class="eye" cx="{cx + 4.5}" cy="{head_cy}" r="1.6" fill="#4a4536"
                style="animation-delay:{delay:.2f}s"/>
        <path class="mouth" d="M {cx - 3.5} {head_cy + 5.5} q 3.5 2.4 7 0"
              stroke="#4a4536" stroke-width="1.3" fill="none" stroke-linecap="round"/>
      </g>
      <!-- typing hands (visible while running) -->
      <circle class="hand-l" cx="{cx - 10}" cy="{desk_y - 4}" r="4" fill="{skin}"/>
      <circle class="hand-r" cx="{cx + 10}" cy="{desk_y - 4}" r="4" fill="{skin}"/>
      <!-- coffee (idle) -->
      <g class="coffee" transform="translate({cx + 26}, {desk_y - 10})">
        <rect x="0" y="0" width="9" height="8" rx="1.5" fill="#f5efe6" stroke="#c9b9a4"/>
        <path class="steam s1" d="M 2 -3 q 2 -3 0 -6" stroke="#b9c6d2" fill="none"
              stroke-linecap="round"/>
        <path class="steam s2" d="M 6 -3 q 2 -3 0 -6" stroke="#b9c6d2" fill="none"
              stroke-linecap="round"/>
      </g>
      <!-- status bubbles -->
      <g class="bubble running-bubble" transform="translate({cx + 16}, {head_cy - 22})">
        <circle r="9" fill="#e6f4f0" stroke="#8fd3c8"/>
        <circle class="dotdot d1" cx="-3.5" cy="0" r="1.8" fill="#3f8f85"/>
        <circle class="dotdot d2" cx="0" cy="0" r="1.8" fill="#3f8f85"/>
        <circle class="dotdot d3" cx="3.5" cy="0" r="1.8" fill="#3f8f85"/>
      </g>
      <g class="bubble done-bubble" transform="translate({cx + 16}, {head_cy - 22})">
        <circle r="9" fill="#eef5e7" stroke="#9ecf98"/>
        <path d="M -4 0 l 3 3 l 5 -6" stroke="#5d9c68" stroke-width="2.2" fill="none"
              stroke-linecap="round" stroke-linejoin="round"/>
      </g>
      <g class="bubble failed-bubble" transform="translate({cx + 16}, {head_cy - 22})">
        <circle r="9" fill="#f9ece6" stroke="#dfa38f"/>
        <text y="3.5" text-anchor="middle" font-size="12" font-weight="700"
              fill="#c26b5a">!</text>
      </g>
    </g>
    """


def _desk(spec, cx: float, desk_y: float) -> str:
    return f"""
    <g class="desk">
      <rect x="{cx - 62}" y="{desk_y}" width="124" height="14" rx="4"
            fill="#e6d3b3" stroke="#d6c09a"/>
      <rect x="{cx - 56}" y="{desk_y + 14}" width="8" height="20" fill="#c9b98a"/>
      <rect x="{cx + 48}" y="{desk_y + 14}" width="8" height="20" fill="#c9b98a"/>
      <rect class="monitor" x="{cx - 15}" y="{desk_y - 22}" width="30" height="19" rx="2.5"/>
      <rect class="monitor-foot" x="{cx - 3}" y="{desk_y - 4}" width="6" height="4" fill="#a89e88"/>
      <text x="{cx}" y="{desk_y + 46}" text-anchor="middle" class="desk-label">
        {spec.agent_id.upper().replace("T", "T ", 1)} · {SHORT.get(spec.agent_id, "")}
      </text>
    </g>
    """


def build_office_svg() -> str:
    """Full office-floor SVG for the ten pipeline workers."""
    parts = [
        '<svg id="office-svg" viewBox="0 0 1000 440" '
        'preserveAspectRatio="xMidYMid meet" aria-hidden="true">'
    ]

    # décor: back wall, windows, clock, plants, sign
    parts.append("""
    <defs>
      <linearGradient id="wall-g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#f4eedd"/><stop offset="1" stop-color="#ece2cc"/>
      </linearGradient>
    </defs>
    <rect x="0" y="0" width="1000" height="440" rx="14" fill="url(#wall-g)"/>
    <rect x="0" y="140" width="1000" height="300" fill="#efe6d0"/>
    <line x1="0" y1="140" x2="1000" y2="140" stroke="#ddd2b8" stroke-width="3"/>
    <g class="window"><rect x="70" y="34" width="130" height="66" rx="8" fill="#dfeae2"
        stroke="#b9cfc5"/><line x1="135" y1="34" x2="135" y2="100" stroke="#b9cfc5"/>
        <line x1="70" y1="67" x2="200" y2="67" stroke="#b9cfc5"/>
        <circle class="sun" cx="176" cy="52" r="9" fill="#f3d9a4"/></g>
    <g class="window"><rect x="800" y="34" width="130" height="66" rx="8" fill="#dfeae2"
        stroke="#b9cfc5"/><line x1="865" y1="34" x2="865" y2="100" stroke="#b9cfc5"/>
        <line x1="800" y1="67" x2="930" y2="67" stroke="#b9cfc5"/>
        <circle class="sun" cx="826" cy="52" r="9" fill="#f3d9a4"/></g>
    <g class="clock" transform="translate(500, 62)">
      <circle r="22" fill="#fffdf6" stroke="#cfc4ac" stroke-width="2.5"/>
      <line class="hand-min" x1="0" y1="0" x2="0" y2="-15" stroke="#6f6858"
            stroke-width="2" stroke-linecap="round"/>
      <line class="hand-hour" x1="0" y1="0" x2="8" y2="-6" stroke="#3e3a31"
            stroke-width="2.4" stroke-linecap="round"/>
    </g>
    <text x="500" y="26" text-anchor="middle" class="office-sign">CAPA-2 · TRADING DESK</text>
    <g class="plant" transform="translate(36, 128)">
      <path d="M 0 0 q -12 -18 -4 -34 q 6 14 4 34 z" fill="#8fbf9a"/>
      <path d="M 2 0 q 10 -20 18 -26 q -4 16 -18 26 z" fill="#7fb98b"/>
      <path d="M 0 0 q -4 -22 4 -34 q 2 18 -4 34 z" fill="#a3cba9"/>
      <rect x="-9" y="0" width="22" height="12" rx="3" fill="#c9a279"/>
    </g>
    <g class="plant" transform="translate(964, 128)">
      <path d="M 0 0 q 12 -18 4 -34 q -6 14 -4 34 z" fill="#8fbf9a"/>
      <path d="M -2 0 q -10 -20 -18 -26 q 4 16 18 26 z" fill="#7fb98b"/>
      <path d="M 0 0 q 4 -22 -4 -34 q -2 18 4 34 z" fill="#a3cba9"/>
      <rect x="-13" y="0" width="22" height="12" rx="3" fill="#c9a279"/>
    </g>
    """)

    # desks + workers, pipeline order
    coords: dict[str, tuple[float, float]] = {}
    for index, spec in enumerate(AGENT_SPECS):
        row = 0 if index < 5 else 1
        cx = _CX[index % 5]
        desk_y = _ROW_Y[row]
        coords[spec.agent_id] = (cx, desk_y - 30)
        parts.append(_desk(spec, cx, desk_y))
        parts.append(_worker_group(spec.agent_id, index, cx, desk_y))

    # the travelling document
    parts.append("""
    <g id="office-doc" class="office-doc" opacity="0">
      <rect x="-10" y="-12" width="20" height="25" rx="2" fill="#fffdf6"
            stroke="#cfc4ac" stroke-width="1.5"/>
      <path d="M -5 -6 h 10 M -5 -1 h 10 M -5 4 h 7" stroke="#9db4c9"
            stroke-width="1.4" stroke-linecap="round"/>
      <path d="M 2 -12 l 8 0 l 0 8 z" fill="#f4eedd" stroke="#cfc4ac" stroke-width="1"/>
    </g>
    </svg>
    """)

    return "".join(parts)


_CSS = """
/* ── office scene ─────────────────────────────────────────────────── */
.office-wrap { position: relative; width: 100%; }
#office-svg { width: 100%; height: auto; display: block; }
.desk-label { font-family: 'JetBrains Mono', monospace; font-size: 11px;
  fill: #6f6858; letter-spacing: .04em; }
.office-sign { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 700;
  fill: #948b77; letter-spacing: .25em; }

/* workers: gentle idle breathing (group) */
.worker { animation: worker-breathe 3.4s ease-in-out infinite;
  transform-box: fill-box; transform-origin: center; cursor: pointer; }
@keyframes worker-breathe { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-1.6px); } }
.eye { animation: blink 4.6s infinite; transform-box: fill-box; transform-origin: center; }
@keyframes blink { 0%, 94%, 100% { transform: scaleY(1); } 96% { transform: scaleY(.1); } }

/* idle: coffee steam rises */
.coffee .steam { animation: steam 2.6s ease-in-out infinite; opacity: 0; }
.coffee .steam.s2 { animation-delay: 1.2s; }
@keyframes steam { 0% { opacity: 0; transform: translateY(0); }
  35% { opacity: .9; } 100% { opacity: 0; transform: translateY(-5px); } }

/* default: hide status-specific bits */
.worker .hand-l, .worker .hand-r { opacity: 0; }
.worker .bubble { opacity: 0; }
.worker .monitor { fill: #d0c9b8; stroke: #b8b09c; stroke-width: 1.5;
  transition: fill .3s ease; }
.worker .mouth { transition: d .3s ease; }
.coffee { opacity: 0; transition: opacity .4s; }

/* idle */
.worker.w-idle .coffee { opacity: 1; }

/* running: lean in, type, teal screen, thinking dots */
.worker.w-running { animation: worker-type .5s ease-in-out infinite; }
@keyframes worker-type { 0%,100% { transform: translateY(0) }
  50% { transform: translateY(-.7px) } }
.worker.w-running .hand-l { opacity: 1; animation: hand-l .28s ease-in-out infinite; }
.worker.w-running .hand-r { opacity: 1; animation: hand-r .28s ease-in-out infinite; }
@keyframes hand-l { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-2.4px); } }
@keyframes hand-r { 0%,100% { transform: translateY(-2.4px); } 50% { transform: translateY(0); } }
.worker.w-running .monitor { fill: #a5dcd2; stroke: #6cbfb2; }
.worker.w-running .running-bubble { opacity: 1; }
.worker .dotdot { animation: dot-bounce 1s ease-in-out infinite; }
.worker .dotdot.d2 { animation-delay: .16s; }
.worker .dotdot.d3 { animation-delay: .32s; }
@keyframes dot-bounce { 0%,100% { transform: translateY(0); } 40% { transform: translateY(-3px); } }

/* done: green screen, pop check, relaxed */
.worker.w-done .monitor { fill: #bfe3b4; stroke: #8fca8a; }
.worker.w-done .done-bubble { opacity: 1; animation: bubble-pop .5s
  cubic-bezier(.2,2,.4,1); }
@keyframes bubble-pop { 0% { transform: scale(.2); opacity: 0; }
  70% { transform: scale(1.15); } 100% { transform: scale(1); opacity: 1; } }

/* failed: red screen + alert */
.worker.w-failed .monitor { fill: #f0c9bd; stroke: #d89a8a; }
.worker.w-failed .failed-bubble { opacity: 1; animation: bubble-shake .5s ease; }
@keyframes bubble-shake { 0%,100% { transform: translateX(0); }
  25% { transform: translateX(-2.5px); } 75% { transform: translateX(2.5px); } }

/* skipped */
.worker.w-skipped { opacity: .35; filter: grayscale(.7); }

/* travelling document */
.office-doc { transition: transform .55s cubic-bezier(.3,.9,.35,1), opacity .3s;
  transform-box: fill-box; }
.office-doc.moving { animation: doc-wobble .8s ease-in-out infinite; }
@keyframes doc-wobble { 0%,100% { rotate: -4deg; } 50% { rotate: 5deg; } }

/* décor motion */
.clock .hand-min { animation: spin 60s linear infinite; transform-box: fill-box;
  transform-origin: center; }
.clock .hand-hour { animation: spin 720s linear infinite; transform-box: fill-box;
  transform-origin: center; }
@keyframes spin { to { transform: rotate(360deg); } }
.sun { animation: sun-glow 6s ease-in-out infinite; }
@keyframes sun-glow { 0%,100% { opacity: .7; } 50% { opacity: 1; } }
.plant { animation: plant-sway 7s ease-in-out infinite; transform-box: fill-box;
  transform-origin: bottom center; }
@keyframes plant-sway { 0%,100% { transform: rotate(-2deg); } 50% { transform: rotate(2.4deg); } }

/* invisible hit-areas over desks */
.desk-hit { position: absolute; border: 0; background: transparent; cursor: pointer;
  border-radius: 10px; }
.desk-hit:hover { background: rgba(95,143,133,.08); }
"""

_JS_TEMPLATE = """
window.swarmOffice = (function () {{
  const POS = {positions_json};
  const docEl = () => document.getElementById('office-doc');
  function setState(statuses, activeId) {{
    for (const [id, status] of Object.entries(statuses)) {{
      const el = document.getElementById('w-' + id);
      if (!el) continue;
      el.setAttribute('class', 'worker w-' + status.toLowerCase());
    }}
    const doc = docEl();
    if (!doc) return;
    if (activeId && POS[activeId]) {{
      const [x, y] = POS[activeId];
      doc.setAttribute('transform', `translate(${{x}}, ${{y}})`);
      doc.setAttribute('opacity', '1');
      doc.classList.add('moving');
    }} else {{
      doc.setAttribute('opacity', '0');
      doc.classList.remove('moving');
    }}
  }}
  return {{ setState }};
}})();
"""


class OfficeScene:
    """SVG office floor + clickable overlays, driven by :meth:`update`."""

    def __init__(self, on_click: Callable[[str], None]) -> None:
        ui.add_css(_CSS)

        coords: dict[str, tuple[float, float]] = {}
        for index, spec in enumerate(AGENT_SPECS):
            row = 0 if index < 5 else 1
            coords[spec.agent_id] = (_CX[index % 5], _ROW_Y[row] - 30)
        positions_json = json.dumps(coords)

        with ui.element("div").classes("office-wrap") as wrap:
            self.wrap = wrap
            ui.html(build_office_svg())
            for index, spec in enumerate(AGENT_SPECS):
                row = 0 if index < 5 else 1
                cx = _CX[index % 5]
                desk_y = _ROW_Y[row]
                left = (cx - 70) / 1000 * 100
                top = (desk_y - 92) / 440 * 100
                width = 140 / 1000 * 100
                height = 150 / 440 * 100
                title, _ = STEP_TITLES.get(spec.agent_id, (spec.name, ""))
                (
                    ui.button(on_click=lambda _, aid=spec.agent_id: on_click(aid))
                    .props(f'aria-label="Open step {index}: {title}"')
                    .classes("desk-hit")
                    .style(
                        f"left:{left:.2f}%; top:{top:.2f}%; "
                        f"width:{width:.2f}%; height:{height:.2f}%"
                    )
                    .mark(f"office_desk_{spec.agent_id}")
                    .props("flat unelevated")
                )

        ui.add_body_html(f"<script>{_JS_TEMPLATE.format(positions_json=positions_json)}</script>")

    def update(self, states: dict) -> None:
        """Push statuses + active worker to the scene (client-side)."""
        statuses = {
            spec.agent_id: getattr(states.get(spec.agent_id), "status", "IDLE")
            for spec in AGENT_SPECS
        }
        active = next(
            (spec.agent_id for spec in AGENT_SPECS if statuses[spec.agent_id] == "RUNNING"),
            None,
        )
        try:
            ui.run_javascript(f"swarmOffice.setState({json.dumps(statuses)}, {json.dumps(active)})")
        except Exception:  # noqa: BLE001 - scene must never break the page
            pass
