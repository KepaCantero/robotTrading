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


class CostCalculatorError(ValueError):
    """Raised when cost calculation parameters are invalid."""



class AssetType(str, Enum):
    """Asset type for cost calculation."""

    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"


class CostCalculator:
    """
    Advanced cost calculator for backtesting (TASK-CST-1, CST-2, Req #9).

    Provides realistic cost modeling with:
    - Dynamic spreads (0.01-0.03% for stocks)
    - Asset-type-specific commissions (0.01-0.05%)
    - Market impact and slippage (0.02-0.1%)
    - Total cost per trade calculation
    - ADV-based slippage model (Req #9): Slippage = Base + (Order_Size/ADV)^2 * Coef
    - Volatility multiplier (Req #9): VIX > 30 = slippage x2
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
    # Req #9: Large Caps 2-5 bps, Small Caps 10-25 bps
    SLIPPAGE_RANGES = {
        AssetType.EQUITY: (Decimal("0.0002"), Decimal("0.001")),  # 0.02-0.1%
        AssetType.CRYPTO: (Decimal("0.0005"), Decimal("0.002")),  # 0.05-0.2%
        AssetType.FOREX: (Decimal("0.0001"), Decimal("0.0003")),  # 0.01-0.03%
        AssetType.COMMODITY: (Decimal("0.0003"), Decimal("0.001")),  # 0.03-0.1%
    }

    # Market impact multiplier (increases with order size)
    MARKET_IMPACT_BASE = Decimal("0.0001")  # 0.01% base

    # Req #9: ADV-based slippage constants
    # Slippage_Bps = Base_Slippage + (Order_Size / ADV)^2 * Impact_Coefficient
    LARGE_CAP_BASE_SLIPPAGE_BPS = Decimal("3.5")  # 2-5 bps average for large caps
    SMALL_CAP_BASE_SLIPPAGE_BPS = Decimal("17.5")  # 10-25 bps average for small caps
    IMPACT_COEFFICIENT = Decimal("100")  # Multiplier for ADV impact

    # Req #9: Volatility thresholds
    VIX_HIGH_VOLATILITY_THRESHOLD = Decimal("30")  # VIX > 30
    VOLATILITY_MULTIPLIER_HIGH = Decimal("2")  # 2x slippage in high vol

    # Market cap classification (annual trading volume)
    LARGE_CAP_MIN_VOLUME = Decimal("1000000000")  # $1B+ daily volume
    SMALL_CAP_MAX_VOLUME = Decimal("100000000")  # <$100M daily volume

    def __init__(self, use_dynamic_costs: bool = True):
        """
        Initialize cost calculator.

        Args:
            use_dynamic_costs: If True, use dynamic spreads/slippage based on market conditions
        """
        self.use_dynamic_costs = use_dynamic_costs

    def _validate_positive_decimal(
        self, value: Decimal, name: str, allow_zero: bool = False
    ) -> None:
        """
        Validate that a Decimal value is positive.

        Args:
            value: Value to validate
            name: Parameter name for error messages
            allow_zero: Whether zero is allowed (default: False)

        Raises:
            CostCalculatorError: If validation fails
        """
        if value < 0:
            raise CostCalculatorError(f"{name} must be non-negative, got: {value}")

        if not allow_zero and value == 0:
            raise CostCalculatorError(f"{name} must be positive, got: {value}")

    def _validate_percentage(
        self, value: Optional[Decimal], name: str, max_value: Decimal = Decimal("1")
    ) -> None:
        """
        Validate that a value is a percentage (0-1 or 0-100).

        Args:
            value: Value to validate (None skips validation)
            name: Parameter name for error messages
            max_value: Maximum allowed value (default: 1 for 0-100%)

        Raises:
            CostCalculatorError: If validation fails
        """
        if value is None:
            return

        if value < 0:
            raise CostCalculatorError(f"{name} must be non-negative, got: {value}")

        if value > max_value:
            raise CostCalculatorError(f"{name} must be <= {max_value} (as decimal), got: {value}")

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

    def classify_market_cap(self, adv_value: Decimal) -> str:
        """
        Classify market cap based on ADV (Req #9).

        Args:
            adv_value: Average Daily Volume (20-day) in dollars

        Returns:
            "large_cap", "small_cap", or "mid_cap"
        """
        if adv_value >= self.LARGE_CAP_MIN_VOLUME:
            return "large_cap"
        elif adv_value <= self.SMALL_CAP_MAX_VOLUME:
            return "small_cap"
        else:
            return "mid_cap"

    def calculate_adv_based_slippage_bps(
        self,
        order_value: Decimal,
        adv_value: Decimal,
        vix: Optional[Decimal] = None,
        asset_type: AssetType = AssetType.EQUITY,
    ) -> Decimal:
        """
        Calculate ADV-based slippage in basis points (Req #9).

        Formula: Slippage_Bps = Base_Slippage + (Order_Size / ADV)^2 * Impact_Coefficient

        Args:
            order_value: Value of the order in dollars (must be > 0)
            adv_value: Average Daily Volume (20-day) in dollars (must be > 0)
            vix: Optional VIX index value for volatility multiplier
            asset_type: Type of asset being traded

        Returns:
            Slippage in basis points

        Raises:
            CostCalculatorError: If order_value or adv_value are invalid
        """
        # Validate inputs
        self._validate_positive_decimal(order_value, "order_value", allow_zero=False)

        # Handle zero or negative ADV: treat as "no ADV data available"
        # Use default slippage range instead of raising error
        if adv_value <= 0:
            # Use default slippage from SLIPPAGE_RANGES for the asset type
            min_slippage, max_slippage = self.SLIPPAGE_RANGES.get(
                asset_type, (Decimal("0.0002"), Decimal("0.0010"))
            )
            # Return average of range in bps
            default_slippage_bps = ((min_slippage + max_slippage) / 2) * Decimal("10000")
            logger.debug(f"ADV <= 0, using default slippage: {default_slippage_bps} bps")
            return default_slippage_bps

        # Determine base slippage based on market cap (Req #9)
        market_cap = self.classify_market_cap(adv_value)

        if market_cap == "large_cap":
            # Large caps: 2-5 bps base (using 3.5 bps average)
            base_slippage = self.LARGE_CAP_BASE_SLIPPAGE_BPS
        elif market_cap == "small_cap":
            # Small caps: 10-25 bps base (using 17.5 bps average)
            base_slippage = self.SMALL_CAP_BASE_SLIPPAGE_BPS
        else:  # mid_cap
            # Mid caps: interpolate between small and large
            base_slippage = (
                self.LARGE_CAP_BASE_SLIPPAGE_BPS + self.SMALL_CAP_BASE_SLIPPAGE_BPS
            ) / 2

        # Calculate order size as percentage of ADV
        order_size_pct = order_value / adv_value

        # Apply ADV impact formula (Req #9): (Order_Size / ADV)^2 * Impact_Coefficient
        adv_impact = (order_size_pct**2) * self.IMPACT_COEFFICIENT * Decimal("10000")  # To bps

        # Calculate total slippage
        total_slippage_bps = base_slippage + adv_impact

        # Apply volatility multiplier (Req #9): VIX > 30 = slippage x2
        if vix and vix > self.VIX_HIGH_VOLATILITY_THRESHOLD:
            total_slippage_bps = total_slippage_bps * self.VOLATILITY_MULTIPLIER_HIGH
            logger.debug(f"High VIX ({vix}): Slippage doubled to {total_slippage_bps} bps")

        return total_slippage_bps

    def calculate_adv_based_slippage(
        self,
        asset_type: AssetType,
        trade_value: Decimal,
        adv_value: Decimal,
        order_size_pct: Optional[Decimal] = None,
        volatility: Optional[Decimal] = None,
        vix: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate slippage using ADV-based model (Req #9).

        This is an enhanced version that uses the ADV-based formula.

        Args:
            asset_type: Type of asset
            trade_value: Value of the trade
            adv_value: Average Daily Volume (20-day) in dollars
            order_size_pct: Order size as % of ADV (calculated if not provided)
            volatility: Market volatility (deprecated, use vix instead)
            vix: VIX index value for volatility multiplier

        Returns:
            Slippage amount in dollars
        """
        # Calculate slippage in bps using ADV model
        slippage_bps = self.calculate_adv_based_slippage_bps(
            order_value=trade_value,
            adv_value=adv_value,
            vix=vix,
            asset_type=asset_type,
        )

        # Convert bps to dollar amount
        slippage = trade_value * slippage_bps / Decimal("10000")

        return slippage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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
            trade_value: Value of the trade (>= 0)

        Returns:
            Commission amount (0 if trade_value is 0)

        Raises:
            CostCalculatorError: If trade_value is invalid
        """
        # Allow zero trade value (e.g., zero quantity orders)
        if trade_value <= 0:
            return Decimal("0")

        self._validate_positive_decimal(trade_value, "trade_value", allow_zero=False)

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
            trade_value: Value of the trade (must be > 0)
            order_size_pct: Order size as % of average daily volume (0-1)
            volatility: Market volatility (0-1 range recommended)

        Returns:
            Slippage amount

        Raises:
            CostCalculatorError: If trade_value or order_size_pct are invalid
        """
        self._validate_positive_decimal(trade_value, "trade_value", allow_zero=False)
        self._validate_percentage(order_size_pct, "order_size_pct", max_value=Decimal("1"))

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
            trade_value: Value of the trade (must be > 0)
            order_size_pct: Order size as % of average daily volume (0-1)

        Returns:
            Market impact amount

        Raises:
            CostCalculatorError: If trade_value is invalid
        """
        self._validate_positive_decimal(trade_value, "trade_value", allow_zero=False)
        self._validate_percentage(order_size_pct, "order_size_pct", max_value=Decimal("1"))

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
            base_price: Base market price (must be > 0)
            symbol: Trading symbol
            is_buy: True for buy orders, False for sell
            volatility: Market volatility
            liquidity: Market liquidity

        Returns:
            Adjusted execution price

        Raises:
            CostCalculatorError: If base_price is invalid
        """
        self._validate_positive_decimal(base_price, "base_price", allow_zero=False)

        asset_type = self.detect_asset_type(symbol)
        spread = self.calculate_spread(asset_type, volatility, liquidity)

        if is_buy:
            # Buy at ask (higher price)
            return base_price * (Decimal("1") + spread)
        else:
            # Sell at bid (lower price)
            return base_price * (Decimal("1") - spread)
