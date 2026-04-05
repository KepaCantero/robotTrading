"""ProfitabilityEngine - evaluates backtest results against profile thresholds.

Produces PASS/FAIL/INCONCLUSIVE verdicts with a 0-100 risk-adjusted score
for the NiceGUI backtesting dashboard.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.infrastructure.persistence.backtest_result_store import BacktestRunRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Profile-specific thresholds (from profile_batch_backtest.yaml)
# ---------------------------------------------------------------------------

PROFILE_THRESHOLDS: dict[str, dict[str, Any]] = {
    "maximizar_capital": {
        "primary_metric": "sharpe_ratio",
        "min_sharpe": 1.0,
        "min_return": 0.10,
    },
    "maximizar_dividendos": {
        "primary_metric": "total_return",
        "min_sharpe": 0.8,
        "min_return": 0.10,
        "dividend_focus": True,
    },
    "capital_preservation": {
        "primary_metric": "max_drawdown",
        "min_sharpe": 0.5,
        "min_return": 0.05,
        "max_drawdown_limit": 0.10,
    },
    "balanced_growth": {
        "primary_metric": "sharpe_ratio",
        "min_sharpe": 1.0,
        "min_return": 0.10,
    },
    "income_generation": {
        "primary_metric": "total_return",
        "min_sharpe": 0.7,
        "min_return": 0.10,
        "dividend_focus": True,
    },
}

# Global acceptance criteria (from acceptance_criteria section)
DEFAULT_CRITERIA: dict[str, Any] = {
    "min_sharpe": 0.5,
    "max_drawdown": -0.25,
    "min_win_rate": 0.45,
    "min_trades": 20,
    "min_profit_factor": 1.5,
}

# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class ProfitabilityResult(BaseModel):
    """Outcome of a profitability evaluation."""

    verdict: str  # "PASS", "FAIL", "INCONCLUSIVE"
    score: float  # 0-100 risk-adjusted score
    profile: str
    strategy: str
    details: dict[str, Any]  # per-metric evaluation
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

# Mapping from profile threshold keys to BacktestRunRecord attribute names.
_THRESHOLD_TO_ATTR: dict[str, str] = {
    "min_sharpe": "sharpe_ratio",
    "min_return": "total_return",
}


class ProfitabilityEngine:
    """Evaluates backtest results against profile-specific thresholds."""

    def __init__(self) -> None:
        self._thresholds = PROFILE_THRESHOLDS
        self._defaults = DEFAULT_CRITERIA

    # -- public API ---------------------------------------------------------

    def evaluate(self, run: BacktestRunRecord) -> ProfitabilityResult:
        """Evaluate a backtest run using the profile stored on the record."""
        profile = run.investor_profile or "unknown"
        return self._evaluate_internal(run, profile)

    def evaluate_with_profile(self, run: BacktestRunRecord, profile: str) -> ProfitabilityResult:
        """Evaluate a backtest run against an explicit profile."""
        return self._evaluate_internal(run, profile)

    def compute_score(self, run: BacktestRunRecord) -> float:
        """Compute a 0-100 risk-adjusted score for a backtest run."""
        return self._compute_score(run)

    def batch_evaluate(self, runs: list[BacktestRunRecord]) -> list[ProfitabilityResult]:
        """Evaluate multiple runs and return a list of results."""
        return [self.evaluate(run) for run in runs]

    # -- internal helpers ---------------------------------------------------

    def _evaluate_internal(self, run: BacktestRunRecord, profile: str) -> ProfitabilityResult:
        """Core evaluation logic."""
        thresholds = self._thresholds.get(profile)
        details: dict[str, Any] = {}
        warnings: list[str] = []

        if thresholds is None:
            # Unknown profile -- fall back to default criteria
            result = self._evaluate_with_defaults(run, profile)
            return result

        primary_metric = thresholds.get("primary_metric", "sharpe_ratio")

        # Evaluate primary metric
        primary_value = getattr(run, primary_metric, None)
        primary_threshold = self._primary_threshold_for(profile, thresholds)

        if primary_value is None:
            details[primary_metric] = {
                "value": None,
                "threshold": primary_threshold,
                "passed": None,
            }
            warnings.append(f"Primary metric '{primary_metric}' is missing")
            return ProfitabilityResult(
                verdict="INCONCLUSIVE",
                score=self._compute_score(run),
                profile=profile,
                strategy=run.strategy_name,
                details=details,
                warnings=warnings,
            )

        primary_passed = self._check_primary(primary_metric, primary_value, thresholds)
        details[primary_metric] = {
            "value": primary_value,
            "threshold": primary_threshold,
            "passed": primary_passed,
        }

        # If primary metric fails, verdict is FAIL immediately
        if not primary_passed:
            self._evaluate_secondary_metrics(run, thresholds, details)
            return ProfitabilityResult(
                verdict="FAIL",
                score=self._compute_score(run),
                profile=profile,
                strategy=run.strategy_name,
                details=details,
                warnings=warnings,
            )

        # Check secondary thresholds
        secondary_missing, secondary_failed = self._evaluate_secondary_metrics(
            run, thresholds, details
        )

        if secondary_missing:
            return ProfitabilityResult(
                verdict="INCONCLUSIVE",
                score=self._compute_score(run),
                profile=profile,
                strategy=run.strategy_name,
                details=details,
                warnings=warnings,
            )

        if secondary_failed:
            return ProfitabilityResult(
                verdict="FAIL",
                score=self._compute_score(run),
                profile=profile,
                strategy=run.strategy_name,
                details=details,
                warnings=warnings,
            )

        # Check max_drawdown_limit if present
        if "max_drawdown_limit" in thresholds:
            if run.max_drawdown is None:
                details["max_drawdown"] = {
                    "value": None,
                    "threshold": -thresholds["max_drawdown_limit"],
                    "passed": None,
                }
                warnings.append("max_drawdown is missing")
                return ProfitabilityResult(
                    verdict="INCONCLUSIVE",
                    score=self._compute_score(run),
                    profile=profile,
                    strategy=run.strategy_name,
                    details=details,
                    warnings=warnings,
                )

            dd_limit = thresholds["max_drawdown_limit"]
            dd_passed = abs(run.max_drawdown) <= dd_limit
            details["max_drawdown"] = {
                "value": run.max_drawdown,
                "threshold": -dd_limit,
                "passed": dd_passed,
            }
            if not dd_passed:
                return ProfitabilityResult(
                    verdict="FAIL",
                    score=self._compute_score(run),
                    profile=profile,
                    strategy=run.strategy_name,
                    details=details,
                    warnings=warnings,
                )

        return ProfitabilityResult(
            verdict="PASS",
            score=self._compute_score(run),
            profile=profile,
            strategy=run.strategy_name,
            details=details,
            warnings=warnings,
        )

    def _primary_threshold_for(self, profile: str, thresholds: dict[str, Any]) -> Any:
        """Return the numeric threshold for the primary metric."""
        primary = thresholds.get("primary_metric", "sharpe_ratio")
        if primary == "sharpe_ratio":
            return thresholds.get("min_sharpe")
        if primary == "total_return":
            return thresholds.get("min_return")
        if primary == "max_drawdown":
            return -thresholds.get("max_drawdown_limit", 0.25)
        return None

    def _check_primary(
        self,
        metric: str,
        value: float,
        thresholds: dict[str, Any],
    ) -> bool:
        """Check whether the primary metric meets its threshold."""
        if metric == "sharpe_ratio":
            return bool(value >= thresholds["min_sharpe"])
        if metric == "total_return":
            return bool(value >= thresholds["min_return"])
        if metric == "max_drawdown":
            limit = thresholds.get("max_drawdown_limit", 0.25)
            return bool(abs(value) <= limit)
        return False

    def _evaluate_secondary_metrics(
        self,
        run: BacktestRunRecord,
        thresholds: dict[str, Any],
        details: dict[str, Any],
    ) -> tuple[bool, bool]:
        """Evaluate secondary thresholds (min_sharpe, min_return).

        Returns a tuple of (missing, failed):
          - missing: True if any required secondary metric is None
          - failed: True if any secondary metric is present but below threshold
        """
        missing = False
        failed = False

        for key, attr in _THRESHOLD_TO_ATTR.items():
            if key not in thresholds:
                continue
            value = getattr(run, attr, None)
            threshold = thresholds[key]
            if value is None:
                details[attr] = {
                    "value": None,
                    "threshold": threshold,
                    "passed": None,
                }
                missing = True
            else:
                passed = value >= threshold
                details[attr] = {
                    "value": value,
                    "threshold": threshold,
                    "passed": passed,
                }
                if not passed:
                    failed = True

        return missing, failed

    def _evaluate_with_defaults(self, run: BacktestRunRecord, profile: str) -> ProfitabilityResult:
        """Evaluate using default criteria when profile is unknown."""
        details: dict[str, Any] = {}
        warnings: list[str] = []

        # Check sharpe_ratio as primary for unknown profiles
        sharpe = run.sharpe_ratio
        min_sharpe = self._defaults["min_sharpe"]
        if sharpe is None:
            details["sharpe_ratio"] = {
                "value": None,
                "threshold": min_sharpe,
                "passed": None,
            }
            warnings.append("sharpe_ratio is missing")
            return ProfitabilityResult(
                verdict="INCONCLUSIVE",
                score=self._compute_score(run),
                profile=profile,
                strategy=run.strategy_name,
                details=details,
                warnings=warnings,
            )

        sharpe_passed = sharpe >= min_sharpe
        details["sharpe_ratio"] = {
            "value": sharpe,
            "threshold": min_sharpe,
            "passed": sharpe_passed,
        }

        if not sharpe_passed:
            return ProfitabilityResult(
                verdict="FAIL",
                score=self._compute_score(run),
                profile=profile,
                strategy=run.strategy_name,
                details=details,
                warnings=warnings,
            )

        return ProfitabilityResult(
            verdict="PASS",
            score=self._compute_score(run),
            profile=profile,
            strategy=run.strategy_name,
            details=details,
            warnings=warnings,
        )

    # -- score computation --------------------------------------------------

    def _compute_score(self, run: BacktestRunRecord) -> float:
        """Compute a 0-100 risk-adjusted score."""
        # Base: Sharpe * 20 (max 40)
        sharpe = run.sharpe_ratio if run.sharpe_ratio is not None else 0.0
        sharpe_pts = min(sharpe * 20, 40)

        # Return contribution (max 30)
        ret = run.total_return if run.total_return is not None else 0.0
        return_pts = min(abs(ret) * 100, 30)

        # Risk penalty (max -20)
        dd = run.max_drawdown if run.max_drawdown is not None else 0.0
        dd_penalty = min(abs(dd) * 100, 20)

        # Win rate bonus (max 30)
        wr = run.win_rate if run.win_rate is not None else 0.0
        wr_pts = min(wr * 30, 30)

        # Profit factor bonus (max 20)
        pf = run.profit_factor if run.profit_factor is not None else 0.0
        pf_pts = min((pf - 1) * 10, 20) if pf > 1 else 0.0

        raw = sharpe_pts + return_pts - dd_penalty + wr_pts + pf_pts
        return max(0.0, min(raw, 100.0))
