"""
Discrepancy Detector Service

R16: Reconciliación Diaria - Component for detecting position discrepancies

This module provides specialized detection of position, price, and value discrepancies
between broker and internal records.

Uses centralized configuration for all tolerance thresholds.
"""

from decimal import Decimal
from typing import Optional

from app.core.config.base import get_config


class DiscrepancyDetector:
    """
    Detector of discrepancies in reconciliation (R16)

    Analyzes differences between broker and system internal positions
    with configurable tolerance thresholds from centralized config.

    Tolerances are loaded from config:
    - reconciliation_quantity_tolerance: ±N shares
    - reconciliation_price_tolerance_pct: ±N%
    - reconciliation_value_tolerance_pct: ±N%

    Example:
        detector = DiscrepancyDetector()
        result = detector.detect_position_mismatch(
            broker_qty=Decimal("100"),
            internal_qty=Decimal("98")
        )
        if result:
            logger.warning(f"Quantity mismatch: {result}")
    """

    def __init__(self):
        """Initialize detector and load tolerances from centralized config."""
        config = get_config()
        # Get tolerances from config with defaults
        self.QUANTITY_TOLERANCE = Decimal(str(getattr(
            config.trading, 'reconciliation_quantity_tolerance', 1
        )))
        self.PRICE_TOLERANCE_PCT = Decimal(str(getattr(
            config.trading, 'reconciliation_price_tolerance_pct', 0.001
        )))
        self.VALUE_TOLERANCE_PCT = Decimal(str(getattr(
            config.trading, 'reconciliation_value_tolerance_pct', 0.005
        )))

    def detect_position_mismatch(
        self, broker_qty: Decimal, internal_qty: Decimal
    ) -> Optional[dict]:
        """
        Detect quantity discrepancy in position (R16)

        Checks if the quantity difference between broker and internal
        exceeds the tolerance threshold.

        Args:
            broker_qty: Quantity according to broker
            internal_qty: Quantity according to internal records

        Returns:
            Dictionary with discrepancy details or None if within tolerance

        Example:
            result = detector.detect_position_mismatch(
                broker_qty=Decimal("100"),
                internal_qty=Decimal("98")
            )
            # Returns: discrepancy dict (difference of 2 > tolerance of 1)
        """
        diff = abs(broker_qty - internal_qty)

        if diff > self.QUANTITY_TOLERANCE:
            # Determine severity based on magnitude
            if diff > Decimal("10"):
                severity = "CRITICAL"
            elif diff > Decimal("5"):
                severity = "HIGH"
            else:
                severity = "MEDIUM"

            return {
                "type": "QUANTITY_MISMATCH",
                "broker_qty": str(broker_qty),
                "internal_qty": str(internal_qty),
                "difference": str(diff),
                "difference_pct": (
                    f"{(diff / internal_qty * 100):.2f}%" if internal_qty != 0 else "N/A"
                ),
                "tolerance": str(self.QUANTITY_TOLERANCE),
                "severity": severity,
            }

        return None

    def detect_price_mismatch(
        self, broker_price: Decimal, internal_price: Decimal
    ) -> Optional[dict]:
        """
        Detect price discrepancy (R16)

        Checks if the price difference percentage exceeds the tolerance.
        Uses relative percentage difference for comparison.

        Args:
            broker_price: Price according to broker
            internal_price: Price according to internal records

        Returns:
            Dictionary with discrepancy details or None if within tolerance

        Example:
            result = detector.detect_price_mismatch(
                broker_price=Decimal("100.50"),
                internal_price=Decimal("100.00")
            )
            # Returns: discrepancy dict (0.5% > 0.1% tolerance)
        """
        # Handle zero price case
        if internal_price == 0:
            if broker_price == 0:
                return None  # Both zero - no discrepancy
            return {
                "type": "PRICE_MISMATCH",
                "broker_price": str(broker_price),
                "internal_price": str(internal_price),
                "difference": str(broker_price),
                "difference_pct": "N/A",
                "detail": "Internal price is zero",
                "tolerance": "0.1%",
                "severity": "HIGH",
            }

        diff_pct = abs(broker_price - internal_price) / internal_price

        if diff_pct > self.PRICE_TOLERANCE_PCT:
            # Determine severity
            if diff_pct > Decimal("0.01"):  # > 1%
                severity = "CRITICAL"
            elif diff_pct > Decimal("0.005"):  # > 0.5%
                severity = "HIGH"
            else:
                severity = "MEDIUM"

            return {
                "type": "PRICE_MISMATCH",
                "broker_price": str(broker_price),
                "internal_price": str(internal_price),
                "difference": str(abs(broker_price - internal_price)),
                "difference_pct": f"{diff_pct * 100:.3f}%",
                "tolerance": "0.1%",
                "severity": severity,
            }

        return None

    def detect_value_mismatch(
        self, broker_value: Decimal, internal_value: Decimal
    ) -> Optional[dict]:
        """
        Detect market value discrepancy (R16)

        Checks if the total value difference exceeds tolerance.
        This is useful for detecting larger discrepancies that might
        not be caught by quantity or price checks alone.

        Args:
            broker_value: Market value according to broker
            internal_value: Market value according to internal records

        Returns:
            Dictionary with discrepancy details or None if within tolerance

        Example:
            result = detector.detect_value_mismatch(
                broker_value=Decimal("10050.00"),
                internal_value=Decimal("10000.00")
            )
            # Returns: discrepancy dict if > 0.5% difference
        """
        # Handle zero value case
        if internal_value == 0:
            if broker_value == 0:
                return None
            return {
                "type": "VALUE_MISMATCH",
                "broker_value": str(broker_value),
                "internal_value": str(internal_value),
                "difference": str(broker_value),
                "difference_pct": "N/A",
                "detail": "Internal value is zero",
                "tolerance": "0.5%",
                "severity": "HIGH",
            }

        diff_pct = abs(broker_value - internal_value) / internal_value

        if diff_pct > self.VALUE_TOLERANCE_PCT:
            return {
                "type": "VALUE_MISMATCH",
                "broker_value": str(broker_value),
                "internal_value": str(internal_value),
                "difference": str(abs(broker_value - internal_value)),
                "difference_pct": f"{diff_pct * 100:.2f}%",
                "tolerance": "0.5%",
                "severity": "MEDIUM",
            }

        return None

    def detect_missing_positions(
        self, broker_symbols: set[str], internal_symbols: set[str]
    ) -> list[dict]:
        """
        Detect positions that exist in one system but not the other (R16)

        Identifies orphaned positions (in broker but not internal) and
        phantom positions (in internal but not broker).

        Args:
            broker_symbols: Set of symbols in broker
            internal_symbols: Set of symbols in internal records

        Returns:
            List of missing position dictionaries

        Example:
            broker_syms = {"SAN.MC", "REE.MC"}
            internal_syms = {"SAN.MC", "AAPL"}
            missing = detector.detect_missing_positions(broker_syms, internal_syms)
            # Returns: 2 discrepancies (REE.MC missing in internal, AAPL missing in broker)
        """
        missing: list[dict] = []

        # Symbols in broker but not in internal (orphaned positions)
        for symbol in broker_symbols - internal_symbols:
            missing.append(
                {
                    "type": "MISSING_IN_INTERNAL",
                    "symbol": symbol,
                    "detail": "Position exists in broker but not in internal records",
                    "severity": "HIGH",
                    "action_required": "Add to internal records or investigate",
                }
            )

        # Symbols in internal but not in broker (phantom positions)
        for symbol in internal_symbols - broker_symbols:
            missing.append(
                {
                    "type": "MISSING_IN_BROKER",
                    "symbol": symbol,
                    "detail": "Position exists in internal records but broker reports closed",
                    "severity": "CRITICAL",
                    "action_required": "Mark as closed in internal or investigate with broker",
                }
            )

        return missing

    def detect_all_discrepancies(
        self,
        broker_positions: dict,  # {symbol: {"quantity": Decimal, "price": Decimal, "value": Decimal}}
        internal_positions: dict,
    ) -> dict:
        """
        Comprehensive discrepancy detection (R16)

        Runs all detection methods and returns a consolidated report
        of all discrepancies found.

        Args:
            broker_positions: Dict of broker positions by symbol
            internal_positions: Dict of internal positions by symbol

        Returns:
            Dictionary with all discrepancies categorized by type

        Example:
            discrepancies = detector.detect_all_discrepancies(
                broker_positions={"SAN.MC": {"quantity": Decimal("100"), ...}},
                internal_positions={"SAN.MC": {"quantity": Decimal("98"), ...}}
            )
        """
        result = {
            "quantity_mismatches": [],
            "price_mismatches": [],
            "value_mismatches": [],
            "missing_positions": [],
            "total_discrepancies": 0,
        }

        all_symbols = set(broker_positions.keys()) | set(internal_positions.keys())

        for symbol in all_symbols:
            broker_pos = broker_positions.get(symbol, {})
            internal_pos = internal_positions.get(symbol, {})

            # Check quantity mismatch
            qty_result = self.detect_position_mismatch(
                broker_qty=broker_pos.get("quantity", Decimal("0")),
                internal_qty=internal_pos.get("quantity", Decimal("0")),
            )
            if qty_result:
                qty_result["symbol"] = symbol
                result["quantity_mismatches"].append(qty_result)

            # Check price mismatch
            price_result = self.detect_price_mismatch(
                broker_price=broker_pos.get("price", Decimal("0")),
                internal_price=internal_pos.get("price", Decimal("0")),
            )
            if price_result:
                price_result["symbol"] = symbol
                result["price_mismatches"].append(price_result)

            # Check value mismatch
            value_result = self.detect_value_mismatch(
                broker_value=broker_pos.get("value", Decimal("0")),
                internal_value=internal_pos.get("value", Decimal("0")),
            )
            if value_result:
                value_result["symbol"] = symbol
                result["value_mismatches"].append(value_result)

        # Check for missing positions
        missing = self.detect_missing_positions(
            broker_symbols=set(broker_positions.keys()),
            internal_symbols=set(internal_positions.keys()),
        )
        result["missing_positions"] = missing

        # Calculate total
        result["total_discrepancies"] = (
            len(result["quantity_mismatches"])
            + len(result["price_mismatches"])
            + len(result["value_mismatches"])
            + len(result["missing_positions"])
        )

        return result

    def get_severity_counts(self, discrepancies: list[dict]) -> dict:
        """
        Count discrepancies by severity level

        Args:
            discrepancies: List of discrepancy dictionaries

        Returns:
            Dictionary with counts by severity (CRITICAL, HIGH, MEDIUM)
        """
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for disc in discrepancies:
            severity = disc.get("severity", "MEDIUM")
            if severity in counts:
                counts[severity] += 1
            else:
                counts["MEDIUM"] += 1

        return counts
