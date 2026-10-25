"""Winner adoption rule: latest APPROVED/CONDITIONAL run with green gates,
curated seed fallback, concentration caps binding on the winner."""

from __future__ import annotations

import json
from decimal import Decimal

import aiosqlite

from app.services.portfolio_management.models import ProfileAnswers
from app.services.portfolio_management.winner_adoption import (
    build_target,
    latest_winner,
    seed_target,
)

D = Decimal

SCHEMA = """
CREATE TABLE IF NOT EXISTS swarm_runs (
    workflow_id     TEXT PRIMARY KEY,
    status          TEXT NOT NULL,
    request_json    TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    total_xp        INTEGER NOT NULL DEFAULT 0,
    achievements_json TEXT NOT NULL DEFAULT '[]',
    results_json    TEXT
);
"""


async def _swarm_db(tmp_path, rows: list[dict]):
    path = tmp_path / "swarm_runs.db"
    async with aiosqlite.connect(path) as db:
        await db.executescript(SCHEMA)
        for row in rows:
            await db.execute(
                "INSERT INTO swarm_runs (workflow_id, status, request_json, started_at, "
                "results_json) VALUES (?, ?, '{}', ?, ?)",
                (
                    row["id"],
                    row.get("status", "completed"),
                    row["started_at"],
                    json.dumps(row.get("results", {})),
                ),
            )
        await db.commit()
    return path


def _results(status: str, allocations: list[dict], passed: bool = True) -> dict:
    return {
        "deployment_decision": {"status": status, "strategy_name": "dividend_tracking"},
        "validation": {"passed": passed},
        "portfolio": {
            "allocations": allocations,
            "expected_portfolio_return_pct": 7.5,
            "expected_portfolio_sharpe": 0.9,
        },
    }


PROFILE = ProfileAnswers(objective="MAXIMIZAR_DIVIDENDOS", risk_level="medium")


async def test_picks_latest_approved_skipping_rejected(tmp_path):
    db = await _swarm_db(
        tmp_path,
        [
            {
                "id": "old-winner",
                "started_at": "2026-10-20T10:00:00",
                "results": _results("APPROVED", [{"module_name": "SCHD", "weight_pct": 100}]),
            },
            {
                "id": "new-rejected",
                "started_at": "2026-10-22T10:00:00",
                "results": _results("REJECTED", [{"module_name": "VYM", "weight_pct": 100}]),
            },
        ],
    )
    winner = await latest_winner(db)
    assert winner is not None
    assert winner["run_id"] == "old-winner"
    assert winner["decision_status"] == "APPROVED"


async def test_conditional_with_failed_gates_is_not_a_winner(tmp_path):
    db = await _swarm_db(
        tmp_path,
        [
            {
                "id": "bad",
                "started_at": "2026-10-22T10:00:00",
                "results": _results(
                    "CONDITIONAL", [{"module_name": "SCHD", "weight_pct": 100}], passed=False
                ),
            }
        ],
    )
    assert await latest_winner(db) is None


async def test_missing_db_falls_back_to_seed(tmp_path):
    target = build_target(PROFILE, await latest_winner(tmp_path / "nope.db"))
    assert target.source == "seed"
    assert {h.symbol for h in target.holdings} == {"SCHD", "VYM", "VIG", "VYMI", "BND"}
    weights = sum((h.weight for h in target.holdings), D("0"))
    assert abs(weights - D("1")) < D("0.001")
    assert all(h.rationale for h in target.holdings)  # requirement 2: why each ETF


async def test_seed_respects_conservative_equity_cap(tmp_path):
    conservative = ProfileAnswers(objective="MAXIMIZAR_CAPITAL", risk_level="conservative")
    target = build_target(conservative, None)
    equity = sum((h.weight for h in target.holdings if h.symbol != "BND"), D("0"))
    assert equity <= D("0.61")  # 60% cap + rounding slack


async def test_winner_holdings_clamped_to_position_cap(tmp_path):
    winner = {
        "run_id": "r1",
        "decision_status": "APPROVED",
        "strategy_name": "static_ew",
        "holdings": [],
    }
    from app.services.portfolio_management.models import Holding

    # one 60% monster holding from a winner that ran a tiny universe
    winner["holdings"] = [
        Holding(symbol="SCHD", weight=D("0.6")),
        Holding(symbol="VYM", weight=D("0.4")),
    ]
    aggressive = ProfileAnswers(objective="MAXIMIZAR_CAPITAL", risk_level="medium")
    target = build_target(aggressive, winner)
    assert target.source == "swarm_winner"
    assert target.max_position_pct == D("35")
    # a 2-holding portfolio cannot sum to 100% under a 35% cap: the cap
    # relaxes to the minimum feasible share (50% each) — the monster
    # holding is still cut down from 60% to an even split
    assert all(h.weight <= D("0.501") for h in target.holdings)
    weights = [h.weight for h in target.holdings]
    assert abs(weights[0] - weights[1]) < D("0.01")
    assert abs(sum(weights) - D("1")) < D("0.001")


async def test_seed_target_direct_shape():
    target = seed_target(
        ProfileAnswers(objective="CAPITAL_PRESERVATION", risk_level="conservative")
    )
    assert target.source == "seed"
    assert target.drift_band_pct == D("2.0")  # conservative band
    assert target.cooldown_days == 7
