"""
T15.1.2: WashSaleDetector - Wash-sale violation detection and prevention

Monitors trades to detect wash-sale violations and adjusts cost basis accordingly.
A wash sale occurs when a security is sold at a loss and a substantially identical
security is purchased within 30 days before or after the sale.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Record of a buy or sell transaction."""

    symbol: str
    date: datetime
    side: str  # 'BUY' or 'SELL'
    quantity: Decimal
    price: Decimal
    total_value: Decimal  # quantity × price


@dataclass
class WashSaleViolation:
    """Detected wash-sale violation."""

    sale_trade: Trade
    replacement_trade: Trade
    violation_date: datetime
    loss_amount: Decimal
    disallowed_loss: Decimal
    cost_basis_adjustment: Decimal
    days_between: int


@dataclass
class CostBasisAdjustment:
    """Cost basis adjustment due to wash-sale."""

    original_cost_basis: Decimal
    disallowed_loss: Decimal
    adjusted_cost_basis: Decimal  # original + disallowed loss
    adjustment_date: datetime


class WashSaleDetector:
    """
    Detects and prevents wash-sale violations.

    Features:
    - Monitor 30-day window before and after sales
    - Identify substantially identical positions
    - Calculate cost basis adjustments
    - Track violations with compliance alerts
    """

    # Wash-sale window: 30 days before sale + 30 days after
    WASH_SALE_WINDOW_DAYS = 30

    def __init__(self):
        """Initialize wash-sale detector."""
        self.violation_history: List[WashSaleViolation] = []
        self.cost_basis_adjustments: Dict[str, List[CostBasisAdjustment]] = {}
        logger.info("✅ WashSaleDetector initialized")

    def detect_wash_sale(
        self,
        sell_trade: Trade,
        buy_trades: List[Trade],
        substantially_identical_symbols: Optional[List[str]] = None,
    ) -> Optional[WashSaleViolation]:
        """
        Detect wash-sale violation for a sell transaction.

        Args:
            sell_trade: The sale that may trigger wash-sale
            buy_trades: All recent purchase transactions
            substantially_identical_symbols: List of symbols considered identical to sell_trade.symbol

        Returns:
            WashSaleViolation if detected, None otherwise
        """
        if sell_trade.side != "SELL":
            return None

        # Get list of substantially identical symbols
        identical_symbols = substantially_identical_symbols or [sell_trade.symbol]

        # Check for purchases within 30 days before or after sale
        window_start = sell_trade.date - timedelta(days=self.WASH_SALE_WINDOW_DAYS)
        window_end = sell_trade.date + timedelta(days=self.WASH_SALE_WINDOW_DAYS)

        for buy_trade in buy_trades:
            if buy_trade.side != "BUY":
                continue

            # Check if purchase is within window
            if not (window_start <= buy_trade.date <= window_end):
                continue

            # Check if it's a substantially identical security
            if buy_trade.symbol not in identical_symbols:
                continue

            # Check if the sale resulted in a loss
            loss_amount = (
                sell_trade.price - self.get_cost_basis_per_share(sell_trade.symbol)
            ) * sell_trade.quantity
            if loss_amount >= 0:
                continue  # No loss, no wash-sale

            # Violation detected
            days_between = abs((buy_trade.date - sell_trade.date).days)
            violation = WashSaleViolation(
                sale_trade=sell_trade,
                replacement_trade=buy_trade,
                violation_date=datetime.now(),
                loss_amount=loss_amount,
                disallowed_loss=abs(loss_amount),
                cost_basis_adjustment=abs(loss_amount),  # Add loss back to basis
                days_between=days_between,
            )

            self.violation_history.append(violation)
            logger.warning(
                f"⚠️ Wash-sale violation detected: {sell_trade.symbol} sale on {sell_trade.date.date()}, "
                f"replacement purchase on {buy_trade.date.date()}"
            )

            return violation

        return None

    def adjust_cost_basis(
        self,
        symbol: str,
        original_cost_basis: Decimal,
        disallowed_loss: Decimal,
    ) -> CostBasisAdjustment:
        """
        Calculate cost basis adjustment due to wash-sale.

        The disallowed loss is added back to the cost basis of the replacement position.

        Args:
            symbol: Symbol with wash-sale violation
            original_cost_basis: Original cost basis
            disallowed_loss: Disallowed loss amount

        Returns:
            Cost basis adjustment record
        """
        adjusted_basis = original_cost_basis + disallowed_loss

        adjustment = CostBasisAdjustment(
            original_cost_basis=original_cost_basis,
            disallowed_loss=disallowed_loss,
            adjusted_cost_basis=adjusted_basis,
            adjustment_date=datetime.now(),
        )

        if symbol not in self.cost_basis_adjustments:
            self.cost_basis_adjustments[symbol] = []

        self.cost_basis_adjustments[symbol].append(adjustment)

        logger.info(
            f"✅ Cost basis adjusted for {symbol}: "
            f"€{original_cost_basis:,.2f} → €{adjusted_basis:,.2f}"
        )

        return adjustment

    def get_compliance_window(self, sale_date: datetime) -> tuple:
        """
        Get the wash-sale compliance window for a sale date.

        Returns dates 30 days before and after the sale.

        Args:
            sale_date: Date of the sale

        Returns:
            (window_start_date, window_end_date)
        """
        window_start = sale_date - timedelta(days=self.WASH_SALE_WINDOW_DAYS)
        window_end = sale_date + timedelta(days=self.WASH_SALE_WINDOW_DAYS)
        return window_start, window_end

    def is_substantially_identical(
        self,
        symbol1: str,
        symbol2: str,
        price_correlation: Decimal = Decimal("0.85"),  # threshold
    ) -> bool:
        """
        Check if two symbols are substantially identical for tax purposes.

        Substantially identical includes:
        - Same security
        - Different share classes of same company
        - Highly correlated exchange-traded fund
        - Call/put options on same security (generally)

        Args:
            symbol1: First symbol
            symbol2: Second symbol
            price_correlation: Correlation threshold (0-1)

        Returns:
            True if substantially identical, False otherwise
        """
        # Exact match
        if symbol1 == symbol2:
            return True

        # Define substantially identical pairs (both directions)
        identical_pairs = {
            ("AAPL", "AAPL"),
            ("AGG", "BND"),  # Broad bond funds
            ("IVV", "SPY"),  # iShares vs SPDR S&P 500
            ("IEF", "TLT"),  # Bond ETFs
            ("SPY", "VOO"),  # Broad market S&P 500
        }

        # Check both directions
        return (symbol1, symbol2) in identical_pairs or (symbol2, symbol1) in identical_pairs

    def get_cost_basis_per_share(
        self, symbol: str, quantity_owned: Decimal = Decimal("1")
    ) -> Decimal:
        """
        Get adjusted cost basis per share.

        Accounts for wash-sale adjustments.

        Args:
            symbol: Symbol
            quantity_owned: Shares owned

        Returns:
            Cost per share
        """
        if symbol not in self.cost_basis_adjustments:
            return Decimal("0")

        total_adjustment = sum(adj.disallowed_loss for adj in self.cost_basis_adjustments[symbol])

        if quantity_owned <= 0:
            return Decimal("0")

        return total_adjustment / quantity_owned

    def generate_compliance_report(self) -> Dict:
        """
        Generate wash-sale compliance report.

        Returns:
            Dict with violation summary and cost basis adjustments
        """
        return {
            "total_violations": len(self.violation_history),
            "violations": [
                {
                    "symbol": v.sale_trade.symbol,
                    "sale_date": v.sale_trade.date.isoformat(),
                    "replacement_date": v.replacement_trade.date.isoformat(),
                    "days_between": v.days_between,
                    "disallowed_loss": float(v.disallowed_loss),
                }
                for v in self.violation_history
            ],
            "total_disallowed_losses": float(
                sum(v.disallowed_loss for v in self.violation_history)
            ),
            "cost_basis_adjustments": {
                symbol: [
                    {
                        "original": float(adj.original_cost_basis),
                        "adjustment": float(adj.disallowed_loss),
                        "adjusted": float(adj.adjusted_cost_basis),
                    }
                    for adj in adjustments
                ]
                for symbol, adjustments in self.cost_basis_adjustments.items()
            },
        }


# Singleton
_detector: Optional[WashSaleDetector] = None


def get_wash_sale_detector() -> WashSaleDetector:
    """Get or create singleton WashSaleDetector."""
    global _detector
    if _detector is None:
        _detector = WashSaleDetector()
        logger.info("✅ WashSaleDetector singleton initialized")

    return _detector
