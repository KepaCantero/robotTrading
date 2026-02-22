"""
Transaction Cost Model for Realistic Backtesting.

This module implements a comprehensive transaction cost model based on
real-world broker costs, primarily Interactive Brokers (IBKR).

BUG #3 FIX: Transaction costs were severely underestimated.
- Commission: Was 0.1% flat, now uses IBKR's actual pricing
- Slippage: Was not properly modeled, now uses market impact model
- Spread: Was missing, now includes bid-ask spread impact

References:
- IBKR Commission Structure: https://www.interactivebrokers.com/en/pricing/commissions-home.php
- Almgren-Chriss Market Impact Model
- Kissell Research Group implementation patterns

SINGLE SOURCE OF TRUTH: All values are sourced from CentralizedConfig.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, Optional

# SINGLE SOURCE OF TRUTH: Import CentralizedConfig for all values
from app.core.centralized_config import get_config

logger = logging.getLogger(__name__)


class BrokerType(Enum):
    """Supported broker types for cost modeling."""
    INTERACTIVE_BROKERS = "interactive_brokers"
    ALPACA = "alpaca"
    GENERIC = "generic"


class OrderType(Enum):
    """Order types for cost calculation."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


def _get_backtesting_config():
    """Helper to get backtesting config from CentralizedConfig."""
    return get_config().backtesting


@dataclass
class BrokerConfig:
    """
    Configuration for a specific broker's cost structure.

    SINGLE SOURCE OF TRUTH: Default values come from CentralizedConfig.
    """

    # Commission structure - defaults from CentralizedConfig
    commission_per_share: Optional[Decimal] = None   # IBKR: $0.005/share
    commission_minimum: Optional[Decimal] = None     # IBKR: $1.00 minimum
    commission_maximum: Optional[Decimal] = None    # IBKR: 0.5% of trade value max

    # Exchange fees (SEC, TAF, etc.) - these are regulatory, not broker-specific
    sec_fee_rate: Decimal = Decimal("0.0000278")     # SEC fee per dollar of sale
    taf_fee_per_share: Decimal = Decimal("0.000166")  # Trading Activity Fee

    # Spread assumptions (typical for liquid stocks) - from CentralizedConfig
    default_spread_bps: Optional[Decimal] = None
    large_cap_spread_bps: Decimal = Decimal("3")     # 3 bps for large caps
    small_cap_spread_bps: Decimal = Decimal("15")    # 15 bps for small caps

    # Slippage parameters (Almgren-Chriss inspired) - from CentralizedConfig
    temporary_impact_coefficient: Decimal = Decimal("0.1")   # Temporary impact
    permanent_impact_coefficient: Decimal = Decimal("0.05")  # Permanent impact

    # Participation rate limits - from CentralizedConfig
    max_participation_rate: Optional[Decimal] = None

    def __post_init__(self):
        """Fill in defaults from CentralizedConfig after initialization."""
        config = _get_backtesting_config()

        if self.commission_per_share is None:
            self.commission_per_share = config.default_commission_per_share
        if self.commission_minimum is None:
            self.commission_minimum = config.min_commission
        if self.commission_maximum is None:
            self.commission_maximum = config.default_commission_rate
        if self.default_spread_bps is None:
            self.default_spread_bps = config.base_slippage_bps / Decimal("2")  # Spread is half slippage
        if self.max_participation_rate is None:
            self.max_participation_rate = config.adv_limit_pct


