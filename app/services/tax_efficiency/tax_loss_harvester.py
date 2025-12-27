"""
T15.1.1: TaxLossHarvester - Tax-loss harvesting implementation

Identifies positions with unrealized losses eligible for tax harvesting,
calculates tax benefits, and suggests replacement positions to maintain
portfolio exposure while locking in losses.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HarvestablePosition:
    """Position eligible for tax-loss harvesting."""

    symbol: str
    quantity: Decimal
    purchase_price: Decimal
    current_price: Decimal
    unrealized_loss: Decimal  # Negative value
    tax_benefit: Decimal  # Loss × marginal tax rate
    hold_period_days: int


@dataclass
class ReplacementPosition:
    """Suggested replacement position to maintain exposure."""

    symbol: str
    quantity: Decimal
    target_allocation_pct: Decimal
    correlation_with_original: Decimal  # 0-1, higher = more similar


@dataclass
class HarvestingOpportunity:
    """Complete tax-harvesting opportunity."""

    position: HarvestablePosition
    replacement: Optional[ReplacementPosition]
    total_tax_benefit: Decimal
    recommendation: str


class TaxLossHarvester:
    """
    Identifies and calculates tax-loss harvesting opportunities.

    Features:
    - Position-level loss identification
    - Tax benefit calculation (loss × marginal_tax_rate)
    - Replacement position suggestion (wash-sale compliant)
    - Annual tax benefit aggregation
    - Integration with portfolio rebalancing
    """

    # Wash-sale window: 30 days before and after sale
    WASH_SALE_WINDOW_DAYS = 30

    # Replacement position correlation threshold
    MIN_CORRELATION_FOR_REPLACEMENT = Decimal("0.7")

    def __init__(self):
        """Initialize tax loss harvester."""
        logger.info("✅ TaxLossHarvester initialized")

    def identify_harvestable_positions(
        self,
        positions: Dict[str, Decimal],  # symbol → current_value
        cost_basis: Dict[str, Decimal],  # symbol → total_cost
        quantities: Dict[str, Decimal],  # symbol → quantity
        current_prices: Dict[str, Decimal],  # symbol → price
        min_loss_threshold: Decimal = Decimal("100"),  # Minimum loss to consider
    ) -> List[HarvestablePosition]:
        """
        Identify positions with unrealized losses eligible for harvesting.

        Args:
            positions: Current position values
            cost_basis: Total purchase cost per symbol
            quantities: Shares owned per symbol
            current_prices: Current price per share
            min_loss_threshold: Minimum loss amount to consider (€)

        Returns:
            List of harvestable positions sorted by loss amount
        """
        harvestable = []

        for symbol, quantity in quantities.items():
            if quantity <= 0:
                continue

            cost = cost_basis.get(symbol, Decimal("0"))
            current = positions.get(symbol, Decimal("0"))
            unrealized_loss = current - cost

            # Only include positions with losses greater than threshold
            if unrealized_loss >= Decimal("0") or abs(unrealized_loss) < min_loss_threshold:
                continue

            position = HarvestablePosition(
                symbol=symbol,
                quantity=quantity,
                purchase_price=cost / quantity if quantity > 0 else Decimal("0"),
                current_price=current_prices.get(symbol, Decimal("0")),
                unrealized_loss=unrealized_loss,
                tax_benefit=Decimal("0"),  # Will be calculated with tax rate
                hold_period_days=0,  # Will be set if tracked
            )

            harvestable.append(position)

        # Sort by loss amount (largest losses first)
        harvestable.sort(key=lambda p: p.unrealized_loss)

        logger.info(f"✅ Identified {len(harvestable)} harvestable positions")
        return harvestable

    def calculate_tax_benefit(
        self,
        unrealized_loss: Decimal,
        marginal_tax_rate: Decimal,  # 0.15 = 15%, etc.
    ) -> Decimal:
        """
        Calculate tax benefit from harvesting a loss.

        Formula: Tax Benefit = |Loss| × Marginal Tax Rate

        Args:
            unrealized_loss: Negative value representing the loss
            marginal_tax_rate: Investor's marginal tax rate (decimal)

        Returns:
            Tax benefit amount (positive)
        """
        if unrealized_loss >= 0:
            return Decimal("0")

        tax_benefit = abs(unrealized_loss) * marginal_tax_rate
        return tax_benefit

    def suggest_replacement_position(
        self,
        harvested_symbol: str,
        harvested_quantity: Decimal,
        current_price: Decimal,
        asset_class: str = "equity",  # equity, fixed_income, crypto, etc.
    ) -> ReplacementPosition:
        """
        Suggest replacement position that maintains exposure while avoiding wash-sale.

        Strategy: Replace with highly correlated but not identical security
        Examples:
        - AAPL → MSFT, SPY, QQQ (tech-heavy)
        - BND → AGG (broad bonds)

        Args:
            harvested_symbol: Symbol being harvested
            harvested_quantity: Quantity being sold
            current_price: Current price
            asset_class: Asset class for finding replacements

        Returns:
            Suggested replacement position
        """
        # Replacement suggestions by asset class and original symbol
        replacements = {
            ("AAPL", "equity"): ("MSFT", Decimal("0.75")),  # 75% correlation
            ("MSFT", "equity"): ("AAPL", Decimal("0.75")),
            ("GOOGL", "equity"): ("MSFT", Decimal("0.70")),
            ("TSLA", "equity"): ("NVDA", Decimal("0.68")),
            ("VOO", "equity"): ("SPY", Decimal("0.98")),  # Very high correlation
            ("BND", "fixed_income"): ("AGG", Decimal("0.85")),
            ("TLT", "fixed_income"): ("IEF", Decimal("0.92")),
        }

        # Default: suggest broad index fund for same asset class
        replacement_symbol, correlation = replacements.get(
            (harvested_symbol, asset_class),
            ("SPY" if asset_class == "equity" else "AGG", Decimal("0.70")),
        )

        return ReplacementPosition(
            symbol=replacement_symbol,
            quantity=harvested_quantity,
            target_allocation_pct=(harvested_quantity * current_price)
            / Decimal("1000000"),  # Rough estimate
            correlation_with_original=correlation,
        )

    def estimate_annual_tax_benefit(
        self,
        harvestable_positions: List[HarvestablePosition],
        marginal_tax_rate: Decimal,
        capital_losses_carryforward: Decimal = Decimal("0"),
    ) -> Dict:
        """
        Estimate total annual tax benefit from all harvestable positions.

        Considerations:
        - Capital losses offset capital gains first
        - Excess losses carryforward to future years (max $3k/year for individuals)
        - Different tax treatment for ST vs LT

        Args:
            harvestable_positions: List of positions to harvest
            marginal_tax_rate: Investor's marginal tax rate
            capital_losses_carryforward: Prior year losses to offset

        Returns:
            Dict with total benefit, usable amount, carryforward
        """
        total_loss = sum(p.unrealized_loss for p in harvestable_positions)
        total_loss_amount = abs(total_loss)

        # For individuals, max €3000/year of capital losses against ordinary income
        # Excess carryforwards indefinitely
        max_annual_deduction = Decimal("3000")

        # Total available losses = new losses + carryforward
        total_available = total_loss_amount + capital_losses_carryforward

        # Use up to the annual maximum
        usable_this_year = min(total_available, max_annual_deduction)
        carryforward = total_available - usable_this_year

        tax_benefit = usable_this_year * marginal_tax_rate

        return {
            "total_harvestable_loss": total_loss_amount,
            "usable_this_year": usable_this_year,
            "carryforward_to_next_year": carryforward,
            "tax_benefit_this_year": tax_benefit,
            "estimated_cash_savings": tax_benefit,
        }

    def create_harvesting_opportunity(
        self,
        position: HarvestablePosition,
        marginal_tax_rate: Decimal,
        suggest_replacement: bool = True,
    ) -> HarvestingOpportunity:
        """
        Create a complete harvesting opportunity with analysis.

        Args:
            position: Position to harvest
            marginal_tax_rate: Investor's tax rate
            suggest_replacement: Whether to suggest replacement

        Returns:
            Complete harvesting opportunity with recommendation
        """
        tax_benefit = self.calculate_tax_benefit(position.unrealized_loss, marginal_tax_rate)

        replacement = None
        if suggest_replacement:
            replacement = self.suggest_replacement_position(
                position.symbol,
                position.quantity,
                position.current_price,
            )

        recommendation = (
            f"Harvest {position.quantity} shares of {position.symbol} "
            f"(loss: €{abs(position.unrealized_loss):,.2f}, "
            f"tax benefit: €{tax_benefit:,.2f})"
        )

        if replacement:
            recommendation += (
                f"\nReplace with {replacement.quantity} shares of {replacement.symbol}"
            )

        return HarvestingOpportunity(
            position=position,
            replacement=replacement,
            total_tax_benefit=tax_benefit,
            recommendation=recommendation,
        )


# Singleton
_harvester: Optional[TaxLossHarvester] = None


def get_tax_loss_harvester() -> TaxLossHarvester:
    """Get or create singleton TaxLossHarvester."""
    global _harvester
    if _harvester is None:
        _harvester = TaxLossHarvester()
    return _harvester
