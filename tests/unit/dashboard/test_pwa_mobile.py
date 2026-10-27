"""UI-5 — PWA manifest validity + mobile nav gates."""

from __future__ import annotations

import json
from pathlib import Path

from app.presentation.dashboard.nicegui_app.layout import AppShell

_PWA = Path(__file__).resolve().parents[3] / ("app/presentation/dashboard/nicegui_app/static/pwa")


class TestManifest:
    def test_manifest_is_valid_and_complete(self):
        data = json.loads((_PWA / "manifest.webmanifest").read_text())
        assert data["start_url"] == "/start"  # the wizard is the door
        assert data["display"] == "standalone"  # installs like an app
        assert data["background_color"] == "#fffdf6"  # cream, never white
        assert data["theme_color"] == "#3f8f85"  # ds teal
        icons = {i["purpose"] if "purpose" in i else "any": i for i in data["icons"]}
        assert "maskable" in icons  # Android adaptive
        assert any(i["sizes"] == "512x512" for i in data["icons"])

    def test_icon_files_exist(self):
        for name in ("icon-192.png", "icon-512.png", "icon-maskable-512.png"):
            assert (_PWA / name).stat().st_size > 500, name


class TestMobileNav:
    def test_five_thumb_reachable_stages(self):
        routes = [p["route"] for p in AppShell.MOBILE_NAV]
        assert routes == ["/start", "/", "/portfolio", "/optimize", "/trust"]

    def test_every_nav_entry_has_name_and_icon(self):
        for page in AppShell.MOBILE_NAV:
            assert page["name"] and page["icon"]
