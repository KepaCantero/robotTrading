"""UI-0 — Design system: the single visual language of the product.

The tokens are not aspirational: they codify the palette the pages
already speak (cream shell #fffdf6, warm ink #3e3a31, sage #b9cfc5,
teal #3f8f85, honey #f3d9a4) so every NEW page is built from the same
author. Two hard rules from the plan: NO pure white backgrounds, and
WCAG AA contrast on every token pair we ship (checked by TEST, not by
eye: tests/unit/dashboard/test_design_system.py).

Usage — pages compose ONLY these:

    from app.presentation.dashboard.nicegui_app.design_system as ds

    with ds.card(title="Honest numbers"):
        ds.honest_number("+114.9%", "18-year total return")
        ds.validation_badge("fees")
    ds.button("Validate it", on_click=...)
    ds.eli5_tooltip(term="Drawdown", plain="How far it fell from its
        highest point before recovering. Bigger (more negative) = a
        scarier ride.")

The /design page renders the full kit — it is the acceptance demo.
"""

from __future__ import annotations

from typing import Any, Callable

from nicegui import ui

# ═══════════════════════════════════════════════════════════════════
# TOKENS — the only place colors/sizes live
# ═══════════════════════════════════════════════════════════════════

TOKENS: dict[str, Any] = {
    "color": {
        # surfaces (never pure white)
        "bg": "#fffdf6",  # cream shell
        "surface": "#f9f5ec",  # raised card tint
        "surface_alt": "#f4eedd",  # inset / secondary card
        # ink
        "text": "#3e3a31",  # primary warm ink
        "text_soft": "#6f6858",  # secondary text (AA on bg)
        "line": "#e2d9c8",  # hairlines / borders
        # brand (learning-app warm)
        "sage": "#b9cfc5",
        "teal": "#3f8f85",  # primary action
        "teal_deep": "#2e6b63",  # links / strong accents
        "honey": "#f3d9a4",  # highlight fills
        "honey_deep": "#6d5510",  # AA-measured 5.1:1 on honey
        # semantics (darkened to keep AA on cream — status colors from
        # the old theme failed contrast; these don't)
        "good": "#2e7d4f",
        "good_tint": "#eef5e7",
        "bad": "#b3402f",
        "bad_tint": "#f9ece6",
        "warn": "#8a5f0c",  # AA-measured 4.98:1 on warn_tint
        "warn_tint": "#faf0d7",
    },
    "type": {
        "font": "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
        "display": ("34px", "700"),
        "h1": ("24px", "700"),
        "h2": ("18px", "600"),
        "body": ("15px", "400"),
        "small": ("13px", "400"),
        "caption": ("11.5px", "500"),
    },
    "space": {"xs": 4, "s": 8, "m": 16, "l": 24, "xl": 32, "xxl": 48},
    "radius": {"s": 8, "m": 12, "l": 16},
    "shadow": "0 2px 10px rgba(62,58,49,0.08), 0 1px 3px rgba(62,58,49,0.06)",
    "motion": "160ms ease",
}

#: WCAG pairs that MUST hold — enforced by test (ratio, [pairs])
AA_PAIRS: list[tuple[str, str]] = [
    ("text", "bg"),
    ("text", "surface"),
    ("text", "surface_alt"),
    ("text_soft", "bg"),
    ("teal_deep", "bg"),
    ("good", "good_tint"),
    ("bad", "bad_tint"),
    ("warn", "warn_tint"),
    ("honey_deep", "honey"),
]

# ═══════════════════════════════════════════════════════════════════
# CSS — custom properties + component classes (built ONLY from TOKENS)
# ═══════════════════════════════════════════════════════════════════


