"""
T16.1.3: RiskGates - Pre-trade risk validation

Validates orders against risk limits before execution:
- Position size limits
- Leverage limits
- Maximum drawdown limits
- Daily loss limits (Chan #15: 5% daily loss circuit breaker)
- Concentration limits



References:
    - Chan #15: Circuit breaker 5% daily loss limit
    - Hull #65: Kill switches and circuit breakers

Uses centralized configuration from app.shared.config.centralized_config.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

from fastapi import Depends

from app.shared.config.centralized_config import get_config

from .broker_connector import BrokerConnector, OrderSide, get_broker_connector

_DEFAULT_DEPENDS = Depends(get_broker_connector)

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __lt__(self, other):
        if not isinstance(other, RiskLevel):
            return NotImplemented
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return order[self.value] < order[other.value]

    def __le__(self, other):
        if not isinstance(other, RiskLevel):
            return NotImplemented
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return order[self.value] <= order[other.value]

    def __gt__(self, other):
        if not isinstance(other, RiskLevel):
            return NotImplemented
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return order[self.value] > order[other.value]

    def __ge__(self, other):
        if not isinstance(other, RiskLevel):
            return NotImplemented
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return order[self.value] >= order[other.value]


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
    violations: list[str] = None
    warnings: list[str] = None

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
        """Initialize risk gates with centralized configuration."""
        self.broker = broker or get_broker_connector()

        # Load risk limits from centralized configuration
        config = get_config()
        thresholds = config.trading

        # Risk limits from centralized config (with fallback defaults)
        self.max_position_size = Decimal("50000")  # Max € per position (absolute value)
        self.max_leverage = Decimal("2.0")  # Max 2x leverage
        self.max_concentration = Decimal(str(thresholds.max_sector_exposure))  # From config: 0.30
        self.max_daily_loss = Decimal(str(thresholds.daily_loss_limit))  # From config: 0.05
        self.max_drawdown = Decimal(str(thresholds.max_drawdown_limit))  # From config: 0.15
        self.min_cash_reserve = Decimal(str(1 - thresholds.max_total_exposure))  # Derived: 0.20

        # Additional risk parameters from config
        self.stop_loss_pct = Decimal(str(thresholds.stop_loss_pct))  # From config: 0.05
        self.max_risk_per_trade = getattr(config.trading, "max_risk_per_trade", 0.02)
        self.circuit_breaker_daily_loss = Decimal(  # Chan #15: 5% daily loss circuit breaker
            str(thresholds.circuit_breaker_daily_loss)
        )  # 0.03
        self.circuit_breaker_drawdown = Decimal(str(thresholds.circuit_breaker_drawdown))  # 0.10

        # Tracking
        # Chan #15: 5% Daily Loss Circuit Breaker
        self.start_of_day_capital = Decimal(
            "0"
        )  # Track starting capital for daily loss calculations
        self.daily_pnl = Decimal("0")
        self.max_intraday_value = Decimal("0")
        self.current_drawdown = Decimal("0")
        self.circuit_breaker_active = False

        logger.info(
            f"✅ RiskGates initialized with centralized config "
            f"(max_daily_loss={self.max_daily_loss:.1%}, max_drawdown={self.max_drawdown:.1%})"
        )

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

        # CRITICAL CHECK 0: Circuit breaker
        if self.circuit_breaker_active:
            violations.append("Trading halted: circuit breaker active due to excessive losses")
            return RiskCheckResult(False, RiskLevel.CRITICAL, violations)

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
        if side == OrderSide.BUY and order_value > account.buying_power:
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

        # Check 6: Daily loss limit (CRITICAL)
        daily_loss_passed, daily_loss_msg = await self.check_daily_loss(abs(self.daily_pnl))
        if not daily_loss_passed:
            violations.append(daily_loss_msg)
            risk_level = RiskLevel.CRITICAL
            # Activate circuit breaker
            self._activate_circuit_breaker("daily_loss_exceeded")

        # Check 7: Drawdown limit (CRITICAL)
        if self.max_intraday_value > 0:
            drawdown_passed, drawdown_msg = await self.check_drawdown(
                account.portfolio_value, self.max_intraday_value
            )
            if not drawdown_passed:
                violations.append(drawdown_msg)
                risk_level = RiskLevel.CRITICAL
                # Activate circuit breaker
                self._activate_circuit_breaker("drawdown_exceeded")

        # Update max intraday value for drawdown tracking
        if account.portfolio_value > self.max_intraday_value:
            self.max_intraday_value = account.portfolio_value

        passed = len(violations) == 0
        return RiskCheckResult(passed, risk_level, violations, warnings)

    def _activate_circuit_breaker(self, reason: str) -> None:
        """Activate circuit breaker to halt all trading."""
        if not self.circuit_breaker_active:
            self.circuit_breaker_active = True
            logger.critical(f"CIRCUIT BREAKER ACTIVATED: {reason}")

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker (manual override only)."""
        self.circuit_breaker_active = False
        self.daily_pnl = Decimal("0")
        self.max_intraday_value = Decimal("0")
        logger.warning("Circuit breaker RESET - trading resumed")

    def update_daily_pnl(self, pnl_change: Decimal) -> None:
        """
        Update daily P&L tracking.

        Note: This method only tracks P&L. Use check_daily_loss_limit()
        to actually trigger the circuit breaker when needed (Chan #15).
        """
        self.daily_pnl += pnl_change

    def check_daily_loss_limit(self) -> bool:
        """
        Detener trading si pérdida diaria > 5%.

        Referencias:
            - Chan #15: Circuit breaker 5% daily
            - Hull #65: Kill switches

        Returns:
            bool: True si trading puede continuar, False si debe detenerse
        """
        # First check if circuit breaker is already active
        if self.circuit_breaker_active:
            return False

        # Calculate daily P&L percentage
        if self.start_of_day_capital <= 0:
            logger.warning("Start of day capital not set, cannot check daily loss limit")
            return True

        daily_pnl = self.daily_pnl
        daily_loss_pct = daily_pnl / self.start_of_day_capital

        if daily_loss_pct <= -0.05:  # -5% threshold per Chan #15
            logger.critical(
                f"🛑 CIRCUIT BREAKER (Chan #15): Daily loss {daily_loss_pct:.1%} > 5% threshold"
            )
            self._activate_circuit_breaker(f"daily_loss_{daily_loss_pct:.1%}")
            self.halt_trading()
            return False

        return True

    def halt_trading(self) -> None:
        """Halt all trading activity (Hull #65: Kill switch)."""
        self._activate_circuit_breaker("halt_trading_called")
        logger.critical("TRADING HALTED: halt_trading() was called")

    def set_start_of_day_capital(self, capital: Decimal) -> None:
        """Set the starting capital for daily loss tracking (Chan #15)."""
        self.start_of_day_capital = capital
        self.daily_pnl = Decimal("0")
        self.max_intraday_value = capital
        logger.info(f"Start of day capital set to ${capital:,.2f}")

    async def check_daily_loss(self, daily_loss: Decimal) -> tuple[bool, str]:
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

    async def check_drawdown(self, current_value: Decimal, peak_value: Decimal) -> tuple[bool, str]:
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
    ) -> tuple[bool, Optional[Decimal]]:
        """
        Check if target position quantity is within limits.

        Args:
            symbol: Stock symbol
            target_quantity: Target number of shares

        Returns:
            (passed, adjusted_quantity)
        """
        positions = await self.broker.get_positions()
        current_qty = positions.get(symbol)
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
        sector_allocations: dict[str, Decimal],
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
        positions: dict[str, Decimal],  # symbol → allocation
        correlations: dict[tuple[str, str], Decimal],  # (symbol1, symbol2) → correlation
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
    broker: BrokerConnector = _DEFAULT_DEPENDS,
) -> RiskGates:
    """Get or create singleton RiskGates."""
    global _gates
    if _gates is None:
        _gates = RiskGates(broker=broker)

    return _gates
