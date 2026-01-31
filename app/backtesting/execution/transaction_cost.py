"""
Transaction Cost Calculator for US Equity Trading (FASE 5.2)

This module implements realistic transaction cost calculation for US equity trading,
including:
- Per-share commission
- SEC fees (Section 31 fee)
- FINRA Trading Activity Fee (TAF)
- Exchange fees
- Minimum commission
- Tiered commission structures

Reference: US equity trading fee structure as of 2024
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FeeType(str, Enum):
    """Type of regulatory fee."""

    SEC_FEE = "sec_fee"  # SEC Section 31 fee on sells
    FINRA_TAF = "finra_taf"  # FINRA Trading Activity Fee
    EXCHANGE_FEE = "exchange_fee"  # Exchange fees (NYSE/NASDAQ)
    PLATFORM_FEE = "platform_fee"  # Platform/broker fees


class CommissionType(str, Enum):
    """Type of commission structure."""

    FIXED_PER_SHARE = "fixed_per_share"  # Fixed amount per share
    TIERED = "tiered"  # Tiered based on volume
    PERCENTAGE = "percentage"  # Percentage of trade value
    HYBRID = "hybrid"  # Combination with minimum


@dataclass
class FeeConfig:
    """
    Configuration for a single regulatory fee.

    Attributes:
        fee_type: Type of fee
        rate: Fee rate (per share, per dollar, or percentage)
        min_fee: Minimum fee (optional)
        max_fee: Maximum fee (optional)
        applies_to_buy: Whether fee applies to buy orders
        applies_to_sell: Whether fee applies to sell orders
        description: Human-readable description
    """

    fee_type: FeeType
    rate: Decimal
    min_fee: Optional[Decimal] = None
    max_fee: Optional[Decimal] = None
    applies_to_buy: bool = False
    applies_to_sell: bool = True
    description: str = ""


@dataclass
class CommissionTier:
    """
    Single tier in tiered commission structure.

    Attributes:
        min_shares: Minimum shares for this tier
        max_shares: Maximum shares for this tier (None for unlimited)
        rate: Commission rate per share
        min_commission: Minimum commission for this tier
    """

    min_shares: int
    max_shares: Optional[int]
    rate: Decimal
    min_commission: Decimal


# US Equity regulatory fees (2024 rates)
US_EQUITY_FEES: Dict[str, FeeConfig] = {
    "sec_fee": FeeConfig(
        fee_type=FeeType.SEC_FEE,
        rate=Decimal("0.0000078"),  # $0.0000078 per dollar sold (Section 31)
        min_fee=Decimal("0.01"),
        max_fee=Decimal("5.95"),  # Cap at $5.95 per trade
        applies_to_buy=False,
        applies_to_sell=True,
        description="SEC Section 31 fee on sales of stocks",
    ),
    "finra_taf": FeeConfig(
        fee_type=FeeType.FINRA_TAF,
        rate=Decimal("0.000145"),  # $0.000145 per share traded
        applies_to_buy=True,
        applies_to_sell=True,
        description="FINRA Trading Activity Fee (TAF)",
    ),
    "exchange_fee": FeeConfig(
        fee_type=FeeType.EXCHANGE_FEE,
        rate=Decimal("0.003"),  # ~$0.003 per share (varies by exchange)
        min_fee=Decimal("0.01"),
        applies_to_buy=True,
        applies_to_sell=True,
        description="Exchange fees for NYSE/NASDAQ execution",
    ),
    "platform_fee": FeeConfig(
        fee_type=FeeType.PLATFORM_FEE,
        rate=Decimal("0"),  # Often bundled with commission
        applies_to_buy=True,
        applies_to_sell=True,
        description="Platform or data fees (if applicable)",
    ),
}


@dataclass
class TransactionCost:
    """
    Complete breakdown of transaction costs.

    This represents all costs associated with a single trade execution.

    Attributes:
        commission: Broker commission
        sec_fee: SEC fee (only on sells)
        finra_taf: FINRA Trading Activity Fee
        exchange_fee: Exchange fees
        platform_fee: Platform/broker fees
        total_cost: Sum of all costs
    """

    commission: Decimal
    sec_fee: Decimal
    finra_taf: Decimal
    exchange_fee: Decimal
    platform_fee: Decimal
    total_cost: Decimal

    # Detailed breakdown for transparency
    fee_details: Dict[str, Decimal] = field(default_factory=dict)

    @property
    def regulatory_fees(self) -> Decimal:
        """Sum of all regulatory fees."""
        return self.sec_fee + self.finra_taf + self.exchange_fee

    @property
    def execution_fees(self) -> Decimal:
        """Sum of execution-related fees."""
        return self.commission + self.regulatory_fees

    def to_dict(self) -> Dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary with all cost components as float values.
        """
        return {
            "commission": float(self.commission),
            "sec_fee": float(self.sec_fee),
            "finra_taf": float(self.finra_taf),
            "exchange_fee": float(self.exchange_fee),
            "platform_fee": float(self.platform_fee),
            "total_cost": float(self.total_cost),
            "regulatory_fees": float(self.regulatory_fees),
            "execution_fees": float(self.execution_fees),
        }


