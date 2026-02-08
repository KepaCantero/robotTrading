"""
Spain tax protocols (IRPF, Dividendos, Modelo 720)
"""
from typing import Protocol
from decimal import Decimal


class ISpainTaxEngine(Protocol):
    """Motor de impuestos España - Máximo 5 métodos"""

    def calculate_capital_gains_tax(self, profit: Decimal) -> Decimal:
        """IRPF-001: Progresivo 19/21/23%"""
        ...

    def calculate_dividend_tax(self, symbol: str, amount: Decimal) -> Decimal:
        """DIV-001: UE 0% vs No-UE 19%"""
        ...

    def is_eu_country(self, symbol: str) -> bool:
        """Verificar si país es UE"""
        ...

    def check_modelo_720_threshold(self, foreign_assets: Decimal) -> bool:
        """MOD720-001: > €50k extranjeros"""
        ...

    def generate_modelo_720_report(self) -> dict:
        """Generar reporte Modelo 720"""
        ...
