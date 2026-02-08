"""
Spain Tax Engine - Implementation for Spanish tax resident

Implements:
- IRPF-001: Progressive capital gains 19/21/23%
- DIV-001: EU dividends 0% vs Non-EU 19%
- MOD720-001: Modelo 720 reporting > €50k foreign assets
- LOSS-CF-001: Loss carryforward max 4 years
"""
from typing import Optional
from decimal import Decimal
from datetime import datetime, date
from app.core.protocols.i_spain_tax_engine import ISpainTaxEngine  # @skip-import si no existe


class SpainTaxEngineImpl(ISpainTaxEngine):
    """
    Motor de impuestos español para trading

    NOTA: España NO tiene distinción entre Long Term y Short Term.
    Todos los rendimientos de capital se gravan igual.
    """

    # IRPF Brackets 2026
    BRACKETS = [
        {"min": 0, "max": 6000, "rate": Decimal("0.19")},
        {"min": 6000, "max": 50000, "rate": Decimal("0.21")},
        {"min": 50000, "max": 999999999, "rate": Decimal("0.23")},
    ]

    # EU Countries for dividend tax (DIV-001)
    EU_COUNTRIES = {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IS", "IE", "IT", "LV", "LI", "LT", "LU",
        "MT", "NL", "NO", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
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
        if profit <= 0:
            return Decimal("0")

        tax = Decimal("0")
        remaining = profit

        for bracket in self.BRACKETS:
            if remaining <= 0:
                break

            taxable_in_bracket = min(
                remaining,
                bracket["max"] - bracket["min"]
            )

            tax += taxable_in_bracket * bracket["rate"]
            remaining -= taxable_in_bracket

        return tax.quantize(Decimal("0.01"))

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
        if self.is_eu_country(symbol):
            return Decimal("0")
        else:
            return (amount * Decimal("0.19")).quantize(Decimal("0.01"))

    def is_eu_country(self, symbol: str) -> bool:
        """
        Verificar si el ticker es de un país UE

        @todo: Implementar mapeo completo ticker -> país
        TODO: Agregar más tickers europeos

        Args:
            symbol: Símbolo de ticker

        Returns:
            True si es UE, False otherwise
        """
        # Mapeo básico de tickers conocidos
        eu_tickers = {
            # IBEX35
            "SAN", "REE", "TEF", "ITX", "AMS", "ACS", "FER", "IAG",
            "BME", "ENG", "MAP", "SAB", "CLNX", "VIS", "COL", "MRL",

            # Euro Stoxx 50
            "ASML", "MC", "AIR", "SAN", "ISP", "AI", "OR", "BNP",

            # Other EU
            "SAP", "SIE", "NESN", "RO", "NOVN", "UBSG", "DNB",
        }

        # @clarify: ¿Cómo detectar país desde ticker de IBKR?
        # TODO: Implementar búsqueda en base de datos de IBKR

        return symbol in eu_tickers

    def check_modelo_720_threshold(self, foreign_assets: Decimal) -> bool:
        """
        MOD720-001: Verificar si supera umbral de Modelo 720

        Args:
            foreign_assets: Total de activos en el extranjero

        Returns:
            True si > €50,000 (requiere Modelo 720)
        """
        return foreign_assets > self.MODELO_720_THRESHOLD

    def generate_modelo_720_report(self) -> dict:
        """
        MOD720-001: Generar reporte para Modelo 720

        @todo: Implementar generación real del reporte
        TODO: Conectar con datos de broker

        Returns:
            Diccionario con datos para Modelo 720
        """
        return {
            "report_type": "MODELO_720",
            "year": datetime.now().year,
            "deadline": "2026-03-31",  # Siempre antes del 31 de marzo
            "threshold": float(self.MODELO_720_THRESHOLD),
            "foreign_assets": {
                "stocks": "TODO: Get from broker",
                "funds": "TODO: Get from broker",
                "bonds": "TODO: Get from broker",
            },
            "@todo": "Conectar con broker API para obtener valores reales"
        }

    def record_loss(self, year: int, loss: Decimal) -> None:
        """
        LOSS-CF-001: Registrar pérdida para carryforward

        Args:
            year: Año de la pérdida
            loss: Importe de la pérdida
        """
        if year not in self._losses_by_year:
            self._losses_by_year[year] = Decimal("0")

        self._losses_by_year[year] += loss

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

    def apply_loss_carryforward(self, profit: Decimal, current_year: int) -> tuple[Decimal, Decimal]:
        """
        LOSS-CF-001: Aplicar carryforward de pérdidas

        Args:
            profit: Ganancia actual
            current_year: Año actual

        Returns:
            (profit_after_losses, losses_used)
        """
        available_losses = self.get_available_losses(current_year)

        if available_losses >= profit:
            # Usar solo lo necesario
            return Decimal("0"), profit
        else:
            # Usar todas las pérdidas disponibles
            return (profit - available_losses), available_losses
