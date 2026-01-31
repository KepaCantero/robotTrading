"""
Slippage Model for Realistic Execution Simulation (FASE 5.2)

This module implements advanced slippage modeling based on:
- Order size as percentage of Average Daily Volume (ADV)
- Current volatility (VIX, historical vol)
- Bid-ask spread
- Time-of-day impact (worse at open/close)
- Market capitalization (large caps have less slippage)

Reference: Realistic slippage modeling for algorithmic trading
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TimeOfDay(str, Enum):
    """Time of day categories with different slippage characteristics."""

    PRE_MARKET = "pre_market"  # Before 9:30 AM ET
    OPEN = "open"  # 9:30-10:00 AM ET (high slippage)
    MORNING = "morning"  # 10:00 AM - 12:00 PM ET
    LUNCH = "lunch"  # 12:00 PM - 1:00 PM ET (lower slippage)
    AFTERNOON = "afternoon"  # 1:00 PM - 3:30 PM ET
    CLOSE = "close"  # 3:30-4:00 PM ET (high slippage)
    AFTER_HOURS = "after_hours"  # After 4:00 PM ET


class MarketCapCategory(str, Enum):
    """Market capitalization categories."""

    LARGE_CAP = "large_cap"  # >$10B market cap, high liquidity
    MID_CAP = "mid_cap"  # $1B-$10B market cap
    SMALL_CAP = "small_cap"  # $100M-$1B market cap
    MICRO_CAP = "micro_cap"  # <$100M market cap, low liquidity


@dataclass
class TimeOfDayImpact:
    """
    Slippage multiplier for different times of day.

    Reference: "Algorithmic Trading" by Barry Johnson
    - Open and close have higher slippage due to order imbalance
    - Lunch (12-1pm ET) typically has lowest slippage

    Attributes:
        time_of_day: Time category
        slippage_multiplier: Multiplier applied to base slippage
        volume_participation_rate: Typical participation rate
        description: Human-readable description
    """

    time_of_day: TimeOfDay
    slippage_multiplier: Decimal
    volume_participation_rate: Decimal
    description: str


# Time-of-day impact multipliers
TIME_OF_DAY_IMPACTS: Dict[TimeOfDay, TimeOfDayImpact] = {
    TimeOfDay.PRE_MARKET: TimeOfDayImpact(
        time_of_day=TimeOfDay.PRE_MARKET,
        slippage_multiplier=Decimal("2.0"),  # 2x slippage
        volume_participation_rate=Decimal("0.01"),  # Low volume
        description="Pre-market: Low liquidity, 2x slippage",
    ),
    TimeOfDay.OPEN: TimeOfDayImpact(
        time_of_day=TimeOfDay.OPEN,
        slippage_multiplier=Decimal("1.5"),  # 1.5x slippage
        volume_participation_rate=Decimal("0.15"),  # High volume but imbalance
        description="Open: Order imbalance, 1.5x slippage",
    ),
    TimeOfDay.MORNING: TimeOfDayImpact(
        time_of_day=TimeOfDay.MORNING,
        slippage_multiplier=Decimal("1.0"),  # Normal slippage
        volume_participation_rate=Decimal("0.10"),
        description="Morning: Normal trading conditions",
    ),
    TimeOfDay.LUNCH: TimeOfDayImpact(
        time_of_day=TimeOfDay.LUNCH,
        slippage_multiplier=Decimal("0.8"),  # 0.8x slippage (best time)
        volume_participation_rate=Decimal("0.05"),  # Lower volume
        description="Lunch: Lowest slippage (0.8x), best execution",
    ),
    TimeOfDay.AFTERNOON: TimeOfDayImpact(
        time_of_day=TimeOfDay.AFTERNOON,
        slippage_multiplier=Decimal("1.0"),  # Normal slippage
        volume_participation_rate=Decimal("0.10"),
        description="Afternoon: Normal trading conditions",
    ),
    TimeOfDay.CLOSE: TimeOfDayImpact(
        time_of_day=TimeOfDay.CLOSE,
        slippage_multiplier=Decimal("1.5"),  # 1.5x slippage
        volume_participation_rate=Decimal("0.20"),  # High volume, imbalance
        description="Close: Order imbalance, 1.5x slippage",
    ),
    TimeOfDay.AFTER_HOURS: TimeOfDayImpact(
        time_of_day=TimeOfDay.AFTER_HOURS,
        slippage_multiplier=Decimal("2.5"),  # 2.5x slippage
        volume_participation_rate=Decimal("0.005"),  # Very low volume
        description="After hours: Very low liquidity, 2.5x slippage",
    ),
}


@dataclass
class SlippageConfig:
    """
    Configuration for slippage model.

    Attributes:
        base_slippage_bps: Base slippage in basis points
        vol_multiplier: Volatility multiplier (slippage increases with vol)
        adv_impact_exponent: Exponent for ADV impact (default 2 for square)
        spread_impact: Whether to include spread impact
        time_of_day_impact: Whether to apply time-of-day multipliers
        market_cap_impact: Whether to adjust for market cap
        max_slippage_bps: Maximum slippage to apply
    """

    # Base slippage settings
    base_slippage_bps: Decimal = Decimal("5")  # 5 bps base (0.05%)

    # Volatility adjustment
    vol_multiplier: Decimal = Decimal("2")  # Volatility multiplier

    # ADV impact
    adv_impact_exponent: Decimal = Decimal("2")  # Square relationship

    # Feature flags
    spread_impact: bool = True  # Include half spread in slippage
    time_of_day_impact: bool = True  # Apply time-of-day multipliers
    market_cap_impact: bool = True  # Adjust for market cap

    # Limits
    max_slippage_bps: Decimal = Decimal("50")  # 50 bps max (0.5%)


@dataclass
class SlippageEstimate:
    """
    Result of slippage estimation.

    Attributes:
        basis_points: Slippage in basis points
        price_adjustment: Adjustment to price (decimal, e.g., 0.001 = 0.1%)
        fill_probability: Probability of fill (0-1)
        estimated_fill_price: Estimated execution price
        time_of_day_impact: Applied time-of-day multiplier
        volatility_impact: Applied volatility multiplier
        adv_impact: Impact from order size vs ADV
        spread_impact: Impact from bid-ask spread
        components: Detailed breakdown of slippage components
    """

    basis_points: Decimal
    price_adjustment: Decimal
    fill_probability: float
    estimated_fill_price: Decimal
    time_of_day_impact: Decimal
    volatility_impact: Decimal
    adv_impact: Decimal
    spread_impact: Decimal
    components: Dict[str, Decimal] = field(default_factory=dict)

    @property
    def total_impact_bps(self) -> Decimal:
        """Total impact in basis points."""
        return self.basis_points

    def total_impact_dollars(self, shares: int) -> Decimal:
        """
        Calculate total slippage cost in dollars.

        Args:
            shares: Number of shares

        Returns:
            Total slippage cost
        """
        price_value = Decimal(str(shares)) * self.estimated_fill_price
        return price_value * (self.basis_points / Decimal("10000"))


class SlippageModel:
    """
    Advanced slippage model for realistic execution simulation.

    This model calculates slippage based on:

    1. **Order Size Impact**: Larger orders as % of ADV have more slippage
       Formula: impact = (order_size / ADV)^exponent * coefficient

    2. **Volatility Impact**: Higher volatility increases slippage
       VIX > 30: 2x slippage
       VIX > 50: 3x slippage

    3. **Spread Impact**: Half the spread is unavoidable cost
       Added to slippage for realistic execution

    4. **Time-of-Day Impact**: Open/close have higher slippage
       Lunch (12-1pm) typically has lowest slippage

    5. **Market Cap Impact**: Large caps have less slippage
       Large cap: 2-5 bps
       Small cap: 10-25 bps

    Example:
        model = SlippageModel()
        estimate = model.estimate_slippage(
            symbol="AAPL",
            side="buy",
            shares=1000,
            current_price=Decimal("150.00"),
            bid=Decimal("149.98"),
            ask=Decimal("150.02"),
            adv=Decimal("50000000"),  # 50M shares daily
            volatility=Decimal("0.15"),  # 15% annual vol
        )
        print(f"Estimated slippage: {estimate.basis_points} bps")
    """

    # Base slippage by market cap (in bps)
    MARKET_CAP_BASE_SLIPPAGE = {
        MarketCapCategory.LARGE_CAP: Decimal("3.5"),  # 2-5 bps average
        MarketCapCategory.MID_CAP: Decimal("7.5"),  # 5-10 bps
        MarketCapCategory.SMALL_CAP: Decimal("17.5"),  # 10-25 bps
        MarketCapCategory.MICRO_CAP: Decimal("35"),  # 25-50 bps
    }

    # ADV thresholds for market cap classification (daily dollar volume)
    ADV_THRESHOLDS = {
        MarketCapCategory.LARGE_CAP: Decimal("1000000000"),  # >$1B daily
        MarketCapCategory.MID_CAP: Decimal("100000000"),  # $100M-$1B
        MarketCapCategory.SMALL_CAP: Decimal("10000000"),  # $10M-$100M
        MarketCapCategory.MICRO_CAP: Decimal("0"),  # <$10M
    }

    # Volatility thresholds
    VIX_LOW_VOLATILITY = Decimal("20")  # Below 20 = low vol
    VIX_HIGH_VOLATILITY = Decimal("30")  # Above 30 = high vol
    VIX_EXTREME_VOLATILITY = Decimal("50")  # Above 50 = extreme vol

    def __init__(self, config: Optional[SlippageConfig] = None):
        """
        Initialize slippage model.

        Args:
            config: Slippage configuration (uses defaults if not provided)
        """
        self.config = config or SlippageConfig()

    def classify_market_cap(self, adv_dollar_volume: Decimal) -> MarketCapCategory:
        """
        Classify market cap based on average daily volume.

        Args:
            adv_dollar_volume: Average daily dollar volume

        Returns:
            MarketCapCategory
        """
        if adv_dollar_volume >= self.ADV_THRESHOLDS[MarketCapCategory.LARGE_CAP]:
            return MarketCapCategory.LARGE_CAP
        elif adv_dollar_volume >= self.ADV_THRESHOLDS[MarketCapCategory.MID_CAP]:
            return MarketCapCategory.MID_CAP
        elif adv_dollar_volume >= self.ADV_THRESHOLDS[MarketCapCategory.SMALL_CAP]:
            return MarketCapCategory.SMALL_CAP
        else:
            return MarketCapCategory.MICRO_CAP

    def calculate_base_slippage(
        self,
        adv: Decimal,
        volatility: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate base slippage based on market cap (ADV).

        Args:
            adv: Average daily volume (shares or dollar value)
            volatility: Optional volatility measure

        Returns:
            Base slippage in basis points
        """
        market_cap = self.classify_market_cap(adv)
        base_slippage = self.MARKET_CAP_BASE_SLIPPAGE[market_cap]

        return base_slippage

    def calculate_adv_impact(
        self,
        order_value: Decimal,
        adv: Decimal,
    ) -> Decimal:
        """
        Calculate slippage impact from order size vs ADV.

        Formula: impact = (order_value / ADV)^exponent * coefficient

        Args:
            order_value: Value of the order
            adv: Average daily value (same unit as order_value)

        Returns:
            Additional slippage in basis points from order size
        """
        if adv <= 0:
            # No ADV data, assume minimal impact
            return Decimal("0")

        # Calculate order size as percentage of ADV
        order_size_pct = order_value / adv

        # Apply ADV impact formula
        # Using square relationship by default (exponent = 2)
        impact = (order_size_pct**self.config.adv_impact_exponent) * Decimal("10000")

        return impact.quantize(Decimal("0.01"))

    def calculate_volatility_impact(
        self,
        volatility: Optional[Decimal],
        vix: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate slippage multiplier from volatility.

        Args:
            volatility: Historical volatility (decimal, e.g., 0.20 for 20%)
            vix: VIX index value (preferred, in range 10-80)

        Returns:
            Volatility multiplier (1.0 = normal, 2.0 = double slippage)
        """
        # Use VIX if available, otherwise use historical volatility
        # VIX is in range 10-80 (e.g., 20, 30, 50), while historical volatility is decimal (e.g., 0.20, 0.30, 0.50)
        # Normalize historical volatility to VIX scale by multiplying by 100
        if vix is not None:
            vol_measure = vix
        elif volatility is not None:
            vol_measure = volatility * Decimal("100")  # Convert 0.20 -> 20 for VIX scale comparison
        else:
            return Decimal("1.0")

        if vol_measure <= self.VIX_LOW_VOLATILITY:
            # Low volatility: normal slippage
            return Decimal("1.0")
        elif vol_measure <= self.VIX_HIGH_VOLATILITY:
            # Medium volatility: slight increase
            excess_vol = (vol_measure - self.VIX_LOW_VOLATILITY) / (
                self.VIX_HIGH_VOLATILITY - self.VIX_LOW_VOLATILITY
            )
            return Decimal("1.0") + excess_vol
        elif vol_measure <= self.VIX_EXTREME_VOLATILITY:
            # High volatility: 2x slippage
            return Decimal("2.0")
        else:
            # Extreme volatility: 3x slippage
            return Decimal("3.0")

    def calculate_time_of_day_impact(
        self,
        time_of_day: TimeOfDay,
    ) -> Decimal:
        """
        Get slippage multiplier for time of day.

        Args:
            time_of_day: Time of day category

        Returns:
            Time-of-day multiplier
        """
        if not self.config.time_of_day_impact:
            return Decimal("1.0")

        impact = TIME_OF_DAY_IMPACTS.get(time_of_day)

        if impact:
            return impact.slippage_multiplier

        return Decimal("1.0")

    def calculate_spread_impact(
        self,
        bid: Decimal,
        ask: Decimal,
        current_price: Decimal,
    ) -> Decimal:
        """
        Calculate slippage impact from bid-ask spread.

        Half the spread is unavoidable (cross the spread to execute).

        Args:
            bid: Bid price
            ask: Ask price
            current_price: Current/mid price

        Returns:
            Spread impact in basis points
        """
        if not self.config.spread_impact:
            return Decimal("0")

        spread = ask - bid
        half_spread = spread / 2

        # Convert to bps
        if current_price > 0:
            spread_bps = (half_spread / current_price) * Decimal("10000")
            return spread_bps.quantize(Decimal("0.01"))

        return Decimal("0")

    def estimate_slippage(
        self,
        symbol: str,
        side: str,
        shares: int,
        current_price: Decimal,
        bid: Decimal,
        ask: Decimal,
        adv: Decimal,
        volatility: Optional[Decimal] = None,
        vix: Optional[Decimal] = None,
        timestamp: Optional[object] = None,  # datetime-like object
    ) -> SlippageEstimate:
        """
        Estimate slippage for an order.

        This combines all slippage components:
        1. Base slippage (market cap based)
        2. ADV impact (order size)
        3. Volatility impact
        4. Time-of-day impact
        5. Spread impact

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            shares: Number of shares
            current_price: Current market price
            bid: Current bid price
            ask: Current ask price
            adv: Average daily volume (shares)
            volatility: Historical volatility (optional)
            vix: VIX index value (optional, preferred over volatility)
            timestamp: Order timestamp for time-of-day impact

        Returns:
            SlippageEstimate with detailed breakdown

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate inputs
        if shares <= 0:
            raise ValueError(f"Shares must be positive, got {shares}")

        if current_price <= 0:
            raise ValueError(f"Current price must be positive, got {current_price}")

        side_lower = side.lower()
        if side_lower not in ("buy", "sell"):
            raise ValueError(f"Side must be 'buy' or 'sell', got '{side}'")

        # Calculate order value
        order_value = Decimal(str(shares)) * current_price

        # 1. Base slippage (market cap based)
        base_slippage_bps = self.calculate_base_slippage(adv, volatility)

        # 2. ADV impact (order size)
        adv_impact_bps = self.calculate_adv_impact(order_value, adv * current_price)

        # 3. Volatility impact (multiplier)
        vol_multiplier = self.calculate_volatility_impact(volatility, vix)

        # 4. Time-of-day impact (multiplier)
        # Default to afternoon if no timestamp
        time_of_day = TimeOfDay.AFTERNOON
        if timestamp and hasattr(timestamp, "hour"):
            hour = timestamp.hour
            if hour < 9:
                time_of_day = TimeOfDay.PRE_MARKET
            elif hour < 10:
                time_of_day = TimeOfDay.OPEN
            elif hour < 12:
                time_of_day = TimeOfDay.MORNING
            elif hour < 13:
                time_of_day = TimeOfDay.LUNCH
            elif hour < 15:
                time_of_day = TimeOfDay.AFTERNOON
            elif hour < 16:
                time_of_day = TimeOfDay.CLOSE
            else:
                time_of_day = TimeOfDay.AFTER_HOURS

        tod_multiplier = self.calculate_time_of_day_impact(time_of_day)

        # 5. Spread impact (additive)
        spread_impact_bps = self.calculate_spread_impact(bid, ask, current_price)

        # Calculate total slippage
        # Formula: (base + adv_impact) * vol_multiplier * tod_multiplier + spread
        base_total = base_slippage_bps + adv_impact_bps
        adjusted_total = base_total * vol_multiplier * tod_multiplier
        total_slippage_bps = adjusted_total + spread_impact_bps

        # Apply maximum
        total_slippage_bps = min(total_slippage_bps, self.config.max_slippage_bps)

        # Calculate price adjustment
        # Buy: pay more (add slippage), Sell: receive less (subtract slippage)
        price_adjustment = total_slippage_bps / Decimal("10000")

        if side_lower == "buy":
            estimated_fill_price = current_price * (Decimal("1") + price_adjustment)
        else:
            estimated_fill_price = current_price * (Decimal("1") - price_adjustment)

        # Estimate fill probability based on order size vs ADV
        fill_probability = self._estimate_fill_probability(order_value, adv * current_price)

        # Build components dict for transparency
        components = {
            "base_slippage_bps": base_slippage_bps,
            "adv_impact_bps": adv_impact_bps,
            "vol_multiplier": vol_multiplier,
            "tod_multiplier": tod_multiplier,
            "spread_impact_bps": spread_impact_bps,
            "total_slippage_bps": total_slippage_bps,
        }

        return SlippageEstimate(
            basis_points=total_slippage_bps.quantize(Decimal("0.01")),
            price_adjustment=price_adjustment.quantize(Decimal("0.000001")),
            fill_probability=fill_probability,
            estimated_fill_price=estimated_fill_price.quantize(Decimal("0.01")),
            time_of_day_impact=tod_multiplier,
            volatility_impact=vol_multiplier,
            adv_impact=adv_impact_bps,
            spread_impact=spread_impact_bps,
            components=components,
        )

    def _estimate_fill_probability(
        self,
        order_value: Decimal,
        adv: Decimal,
    ) -> float:
        """
        Estimate probability of order being filled.

        Based on order size as percentage of ADV.

        Args:
            order_value: Value of the order
            adv: Average daily value

        Returns:
            Fill probability (0-1)
        """
        if adv <= 0:
            return 0.5  # Unknown, assume 50%

        order_size_pct = float(order_value / adv)

        # Heuristic: fill probability decreases with order size
        # < 1% ADV: 100% fill
        # 1-5% ADV: 90% fill
        # 5-10% ADV: 70% fill
        # 10-20% ADV: 50% fill
        # > 20% ADV: 20% fill

        if order_size_pct < 0.01:
            return 1.0
        elif order_size_pct < 0.05:
            return 0.9
        elif order_size_pct < 0.10:
            return 0.7
        elif order_size_pct < 0.20:
            return 0.5
        else:
            return 0.2

