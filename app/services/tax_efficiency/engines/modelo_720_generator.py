"""
Modelo 720 Report Generator

Genera reportes para el Modelo 720 (declaracion de bienes en el extranjero)
"""
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class Modelo720Generator:
    """
    Generador de reportes Modelo 720

    El Modelo 720 debe presentarse antes del 31 de marzo de cada ano.
    Incluye todos los activos en el extranjero > EUR50k.
    """

    def __init__(self):
        self.assets = {
            "stocks": {},
            "funds": {},
            "bonds": {},
            "cash_accounts": {},
        }

        logger.info(
            "Modelo720Generator initialized",
            extra={
                "component": "modelo_720_generator",
                "operation": "init",
            },
        )

    def add_stock(self, symbol: str, isin: str, value: Decimal) -> None:
        """Anadir accion extranjera"""
        country = self._get_country_from_isin(isin)

        self.assets["stocks"][symbol] = {
            "isin": isin,
            "value": float(value),
            "country": country,
        }

        logger.info(
            "Stock added to Modelo 720",
            extra={
                "component": "modelo_720_generator",
                "operation": "add_stock",
                "symbol": symbol,
                "isin": isin,
                "value": str(value),
                "country": country,
            },
        )

    def add_fund(self, name: str, isin: str, value: Decimal) -> None:
        """Anadir fondo extranjero"""
        country = self._get_country_from_isin(isin)

        self.assets["funds"][name] = {
            "isin": isin,
            "value": float(value),
            "country": country,
        }

        logger.info(
            "Fund added to Modelo 720",
            extra={
                "component": "modelo_720_generator",
                "operation": "add_fund",
                "name": name,
                "isin": isin,
                "value": str(value),
                "country": country,
            },
        )

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
        # ISIN: primeros 2 caracteres son el pais
        country = isin[:2] if len(isin) >= 2 else "UNKNOWN"

        logger.debug(
            "Country extracted from ISIN",
            extra={
                "component": "modelo_720_generator",
                "operation": "get_country_from_isin",
                "isin": isin,
                "country": country,
            },
        )

        return country

    def generate_report(self, year: int) -> dict:
        """
        Generar reporte completo para Modelo 720

        Args:
            year: Ano fiscal

        Returns:
            Diccionario con datos del reporte
        """
        logger.info(
            "Generating Modelo 720 report",
            extra={
                "component": "modelo_720_generator",
                "operation": "generate_report",
                "year": year,
            },
        )

        total_value = sum(
            sum(item["value"] for item in category.values()) for category in self.assets.values()
        )

        above_threshold = total_value > 50000

        report = {
            "report_type": "MODELO_720",
            "year": year,
            "generated_at": datetime.now().isoformat(),
            "deadline": f"{year + 1}-03-31",
            "total_value_eur": total_value,
            "above_threshold": above_threshold,
            "assets": self.assets,
            "summary": {
                "stocks_count": len(self.assets["stocks"]),
                "funds_count": len(self.assets["funds"]),
                "bonds_count": len(self.assets["bonds"]),
                "cash_accounts_count": len(self.assets["cash_accounts"]),
            },
        }

        logger.info(
            "Modelo 720 report generated",
            extra={
                "component": "modelo_720_generator",
                "operation": "generate_report_complete",
                "year": year,
                "total_value_eur": total_value,
                "above_threshold": above_threshold,
                "stocks_count": len(self.assets["stocks"]),
                "funds_count": len(self.assets["funds"]),
            },
        )

        if above_threshold:
            logger.warning(
                "Modelo 720 report exceeds EUR50k threshold - declaration required",
                extra={
                    "component": "modelo_720_generator",
                    "operation": "generate_report",
                    "total_value_eur": total_value,
                    "threshold": 50000,
                },
            )

        return report
