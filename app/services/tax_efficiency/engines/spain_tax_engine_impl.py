"""
Spain Tax Engine - Implementation for Spanish tax resident

Implements:
- IRPF-001: Progressive capital gains 19/21/23%
- DIV-001: EU dividends 0% vs Non-EU 19%
- MOD720-001: Modelo 720 reporting > €50k foreign assets
- LOSS-CF-001: Loss carryforward max 4 years
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import ClassVar

from app.shared.protocols.i_spain_tax_engine import ISpainTaxEngine

logger = logging.getLogger(__name__)


class SpainTaxEngineImpl(ISpainTaxEngine):
    """
    Motor de impuestos español para trading

    NOTA: España NO tiene distinción entre Long Term y Short Term.
    Todos los rendimientos de capital se gravan igual.
    """

    # IRPF Brackets 2026
    BRACKETS: ClassVar[list] = [
        {"min": 0, "max": 6000, "rate": Decimal("0.19")},
        {"min": 6000, "max": 50000, "rate": Decimal("0.21")},
        {"min": 50000, "max": 999999999, "rate": Decimal("0.23")},
    ]

    # EU Countries for dividend tax (DIV-001)
    EU_COUNTRIES: ClassVar[set[str]] = {
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

    # Modelo 720 threshold (MOD720-001)
    MODELO_720_THRESHOLD = Decimal("50000")

    def __init__(self):
        self._losses_by_year: dict[int, Decimal] = {}

    def calculate_capital_gains_tax(self, profit: Decimal) -> Decimal:
        """
        IRPF-001: Calcular IRPF sobre ganancias de capital

        Progresivo:
        - 0 - €6,000: 19%
        - €6,000 - €50,000: 21%
        - > €50,000: 23%

        Args:
            profit: Ganancia bruta

        Returns:
            Impuesto a pagar
        """
        logger.debug(
            "Calculating capital gains tax",
            extra={"profit": float(profit), "operation": "calculate_capital_gains_tax"},
        )
        if profit <= 0:
            logger.debug(
                "No tax on zero or negative profit", extra={"profit": float(profit), "tax": 0.0}
            )
            return Decimal("0")

        tax = Decimal("0")
        remaining = profit

        for bracket in self.BRACKETS:
            if remaining <= 0:
                break

            taxable_in_bracket = min(remaining, bracket["max"] - bracket["min"])

            tax += taxable_in_bracket * bracket["rate"]
            remaining -= taxable_in_bracket

        final_tax = tax.quantize(Decimal("0.01"))
        logger.info(
            "Capital gains tax calculated",
            extra={
                "profit": float(profit),
                "tax": float(final_tax),
                "effective_rate": float(final_tax / profit) if profit > 0 else 0.0,
            },
        )
        return final_tax

    def calculate_dividend_tax(self, symbol: str, amount: Decimal) -> Decimal:
        """
        DIV-001: Calcular retención de dividendos

        - UE: 0%
        - No-UE: 19%

        Args:
            symbol: Símbolo de ticker
            amount: Importe del dividendo

        Returns:
            Impuesto retenido
        """
        is_eu = self.is_eu_country(symbol)
        logger.debug(
            "Calculating dividend tax",
            extra={
                "symbol": symbol,
                "amount": float(amount),
                "is_eu": is_eu,
                "operation": "calculate_dividend_tax",
            },
        )
        if is_eu:
            logger.info(
                "EU dividend - no withholding tax",
                extra={"symbol": symbol, "amount": float(amount), "tax": 0.0, "is_eu": True},
            )
            return Decimal("0")
        else:
            tax = (amount * Decimal("0.19")).quantize(Decimal("0.01"))
            logger.info(
                "Non-EU dividend tax calculated",
                extra={
                    "symbol": symbol,
                    "amount": float(amount),
                    "tax": float(tax),
                    "is_eu": False,
                },
            )
            return tax

    def is_eu_country(self, symbol: str) -> bool:
        """
        Check if a stock symbol is from an EU country.

        This method checks if the ticker belongs to a European Union country
        for dividend tax calculation purposes (EU dividends: 0% withholding).

        The current implementation uses a curated list of major EU tickers.
        For comprehensive coverage, integrate with a securities master database
        or broker API that provides country of incorporation data.

        Args:
            symbol: Stock ticker symbol (e.g., "SAN", "ASML", "AAPL")

        Returns:
            True if the ticker is from an EU country, False otherwise

        Note:
            This list includes IBEX35 and Euro Stoxx 50 constituents.
            Add additional tickers as needed for your trading universe.
        """
        # Mapeo básico de tickers conocidos
        eu_tickers = {
            # IBEX35
            "SAN",
            "REE",
            "TEF",
            "ITX",
            "AMS",
            "ACS",
            "FER",
            "IAG",
            "BME",
            "ENG",
            "MAP",
            "SAB",
            "CLNX",
            "VIS",
            "COL",
            "MRL",
            # Euro Stoxx 50
            "ASML",
            "MC",
            "AIR",
            "ISP",
            "AI",
            "OR",
            "BNP",
            # Other EU
            "SAP",
            "SIE",
            "NESN",
            "RO",
            "NOVN",
            "UBSG",
            "DNB",
        }

        return symbol in eu_tickers

    def check_modelo_720_threshold(self, foreign_assets: Decimal) -> bool:
        """
        MOD720-001: Verificar si supera umbral de Modelo 720

        Args:
            foreign_assets: Total de activos en el extranjero

        Returns:
            True si > €50,000 (requiere Modelo 720)
        """
        exceeds = foreign_assets > self.MODELO_720_THRESHOLD
        logger.info(
            "Modelo 720 threshold check",
            extra={
                "foreign_assets": float(foreign_assets),
                "threshold": float(self.MODELO_720_THRESHOLD),
                "exceeds_threshold": exceeds,
                "operation": "check_modelo_720_threshold",
            },
        )
        return exceeds

    def generate_modelo_720_report(self, foreign_assets_data: dict | None = None) -> dict:
        """
        Generate a Modelo 720 report structure for foreign assets declaration.

        Modelo 720 is an annual information report that Spanish tax residents must
        file when they hold assets abroad worth more than €50,000 in total.

        Deadline: March 31st of the following year.

        For production implementation, integrate with broker API to automatically
        populate foreign assets data from account holdings.

        Args:
            foreign_assets_data: Optional dict with actual asset values from broker.
                Expected format:
                {
                    "stocks": {"symbol": value, ...},
                    "funds": {"isin": value, ...},
                    "bonds": {"isin": value, ...},
                    "cash_accounts": {"bank": value, ...}
                }

        Returns:
            Dictionary with Modelo 720 report structure

        Example:
            >>> generate_modelo_720_report({
            ...     "stocks": {"AAPL": 50000},
            ...     "funds": {},
            ...     "bonds": {},
            ...     "cash_accounts": {}
            ... })
        """
        logger.info(
            "Generating Modelo 720 report",
            extra={
                "has_data": foreign_assets_data is not None,
                "operation": "generate_modelo_720_report",
            },
        )
        current_year = datetime.now().year

        # If no data provided, return template structure
        if foreign_assets_data is None:
            foreign_assets_data = {
                "stocks": {},
                "funds": {},
                "bonds": {},
                "cash_accounts": {},
            }

        # Calculate total value
        total_value = Decimal("0")
        for category in foreign_assets_data.values():
            if isinstance(category, dict):
                total_value += Decimal(
                    str(
                        sum(
                            Decimal(str(v))
                            for v in category.values()
                            if isinstance(v, (int, float, str, Decimal))
                        )
                    )
                )

        report = {
            "report_type": "MODELO_720",
            "year": current_year,
            "deadline": f"{current_year + 1}-03-31",  # Always before March 31st
            "threshold": float(self.MODELO_720_THRESHOLD),
            "total_value_eur": float(total_value),
            "above_threshold": total_value > self.MODELO_720_THRESHOLD,
            "foreign_assets": foreign_assets_data,
        }
        logger.info(
            "Modelo 720 report generated",
            extra={
                "year": current_year,
                "total_value_eur": float(total_value),
                "above_threshold": total_value > self.MODELO_720_THRESHOLD,
            },
        )
        return report

    def record_loss(self, year: int, loss: Decimal) -> None:
        """
        LOSS-CF-001: Registrar pérdida para carryforward

        Args:
            year: Año de la pérdida
            loss: Importe de la pérdida
        """
        logger.info(
            "Recording loss for carryforward",
            extra={"year": year, "loss": float(loss), "operation": "record_loss"},
        )
        if year not in self._losses_by_year:
            self._losses_by_year[year] = Decimal("0")

        self._losses_by_year[year] += loss
        logger.debug(
            "Loss recorded",
            extra={"year": year, "total_loss_for_year": float(self._losses_by_year[year])},
        )

    def get_available_losses(self, current_year: int) -> Decimal:
        """
        LOSS-CF-001: Obtener pérdidas disponibles para compensar

        Solo pérdidas de los últimos 4 años

        Args:
            current_year: Año actual

        Returns:
            Pérdidas disponibles
        """
        available = Decimal("0")
        min_year = current_year - 4

        for year, loss in self._losses_by_year.items():
            if min_year <= year < current_year:
                available += loss

        return available

    def apply_loss_carryforward(
        self, profit: Decimal, current_year: int
    ) -> tuple[Decimal, Decimal]:
        """
        LOSS-CF-001: Aplicar carryforward de pérdidas

        Args:
            profit: Ganancia actual
            current_year: Año actual

        Returns:
            (profit_after_losses, losses_used)
        """
        available_losses = self.get_available_losses(current_year)
        logger.debug(
            "Applying loss carryforward",
            extra={
                "profit": float(profit),
                "current_year": current_year,
                "available_losses": float(available_losses),
                "operation": "apply_loss_carryforward",
            },
        )

        if available_losses >= profit:
            # Usar solo lo necesario
            result = (Decimal("0"), profit)
            logger.info(
                "Loss carryforward applied - full profit offset",
                extra={
                    "original_profit": float(profit),
                    "losses_used": float(profit),
                    "remaining_profit": 0.0,
                },
            )
            return result
        else:
            # Usar todas las pérdidas disponibles
            result = (profit - available_losses), available_losses
            logger.info(
                "Loss carryforward applied - partial offset",
                extra={
                    "original_profit": float(profit),
                    "losses_used": float(available_losses),
                    "remaining_profit": float(result[0]),
                },
            )
            return result
