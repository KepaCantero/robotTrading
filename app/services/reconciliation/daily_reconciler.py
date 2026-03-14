"""
Daily Reconciliation Service

R16: Reconciliación Diaria - Reconcilia posición del sistema vs broker DÍARIAMENTE

This module provides daily reconciliation between broker positions and internal records
to detect discrepancies and ensure data consistency.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Position:
    """
    Position for reconciliation (R16)

    Represents a trading position from either broker or internal records.
    """

    symbol: str
    quantity: Decimal
    avg_price: Decimal
    current_price: Decimal
    market_value: Decimal
    currency: str = "EUR"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "quantity": str(self.quantity),
            "avg_price": str(self.avg_price),
            "current_price": str(self.current_price),
            "market_value": str(self.market_value),
            "currency": self.currency,
        }


@dataclass
class ReconciliationResult:
    """
    Result of daily reconciliation (R16)

    Contains summary statistics and detailed discrepancies found during
    broker vs internal position reconciliation.
    """

    date: date
    total_positions: int
    matched_positions: int
    mismatched_positions: int
    missing_positions: int
    discrepancies: list[dict] = field(default_factory=list)
    is_balanced: bool = False
    reconciled_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "date": self.date.isoformat(),
            "total_positions": self.total_positions,
            "matched_positions": self.matched_positions,
            "mismatched_positions": self.mismatched_positions,
            "missing_positions": self.missing_positions,
            "discrepancies": self.discrepancies,
            "is_balanced": self.is_balanced,
            "reconciled_at": self.reconciled_at.isoformat(),
        }


class DailyReconciler:
    """
    Daily position reconciler (R16)

    Compares broker positions with internal records and detects discrepancies.
    This is critical for data integrity and risk management.

    Tolerances:
    - Quantity: ±1 share
    - Price: ±0.1%

    Example:
        reconciler = DailyReconciler()
        result = await reconciler.reconcile_positions(
            broker_positions=[...],
            internal_positions=[...]
        )
        if not result.is_balanced:
            logger.warning(f"Found {result.mismatched_positions} mismatches")
    """

    # Tolerances (R16)
    QUANTITY_TOLERANCE = Decimal("1")  # 1 share
    PRICE_TOLERANCE_PCT = Decimal("0.001")  # 0.1%

    def __init__(self) -> None:
        """Initialize the daily reconciler"""
        self._broker_positions: dict[str, Position] = {}
        self._internal_positions: dict[str, Position] = {}
        logger.debug(
            "DailyReconciler initialized",
            extra={"component": "reconciliation", "action": "init"},
        )

    async def reconcile_positions(
        self, broker_positions: list[Position], internal_positions: list[Position]
    ) -> ReconciliationResult:
        """
        Reconcile broker positions vs internal positions (R16)

        This is the main reconciliation method that compares positions from
        the broker API with internal database records and identifies discrepancies.

        Args:
            broker_positions: Positions from broker API
            internal_positions: Positions from internal database

        Returns:
            ReconciliationResult with detailed discrepancy information

        Example:
            result = await reconciler.reconcile_positions(
                broker_positions=[Position("SAN.MC", Decimal("100"), ...)],
                internal_positions=[Position("SAN.MC", Decimal("100"), ...)]
            )
        """
        logger.info(
            "Starting position reconciliation",
            extra={
                "component": "reconciliation",
                "action": "reconcile_start",
                "broker_positions_count": len(broker_positions),
                "internal_positions_count": len(internal_positions),
            },
        )

        # Convert to dict by symbol for efficient lookup
        self._broker_positions = {p.symbol: p for p in broker_positions}
        self._internal_positions = {p.symbol: p for p in internal_positions}

        # Get all unique symbols
        all_symbols = set(self._broker_positions.keys()) | set(self._internal_positions.keys())

        discrepancies: list[dict] = []
        matched = 0
        mismatched = 0
        missing = 0

        # Compare each symbol
        for symbol in all_symbols:
            broker_pos = self._broker_positions.get(symbol)
            internal_pos = self._internal_positions.get(symbol)

            # Detect discrepancies
            result = self._compare_positions(symbol, broker_pos, internal_pos)

            if result["status"] == "MATCHED":
                matched += 1
            elif result["status"] == "MISMATCH":
                mismatched += 1
                discrepancies.append(result)
            elif result["status"] == "MISSING":
                missing += 1
                discrepancies.append(result)

        total = len(all_symbols)
        is_balanced = mismatched == 0 and missing == 0

        logger.info(
            "Position reconciliation completed",
            extra={
                "component": "reconciliation",
                "action": "reconcile_complete",
                "total_positions": total,
                "matched_positions": matched,
                "mismatched_positions": mismatched,
                "missing_positions": missing,
                "is_balanced": is_balanced,
            },
        )

        if not is_balanced:
            logger.warning(
                "Reconciliation found discrepancies",
                extra={
                    "component": "reconciliation",
                    "action": "discrepancies_found",
                    "mismatched_count": mismatched,
                    "missing_count": missing,
                },
            )

        return ReconciliationResult(
            date=date.today(),
            total_positions=total,
            matched_positions=matched,
            mismatched_positions=mismatched,
            missing_positions=missing,
            discrepancies=discrepancies,
            is_balanced=is_balanced,
        )

    def _compare_positions(
        self, symbol: str, broker_pos: Optional[Position], internal_pos: Optional[Position]
    ) -> dict:
        """
        Compare two positions and return comparison result

        Args:
            symbol: Position symbol
            broker_pos: Position from broker (None if missing)
            internal_pos: Position from internal (None if missing)

        Returns:
            Dictionary with comparison status and details
        """
        # Both missing - shouldn't happen but handle gracefully
        if broker_pos is None and internal_pos is None:
            return {"status": "MATCHED", "symbol": symbol}

        # Only in broker (missing in internal records)
        if broker_pos is not None and internal_pos is None:
            logger.warning(
                "Position missing in internal records",
                extra={
                    "component": "reconciliation",
                    "action": "position_missing_internal",
                    "symbol": symbol,
                    "broker_quantity": str(broker_pos.quantity),
                    "severity": "HIGH",
                },
            )
            return {
                "status": "MISSING",
                "symbol": symbol,
                "type": "INTERNAL_ONLY",
                "broker_quantity": str(broker_pos.quantity),
                "broker_value": str(broker_pos.market_value),
                "severity": "HIGH",
                "detail": "Position exists in broker but not in internal records",
            }

        # Only in internal (missing in broker - phantom position)
        if broker_pos is None and internal_pos is not None:
            logger.error(
                "Phantom position detected - exists in internal but not broker",
                extra={
                    "component": "reconciliation",
                    "action": "phantom_position",
                    "symbol": symbol,
                    "internal_quantity": str(internal_pos.quantity),
                    "severity": "CRITICAL",
                },
            )
            return {
                "status": "MISSING",
                "symbol": symbol,
                "type": "BROKER_ONLY",
                "internal_quantity": str(internal_pos.quantity),
                "internal_value": str(internal_pos.market_value),
                "severity": "CRITICAL",
                "detail": "Position exists in internal records but broker reports closed",
            }

        # Both exist - verify quantities and prices
        qty_diff = abs(broker_pos.quantity - internal_pos.quantity)

        # Price difference calculation (avoid division by zero)
        if internal_pos.current_price != 0:
            price_diff_pct = (
                abs(broker_pos.current_price - internal_pos.current_price)
                / internal_pos.current_price
            )
        else:
            price_diff_pct = Decimal("1")  # 100% difference if internal price is 0

        # Check tolerances (R16)
        if qty_diff <= self.QUANTITY_TOLERANCE and price_diff_pct <= self.PRICE_TOLERANCE_PCT:
            return {"status": "MATCHED", "symbol": symbol}

        # There's a discrepancy
        discrepancies: list[dict] = []

        if qty_diff > self.QUANTITY_TOLERANCE:
            discrepancies.append(
                {
                    "type": "QUANTITY_MISMATCH",
                    "broker": str(broker_pos.quantity),
                    "internal": str(internal_pos.quantity),
                    "difference": str(qty_diff),
                    "tolerance": str(self.QUANTITY_TOLERANCE),
                }
            )

        if price_diff_pct > self.PRICE_TOLERANCE_PCT:
            discrepancies.append(
                {
                    "type": "PRICE_MISMATCH",
                    "broker": str(broker_pos.current_price),
                    "internal": str(internal_pos.current_price),
                    "difference_pct": str(price_diff_pct * Decimal("100")) + "%",
                    "tolerance": "0.1%",
                }
            )

        severity = "HIGH" if len(discrepancies) > 1 else "MEDIUM"
        logger.warning(
            "Position mismatch detected",
            extra={
                "component": "reconciliation",
                "action": "position_mismatch",
                "symbol": symbol,
                "discrepancies_count": len(discrepancies),
                "discrepancy_types": [d["type"] for d in discrepancies],
                "severity": severity,
            },
        )

        return {
            "status": "MISMATCH",
            "symbol": symbol,
            "discrepancies": discrepancies,
            "severity": severity,
        }

    def generate_reconciliation_report(self, result: ReconciliationResult) -> str:
        """
        Generate markdown reconciliation report (R16)

        Creates a human-readable report of the reconciliation results
        suitable for logging and alerting.

        Args:
            result: Reconciliation result from reconcile_positions()

        Returns:
            Markdown formatted report string

        Example:
            report = reconciler.generate_reconciliation_report(result)
            logger.info(report)
        """
        status_emoji = "BALANCED" if result.is_balanced else "DISCREPANCIES"
        status_prefix = "OK" if result.is_balanced else "WARNING"

        report = f"""# Daily Reconciliation Report (R16)
