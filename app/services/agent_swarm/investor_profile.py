"""Investor-profile persistence — the /start wizard's five answers, saved.

The profile IS the app-level default: Mission Control (/swarm) and the
portfolio pages read it instead of re-asking (owner decision 31-10: /start
only captures the profile; building and validating portfolios moved to
the swarm agents, which use this saved profile as their default).

One JSON file next to swarm_runs.db (repo root): single user, single
machine, atomic replace so a crash never leaves a half-written profile.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_INVESTOR_PROFILE_PATH = str(Path(__file__).resolve().parents[3] / "investor_profile.json")


class InvestorProfile(BaseModel):
    """The persisted questionnaire answers (names match SwarmRunRequest)."""

    investor_age: int
    investment_horizon: int  # months
    risk_tolerance: str  # BAJO | MEDIO | ALTO
    objetivo_inversion: str  # key of the wizard's GOAL_OPTIONS
    tax_province: str = "Madrid"
    updated_at: datetime = Field(default_factory=datetime.utcnow)


def load_investor_profile(path: str | Path | None = None) -> InvestorProfile | None:
    """Read the saved profile; a missing file means None (first visit).

    A corrupt or invalid file must never break the wizard — the user just
    answers again (the log records why the profile was discarded).
    """
    target = Path(path or DEFAULT_INVESTOR_PROFILE_PATH)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return InvestorProfile.model_validate(data)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:  # unreadable/corrupt → start fresh
        logger.warning("Investor profile at %s discarded: %s", target, exc)
        return None


def save_investor_profile(profile: InvestorProfile, path: str | Path | None = None) -> None:
    """Persist the profile atomically (write a tmp file, then replace)."""
    target = Path(path or DEFAULT_INVESTOR_PROFILE_PATH)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp, target)
