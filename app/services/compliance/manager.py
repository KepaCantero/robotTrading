"""
Compliance Manager - Centralized compliance tracking.

Manages all regulatory compliance requirements:
- PDT rule enforcement (USA)
- Wash sale tracking (USA)
- Order pattern analysis
- Geographic restrictions
- KYC verification

This is the main interface for compliance checking in the trading system.

Usage:
    from app.services.compliance import ComplianceManager, Country, TradeRecord

    # Create compliance manager for Spain
    compliance = ComplianceManager(country=Country.ES)

    # Check if trade is allowed
    trade = TradeRecord(
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("100"),
        price=Decimal("150"),
        trade_date=date.today(),
    )

    allowed, violations = compliance.check_trade_allowed(
        trade=trade,
        account_equity=Decimal("100000"),
    )

    if not allowed:
        logger.warning(f"Trade rejected: {violations}")
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from app.services.compliance.pdt_tracker import (
    Country,
    PDTTracker,
    PDTStatus,
)
from app.services.compliance.wash_sale_tracker import (
    WashSaleTracker,
)
from app.services.compliance.order_pattern_analyzer import (
    OrderPatternAnalyzer,
)


logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a trade for compliance tracking."""

    symbol: str
    side: str  # BUY or SELL
    quantity: Decimal
    price: Decimal
    trade_date: date
    order_id: Optional[str] = None
    is_day_trade: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": str(self.quantity),
            "price": str(self.price),
            "trade_date": self.trade_date.isoformat(),
            "order_id": self.order_id,
            "is_day_trade": self.is_day_trade,
        }


@dataclass
class ComplianceViolation:
    """Record of a compliance violation."""

    violation_type: str
    severity: str  # INFO, WARNING, CRITICAL
    description: str
    timestamp: datetime
    trade_reference: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "violation_type": self.violation_type,
            "severity": self.severity,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "trade_reference": self.trade_reference,
        }


@dataclass
class ComplianceReport:
    """Compliance status report."""

    country: str
    account_equity: Decimal
    pdt_status: Optional[PDTStatus] = None
    wash_sale_count: int = 0
    wash_sale_disallowed_loss: Decimal = Decimal("0")
    order_pattern_alerts: int = 0
    active_violations: List[ComplianceViolation] = field(default_factory=list)
    can_day_trade: bool = True
    restricted: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "country": self.country,
            "account_equity": str(self.account_equity),
            "pdt_status": self.pdt_status.to_dict() if self.pdt_status else None,
            "wash_sale_count": self.wash_sale_count,
            "wash_sale_disallowed_loss": str(self.wash_sale_disallowed_loss),
            "order_pattern_alerts": self.order_pattern_alerts,
            "active_violations": [v.to_dict() for v in self.active_violations],
            "can_day_trade": self.can_day_trade,
            "restricted": self.restricted,
        }


