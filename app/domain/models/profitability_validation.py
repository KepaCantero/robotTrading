"""
Modelos Pydantic para validación de rentabilidad de estrategias.

Este módulo define los modelos de datos para validar que las estrategias
generen rentabilidad neta positiva después de todos los costos operativos.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ValidationStatus(str, Enum):
    """Estado de la validación de rentabilidad."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"


class ProfitabilityMetric(str, Enum):
    """Métricas de rentabilidad disponibles."""

    NET_PROFIT = "net_profit"
    GROSS_PROFIT = "gross_profit"
    TOTAL_COSTS = "total_costs"
    PROFIT_MARGIN = "profit_margin"
    RETURN_ON_INVESTMENT = "return_on_investment"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    COST_IMPACT_RATIO = "cost_impact_ratio"


class CostBreakdown(BaseModel):
    """Desglose detallado de costos operativos."""

    commissions: Decimal = Field(..., description="Comisiones pagadas")
    slippage: Decimal = Field(..., description="Slippage total")
    market_impact: Decimal = Field(..., description="Impacto en el mercado")
    infrastructure: Decimal = Field(..., description="Costos de infraestructura")
    data_fees: Decimal = Field(default=Decimal("0"), description="Costos de datos de mercado")
    financing: Decimal = Field(default=Decimal("0"), description="Costos de financiación")
    other: Decimal = Field(default=Decimal("0"), description="Otros costos")

    @property
    def total_costs(self) -> Decimal:
        """Calcular el total de costos."""
        return (
            self.commissions
            + self.slippage
            + self.market_impact
            + self.infrastructure
            + self.data_fees
            + self.financing
            + self.other
        )

    @field_validator(
        "commissions",
        "slippage",
        "market_impact",
        "infrastructure",
        "data_fees",
        "financing",
        "other",
    )
    @classmethod
    def validate_positive_amount(cls, v):
        if v < 0:
            raise ValueError("Cost amounts must be non-negative")
        return v


class ProfitabilityMetrics(BaseModel):
    """Métricas de rentabilidad calculadas."""

    gross_profit: Decimal = Field(..., description="Ganancia bruta")
    net_profit: Decimal = Field(..., description="Ganancia neta")
    total_costs: Decimal = Field(..., description="Costos totales")
    profit_margin: Decimal = Field(..., description="Margen de ganancia (%)")
    return_on_investment: Decimal = Field(..., description="ROI (%)")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Ratio de Sharpe")
    max_drawdown: Decimal = Field(..., description="Drawdown máximo (%)")
    win_rate: Decimal = Field(..., description="Tasa de ganancia (%)")
    profit_factor: Decimal = Field(..., description="Factor de ganancia")
    cost_impact_ratio: Decimal = Field(..., description="Ratio de impacto de costos")

    @field_validator("profit_margin", "return_on_investment", "max_drawdown", "win_rate")
    @classmethod
    def validate_percentage(cls, v):
        if not -100 <= v <= 1000:  # Permitir hasta 1000% para casos extremos
            raise ValueError("Percentage values must be between -100 and 1000")
        return v

    @field_validator("profit_factor", "cost_impact_ratio")
    @classmethod
    def validate_ratio(cls, v):
        if v < 0:
            raise ValueError("Ratio values must be non-negative")
        return v


