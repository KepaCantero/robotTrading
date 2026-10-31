"""Named investor-profile store: CRUD, active pointer, legacy migration."""

from __future__ import annotations

import json

from app.services.agent_swarm import investor_profile as store
from app.services.agent_swarm.investor_profile import InvestorProfile


def _profile(name: str = "Retirement", **over) -> InvestorProfile:
    base = dict(
        name=name,
        investor_age=42,
        investment_horizon=120,
        risk_tolerance="MEDIO",
        tax_province="Bizkaia",
        objetivo_inversion="ACUMULAR",
    )
    base.update(over)
    return InvestorProfile(**base)


class TestListAndGet:
    def test_empty_store_lists_nothing(self, tmp_path):
        assert store.list_profiles(tmp_path / "profiles.json") == []

    def test_corrupt_store_is_tolerated(self, tmp_path):
        path = tmp_path / "profiles.json"
        path.write_text("{not json", encoding="utf-8")
        assert store.list_profiles(path) == []

    def test_invalid_rows_are_skipped_not_fatal(self, tmp_path):
        path = tmp_path / "profiles.json"
        path.write_text(
            json.dumps(
                {
                    "active": None,
                    "profiles": [{"investor_age": "very old"}, _profile().model_dump(mode="json")],
                }
            ),
            encoding="utf-8",
        )
        names = [p.name for p in store.list_profiles(path)]
        assert names == ["Retirement"]

    def test_list_is_newest_first(self, tmp_path):
        path = tmp_path / "profiles.json"
        store.save_profile(_profile("Old"), path)
        store.save_profile(_profile("New"), path)
        assert [p.name for p in store.list_profiles(path)] == ["New", "Old"]

    def test_get_returns_exact_name_or_none(self, tmp_path):
        path = tmp_path / "profiles.json"
        store.save_profile(_profile("Retirement"), path)
        assert store.get_profile("Retirement", path) is not None
        assert store.get_profile("retirement", path) is None  # names are exact


class TestSaveUpsertDelete:
    def test_save_then_load_round_trips(self, tmp_path):
        path = tmp_path / "profiles.json"
        profile = _profile()
        store.save_profile(profile, path)
        assert store.list_profiles(path) == [profile]

    def test_same_name_updates_in_place(self, tmp_path):
        path = tmp_path / "profiles.json"
        store.save_profile(_profile(), path)
        store.save_profile(_profile(risk_tolerance="ALTO"), path)
        profiles = store.list_profiles(path)
        assert len(profiles) == 1
        assert profiles[0].risk_tolerance == "ALTO"

    def test_delete_removes_only_that_profile(self, tmp_path):
        path = tmp_path / "profiles.json"
        store.save_profile(_profile("A"), path)
        store.save_profile(_profile("B"), path)
        store.delete_profile("A", path)
        assert [p.name for p in store.list_profiles(path)] == ["B"]

    def test_delete_clears_active_pointer(self, tmp_path):
        path = tmp_path / "profiles.json"
        store.save_profile(_profile("A"), path)
        store.set_active("A", path)
        store.delete_profile("A", path)
        assert store.active_profile(path) is None

    def test_writes_are_atomic_no_tmp_leftover(self, tmp_path):
        path = tmp_path / "profiles.json"
        store.save_profile(_profile(), path)
        store.save_profile(_profile("B"), path)
        assert list(tmp_path.iterdir()) == [path]


class TestActivePointer:
    def test_active_round_trip(self, tmp_path):
        path = tmp_path / "profiles.json"
        store.save_profile(_profile("A"), path)
        store.set_active("A", path)
        active = store.active_profile(path)
        assert active is not None and active.name == "A"

    def test_active_none_by_default(self, tmp_path):
        assert store.active_profile(tmp_path / "profiles.json") is None

    def test_active_missing_name_is_none(self, tmp_path):
        path = tmp_path / "profiles.json"
        store.save_profile(_profile("A"), path)
        store.set_active("ghost", path)
        assert store.active_profile(path) is None


class TestLegacyMigration:
    def test_old_single_profile_file_is_imported_once(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            store, "DEFAULT_INVESTOR_PROFILES_PATH", str(tmp_path / "profiles.json")
        )
        monkeypatch.setattr(store, "_LEGACY_PROFILE_PATH", str(tmp_path / "investor_profile.json"))
        (tmp_path / "investor_profile.json").write_text(
            json.dumps(
                {
                    "investor_age": 42,
                    "investment_horizon": 240,
                    "risk_tolerance": "ALTO",
                    "tax_province": "Bizkaia",
                    "objetivo_inversion": "ACUMULAR",
                }
            ),
            encoding="utf-8",
        )

        profiles = store.list_profiles()
        assert [p.name for p in profiles] == ["My profile"]
        assert store.active_profile() is not None  # it was THE profile

        # and the import persists to the new store
        assert (tmp_path / "profiles.json").exists()
