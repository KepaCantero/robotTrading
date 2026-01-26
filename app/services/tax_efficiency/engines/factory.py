"""
Tax Engine Factory - Creates appropriate tax engine based on residence.

Supports multiple tax jurisdictions:
- ES: Spain
- US: United States
- UK: United Kingdom
- DE: Germany
- FR: France

This factory provides a clean interface for getting the appropriate
tax engine based on the investor's country of tax residence.
"""

import logging
from typing import Dict, Optional

from app.services.tax_efficiency.engines.base import TaxEngine
from app.services.tax_efficiency.engines.spain_tax_engine import SpainTaxEngine

logger = logging.getLogger(__name__)


# Registry of available tax engines
TAX_ENGINES: Dict[str, type] = {
    "ES": SpainTaxEngine,
    # Add more engines as they are implemented:
    # "US": USTaxEngine,
    # "UK": UKTaxEngine,
    # "DE": GermanyTaxEngine,
    # "FR": FranceTaxEngine,
}


def get_tax_engine(
    country_code: str = "ES",
    config: Optional[Dict] = None,
) -> TaxEngine:
    """
    Get tax engine for specified country.

    Args:
        country_code: ISO country code (ES, US, UK, etc.)
        config: Optional configuration dictionary for the tax engine

    Returns:
        Tax engine instance

    Raises:
        ValueError: If country_code is not a valid ISO code

    Example:
        >>> engine = get_tax_engine("ES")
        >>> tax = engine.calculate_capital_gains_tax(Decimal("10000"))
        >>> print(f"Tax: €{tax}")
        Tax: €1900.00

        >>> us_engine = get_tax_engine("US", config={"lt_rate": 0.20})
        >>> us_tax = us_engine.calculate_capital_gains_tax(
        ...     Decimal("10000"),
        ...     holding_period_days=400
        ... )
    """
    if not country_code or len(country_code) != 2:
        raise ValueError(
            f"Invalid country code '{country_code}'. "
            "Must be a 2-letter ISO country code."
        )

    country_code = country_code.upper()

    engine_class = TAX_ENGINES.get(country_code)

    if not engine_class:
        logger.warning(
            f"No tax engine implemented for {country_code}, "
            f"defaulting to Spain engine"
        )
        engine_class = SpainTaxEngine

    engine = engine_class(config or {})

    logger.info(f"Created {engine.__class__.__name__} for country {country_code}")

    return engine


def register_tax_engine(country_code: str, engine_class: type) -> None:
    """
    Register a new tax engine for a country.

    This allows for dynamic registration of tax engines at runtime,
    useful for plugins or extending the system without modifying core code.

    Args:
        country_code: ISO country code (2 letters)
        engine_class: Tax engine class (must inherit from TaxEngine)

    Raises:
        ValueError: If engine_class doesn't inherit from TaxEngine

    Example:
        >>> from app.services.tax_efficiency.engines.base import TaxEngine
        >>> class PortugalTaxEngine(TaxEngine):
        ...     # Implementation here
        ...     pass
        >>> register_tax_engine("PT", PortugalTaxEngine)
    """
    if not issubclass(engine_class, TaxEngine):
        raise ValueError(
            f"Engine class must inherit from TaxEngine, "
            f"got {engine_class.__name__}"
        )

    country_code = country_code.upper()
    TAX_ENGINES[country_code] = engine_class

    logger.info(f"Registered {engine_class.__name__} for country {country_code}")


def get_supported_countries() -> list[str]:
    """
    Get list of supported country codes.

    Returns:
        List of ISO country codes with implemented tax engines

    Example:
        >>> countries = get_supported_countries()
        >>> print(countries)
        ['ES']
    """
    return sorted(TAX_ENGINES.keys())


def is_country_supported(country_code: str) -> bool:
    """
    Check if a country has a specific tax engine implementation.

    Args:
        country_code: ISO country code

    Returns:
        True if country has a dedicated tax engine

    Example:
        >>> is_country_supported("ES")
        True
        >>> is_country_supported("XX")
        False
    """
    return country_code.upper() in TAX_ENGINES
