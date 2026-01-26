"""
Tax Engines - Country-specific tax calculation implementations.

This module provides tax engines for different jurisdictions, each
implementing the TaxEngine interface with country-specific tax rules.

Available engines:
- SpainTaxEngine: Progressive 19/21/23% rates, no LT/ST distinction
- More engines can be added as needed (US, UK, DE, FR, etc.)

Usage:
    from app.services.tax_efficiency.engines import get_tax_engine

    engine = get_tax_engine("ES")  # Spain
    tax = engine.calculate_capital_gains_tax(Decimal("10000"))
"""

from app.services.tax_efficiency.engines.base import TaxEngine
from app.services.tax_efficiency.engines.factory import (
    get_tax_engine,
    get_supported_countries,
    is_country_supported,
    register_tax_engine,
)
from app.services.tax_efficiency.engines.spain_tax_engine import SpainTaxEngine

__all__ = [
    # Base classes
    "TaxEngine",
    # Implementations
    "SpainTaxEngine",
    # Factory functions
    "get_tax_engine",
    "get_supported_countries",
    "is_country_supported",
    "register_tax_engine",
]
