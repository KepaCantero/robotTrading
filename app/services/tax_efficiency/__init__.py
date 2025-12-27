"""
T15.1: Tax Efficiency System - Capital gains tracking and tax-loss harvesting

Provides:
- TaxLossHarvester: Identify and execute tax-loss harvesting
- WashSaleDetector: Detect and prevent wash-sale violations
- CapitalGainTracker: Track ST/LT gains and calculate tax liability
- TaxOptimizedPortfolioBuilder: Integrated tax-aware portfolio optimization
"""

from .capital_gain_tracker import (
    CapitalGainTracker,
    get_capital_gain_tracker,
)
from .tax_loss_harvester import (
    TaxLossHarvester,
    get_tax_loss_harvester,
)
from .tax_optimized_builder import (
    TaxOptimizedPortfolioBuilder,
    get_tax_optimized_builder,
)
from .wash_sale_detector import (
    WashSaleDetector,
    get_wash_sale_detector,
)

__all__ = [
    "TaxLossHarvester",
    "get_tax_loss_harvester",
    "WashSaleDetector",
    "get_wash_sale_detector",
    "CapitalGainTracker",
    "get_capital_gain_tracker",
    "TaxOptimizedPortfolioBuilder",
    "get_tax_optimized_builder",
]