@dataclass
class CostConfig:
    """
    Configuration for transaction cost calculator.

    Attributes:
        commission_per_share: Commission rate per share
        min_commission: Minimum commission per trade
        max_commission: Maximum commission per trade (None for unlimited)
        commission_type: Type of commission structure
        commission_tiers: Tiers for tiered commission (if applicable)
        use_sec_fee: Whether to apply SEC fee
        use_finra_taf: Whether to apply FINRA TAF
        use_exchange_fees: Whether to apply exchange fees
        custom_fees: Custom fee configurations
    """

    # Commission settings
    commission_per_share: Decimal = Decimal("0.005")  # $0.005 per share (half penny)
    min_commission: Decimal = Decimal("1.0")  # $1 minimum
    max_commission: Optional[Decimal] = None  # No maximum by default
    commission_type: CommissionType = CommissionType.FIXED_PER_SHARE

    # Tiered commission (for large accounts)
    commission_tiers: List[CommissionTier] = field(default_factory=list)

    # Regulatory fee flags
    use_sec_fee: bool = True
    use_finra_taf: bool = True
    use_exchange_fees: bool = True

    # Custom fees (for specific brokers/exchanges)
    custom_fees: Dict[str, FeeConfig] = field(default_factory=dict)


class TransactionCostCalculator:
    """
    Calculator for realistic US equity transaction costs.

    This implements the complete fee structure for US equity trading:

    1. Commission: Per-share or tiered commission
    2. SEC Fee: Section 31 fee on sells ($0.0000078 per dollar, capped at $5.95)
    3. FINRA TAF: $0.000145 per share traded
    4. Exchange Fees: ~$0.003 per share
    5. Platform fees: If applicable

    Example:
        calculator = TransactionCostCalculator()
        cost = calculator.calculate_cost(
            symbol="AAPL",
            side="buy",
            shares=100,
            price=Decimal("150.00"),
        )
        print(f"Total cost: ${cost.total_cost:.2f}")
    """

    def __init__(self, config: Optional[CostConfig] = None):
        """
        Initialize transaction cost calculator.

        Args:
            config: Cost configuration (uses defaults if not provided)
        """
        self.config = config or CostConfig()

        # Build fee lookup from config and defaults
        self.fees: Dict[str, FeeConfig] = {}
        self.fees.update(US_EQUITY_FEES)
        self.fees.update(self.config.custom_fees)

    def calculate_commission(
        self,
        shares: int,
        price: Decimal,
    ) -> Decimal:
        """
        Calculate commission based on share count and trade value.

        Args:
            shares: Number of shares
            price: Price per share

        Returns:
            Commission amount

        Raises:
            ValueError: If parameters are invalid
        """
        if shares <= 0:
            raise ValueError(f"Shares must be positive, got {shares}")

        if price <= 0:
            raise ValueError(f"Price must be positive, got {price}")

        commission = Decimal("0")

        if self.config.commission_type == CommissionType.FIXED_PER_SHARE:
            # Simple per-share commission
            commission = Decimal(str(shares)) * self.config.commission_per_share

        elif self.config.commission_type == CommissionType.PERCENTAGE:
            # Percentage of trade value
            trade_value = Decimal(str(shares)) * price
            commission = trade_value * self.config.commission_per_share

        elif self.config.commission_type == CommissionType.TIERED:
            # Tiered commission
            commission = self._calculate_tiered_commission(shares)

        elif self.config.commission_type == CommissionType.HYBRID:
            # Hybrid: percentage with minimum
            trade_value = Decimal(str(shares)) * price
            commission = trade_value * self.config.commission_per_share
            commission = max(commission, self.config.min_commission)

        else:
            logger.warning(f"Unknown commission type: {self.config.commission_type}")
            commission = Decimal(str(shares)) * self.config.commission_per_share

        # Apply minimum
        commission = max(commission, self.config.min_commission)

        # Apply maximum (if set)
        if self.config.max_commission is not None:
            commission = min(commission, self.config.max_commission)

        return commission.quantize(Decimal("0.01"))

    def _calculate_tiered_commission(self, shares: int) -> Decimal:
        """
        Calculate tiered commission.

        Args:
            shares: Number of shares

        Returns:
            Commission amount based on tiered structure
        """
        if not self.config.commission_tiers:
            # Fallback to simple per-share
            return Decimal(str(shares)) * self.config.commission_per_share

        commission = Decimal("0")
        remaining_shares = shares

        # Sort tiers by min_shares
        sorted_tiers = sorted(self.config.commission_tiers, key=lambda t: t.min_shares)

        for tier in sorted_tiers:
            if remaining_shares <= 0:
                break

            if shares >= tier.min_shares:
                # Calculate shares in this tier
                max_in_tier = min(tier.max_shares, shares) if tier.max_shares else shares
                shares_in_tier = min(remaining_shares, max_in_tier - tier.min_shares + 1)

                tier_commission = Decimal(str(shares_in_tier)) * tier.rate
                commission += max(tier_commission, tier.min_commission)

                remaining_shares -= shares_in_tier

        return commission

    def calculate_sec_fee(
        self,
        shares: int,
        price: Decimal,
    ) -> Decimal:
        """
        Calculate SEC Section 31 fee (only on sells).

        Fee rate: $0.0000078 per dollar of sales
        Maximum: $5.95 per sell transaction

        Args:
            shares: Number of shares
            price: Sale price per share

        Returns:
            SEC fee amount (0 for buy orders)
        """
        # SEC fee only applies to sells
        if self.config.use_sec_fee:
            sale_value = Decimal(str(shares)) * price
            sec_fee = sale_value * Decimal("0.0000078")

            # Apply cap
            sec_fee = min(sec_fee, Decimal("5.95"))

            # Apply minimum
            sec_fee = max(sec_fee, Decimal("0.01"))

            return sec_fee.quantize(Decimal("0.01"))

        return Decimal("0")

    def calculate_finra_taf(
        self,
        shares: int,
    ) -> Decimal:
        """
        Calculate FINRA Trading Activity Fee.

        Fee rate: $0.000145 per share traded
        Applies to both buys and sells

        Args:
            shares: Number of shares

        Returns:
            FINRA TAF amount
        """
        if self.config.use_finra_taf:
            taf = Decimal(str(shares)) * Decimal("0.000145")
            return taf.quantize(Decimal("0.01"))

        return Decimal("0")

    def calculate_exchange_fee(
        self,
        shares: int,
        exchange: Optional[str] = None,
    ) -> Decimal:
        """
        Calculate exchange fees.

        Approximate rate: $0.003 per share
        Varies by exchange (NYSE vs NASDAQ)

        Args:
            shares: Number of shares
            exchange: Exchange code (optional, uses default if not provided)

        Returns:
            Exchange fee amount
        """
        if not self.config.use_exchange_fees:
            return Decimal("0")

        # Default exchange fee (NYSE/NASDAQ average)
        fee_rate = Decimal("0.003")

        # Exchange-specific overrides (if needed)
        if exchange:
            exchange_rates = {
                "NYSE": Decimal("0.0030"),
                "NASDAQ": Decimal("0.0030"),
                "ARCA": Decimal("0.0030"),
                "BATS": Decimal("0.0025"),
            }
            fee_rate = exchange_rates.get(exchange.upper(), fee_rate)

        exchange_fee = Decimal(str(shares)) * fee_rate
        return exchange_fee.quantize(Decimal("0.01"))

    def calculate_platform_fee(
        self,
        shares: int,
        price: Decimal,
    ) -> Decimal:
        """
        Calculate platform or broker fees.

        Most brokers bundle this with commission, but some charge separately.

        Args:
            shares: Number of shares
            price: Price per share

        Returns:
            Platform fee amount
        """
        platform_config = self.fees.get("platform_fee")

        if platform_config:
            # Calculate based on configured rate
            trade_value = Decimal(str(shares)) * price
            fee = trade_value * platform_config.rate

            if platform_config.min_fee:
                fee = max(fee, platform_config.min_fee)

            if platform_config.max_fee:
                fee = min(fee, platform_config.max_fee)

            return fee.quantize(Decimal("0.01"))

        return Decimal("0")

    def calculate_cost(
        self,
        symbol: str,
        side: str,
        shares: int,
        price: Decimal,
        exchange: Optional[str] = None,
    ) -> TransactionCost:
        """
        Calculate total transaction cost for a trade.

        This includes:
        1. Commission (per-share or tiered)
        2. SEC fee (sells only)
        3. FINRA TAF (all trades)
        4. Exchange fees
        5. Platform fees (if applicable)

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            shares: Number of shares
            price: Price per share
            exchange: Exchange code (optional)

        Returns:
            TransactionCost with complete breakdown

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate inputs
        if shares <= 0:
            raise ValueError(f"Shares must be positive, got {shares}")

        if price <= 0:
            raise ValueError(f"Price must be positive, got {price}")

        side_lower = side.lower()
        if side_lower not in ("buy", "sell"):
            raise ValueError(f"Side must be 'buy' or 'sell', got '{side}'")

        # Calculate each cost component
        commission = self.calculate_commission(shares, price)
        sec_fee = self.calculate_sec_fee(shares, price) if side_lower == "sell" else Decimal("0")
        finra_taf = self.calculate_finra_taf(shares)
        exchange_fee = self.calculate_exchange_fee(shares, exchange)
        platform_fee = self.calculate_platform_fee(shares, price)

        # Sum all costs
        total_cost = commission + sec_fee + finra_taf + exchange_fee + platform_fee

        # Build fee details for transparency
        fee_details = {
            "commission": commission,
            "sec_fee": sec_fee,
            "finra_taf": finra_taf,
            "exchange_fee": exchange_fee,
            "platform_fee": platform_fee,
        }

        return TransactionCost(
            commission=commission,
            sec_fee=sec_fee,
            finra_taf=finra_taf,
            exchange_fee=exchange_fee,
            platform_fee=platform_fee,
            total_cost=total_cost,
            fee_details=fee_details,
        )

    def estimate_cost_range(
        self,
        symbol: str,
        side: str,
        shares: int,
        price_min: Decimal,
        price_max: Decimal,
    ) -> tuple[TransactionCost, TransactionCost]:
        """
        Estimate cost range for an order with price uncertainty.

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            shares: Number of shares
            price_min: Minimum expected price
            price_max: Maximum expected price

        Returns:
            Tuple of (min_cost, max_cost) TransactionCost objects
        """
        min_cost = self.calculate_cost(symbol, side, shares, price_min)
        max_cost = self.calculate_cost(symbol, side, shares, price_max)

        return min_cost, max_cost

    def get_cost_as_bps(
        self,
        cost: TransactionCost,
        trade_value: Decimal,
    ) -> Decimal:
        """
        Convert cost to basis points of trade value.

        Args:
            cost: Transaction cost
            trade_value: Total trade value (shares * price)

        Returns:
            Cost in basis points
        """
        if trade_value <= 0:
            return Decimal("0")

        return (cost.total_cost / trade_value) * Decimal("10000")

    def get_effective_cost(
        self,
        symbol: str,
        side: str,
        shares: int,
        price: Decimal,
        exchange: Optional[str] = None,
    ) -> Decimal:
        """
        Get effective all-in cost per share including all fees.

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            shares: Number of shares
            price: Price per share
            exchange: Exchange code

        Returns:
            Effective cost per share (added to price for buys, subtracted for sells)
        """
        cost = self.calculate_cost(symbol, side, shares, price, exchange)
        cost_per_share = cost.total_cost / Decimal(str(shares))

        return cost_per_share.quantize(Decimal("0.0001"))
