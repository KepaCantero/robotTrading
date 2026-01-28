"""
Slippage Models

Implements various slippage models for realistic backtesting:
- Linear slippage (proportional to volume)
- Percentage slippage (fixed percentage)
- Volatility-adjusted slippage
- Time-weighted slippage

Reference: Rule 62-johnson-algorithmic-trading-dma.md
Paper: Johnson, B. (2010) "Algorithmic Trading & DMA"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, time
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class SlippageType(str, Enum):
    """Type of slippage model."""

    LINEAR = "linear"
    PERCENTAGE = "percentage"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    TIME_WEIGHTED = "time_weighted"


@dataclass
class SlippageResult:
    """Result of slippage calculation."""

    expected_price: Decimal
    execution_price: Decimal
    slippage_amount: Decimal
    slippage_percentage: float
    side: str

    @property
    def adverse(self) -> bool:
        """Check if slippage is adverse (worse than expected)."""
        if self.side == "buy":
            return self.execution_price > self.expected_price
        else:
            return self.execution_price < self.expected_price


class SlippageModel(ABC):
    """
    Base class for slippage models.

    Slippage is the difference between the expected price of a trade
    and the price at which the trade is actually executed.

    Factors affecting slippage:
    - Order size relative to volume
    - Market volatility
    - Time of day
    - Market conditions
    - Bid-ask spread
    """

    @abstractmethod
    def calculate_slippage(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        timestamp: Optional[datetime] = None,
        volume: Optional[Decimal] = None,
        volatility: Optional[float] = None,
        spread: Optional[Decimal] = None,
    ) -> SlippageResult:
        """
        Calculate slippage for an order.

        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Number of shares
            price: Expected price
            timestamp: Order timestamp
            volume: Available volume at price
            volatility: Current volatility
            spread: Bid-ask spread

        Returns:
            SlippageResult with execution details
        """
        pass


class LinearSlippageModel(SlippageModel):
    """
    Linear slippage model.

    Slippage = base_rate * (quantity / volume)

    Slippage increases linearly with order size relative to available volume.
    """

    def __init__(
        self,
        base_rate: float = 0.001,  # 0.1% base slippage
        volume_factor: float = 0.5,  # Additional slippage per unit of volume ratio
    ):
        """
        Initialize linear slippage model.

        Args:
            base_rate: Base slippage rate
            volume_factor: Additional factor for volume impact
        """
        self._base_rate = base_rate
        self._volume_factor = volume_factor

    def calculate_slippage(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        timestamp: Optional[datetime] = None,
        volume: Optional[Decimal] = None,
        volatility: Optional[float] = None,
        spread: Optional[Decimal] = None,
    ) -> SlippageResult:
        """Calculate linear slippage."""
        # Base slippage
        slippage_pct = self._base_rate

        # Volume impact
        if volume and volume > 0:
            volume_ratio = float(quantity) / float(volume)
            slippage_pct += self._volume_factor * volume_ratio

        # Calculate execution price
        if side == "buy":
            slippage_amount = price * Decimal(str(slippage_pct))
            execution_price = price + slippage_amount
        else:
            slippage_amount = price * Decimal(str(slippage_pct))
            execution_price = price - slippage_amount

        return SlippageResult(
            expected_price=price,
            execution_price=execution_price,
            slippage_amount=slippage_amount,
            slippage_percentage=slippage_pct,
            side=side,
        )


class PercentageSlippageModel(SlippageModel):
    """
    Percentage slippage model.

    Simplest model: fixed percentage slippage regardless of order size.
    """

    def __init__(
        self,
        buy_slippage: float = 0.0005,  # 0.05% for buys
        sell_slippage: float = 0.0005,  # 0.05% for sells
    ):
        """
        Initialize percentage slippage model.

        Args:
            buy_slippage: Slippage percentage for buy orders
            sell_slippage: Slippage percentage for sell orders
        """
        self._buy_slippage = buy_slippage
        self._sell_slippage = sell_slippage

    def calculate_slippage(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        timestamp: Optional[datetime] = None,
        volume: Optional[Decimal] = None,
        volatility: Optional[float] = None,
        spread: Optional[Decimal] = None,
    ) -> SlippageResult:
        """Calculate percentage slippage."""
        slippage_pct = self._buy_slippage if side == "buy" else self._sell_slippage

        # Add spread component (half the spread)
        if spread:
            slippage_pct += float(spread) / (2 * float(price))

        slippage_amount = price * Decimal(str(slippage_pct))

        if side == "buy":
            execution_price = price + slippage_amount
        else:
            execution_price = price - slippage_amount

        return SlippageResult(
            expected_price=price,
            execution_price=execution_price,
            slippage_amount=slippage_amount,
            slippage_percentage=slippage_pct,
            side=side,
        )


class VolatilityAdjustedSlippage(SlippageModel):
    """
    Volatility-adjusted slippage model.

    Slippage increases with market volatility.

    Higher volatility = more price movement during order execution.
    """

    def __init__(
        self,
        base_rate: float = 0.0005,  # Base slippage at 20% volatility
        vol_sensitivity: float = 0.5,  # How much slippage increases with vol
        benchmark_vol: float = 0.2,  # Benchmark volatility (20%)
    ):
        """
        Initialize volatility-adjusted slippage model.

        Args:
            base_rate: Base slippage rate
            vol_sensitivity: Sensitivity to volatility
            benchmark_vol: Benchmark volatility level
        """
        self._base_rate = base_rate
        self._vol_sensitivity = vol_sensitivity
        self._benchmark_vol = benchmark_vol

    def calculate_slippage(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        timestamp: Optional[datetime] = None,
        volume: Optional[Decimal] = None,
        volatility: Optional[float] = None,
        spread: Optional[Decimal] = None,
    ) -> SlippageResult:
        """Calculate volatility-adjusted slippage."""
        # Use default volatility if not provided
        if volatility is None:
            volatility = self._benchmark_vol

        # Adjust slippage based on volatility
        vol_ratio = volatility / self._benchmark_vol
        slippage_pct = self._base_rate * (1 + self._vol_sensitivity * (vol_ratio - 1))

        # Add spread component
        if spread:
            slippage_pct += float(spread) / (2 * float(price))

        # Volume impact
        if volume and volume > 0:
            volume_ratio = float(quantity) / float(volume)
            slippage_pct *= (1 + volume_ratio)

        slippage_amount = price * Decimal(str(slippage_pct))

        if side == "buy":
            execution_price = price + slippage_amount
        else:
            execution_price = price - slippage_amount

        return SlippageResult(
            expected_price=price,
            execution_price=execution_price,
            slippage_amount=slippage_amount,
            slippage_percentage=slippage_pct,
            side=side,
        )


class TimeWeightedSlippageModel(SlippageModel):
    """
    Time-weighted slippage model.

    Slippage varies based on time of day:
    - Open (9:30-10:00 ET): High volatility, higher slippage
    - Mid-day (10:00-15:00 ET): Lower slippage
    - Close (15:00-16:00 ET): Higher slippage due to closing auctions

    Reference: Johnson (2010) "Algorithmic Trading & DMA"
    """

    # Time periods for US market (ET)
    OPEN_PERIOD = (time(9, 30), time(10, 0))
    MIDDAY_PERIOD = (time(10, 0), time(15, 0))
    CLOSE_PERIOD = (time(15, 0), time(16, 0))

    def __init__(
        self,
        base_slippage: float = 0.0005,
        open_multiplier: float = 2.0,  # 2x slippage at open
        close_multiplier: float = 1.5,  # 1.5x slippage at close
    ):
        """
        Initialize time-weighted slippage model.

        Args:
            base_slippage: Base slippage rate
            open_multiplier: Multiplier for open period
            close_multiplier: Multiplier for close period
        """
        self._base_slippage = base_slippage
        self._open_multiplier = open_multiplier
        self._close_multiplier = close_multiplier

    def _get_time_multiplier(self, timestamp: Optional[datetime]) -> float:
        """Get time-based multiplier for slippage."""
        if timestamp is None:
            return 1.0

        current_time = timestamp.time()

        # Check which period we're in
        if self.OPEN_PERIOD[0] <= current_time < self.OPEN_PERIOD[1]:
            return self._open_multiplier
        elif self.CLOSE_PERIOD[0] <= current_time < self.CLOSE_PERIOD[1]:
            return self._close_multiplier
        else:
            return 1.0

    def calculate_slippage(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        timestamp: Optional[datetime] = None,
        volume: Optional[Decimal] = None,
        volatility: Optional[float] = None,
        spread: Optional[Decimal] = None,
    ) -> SlippageResult:
        """Calculate time-weighted slippage."""
        # Get time multiplier
        time_multiplier = self._get_time_multiplier(timestamp)

        # Base slippage adjusted for time
        slippage_pct = self._base_slippage * time_multiplier

        # Add spread component
        if spread:
            slippage_pct += float(spread) / (2 * float(price))

        # Volatility adjustment
        if volatility:
            vol_multiplier = 1 + (volatility - 0.2)  # 0.2 is benchmark
            slippage_pct *= vol_multiplier

        slippage_amount = price * Decimal(str(slippage_pct))

        if side == "buy":
            execution_price = price + slippage_amount
        else:
            execution_price = price - slippage_amount

        return SlippageResult(
            expected_price=price,
            execution_price=execution_price,
            slippage_amount=slippage_amount,
            slippage_percentage=slippage_pct,
            side=side,
        )


@dataclass
class SpreadAwareSlippageConfig:
    """Configuration for spread-aware slippage."""

    half_spread: bool = True  # Use half spread for slippage
    spread_skew: float = 0.5  # Skew towards bid or ask (0.5 = centered)
    liquidity_premium: float = 0.0001  # Additional cost for illiquid stocks


class SpreadAwareSlippageModel(SlippageModel):
    """
    Spread-aware slippage model.

    Takes into account bid-ask spread when calculating slippage.

    For buy orders: slippage偏向ask
    For sell orders: slippage偏向bid
    """

    def __init__(
        self,
        config: Optional[SpreadAwareSlippageConfig] = None,
    ):
        """
        Initialize spread-aware slippage model.

        Args:
            config: Configuration for spread-aware calculation
        """
        self._config = config or SpreadAwareSlippageConfig()

    def calculate_slippage(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        timestamp: Optional[datetime] = None,
        volume: Optional[Decimal] = None,
        volatility: Optional[float] = None,
        spread: Optional[Decimal] = None,
    ) -> SlippageResult:
        """Calculate spread-aware slippage."""
        slippage_pct = 0.0

        # Spread component
        if spread and self._config.half_spread:
            spread_pct = float(spread) / float(price)
            if side == "buy":
                slippage_pct += spread_pct * (0.5 + self._config.spread_skew * 0.5)
            else:
                slippage_pct += spread_pct * (0.5 + (1 - self._config.spread_skew) * 0.5)

        # Add liquidity premium
        slippage_pct += self._config.liquidity_premium

        # Volatility component
        if volatility:
            slippage_pct += volatility * 0.1

        # Volume component
        if volume and volume > 0:
            volume_ratio = float(quantity) / float(volume)
            slippage_pct += volume_ratio * 0.01

        slippage_amount = price * Decimal(str(slippage_pct))

        if side == "buy":
            execution_price = price + slippage_amount
        else:
            execution_price = price - slippage_amount

        return SlippageResult(
            expected_price=price,
            execution_price=execution_price,
            slippage_amount=slippage_amount,
            slippage_percentage=slippage_pct,
            side=side,
        )