class ValidationCriteria(BaseModel):
    """Criterios de validación de rentabilidad."""

    min_net_profit: Decimal = Field(default=Decimal("100"), description="Ganancia neta mínima")
    min_profit_margin: Decimal = Field(default=Decimal("5"), description="Margen mínimo (%)")
    min_roi: Decimal = Field(default=Decimal("10"), description="ROI mínimo (%)")
    min_sharpe_ratio: Decimal = Field(default=Decimal("1.0"), description="Sharpe ratio mínimo")
    max_drawdown_limit: Decimal = Field(default=Decimal("15"), description="Drawdown máximo (%)")
    min_win_rate: Decimal = Field(default=Decimal("50"), description="Tasa de ganancia mínima (%)")
    min_profit_factor: Decimal = Field(
        default=Decimal("1.5"), description="Factor de ganancia mínimo"
    )
    max_cost_impact_ratio: Decimal = Field(
        default=Decimal("0.3"), description="Ratio máximo de impacto de costos"
    )

    @field_validator("min_profit_margin", "min_roi", "max_drawdown_limit", "min_win_rate")
    @classmethod
    def validate_percentage(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Percentage values must be between 0 and 100")
        return v


class ProfitabilityValidation(BaseModel):
    """Resultado de la validación de rentabilidad."""

    strategy_name: str = Field(..., description="Nombre de la estrategia")
    validation_date: datetime = Field(
        default_factory=datetime.now, description="Fecha de validación"
    )
    period_start: date = Field(..., description="Inicio del período")
    period_end: date = Field(..., description="Fin del período")
    initial_capital: Decimal = Field(..., description="Capital inicial")
    final_capital: Decimal = Field(..., description="Capital final")

    # Métricas calculadas
    metrics: ProfitabilityMetrics = Field(..., description="Métricas de rentabilidad")
    cost_breakdown: CostBreakdown = Field(..., description="Desglose de costos")

    # Criterios de validación
    criteria: ValidationCriteria = Field(..., description="Criterios aplicados")

    # Resultado de la validación
    status: ValidationStatus = Field(..., description="Estado de la validación")
    passed_tests: List[str] = Field(default_factory=list, description="Tests que pasaron")
    failed_tests: List[str] = Field(default_factory=list, description="Tests que fallaron")
    warnings: List[str] = Field(default_factory=list, description="Advertencias")

    # Análisis adicional
    is_profitable: bool = Field(..., description="¿Es rentable la estrategia?")
    recommendation: str = Field(..., description="Recomendación basada en la validación")
    risk_level: str = Field(..., description="Nivel de riesgo (low, medium, high)")

    @field_validator("initial_capital", "final_capital")
    @classmethod
    def validate_positive_capital(cls, v):
        if v <= 0:
            raise ValueError("Capital amounts must be positive")
        return v


class ValidationRequest(BaseModel):
    """Request para validación de rentabilidad."""

    strategy_name: str = Field(..., description="Nombre de la estrategia")
    period_start: date = Field(..., description="Inicio del período")
    period_end: date = Field(..., description="Fin del período")
    initial_capital: Decimal = Field(..., description="Capital inicial")
    trades_data: List[Dict[str, Any]] = Field(..., description="Datos de trades")
    criteria: Optional[ValidationCriteria] = Field(None, description="Criterios personalizados")

    @field_validator("initial_capital")
    @classmethod
    def validate_positive_capital(cls, v):
        if v <= 0:
            raise ValueError("Initial capital must be positive")
        return v


class ValidationResponse(BaseModel):
    """Response de validación de rentabilidad."""

    validation: ProfitabilityValidation = Field(..., description="Resultado de la validación")
    summary: Dict[str, Any] = Field(..., description="Resumen de la validación")
    recommendations: List[str] = Field(..., description="Recomendaciones")
    next_steps: List[str] = Field(..., description="Próximos pasos")


class StrategyComparison(BaseModel):
    """Comparación entre múltiples estrategias."""

    comparison_date: datetime = Field(
        default_factory=datetime.now, description="Fecha de comparación"
    )
    strategies: List[ProfitabilityValidation] = Field(
        ..., description="Validaciones de estrategias"
    )
    best_strategy: str = Field(..., description="Mejor estrategia")
    worst_strategy: str = Field(..., description="Peor estrategia")
    average_metrics: ProfitabilityMetrics = Field(..., description="Métricas promedio")
    ranking: List[Dict[str, Any]] = Field(..., description="Ranking de estrategias")


class HistoricalValidation(BaseModel):
    """Validación histórica de una estrategia."""

    strategy_name: str = Field(..., description="Nombre de la estrategia")
    validations: List[ProfitabilityValidation] = Field(..., description="Validaciones históricas")
    trend_analysis: Dict[str, Any] = Field(..., description="Análisis de tendencias")
    stability_score: Decimal = Field(..., description="Score de estabilidad (0-100)")
    consistency_rating: str = Field(..., description="Rating de consistencia")


class ValidationReport(BaseModel):
    """Reporte completo de validación de rentabilidad."""

    report_date: datetime = Field(default_factory=datetime.now, description="Fecha del reporte")
    strategy_validations: List[ProfitabilityValidation] = Field(
        ..., description="Validaciones de estrategias"
    )
    strategy_comparison: Optional[StrategyComparison] = Field(
        None, description="Comparación de estrategias"
    )
    historical_analysis: Optional[HistoricalValidation] = Field(
        None, description="Análisis histórico"
    )
    overall_assessment: str = Field(..., description="Evaluación general")
    risk_assessment: str = Field(..., description="Evaluación de riesgo")
    recommendations: List[str] = Field(..., description="Recomendaciones generales")
