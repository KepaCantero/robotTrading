"""
T15.1.4: TaxOptimizedPortfolioBuilder - Integrated tax-aware portfolio optimization

Combines TaxLossHarvester, WashSaleDetector, and CapitalGainTracker to create
tax-efficient portfolio allocations.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from .capital_gain_tracker import get_capital_gain_tracker
from .tax_loss_harvester import get_tax_loss_harvester
from .wash_sale_detector import get_wash_sale_detector

logger = logging.getLogger(__name__)


@dataclass
class TaxOptimizedAllocation:
    """Tax-optimized portfolio allocation."""
    base_allocation: Dict[str, Decimal]  # symbol → weight
    tax_adjusted_allocation: Dict[str, Decimal]  # symbol → adjusted weight
    harvesting_opportunities: List[str]  # symbols to harvest
    tax_benefit_estimated: Decimal  # €
    after_tax_return_pct: Decimal  # %
    adjustments_made: List[str]  # list of changes


class TaxOptimizedPortfolioBuilder:
    """
    Builds tax-efficient portfolios by integrating tax optimization strategies.

    Features:
    - Harvest tax losses while maintaining desired allocation
    - Avoid wash-sale violations
    - Rebalance with tax efficiency in mind
    - Calculate after-tax returns
    """

    def __init__(self):
        """Initialize tax-optimized builder."""
        self.harvester = get_tax_loss_harvester()
        self.wash_detector = get_wash_sale_detector()
        self.gain_tracker = get_capital_gain_tracker()
        logger.info("✅ TaxOptimizedPortfolioBuilder initialized")

    async def optimize_for_taxes(
        self,
        base_allocation: Dict[str, Decimal],  # symbol → target weight
        current_positions: Dict[str, Decimal],  # symbol → current value
        cost_basis: Dict[str, Decimal],  # symbol → total cost
        quantities: Dict[str, Decimal],  # symbol → shares owned
        current_prices: Dict[str, Decimal],  # symbol → price per share
        marginal_tax_rate: Decimal = Decimal("0.25"),
        capital: Decimal = Decimal("100000"),
    ) -> TaxOptimizedAllocation:
        """
        Optimize portfolio for tax efficiency.

        Strategy:
        1. Identify harvestable losses in positions overweight vs target
        2. Execute tax loss harvesting
        3. Suggest replacements (wash-sale compliant)
        4. Calculate resulting allocation and tax benefit

        Args:
            base_allocation: Target portfolio allocation (symbol → weight)
            current_positions: Current position values
            cost_basis: Cost basis per symbol
            quantities: Shares owned per symbol
            current_prices: Current prices per share
            marginal_tax_rate: Investor's marginal tax rate
            capital: Total portfolio capital

        Returns:
            Tax-optimized allocation with adjustments
        """
        adjustments = []

        # Step 1: Identify harvestable positions (losses in overweight positions)
        harvestable = self.harvester.identify_harvestable_positions(
            current_positions, cost_basis, quantities, current_prices
        )

        harvesting_symbols = []
        total_tax_benefit = Decimal("0")

        # Step 2: Check each harvestable position
        for position in harvestable:
            # Calculate current vs target weight
            current_weight = (current_positions.get(position.symbol, Decimal("0")) / capital)
            target_weight = base_allocation.get(position.symbol, Decimal("0"))

            # Only harvest if position is overweight or we're below target allocation
            if current_weight <= target_weight + Decimal("0.05"):  # 5% tolerance
                continue

            # Calculate tax benefit
            tax_benefit = self.harvester.calculate_tax_benefit(
                position.unrealized_loss, marginal_tax_rate
            )

            # Suggest replacement
            replacement = self.harvester.suggest_replacement_position(
                position.symbol,
                position.quantity,
                position.current_price,
            )

            harvesting_symbols.append(position.symbol)
            total_tax_benefit += tax_benefit

            adjustments.append(
                f"Harvest {position.symbol}: {tax_benefit:.2f} € tax benefit, "
                f"replace with {replacement.symbol}"
            )

        # Step 3: Apply adjustments to allocation
        adjusted_allocation = base_allocation.copy()
        for symbol in harvesting_symbols:
            # Reduce harvested position to target
            adjusted_allocation[symbol] = base_allocation.get(symbol, Decimal("0"))

            # Increase replacement position
            # (simplified - would need to track replacements)

        # Step 4: Calculate after-tax return
        # Simplified: assume base return of 5%, reduce by estimated tax on gains
        base_return = Decimal("5.0")  # 5% annual return
        if capital > 0:
            estimated_gains = capital * base_return / Decimal("100")
            tax_on_gains = (estimated_gains * marginal_tax_rate) - total_tax_benefit
            after_tax_return = base_return - (tax_on_gains / capital * Decimal("100"))
            after_tax_return = max(after_tax_return, Decimal("0"))
        else:
            after_tax_return = Decimal("0")

        result = TaxOptimizedAllocation(
            base_allocation=base_allocation,
            tax_adjusted_allocation=adjusted_allocation,
            harvesting_opportunities=harvesting_symbols,
            tax_benefit_estimated=total_tax_benefit,
            after_tax_return_pct=after_tax_return,
            adjustments_made=adjustments,
        )

        logger.info(f"✅ Optimized portfolio for taxes: €{total_tax_benefit:,.2f} benefit")
        return result

    def calculate_after_tax_return(
        self,
        gross_return_pct: Decimal,
        realized_gains: Decimal,
        realized_losses: Decimal,
        long_term_percentage: Decimal = Decimal("0.6"),  # 60% LT, 40% ST
        marginal_tax_rate_st: Decimal = Decimal("0.35"),
        marginal_tax_rate_lt: Decimal = Decimal("0.15"),
    ) -> Decimal:
        """
        Calculate after-tax return accounting for capital gains taxes.

        Args:
            gross_return_pct: Gross return percentage
            realized_gains: Total realized gains
            realized_losses: Total realized losses
            long_term_percentage: % of gains that are long-term
            marginal_tax_rate_st: Short-term tax rate
            marginal_tax_rate_lt: Long-term tax rate

        Returns:
            After-tax return percentage
        """
        net_gains = realized_gains - realized_losses

        if net_gains <= 0:
            return gross_return_pct

        # Calculate tax
        lt_gains = net_gains * long_term_percentage
        st_gains = net_gains * (Decimal("1") - long_term_percentage)

        taxes = (lt_gains * marginal_tax_rate_lt) + (st_gains * marginal_tax_rate_st)

        # After-tax return = Gross return - (Taxes / Capital)
        # Simplified calculation
        after_tax = gross_return_pct - (taxes / Decimal("100000") * Decimal("100"))

        return max(after_tax, Decimal("0"))

    def get_tax_report(self) -> Dict:
        """
        Get comprehensive tax report for the portfolio.

        Returns:
            Dict with gains/losses, tax liability, recommendations
        """
        gain_report = self.gain_tracker.generate_tax_lot_report()
        compliance_report = self.wash_detector.generate_compliance_report()

        return {
            "capital_gains_summary": {
                "short_term_gains": float(gain_report.total_short_term_gains),
                "short_term_losses": float(gain_report.total_short_term_losses),
                "long_term_gains": float(gain_report.total_long_term_gains),
                "long_term_losses": float(gain_report.total_long_term_losses),
                "net_gain_loss": float(gain_report.net_capital_gain_loss),
                "projected_tax": float(gain_report.projected_annual_tax),
            },
            "wash_sale_compliance": compliance_report,
            "tax_efficiency_score": self._calculate_tax_efficiency_score(gain_report),
        }

    def _calculate_tax_efficiency_score(self, gain_report) -> Decimal:
        """
        Calculate a score (0-100) for tax efficiency.

        Higher score = better tax efficiency.
        """
        # More long-term gains = higher efficiency
        total_gains = (gain_report.total_long_term_gains +
                      gain_report.total_short_term_gains)

        if total_gains <= 0:
            return Decimal("100")  # No gains = no tax

        lt_percentage = gain_report.total_long_term_gains / total_gains

        # Score: 50-100 based on LT percentage (100 = 100% LT)
        score = Decimal("50") + (lt_percentage * Decimal("50"))

        return min(score, Decimal("100"))


# Singleton
_builder: Optional[TaxOptimizedPortfolioBuilder] = None


def get_tax_optimized_builder() -> TaxOptimizedPortfolioBuilder:
    """Get or create singleton TaxOptimizedPortfolioBuilder."""
    global _builder
    if _builder is None:
        _builder = TaxOptimizedPortfolioBuilder()
    return _builder
