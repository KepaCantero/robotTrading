"""UI-6 — weekly digest: what happened, what to do (usually nothing).

A pure function over REAL state (last run, drift plan, next rebalance)
that speaks like a calm advisor: the most common digest must be
"suggested action: none — that's the product working".
"""

from __future__ import annotations

from datetime import date
from typing import Any


def weekly_digest(
    *,
    last_run_status: str | None,
    last_run_return_pct: Any | None = None,
    drift_status: str | None,
    next_rebalance_days: int | None = None,
    today: date | None = None,
) -> dict[str, str]:
    """Plain-English weekly summary from real signals.

    Every line derives from its input — there is no "you're doing
    great!" filler, and the no-action case says so explicitly.
    """
    del today  # deterministic output; reserved for date stamps
    if last_run_status == "completed":
        head = (
            f"Your portfolio's plan returned {last_run_return_pct}% across the "
            "tested years, fees included."
            if last_run_return_pct is not None
            else "Your portfolio's plan finished its check successfully."
        )
    elif last_run_status:
        head = "The last engine run didn't complete — nothing was hidden, nothing traded."
    else:
        head = "No runs yet: your portfolio is five questions away (/start)."

    action_by_drift = {
        "skipped": "Suggested action: none — your portfolio is inside its band. "
        "Doing nothing IS the strategy working.",
        "reactive": "Suggested action: none — new cash will be invested at the "
        "next scheduled touch; no selling needed.",
        "proactive": "Suggested action: a rebalance is due — open Portfolio to "
        "preview it with its tax cost before confirming.",
    }
    action = action_by_drift.get(
        drift_status or "", "Drift status unknown — open Portfolio to see it."
    )
    if next_rebalance_days is not None and next_rebalance_days > 0:
        when = f"Next scheduled touch: in {next_rebalance_days} days."
    elif next_rebalance_days == 0:
        when = "Next scheduled touch: today."
    else:
        when = ""
    return {"headline": head, "action": action, "when": when}