def _build_css() -> str:
    c, t, s, r = TOKENS["color"], TOKENS["type"], TOKENS["space"], TOKENS["radius"]
    roots = "\n".join(f"  --ds-{k}: {v};" for k, v in c.items())
    sizes = "\n".join(f"  --ds-{k}-size: {v[0]}; --ds-{k}-weight: {v[1]};" for k, v in t.items())
    spaces = "\n".join(f"  --ds-space-{k}: {v}px;" for k, v in s.items())
    return f"""
:root {{
{roots}
{sizes}
{spaces}
  --ds-radius-s: {r["s"]}px; --ds-radius-m: {r["m"]}px; --ds-radius-l: {r["l"]}px;
  --ds-shadow: {TOKENS["shadow"]};
  --ds-motion: {TOKENS["motion"]};
  --ds-font: {t["font"]};
}}
.ds-card {{
  background: var(--ds-surface); border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-m); box-shadow: var(--ds-shadow);
  padding: var(--ds-space-l); transition: box-shadow var(--ds-motion);
}}
.ds-card--alt {{ background: var(--ds-surface_alt); }}
.ds-card__title {{
  font-size: var(--ds-h2-size); font-weight: var(--ds-h2-weight);
  color: var(--ds-text); margin: 0 0 var(--ds-space-m);
}}
.ds-btn {{
  border-radius: var(--ds-radius-s); font-weight: 600; font-size: var(--ds-body-size);
  padding: 10px var(--ds-space-l); border: 1px solid transparent;
  cursor: pointer; transition: filter var(--ds-motion), transform var(--ds-motion);
  min-height: 44px; display: inline-flex; align-items: center; gap: var(--ds-s);
}}
.ds-btn--primary {{ background: var(--ds-teal); color: #fffdf6; }}
.ds-btn--primary:hover {{ filter: brightness(0.92); }}
.ds-btn--secondary {{ background: transparent; color: var(--ds-teal_deep); border-color: var(--ds-teal); }}
.ds-btn--secondary:hover {{ background: rgba(63,143,133,0.08); }}
.ds-skeleton {{
  background: linear-gradient(90deg, var(--ds-surface_alt) 25%, #ece3cf 50%, var(--ds-surface_alt) 75%);
  background-size: 200% 100%; animation: ds-shimmer 1.4s infinite;
  border-radius: var(--ds-radius-s); color: transparent; user-select: none;
}}
@keyframes ds-shimmer {{ 0% {{ background-position: 200% 0; }} 100% {{ background-position: -200% 0; }} }}
.ds-state {{ border: 1px dashed var(--ds-line); border-radius: var(--ds-radius-m);
  padding: var(--ds-space-xl); text-align: center; color: var(--ds-text_soft); }}
.ds-state__icon {{ font-size: 34px; margin-bottom: var(--ds-s); }}
.ds-state--error {{ border-color: var(--ds-bad); background: var(--ds-bad_tint); color: var(--ds-bad); }}
.ds-badge {{
  display: inline-flex; align-items: center; gap: 6px;
  font-size: var(--ds-caption-size); font-weight: var(--ds-caption-weight);
  padding: 4px 10px; border-radius: 999px; background: var(--ds-good_tint); color: var(--ds-good);
}}
.ds-badge--info {{ background: var(--ds-honey); color: var(--ds-honey_deep); }}
.ds-badge--warn {{ background: var(--ds-warn_tint); color: var(--ds-warn); }}
.ds-num {{ font-size: var(--ds-display-size); font-weight: var(--ds-display-weight);
  color: var(--ds-text); line-height: 1.1; }}
.ds-num__label {{ font-size: var(--ds-small-size); color: var(--ds-text_soft); margin-top: var(--ds-xs); }}
.ds-tip {{
  background: var(--ds-text); color: var(--ds-bg); font-size: var(--ds-small-size);
  border-radius: var(--ds-radius-s); padding: var(--ds-s) var(--ds-m);
  max-width: 280px; white-space: normal; line-height: 1.45;
}}
@media (prefers-reduced-motion: reduce) {{
  .ds-skeleton {{ animation: none; }} .ds-btn {{ transition: none; }}
}}
"""


def inject() -> None:
    """Add the design-system stylesheet to the current page (call per page)."""
    ui.add_head_html(f"<style>{_build_css()}</style>")


# ═══════════════════════════════════════════════════════════════════
# COMPONENTS — pages build ONLY from these
# ═══════════════════════════════════════════════════════════════════


def card(title: str | None = None, alt: bool = False) -> ui.element:
    """Standard surface. `with card(title=...): ...`"""
    c = ui.element("div").classes("ds-card" + (" ds-card--alt" if alt else ""))
    if title:
        with c:
            _txt_div("ds-card__title", title)
    return c


def button(label: str, on_click: Callable | None = None, primary: bool = True) -> ui.button:
    b = (
        ui.button(label, on_click=on_click)
        .classes("ds-btn " + ("ds-btn--primary" if primary else "ds-btn--secondary"))
        .props("no-caps unelevated outline" if not primary else "no-caps unelevated")
    )
    return b


def skeleton(width: str = "100%", height: str = "18px") -> ui.element:
    return ui.element("div").classes("ds-skeleton").style(f"width:{width};height:{height}")


def empty_state(message: str, icon: str = "🌾") -> ui.element:
    with ui.element("div").classes("ds-state") as e:
        _txt_div("ds-state__icon", icon)
        ui.label(message)
    return e