class ComplianceManager:
    """
    Manage all compliance tracking.

    Routes to appropriate trackers based on country.
    Provides unified interface for compliance checking.

    Usage:
        # Spain (no PDT, no wash sale)
        compliance_es = ComplianceManager(country=Country.ES)

        # USA (PDT and wash sale rules apply)
        compliance_us = ComplianceManager(country=Country.US)

        # Check trade
        allowed, violations = compliance_es.check_trade_allowed(
            trade=trade,
            account_equity=Decimal("100000"),
        )
    """

    def __init__(
        self,
        country: Country = Country.ES,
        account_equity: Optional[Decimal] = None,
    ):
        """
        Initialize compliance manager.

        Args:
            country: Country for compliance rules
            account_equity: Initial account equity
        """
        self.country = country
        self.account_equity = account_equity or Decimal("0")

        # Initialize trackers
        self.pdt_tracker = PDTTracker(country)
        self.wash_sale_tracker = WashSaleTracker(country)
        self.order_analyzer = OrderPatternAnalyzer()

        # Violation tracking
        self._violations: List[ComplianceViolation] = []

        logger.info(
            f"ComplianceManager initialized for {country.value} "
            f"with equity ${self.account_equity:,.2f}"
        )

    def check_trade_allowed(
        self,
        trade: TradeRecord,
        account_equity: Optional[Decimal] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Check if trade is allowed under compliance rules.

        This is the main method to call before executing a trade.
        It checks all applicable compliance rules.

        Args:
            trade: Trade to check
            account_equity: Current account equity (optional, uses default if not provided)

        Returns:
            Tuple of (allowed, list of violations)

        Examples:
            >>> compliance = ComplianceManager(country=Country.US)
            >>> trade = TradeRecord(
            ...     symbol="AAPL",
            ...     side="BUY",
            ...     quantity=Decimal("100"),
            ...     price=Decimal("150"),
            ...     trade_date=date.today(),
            ... )
            >>> allowed, violations = compliance.check_trade_allowed(
            ...     trade=trade,
            ...     account_equity=Decimal("30000"),
            ... )
            >>> allowed
            True
        """
        violations = []

        # Update equity if provided
        if account_equity is not None:
            self.account_equity = account_equity

        # Check PDT (USA only)
        if self.country == Country.US:
            allowed, message = self.pdt_tracker.check_pdt_limit(
                account_equity=self.account_equity,
                symbol=trade.symbol,
                side=trade.side,
            )
            if not allowed:
                violations.append(message)
                self._record_violation(
                    "PDT_RESTRICTION",
                    "CRITICAL",
                    message,
                    trade.symbol,
                )

        # Check order patterns (all countries)
        patterns = self.order_analyzer.analyze_order(
            trade.symbol,
            trade.side,
            trade.quantity,
            trade.price,
            "MARKET",
        )

        if patterns:
            pattern_msg = f"Suspicious patterns: {', '.join(patterns)}"
            violations.append(pattern_msg)
            self._record_violation(
                "ORDER_PATTERN",
                "WARNING",
                pattern_msg,
                trade.symbol,
            )

        # Check wash sale (USA only, on SELL orders)
        if self.country == Country.US and trade.side == "SELL":
            is_wash = self.wash_sale_tracker.is_wash_sale(
                trade.symbol,
                trade.trade_date,
                trade.price,
            )
            if is_wash:
                wash_msg = (
                    f"Wash sale detected: {trade.symbol} - "
                    f"loss may be disallowed"
                )
                violations.append(wash_msg)
                self._record_violation(
                    "WASH_SALE",
                    "INFO",
                    wash_msg,
                    trade.symbol,
                )

        return len(violations) == 0, violations

    def record_trade(self, trade: TradeRecord) -> None:
        """
        Record a trade for compliance tracking.

        Call this after a trade is executed to update compliance records.

        Args:
            trade: Trade to record
        """
        # Record in PDT tracker
        self.pdt_tracker.record_trade(
            symbol=trade.symbol,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
            trade_date=trade.trade_date,
        )

        # Record in wash sale tracker
        self.wash_sale_tracker.record_trade(
            symbol=trade.symbol,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
            trade_date=trade.trade_date,
        )

        # Record order for pattern analysis
        if trade.order_id:
            self.order_analyzer.record_order(
                order_id=trade.order_id,
                symbol=trade.symbol,
                side=trade.side,
                quantity=trade.quantity,
                price=trade.price,
                order_type="MARKET",
            )

        logger.info(
            f"Trade recorded for compliance: {trade.side} {trade.quantity} "
            f"{trade.symbol} @ ${trade.price}"
        )

    def generate_report(self) -> ComplianceReport:
        """
        Generate comprehensive compliance report.

        Returns:
            ComplianceReport with current status
        """
        # Get PDT status
        pdt_status = None
        if self.country == Country.US:
            pdt_status = self.pdt_tracker.get_status(self.account_equity)

        # Get wash sale summary
        wash_summary = self.wash_sale_tracker.get_wash_sale_summary()

        # Get pattern alerts
        pattern_alerts = self.order_analyzer.get_alerts()

        # Check if restricted
        restricted = False
        if pdt_status and pdt_status.is_restricted:
            restricted = True

        return ComplianceReport(
            country=self.country.value,
            account_equity=self.account_equity,
            pdt_status=pdt_status,
            wash_sale_count=wash_summary.get("total_wash_sales", 0),
            wash_sale_disallowed_loss=Decimal(
                wash_summary.get("total_disallowed_loss", "0")
            ),
            order_pattern_alerts=len(pattern_alerts),
            active_violations=self._violations.copy(),
            can_day_trade=not restricted,
            restricted=restricted,
        )

    def can_day_trade(self) -> bool:
        """
        Check if account can day trade.

        Returns:
            True if day trading is allowed
        """
        if self.country != Country.US:
            return True  # No PDT rule outside US

        status = self.pdt_tracker.get_status(self.account_equity)
        return not status.is_restricted

    def get_day_trades_remaining(self) -> int:
        """
        Get number of day trades remaining (USA only).

        Returns:
            Number of day trades remaining in 5-day period
        """
        if self.country != Country.US:
            return 999  # No limit outside US

        status = self.pdt_tracker.get_status(self.account_equity)
        return max(0, status.max_day_trades_allowed - status.day_trades_last_5_days)

    def get_violations(
        self,
        severity: Optional[str] = None,
    ) -> List[ComplianceViolation]:
        """
        Get compliance violations.

        Args:
            severity: Optional severity filter

        Returns:
            List of violations
        """
        if severity:
            return [v for v in self._violations if v.severity == severity]
        return self._violations.copy()

    def clear_violations(self) -> None:
        """Clear all violations (for testing/admin)."""
        self._violations.clear()
        logger.info("Compliance violations cleared")

    def update_equity(self, new_equity: Decimal) -> None:
        """
        Update account equity.

        Args:
            new_equity: New account equity
        """
        self.account_equity = new_equity
        logger.info(f"Account equity updated to ${new_equity:,.2f}")

    def _record_violation(
        self,
        violation_type: str,
        severity: str,
        description: str,
        trade_reference: Optional[str] = None,
    ) -> None:
        """Record a compliance violation."""
        violation = ComplianceViolation(
            violation_type=violation_type,
            severity=severity,
            description=description,
            timestamp=datetime.now(),
            trade_reference=trade_reference,
        )

        self._violations.append(violation)

        # Log based on severity
        if severity == "CRITICAL":
            logger.error(f"Compliance violation: {description}")
        elif severity == "WARNING":
            logger.warning(f"Compliance warning: {description}")
        else:
            logger.info(f"Compliance info: {description}")

    def reset(self) -> None:
        """Reset all tracking (for testing)."""
        self.pdt_tracker.reset()
        self.wash_sale_tracker.reset()
        self.order_analyzer.reset()
        self._violations.clear()

        logger.info("ComplianceManager reset")
