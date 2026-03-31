"""
P&L Validator for backtesting results.

Validates profit and loss calculations to ensure accuracy
and detect potential issues in backtesting results.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from app.backtesting.models import Trade, TradeStatus

logger = logging.getLogger(__name__)


class PnLValidationError(Exception):
    """Exception raised when P&L validation fails."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.details = details or {}


class PnLValidator:
    """
    Validate P&L calculations in backtesting results.

    Checks:
    - Trade P&L matches (entry_price - exit_price) * quantity
    - Commission calculations are correct
    - Total P&L matches sum of individual trades
    - No missing P&L values
    """

    # Validation thresholds
    MAX_PNL_DIFFERENCE_BPS = Decimal("1")  # Max 1 basis point difference
    MAX_COMMISSION_PCT = Decimal("0.01")  # Max 1% commission

    def __init__(
        self,
        max_difference_bps: Optional[Decimal] = None,
        max_commission_pct: Optional[Decimal] = None,
    ):
        """
        Initialize P&L Validator.

        Args:
            max_difference_bps: Max allowed difference in basis points
            max_commission_pct: Max allowed commission as percentage
        """
        self.max_difference_bps = max_difference_bps or self.MAX_PNL_DIFFERENCE_BPS
        self.max_commission_pct = max_commission_pct or self.MAX_COMMISSION_PCT

    def validate_trade_pnl(self, trade: Trade) -> bool:
        """
        Validate individual trade P&L calculation.

        Args:
            trade: Trade to validate

        Returns:
            True if P&L is valid

        Raises:
            PnLValidationError: If P&L validation fails
        """
        if trade.status != TradeStatus.CLOSED:
            return True  # Skip open trades

        if trade.pnl is None:
            raise PnLValidationError(
                f"Trade {trade.trade_id} has no P&L value",
                details={"trade_id": trade.trade_id},
            )

        if trade.entry_price is None or trade.exit_price is None:
            raise PnLValidationError(
                f"Trade {trade.trade_id} missing entry/exit price",
                details={"trade_id": trade.trade_id},
            )

        # Calculate expected P&L
        if trade.side.lower() in ("buy", "long"):
            expected_pnl = (trade.exit_price - trade.entry_price) * trade.quantity
        else:  # sell/short
            expected_pnl = (trade.entry_price - trade.exit_price) * trade.quantity

        # Apply commission (if available)
        commission = trade.commission or Decimal("0")
        expected_pnl -= commission

        # Compare with actual P&L
        difference = abs(trade.pnl - expected_pnl)
        difference_bps = (
            (difference / abs(expected_pnl) * 10000) if expected_pnl != 0 else Decimal("0")
        )

        if difference_bps > self.max_difference_bps:
            raise PnLValidationError(
                f"Trade {trade.trade_id} P&L mismatch: "
                f"expected {expected_pnl}, got {trade.pnl} "
                f"(diff: {difference_bps} bps)",
                details={
                    "trade_id": trade.trade_id,
                    "expected_pnl": float(expected_pnl),
                    "actual_pnl": float(trade.pnl),
                    "difference_bps": float(difference_bps),
                },
            )

        return True

    def validate_trades_pnl(self, trades: list[Trade]) -> tuple[bool, list[str]]:
        """
        Validate P&L for all trades.

        Args:
            trades: List of trades to validate

        Returns:
            Tuple of (all_valid, error_messages)
        """
        errors = []

        for trade in trades:
            try:
                self.validate_trade_pnl(trade)
            except PnLValidationError as e:
                errors.append(str(e))

        return len(errors) == 0, errors

    def validate_total_pnl(
        self,
        trades: list[Trade],
        reported_total: Decimal,
    ) -> bool:
        """
        Validate total P&L matches sum of individual trades.

        Args:
            trades: List of trades
            reported_total: Reported total P&L

        Returns:
            True if total matches

        Raises:
            PnLValidationError: If total doesn't match
        """
        calculated_total = sum(
            trade.pnl
            for trade in trades
            if trade.status == TradeStatus.CLOSED and trade.pnl is not None
        )

        difference = abs(reported_total - calculated_total)
        difference_bps = (
            (difference / abs(calculated_total) * 10000) if calculated_total != 0 else Decimal("0")
        )

        if difference_bps > self.max_difference_bps:
            raise PnLValidationError(
                f"Total P&L mismatch: reported {reported_total}, "
                f"calculated {calculated_total} (diff: {difference_bps} bps)",
                details={
                    "reported_total": float(reported_total),
                    "calculated_total": float(calculated_total),
                    "difference_bps": float(difference_bps),
                },
            )

        return True

    def validate_commission(
        self,
        trade_value: Decimal,
        commission: Decimal,
    ) -> bool:
        """
        Validate commission is reasonable.

        Args:
            trade_value: Total trade value
            commission: Commission charged

        Returns:
            True if commission is reasonable

        Raises:
            PnLValidationError: If commission is too high
        """
        if trade_value <= 0:
            return True

        commission_pct = commission / trade_value

        if commission_pct > self.max_commission_pct:
            raise PnLValidationError(
                f"Commission too high: {commission} on {trade_value} ({commission_pct * 100:.2f}%)",
                details={
                    "trade_value": float(trade_value),
                    "commission": float(commission),
                    "commission_pct": float(commission_pct),
                },
            )

        return True

    def validate_pnl_consistency(
        self,
        trades: list[Trade],
        initial_capital: Decimal,
        final_capital: Decimal,
    ) -> bool:
        """
        Validate P&L consistency with capital changes.

        Args:
            trades: List of closed trades
            initial_capital: Starting capital
            final_capital: Ending capital

        Returns:
            True if consistent

        Raises:
            PnLValidationError: If inconsistent
        """
        total_pnl = sum(
            trade.pnl
            for trade in trades
            if trade.status == TradeStatus.CLOSED and trade.pnl is not None
        )

        expected_final = initial_capital + total_pnl
        difference = abs(final_capital - expected_final)
        difference_bps = (
            (difference / abs(expected_final) * 10000) if expected_final != 0 else Decimal("0")
        )

        if difference_bps > self.max_difference_bps:
            raise PnLValidationError(
                f"Capital inconsistency: expected {expected_final}, "
                f"got {final_capital} (diff: {difference_bps} bps)",
                details={
                    "initial_capital": float(initial_capital),
                    "final_capital": float(final_capital),
                    "expected_final": float(expected_final),
                    "total_pnl": float(total_pnl),
                    "difference_bps": float(difference_bps),
                },
            )

        return True
