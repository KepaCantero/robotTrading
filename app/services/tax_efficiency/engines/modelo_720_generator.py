"""
Modelo 720 Report Generator

Genera reportes para el Modelo 720 (declaración de bienes en el extranjero)
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict


class Modelo720Generator:
    """
    Generador de reportes Modelo 720

    El Modelo 720 debe presentarse antes del 31 de marzo de cada año.
    Incluye todos los activos en el extranjero > €50k.
    """

    def __init__(self):
        self.assets = {
            "stocks": {},
            "funds": {},
            "bonds": {},
            "cash_accounts": {},
        }

    def add_stock(self, symbol: str, isin: str, value: Decimal) -> None:
        """Añadir acción extranjera"""
        self.assets["stocks"][symbol] = {
            "isin": isin,
            "value": float(value),
            "country": self._get_country_from_isin(isin),
        }

    def add_fund(self, name: str, isin: str, value: Decimal) -> None:
        """Añadir fondo extranjero"""
        self.assets["funds"][name] = {
            "isin": isin,
            "value": float(value),
            "country": self._get_country_from_isin(isin),
        }

    def _get_country_from_isin(self, isin: str) -> str:
        """
        Extract country code from ISIN (International Securities Identification Number).

        ISIN format: First 2 characters represent the country code per ISO 3166-1 alpha-2.
        For enhanced accuracy, consider integrating with a securities database service
        to handle edge cases and historical ISIN changes.

        Args:
            isin: International Securities Identification Number (12 characters)

        Returns:
            Country code (ISO 3166-1 alpha-2 format)

        Examples:
            >>> _get_country_from_isin("US0378331005")  # Apple
            'US'
            >>> _get_country_from_isin("ES0173546111")  # Telefonica
            'ES'
        """
        # ISIN: primeros 2 caracteres son el país
        return isin[:2] if len(isin) >= 2 else "UNKNOWN"

    def generate_report(self, year: int) -> dict:
        """
        Generar reporte completo para Modelo 720

        Args:
            year: Año fiscal

        Returns:
            Diccionario con datos del reporte
        """
        total_value = sum(
            sum(item["value"] for item in category.values()) for category in self.assets.values()
        )

        return {
            "report_type": "MODELO_720",
            "year": year,
            "generated_at": datetime.now().isoformat(),
            "deadline": f"{year + 1}-03-31",
            "total_value_eur": total_value,
            "above_threshold": total_value > 50000,
            "assets": self.assets,
            "summary": {
                "stocks_count": len(self.assets["stocks"]),
                "funds_count": len(self.assets["funds"]),
                "bonds_count": len(self.assets["bonds"]),
                "cash_accounts_count": len(self.assets["cash_accounts"]),
            },
        }
