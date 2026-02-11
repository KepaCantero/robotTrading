"""
Spain Dividend Tax Calculator

Calcula retenciones de dividendos para residentes españoles
"""
from decimal import Decimal
from typing import dict


class SpainDividendTaxCalculator:
    """
    Calculadora de impuestos sobre dividendos

    - UE: 0% retención
    - No-UE: 19% retención
    """

    # Países UE (códigos ISO)
    EU_COUNTRY_CODES = {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IS", "IE", "IT", "LV", "LI", "LT", "LU",
        "MT", "NL", "NO", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
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
            "SAN": "ES", "REE": "ES", "TEF": "ES",
            # Euro Stoxx
            "ASML": "NL", "MC": "FR", "AIR": "FR",
        }

    def calculate_withholding(self, symbol: str, gross_amount: Decimal) -> dict:
        """
        Calcular retención sobre dividendo

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

        if is_eu:
            rate = self.UE_WITHHOLDING
        else:
            rate = self.NON_EU_WITHHOLDING

        withholding_amount = gross_amount * rate
        net_amount = gross_amount - withholding_amount

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
        return self._ticker_to_country.get(symbol, "UNKNOWN")

    def add_ticker_mapping(self, symbol: str, country: str) -> None:
        """Añadir mapeo ticker -> país"""
        self._ticker_to_country[symbol] = country
