from __future__ import annotations

"""Avellaneda-Stoikov Market Making Model.

This module implements the core Avellaneda-Stoikov model for optimal market making.
The model calculates reservation prices and optimal spreads that account for
inventory risk and adverse selection.

Key Equations:

1. Reservation Price (inventory-adjusted mid):
   r(s) = s - (gamma * sigma^2 / k) * q * (T - t) / T

   Where:
   - s: Current mid price
   - gamma (gamma): Risk aversion parameter
   - sigma (sigma): Volatility
   - k: Order book depth parameter
   - q: Current inventory
   - T: Total time horizon
   - t: Current time

2. Optimal Spread:
   delta* = (gamma * sigma^2 / k) * (T - t) + (2/gamma) * ln(1 + gamma/2)

   Components:
   - Inventory risk: (gamma * sigma^2 / k) * (T - t)
   - Adverse selection: (2/gamma) * ln(1 + gamma/2)

3. Bid/Ask Quotes:
   - Bid: r(s) - delta*/2
   - Ask: r(s) + delta*/2
"""


import logging
import math
from decimal import Decimal

from app.domain.trading.market_making.avellaneda_stoikov.models import ASConfig, ASQuote

logger = logging.getLogger(__name__)


class AvellanedaStoikovModel:
    """
    Avellaneda-Stoikov market making model.

    This model provides optimal bid/ask quotes for market making by:
    1. Adjusting the mid price based on inventory (reservation price)
    2. Calculating optimal spread based on risk aversion and volatility
    3. Dynamically updating quotes as market conditions change

    Example:
        >>> config = ASConfig(
        ...     gamma=Decimal("0.01"),
        ...     sigma=Decimal("0.3"),
        ...     k=Decimal("0.01"),
        ...     T=Decimal("3600"),
        ...     max_inventory=100,
        ... )
        >>> model = AvellanedaStoikovModel(config)
        >>> quote = model.calculate_quotes(
        ...     mid_price=Decimal("100.0"),
        ...     inventory=10,
        ...     time_remaining=Decimal("1800"),
        ... )
    """

    def __init__(self, config: ASConfig) -> None:
        """
        Initialize the Avellaneda-Stoikov model.

        Args:
            config: Model configuration parameters.

        Raises:
            ValueError: If configuration parameters are invalid.
        """
        self.config = config
        self._gamma = float(config.gamma)
        self._sigma = float(config.sigma)
        self._k = float(config.k)
        self._T = float(config.T)

        # Validate parameters
        if self._gamma <= 0:
            raise ValueError("Risk aversion (gamma) must be positive")
        if self._sigma <= 0:
            raise ValueError("Volatility (sigma) must be positive")
        if self._k <= 0:
            raise ValueError("Order book depth (k) must be positive")
        if self._T <= 0:
            raise ValueError("Time horizon (T) must be positive")

        logger.debug(
            f"Initialized AS model: gamma={self._gamma}, sigma={self._sigma}, "
            f"k={self._k}, T={self._T}"
        )

    def calculate_reservation_price(
        self,
        mid_price: float | Decimal,
        inventory: int,
        time_remaining: float | Decimal,
    ) -> float:
        """
        Calculate reservation price (inventory-adjusted mid price).

        The reservation price is where we would want to transact given our
        current inventory. It shifts the mid price to encourage closing positions:
        - If long inventory: lower reservation price (encourage selling)
        - If short inventory: higher reservation price (encourage buying)

        Formula:
        r(s) = s - (gamma * sigma^2 / k) * q * (T - t) / T

        Args:
            mid_price: Current mid price.
            inventory: Current inventory (positive = long, negative = short).
            time_remaining: Time remaining in trading window.

        Returns:
            Reservation price.

        Examples:
            >>> model = AvellanedaStoikovModel(ASConfig())
            >>> # Neutral inventory
            >>> model.calculate_reservation_price(100.0, 0, 1800)
            100.0
            >>> # Long inventory - reservation price lower
            >>> model.calculate_reservation_price(100.0, 10, 1800)
            99.85
            >>> # Short inventory - reservation price higher
            >>> model.calculate_reservation_price(100.0, -10, 1800)
            100.15
        """
        mid = float(mid_price)
        t_rem = float(time_remaining)

        # Calculate inventory adjustment
        # adjustment = (gamma * sigma^2 / k) * q * (T - t) / T
        inventory_factor = (self._gamma * self._sigma**2) / self._k
        time_decay = t_rem / self._T if self._T > 0 else 0
        adjustment = inventory_factor * inventory * time_decay

        # Reservation price shifts opposite to inventory direction
        reservation_price = mid - adjustment

        logger.debug(
            f"Reservation price: mid={mid:.4f}, inventory={inventory}, "
            f"adjustment={adjustment:.4f}, reservation={reservation_price:.4f}"
        )

        return reservation_price

    def calculate_optimal_spread(
        self,
        time_remaining: float | Decimal,
    ) -> float:
        """
        Calculate optimal half-spread.

        The optimal spread balances:
        1. Inventory risk: Higher when more time remaining and higher volatility
        2. Adverse selection: Constant penalty for providing liquidity

        Formula:
        delta* = (gamma * sigma^2 / k) * (T - t) + (2/gamma) * ln(1 + gamma/2)

        Args:
            time_remaining: Time remaining in trading window.

        Returns:
            Optimal half-spread (not full bid-ask spread).

        Examples:
            >>> model = AvellanedaStoikovModel(ASConfig())
            >>> # At start of trading window (wider spread)
            >>> spread = model.calculate_optimal_spread(3600)
            >>> spread > 0
            True
            >>> # Near end of window (tighter spread)
            >>> spread_later = model.calculate_optimal_spread(300)
            >>> spread_later < spread
            True
        """
        t_rem = float(time_remaining)

        # Inventory risk component: (gamma * sigma^2 / k) * (T - t)
        inventory_risk_component = (self._gamma * self._sigma**2 / self._k) * t_rem

        # Adverse selection component: (2/gamma) * ln(1 + gamma/2)
        # Use approximation for small gamma: ln(1+x) ~ x - x^2/2
        adverse_selection = (2 / self._gamma) * math.log(1 + self._gamma / 2)

        half_spread = inventory_risk_component + adverse_selection

        logger.debug(
            f"Optimal spread: time_remaining={t_rem:.1f}, "
            f"inventory_risk={inventory_risk_component:.6f}, "
            f"adverse_selection={adverse_selection:.6f}, "
            f"half_spread={half_spread:.6f}"
        )

        return max(0.0, half_spread)

    def calculate_inventory_skew(
        self,
        inventory: int,
        time_remaining: float | Decimal,
    ) -> float:
        """
        Calculate inventory skew for reservation price adjustment.

        The skew determines how much to adjust the mid price based on inventory.
        Positive skew = shift up, Negative skew = shift down.

        Formula:
        skew = (gamma * sigma^2 / k) * q * (T - t) / T

        Args:
            inventory: Current inventory position.
            time_remaining: Time remaining in trading window.

        Returns:
            Inventory skew amount.
        """
        mid_adjustment = (self._gamma * self._sigma**2 / self._k) * inventory
        time_decay = float(time_remaining) / self._T if self._T > 0 else 0
        skew = mid_adjustment * time_decay
        return skew

    def calculate_quotes(
        self,
        mid_price: float | Decimal,
        inventory: int,
        time_remaining: float | Decimal,
    ) -> ASQuote:
        """
        Generate optimal bid/ask quotes.

        Combines reservation price calculation with optimal spread to generate
        the complete quote pair.

        Args:
            mid_price: Current mid price.
            inventory: Current inventory position.
            time_remaining: Time remaining in trading window.

        Returns:
            Complete quote with bid, ask, and metadata.

        Examples:
            >>> model = AvellanedaStoikovModel(ASConfig())
            >>> quote = model.calculate_quotes(100.0, 5, 1800)
            >>> quote.optimal_bid < quote.reservation_price < quote.optimal_ask
            True
            >>> quote.optimal_ask - quote.optimal_bid > 0
            True
        """
        mid = float(mid_price)
        t_rem = float(time_remaining)

        # Calculate reservation price
        reservation_price = self.calculate_reservation_price(mid, inventory, t_rem)

        # Calculate optimal spread
        half_spread = self.calculate_optimal_spread(t_rem)

        # Generate quotes
        optimal_bid = reservation_price - half_spread / 2
        optimal_ask = reservation_price + half_spread / 2

        # Calculate inventory skew for reporting
        skew = self.calculate_inventory_skew(inventory, t_rem)

        # Convert spread to basis points
        spread_bps = (half_spread / mid) * 10000 if mid > 0 else 0

        return ASQuote(
            symbol="AS_MODEL",
            timestamp=None,  # Set by caller
            mid_price=Decimal(str(mid)),
            reservation_price=Decimal(str(reservation_price)),
            optimal_bid=Decimal(str(max(0.0001, optimal_bid))),
            optimal_ask=Decimal(str(max(0.0001, optimal_ask))),
            optimal_spread_bps=Decimal(str(spread_bps)),
            inventory=inventory,
            inventory_skew=Decimal(str(skew)),
            time_to_expiry=Decimal(str(t_rem)),
        )

    def get_model_state(self) -> dict[str, float]:
        """
        Get current model state for monitoring/debugging.

        Returns:
            Dictionary with model parameters and state.
        """
        return {
            "gamma": self._gamma,
            "sigma": self._sigma,
            "k": self._k,
            "T": self._T,
            "risk_aversion": self._gamma,
            "volatility": self._sigma,
            "book_depth": self._k,
            "time_horizon": self._T,
        }

    def update_volatility(self, new_sigma: float | Decimal) -> None:
        """
        Update volatility estimate.

        Volatility should be updated periodically based on market conditions.

        Args:
            new_sigma: New volatility estimate (annualized).

        Raises:
            ValueError: If new_sigma is not positive.
        """
        sigma = float(new_sigma)
        if sigma <= 0:
            raise ValueError("Volatility must be positive")

        old_sigma = self._sigma
        self._sigma = sigma
        logger.info(f"Updated volatility: {old_sigma:.4f} -> {self._sigma:.4f}")

    def update_risk_aversion(self, new_gamma: float | Decimal) -> None:
        """
        Update risk aversion parameter.

        Risk aversion can be adjusted based on market conditions or
        inventory targets.

        Args:
            new_gamma: New risk aversion parameter.

        Raises:
            ValueError: If new_gamma is not in valid range.
        """
        gamma = float(new_gamma)
        if gamma < 0.001 or gamma > 0.1:
            raise ValueError("Risk aversion must be between 0.001 and 0.1")

        old_gamma = self._gamma
        self._gamma = gamma
        logger.info(f"Updated risk aversion: {old_gamma:.4f} -> {self._gamma:.4f}")


def calculate_inventory_risk(
    inventory: int,
    price: float,
    volatility: float,
    time_horizon: float,
    risk_multiplier: float = 1.0,
) -> float:
    """
    Calculate inventory risk metric.

    Risk = |inventory| * price * volatility * sqrt(time) * multiplier

    Args:
        inventory: Current inventory position.
        price: Current price.
        volatility: Annualized volatility.
        time_horizon: Time horizon in years (T / 31536000 for seconds).
        risk_multiplier: Risk multiplier for conservative estimates.

    Returns:
        Inventory risk value.
    """
    abs_inventory = abs(inventory)
    time_years = time_horizon / 31536000  # Convert seconds to years
    risk = abs_inventory * price * volatility * math.sqrt(time_years) * risk_multiplier
    return risk
