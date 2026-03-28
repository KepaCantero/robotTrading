"""
Tick Size Constraints

Implements Harris Rule 6.9 and O'Hara Rule 7.8: Handle tick size constraints.

Tick size impacts:
- Bid-ask spread (minimum spread = 1 tick)
- Price granularity
- Liquidity provision
- Market quality
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TickSizeAnalysis:
    """Tick size analysis result."""

    symbol: str
    tick_size: Decimal
    price: Decimal

    # Metrics
    spread_in_ticks: float
    avg_spread_in_ticks: float
    tick_regime: str  # SUB-TICK, TIGHT, NORMAL, WIDE

    # Implications
    can_improve_on_bid: bool
    can_improve_on_ask: bool
    recommended_price_increment: Decimal


@dataclass
class TickConstraintsResult:
    """Tick constraints for order placement."""

    symbol: str
    tick_size: Decimal

    # Constraints
    valid_prices: List[Decimal]
    min_price: Decimal
    max_price: Decimal
    n_price_levels: int

    # Trading implications
    min_spread_bps: float
    liquidity_implication: str


class TickSizeConstraints:
    """
    Tick Size Constraints Handler (Harris Rule 6.9, O'Hara Rule 7.8).

    Handles tick size constraints for order placement and analysis.
    """

    # Common tick sizes by exchange/asset class
    DEFAULT_TICK_SIZES = {
        # US Equities
        "NYSE_EQUITY": Decimal("0.01"),
        "NASDAQ_EQUITY": Decimal("0.01"),
        "PINK_SHEETS": Decimal("0.0001"),
        # Futures
        "ES": Decimal("0.25"),  # S&P 500 E-mini
        "NQ": Decimal("0.25"),  # Nasdaq E-mini
        "CL": Decimal("0.01"),  # Crude Oil
        "GC": Decimal("0.10"),  # Gold
        # Forex (pip-based)
        "FOREX_MAJOR": Decimal("0.0001"),  # 1 pip
        "FOREX_MINOR": Decimal("0.001"),  # 10 pips
        # Crypto
        "BTC": Decimal("0.01"),  # Bitcoin
        "ETH": Decimal("0.001"),  # Ethereum
    }

    # Spread regimes (in ticks)
    SPREAD_REGIMES = {
        "SUB_TICK": (0, 1),
        "TIGHT": (1, 3),
        "NORMAL": (3, 10),
        "WIDE": (10, float("inf")),
    }

    def __init__(
        self,
        default_tick_size: Optional[Decimal] = None,
    ):
        """
        Initialize tick size constraints handler.

        Args:
            default_tick_size: Default tick size if not specified
        """
        if default_tick_size is None:
            default_tick_size = Decimal("0.01")
        self.default_tick_size = default_tick_size
        self._tick_cache: Dict[str, Decimal] = {}

        logger.info(f"TickSizeConstraints initialized with default_tick={default_tick_size}")

    def get_tick_size(
        self,
        symbol: str,
        price: Optional[Decimal] = None,
        exchange: Optional[str] = None,
    ) -> Decimal:
        """
        Get tick size for a symbol.

        Args:
            symbol: Trading symbol
            price: Current price (for dynamic tick sizing)
            exchange: Exchange name

        Returns:
            Tick size in price units
        """
        # Check cache
        if symbol in self._tick_cache:
            return self._tick_cache[symbol]

        # Try to determine from exchange/asset class
        tick_size = self._determine_tick_size(symbol, exchange, price)

        # Cache it
        self._tick_cache[symbol] = tick_size

        return tick_size

    def _determine_tick_size(
        self,
        symbol: str,
        exchange: Optional[str],
        price: Optional[Decimal],
    ) -> Decimal:
        """Determine tick size from symbol/exchange."""
        # Check predefined
        if exchange and exchange in self.DEFAULT_TICK_SIZES:
            return self.DEFAULT_TICK_SIZES[exchange]

        # Determine from symbol
        symbol_upper = symbol.upper()

        # Futures
        if symbol_upper.startswith("ES") or "E-MINI" in symbol_upper:
            return self.DEFAULT_TICK_SIZES["ES"]
        elif symbol_upper.startswith("NQ"):
            return self.DEFAULT_TICK_SIZES["NQ"]
        elif symbol_upper.startswith("CL"):
            return self.DEFAULT_TICK_SIZES["CL"]
        elif symbol_upper.startswith("GC"):
            return self.DEFAULT_TICK_SIZES["GC"]

        # Crypto
        if "BTC" in symbol_upper or "BITCOIN" in symbol_upper:
            return self.DEFAULT_TICK_SIZES["BTC"]
        elif "ETH" in symbol_upper or "ETHEREUM" in symbol_upper:
            return self.DEFAULT_TICK_SIZES["ETH"]

        # Price-based for equities
        if price:
            if price < Decimal("1"):
                # Penny stocks: smaller tick
                return Decimal("0.0001")
            elif price < Decimal("10"):
                return Decimal("0.001")
            else:
                return Decimal("0.01")

        # Default
        return self.default_tick_size

    def round_to_tick(
        self,
        price: Decimal,
        tick_size: Optional[Decimal] = None,
        symbol: Optional[str] = None,
        round_down: bool = False,
    ) -> Decimal:
        """
        Round price to tick size.

        Args:
            price: Price to round
            tick_size: Tick size (optional, will determine from symbol)
            symbol: Symbol (for determining tick size)
            round_down: If True, round down; if False, round to nearest

        Returns:
            Rounded price
        """
        if tick_size is None:
            if symbol:
                tick_size = self.get_tick_size(symbol, price)
            else:
                tick_size = self.default_tick_size

        # Calculate rounded price
        ticks = price / tick_size

        if round_down:
            rounded_ticks = int(ticks)
        else:
            rounded_ticks = int(ticks + Decimal("0.5"))

        return rounded_ticks * tick_size

    def adjust_limit_price(
        self,
        side: str,
        reference_price: Decimal,
        current_bid: Decimal,
        current_ask: Decimal,
        tick_size: Optional[Decimal] = None,
        aggressiveness: float = 0.5,
    ) -> Decimal:
        """
        Adjust limit price based on aggressiveness (Harris Rule 6.6).

        Args:
            side: "BUY" or "SELL"
            reference_price: Reference price (mid, last, etc.)
            current_bid: Current best bid
            current_ask: Current best ask
            tick_size: Tick size
            aggressiveness: 0 = passive, 1 = aggressive

        Returns:
            Adjusted limit price
        """
        if tick_size is None:
            tick_size = self.default_tick_size

        spread = current_ask - current_bid

        if side.upper() == "BUY":
            # Buy: spread portion from 0 (bid) to 1 (ask)
            raw_price = current_bid + spread * Decimal(str(aggressiveness))
            # Round to tick (round up for buy)
            return self.round_to_tick(raw_price + tick_size, tick_size, round_down=False)
        else:
            # Sell: spread portion from 0 (ask) to 1 (bid)
            raw_price = current_ask - spread * Decimal(str(aggressiveness))
            # Round to tick (round down for sell)
            return self.round_to_tick(raw_price, tick_size, round_down=True)

    def analyze_tick_regime(
        self,
        symbol: str,
        price: Decimal,
        bid: Decimal,
        ask: Decimal,
        historical_spreads: Optional[pd.Series] = None,
    ) -> TickSizeAnalysis:
        """
        Analyze tick size regime (O'Hara Rule 7.8).

        Args:
            symbol: Trading symbol
            price: Current mid price
            bid: Current bid
            ask: Current ask
            historical_spreads: Historical spread data

        Returns:
            TickSizeAnalysis with regime and implications
        """
        tick_size = self.get_tick_size(symbol, price)

        # Current spread in ticks
        current_spread = ask - bid
        spread_ticks = float(current_spread / tick_size)

        # Average spread in ticks
        if historical_spreads is not None and len(historical_spreads) > 0:
            avg_spread = historical_spreads.mean()
            avg_spread_ticks = float(avg_spread / tick_size)
        else:
            avg_spread_ticks = spread_ticks

        # Determine regime
        tick_regime = self._classify_spread_regime(spread_ticks, avg_spread_ticks)

        # Check if can improve
        can_improve_bid = self._can_improve_price(bid, tick_size, side="BUY")
        can_improve_ask = self._can_improve_price(ask, tick_size, side="SELL")

        # Recommended increment
        recommended_increment = tick_size

        return TickSizeAnalysis(
            symbol=symbol,
            tick_size=tick_size,
            price=price,
            spread_in_ticks=spread_ticks,
            avg_spread_in_ticks=avg_spread_ticks,
            tick_regime=tick_regime,
            can_improve_on_bid=can_improve_bid,
            can_improve_on_ask=can_improve_ask,
            recommended_price_increment=recommended_increment,
        )

    def _classify_spread_regime(
        self,
        spread_ticks: float,
        avg_spread_ticks: float,
    ) -> str:
        """Classify spread regime."""
        # Use average spread for regime classification
        for regime, (min_ticks, max_ticks) in self.SPREAD_REGIMES.items():
            if min_ticks <= avg_spread_ticks < max_ticks:
                return regime

        return "WIDE"

    def _can_improve_price(
        self,
        price: Decimal,
        tick_size: Decimal,
        side: str,
    ) -> bool:
        """Check if price can be improved by one tick."""
        if side == "BUY":
            # Can we bid higher?
            improved = price + tick_size
        else:
            # Can we ask lower?
            improved = price - tick_size

        # Simple check: not zero
        return improved > 0

    def calculate_tick_constraints(
        self,
        symbol: str,
        min_price: Decimal,
        max_price: Decimal,
        price: Optional[Decimal] = None,
    ) -> TickConstraintsResult:
        """
        Calculate valid price levels and constraints.

        Args:
            symbol: Trading symbol
            min_price: Minimum price of interest
            max_price: Maximum price of interest
            price: Current price (for tick size determination)

        Returns:
            TickConstraintsResult with all valid prices
        """
        tick_size = self.get_tick_size(symbol, price)

        # Calculate number of price levels
        price_range = max_price - min_price
        n_levels = int(price_range / tick_size) + 1

        # Generate valid prices
        valid_prices = []
        current = min_price
        while current <= max_price:
            valid_prices.append(current)
            current += tick_size

        # Minimum spread (1 tick)
        if min_price > 0:
            min_spread = float(tick_size / min_price) * 10000
        else:
            min_spread = 0.0

        # Liquidity implication
        if n_levels > 1000:
            implication = "HIGH_GRANULARITY_MAY_CAUSE_FRAGMENTATION"
        elif n_levels > 100:
            implication = "NORMAL_GRANULARITY"
        else:
            implication = "LOW_GRANULARITY_MAY_HINDER_DISCOVERY"

        return TickConstraintsResult(
            symbol=symbol,
            tick_size=tick_size,
            valid_prices=valid_prices,
            min_price=min_price,
            max_price=max_price,
            n_price_levels=n_levels,
            min_spread_bps=min_spread,
            liquidity_implication=implication,
        )

    def get_optimal_tick_size(
        self,
        symbol: str,
        price_range: Decimal,
        avg_daily_volume: float,
        current_tick_size: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate optimal tick size for market quality.

        Based on research showing:
        - Too large: Wide spreads, poor liquidity
        - Too small: Market fragmentation, adverse selection

        Args:
            symbol: Trading symbol
            price_range: Typical daily price range
            avg_daily_volume: Average daily volume
            current_tick_size: Current tick size

        Returns:
            Recommended tick size
        """
        # Heuristic: Aim for ~100-200 price levels per day
        # This provides sufficient granularity without fragmentation

        target_n_levels = 150
        optimal_tick = price_range / target_n_levels

        # Round to reasonable decimal places
        if optimal_tick < Decimal("0.001"):
            return Decimal("0.0001")
        elif optimal_tick < Decimal("0.01"):
            return Decimal("0.001")
        elif optimal_tick < Decimal("0.1"):
            return Decimal("0.01")
        else:
            return Decimal("0.01")  # Standard equity tick

    def validate_price_ticks(
        self,
        prices: List[Decimal],
        tick_size: Decimal,
        tolerance: float = 0.01,
    ) -> Dict[str, any]:
        """
        Validate if prices are on valid ticks.

        Args:
            prices: List of prices to validate
            tick_size: Expected tick size
            tolerance: Tolerance for rounding errors

        Returns:
            Dict with validation results
        """
        invalid_prices = []
        valid_count = 0

        for price in prices:
            # Check if price is on tick
            ticks = price / tick_size
            is_on_tick = abs(ticks - int(ticks)) < tolerance

            if is_on_tick:
                valid_count += 1
            else:
                invalid_prices.append(
                    {
                        "price": price,
                        "nearest_tick_down": self.round_to_tick(price, tick_size, round_down=True),
                        "nearest_tick_up": self.round_to_tick(
                            price + tick_size, tick_size, round_down=False
                        ),
                    }
                )

        return {
            "total_prices": len(prices),
            "valid_count": valid_count,
            "invalid_count": len(invalid_prices),
            "validity_rate": valid_count / len(prices) if prices else 0,
            "invalid_prices": invalid_prices[:10],  # First 10
        }


# Global singleton
_tick_size_constraints: TickSizeConstraints = None


def get_tick_size_constraints(
    default_tick_size: Optional[Decimal] = None,
) -> TickSizeConstraints:
    """Get or create global TickSizeConstraints instance."""
    if default_tick_size is None:
        default_tick_size = Decimal("0.01")
    global _tick_size_constraints
    if _tick_size_constraints is None:
        _tick_size_constraints = TickSizeConstraints(
            default_tick_size=default_tick_size,
        )

    return _tick_size_constraints
