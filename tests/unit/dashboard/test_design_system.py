"""UI-0 — the design system's hard gate: WCAG AA contrast, computed.

The plan makes AA a REQUIREMENT, not a hope. Every token pair the system
ships (AA_PAIRS) is measured here with the real WCAG relative-luminance
formula — the eye checks nothing, math does. Also: no pure white
anywhere in surfaces (the warm-shell rule), and the CSS is actually
built from tokens (regression against hand-edited escapes).
"""

from __future__ import annotations

from app.presentation.dashboard.nicegui_app.design_system import AA_PAIRS, TOKENS, _build_css


def _lum(hex_color: str) -> float:
    def chan(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    h = hex_color.lstrip("#")
    r, g, b = (chan(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


class TestAaContrast:
    def test_every_shipped_pair_passes_aa(self):
        failures = [
            (fg, bg, contrast(TOKENS["color"][fg], TOKENS["color"][bg]))
            for fg, bg in AA_PAIRS
            if contrast(TOKENS["color"][fg], TOKENS["color"][bg]) < 4.5
        ]
        assert not failures, f"pairs below 4.5:1 → {failures}"

    def test_white_on_teal_button_large_text(self):
        """Buttons are ≥18.66px bold or 24px → 3.0 suffices (AA large)."""
        ratio = contrast("#fffdf6", TOKENS["color"]["teal"])
        assert ratio >= 3.0


class TestWarmShell:
    def test_no_pure_white_surfaces(self):
        surfaces = ("bg", "surface", "surface_alt")
        for name in surfaces:
            assert TOKENS["color"][name].lower() != "#ffffff", name

    def test_status_colors_are_not_the_old_material_reds(self):
        """The old #F44336/#4CAF50 failed AA on cream — the system ships
        darkened semantics; a regression to Material raw fails here."""
        assert TOKENS["color"]["bad"] != "#F44336"
        assert TOKENS["color"]["good"] != "#4CAF50"


class TestCssBuiltFromTokens:
    def test_css_contains_every_color_token(self):
        css = _build_css()
        for name, value in TOKENS["color"].items():
            assert f"--ds-{name}: {value}" in css, name

    def test_css_declares_reduced_motion(self):
        assert "prefers-reduced-motion" in _build_css()

    def test_buttons_are_44px_touch_targets(self):
        assert "min-height: 44px" in _build_css()
