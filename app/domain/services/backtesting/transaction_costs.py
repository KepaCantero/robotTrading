"""
Transaction Cost Models

Implements various transaction cost models for realistic backtesting:
- Linear cost model (per-share commission)
- Piecewise linear cost model (volume discounts)
- Market impact models (Almgren-Chriss, etc.)

Reference: Rule 44-almgren-chriss-optimal-execution.md
Paper: Almgren, R., & Chriss, N. (2001) "Optimal Execution of Portfolio Transactions"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np


class CostModelType(str, Enum):
    """Type of cost model."""

    LINEAR = "linear"
    PIECEWISE_LINEAR = "piecewise_linear"
    NONLINEAR = "nonlinear"


@dataclass
class CostBreakdown:
    """Breakdown of transaction costs."""

    commission: Decimal  # Broker commission
    exchange_fees: Decimal  # Exchange fees
    sec_fees: Decimal  # SEC fees (for US stocks)
    nasdaq_fees: Decimal  # NASDAQ fees
    slippage: Decimal  # Price slippage
    market_impact: Decimal  # Market impact
    total: Decimal  # Total cost

    @property
    def cost_as_percentage(self) -> float:
        """Total cost as percentage of notional value."""
        if self.total == 0:
            return 0.0
        return float(self.total) * 100  # Placeholder


class TransactionCostModel(ABC):
    """
    Base class for transaction cost models.

    Transaction costs include:
    - Commission: Broker fee per trade
    - Exchange fees: Fee charged by exchange
    - Regulatory fees: SEC, FINRA, etc.
    - Slippage: Difference between expected and actual price
    - Market impact: Price movement due to order size
    """

    @abstractmethod
    def calculate_cost(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        volume: Optional[Decimal] = None,
        adv: Optional[Decimal] = None,
    ) -> CostBreakdown:
        """
        Calculate transaction cost breakdown.

        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Number of shares
            price: Price per share
            volume: Volume at time of trade (optional)
            adv: Average daily volume (optional)

        Returns:
            CostBreakdown with all cost components
        """

    @abstractmethod
    def estimate_total_cost(
        self,
        trades: List[Tuple[str, str, Decimal, Decimal]],
    ) -> Decimal:
        """
        Estimate total cost for list of trades.

        Args:
            trades: List of (symbol, side, quantity, price)

        Returns:
            Total estimated cost
        """


class LinearCostModel(TransactionCostModel):
    """
    Linear transaction cost model.

    Costs = fixed_commission + per_share_rate * quantity

    This is the simplest model where costs are linear in quantity.
    """

    def __init__(
        self,
        commission_per_share: Optional[Decimal] = None,
        min_commission: Optional[Decimal] = None,
        exchange_fee_rate: Optional[Decimal] = None,  # $0.00023 per share
        sec_fee_rate: Optional[Decimal] = None,  # SEC fee for sells only
    ):
        """
        Initialize linear cost model.

        Args:
            commission_per_share: Commission per share traded
            min_commission: Minimum commission per trade
            exchange_fee_rate: Exchange fee rate per share
            sec_fee_rate: SEC fee rate (for sell orders)
        """
        if commission_per_share is None:
            commission_per_share = Decimal("0.005")
        if min_commission is None:
            min_commission = Decimal("1.0")
        if exchange_fee_rate is None:
            exchange_fee_rate = Decimal("0.00023")
        if sec_fee_rate is None:
            sec_fee_rate = Decimal("0.0000082")
        self._commission_per_share = commission_per_share
        self._min_commission = min_commission
        self._exchange_fee_rate = exchange_fee_rate
        self._sec_fee_rate = sec_fee_rate

    def calculate_cost(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        volume: Optional[Decimal] = None,
        adv: Optional[Decimal] = None,
    ) -> CostBreakdown:
        """Calculate linear transaction costs."""
        # Commission
        commission = max(quantity * self._commission_per_share, self._min_commission)

        # Exchange fees
        exchange_fees = quantity * self._exchange_fee_rate

        # SEC fees (only on sells)
        sec_fees = Decimal("0")
        if side.lower() == "sell":
            sec_fees = quantity * price * self._sec_fee_rate

        # NASDAQ fees (simplified)
        nasdaq_fees = Decimal("0.0001") * quantity

        # Slippage and market impact would be calculated separately
        slippage = Decimal("0")
        market_impact = Decimal("0")

        total = commission + exchange_fees + sec_fees + nasdaq_fees + slippage + market_impact

        return CostBreakdown(
            commission=commission,
            exchange_fees=exchange_fees,
            sec_fees=sec_fees,
            nasdaq_fees=nasdaq_fees,
            slippage=slippage,
            market_impact=market_impact,
            total=total,
        )

    def estimate_total_cost(
        self,
        trades: List[Tuple[str, str, Decimal, Decimal]],
    ) -> Decimal:
        """Estimate total cost for all trades."""
        total = Decimal("0")
        for symbol, side, quantity, price in trades:
            cost = self.calculate_cost(symbol, side, quantity, price)
            total += cost.total
        return total


class PiecewiseLinearCostModel(TransactionCostModel):
    """
    Piecewise linear cost model with volume discounts.

    Costs decrease with larger volumes (tiered pricing).

    Example tiers:
    - 0-100k shares: $0.005/share
    - 100k-1M shares: $0.003/share
    - 1M+ shares: $0.001/share
    """

    def __init__(
        self,
        tiers: List[Tuple[Decimal, Decimal]],
        min_commission: Optional[Decimal] = None,
    ):
        """
        Initialize piecewise linear cost model.

        Args:
            tiers: List of (threshold, rate) tuples
                   Example: [(Decimal("100000"), Decimal("0.005")),
                             (Decimal("1000000"), Decimal("0.003")),
                             (Decimal("999999999"), Decimal("0.001"))]
            min_commission: Minimum commission per trade
        """
        if min_commission is None:
            min_commission = Decimal("1.0")
        self._tiers = sorted(tiers, key=lambda x: x[0])
        self._min_commission = min_commission

    def _get_rate_for_quantity(self, quantity: Decimal) -> Decimal:
        """Get commission rate for given quantity."""
        for threshold, rate in self._tiers:
            if quantity <= threshold:
                return rate
        return self._tiers[-1][1]  # Return lowest rate

    def calculate_cost(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        volume: Optional[Decimal] = None,
        adv: Optional[Decimal] = None,
    ) -> CostBreakdown:
        """Calculate piecewise linear transaction costs."""
        rate = self._get_rate_for_quantity(quantity)
        commission = max(quantity * rate, self._min_commission)

        # Fixed exchange fees
        exchange_fees = quantity * Decimal("0.00023")

        # SEC fees on sells
        sec_fees = Decimal("0")
        if side.lower() == "sell":
            sec_fees = quantity * price * Decimal("0.0000082")

        nasdaq_fees = Decimal("0.0001") * quantity

        slippage = Decimal("0")
        market_impact = Decimal("0")

        total = commission + exchange_fees + sec_fees + nasdaq_fees + slippage + market_impact

        return CostBreakdown(
            commission=commission,
            exchange_fees=exchange_fees,
            sec_fees=sec_fees,
            nasdaq_fees=nasdaq_fees,
            slippage=slippage,
            market_impact=market_impact,
            total=total,
        )

    def estimate_total_cost(
        self,
        trades: List[Tuple[str, str, Decimal, Decimal]],
    ) -> Decimal:
        """Estimate total cost for all trades."""
        total = Decimal("0")
        for symbol, side, quantity, price in trades:
            cost = self.calculate_cost(symbol, side, quantity, price)
            total += cost.total
        return total


class MarketImpactModel(ABC):
    """Base class for market impact models."""

    @abstractmethod
    def calculate_impact(
        self,
        quantity: Decimal,
        price: Decimal,
        adv: Decimal,
        volatility: float = 0.2,
        participation_rate: Optional[float] = None,
    ) -> Decimal:
        """
        Calculate market impact cost.

        Args:
            quantity: Order size
            price: Current price
            adv: Average daily volume
            volatility: Annualized volatility
            participation_rate: Order participation rate (quantity/adv)

        Returns:
            Market impact cost (per share)
        """


class AlmgrenChristModel(MarketImpactModel):
    """
    Almgren-Chriss market impact model.

    Models market impact as a function of order size and volatility.

    Reference: Almgren, R., & Chriss, N. (2001)
    "Optimal Execution of Portfolio Transactions"

    Impact = temporary_impact + permanent_impact

    Temporary impact: price recovery during execution
    Permanent impact: persistent price change
    """

    # Typical parameter values (from Almgren-Chriss paper)
    # These should be calibrated to specific market conditions
    DEFAULT_PERMANENT_IMPACT = 0.1  # Gamma parameter
    DEFAULT_TEMPORARY_IMPACT = 0.05  # Eta parameter
    DEFAULT_VOLATILITY_IMPACT = 0.5  # Lambda parameter

    def __init__(
        self,
        permanent_impact: float = DEFAULT_PERMANENT_IMPACT,
        temporary_impact: float = DEFAULT_TEMPORARY_IMPACT,
        volatility_impact: float = DEFAULT_VOLATILITY_IMPACT,
    ):
        """
        Initialize Almgren-Chriss model.

        Args:
            permanent_impact: Permanent impact coefficient (gamma)
            temporary_impact: Temporary impact coefficient (eta)
            volatility_impact: Volatility impact coefficient (lambda)
        """
        self._gamma = permanent_impact
        self._eta = temporary_impact
        self._lambda = volatility_impact

    def calculate_impact(
        self,
        quantity: Decimal,
        price: Decimal,
        adv: Decimal,
        volatility: float = 0.2,
        participation_rate: Optional[float] = None,
    ) -> Decimal:
        """
        Calculate Almgren-Chriss market impact.

        Args:
            quantity: Order size (shares)
            price: Current price
            adv: Average daily volume
            volatility: Annualized volatility (default 20%)
            participation_rate: Order participation rate

        Returns:
            Total market impact (per share)
        """
        qty_float = float(quantity)
        adv_float = float(adv)

        # Calculate participation rate if not provided
        if participation_rate is None:
            participation_rate = min(qty_float / adv_float, 1.0)

        # Daily volatility (assuming 252 trading days)
        daily_vol = volatility / np.sqrt(252)

        # Permanent impact: moves price permanently
        # Impact proportional to participation rate
        permanent = self._gamma * participation_rate

        # Temporary impact: depends on execution speed
        # Simplified model
        temporary = self._eta * (qty_float / adv_float) * daily_vol

        # Total impact in price terms
        total_impact_pct = permanent + temporary

        # Convert to dollar amount
        total_impact = price * Decimal(str(total_impact_pct))

        return total_impact

    def calculate_permanent_impact(
        self,
        quantity: Decimal,
        adv: Decimal,
    ) -> float:
        """Calculate permanent impact component only."""
        participation_rate = min(float(quantity) / float(adv), 1.0)
        return self._gamma * participation_rate

    def calculate_temporary_impact(
        self,
        quantity: Decimal,
        adv: Decimal,
        volatility: float = 0.2,
    ) -> float:
        """Calculate temporary impact component only."""
        daily_vol = volatility / np.sqrt(252)
        return self._eta * (float(quantity) / float(adv)) * daily_vol


class SquareRootImpactModel(MarketImpactModel):
    """
    Square root market impact model.

    Based on the square-root law: Impact ~ (Q/ADV)^0.5

    This is a simpler model that works well for many assets.
    """

    def __init__(self, coefficient: float = 0.1):
        """
        Initialize square root model.

        Args:
            coefficient: Impact coefficient (typically 0.05-0.2)
        """
        self._coefficient = coefficient

    def calculate_impact(
        self,
        quantity: Decimal,
        price: Decimal,
        adv: Decimal,
        volatility: float = 0.2,
        participation_rate: Optional[float] = None,
    ) -> Decimal:
        """
        Calculate square root market impact.

        Impact = coefficient * sigma * sqrt(Q/ADV)

        Args:
            quantity: Order size
            price: Current price
            adv: Average daily volume
            volatility: Annualized volatility
            participation_rate: Not used in this model

        Returns:
            Market impact cost (per share)
        """
        if price is None:
            price = Decimal("0")
        # Daily volatility
        daily_vol = volatility / np.sqrt(252)

        # Participation ratio
        participation_ratio = float(quantity) / float(adv)

        # Square root impact
        impact_pct = self._coefficient * daily_vol * np.sqrt(participation_ratio)

        # Convert to dollar amount
        impact = price * Decimal(str(impact_pct))

        return impact


@dataclass
class ImpactParameters:
    """Parameters for market impact calculation."""

    adv: Decimal  # Average daily volume
    volatility: float  # Annualized volatility
    market_cap: Optional[Decimal] = None  # Market capitalization
    spread: Optional[Decimal] = None  # Bid-ask spread
    price: Optional[Decimal] = None  # Current price


@dataclass
class TemporaryImpact:
    """Temporary market impact (recovers during execution)."""

    impact_per_share: Decimal
    recovery_time_hours: float = 1.0  # Time for price to recover


@dataclass
class PermanentImpact:
    """Permanent market impact (persistent)."""

    impact_per_share: Decimal
    price_displacement: Decimal  # Total price displacement
