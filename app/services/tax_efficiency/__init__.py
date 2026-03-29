"""
T15.1: Tax Efficiency System - Capital gains tracking and tax-loss harvesting

Provides:
- TaxLossHarvester: Identify and execute tax-loss harvesting
- WashSaleDetector: Detect and prevent wash-sale violations
- CapitalGainTracker: Track ST/LT gains and calculate tax liability
- TaxOptimizedPortfolioBuilder: Integrated tax-aware portfolio optimization
- Tax Engines: Country-specific tax calculations (Spain, US, UK, etc.)
"""

from .capital_gain_tracker import CapitalGainTracker, get_capital_gain_tracker
from .engines import SpainTaxEngine, get_tax_engine, is_country_supported
from .tax_loss_harvester import TaxLossHarvester, get_tax_loss_harvester
from .tax_optimized_builder import TaxOptimizedPortfolioBuilder, get_tax_optimized_builder
from .wash_sale_detector import WashSaleDetector, get_wash_sale_detector

__all__ = [
    "CapitalGainTracker",
    # Tax engines
    "SpainTaxEngine",
    "TaxLossHarvester",
    "TaxOptimizedPortfolioBuilder",
    "WashSaleDetector",
    "get_capital_gain_tracker",
    "get_tax_engine",
    "get_tax_loss_harvester",
    "get_tax_optimized_builder",
    "get_wash_sale_detector",
    "is_country_supported",
]
