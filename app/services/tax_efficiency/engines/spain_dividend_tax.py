"""
Spain Dividend Tax Calculator

Calcula retenciones de dividendos para residentes espanoles
"""

import logging
from decimal import Decimal
from typing import ClassVar

logger = logging.getLogger(__name__)


class SpainDividendTaxCalculator:
    """
    Calculadora de impuestos sobre dividendos

    - UE: 0% retencion
    - No-UE: 19% retencion
    """

    # Paises UE (codigos ISO)
    EU_COUNTRY_CODES: ClassVar[dict] = {
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IS",
        "IE",
        "IT",
        "LV",
        "LI",
        "LT",
        "LU",
        "MT",
        "NL",
        "NO",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
    }

    UE_WITHHOLDING = Decimal("0.00")
    NON_EU_WITHHOLDING = Decimal("0.19")

    def __init__(self):
        """Initialize the dividend tax calculator.

        The ticker-to-country mapping contains major European and Spanish stocks.
        For production use, integrate with a securities master database or broker API
        to maintain comprehensive ticker mappings.
        """
        self._ticker_to_country: dict[str, str] = {
            # IBEX35
            "SAN": "ES",
            "REE": "ES",
            "TEF": "ES",
            # Euro Stoxx
            "ASML": "NL",
            "MC": "FR",
            "AIR": "FR",
        }

        logger.info(
            "SpainDividendTaxCalculator initialized",
            extra={
                "component": "spain_dividend_tax",
                "operation": "init",
                "ue_withholding": str(self.UE_WITHHOLDING),
                "non_ue_withholding": str(self.NON_EU_WITHHOLDING),
                "ticker_mappings_count": len(self._ticker_to_country),
            },
        )

    def calculate_withholding(self, symbol: str, gross_amount: Decimal) -> dict:
        """
        Calcular retencion sobre dividendo

        Args:
            symbol: Ticker
            gross_amount: Importe bruto del dividendo

        Returns:
            {
                "gross": float,
                "withholding_rate": float,
                "withholding_amount": float,
                "net": float,
                "country": str,
                "is_eu": bool
            }
        """
        country = self._get_country(symbol)
        is_eu = country in self.EU_COUNTRY_CODES

        rate = self.UE_WITHHOLDING if is_eu else self.NON_EU_WITHHOLDING

        withholding_amount = gross_amount * rate
        net_amount = gross_amount - withholding_amount

        logger.info(
            "Dividend withholding calculated",
            extra={
                "component": "spain_dividend_tax",
                "operation": "calculate_withholding",
                "symbol": symbol,
                "country": country,
                "is_eu": is_eu,
                "gross_amount": str(gross_amount),
                "withholding_rate": str(rate),
                "withholding_amount": str(withholding_amount),
                "net_amount": str(net_amount),
            },
        )

        return {
            "gross": float(gross_amount),
            "withholding_rate": float(rate),
            "withholding_amount": float(withholding_amount),
            "net": float(net_amount),
            "country": country,
            "is_eu": is_eu,
        }

    def _get_country(self, symbol: str) -> str:
        """
        Get country code for a stock symbol.

        This method looks up the country from the internal ticker-to-country mapping.
        For enhanced accuracy, consider integrating with Interactive Brokers or other
        broker APIs to fetch country information directly.

        Args:
            symbol: Stock ticker symbol (e.g., "SAN", "ASML")

        Returns:
            Country code (ISO 3166-1 alpha-2 format)
            Returns "UNKNOWN" if ticker not found in mapping

        Note:
            To add new ticker mappings, use add_ticker_mapping() method
        """
        country = self._ticker_to_country.get(symbol, "UNKNOWN")

        logger.debug(
            "Country lookup for symbol",
            extra={
                "component": "spain_dividend_tax",
                "operation": "get_country",
                "symbol": symbol,
                "country": country,
                "found": country != "UNKNOWN",
            },
        )

        return country

    def add_ticker_mapping(self, symbol: str, country: str) -> None:
        """Anadir mapeo ticker -> pais"""
        old_country = self._ticker_to_country.get(symbol)
        self._ticker_to_country[symbol] = country

        logger.info(
            "Ticker mapping added/updated",
            extra={
                "component": "spain_dividend_tax",
                "operation": "add_ticker_mapping",
                "symbol": symbol,
                "old_country": old_country,
                "new_country": country,
            },
        )
