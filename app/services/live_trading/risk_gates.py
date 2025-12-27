"""
T16.1.3: RiskGates - Pre-trade risk validation

Validates orders against risk limits before execution:
- Position size limits
- Leverage limits
- Maximum drawdown limits
- Daily loss limits
- Concentration limits
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple

from fastapi import Depends

from .broker_connector import BrokerConnector, OrderSide, get_broker_connector

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskLimit:
    """Risk limit configuration."""

    name: str
    enabled: bool
    threshold: Decimal
    current_value: Decimal = Decimal("0")
    risk_level: RiskLevel = RiskLevel.LOW
    is_breached: bool = False


@dataclass
class RiskCheckResult:
    """Result of risk check."""

    passed: bool
    risk_level: RiskLevel
    violations: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.violations is None:
            self.violations = []
        if self.warnings is None:
            self.warnings = []


class RiskGates:
    """
    Pre-trade risk validation system.

    Features:
    - Position size validation
    - Leverage limits
    - Portfolio concentration checks
    - Daily loss limits
    - Maximum drawdown protection
    """

    def __init__(self, broker: Optional[BrokerConnector] = None):
        """Initialize risk gates."""
        self.broker = broker or get_broker_connector()

        # Risk limits (default values)
        self.max_position_size = Decimal("50000")  # Max € per position
        self.max_leverage = Decimal("2.0")  # Max 2x leverage
        self.max_concentration = Decimal("0.15")  # Max 15% in single position
        self.max_daily_loss = Decimal("0.05")  # Max 5% daily loss
        self.max_drawdown = Decimal("0.20")  # Max 20% drawdown
        self.min_cash_reserve = Decimal("0.10")  # Keep 10% cash

        # Tracking
        self.daily_pnl = Decimal("0")
        self.max_intraday_value = Decimal("0")
        self.current_drawdown = Decimal("0")

        logger.info("✅ RiskGates initialized")

    async def validate_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
    ) -> RiskCheckResult:
        """
        Validate order against risk limits.

        Args:
            symbol: Stock symbol
            side: BUY or SELL
            quantity: Number of shares
            price: Order price

        Returns:
            RiskCheckResult
        """
        violations = []
        warnings = []
        risk_level = RiskLevel.LOW

        # Get account info
        account = await self.broker.get_account_info()
        if not account:
            violations.append("Cannot access account information")
            return RiskCheckResult(False, RiskLevel.CRITICAL, violations)

        # Get current positions
        await self.broker.get_positions()

        # Check 1: Position size
        order_value = quantity * price
        if order_value > self.max_position_size:
            violations.append(
                f"Order value €{order_value} exceeds max position size €{self.max_position_size}"
            )
            risk_level = RiskLevel.HIGH

        # Check 2: Buying power (for buy orders)
        if side == OrderSide.BUY:
            if order_value > account.buying_power:
                violations.append(
                    f"Order value €{order_value} exceeds available buying power €{account.buying_power}"
                )
                risk_level = RiskLevel.CRITICAL

        # Check 3: Concentration
        portfolio_value = account.portfolio_value
        if portfolio_value > 0:
            position_weight = order_value / portfolio_value
            if position_weight > self.max_concentration:
                warnings.append(
                    f"Position weight {position_weight:.1%} exceeds target {self.max_concentration:.1%}"
                )
                risk_level = max(risk_level, RiskLevel.MEDIUM)

        # Check 4: Leverage
        if account.buying_power > 0:
            leverage = (
                account.portfolio_value / account.equity if account.equity > 0 else Decimal("1")
            )
            if leverage > self.max_leverage:
                violations.append(
                    f"Current leverage {leverage:.2f}x exceeds max {self.max_leverage:.2f}x"
                )
                risk_level = max(risk_level, RiskLevel.HIGH)

        # Check 5: Cash reserve (for sell orders, check if buy)
        if side == OrderSide.BUY:
            cash_pct = (
                account.cash_available / account.portfolio_value
                if account.portfolio_value > 0
                else Decimal("0")
            )
            if cash_pct < self.min_cash_reserve:
                warnings.append(
                    f"Cash reserve {cash_pct:.1%} below target {self.min_cash_reserve:.1%}"
                )

        passed = len(violations) == 0
        return RiskCheckResult(passed, risk_level, violations, warnings)

    async def check_daily_loss(self, daily_loss: Decimal) -> Tuple[bool, str]:
        """
        Check if daily loss limit exceeded.

        Args:
            daily_loss: Daily loss amount

        Returns:
            (passed, message)
        """
        account = await self.broker.get_account_info()
        if not account or account.equity <= 0:
            return False, "Cannot calculate daily loss"

        loss_pct = daily_loss / account.equity
        if loss_pct > self.max_daily_loss:
            return False, f"Daily loss {loss_pct:.1%} exceeds limit {self.max_daily_loss:.1%}"

        return True, "Daily loss within limits"

    async def check_drawdown(self, current_value: Decimal, peak_value: Decimal) -> Tuple[bool, str]:
        """
        Check if maximum drawdown exceeded.

        Args:
            current_value: Current portfolio value
            peak_value: Peak portfolio value

        Returns:
            (passed, message)
        """
        if peak_value <= 0:
            return True, "No drawdown data"

        drawdown = (peak_value - current_value) / peak_value
        self.current_drawdown = drawdown

        if drawdown > self.max_drawdown:
            return False, f"Drawdown {drawdown:.1%} exceeds limit {self.max_drawdown:.1%}"

        return True, f"Drawdown {drawdown:.1%} within limits"

    async def validate_position_limit(
        self,
        symbol: str,
        target_quantity: Decimal,
    ) -> Tuple[bool, Optional[Decimal]]:
        """
        Check if target position quantity is within limits.

        Args:
            symbol: Stock symbol
            target_quantity: Target number of shares

        Returns:
            (passed, adjusted_quantity)
        """
        positions = await self.broker.get_positions()
        current_qty = positions.get(symbol, None)
        current_qty = current_qty.quantity if current_qty else Decimal("0")

        # Max position quantity (assume €100 per share average)
        max_qty = self.max_position_size / Decimal("100")

        if target_quantity > max_qty:
            adjusted_qty = max_qty
            logger.warning(f"⚠️ Adjusted {symbol} quantity from {target_quantity} to {adjusted_qty}")
            return False, adjusted_qty

        return True, target_quantity

    async def check_sector_concentration(
        self,
        sector_allocations: Dict[str, Decimal],
    ) -> RiskCheckResult:
        """
        Check concentration by sector.

        Args:
            sector_allocations: Dict of sector → allocation percentage

        Returns:
            RiskCheckResult
        """
        violations = []
        max_sector_allocation = Decimal("0.30")  # Max 30% per sector

        for sector, allocation in sector_allocations.items():
            if allocation > max_sector_allocation:
                violations.append(
                    f"Sector {sector} allocation {allocation:.1%} exceeds max {max_sector_allocation:.1%}"
                )

        passed = len(violations) == 0
        risk_level = RiskLevel.HIGH if violations else RiskLevel.LOW

        return RiskCheckResult(passed, risk_level, violations)

    async def check_correlation_risk(
        self,
        positions: Dict[str, Decimal],  # symbol → allocation
        correlations: Dict[Tuple[str, str], Decimal],  # (symbol1, symbol2) → correlation
    ) -> RiskCheckResult:
        """
        Check portfolio correlation risk.

        Args:
            positions: Dict of symbol → allocation
            correlations: Dict of (symbol1, symbol2) → correlation coefficient

        Returns:
            RiskCheckResult
        """
        violations = []
        max_correlation = Decimal("0.85")  # Max 85% correlation between positions

        for (sym1, sym2), corr in correlations.items():
            if corr > max_correlation:
                violations.append(f"High correlation {corr:.2f} between {sym1} and {sym2}")

        passed = len(violations) == 0
        risk_level = RiskLevel.MEDIUM if violations else RiskLevel.LOW

        return RiskCheckResult(passed, risk_level, violations)

    def set_max_position_size(self, amount: Decimal) -> None:
        """Set maximum position size."""
        self.max_position_size = amount
        logger.info(f"✅ Max position size set to €{amount}")

    def set_max_leverage(self, leverage: Decimal) -> None:
        """Set maximum leverage."""
        self.max_leverage = leverage
        logger.info(f"✅ Max leverage set to {leverage:.2f}x")

    def set_max_daily_loss(self, loss_pct: Decimal) -> None:
        """Set maximum daily loss percentage."""
        self.max_daily_loss = loss_pct
        logger.info(f"✅ Max daily loss set to {loss_pct:.1%}")

    def set_max_drawdown(self, drawdown_pct: Decimal) -> None:
        """Set maximum drawdown percentage."""
        self.max_drawdown = drawdown_pct
        logger.info(f"✅ Max drawdown set to {drawdown_pct:.1%}")

    def get_current_drawdown(self) -> Decimal:
        """Get current drawdown."""
        return self.current_drawdown


# Singleton
_gates: Optional[RiskGates] = None


def get_risk_gates(
    broker: BrokerConnector = Depends(get_broker_connector),
) -> RiskGates:
    """Get or create singleton RiskGates."""
    global _gates
    if _gates is None:
        pass

    return _gates
