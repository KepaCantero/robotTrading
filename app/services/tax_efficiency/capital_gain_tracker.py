"""
T15.1.3: CapitalGainTracker - Tracks realized and unrealized capital gains/losses

Classifies gains as short-term (<1 year) or long-term (≥1 year) and calculates
tax liability based on investor's tax bracket.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GainLossRecord:
    """Single realized gain or loss from a sale."""

    symbol: str
    quantity: Decimal
    purchase_date: datetime
    sale_date: datetime
    purchase_price: Decimal
    sale_price: Decimal
    gain_loss: Decimal  # Positive for gain, negative for loss
    is_long_term: bool  # True if held ≥ 1 year
    tax_rate: Decimal  # Applicable tax rate


@dataclass
class PositionGainLoss:
    """Unrealized gain/loss on a current position."""

    symbol: str
    quantity: Decimal
    purchase_date: datetime
    cost_basis: Decimal
    current_value: Decimal
    unrealized_gain_loss: Decimal
    is_long_term: bool  # Based on current holding period
    projected_tax_if_sold: Decimal


@dataclass
class TaxLotReport:
    """Complete tax reporting summary."""

    report_date: datetime
    total_short_term_gains: Decimal
    total_short_term_losses: Decimal
    total_long_term_gains: Decimal
    total_long_term_losses: Decimal
    net_short_term: Decimal
    net_long_term: Decimal
    net_capital_gain_loss: Decimal
    projected_annual_tax: Decimal
    unrealized_gains_summary: dict[str, Decimal]


class CapitalGainTracker:
    """
    Tracks and calculates capital gains and losses.

    Features:
    - Position-level gain/loss tracking
    - ST/LT classification
    - Tax liability calculation
    - Tax lot reporting
    - Annual tax projections
    """

    # Long-term holding period: 1 year
    LONG_TERM_HOLDING_DAYS = 365

    def __init__(self):
        """Initialize capital gain tracker."""
        self.realized_gains: list[GainLossRecord] = []
        self.position_history: dict[str, list[dict]] = {}  # symbol → purchase history
        logger.info("✅ CapitalGainTracker initialized")

    def record_position_purchase(
        self,
        symbol: str,
        quantity: Decimal,
        purchase_price: Decimal,
        purchase_date: datetime,
    ) -> None:
        """
        Record a position purchase for tracking.

        Args:
            symbol: Stock symbol
            quantity: Shares purchased
            purchase_price: Price per share
            purchase_date: Date of purchase
        """
        if symbol not in self.position_history:
            self.position_history[symbol] = []

        self.position_history[symbol].append(
            {
                "quantity": quantity,
                "price": purchase_price,
                "date": purchase_date,
                "cost_basis": quantity * purchase_price,
            }
        )

        logger.info(f"✅ Recorded purchase: {quantity} shares of {symbol} at €{purchase_price}")

    def record_position_sale(
        self,
        symbol: str,
        quantity: Decimal,
        sale_price: Decimal,
        sale_date: datetime,
        method: str = "FIFO",  # FIFO, LIFO, AVERAGE_COST
    ) -> list[GainLossRecord]:
        """
        Record a position sale and calculate gains/losses.

        Args:
            symbol: Stock symbol
            quantity: Shares sold
            sale_price: Price per share
            sale_date: Date of sale
            method: Cost basis method (FIFO, LIFO, AVERAGE_COST)

        Returns:
            List of gain/loss records for the sale
        """
        if symbol not in self.position_history or not self.position_history[symbol]:
            logger.warning(f"⚠️ No purchase history for {symbol}")
            return []

        gains_losses = []
        remaining_qty = quantity
        purchases = self.position_history[symbol].copy()

        # Sort by date based on method
        if method == "FIFO":
            purchases.sort(key=lambda x: x["date"])
        elif method == "LIFO":
            purchases.sort(key=lambda x: x["date"], reverse=True)
        else:  # AVERAGE_COST
            avg_price = sum(p["cost_basis"] for p in purchases) / sum(
                p["quantity"] for p in purchases
            )
            purchase_date = min(p["date"] for p in purchases)
            record = GainLossRecord(
                symbol=symbol,
                quantity=quantity,
                purchase_date=purchase_date,
                sale_date=sale_date,
                purchase_price=avg_price,
                sale_price=sale_price,
                gain_loss=(sale_price - avg_price) * quantity,
                is_long_term=(sale_date - purchase_date).days >= self.LONG_TERM_HOLDING_DAYS,
                tax_rate=Decimal("0.15"),  # Default, will be adjusted
            )
            gains_losses.append(record)
            self.realized_gains.append(record)
            logger.info(f"✅ Recorded sale: {quantity} shares of {symbol} at €{sale_price}")
            return gains_losses

        # FIFO/LIFO method
        for purchase in purchases:
            if remaining_qty <= 0:
                break

            qty_from_this_lot = min(remaining_qty, purchase["quantity"])
            holding_days = (sale_date - purchase["date"]).days
            is_long_term = holding_days >= self.LONG_TERM_HOLDING_DAYS

            gain_loss = (sale_price - purchase["price"]) * qty_from_this_lot

            record = GainLossRecord(
                symbol=symbol,
                quantity=qty_from_this_lot,
                purchase_date=purchase["date"],
                sale_date=sale_date,
                purchase_price=purchase["price"],
                sale_price=sale_price,
                gain_loss=gain_loss,
                is_long_term=is_long_term,
                tax_rate=Decimal("0.15") if is_long_term else Decimal("0.35"),  # Approximate
            )

            gains_losses.append(record)
            self.realized_gains.append(record)
            remaining_qty -= qty_from_this_lot

        logger.info(f"✅ Recorded sale: {quantity} shares of {symbol}")
        return gains_losses

    def calculate_unrealized_gains(
        self,
        positions: dict[str, Decimal],  # symbol → current_value
        current_prices: dict[str, Decimal],  # symbol → price per share
        quantities: dict[str, Decimal],  # symbol → quantity held
    ) -> dict[str, PositionGainLoss]:
        """
        Calculate unrealized gains/losses for current positions.

        Args:
            positions: Current position values
            current_prices: Current price per share
            quantities: Quantity held per symbol

        Returns:
            Dict of unrealized gains/losses by symbol
        """
        unrealized = {}

        for symbol, quantity in quantities.items():
            if symbol not in self.position_history or quantity <= 0:
                continue

            # Calculate average cost basis
            purchases = self.position_history[symbol]
            total_cost = sum(p["cost_basis"] for p in purchases)
            avg_price = (
                total_cost / sum(p["quantity"] for p in purchases) if purchases else Decimal("0")
            )

            current_value = positions.get(symbol, Decimal("0"))
            cost_basis = avg_price * quantity
            unrealized_gain_loss = current_value - cost_basis

            # Determine if would be LT if sold today
            oldest_purchase = min((p["date"] for p in purchases), default=datetime.now())
            is_long_term = (datetime.now() - oldest_purchase).days >= self.LONG_TERM_HOLDING_DAYS

            # Estimate tax
            tax_rate = Decimal("0.15") if is_long_term else Decimal("0.35")
            estimated_tax = (
                abs(unrealized_gain_loss) * tax_rate if unrealized_gain_loss > 0 else Decimal("0")
            )

            unrealized[symbol] = PositionGainLoss(
                symbol=symbol,
                quantity=quantity,
                purchase_date=oldest_purchase,
                cost_basis=cost_basis,
                current_value=current_value,
                unrealized_gain_loss=unrealized_gain_loss,
                is_long_term=is_long_term,
                projected_tax_if_sold=estimated_tax,
            )

        logger.info(f"✅ Calculated unrealized gains for {len(unrealized)} positions")
        return unrealized

    def get_short_term_gains(self) -> Decimal:
        """Calculate total short-term realized gains."""
        st_gains = sum(
            (g.gain_loss for g in self.realized_gains if not g.is_long_term and g.gain_loss > 0),
            Decimal("0"),
        )
        return st_gains

    def get_short_term_losses(self) -> Decimal:
        """Calculate total short-term realized losses."""
        st_losses = sum(
            (
                abs(g.gain_loss)
                for g in self.realized_gains
                if not g.is_long_term and g.gain_loss < 0
            ),
            Decimal("0"),
        )
        return st_losses

    def get_long_term_gains(self) -> Decimal:
        """Calculate total long-term realized gains."""
        lt_gains = sum(
            (g.gain_loss for g in self.realized_gains if g.is_long_term and g.gain_loss > 0),
            Decimal("0"),
        )
        return lt_gains

    def get_long_term_losses(self) -> Decimal:
        """Calculate total long-term realized losses."""
        lt_losses = sum(
            (abs(g.gain_loss) for g in self.realized_gains if g.is_long_term and g.gain_loss < 0),
            Decimal("0"),
        )
        return lt_losses

    def project_annual_tax(
        self,
        marginal_tax_rate_st: Optional[Decimal] = None,  # Short-term
        marginal_tax_rate_lt: Optional[Decimal] = None,  # Long-term
    ) -> Decimal:
        """
        Project annual tax liability from realized gains.

        Args:
            marginal_tax_rate_st: Marginal tax rate for short-term gains
            marginal_tax_rate_lt: Marginal tax rate for long-term gains

        Returns:
            Estimated annual tax liability
        """
        if marginal_tax_rate_st is None:
            marginal_tax_rate_st = Decimal("0.35")
        if marginal_tax_rate_lt is None:
            marginal_tax_rate_lt = Decimal("0.15")
        net_st = self.get_short_term_gains() - self.get_short_term_losses()
        net_lt = self.get_long_term_gains() - self.get_long_term_losses()

        # Capital losses offset gains (ST first, then LT)
        if net_st < 0:
            net_lt = max(net_lt + net_st, Decimal("0"))
            net_st = Decimal("0")
        if net_lt < 0:
            net_st = max(net_st + net_lt, Decimal("0"))
            net_lt = Decimal("0")

        tax = (net_st * marginal_tax_rate_st) + (net_lt * marginal_tax_rate_lt)
        return max(tax, Decimal("0"))

    def generate_tax_lot_report(self) -> TaxLotReport:
        """
        Generate comprehensive tax lot report.

        Returns:
            Complete tax reporting summary
        """
        st_gains = self.get_short_term_gains()
        st_losses = self.get_short_term_losses()
        lt_gains = self.get_long_term_gains()
        lt_losses = self.get_long_term_losses()

        net_st = st_gains - st_losses
        net_lt = lt_gains - lt_losses
        net_capital = net_st + net_lt

        return TaxLotReport(
            report_date=datetime.now(),
            total_short_term_gains=st_gains,
            total_short_term_losses=st_losses,
            total_long_term_gains=lt_gains,
            total_long_term_losses=lt_losses,
            net_short_term=net_st,
            net_long_term=net_lt,
            net_capital_gain_loss=net_capital,
            projected_annual_tax=self.project_annual_tax(),
            unrealized_gains_summary={g.symbol: g.gain_loss for g in self.realized_gains},
        )


# Singleton
_tracker: Optional[CapitalGainTracker] = None


def get_capital_gain_tracker() -> CapitalGainTracker:
    """Get or create singleton CapitalGainTracker."""
    global _tracker
    if _tracker is None:
        _tracker = CapitalGainTracker()
        logger.info("✅ CapitalGainTracker singleton initialized")

    return _tracker
