"""
Almgren-Chriss Market Impact Model

Implements Harris Rule 6.4: Market impact model using Almgren-Chriss framework.

The Almgren-Chriss model decomposes market impact into:
1. Permanent impact: Price displacement that persists after execution
2. Temporary impact: Price displacement during execution that recovers

Reference:
Almgren, R., & Chriss, N. (2001). "Optimal Execution of Portfolio Transactions"
Journal of Risk, 3(2), 5-39.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

import numpy as np

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


class ImpactComponent(Enum):
    """Market impact components."""

    PERMANENT = "permanent"
    TEMPORARY = "temporary"
    TOTAL = "total"


@dataclass
class MarketImpactEstimate:
    """Market impact estimate from Almgren-Chriss model."""

    symbol: str
    order_size: Decimal
    adv: Decimal  # Average daily volume
    participation_rate: float

    # Impact components
    permanent_impact_bps: Decimal
    temporary_impact_bps: Decimal
    total_impact_bps: Decimal

    # Cost estimates
    permanent_cost_usd: Decimal
    temporary_cost_usd: Decimal
    total_cost_usd: Decimal

    # Model parameters
    gamma: float  # Permanent impact coefficient
    eta: float  # Temporary impact coefficient
    volatility: float

    # Recommendations
    recommended_execution_time: int  # seconds
    recommended_tranche_size: Decimal


@dataclass
class OptimalExecutionSchedule:
    """Optimal execution schedule from Almgren-Chriss."""

    symbol: str
    total_quantity: Decimal
    time_horizon: int  # seconds
    n_tranches: int

    # Schedule: list of (time_seconds, quantity)
    schedule: list[tuple[int, Decimal]]

    expected_total_cost_bps: Decimal
    expected_total_cost_usd: Decimal


class AlmgrenChrissModel:
    """
    Almgren-Chriss Market Impact Model (Harris Rule 6.4).

    Models market impact as a function of:
    - Order size (participation rate)
    - Volatility
    - Execution time

    Impact = Permanent + Temporary
    - Permanent: gamma * sigma * sqrt(participation)
    - Temporary: eta * sigma * (size / ADV)
    """

    # Default model parameters (calibrated for US equities)
    DEFAULT_GAMMA = 0.1  # Permanent impact coefficient
    DEFAULT_ETA = 0.05  # Temporary impact coefficient

    # Parameter ranges for different asset classes
    PARAMETER_RANGES: ClassVar[dict] = {
        "equity": {
            "gamma": (0.05, 0.2),
            "eta": (0.02, 0.1),
        },
        "etf": {
            "gamma": (0.03, 0.15),
            "eta": (0.01, 0.05),
        },
        "forex": {
            "gamma": (0.01, 0.05),
            "eta": (0.005, 0.02),
        },
        "crypto": {
            "gamma": (0.1, 0.5),
            "eta": (0.05, 0.2),
        },
        "futures": {
            "gamma": (0.03, 0.1),
            "eta": (0.01, 0.05),
        },
    }

    def __init__(
        self,
        gamma: float | None = None,
        eta: float | None = None,
        asset_class: str = "equity",
    ):
        """
        Initialize Almgren-Chriss model.

        Args:
            gamma: Permanent impact coefficient (default: from asset class)
            eta: Temporary impact coefficient (default: from asset class)
            asset_class: Asset class for default parameters
        """
        if gamma is None or eta is None:
            # Use defaults for asset class
            params = self.PARAMETER_RANGES.get(
                asset_class,
                self.PARAMETER_RANGES["equity"],
            )
            self.gamma = (params["gamma"][0] + params["gamma"][1]) / 2
            self.eta = (params["eta"][0] + params["eta"][1]) / 2
        else:
            self.gamma = gamma
            self.eta = eta

        self.asset_class = asset_class

        logger.info(
            f"Almgren-Chriss model initialized: gamma={self.gamma:.4f}, eta={self.eta:.4f}, "
            f"asset_class={asset_class}"
        )

    def estimate_impact(
        self,
        symbol: str,
        order_size: Decimal,
        adv: Decimal,
        volatility: float,
        execution_time_seconds: int = 3600,
        price: Decimal | None = None,
    ) -> MarketImpactEstimate:
        """
        Estimate market impact using Almgren-Chriss model.

        Args:
            symbol: Trading symbol
            order_size: Order quantity (shares)
            adv: Average daily volume (shares)
            volatility: Daily volatility (decimal, e.g., 0.02 for 2%)
            execution_time_seconds: Execution time horizon
            price: Current price (for USD cost calculation)

        Returns:
            MarketImpactEstimate with detailed impact breakdown
        """
        # Calculate participation rate
        participation_rate = float(order_size / adv) if adv > 0 else 0

        # Permanent impact: gamma * sigma * sqrt(participation)
        # This is the price displacement that persists after execution
        permanent_impact = self.gamma * volatility * np.sqrt(max(participation_rate, 0))

        # Temporary impact: eta * sigma * (size / ADV) / (1 + execution_time_factor)
        # This is the walking the book cost that recovers
        time_factor = np.sqrt(execution_time_seconds / 86400)  # Normalize to day
        temporary_impact = self.eta * volatility * participation_rate / time_factor

        # Total impact
        total_impact = permanent_impact + temporary_impact

        # Convert to basis points
        permanent_impact_bps = Decimal(str(permanent_impact * 10000))
        temporary_impact_bps = Decimal(str(temporary_impact * 10000))
        total_impact_bps = Decimal(str(total_impact * 10000))

        # Calculate USD costs
        if price is not None:
            order_value = float(order_size * price)
            permanent_cost_usd = Decimal(str(order_value * permanent_impact))
            temporary_cost_usd = Decimal(str(order_value * temporary_impact))
            total_cost_usd = permanent_cost_usd + temporary_cost_usd
        else:
            permanent_cost_usd = Decimal("0")
            temporary_cost_usd = Decimal("0")
            total_cost_usd = Decimal("0")

        # Calculate optimal execution parameters
        # Rule of thumb: Execute over time such that temporary impact = permanent impact
        if temporary_impact > 0 and permanent_impact > 0:
            optimal_time_factor = temporary_impact / permanent_impact
            recommended_time = int(execution_time_seconds * optimal_time_factor)
        else:
            recommended_time = execution_time_seconds

        # Recommended tranche size
        n_tranches = max(1, recommended_time // 300)  # One tranche per 5 minutes
        if n_tranches > 0:
            recommended_tranche_size = order_size / Decimal(str(n_tranches))
        else:
            recommended_tranche_size = order_size

        return MarketImpactEstimate(
            symbol=symbol,
            order_size=order_size,
            adv=adv,
            participation_rate=participation_rate,
            permanent_impact_bps=permanent_impact_bps,
            temporary_impact_bps=temporary_impact_bps,
            total_impact_bps=total_impact_bps,
            permanent_cost_usd=permanent_cost_usd,
            temporary_cost_usd=temporary_cost_usd,
            total_cost_usd=total_cost_usd,
            gamma=self.gamma,
            eta=self.eta,
            volatility=volatility,
            recommended_execution_time=recommended_time,
            recommended_tranche_size=recommended_tranche_size,
        )

    def calculate_optimal_schedule(
        self,
        symbol: str,
        total_quantity: Decimal,
        time_horizon_seconds: int,
        adv: Decimal,
        volatility: float,
        price: Decimal,
        n_tranches: int | None = None,
    ) -> OptimalExecutionSchedule:
        """
        Calculate optimal execution schedule using Almgren-Chriss.

        The optimal schedule trades off market impact vs timing risk.
        Faster execution = higher temporary impact, lower timing risk
        Slower execution = lower temporary impact, higher timing risk

        Args:
            symbol: Trading symbol
            total_quantity: Total quantity to execute
            time_horizon_seconds: Maximum execution time
            adv: Average daily volume
            volatility: Daily volatility
            price: Current price
            n_tranches: Number of tranches (default: auto-calculated)

        Returns:
            OptimalExecutionSchedule with timing and quantities
        """
        # Auto-calculate number of tranches
        if n_tranches is None:
            # Rule: One tranche per 5 minutes, max 20 tranches
            n_tranches = min(20, max(1, time_horizon_seconds // 300))

        # Almgren-Chriss optimal: Equal-sized tranches at equal intervals
        tranche_size = total_quantity / Decimal(str(n_tranches))
        interval = time_horizon_seconds // n_tranches

        # Build schedule
        schedule = []
        for i in range(n_tranches):
            time_seconds = i * interval
            schedule.append((time_seconds, tranche_size))

        # Estimate total cost
        impact_estimate = self.estimate_impact(
            symbol=symbol,
            order_size=total_quantity,
            adv=adv,
            volatility=volatility,
            execution_time_seconds=time_horizon_seconds,
            price=price,
        )

        return OptimalExecutionSchedule(
            symbol=symbol,
            total_quantity=total_quantity,
            time_horizon=time_horizon_seconds,
            n_tranches=n_tranches,
            schedule=schedule,
            expected_total_cost_bps=impact_estimate.total_impact_bps,
            expected_total_cost_usd=impact_estimate.total_cost_usd,
        )

    def compare_execution_strategies(
        self,
        symbol: str,
        order_size: Decimal,
        adv: Decimal,
        volatility: float,
        price: Decimal,
    ) -> dict[str, MarketImpactEstimate]:
        """
        Compare different execution strategies.

        Returns estimates for:
        - urgent: Execute in 5 minutes
        - normal: Execute in 1 hour
        - patient: Execute in 4 hours
        """
        strategies = {
            "urgent": 300,  # 5 minutes
            "normal": 3600,  # 1 hour
            "patient": 14400,  # 4 hours
        }

        results = {}
        for strategy, time_seconds in strategies.items():
            estimate = self.estimate_impact(
                symbol=symbol,
                order_size=order_size,
                adv=adv,
                volatility=volatility,
                execution_time_seconds=time_seconds,
                price=price,
            )
            results[strategy] = estimate

        return results

    def calibrate_parameters(
        self,
        historical_executions: pd.DataFrame,
        symbol_col: str = "symbol",
        size_col: str = "size",
        adv_col: str = "adv",
        volatility_col: str = "volatility",
        impact_col: str = "impact_bps",
    ) -> dict[str, float]:
        """
        Calibrate model parameters from historical execution data.

        Uses regression to estimate gamma and eta.

        Args:
            historical_executions: DataFrame with historical executions
            symbol_col: Column name for symbol
            size_col: Column name for order size
            adv_col: Column name for ADV
            volatility_col: Column name for volatility
            impact_col: Column name for realized impact (bps)

        Returns:
            Dict with calibrated parameters
        """
        required_cols = [size_col, adv_col, volatility_col, impact_col]
        missing = [c for c in required_cols if c not in historical_executions.columns]

        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Calculate participation rate
        df = historical_executions.copy()
        df["participation"] = df[size_col] / df[adv_col]
        df["sqrt_participation"] = np.sqrt(df["participation"])

        # Prepare for regression
        X = df[[volatility_col, "sqrt_participation", "participation"]].values
        y = df[impact_col].values / 10000  # Convert bps to decimal

        # Add intercept
        X = np.column_stack([np.ones(len(X)), X])

        # OLS regression
        try:
            coefficients, _, _, _ = np.linalg.lstsq(X, y, rcond=None)

            # Extract parameters (simplified)
            # impact = beta0 + beta1*vol + beta2*vol*sqrt(part) + beta3*vol*part
            # We focus on beta2 ~ gamma, beta3 ~ eta

            gamma = max(0.01, abs(float(coefficients[2])))
            eta = max(0.005, abs(float(coefficients[3])))

            logger.info(f"Calibrated parameters: gamma={gamma:.4f}, eta={eta:.4f}")

            return {
                "gamma": gamma,
                "eta": eta,
                "n_observations": len(df),
                "r_squared": self._calculate_r_squared(X, y, coefficients),
            }

        except Exception as e:
            logger.warning(f"Calibration failed: {e}, using defaults")
            return {
                "gamma": self.gamma,
                "eta": self.eta,
                "n_observations": 0,
                "r_squared": 0.0,
            }

    def _calculate_r_squared(
        self,
        X: np.ndarray,
        y: np.ndarray,
        coefficients: np.ndarray,
    ) -> float:
        """Calculate R-squared for regression fit."""
        y_pred = X @ coefficients
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        if ss_tot == 0:
            return 0.0

        return 1 - (ss_res / ss_tot)


# Global singleton
_almgren_chriss_model: AlmgrenChrissModel = None


def get_almgren_chriss_model(
    gamma: float | None = None,
    eta: float | None = None,
    asset_class: str = "equity",
) -> AlmgrenChrissModel:
    """Get or create global AlmgrenChrissModel instance."""
    global _almgren_chriss_model
    if _almgren_chriss_model is None:
        _almgren_chriss_model = AlmgrenChrissModel(
            gamma=gamma,
            eta=eta,
            asset_class=asset_class,
        )

    return _almgren_chriss_model