**Date:** {result.date}
**Status:** {status_prefix} - {status_emoji}
**Reconciled at:** {result.reconciled_at.strftime("%H:%M:%S UTC")}

## Summary
- **Total Positions:** {result.total_positions}
- **Matched:** {result.matched_positions}
- **Mismatched:** {result.mismatched_positions}
- **Missing:** {result.missing_positions}
- **Balance Status:** {'✅ BALANCED' if result.is_balanced else '⚠️ UNBALANCED'}
"""

        if result.discrepancies:
            report += "\n## Discrepancies\n\n"
            for disc in result.discrepancies:
                severity_emoji = (
                    "CRITICAL"
                    if disc.get("severity") == "CRITICAL"
                    else ("HIGH" if disc.get("severity") == "HIGH" else "MEDIUM")
                )
                report += f"### {disc['symbol']} [{severity_emoji}]\n"
                report += f"- **Status:** {disc['status']}\n"

                if disc.get('discrepancies'):
                    for d in disc['discrepancies']:
                        report += f"  - **{d['type']}:** {d}\n"

                if disc.get('detail'):
                    report += f"- **Detail:** {disc['detail']}\n"

                if disc.get('type'):
                    report += f"- **Type:** {disc['type']}\n"

                report += "\n"

        return report

    def get_position_delta(
        self, symbol: str, broker_pos: Optional[Position], internal_pos: Optional[Position]
    ) -> dict:
        """
        Calculate the delta between broker and internal position

        Args:
            symbol: Position symbol
            broker_pos: Broker position (None if missing)
            internal_pos: Internal position (None if missing)

        Returns:
            Dictionary with delta information
        """
        if broker_pos is None and internal_pos is None:
            return {"symbol": symbol, "delta_quantity": Decimal("0"), "delta_value": Decimal("0")}

        if broker_pos is None:
            return {
                "symbol": symbol,
                "delta_quantity": -internal_pos.quantity,
                "delta_value": -internal_pos.market_value,
                "note": "Phantom position",
            }

        if internal_pos is None:
            return {
                "symbol": symbol,
                "delta_quantity": broker_pos.quantity,
                "delta_value": broker_pos.market_value,
                "note": "Missing in internal",
            }

        return {
            "symbol": symbol,
            "delta_quantity": broker_pos.quantity - internal_pos.quantity,
            "delta_value": broker_pos.market_value - internal_pos.market_value,
        }
