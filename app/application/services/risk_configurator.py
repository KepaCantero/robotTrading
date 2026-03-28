"""
Risk Configuration Service

Provides risk management configuration based on risk tolerance.
Implements VaR, Expected Shortfall, and drawdown controls.

Reference: Rule 13-john-hull-risk-management.md
Paper: Artzner, et al. (1999). "Coherent Measures of Risk"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class RiskLimitType(str, Enum):
    """Types of risk limits."""

    MAX_DRAWDOWN = "max_drawdown"
    MAX_VOLATILITY = "max_volatility"
    VAR_LIMIT = "var_limit"
    EXPECTED_SHORTFALL = "expected_shortfall"
    MAX_POSITION_SIZE = "max_position_size"
    MAX_LEVERAGE = "max_leverage"
    CONCENTRATION_LIMIT = "concentration_limit"


class StressTestScenario(str, Enum):
    """Stress test scenarios for risk management."""

    MARKET_CRASH = "market_crash"  # -30% market drop
    VOLATILITY_SPIKE = "volatility_spike"  # 2x volatility
    SECTOR_ROTATION = "sector_rotation"  # Sector-specific moves
    LIQUIDITY_CRISIS = "liquidity_crisis"  # Wide bid-ask spreads
    CORRELATION_BREAKDOWN = "correlation_breakdown"  # Diversification fails


@dataclass
class RiskLimit:
    """A single risk limit."""

    limit_type: RiskLimitType
    limit_value: Decimal
    current_value: Decimal
    utilization: float  # 0-1, percentage of limit used
    is_breached: bool
    timestamp: datetime


@dataclass
class VaRResult:
    """Value at Risk calculation result."""

    var_95: Decimal  # VaR at 95% confidence
    var_99: Decimal  # VaR at 99% confidence
    expected_shortfall_95: Decimal  # ES at 95% confidence
    expected_shortfall_99: Decimal  # ES at 99% confidence
    confidence_interval: Tuple[Decimal, Decimal]  # 95% CI for VaR
    calculation_date: datetime


@dataclass
class DrawdownMetrics:
    """Drawdown metrics."""

    current_drawdown: Decimal
    max_drawdown: Decimal
    avg_drawdown: Decimal
    drawdown_duration: int  # Days in current drawdown
    max_drawdown_duration: int  # Longest drawdown period
    recovery_factor: float  # Months to recover from max DD


@dataclass
class RiskBudget:
    """Risk budget allocation."""

    total_risk_budget: Decimal  # In volatility terms
    equity_risk: Decimal  # Allocation to equities
    fixed_income_risk: Decimal  # Allocation to fixed income
    alternative_risk: Decimal  # Allocation to alternatives
    currency_risk: Decimal  # Allocation to currency risk
    concentration_risk: Decimal  # Allocation to concentration


class RiskConfigurator:
    """
    Risk configuration service.

    Provides risk management configuration based on risk tolerance:
    - VaR and Expected Shortfall calculations
    - Drawdown monitoring and control
    - Position sizing limits
    - Leverage constraints
    - Stress testing

    Reference: John Hull, "Risk Management and Financial Institutions"
    Reference: Artzner, et al. (1999), "Coherent Measures of Risk"
    """

    def __init__(self):
        """Initialize risk configurator."""
        self._risk_limits: Dict[RiskLimitType, Decimal] = {}
        self._stress_scenarios = self._initialize_stress_scenarios()

    def configure_risk_limits(
        self,
        risk_tolerance: str,  # "BAJO", "MEDIO", "ALTO"
        capital: Decimal,
    ) -> dict[RiskLimitType, Decimal]:
        """
        Configure risk limits based on risk tolerance.

        Args:
            risk_tolerance: Risk tolerance level (BAJO, MEDIO, ALTO)
            capital: Total capital

        Returns:
            Dictionary of risk limits

        Raises:
            ValueError: If risk_tolerance is invalid or capital is non-positive
        """
        if capital <= 0:
            raise ValueError("capital must be positive")

        valid_tolerances = {"BAJO", "MEDIO", "ALTO"}
        if risk_tolerance not in valid_tolerances:
            raise ValueError(
                f"risk_tolerance must be one of {valid_tolerances}, got '{risk_tolerance}'"
            )

        logger.info(
            "Configuring risk limits: risk_tolerance=%s, capital=%s",
            risk_tolerance,
            str(capital),
        )

        if risk_tolerance == "BAJO":
            return {
                RiskLimitType.MAX_DRAWDOWN: Decimal("0.15"),  # 15%
                RiskLimitType.MAX_VOLATILITY: Decimal("0.20"),  # 20%
                RiskLimitType.VAR_LIMIT: capital * Decimal("0.05"),  # 5% of capital
                RiskLimitType.EXPECTED_SHORTFALL: capital * Decimal("0.07"),  # 7%
                RiskLimitType.MAX_POSITION_SIZE: Decimal("0.05"),  # 5%
                RiskLimitType.MAX_LEVERAGE: Decimal("1.0"),  # No leverage
                RiskLimitType.CONCENTRATION_LIMIT: Decimal("0.20"),  # 20% per sector
            }
        elif risk_tolerance == "MEDIO":
            return {
                RiskLimitType.MAX_DRAWDOWN: Decimal("0.25"),  # 25%
                RiskLimitType.MAX_VOLATILITY: Decimal("0.30"),  # 30%
                RiskLimitType.VAR_LIMIT: capital * Decimal("0.08"),  # 8%
                RiskLimitType.EXPECTED_SHORTFALL: capital * Decimal("0.12"),  # 12%
                RiskLimitType.MAX_POSITION_SIZE: Decimal("0.10"),  # 10%
                RiskLimitType.MAX_LEVERAGE: Decimal("1.5"),  # 1.5x
                RiskLimitType.CONCENTRATION_LIMIT: Decimal("0.30"),  # 30%
            }
        else:  # risk_tolerance == "ALTO" (validated above)
            return {
                RiskLimitType.MAX_DRAWDOWN: Decimal("0.40"),  # 40%
                RiskLimitType.MAX_VOLATILITY: Decimal("0.50"),  # 50%
                RiskLimitType.VAR_LIMIT: capital * Decimal("0.12"),  # 12%
                RiskLimitType.EXPECTED_SHORTFALL: capital * Decimal("0.18"),  # 18%
                RiskLimitType.MAX_POSITION_SIZE: Decimal("0.20"),  # 20%
                RiskLimitType.MAX_LEVERAGE: Decimal("2.0"),  # 2x
                RiskLimitType.CONCENTRATION_LIMIT: Decimal("0.40"),  # 40%
            }

        logger.debug("Risk limits configured successfully")
        # Note: unreachable code due to validation above, but kept for safety
        return {}

    def calculate_var(
        self,
        returns: np.ndarray,
        capital: Decimal,
        confidence_levels: list[float] | None = None,
    ) -> VaRResult:
        """
        Calculate Value at Risk using historical simulation.

        Args:
            returns: Historical returns (daily)
            capital: Current portfolio value
            confidence_levels: Confidence levels for VaR

        Returns:
            VaRResult with VaR and Expected Shortfall
        """
        if confidence_levels is None:
            confidence_levels = [0.95, 0.99]

        if len(returns) < 2:
            # Not enough data
            return VaRResult(
                var_95=Decimal("0"),
                var_99=Decimal("0"),
                expected_shortfall_95=Decimal("0"),
                expected_shortfall_99=Decimal("0"),
                confidence_interval=(Decimal("0"), Decimal("0")),
                calculation_date=datetime.now(),
            )

        # Calculate daily VaR
        sorted_returns = np.sort(returns)

        var_95_idx = int((1 - 0.95) * len(sorted_returns))
        var_99_idx = int((1 - 0.99) * len(sorted_returns))

        var_95_daily = (
            sorted_returns[var_95_idx] if var_95_idx < len(sorted_returns) else sorted_returns[0]
        )
        var_99_daily = (
            sorted_returns[var_99_idx] if var_99_idx < len(sorted_returns) else sorted_returns[0]
        )

        # Convert to absolute value
        var_95 = abs(Decimal(str(var_95_daily)) * capital)
        var_99 = abs(Decimal(str(var_99_daily)) * capital)

        # Calculate Expected Shortfall (average of losses beyond VaR)
        es_95_losses = sorted_returns[:var_95_idx]
        es_99_losses = sorted_returns[:var_99_idx]

        es_95_daily = np.mean(es_95_losses) if len(es_95_losses) > 0 else var_95_daily
        es_99_daily = np.mean(es_99_losses) if len(es_99_losses) > 0 else var_99_daily

        expected_shortfall_95 = abs(Decimal(str(es_95_daily)) * capital)
        expected_shortfall_99 = abs(Decimal(str(es_99_daily)) * capital)

        # Calculate confidence interval using bootstrap
        ci_95 = self._bootstrap_var_ci(returns, capital, 0.95)

        return VaRResult(
            var_95=var_95,
            var_99=var_99,
            expected_shortfall_95=expected_shortfall_95,
            expected_shortfall_99=expected_shortfall_99,
            confidence_interval=ci_95,
            calculation_date=datetime.now(),
        )

    def _bootstrap_var_ci(
        self,
        returns: np.ndarray,
        capital: Decimal,
        confidence: float,
        n_bootstrap: int = 1000,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate confidence interval for VaR using bootstrap.

        Args:
            returns: Historical returns
            capital: Portfolio value
            confidence: Confidence level
            n_bootstrap: Number of bootstrap samples

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        var_estimates: list[float] = []

        for _ in range(n_bootstrap):
            # Bootstrap sample
            sample = np.random.choice(returns, size=len(returns), replace=True)
            sorted_sample = np.sort(sample)

            var_idx = int((1 - confidence) * len(sorted_sample))
            var_daily = sorted_sample[var_idx] if var_idx < len(sorted_sample) else sorted_sample[0]
            var_estimates.append(abs(var_daily))

        # Calculate percentile-based CI
        var_estimates_array = np.array(var_estimates)
        lower = np.percentile(var_estimates_array, 2.5)  # 2.5th percentile
        upper = np.percentile(var_estimates_array, 97.5)  # 97.5th percentile

        return (Decimal(str(lower)) * capital, Decimal(str(upper)) * capital)

    def calculate_drawdown_metrics(
        self,
        equity_curve: np.ndarray,
    ) -> DrawdownMetrics:
        """
        Calculate drawdown metrics.

        Args:
            equity_curve: Portfolio value over time

        Returns:
            DrawdownMetrics with various drawdown statistics
        """
        if len(equity_curve) < 2:
            return DrawdownMetrics(
                current_drawdown=Decimal("0"),
                max_drawdown=Decimal("0"),
                avg_drawdown=Decimal("0"),
                drawdown_duration=0,
                max_drawdown_duration=0,
                recovery_factor=0.0,
            )

        # Calculate running maximum
        running_max = np.maximum.accumulate(equity_curve)

        # Calculate drawdown
        drawdown = (equity_curve - running_max) / running_max

        # Current drawdown
        current_dd = float(drawdown[-1])

        # Maximum drawdown
        max_dd = float(np.min(drawdown))

        # Average drawdown (only from drawdown periods)
        drawdown_periods = drawdown[drawdown < 0]
        avg_dd = float(np.mean(drawdown_periods)) if len(drawdown_periods) > 0 else 0.0

        # Current drawdown duration
        current_dd_duration = 0
        for i in range(len(drawdown) - 1, -1, -1):
            if drawdown[i] < 0:
                current_dd_duration += 1
            else:
                break

        # Maximum drawdown duration
        max_dd_duration = 0
        current_duration = 0
        for dd in drawdown:
            if dd < 0:
                current_duration += 1
                max_dd_duration = max(max_dd_duration, current_duration)
            else:
                current_duration = 0

        # Recovery factor (approximate)
        # Months to recover from max drawdown
        recovery_factor = abs(max_dd) * 12 if max_dd < 0 else 0.0

        return DrawdownMetrics(
            current_drawdown=Decimal(str(current_dd)),
            max_drawdown=Decimal(str(max_dd)),
            avg_drawdown=Decimal(str(avg_dd)),
            drawdown_duration=current_dd_duration,
            max_drawdown_duration=max_dd_duration,
            recovery_factor=recovery_factor,
        )

    def check_risk_limits(
        self,
        current_values: dict[RiskLimitType, Decimal],
        risk_limits: dict[RiskLimitType, Decimal],
    ) -> list[RiskLimit]:
        """
        Check if current risk values are within limits.

        Args:
            current_values: Current risk metric values
            risk_limits: Risk limit thresholds

        Returns:
            List of RiskLimit objects
        """
        risk_limit_objects = []

        for limit_type, limit_value in risk_limits.items():
            current_value = current_values.get(limit_type, Decimal("0"))

            # Calculate utilization
            if limit_value > 0:
                utilization = float(current_value / limit_value)
            else:
                utilization = 0.0

            # Check if breached
            is_breached = current_value > limit_value

            risk_limit_objects.append(
                RiskLimit(
                    limit_type=limit_type,
                    limit_value=limit_value,
                    current_value=current_value,
                    utilization=min(1.0, utilization),
                    is_breached=is_breached,
                    timestamp=datetime.now(),
                )
            )

        return risk_limit_objects

    def allocate_risk_budget(
        self,
        total_risk_budget: Decimal,  # Target portfolio volatility
        asset_class_volatilities: dict[str, float],
        correlations: Optional[dict[tuple[str, str], float]] = None,
    ) -> RiskBudget:
        """
        Allocate risk budget across asset classes.

        Uses inverse volatility weighting for risk parity allocation.

        Args:
            total_risk_budget: Target portfolio volatility
            asset_class_volatilities: Volatility per asset class
            correlations: Correlation matrix (optional)

        Returns:
            RiskBudget with risk allocations
        """
        # Simple inverse volatility allocation
        inv_vols = {k: 1.0 / v for k, v in asset_class_volatilities.items()}
        total_inv_vol = sum(inv_vols.values())

        if total_inv_vol == 0:
            # Equal weight if no data
            n_assets = len(asset_class_volatilities)
            weight = 1.0 / n_assets if n_assets > 0 else 0.0
            weights = dict.fromkeys(asset_class_volatilities.keys(), weight)
        else:
            weights = {k: v / total_inv_vol for k, v in inv_vols.items()}

        # Calculate risk contribution (simplified)
        equity_risk = total_risk_budget * Decimal(str(weights.get("equity", 0.25)))
        fixed_income_risk = total_risk_budget * Decimal(str(weights.get("fixed_income", 0.25)))
        alternative_risk = total_risk_budget * Decimal(str(weights.get("alternatives", 0.25)))
        currency_risk = total_risk_budget * Decimal(str(weights.get("currency", 0.10)))
        concentration_risk = total_risk_budget * Decimal(str(weights.get("concentration", 0.15)))

        return RiskBudget(
            total_risk_budget=total_risk_budget,
            equity_risk=equity_risk,
            fixed_income_risk=fixed_income_risk,
            alternative_risk=alternative_risk,
            currency_risk=currency_risk,
            concentration_risk=concentration_risk,
        )

    def _initialize_stress_scenarios(self) -> dict[StressTestScenario, dict[str, float]]:
        """Initialize standard stress test scenarios."""
        return {
            StressTestScenario.MARKET_CRASH: {
                "equity_shock": -0.30,  # -30% equities
                "bond_shock": 0.05,  # +5% bonds (flight to safety)
                "vol_multiplier": 2.0,  # 2x volatility
            },
            StressTestScenario.VOLATILITY_SPIKE: {
                "equity_shock": 0.0,
                "bond_shock": 0.0,
                "vol_multiplier": 3.0,  # 3x volatility
            },
            StressTestScenario.SECTOR_ROTATION: {
                "equity_shock": 0.0,
                "sector_rotation": True,
                "vol_multiplier": 1.5,
            },
            StressTestScenario.LIQUIDITY_CRISIS: {
                "liquidity_spread_multiplier": 5.0,  # 5x bid-ask spreads
                "equity_shock": -0.15,
            },
            StressTestScenario.CORRELATION_BREAKDOWN: {
                "correlation_increase": 0.9,  # All correlations go to 0.9
                "diversification_failure": True,
            },
        }

    def run_stress_test(
        self,
        portfolio_value: Decimal,
        portfolio_positions: dict[str, Decimal],  # symbol -> weight
        scenario: StressTestScenario,
    ) -> Decimal:
        """
        Run stress test on portfolio.

        Args:
            portfolio_value: Current portfolio value
            portfolio_positions: Current positions (symbol -> weight)
            scenario: Stress test scenario

        Returns:
            Estimated loss under stress scenario
        """
        scenario_params = self._stress_scenarios.get(scenario, {})

        # Apply shocks
        total_loss = Decimal("0")

        for _symbol, weight in portfolio_positions.items():
            # Simplified - assume all positions are equities
            equity_shock = Decimal(str(scenario_params.get("equity_shock", 0.0)))

            # Calculate position loss
            position_value = portfolio_value * weight
            position_loss = position_value * abs(equity_shock)

            total_loss += position_loss

        return total_loss
