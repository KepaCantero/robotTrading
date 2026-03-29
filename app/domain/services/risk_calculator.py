"""
Risk Calculator Domain Service - Risk metrics calculations

RiskCalculator provides domain logic for calculating risk metrics
for portfolios and positions.

Reference: Rule 05-architecture.md, Rule 03-solid-principles.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np

from app.shared.config.centralized_config import get_config

if TYPE_CHECKING:
    from app.domain.entities.portfolio import Portfolio
    from app.domain.entities.position import Position

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Risk metrics for a portfolio or position."""

    # Portfolio value for percentage calculations
    portfolio_value: Decimal  # Total portfolio value used for VaR calculations

    # Value at Risk metrics
    var_95: Decimal  # Value at Risk at 95% confidence
    var_99: Decimal  # Value at Risk at 99% confidence

    # Volatility metrics
    daily_volatility: Decimal
    annualized_volatility: Decimal

    # Drawdown metrics
    max_drawdown: Decimal
    avg_drawdown: Decimal

    # Concentration metrics
    concentration: Decimal  # Highest position concentration
    herfindahl_index: Decimal  # Portfolio concentration index

    # Risk limits
    utilisation: Decimal  # Risk utilisation as % of limits


class RiskCalculator:
    """
    Domain service for calculating risk metrics.

    Provides pure risk calculation logic without external dependencies.
    """

    def __init__(self, risk_free_rate: Decimal | None = None):
        """
        Initialize risk calculator.

        Args:
            risk_free_rate: Risk-free rate for Sharpe ratio calculation (default: from CentralizedConfig)
        """
        self._risk_free_rate = (
            risk_free_rate
            if risk_free_rate is not None
            else get_config().backtesting.default_risk_free_rate
        )
        logger.debug(
            "RiskCalculator initialized",
            extra={"risk_free_rate": str(self._risk_free_rate)},
        )

    def calculate_portfolio_risk(self, portfolio: Portfolio) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics for a portfolio.

        Args:
            portfolio: Portfolio to analyze

        Returns:
            RiskMetrics object with calculated metrics
        """
        logger.info(
            "Calculating portfolio risk",
            extra={"portfolio_id": getattr(portfolio, "id", "unknown")},
        )

        # Get position values
        position_values = [pos.get_value().amount for pos in portfolio.get_open_positions()]
        total_value = portfolio.get_total_value().amount

        if total_value == 0 or not position_values:
            logger.warning(
                "Empty portfolio or zero value - returning zero metrics",
                extra={"total_value": str(total_value), "position_count": len(position_values)},
            )
            return RiskMetrics(
                portfolio_value=Decimal("0"),
                var_95=Decimal("0"),
                var_99=Decimal("0"),
                daily_volatility=Decimal("0"),
                annualized_volatility=Decimal("0"),
                max_drawdown=Decimal("0"),
                avg_drawdown=Decimal("0"),
                concentration=Decimal("0"),
                herfindahl_index=Decimal("0"),
                utilisation=Decimal("0"),
            )

        # Calculate concentration metrics
        concentration = self._calculate_concentration(portfolio)
        herfindahl = self._calculate_herfindahl(portfolio)

        # Calculate volatility (simplified - uses position weights)
        weights = [v / total_value for v in position_values]
        daily_vol = self._estimate_portfolio_volatility(weights, position_values)
        annual_vol = daily_vol * Decimal(
            str(np.sqrt(get_config().backtesting.trading_days_per_year))
        )

        # Calculate VaR (simplified parametric VaR)
        var_95 = self._calculate_var(total_value, daily_vol, Decimal("1.65"))
        var_99 = self._calculate_var(total_value, daily_vol, Decimal("2.33"))

        # Calculate drawdown metrics (placeholder - needs historical data)
        max_dd = self._estimate_max_drawdown(weights)
        avg_dd = max_dd / Decimal("2")  # Simplified

        # Calculate risk utilisation
        utilisation = self._calculate_risk_utilisation(portfolio)

        logger.info(
            "Portfolio risk calculated",
            extra={
                "var_95": str(var_95),
                "var_99": str(var_99),
                "daily_volatility": str(daily_vol),
                "utilisation": str(utilisation),
            },
        )

        return RiskMetrics(
            portfolio_value=total_value,
            var_95=var_95,
            var_99=var_99,
            daily_volatility=daily_vol,
            annualized_volatility=annual_vol,
            max_drawdown=max_dd,
            avg_drawdown=avg_dd,
            concentration=concentration,
            herfindahl_index=herfindahl,
            utilisation=utilisation,
        )

    def calculate_position_risk(
        self,
        position: Position,
        portfolio_value: Decimal,
    ) -> dict[str, Decimal]:
        """
        Calculate risk metrics for a single position.

        Args:
            position: Position to analyze
            portfolio_value: Total portfolio value for context

        Returns:
            Dictionary of risk metrics
        """
        position_value = position.get_value().amount

        # Position as percentage of portfolio (with zero-division protection)
        position_pct = self._safe_divide(position_value * Decimal("100"), portfolio_value)

        # Position risk (simplified - uses unrealized P&L as proxy)
        unrealized_pnl = position.get_unrealized_pnl().amount
        risk_amount = (
            abs(unrealized_pnl) if unrealized_pnl < 0 else position_value * Decimal("0.05")
        )

        return {
            "position_value": position_value,
            "position_pct": position_pct,
            "risk_amount": risk_amount,
            "unrealized_pnl": unrealized_pnl,
            "pnl_percent": position.get_pnl_percent(),
        }

    def calculate_sharpe_ratio(
        self,
        returns: list[Decimal],
        annualized: bool = True,
    ) -> Decimal:
        """
        Calculate Sharpe ratio.

        Args:
            returns: List of returns
            annualized: Whether to annualize the ratio

        Returns:
            Sharpe ratio
        """
        if not returns:
            return Decimal("0")

        # Convert to numpy for calculation
        returns_arr = np.array([float(r) for r in returns])

        if len(returns_arr) < 2:
            return Decimal("0")

        mean_return = Decimal(str(np.mean(returns_arr)))
        std_return = Decimal(str(np.std(returns_arr, ddof=1)))

        if std_return == 0:
            return Decimal("0")

        sharpe = (mean_return - self._risk_free_rate) / std_return

        if annualized:
            sharpe *= Decimal(str(np.sqrt(get_config().backtesting.trading_days_per_year)))

        return sharpe

    def calculate_sortino_ratio(
        self,
        returns: list[Decimal],
        target_return: Decimal | None = None,
        annualized: bool = True,
    ) -> Decimal:
        """
        Calculate Sortino ratio (downside deviation).

        Args:
            returns: List of returns
            target_return: Target/minimum acceptable return
            annualized: Whether to annualize the ratio

        Returns:
            Sortino ratio
        """
        if target_return is None:
            target_return = Decimal("0")
        if not returns:
            return Decimal("0")

        returns_arr = np.array([float(r) for r in returns])

        if len(returns_arr) < 2:
            return Decimal("0")

        mean_return = Decimal(str(np.mean(returns_arr)))

        # Calculate downside deviation
        downside_returns = [r for r in returns if r < target_return]

        if not downside_returns:
            return get_config().backtesting.sortino_infinite_value  # Infinite Sortino (no downside)

        downside_arr = np.array([float(r - target_return) for r in downside_returns])
        downside_deviation = Decimal(str(np.sqrt(np.mean(downside_arr**2))))

        if downside_deviation == 0:
            return get_config().backtesting.sortino_infinite_value

        sortino = (mean_return - target_return) / downside_deviation

        if annualized:
            sortino *= Decimal(str(np.sqrt(get_config().backtesting.trading_days_per_year)))

        return sortino

    def calculate_beta(
        self,
        asset_returns: list[Decimal],
        market_returns: list[Decimal],
    ) -> Decimal:
        """
        Calculate beta (asset sensitivity to market).

        Args:
            asset_returns: Asset returns
            market_returns: Market/benchmark returns

        Returns:
            Beta value
        """
        if len(asset_returns) != len(market_returns) or len(asset_returns) < 2:
            return Decimal("1.0")  # Default beta

        asset_arr = np.array([float(r) for r in asset_returns])
        market_arr = np.array([float(r) for r in market_returns])

        # Calculate covariance and variance
        covariance = np.cov(asset_arr, market_arr)[0, 1]
        market_variance = np.var(market_arr, ddof=1)

        if market_variance == 0:
            return Decimal("1.0")

        beta = Decimal(str(covariance / market_variance))
        return beta

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    @staticmethod
    def _safe_divide(
        numerator: Decimal, denominator: Decimal, default: Decimal | None = None
    ) -> Decimal:
        """
        Perform safe division with zero-division protection.

        Args:
            numerator: Value to divide
            denominator: Value to divide by
            default: Default value if denominator is zero

        Returns:
            Result of division or default value
        """
        if default is None:
            default = Decimal("0")
        if denominator == 0:
            return default
        try:
            return numerator / denominator
        except ArithmeticError:
            return default

    def _calculate_concentration(self, portfolio: Portfolio) -> Decimal:
        """Calculate highest position concentration."""
        if not portfolio.get_open_positions():
            return Decimal("0")

        _max_symbol, max_conc = portfolio.get_max_concentration()
        return max_conc

    def _calculate_herfindahl(self, portfolio: Portfolio) -> Decimal:
        """
        Calculate Herfindahl-Hirschman Index (HHI).

        HHI measures portfolio concentration.
        Lower values indicate more diversification.
        """
        positions = portfolio.get_open_positions()
        if not positions:
            return Decimal("0")

        total_value = portfolio.get_total_value().amount
        if total_value == 0:
            return Decimal("0")

        # Calculate sum of squared weights
        hhi = Decimal("0")
        for position in positions:
            weight = position.get_value().amount / total_value
            hhi += weight**2

        return hhi

    def _estimate_portfolio_volatility(
        self,
        weights: list[Decimal],
        values: list[Decimal],
    ) -> Decimal:
        """
        Estimate portfolio volatility from weights and values.

        Simplified calculation - assumes no correlation for robustness.
        """
        if not weights:
            return Decimal("0")

        # Use weighted average as proxy (simplified)
        total_weight = sum(weights)
        if total_weight == 0:
            return Decimal("0")

        # Use default daily volatility from config (conservative)
        position_vol = float(get_config().backtesting.default_daily_volatility)

        # Portfolio vol = weighted average * sqrt(n) for uncorrelated
        n = len(weights)
        portfolio_vol = (
            Decimal(str(position_vol)) * Decimal(str(np.sqrt(n))) if n > 0 else Decimal("0")
        )

        return portfolio_vol

    def _calculate_var(
        self,
        portfolio_value: Decimal,
        volatility: Decimal,
        z_score: Decimal,
    ) -> Decimal:
        """
        Calculate parametric Value at Risk.

        Args:
            portfolio_value: Portfolio value
            volatility: Daily volatility
            z_score: Z-score for confidence level

        Returns:
            VaR amount
        """
        return portfolio_value * volatility * z_score

    def _estimate_max_drawdown(self, weights: list[Decimal]) -> Decimal:
        """
        Estimate maximum drawdown from position weights.

        Simplified - assumes worst case for largest position.
        """
        if not weights:
            return Decimal("0")

        max_weight = max(weights)
        # Use default volatility for drawdown estimation from config
        return max_weight * get_config().backtesting.default_volatility_for_dd

    def _calculate_risk_utilisation(self, portfolio: Portfolio) -> Decimal:
        """
        Calculate risk utilisation as percentage of limits.

        Returns how much of risk limits are being used.
        """
        max_exposure = portfolio.risk_parameters.max_portfolio_exposure
        current_exposure = portfolio.get_gross_exposure()

        utilisation = self._safe_divide(current_exposure * Decimal("100"), max_exposure)
        return min(utilisation, Decimal("100"))  # Cap at 100%

    def get_risk_summary(self, metrics: RiskMetrics) -> dict[str, str]:
        """
        Get human-readable risk summary.

        Args:
            metrics: Calculated risk metrics

        Returns:
            Dictionary of risk assessment summaries
        """
        # Risk level classification
        if metrics.annualized_volatility < Decimal("0.15"):
            vol_level = "Low"
        elif metrics.annualized_volatility < Decimal("0.25"):
            vol_level = "Medium"
        else:
            vol_level = "High"

        # Concentration assessment
        if metrics.concentration < Decimal("10"):
            conc_level = "Well diversified"
        elif metrics.concentration < Decimal("25"):
            conc_level = "Moderately concentrated"
        else:
            conc_level = "Highly concentrated"

        # Utilisation assessment
        if metrics.utilisation < Decimal("50"):
            util_level = "Low utilisation"
        elif metrics.utilisation < Decimal("80"):
            util_level = "Moderate utilisation"
        else:
            util_level = "High utilisation"

        # Calculate VaR as percentage of portfolio value (with zero-division protection)
        var_95_percentage = self._safe_divide(
            metrics.var_95 * Decimal("100"), metrics.portfolio_value
        )

        return {
            "volatility_level": vol_level,
            "concentration_level": conc_level,
            "utilisation_level": util_level,
            "var_95_pct": f"{var_95_percentage:.1f}%",
        }
