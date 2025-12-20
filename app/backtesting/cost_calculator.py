"""
Advanced Cost Calculator for Backtesting (TASK-CST-1, CST-2)

Calculates realistic trading costs including:
- Dynamic spreads (0.01-0.03% for stocks, higher for crypto/forex)
- Commission by asset type (0.01-0.05%)
- Market impact and slippage (0.02-0.1% additional)
- Total cost per trade (0.02-0.1% additional)
"""

import logging
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class AssetType(str, Enum):
    """Asset type for cost calculation."""

    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"


class CostCalculator:
    """
    Advanced cost calculator for backtesting (TASK-CST-1, CST-2).

    Provides realistic cost modeling with:
    - Dynamic spreads (0.01-0.03% for stocks)
    - Asset-type-specific commissions (0.01-0.05%)
    - Market impact and slippage (0.02-0.1%)
    - Total cost per trade calculation
    """

    # Spread ranges by asset type (percentage)
    SPREAD_RANGES = {
        AssetType.EQUITY: (Decimal("0.0001"), Decimal("0.0003")),  # 0.01-0.03%
        AssetType.CRYPTO: (Decimal("0.0005"), Decimal("0.002")),  # 0.05-0.2%
        AssetType.FOREX: (Decimal("0.0001"), Decimal("0.0005")),  # 0.01-0.05%
        AssetType.COMMODITY: (Decimal("0.0002"), Decimal("0.0005")),  # 0.02-0.05%
    }

    # Commission rates by asset type (percentage of trade value)
    COMMISSION_RATES = {
        AssetType.EQUITY: Decimal("0.0001"),  # 0.01% (typical for online brokers)
        AssetType.CRYPTO: Decimal("0.001"),  # 0.1%
        AssetType.FOREX: Decimal("0.0002"),  # 0.02%
        AssetType.COMMODITY: Decimal("0.0002"),  # 0.02%
    }

    # Slippage ranges by asset type (percentage)
    SLIPPAGE_RANGES = {
        AssetType.EQUITY: (Decimal("0.0002"), Decimal("0.001")),  # 0.02-0.1%
        AssetType.CRYPTO: (Decimal("0.0005"), Decimal("0.002")),  # 0.05-0.2%
        AssetType.FOREX: (Decimal("0.0001"), Decimal("0.0003")),  # 0.01-0.03%
        AssetType.COMMODITY: (Decimal("0.0003"), Decimal("0.001")),  # 0.03-0.1%
    }

    # Market impact multiplier (increases with order size)
    MARKET_IMPACT_BASE = Decimal("0.0001")  # 0.01% base

    def __init__(self, use_dynamic_costs: bool = True):
        """
        Initialize cost calculator.

        Args:
            use_dynamic_costs: If True, use dynamic spreads/slippage based on market conditions
        """
        self.use_dynamic_costs = use_dynamic_costs

    def detect_asset_type(self, symbol: str) -> AssetType:
        """
        Detect asset type from symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Asset type
        """
        symbol_upper = symbol.upper()

        # Crypto detection (common pairs)
        crypto_pairs = ["BTC", "ETH", "USDT", "USDC", "BNB", "ADA", "DOGE", "XRP"]
        if any(crypto in symbol_upper for crypto in crypto_pairs):
            return AssetType.CRYPTO

        # Forex detection (currency pairs)
        forex_patterns = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]
        if len(symbol) <= 6 and any(currency in symbol_upper for currency in forex_patterns):
            return AssetType.FOREX

        # Commodity detection
        commodities = ["GLD", "SLV", "OIL", "CL", "GC", "SI", "NG"]
        if any(c in symbol_upper for c in commodities):
            return AssetType.COMMODITY

        # Default to equity
        return AssetType.EQUITY

    def calculate_spread(
        self,
        asset_type: AssetType,
        volatility: Optional[Decimal] = None,
        liquidity: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate dynamic spread (TASK-CST-1: 0.01-0.03% for stocks).

        Args:
            asset_type: Type of asset
            volatility: Market volatility (0-1) to adjust spread
            liquidity: Market liquidity (volume) to adjust spread

        Returns:
            Spread as percentage (e.g., 0.0002 for 0.02%)
        """
        min_spread, max_spread = self.SPREAD_RANGES[asset_type]

        if not self.use_dynamic_costs:
            # Use midpoint
            return (min_spread + max_spread) / 2

        # Adjust based on volatility and liquidity
        base_spread = (min_spread + max_spread) / 2

        if volatility:
            # Higher volatility = wider spread
            volatility_factor = Decimal("1") + (volatility * Decimal("2"))  # Max 3x
            spread = base_spread * volatility_factor
        else:
            spread = base_spread

        if liquidity and liquidity < Decimal("1000000"):  # Low liquidity
            # Wider spread for illiquid assets
            spread = spread * Decimal("1.5")

        # Clamp to range
        spread = max(min_spread, min(max_spread, spread))

        return spread.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def calculate_commission(
        self,
        asset_type: AssetType,
        trade_value: Decimal,
    ) -> Decimal:
        """
        Calculate commission (TASK-CST-1: 0.01-0.05%).

        Args:
            asset_type: Type of asset
            trade_value: Value of the trade

        Returns:
            Commission amount
        """
        rate = self.COMMISSION_RATES[asset_type]
        commission = trade_value * rate

        # Minimum commission (e.g., $1 per trade)
        min_commission = Decimal("1.0")
        commission = max(min_commission, commission)

        return commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_slippage(
        self,
        asset_type: AssetType,
        trade_value: Decimal,
        order_size_pct: Optional[Decimal] = None,
        volatility: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate slippage (TASK-CST-1: dynamic based on market conditions).

        Args:
            asset_type: Type of asset
            trade_value: Value of the trade
            order_size_pct: Order size as % of average daily volume
            volatility: Market volatility

        Returns:
            Slippage amount
        """
        min_slippage, max_slippage = self.SLIPPAGE_RANGES[asset_type]

        if not self.use_dynamic_costs:
            slippage_rate = (min_slippage + max_slippage) / 2
        else:
            # Adjust based on order size and volatility
            base_slippage = (min_slippage + max_slippage) / 2

            # Larger orders = more slippage
            if order_size_pct:
                size_factor = Decimal("1") + (order_size_pct * Decimal("5"))  # Up to 6x
                slippage_rate = base_slippage * min(size_factor, Decimal("6"))
            else:
                slippage_rate = base_slippage

            # Higher volatility = more slippage
            if volatility:
                volatility_factor = Decimal("1") + (volatility * Decimal("2"))
                slippage_rate = slippage_rate * volatility_factor

            # Clamp to range
            slippage_rate = max(min_slippage, min(max_slippage, slippage_rate))

        slippage = trade_value * slippage_rate

        return slippage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_market_impact(
        self,
        trade_value: Decimal,
        order_size_pct: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate market impact cost.

        Args:
            trade_value: Value of the trade
            order_size_pct: Order size as % of average daily volume

        Returns:
            Market impact amount
        """
        if not order_size_pct:
            return Decimal("0")

        # Market impact increases with order size
        impact_multiplier = Decimal("1") + (order_size_pct * Decimal("3"))  # Up to 4x
        market_impact = trade_value * self.MARKET_IMPACT_BASE * impact_multiplier

        return market_impact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_total_cost(
        self,
        symbol: str,
        trade_value: Decimal,
        is_buy: bool,
        volatility: Optional[Decimal] = None,
        liquidity: Optional[Decimal] = None,
        order_size_pct: Optional[Decimal] = None,
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate total cost per trade (TASK-CST-2: 0.02-0.1% additional).

        Returns:
            Tuple of (total_cost, execution_price_adjustment)
            - total_cost: Total cost in dollars
            - execution_price_adjustment: Price adjustment for spread (percentage)
        """
        asset_type = self.detect_asset_type(symbol)

        # Calculate spread
        spread = self.calculate_spread(asset_type, volatility, liquidity)

        # Apply spread to execution price
        # Buy: pay more (ask price), Sell: receive less (bid price)
        if is_buy:
            execution_price_adjustment = spread  # Add spread for buy
        else:
            execution_price_adjustment = -spread  # Subtract spread for sell

        # Calculate commission
        commission = self.calculate_commission(asset_type, trade_value)

        # Calculate slippage
        slippage = self.calculate_slippage(asset_type, trade_value, order_size_pct, volatility)

        # Calculate market impact
        market_impact = self.calculate_market_impact(trade_value, order_size_pct)

        # Total cost (TASK-CST-2: includes all costs)
        total_cost = commission + slippage + market_impact

        # Additional cost percentage (for reporting)
        additional_cost_pct = (
            (total_cost / trade_value) * Decimal("100") if trade_value > 0 else Decimal("0")
        )

        logger.debug(
            f"Cost breakdown for {symbol} ({asset_type.value}): "
            f"spread={spread*100:.3f}%, commission=${commission:.2f}, "
            f"slippage=${slippage:.2f}, impact=${market_impact:.2f}, "
            f"total=${total_cost:.2f} ({additional_cost_pct:.3f}%)"
        )

        return total_cost, execution_price_adjustment

    def apply_execution_costs(
        self,
        base_price: Decimal,
        symbol: str,
        is_buy: bool,
        volatility: Optional[Decimal] = None,
        liquidity: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Apply execution costs to base price.

        Args:
            base_price: Base market price
            symbol: Trading symbol
            is_buy: True for buy orders, False for sell
            volatility: Market volatility
            liquidity: Market liquidity

        Returns:
            Adjusted execution price
        """
        asset_type = self.detect_asset_type(symbol)
        spread = self.calculate_spread(asset_type, volatility, liquidity)

        if is_buy:
            # Buy at ask (higher price)
            return base_price * (Decimal("1") + spread)
        else:
            # Sell at bid (lower price)
            return base_price * (Decimal("1") - spread)
