"""Named investor profiles — the /start wizard's answers, saved.

A profile is five answers plus a NAME ("Conservative", "Retirement", …):
the owner keeps several at once (product rule: anything account-like is
plural and user-named, like the paper portfolios) and picks one in
Mission Control, which applies it as the run configuration. One JSON
file next to swarm_runs.db (repo root): single user, single machine,
atomic replace so a crash never leaves a half-written store.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_INVESTOR_PROFILES_PATH = str(Path(__file__).resolve().parents[3] / "investor_profiles.json")
#: the wizard's first cut (31-10 morning) saved ONE anonymous profile
#: here; imported automatically the first time the new store is read.
_LEGACY_PROFILE_PATH = str(Path(__file__).resolve().parents[3] / "investor_profile.json")

_LEGACY_IMPORT_NAME = "My profile"


class InvestorProfile(BaseModel):
    """One named set of questionnaire answers (names match SwarmRunRequest)."""

    name: str
    investor_age: int
    investment_horizon: int  # months
    risk_tolerance: str  # BAJO | MEDIO | ALTO
    objetivo_inversion: str  # key of the swarm OBJECTIVES table
    tax_province: str = "Madrid"
    updated_at: datetime = Field(default_factory=datetime.utcnow)


def _empty_store() -> dict[str, Any]:
    return {"active": None, "profiles": []}


def _read_store(path: str | Path | None) -> dict[str, Any]:
    """Parse the JSON store; a corrupt file means an empty store (log why)."""
    target = Path(path or DEFAULT_INVESTOR_PROFILES_PATH)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if path is None:
            return _migrate_legacy()
        return _empty_store()
    except (OSError, ValueError) as exc:  # unreadable/corrupt → start fresh
        logger.warning("Investor-profile store at %s discarded: %s", target, exc)
        return _empty_store()
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), list):
        logger.warning("Investor-profile store at %s has an unexpected shape", target)
        return _empty_store()
    return data


def _write_store(store: dict[str, Any], path: str | Path | None) -> None:
    target = Path(path or DEFAULT_INVESTOR_PROFILES_PATH)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(store, indent=2), encoding="utf-8")
    os.replace(tmp, target)


def _migrate_legacy() -> dict[str, Any]:
    """Import the old single-profile file once, then forget it exists."""
    try:
        data = json.loads(Path(_LEGACY_PROFILE_PATH).read_text(encoding="utf-8"))
        profile = InvestorProfile.model_validate({**data, "name": _LEGACY_IMPORT_NAME})
    except (OSError, ValueError):
        return _empty_store()
    store = {"active": profile.name, "profiles": [profile.model_dump(mode="json")]}
    try:
        _write_store(store, None)
        logger.info("Migrated legacy investor profile to the named store")
    except OSError:
        logger.warning("Could not write the migrated investor-profile store")
    return store


def list_profiles(path: str | Path | None = None) -> list[InvestorProfile]:
    """All saved profiles, most recently updated first."""
    profiles: list[InvestorProfile] = []
    for raw in _read_store(path)["profiles"]:
        try:
            profiles.append(InvestorProfile.model_validate(raw))
        except ValueError:  # one bad row never hides the good ones
            logger.warning("Skipping invalid investor profile row: %r", raw)
    return sorted(profiles, key=lambda p: p.updated_at, reverse=True)


def get_profile(name: str, path: str | Path | None = None) -> InvestorProfile | None:
    """One profile by its exact name; None when absent."""
    for profile in list_profiles(path):
        if profile.name == name:
            return profile
    return None


def save_profile(profile: InvestorProfile, path: str | Path | None = None) -> None:
    """Insert or update (upsert keyed by name)."""
    store = _read_store(path)
    rows = [r for r in store["profiles"] if r.get("name") != profile.name]
    rows.append(profile.model_dump(mode="json"))
    store["profiles"] = rows
    _write_store(store, path)


def delete_profile(name: str, path: str | Path | None = None) -> None:
    """Remove one profile; the active pointer clears with it."""
    store = _read_store(path)
    store["profiles"] = [r for r in store["profiles"] if r.get("name") != name]
    if store.get("active") == name:
        store["active"] = None
    _write_store(store, path)


def active_profile(path: str | Path | None = None) -> InvestorProfile | None:
    """The profile Mission Control applies by default (None = app defaults)."""
    store = _read_store(path)
    name = store.get("active")
    if not name:
        return None
    for raw in store["profiles"]:
        if raw.get("name") == name:
            try:
                return InvestorProfile.model_validate(raw)
            except ValueError:
                return None
    return None


def set_active(name: str | None, path: str | Path | None = None) -> None:
    """Remember which profile Mission Control should apply on load."""
    store = _read_store(path)
    store["active"] = name
    _write_store(store, path)