def error_state(message: str, hint: str | None = None) -> ui.element:
    with ui.element("div").classes("ds-state ds-state--error") as e:
        _txt_div("ds-state__icon", "⚠️")
        _txt_div_styled("font-weight:600", message)
        if hint:
            _txt_div_styled("font-size:var(--ds-small-size)", hint)
    return e


def honest_number(value: str, label: str) -> ui.element:
    with ui.element("div") as e:
        _txt_div("ds-num", value)
        _txt_div("ds-num__label", label)
    return e


def validation_badge(kind: str, text: str | None = None) -> ui.element:
    """Trust badges: fees / walk_forward / paper / taxes."""
    presets = {
        "fees": ("Fees included ✓", "good"),
        "walk_forward": ("Walk-forward 5/5 ✓", "good"),
        "paper": ("Verified on paper ✓", "good"),
        "taxes": ("Spain tax rules ✓", "info"),
        "partial": ("Partial data — shown honestly", "warn"),
    }
    label = text or presets.get(kind, (kind, "info"))[0]
    tone = presets.get(kind, (None, "info"))[1]
    cls = "ds-badge" if tone == "good" else f"ds-badge ds-badge--{tone}"
    return ui.label(label).classes(cls)


def eli5_tooltip(anchor: ui.element, term: str, plain: str) -> ui.element:
    """Attach a plain-English tooltip to any element (0 jargon rule)."""
    t = anchor.tooltip(f"{term} — {plain}")
    t.classes("ds-tip")
    return t


def section_heading(text: str, caption: str | None = None) -> ui.element:
    with ui.element("div").style("margin-bottom:var(--ds-space-m)") as e:
        ui.label(text).style(
            "font-size:var(--ds-h1-size);font-weight:var(--ds-h1-weight);color:var(--ds-text)"
        )
        if caption:
            ui.label(caption).style("font-size:var(--ds-small-size);color:var(--ds-text_soft)")
    return e


# NiceGUI 3 helpers: ui.element has no .text() — small shims so the
# component code above stays declarative.
def _txt_div(classes: str, text: str) -> ui.label:
    return ui.label(text).classes(classes)


def _txt_span(classes: str, text: str) -> ui.label:
    return ui.label(text).classes(classes)


def _txt_div_styled(style: str, text: str) -> ui.label:
    return ui.label(text).style(style)


# ═══════════════════════════════════════════════════════════════════
# UI-6 — plain-English glossary (the 0-jargon rule, data-backed)
# ═══════════════════════════════════════════════════════════════════

#: every financial term a novice meets on these pages, explained once,
#: in one breath. The /glossary page renders it whole; eli5_tooltip and
#: term() attach the same text where the word appears.
GLOSSARY: dict[str, str] = {
    "Portfolio": "All your investments together, like one basket you carry.",
    "ETF": "A single ticker that holds many companies at once — instant diversity.",
    "Dividend": "Cash a company pays you regularly, just for owning its shares.",
    "Backtest": "Replaying the past with today's plan to see how it would have done.",
    "Fees": "What trading costs — always included in our numbers, never hidden.",
    "Walk-forward": "Testing on stretches of time the plan never saw while learning.",
    "Drawdown": "How far it fell from its highest point before recovering.",
    "Worst fall": "The biggest drop your portfolio ever took in the data we tested.",
    "Rebalance": "Selling a bit of what grew too much to buy what lagged — back to plan.",
    "Drift": "How far your real portfolio has wandered from its target weights.",
    "Paper trading": "Real prices, real rules, imaginary money — the dress rehearsal.",
    "Live trading": "The same robot moving real euros. Off by design for now.",
    "Sharpe ratio": "Return per unit of bumps — higher means a smoother ride.",
    "Optimize": "Quietly trying many settings in the past to pick sensible ones.",
    "Equal-weight": "Every position the same size — the honest baseline we must beat.",
    "Tax preview": "What selling would cost you in Spanish taxes, shown BEFORE you confirm.",
}


def term(label_text: str, key: str | None = None) -> ui.label:
    """A term with its glossary tooltip attached — the word and its
    explanation can never drift apart."""
    key = (key or label_text).strip()
    plain = GLOSSARY.get(key) or next(
        (v for k, v in GLOSSARY.items() if k.lower() == key.lower()), ""
    )
    element = ui.label(label_text)
    if plain:
        element.classes("underline decoration-dotted cursor-help").style(
            "color:var(--ds-teal_deep)"
        )
        eli5_tooltip(element, key, plain)
    return element
