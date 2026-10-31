"""Investor-profile store: round-trip, atomic write, corrupt-file tolerance."""

from __future__ import annotations

from datetime import datetime

from app.services.agent_swarm.investor_profile import (
    InvestorProfile,
    load_investor_profile,
    save_investor_profile,
)


def _profile(**over) -> InvestorProfile:
    base = dict(
        investor_age=42,
        investment_horizon=120,
        risk_tolerance="MEDIO",
        tax_province="Bizkaia",
        objetivo_inversion="ACUMULAR",
    )
    base.update(over)
    return InvestorProfile(**base)


class TestRoundTrip:
    def test_save_then_load(self, tmp_path):
        path = tmp_path / "profile.json"
        profile = _profile()
        save_investor_profile(profile, path)
        assert load_investor_profile(path) == profile

    def test_load_missing_returns_none(self, tmp_path):
        assert load_investor_profile(tmp_path / "nope.json") is None

    def test_corrupt_json_returns_none(self, tmp_path):
        path = tmp_path / "profile.json"
        path.write_text("{not json", encoding="utf-8")
        assert load_investor_profile(path) is None

    def test_invalid_fields_return_none(self, tmp_path):
        path = tmp_path / "profile.json"
        path.write_text('{"investor_age": "very old"}', encoding="utf-8")
        assert load_investor_profile(path) is None


class TestAtomicOverwrite:
    def test_overwrite_replaces_profile_without_tmp_leftover(self, tmp_path):
        path = tmp_path / "profile.json"
        save_investor_profile(_profile(), path)
        save_investor_profile(_profile(risk_tolerance="ALTO"), path)
        loaded = load_investor_profile(path)
        assert loaded is not None
        assert loaded.risk_tolerance == "ALTO"
        assert list(tmp_path.iterdir()) == [path]  # replace left no .tmp behind

    def test_updated_at_is_stamped_on_save(self, tmp_path):
        path = tmp_path / "profile.json"
        before = datetime.utcnow()
        save_investor_profile(_profile(), path)
        loaded = load_investor_profile(path)
        assert loaded is not None
        assert loaded.updated_at >= before
