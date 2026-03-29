"""
Market Impact Model - Almgren-Chriss Implementation (FASE 5.2)

This module implements the Almgren-Chriss market impact model for
realistic execution simulation.

The Almgren-Chriss model decomposes market impact into:
1. Permanent impact: Price shift that persists after execution
2. Temporary impact: Price movement during execution that recovers

Key equations:
- Permanent impact: gamma * (X / ADV)
- Temporary impact: eta * sigma * sqrt(X / ADV)
- Total impact: permanent + temporary

Where:
- gamma: Permanent impact coefficient
- eta: Temporary impact coefficient
- X: Order size
- ADV: Average daily volume
- sigma: Volatility

Reference:
    Almgren, R., & Chriss, N. (2001). "Optimal Execution of
    Portfolio Transactions." Journal of Risk, 3(2), 5-39.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ImpactType(str, Enum):
    """Type of market impact."""

    PERMANENT = "permanent"  # Permanent price shift
    TEMPORARY = "temporary"  # Temporary price movement that recovers
    TOTAL = "total"  # Combined permanent + temporary


@dataclass(frozen=True)
class AlmgrenChrissConfig:
    """
    Configuration for Almgren-Chriss market impact model.

    These coefficients are typically calibrated from historical execution data.

    Attributes:
        permanent_coef: Permanent impact coefficient (gamma)
        temporary_coef: Temporary impact coefficient (eta)
        volatility_exponent: Exponent for volatility (default 0.5 = sqrt)
        adv_exponent: Exponent for order size vs ADV (default 0.5 = sqrt)
        max_impact_bps: Maximum impact to apply (safety limit)
    """

    # Impact coefficients (calibrated from historical data)
    permanent_coef: Decimal = Decimal("0.05")  # gamma: 5 bps per 1% ADV
    temporary_coef: Decimal = Decimal("0.1")  # eta: 10 bps per sqrt(1% ADV)

    # Exponents
    volatility_exponent: Decimal = Decimal("0.5")  # Square root
    adv_exponent: Decimal = Decimal("0.5")  # Square root

    # Safety limits
    max_impact_bps: Decimal = Decimal("100")  # Max 100 bps (1%) impact


@dataclass(frozen=True)
class MarketImpact:
    """
    Result of market impact calculation.

    Attributes:
        temporary_impact_bps: Temporary price impact (in bps)
        permanent_impact_bps: Permanent price shift (in bps)
        total_impact_bps: Combined impact (in bps)
        estimated_price: Price after accounting for impact
        temporary_impact_dollars: Temporary impact in dollar terms
        permanent_impact_dollars: Permanent impact in dollar terms
        total_impact_dollars: Total impact in dollar terms
    """

    temporary_impact_bps: Decimal
    permanent_impact_bps: Decimal
    total_impact_bps: Decimal
    estimated_price: Decimal
    temporary_impact_dollars: Decimal
    permanent_impact_dollars: Decimal
    total_impact_dollars: Decimal

    @property
    def temporary_price_adjustment(self) -> Decimal:
        """Temporary impact as decimal adjustment."""
        return self.temporary_impact_bps / Decimal("10000")

    @property
    def permanent_price_adjustment(self) -> Decimal:
        """Permanent impact as decimal adjustment."""
        return self.permanent_impact_bps / Decimal("10000")

    @property
    def total_price_adjustment(self) -> Decimal:
        """Total impact as decimal adjustment."""
        return self.total_impact_bps / Decimal("10000")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "temporary_impact_bps": float(self.temporary_impact_bps),
            "permanent_impact_bps": float(self.permanent_impact_bps),
            "total_impact_bps": float(self.total_impact_bps),
            "estimated_price": float(self.estimated_price),
            "temporary_impact_dollars": float(self.temporary_impact_dollars),
            "permanent_impact_dollars": float(self.permanent_impact_dollars),
            "total_impact_dollars": float(self.total_impact_dollars),
        }


@dataclass(frozen=True)
class ImpactConfig:
    """
    Configuration for market impact model.

    This is a wrapper around AlmgrenChrissConfig for easier integration.
    """

    temporary_coef: Decimal = Decimal("0.1")
    permanent_coef: Decimal = Decimal("0.05")
    max_impact_bps: Decimal = Decimal("100")

    def to_almgren_chriss_config(self) -> AlmgrenChrissConfig:
        """Convert to AlmgrenChrissConfig."""
        return AlmgrenChrissConfig(
            permanent_coef=self.permanent_coef,
            temporary_coef=self.temporary_coef,
            max_impact_bps=self.max_impact_bps,
        )


class MarketImpactModel:
    """
    Almgren-Chriss Market Impact Model.

    This model calculates market impact for order execution:

    **Permanent Impact:**
    Represents the permanent price shift due to information content
    of the trade. It persists after execution completes.

    Formula: permanent_impact = gamma * (order_size / ADV)

    Where:
    - gamma (gamma): Permanent impact coefficient (typically 1-10 bps per %ADV)
    - order_size: Size of the order in dollars
    - ADV: Average daily volume in dollars

    **Temporary Impact:**
    Represents the price movement during execution that recovers
    after the order is completed. It's caused by liquidity demand.

    Formula: temporary_impact = eta * sigma * sqrt(order_size / ADV)

    Where:
    - eta (eta): Temporary impact coefficient (typically 5-50 bps)
    - sigma (sigma): Volatility (annualized)
    - order_size/ADV: Order size as fraction of daily volume

    **Total Impact:**
    total_impact = permanent_impact + temporary_impact

    Example:
        model = MarketImpactModel()

        # Buy 10,000 shares at $150 = $1.5M
        # Stock has $50M ADV and 20% volatility
        impact = model.calculate_impact(
            order_size=Decimal("1500000"),  # $1.5M
            adv=Decimal("50000000"),  # $50M
            volatility=Decimal("0.20"),  # 20%
            side="buy"
        )

        logger.debug(f"Total impact: {impact.total_impact_bps} bps")
        logger.debug(f"Estimated fill price: ${impact.estimated_price}")
    """

    # Typical coefficient ranges (from empirical studies)
    PERMANENT_COEF_RANGE = (Decimal("0.01"), Decimal("0.10"))  # 1-10 bps per %ADV
    TEMPORARY_COEF_RANGE = (Decimal("0.05"), Decimal("0.50"))  # 5-50 bps

    # Volatility scaling (convert annual to daily)
    # For Almgren-Chriss: daily_vol = annual_vol / sqrt(252)
    ANNUAL_TO_DAILY_VOL_FACTOR = Decimal("1") / (Decimal("252").sqrt())

    def __init__(self, config: ImpactConfig | None = None):
        """
        Initialize market impact model.

        Args:
            config: Impact configuration (uses defaults if not provided)
        """
        self.config = config or ImpactConfig()
        self.ac_config = self.config.to_almgren_chriss_config()

    def calculate_permanent_impact(
        self,
        order_size: Decimal,
        adv: Decimal,
        side: str,
    ) -> Decimal:
        """
        Calculate permanent market impact.

        Permanent impact is the price shift that persists after execution.
        It represents the information content of the trade.

        Formula: impact = gamma * (order_size / ADV)

        Args:
            order_size: Size of the order in dollars (must be > 0)
            adv: Average daily volume in dollars (must be > 0)
            side: "buy" or "sell"

        Returns:
            Permanent impact in basis points

        Raises:
            ValueError: If parameters are invalid
        """
        if order_size <= 0:
            raise ValueError(f"Order size must be positive, got {order_size}")

        if adv <= 0:
            raise ValueError(f"ADV must be positive, got {adv}")

        side_lower = side.lower()
        if side_lower not in ("buy", "sell"):
            raise ValueError(f"Side must be 'buy' or 'sell', got '{side}'")

        # Calculate order size as fraction of ADV
        order_fraction = order_size / adv

        # Apply permanent impact formula: gamma * (order_size / ADV)
        # Result is in decimal, convert to bps
        impact_decimal = self.ac_config.permanent_coef * order_fraction
        impact_bps = impact_decimal * Decimal("10000")

        return impact_bps.quantize(Decimal("0.01"))

    def calculate_temporary_impact(
        self,
        order_size: Decimal,
        adv: Decimal,
        volatility: Decimal,
        side: str,
    ) -> Decimal:
        """
        Calculate temporary market impact.

        Temporary impact is the price movement during execution that
        recovers after completion. It's caused by liquidity demand.

        Formula: impact = eta * sigma_daily * sqrt(order_size / ADV)

        Where sigma_daily is daily volatility (annual vol / sqrt(252)).

        Args:
            order_size: Size of the order in dollars (must be > 0)
            adv: Average daily volume in dollars (must be > 0)
            volatility: Annual volatility as decimal (e.g., 0.20 for 20%)
            side: "buy" or "sell"

        Returns:
            Temporary impact in basis points

        Raises:
            ValueError: If parameters are invalid
        """
        if order_size <= 0:
            raise ValueError(f"Order size must be positive, got {order_size}")

        if adv <= 0:
            raise ValueError(f"ADV must be positive, got {adv}")

        if volatility < 0:
            raise ValueError(f"Volatility cannot be negative, got {volatility}")

        side_lower = side.lower()
        if side_lower not in ("buy", "sell"):
            raise ValueError(f"Side must be 'buy' or 'sell', got '{side}'")

        # Convert annual volatility to daily using proper Almgren-Chriss formula
        # daily_vol = annual_vol / sqrt(252)
        daily_vol = volatility * self.ANNUAL_TO_DAILY_VOL_FACTOR

        # Calculate order size fraction
        order_fraction = order_size / adv

        # Apply temporary impact formula with square root
        # impact = eta * sigma * sqrt(order_size / ADV)
        sqrt_fraction = order_fraction**self.ac_config.adv_exponent
        impact_decimal = self.ac_config.temporary_coef * daily_vol * sqrt_fraction

        # Convert to bps
        impact_bps = impact_decimal * Decimal("10000")

        return impact_bps.quantize(Decimal("0.01"))

    def calculate_impact(
        self,
        order_size: Decimal,
        adv: Decimal,
        volatility: Decimal,
        side: str,
        base_price: Decimal | None = None,
    ) -> MarketImpact:
        """
        Calculate total market impact using Almgren-Chriss model.

        Combines permanent and temporary impact into a single estimate.

        Args:
            order_size: Size of the order in dollars
            adv: Average daily volume in dollars
            volatility: Annual volatility as decimal
            side: "buy" or "sell"
            base_price: Base price before impact (optional)

        Returns:
            MarketImpact with detailed breakdown

        Raises:
            ValueError: If parameters are invalid
        """
        # Calculate permanent and temporary impacts
        permanent_bps = self.calculate_permanent_impact(order_size, adv, side)
        temporary_bps = self.calculate_temporary_impact(order_size, adv, volatility, side)

        # Total impact
        total_bps = permanent_bps + temporary_bps

        # Apply safety limit
        total_bps = min(total_bps, self.ac_config.max_impact_bps)

        # Calculate estimated price if base price provided
        estimated_price = base_price if base_price else Decimal("0")

        if base_price and base_price > 0:
            # Apply impact to price
            # Buy: price increases (pay more)
            # Sell: price decreases (receive less)
            price_adjustment = total_bps / Decimal("10000")

            if side.lower() == "buy":
                estimated_price = base_price * (Decimal("1") + price_adjustment)
            else:
                estimated_price = base_price * (Decimal("1") - price_adjustment)

            estimated_price = estimated_price.quantize(Decimal("0.01"))

        # Calculate dollar impacts
        if base_price and base_price > 0:
            shares = order_size / base_price
            permanent_dollars = shares * base_price * (permanent_bps / Decimal("10000"))
            temporary_dollars = shares * base_price * (temporary_bps / Decimal("10000"))
        else:
            permanent_dollars = Decimal("0")
            temporary_dollars = Decimal("0")

        total_dollars = permanent_dollars + temporary_dollars

        return MarketImpact(
            temporary_impact_bps=temporary_bps,
            permanent_impact_bps=permanent_bps,
            total_impact_bps=total_bps,
            estimated_price=estimated_price,
            temporary_impact_dollars=temporary_dollars.quantize(Decimal("0.01")),
            permanent_impact_dollars=permanent_dollars.quantize(Decimal("0.01")),
            total_impact_dollars=total_dollars.quantize(Decimal("0.01")),
        )

    def calibrate_coefficients(
        self,
        historical_impacts: list[dict[str, Any]],
    ) -> AlmgrenChrissConfig:
        """
        Calibrate impact coefficients from historical execution data using
        ordinary least squares regression.

        The Almgren-Chriss model decomposes market impact into:
        observed_impact = gamma * (order_size/adv) + eta * sigma * sqrt(order_size/adv)

        We perform linear regression to estimate:
        - gamma (gamma): Permanent impact coefficient
        - eta (eta): Temporary impact coefficient

        Args:
            historical_impacts: List of dicts with keys:
                - order_size: Order size in dollars
                - adv: Average daily volume
                - volatility: Annual volatility
                - observed_impact_bps: Actual impact observed

        Returns:
            Calibrated AlmgrenChrissConfig with regression-estimated coefficients
        """
        if not historical_impacts:
            logger.warning("No historical data provided for calibration, using defaults")
            return self.ac_config

        if len(historical_impacts) < 3:
            logger.warning(
                f"Insufficient data points for calibration ({len(historical_impacts)} < 3), using defaults"
            )
            return self.ac_config

        try:
            # Prepare data for regression
            # Model: impact = gamma * X1 + eta * X2
            # where X1 = order_size/adv, X2 = volatility * sqrt(order_size/adv)

            X1_values = []  # Permanent impact regressor (order_size / adv)
            X2_values = []  # Temporary impact regressor (volatility * sqrt(order_size / adv))
            y_values = []  # Observed impact (dependent variable)

            for data_point in historical_impacts:
                try:
                    order_size = Decimal(str(data_point.get("order_size", 0)))
                    adv = Decimal(str(data_point.get("adv", 1)))
                    volatility = Decimal(str(data_point.get("volatility", 0)))
                    observed_impact = Decimal(str(data_point.get("observed_impact_bps", 0)))

                    # Skip invalid data points
                    if adv <= 0 or order_size <= 0:
                        continue

                    # Calculate regressors
                    participation_rate = float(order_size / adv)
                    X1 = participation_rate  # Permanent: order_size / adv
                    X2 = float(volatility) * math.sqrt(
                        participation_rate
                    )  # Temporary: vol * sqrt(order_size / adv)

                    X1_values.append(X1)
                    X2_values.append(X2)
                    y_values.append(float(observed_impact))

                except (ValueError, TypeError, ZeroDivisionError) as e:
                    logger.debug(f"Skipping invalid data point: {e}")
                    continue

            if len(X1_values) < 3:
                logger.warning("Insufficient valid data points for regression, using defaults")
                return self.ac_config

            # Perform ordinary least squares regression
            # Using numpy for efficient computation
            import numpy as np

            # Design matrix: [X1, X2]
            X = np.column_stack([X1_values, X2_values])
            y = np.array(y_values)

            # Add intercept column (not strictly needed as impact should be 0 at 0 participation,
            # but helps with model fitting)
            X_with_intercept = np.column_stack([np.ones(len(X1_values)), X])

            # OLS regression: (X^T X)^-1 X^T y
            try:
                # Use np.linalg.lstsq for numerical stability
                coefficients, _residuals, _rank, _singular_values = np.linalg.lstsq(
                    X_with_intercept, y, rcond=None
                )

                # Extract coefficients (skipping intercept)
                # coefficients[0] = intercept, coefficients[1] = gamma, coefficients[2] = eta
                coefficients[0]
                gamma = max(0, coefficients[1])  # Permanent impact coefficient (non-negative)
                eta = max(0, coefficients[2])  # Temporary impact coefficient (non-negative)

                # Calculate R-squared for goodness of fit
                y_pred = X_with_intercept @ coefficients
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                ss_res = np.sum((y - y_pred) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

                logger.info(
                    f"Market impact calibration complete: "
                    f"gamma={gamma:.6f}, eta={eta:.6f}, R^2={r_squared:.4f} "
                    f"(from {len(X1_values)} data points)"
                )

                # If coefficients are effectively zero or regression failed, use defaults
                if gamma < 1e-10 and eta < 1e-10:
                    logger.warning("Regression produced near-zero coefficients, using defaults")
                    return self.ac_config

                # Create calibrated config with regression coefficients
                calibrated_config = AlmgrenChrissConfig(
                    permanent_coef=Decimal(str(gamma)),
                    temporary_coef=Decimal(str(eta)),
                    volatility_exponent=self.ac_config.volatility_exponent,
                    adv_exponent=self.ac_config.adv_exponent,
                    max_impact_bps=self.ac_config.max_impact_bps,
                )

                return calibrated_config

            except (np.linalg.LinAlgError, ValueError) as e:
                logger.error(f"Regression failed due to numerical error: {e}, using defaults")
                return self.ac_config

        except Exception as e:
            logger.error(
                f"Error during coefficient calibration: {e}, using defaults", exc_info=True
            )
            return self.ac_config

    def estimate_impact_range(
        self,
        order_size: Decimal,
        adv_min: Decimal,
        adv_max: Decimal,
        volatility: Decimal,
        side: str,
        base_price: Decimal | None = None,
    ) -> tuple[MarketImpact, MarketImpact]:
        """
        Estimate impact range for ADV uncertainty.

        Args:
            order_size: Size of the order in dollars
            adv_min: Minimum expected ADV
            adv_max: Maximum expected ADV
            volatility: Annual volatility as decimal
            side: "buy" or "sell"
            base_price: Base price before impact

        Returns:
            Tuple of (max_impact, min_impact) MarketImpact objects
        """
        # Lower ADV = higher impact
        max_impact = self.calculate_impact(order_size, adv_min, volatility, side, base_price)

        # Higher ADV = lower impact
        min_impact = self.calculate_impact(order_size, adv_max, volatility, side, base_price)

        return max_impact, min_impact

    def get_participation_rate_limit(
        self,
        max_impact_bps: Decimal,
        volatility: Decimal,
    ) -> Decimal:
        """
        Calculate maximum participation rate to limit impact.

        Given a maximum acceptable impact, calculate the maximum
        order size as a percentage of ADV.

        Solves for X in: max_impact = gamma * X + eta * sigma * sqrt(X)

        Args:
            max_impact_bps: Maximum acceptable impact in bps
            volatility: Annual volatility

        Returns:
            Maximum participation rate (as decimal, e.g., 0.05 for 5%)
        """
        # This is an approximation - solving the exact equation requires
        # numerical methods since we have both X and sqrt(X) terms

        max_impact_decimal = max_impact_bps / Decimal("10000")
        # Convert annual volatility to daily volatility using the standard formula
        # daily_vol = annual_vol / sqrt(252) for 252 trading days per year
        daily_vol = volatility * self.ANNUAL_TO_DAILY_VOL_FACTOR if volatility > 0 else Decimal("0")

        # Approximate: ignore permanent impact for initial estimate
        # max_impact ~ eta * sigma * sqrt(X)
        # sqrt(X) ~ max_impact / (eta * sigma)
        # X ~ (max_impact / (eta * sigma))^2

        if daily_vol > 0 and self.ac_config.temporary_coef > 0:
            sqrt_x = max_impact_decimal / (self.ac_config.temporary_coef * daily_vol)
            participation_rate = sqrt_x**2
        else:
            participation_rate = Decimal("0.01")  # Default 1%

        # Sanity check: cap at 20%
        participation_rate = min(participation_rate, Decimal("0.20"))

        return participation_rate.quantize(Decimal("0.0001"))
