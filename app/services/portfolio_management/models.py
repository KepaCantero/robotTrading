"""Portfolio management domain models (robo-advisor mode).

This package turns a small set of profile answers into a persisted target
allocation (ETF -> weight) and keeps the live portfolio aligned with it
through drift-band, cash-flow-first, tax-aware rebalancing. The models here
are shared by the store, the winner-adoption step, the drift monitor, the
planner, the Spain tax preview, the executor and the dashboard page.

Design decisions locked with the user (2026-10-24):
- The default "do it for me" portfolio is ADOPTED from the latest winning
  swarm run (deploy decision APPROVED/CONDITIONAL with validation gates
  green); a curated seed is only the fallback when no winner exists yet.
- Rebalancing runs on PaperAdapter first (deterministic broker, first rung
  of the production ladder); the service only talks to the BrokerConnector
  contract so IBKR plugs in later without changes.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

#: Rebalancing rules per risk level. The drift band is absolute (2-3% is
#: the range a novice understands and avoids churn). Concentration caps are
#: PORTFOLIO caps, not the 5/10/20% trading caps of InputProfileRouter
#: (those govern active strategies with dozens of names — a 5-ETF target
#: portfolio cannot sum to 100% under them). Requirement 3 asks for caps
#: per asset (max_position_pct) and per asset TYPE (equity share ceiling):
#: conservative holds at least 40% bonds, aggressive up to 90% equity.
RISK_SETTINGS: dict[str, dict[str, Decimal | int]] = {
    "conservative": {
        "drift_band_pct": Decimal("2.0"),
        "cooldown_days": 7,
        "max_position_pct": Decimal("30"),
        "equity_max_pct": Decimal("60"),
    },
    "medium": {
        "drift_band_pct": Decimal("2.5"),
        "cooldown_days": 7,
        "max_position_pct": Decimal("35"),
        "equity_max_pct": Decimal("75"),
    },
    "aggressive": {
        "drift_band_pct": Decimal("3.0"),
        "cooldown_days": 7,
        "max_position_pct": Decimal("40"),
        "equity_max_pct": Decimal("90"),
    },
}

#: Asset type per curated symbol. Requirement 3's "per asset type" cap is
#: the equity/bond split — the protection that actually matters for a
#: novice. Unknown symbols default to equity (fail-safe: the cap binds).
ASSET_CLASS: dict[str, str] = {
    "BND": "bond",
    "BIV": "bond",
    "SCHZ": "bond",
    "VBT": "bond",
    "IBTS": "bond",  # iShares $ Treasury Bond 1-3yr UCITS ETF
}

#: Questionnaire objectives — same keys the swarm page uses, so a swarm
#: user recognises them on the portfolio page.
OBJECTIVES: dict[str, str] = {
    "MAXIMIZAR_CAPITAL": "Grow capital",
    "MAXIMIZAR_DIVIDENDOS": "Maximise dividends",
    "CAPITAL_PRESERVATION": "Preserve capital",
    "BALANCED_GROWTH": "Balanced growth",
    "INCOME_GENERATION": "Generate income",
}


class RebalanceTrigger(str, Enum):
    """Why a rebalance was considered."""

    CASH = "cash"  # new money (deposit / collected dividend) buys the underweight
    DRIFT = "drift"  # band exceeded and cash was not enough -> sell side
    PROFILE_CHANGE = "profile_change"  # target changed (profile / adoption)
    MANUAL = "manual"  # user pressed the button


class PlanStatus(str, Enum):
    """Outcome of a planning run."""

    SKIPPED = "skipped"  # nothing to do (in band, cooldown, reactive-only wait)
    REACTIVE = "reactive"  # buys funded by new cash only, no sells
    PROACTIVE = "proactive"  # sells (tax-aware) + buys


class Holding(BaseModel):
    """One target position: which ETF and what share of the portfolio."""

    symbol: str
    weight: Decimal  # 0..1 share of total portfolio value
    rationale: str = ""  # one plain sentence: why this ETF is here


class ProfileAnswers(BaseModel):
    """Snapshot of the questionnaire answers behind a target portfolio."""

    objective: str = "BALANCED_GROWTH"  # key of OBJECTIVES
    risk_level: str = "medium"  # conservative | medium | aggressive
    drawdown_tolerance_pct: Decimal = Decimal("20")  # biggest fall the user accepts
    investor_age: int | None = None
    horizon_months: int = 120
    tax_province: str = "Madrid"


class TargetPortfolio(BaseModel):
    """A versioned target allocation plus its rebalancing rules."""

    version: int = 1
    source: str = "seed"  # swarm_winner | seed | import
    source_run_id: str | None = None
    strategy_name: str | None = None
    decision_status: str | None = None  # APPROVED / CONDITIONAL of the adopted run
    holdings: list[Holding] = Field(default_factory=list)
    profile: ProfileAnswers = Field(default_factory=ProfileAnswers)
    drift_band_pct: Decimal = Decimal("2.5")
    cooldown_days: int = 7
    reactive_only: bool = False
    max_position_pct: Decimal = Decimal("35")
    equity_max_pct: Decimal = Decimal("75")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def settings_from_risk_level(self) -> None:
        """Apply the profile-driven band, cooldown and concentration caps."""
        settings = RISK_SETTINGS.get(self.profile.risk_level, RISK_SETTINGS["medium"])
        self.drift_band_pct = Decimal(str(settings["drift_band_pct"]))
        self.cooldown_days = int(settings["cooldown_days"])
        self.max_position_pct = Decimal(str(settings["max_position_pct"]))
        self.equity_max_pct = Decimal(str(settings["equity_max_pct"]))


class LotSnapshot(BaseModel):
    """A purchase lot (tax-aware selling needs per-lot dates and prices)."""

    lot_id: str
    symbol: str
    quantity: Decimal
    purchase_price: Decimal
    purchased_at: datetime
    source: str = "rebalance"


class DriftStatus(BaseModel):
    """Current vs target weight for one symbol."""

    symbol: str
    target_weight: Decimal
    current_weight: Decimal
    drift: Decimal  # current - target, in weight points (0.02 = 2 pp)
    breached: bool = False


class SellTaxImpact(BaseModel):
    """Spain tax preview for one planned sell (requirement 11)."""

    symbol: str
    quantity: Decimal
    price: Decimal
    proceeds: Decimal
    cost_basis: Decimal
    gain: Decimal  # proceeds - cost_basis (FIFO)
    tax: Decimal  # estimated € owed if sold now
    marginal_rate: Decimal
    loss_not_computable: bool = False  # Spain 2-month repurchase rule hit
    notes: list[str] = Field(default_factory=list)


class PlannedTrade(BaseModel):
    """One diff-order in a rebalance plan (never close-and-reopen)."""

    symbol: str
    side: str  # BUY | SELL
    quantity: Decimal  # fractional allowed; whole-share fallback at execution
    price: Decimal  # reference price used to plan
    value: Decimal  # quantity * price
    reason: str = ""  # plain-language why, shown in preview and history
    tax_impact: SellTaxImpact | None = None


class RebalancePlan(BaseModel):
    """The full outcome of one planning run, persisted as a rebalance event."""

    event_id: str
    status: PlanStatus = PlanStatus.SKIPPED
    trigger: RebalanceTrigger = RebalanceTrigger.DRIFT
    trades: list[PlannedTrade] = Field(default_factory=list)
    drifts: list[DriftStatus] = Field(default_factory=list)
    max_abs_drift: Decimal = Decimal("0")
    tax_total: Decimal = Decimal("0")
    summary: str = ""  # the one-paragraph plain-language explanation
    reasons: list[str] = Field(default_factory=list)  # line-by-line detail
    planned_at: datetime = Field(default_factory=datetime.utcnow)

    def to_details(self) -> dict[str, Any]:
        """JSON-ready details for the rebalance_events table."""
        return self.model_dump(mode="json")
