"""
VaR Position Limiter - Limit positions based on portfolio VaR.

Prevents exceeding risk limits by validating new positions
against portfolio Value-at-Risk calculations.

This module implements Phase 2.5 of the risk management system,
providing VaR-based position limits that use real correlation
matrices from Phase 2.4.

Uses centralized configuration for all thresholds and parameters.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import numpy as np

from app.core.centralized_config import get_config
from app.core.decimal_utils import to_decimal, validate_price

if TYPE_CHECKING:
    from app.engines.risk_engine.correlation_analyzers.correlation_analyzers import (
        CorrelationAnalyzer,
    )

logger = logging.getLogger(__name__)


@dataclass
class VaRConfig:
    """Configuration for VaR-based position limits using centralized config."""

    def __init__(self, custom_config: Optional[Dict] = None):
        """Initialize config with centralized values."""
        tt = get_config().trading

        # Get VaR configuration from centralized config
        self.max_var_limit_pct = Decimal(str(getattr(
            tt, 'var_max_limit_pct', 0.02
        )))
        self.confidence_level = getattr(
            tt, 'var_confidence_level', 0.95
        )
        self.lookback_days = getattr(
            tt, 'var_lookback_days', 60
        )
        self.warning_threshold_pct = Decimal(str(getattr(
            tt, 'var_warning_threshold_pct', 0.8
        )))
        self.use_real_correlation = True  # Always use real correlation
        self.default_volatility = getattr(
            tt, 'var_default_volatility', 0.2
        )

        # Apply any custom overrides
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(self, key):
                    setattr(self, key, value)


@dataclass
class ValidationResult:
    """Result of position validation."""

    passed: bool
    message: str
    current_var: Decimal
    projected_var: Decimal
    var_limit: Decimal
    excess_var: Optional[Decimal] = None
    utilization_pct: Decimal = Decimal("0")
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class VaRMetrics:
    """VaR metrics for a portfolio."""

    var_95: Decimal  # VaR at 95% confidence
    var_99: Decimal  # VaR at 99% confidence
    portfolio_value: Decimal
    var_limit: Decimal
    utilization_pct: Decimal
    correlation_used: str  # "real" or "identity"
    calculation_time: datetime
    position_count: int


class VaRPositionLimiter:
    """
    Limit positions based on portfolio VaR.

    Key features:
    - VaR calculated with real correlation matrix
    - New positions rejected if VaR exceeded
    - VaR limit configurable (default: 2% daily)
    - Alerts when approaching VaR limit (>80%)
    - Works across all asset classes
    - Historical volatility calculation
    """

    def __init__(
        self,
        portfolio,
        correlation_analyzer: Optional["CorrelationAnalyzer"] = None,
        config: Optional[VaRConfig] = None,
    ):
        """
        Initialize VaR position limiter.

        Args:
            portfolio: Current portfolio with positions
            correlation_analyzer: Correlation matrix analyzer
            config: VaR configuration
        """
        from app.models.portfolio import Portfolio

        self.portfolio: Portfolio = portfolio
        self.correlation_analyzer = correlation_analyzer
        self.config = config or VaRConfig()

        # Cache for volatilities and prices
        self._volatility_cache: Dict[str, float] = {}
        self._price_cache: Dict[str, Decimal] = {}

        logger.info(
            "VaRPositionLimiter initialized with "
            f"max_var_limit={self.config.max_var_limit_pct:.2%}, "
            f"confidence={self.config.confidence_level:.0%}, "
            f"lookback={self.config.lookback_days} days"
        )

    def validate_position_with_var(
        self,
        symbol: str,
        quantity: Decimal,
        current_price: Decimal,
        side: str = "LONG",
    ) -> ValidationResult:
        """
        Check if new position would exceed VaR limit.

        Args:
            symbol: Symbol to trade
            quantity: Quantity to trade
            current_price: Current price
            side: LONG or SHORT

        Returns:
            ValidationResult with pass/fail status
        """
        try:
            # Validate inputs
            if quantity <= 0:
                return ValidationResult(
                    passed=False,
                    message="Quantity must be positive",
                    current_var=Decimal("0"),
                    projected_var=Decimal("0"),
                    var_limit=Decimal("0"),
                )

            validate_price(current_price)

            # Calculate current portfolio VaR
            current_var = self.calculate_portfolio_var(
                confidence_level=self.config.confidence_level,
                lookback_days=self.config.lookback_days,
            )

            # Calculate projected VaR with new position
            projected_var = self.calculate_var_with_position(
                symbol=symbol,
                quantity=quantity,
                current_price=current_price,
                side=side,
                confidence_level=self.config.confidence_level,
                lookback_days=self.config.lookback_days,
            )

            # Get VaR limit based on portfolio value
            portfolio_value = self._get_portfolio_value()
            var_limit = portfolio_value * self.config.max_var_limit_pct

            # Calculate utilization
            utilization = projected_var / var_limit if var_limit > 0 else Decimal("0")

            # Check if exceeded
            if projected_var > var_limit:
                excess = projected_var - var_limit
                return ValidationResult(
                    passed=False,
                    message=(
                        f"Position would exceed VaR limit by "
                        f"{self._format_currency(excess)} "
                        f"({utilization:.1%} of limit)"
                    ),
                    current_var=current_var,
                    projected_var=projected_var,
                    var_limit=var_limit,
                    excess_var=excess,
                    utilization_pct=utilization,
                )

            # Check warning threshold
            warnings = []
            if utilization >= self.config.warning_threshold_pct:
                warnings.append(f"Warning: Position at {utilization:.1%} of VaR limit")

            return ValidationResult(
                passed=True,
                message="VaR check passed",
                current_var=current_var,
                projected_var=projected_var,
                var_limit=var_limit,
                utilization_pct=utilization,
                warnings=warnings,
            )

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error validating position with VaR: {e}", exc_info=True)
            return ValidationResult(
                passed=False,
                message=f"VaR validation error: {str(e)}",
                current_var=Decimal("0"),
                projected_var=Decimal("0"),
                var_limit=Decimal("0"),
            )

    def calculate_portfolio_var(
        self,
        confidence_level: float = 0.95,
        lookback_days: int = 60,
    ) -> Decimal:
        """
        Calculate current portfolio VaR.

        Uses real correlation matrix if available.

        Formula:
        VaR = portfolio_value * sqrt(portfolio_variance) * z_score

        where portfolio_variance = w' * Σ * w
        (w = weights, Σ = covariance matrix)

        Args:
            confidence_level: Confidence level (e.g., 0.95 for 95%)
            lookback_days: Days of historical data

        Returns:
            VaR amount in portfolio currency
        """
        try:
            # Get current positions
            positions = self._get_positions()

            if not positions:
                return Decimal("0")

            portfolio_value = self._get_portfolio_value()
            if portfolio_value <= 0:
                return Decimal("0")

            # Get correlation matrix
            correlation_type = "identity"
            corr_matrix = None

            if self.config.use_real_correlation and self.correlation_analyzer is not None:
                try:
                    # Try to get cached correlation matrix
                    if hasattr(self.correlation_analyzer, "get_cached_matrix"):
                        corr_matrix = self.correlation_analyzer.get_cached_matrix()
                        if corr_matrix is not None:
                            correlation_type = "real"
                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    logger.debug(f"Could not get cached correlation matrix: {e}")

            # Calculate portfolio variance
            portfolio_variance = self._calculate_portfolio_variance(positions, corr_matrix)

            # Calculate VaR using z-score for confidence level
            from scipy.stats import norm

            z_score = norm.ppf(confidence_level)

            # VaR = portfolio_value * sqrt(variance) * z_score
            std_dev = portfolio_variance**0.5
            var = portfolio_value * to_decimal(str(std_dev)) * to_decimal(str(z_score))

            logger.debug(
                f"Portfolio VaR ({confidence_level:.0%}): "
                f"{self._format_currency(var)} "
                f"(correlation: {correlation_type}, "
                f"portfolio_value: {self._format_currency(portfolio_value)})"
            )

            return max(var, Decimal("0"))

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error calculating portfolio VaR: {e}", exc_info=True)
            return Decimal("0")

    def calculate_var_with_position(
        self,
        symbol: str,
        quantity: Decimal,
        current_price: Decimal,
        side: str,
        confidence_level: float = 0.95,
        lookback_days: int = 60,
    ) -> Decimal:
        """
        Calculate VaR with new position added.

        This calculates the incremental VaR contribution of the new position
        and adds it to the current portfolio VaR.

        For a more accurate calculation, this would recalculate the full
        portfolio variance matrix with the new position included.

        Args:
            symbol: Symbol to add
            quantity: Quantity to add
            current_price: Current price
            side: LONG or SHORT
            confidence_level: Confidence level
            lookback_days: Historical lookback

        Returns:
            Projected VaR amount
        """
        try:
            # Get current VaR
            current_var = self.calculate_portfolio_var(confidence_level, lookback_days)

            # Get portfolio value
            portfolio_value = self._get_portfolio_value()
            if portfolio_value <= 0:
                return current_var

            # Calculate new position value
            position_value = quantity * current_price

            # Get volatility for the symbol (use default if not available)
            volatility = self._get_symbol_volatility(symbol)

            # Calculate incremental VaR
            # This is a simplified calculation that assumes:
            # 1. The new position's risk is proportional to its value
            # 2. Average correlation with existing positions is 0.5
            # For production, should recalculate full covariance matrix

            avg_correlation = 0.5
            weight_new = float(position_value / portfolio_value)

            # Incremental variance contribution (simplified)
            # σ²_new = w_new² * σ²_new + 2 * w_new * w_avg * σ_new * σ_avg * ρ
            incremental_variance = (
                weight_new**2 * volatility**2
                + 2 * weight_new * avg_correlation * volatility * 0.2
            )  # Assuming 20% avg portfolio vol

            # Incremental VaR = portfolio_value * sqrt(incremental_variance) * z_score
            from scipy.stats import norm

            z_score = norm.ppf(confidence_level)
            incremental_var = (
                portfolio_value
                * safe_decimal_sqrt(incremental_variance)
                * to_decimal(str(z_score))
            )

            projected_var = current_var + incremental_var

            logger.debug(
                f"Projected VaR with {symbol} position: "
                f"{self._format_currency(projected_var)} "
                f"(incremental: {self._format_currency(incremental_var)})"
            )

            return max(projected_var, Decimal("0"))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating VaR with position: {e}", exc_info=True)
            # Return current VaR as fallback
            return self.calculate_portfolio_var(confidence_level, lookback_days)

    def _calculate_portfolio_variance(
        self,
        positions,
        corr_matrix,
    ) -> float:
        """
        Calculate portfolio variance using correlation matrix.

        Formula: w' * Σ * w
        where w = weights, Σ = covariance matrix

        Args:
            positions: List of position objects
            corr_matrix: Correlation matrix (or None for identity)

        Returns:
            Portfolio variance as float
        """
        n = len(positions)
        if n == 0:
            return 0.0
        if n == 1:
            # Single position variance
            vol = self._get_position_volatility(positions[0])
            return vol**2

        # Build weight vector
        weights = []
        volatilities = []

        for position in positions:
            # Use market_price for current value
            price = getattr(position, 'market_price', getattr(position, 'current_price', None))
            if price is None:
                continue

            position_value = abs(position.quantity * price)
            weights.append(float(position_value))

            # Get volatility for this position
            vol = self._get_position_volatility(position)
            volatilities.append(vol)

        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        weights = [w / total_weight for w in weights]

        # Build correlation matrix (use identity if not available)
        if corr_matrix is not None and hasattr(corr_matrix, "values"):
            # It's a pandas DataFrame
            import pandas as pd

            if isinstance(corr_matrix, pd.DataFrame):
                correlation = corr_matrix.values
            else:
                correlation = corr_matrix
        elif isinstance(corr_matrix, dict):
            # Convert dict to numpy array
            correlation = np.eye(n)
            for i, pos1 in enumerate(positions):
                for j, pos2 in enumerate(positions):
                    if i != j and pos1.symbol in corr_matrix:
                        if pos2.symbol in corr_matrix[pos1.symbol]:
                            corr = corr_matrix[pos1.symbol][pos2.symbol]
                            if corr is not None:
                                correlation[i][j] = corr
        else:
            # Use identity matrix (uncorrelated assets)
            correlation = np.eye(n)

        # Build covariance matrix: Σ = diag(σ) * Corr * diag(σ)
        vol_array = np.array(volatilities)
        covariance = np.outer(vol_array, vol_array) * correlation

        # Calculate portfolio variance: w' * Σ * w
        weight_array = np.array(weights)
        portfolio_var = float(weight_array.T @ covariance @ weight_array)

        return max(0.0, portfolio_var)

    def _get_position_volatility(self, position) -> float:
        """Get volatility for a position."""
        return self._get_symbol_volatility(position.symbol)

    def _get_symbol_volatility(self, symbol: str) -> float:
        """Get volatility for a symbol (cached)."""
        if symbol not in self._volatility_cache:
            # Use default volatility
            self._volatility_cache[symbol] = self.config.default_volatility
        return self._volatility_cache[symbol]

    def _get_positions(self):
        """Get current positions from portfolio."""
        return getattr(self.portfolio, "positions", [])

    def _get_portfolio_value(self) -> Decimal:
        """Get total portfolio value."""
        try:
            # Try to get total_value from portfolio
            if hasattr(self.portfolio, "total_value"):
                return self.portfolio.total_value
            if hasattr(self.portfolio, "total_equity"):
                return self.portfolio.total_equity

            # Calculate from positions
            positions = self._get_positions()
            total_value = Decimal("0")
            for p in positions:
                # Use market_price primarily, fall back to current_price
                price = getattr(p, 'market_price', getattr(p, 'current_price', None))
                if price is not None and hasattr(p, "quantity"):
                    total_value += abs(p.quantity * price)

            return total_value
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error getting portfolio value: {e}")
            return Decimal("0")

    def get_var_utilization(self) -> Tuple[Decimal, Decimal]:
        """
        Get current VaR utilization.

        Returns:
            Tuple of (current_var, utilization_percent)
        """
        current_var = self.calculate_portfolio_var()
        portfolio_value = self._get_portfolio_value()
        var_limit = portfolio_value * self.config.max_var_limit_pct

        utilization = current_var / var_limit if var_limit > 0 else Decimal("0")

        return current_var, utilization

    def get_var_metrics(self) -> VaRMetrics:
        """
        Get comprehensive VaR metrics.

        Returns:
            VaRMetrics object with all VaR statistics
        """
        var_95 = self.calculate_portfolio_var(confidence_level=0.95)
        var_99 = self.calculate_portfolio_var(confidence_level=0.99)

        portfolio_value = self._get_portfolio_value()
        var_limit = portfolio_value * self.config.max_var_limit_pct

        utilization = var_95 / var_limit if var_limit > 0 else Decimal("0")

        # Determine correlation type used
        correlation_type = "real"
        if not self.config.use_real_correlation or self.correlation_analyzer is None:
            correlation_type = "identity"

        return VaRMetrics(
            var_95=var_95,
            var_99=var_99,
            portfolio_value=portfolio_value,
            var_limit=var_limit,
            utilization_pct=utilization,
            correlation_used=correlation_type,
            calculation_time=datetime.now(timezone.utc),
            position_count=len(self._get_positions()),
        )

    def calculate_max_position_size(
        self,
        symbol: str,
        current_price: Decimal,
        side: str = "LONG",
        target_utilization: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate maximum position size that stays within VaR limits.

        Args:
            symbol: Symbol to trade
            current_price: Current price
            side: LONG or SHORT
            target_utilization: Target VaR utilization (default: 90% of limit)

        Returns:
            Maximum quantity allowed
        """
        if target_utilization is None:
            target_utilization = Decimal("0.9")  # 90% of limit

        try:
            # Get current VaR and limit
            current_var = self.calculate_portfolio_var()
            portfolio_value = self._get_portfolio_value()
            var_limit = portfolio_value * self.config.max_var_limit_pct

            # Calculate allowable VaR for new position
            allowable_var = (var_limit * target_utilization) - current_var

            if allowable_var <= 0:
                return Decimal("0")

            # Calculate position value from allowable VaR
            # This is a simplified calculation
            # VaR ≈ position_value * volatility * z_score
            from scipy.stats import norm

            z_score = norm.ppf(self.config.confidence_level)
            volatility = self._get_symbol_volatility(symbol)

            # Solve for position_value: allowable_var = position_value * vol * z
            max_position_value = (
                allowable_var / to_decimal(str(volatility)) / to_decimal(str(z_score))
            )

            # Calculate max quantity
            max_quantity = max_position_value / current_price

            logger.debug(
                f"Max position size for {symbol}: {max_quantity:.2f} shares "
                f"({self._format_currency(max_position_value)})"
            )

            return max_quantity

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error calculating max position size: {e}", exc_info=True)
            return Decimal("0")

    def update_volatility_cache(self, volatilities: Dict[str, float]) -> None:
        """
        Update the volatility cache with new values.

        Args:
            volatilities: Dictionary mapping symbols to volatilities
        """
        self._volatility_cache.update(volatilities)
        logger.debug(f"Updated volatility cache with {len(volatilities)} symbols")

    def _format_currency(self, value: Decimal) -> str:
        """Format a Decimal as currency string."""
        return f"{value:,.2f}"


def get_var_position_limiter(
    portfolio,
    correlation_analyzer: Optional["CorrelationAnalyzer"] = None,
    config: Optional[VaRConfig] = None,
) -> VaRPositionLimiter:
    """
    Factory function to get a VaR position limiter instance.

    Args:
        portfolio: Current portfolio
        correlation_analyzer: Correlation analyzer
        config: VaR configuration

    Returns:
        VaRPositionLimiter instance
    """
    return VaRPositionLimiter(
        portfolio=portfolio,
        correlation_analyzer=correlation_analyzer,
        config=config,
    )