@dataclass
class TransactionCostResult:
    """Result of transaction cost calculation."""

    # Gross amounts
    gross_value: Decimal = Decimal("0")

    # Commission breakdown
    commission: Decimal = Decimal("0")
    sec_fee: Decimal = Decimal("0")
    taf_fee: Decimal = Decimal("0")

    # Market impact
    spread_cost: Decimal = Decimal("0")
    slippage_cost: Decimal = Decimal("0")
    market_impact_cost: Decimal = Decimal("0")

    # Total
    total_cost: Decimal = Decimal("0")
    total_cost_bps: Decimal = Decimal("0")

    # Effective execution price
    effective_price: Optional[Decimal] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "gross_value": float(self.gross_value),
            "commission": float(self.commission),
            "sec_fee": float(self.sec_fee),
            "taf_fee": float(self.taf_fee),
            "spread_cost": float(self.spread_cost),
            "slippage_cost": float(self.slippage_cost),
            "market_impact_cost": float(self.market_impact_cost),
            "total_cost": float(self.total_cost),
            "total_cost_bps": float(self.total_cost_bps),
            "effective_price": float(self.effective_price) if self.effective_price else None,
        }


class TransactionCostModel:
    """
    Realistic transaction cost model for backtesting.

    This model calculates all components of transaction costs:
    1. Commission (broker fees)
    2. Exchange/regulatory fees (SEC, TAF)
    3. Bid-ask spread cost
    4. Market impact (temporary + permanent)
    5. Slippage (execution uncertainty)

    SINGLE SOURCE OF TRUTH: All values sourced from CentralizedConfig.

    Example:
        >>> model = TransactionCostModel()
        >>> result = model.calculate_costs(
        ...     symbol="AAPL",
        ...     side="BUY",
        ...     quantity=Decimal("100"),
        ...     price=Decimal("150.00"),
        ...     average_volume=Decimal("50000000"),
        ... )
        >>> print(f"Total cost: ${result.total_cost:.2f} ({result.total_cost_bps:.1f} bps)")
    """

    # Default configurations per broker - use BrokerConfig() for CentralizedConfig defaults
    # Note: BrokerConfig.__post_init__ fills in defaults from CentralizedConfig
    BROKER_CONFIGS: Dict[BrokerType, BrokerConfig] = {
        # IBKR: Uses CentralizedConfig defaults (commission_per_share, min, max)
        BrokerType.INTERACTIVE_BROKERS: BrokerConfig(),  # Defaults from CentralizedConfig
        # ALPACA: Commission-free trading
        BrokerType.ALPACA: BrokerConfig(
            commission_per_share=Decimal("0"),
            commission_minimum=Decimal("0"),
            commission_maximum=Decimal("0"),
        ),
        # GENERIC: Slightly higher costs
        BrokerType.GENERIC: BrokerConfig(
            commission_per_share=Decimal("0.01"),
            commission_minimum=Decimal("2.00"),
            commission_maximum=Decimal("0.01"),
        ),
    }

    def __init__(
        self,
        broker: BrokerType = BrokerType.INTERACTIVE_BROKERS,
        config: Optional[BrokerConfig] = None,
        conservative: bool = True,
    ):
        """
        Initialize the transaction cost model.

        Args:
            broker: Broker type for default configuration
            config: Custom broker configuration (overrides defaults)
            conservative: Use conservative (higher) cost estimates
        """
        self.broker = broker
        self.config = config or self.BROKER_CONFIGS.get(broker, BrokerConfig())
        self.conservative = conservative

    def calculate_costs(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        order_type: OrderType = OrderType.MARKET,
        average_volume: Optional[Decimal] = None,
        volatility: Optional[Decimal] = None,
        market_cap_category: str = "large_cap",
        urgency: float = 0.5,
    ) -> TransactionCostResult:
        """
        Calculate all transaction costs for a trade.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Number of shares
            price: Current/expected price
            order_type: Type of order
            average_volume: Average daily volume (for market impact)
            volatility: Asset volatility (for market impact)
            market_cap_category: large_cap, mid_cap, or small_cap
            urgency: Execution urgency (0-1, affects slippage)

        Returns:
            TransactionCostResult with all cost components
        """
        result = TransactionCostResult()

        # Gross trade value
        result.gross_value = quantity * price

        # 1. Calculate commission
        result.commission = self._calculate_commission(quantity, result.gross_value)

        # 2. Calculate regulatory fees (only on sells)
        if side.upper() == "SELL":
            result.sec_fee = self._calculate_sec_fee(result.gross_value)
            result.taf_fee = self._calculate_taf_fee(quantity)

        # 3. Calculate spread cost
        spread_bps = self._get_spread_bps(market_cap_category)
        result.spread_cost = result.gross_value * spread_bps / Decimal("10000")

        # 4. Calculate market impact (if volume provided)
        if average_volume and average_volume > 0:
            result.market_impact_cost = self._calculate_market_impact(
                quantity=quantity,
                price=price,
                average_volume=average_volume,
                volatility=volatility,
                urgency=urgency,
            )

        # 5. Calculate slippage (execution uncertainty)
        result.slippage_cost = self._calculate_slippage(
            gross_value=result.gross_value,
            order_type=order_type,
            volatility=volatility,
            urgency=urgency,
        )

        # Calculate total
        result.total_cost = (
            result.commission
            + result.sec_fee
            + result.taf_fee
            + result.spread_cost
            + result.market_impact_cost
            + result.slippage_cost
        )

        # Calculate basis points
        if result.gross_value > 0:
            result.total_cost_bps = (result.total_cost / result.gross_value) * Decimal("10000")

        # Calculate effective execution price
        if side.upper() == "BUY":
            # Buy: pay more due to costs
            result.effective_price = (result.gross_value + result.total_cost) / quantity
        else:
            # Sell: receive less due to costs
            result.effective_price = (result.gross_value - result.total_cost) / quantity

        # Store metadata
        result.metadata = {
            "symbol": symbol,
            "side": side,
            "quantity": float(quantity),
            "price": float(price),
            "order_type": order_type.value,
            "broker": self.broker.value,
            "conservative": self.conservative,
        }

        return result

    def _calculate_commission(self, quantity: Decimal, trade_value: Decimal) -> Decimal:
        """
        Calculate broker commission using IBKR structure.

        IBKR Tiered Pricing:
        - $0.005 per share
        - $1.00 minimum
        - 0.5% of trade value maximum
        """
        per_share = quantity * self.config.commission_per_share
        minimum = self.config.commission_minimum
        maximum = trade_value * self.config.commission_maximum

        # Apply min/max
        commission = max(per_share, minimum)
        commission = min(commission, maximum)

        return commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculate_sec_fee(self, trade_value: Decimal) -> Decimal:
        """
        Calculate SEC fee (only on sells).

        SEC fee rate: $27.80 per $1,000,000 (as of 2024)
        """
        fee = trade_value * self.config.sec_fee_rate
        return fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculate_taf_fee(self, quantity: Decimal) -> Decimal:
        """
        Calculate Trading Activity Fee (only on sells).

        TAF: $0.000166 per share (FINRA)
        """
        fee = quantity * self.config.taf_fee_per_share
        return fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _get_spread_bps(self, market_cap_category: str) -> Decimal:
        """Get bid-ask spread in basis points based on market cap."""
        if market_cap_category == "large_cap":
            return self.config.large_cap_spread_bps
        elif market_cap_category == "small_cap":
            return self.config.small_cap_spread_bps
        else:
            return self.config.default_spread_bps

    def _calculate_market_impact(
        self,
        quantity: Decimal,
        price: Decimal,
        average_volume: Decimal,
        volatility: Optional[Decimal],
        urgency: float,
    ) -> Decimal:
        """
        Calculate market impact using simplified Almgren-Chriss model.

        Market Impact = Temporary Impact + Permanent Impact

        Temporary Impact: Function of participation rate and volatility
        Permanent Impact: Function of trade size relative to volume
        """
        # Participation rate
        trade_value = quantity * price
        daily_volume_value = average_volume * price

        if daily_volume_value <= 0:
            return Decimal("0")

        participation_rate = trade_value / daily_volume_value

        # Cap participation rate
        participation_rate = min(participation_rate, self.config.max_participation_rate)

        # Volatility adjustment (use default if not provided)
        vol = volatility or Decimal("0.20")  # 20% default

        # Temporary impact (scales with participation rate)
        temp_impact = (
            self.config.temporary_impact_coefficient
            * Decimal(str(participation_rate))
            * Decimal(str(vol))
        )

        # Permanent impact (scales with sqrt of participation rate)
        import math
        perm_impact = (
            self.config.permanent_impact_coefficient
            * Decimal(str(math.sqrt(float(participation_rate))))
            * Decimal(str(vol))
        )

        # Urgency factor (higher urgency = more aggressive = more impact)
        urgency_factor = Decimal("0.5") + Decimal(str(urgency)) * Decimal("0.5")

        # Total impact in decimal
        total_impact = (temp_impact + perm_impact) * urgency_factor

        # Convert to cost
        if self.conservative:
            total_impact *= Decimal("1.5")  # 50% buffer for conservative estimates

        return (trade_value * total_impact).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculate_slippage(
        self,
        gross_value: Decimal,
        order_type: OrderType,
        volatility: Optional[Decimal],
        urgency: float,
    ) -> Decimal:
        """
        Calculate execution slippage (uncertainty in fill price).

        Market orders: Higher slippage
        Limit orders: Lower slippage (but may not fill)

        SINGLE SOURCE OF TRUTH: Base values from CentralizedConfig.
        """
        # Get base slippage from CentralizedConfig
        config = _get_backtesting_config()
        base_slippage_bps = config.base_slippage_bps

        # Order type adjustment - use config multipliers
        if order_type == OrderType.MARKET:
            # Market orders have standard slippage
            pass
        elif order_type == OrderType.LIMIT:
            # Limit orders have lower slippage (better execution expected)
            base_slippage_bps = base_slippage_bps * config.optimistic_slippage_bps / config.base_slippage_bps
        else:
            # Stop orders have worse execution
            base_slippage_bps = base_slippage_bps * config.stop_slippage_multiplier

        # Volatility adjustment
        vol = volatility or Decimal("0.20")
        vol_factor = vol / Decimal("0.20")  # Normalize to 20% baseline

        # Apply volatility multiplier from config
        vol_factor *= config.volatility_multiplier

        # Urgency adjustment (higher urgency = more slippage)
        urgency_factor = Decimal("0.5") + Decimal(str(urgency)) * Decimal("0.5")

        # Calculate final slippage
        slippage_bps = base_slippage_bps * vol_factor * urgency_factor

        if self.conservative:
            slippage_bps *= Decimal("1.5")

        return (gross_value * slippage_bps / Decimal("10000")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def get_round_trip_cost_estimate(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        average_volume: Optional[Decimal] = None,
        volatility: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Get estimated round-trip cost (buy + sell).

        Useful for profitability validation before entering a trade.
        """
        buy_costs = self.calculate_costs(
            symbol=symbol,
            side="BUY",
            quantity=quantity,
            price=price,
            average_volume=average_volume,
            volatility=volatility,
        )

        sell_costs = self.calculate_costs(
            symbol=symbol,
            side="SELL",
            quantity=quantity,
            price=price,
            average_volume=average_volume,
            volatility=volatility,
        )

        return buy_costs.total_cost + sell_costs.total_cost


# Convenience function for quick cost estimation
def estimate_transaction_costs(
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    broker: BrokerType = BrokerType.INTERACTIVE_BROKERS,
) -> TransactionCostResult:
    """
    Quick transaction cost estimation.

    Args:
        symbol: Trading symbol
        side: BUY or SELL
        quantity: Number of shares
        price: Current price
        broker: Broker type

    Returns:
        TransactionCostResult with cost breakdown
    """
    model = TransactionCostModel(broker=broker)
    return model.calculate_costs(
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
    )
