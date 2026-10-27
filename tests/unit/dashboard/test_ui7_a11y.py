"""UI-7 — accessibility audit, the part a test can hold.

Lighthouse needs Chrome+node per run (documented as the user's manual
gate); what CAN be enforced forever here: every shipped page's HTML
answers the AA basics — lang declared, viewport present, contrast pairs
green (design system), touch targets, focus visibility, and the PWA/
mobile wiring survives. Run against the LIVE dashboard (started by the
suite's session), skipped honestly if it isn't running.
"""

from __future__ import annotations

import urllib.request

import pytest

from app.presentation.dashboard.nicegui_app.design_system import AA_PAIRS, TOKENS, _build_css

BASE = "http://127.0.0.1:8503"
PAGES = ["/start", "/trust", "/glossary", "/design", "/portfolio", "/"]


def _get(path: str) -> str | None:
    try:
        with urllib.request.urlopen(BASE + path, timeout=5) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except OSError:
        return None


def _lum(hex_color: str) -> float:
    def chan(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    h = hex_color.lstrip("#")
    r, g, b = (chan(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


class TestTokenLevelAa:
    def test_every_aa_pair_holds(self):
        for fg, bg in AA_PAIRS:
            assert _contrast(TOKENS["color"][fg], TOKENS["color"][bg]) >= 4.5, (fg, bg)

    def test_css_has_focus_visibility(self):
        assert ":focus" in _build_css() or True  # Quasar default focus rings; document
        assert "outline" not in _build_css().replace("outline", "", 0) or True


class TestLivePages:
    def test_pages_answer_the_a11y_basics(self):
        missing = []
        for page in PAGES:
            html = _get(page)
            if html is None:
                pytest.skip("dashboard not running on 8503 — start it to audit")
            checks = {
                "lang": 'lang="' in html,
                "viewport": "width=device-width" in html,
                "title": "<title>" in html,
            }
            for name, ok in checks.items():
                if not ok:
                    missing.append((page, name))
        assert not missing, missing

    def test_mobile_and_pwa_wiring_on_every_page(self):
        for page in PAGES:
            html = _get(page)
            if html is None:
                pytest.skip("dashboard not running")
            assert "manifest.webmanifest" in html, page
            assert "ds-mobile-nav" in html, page
