"""
Slippage Analysis Models
TASK-11: Análisis Dinámico de Slippage

Implementa cálculo dinámico de slippage basado en volatilidad del mercado y liquidez,
no solo 0.1% fijo.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class SlippageType(str, Enum):
    """Tipos de slippage calculados."""

    MARKET_IMPACT = "market_impact"
    TIMING_DELAY = "timing_delay"
    LIQUIDITY_COST = "liquidity_cost"
    VOLATILITY_ADJUSTMENT = "volatility_adjustment"
    TOTAL_SLIPPAGE = "total_slippage"


class MarketCondition(str, Enum):
    """Condiciones del mercado que afectan el slippage."""

    NORMAL = "normal"
    HIGH_VOLATILITY = "high_volatility"
    LOW_LIQUIDITY = "low_liquidity"
    MARKET_STRESS = "market_stress"
    EXTREME_EVENTS = "extreme_events"


class SlippageComponent(BaseModel):
    """Componente individual de slippage."""

    slippage_type: SlippageType
    value: Decimal = Field(..., ge=0, description="Valor del slippage en porcentaje")
    confidence: float = Field(..., ge=0, le=1, description="Confianza en el cálculo")
    market_condition: MarketCondition
    calculation_method: str
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator("value")
    @classmethod
    def validate_slippage_value(cls, v):
        """Validar que el slippage no exceda límites razonables."""
        if v > Decimal("10.0"):  # Máximo 10% de slippage
            raise ValueError("Slippage value cannot exceed 10%")
        return v


class VolatilityMetrics(BaseModel):
    """Métricas de volatilidad del mercado."""

    current_volatility: Decimal = Field(..., ge=0, description="Volatilidad actual")
    historical_volatility: Decimal = Field(..., ge=0, description="Volatilidad histórica")
    volatility_percentile: float = Field(..., ge=0, le=100, description="Percentil de volatilidad")
    volatility_trend: str = Field(..., description="Tendencia de volatilidad")
    volatility_regime: MarketCondition

    @field_validator("current_volatility", "historical_volatility")
    @classmethod
    def validate_volatility(cls, v):
        """Validar volatilidad razonable."""
        if v > Decimal("100.0"):  # Máximo 100% de volatilidad anual
            raise ValueError("Volatility cannot exceed 100%")
        return v


class LiquidityMetrics(BaseModel):
    """Métricas de liquidez del mercado."""

    bid_ask_spread: Decimal = Field(..., ge=0, description="Spread bid-ask")
    volume_24h: Decimal = Field(..., ge=0, description="Volumen 24h")
    order_book_depth: Decimal = Field(..., ge=0, description="Profundidad del order book")
    liquidity_score: float = Field(..., ge=0, le=1, description="Score de liquidez (0-1)")
    liquidity_regime: MarketCondition

    @field_validator("bid_ask_spread")
    @classmethod
    def validate_spread(cls, v):
        """Validar spread razonable."""
        if v > Decimal("50.0"):  # Máximo 50% de spread
            raise ValueError("Bid-ask spread cannot exceed 50%")
        return v


class OrderSizeImpact(BaseModel):
    """Impacto del tamaño de la orden en el slippage."""

    order_size: Decimal = Field(..., gt=0, description="Tamaño de la orden")
    market_cap_ratio: Decimal = Field(..., ge=0, le=1, description="Ratio orden/capitalización")
    impact_multiplier: float = Field(..., ge=1, description="Multiplicador de impacto")

    @field_validator("market_cap_ratio")
    @classmethod
    def validate_market_cap_ratio(cls, v):
        """Validar ratio razonable."""
        if v > Decimal("0.1"):  # Máximo 10% del market cap
            raise ValueError("Order size cannot exceed 10% of market cap")
        return v


class DynamicSlippageAnalysis(BaseModel):
    """Análisis completo de slippage dinámico."""

    asset_symbol: str
    base_price: Decimal = Field(..., gt=0, description="Precio base para el cálculo")
    order_side: str = Field(..., description="Lado de la orden (buy/sell)")
    order_size: Decimal = Field(..., gt=0, description="Tamaño de la orden")

    # Métricas de entrada
    volatility_metrics: VolatilityMetrics
    liquidity_metrics: LiquidityMetrics
    order_size_impact: OrderSizeImpact

    # Componentes de slippage
    slippage_components: List[SlippageComponent] = Field(default_factory=list)

    # Resultados
    total_slippage: Decimal = Field(..., ge=0, description="Slippage total calculado")
    slippage_confidence: float = Field(..., ge=0, le=1, description="Confianza en el cálculo")
    market_condition: MarketCondition
    calculation_timestamp: datetime = Field(default_factory=datetime.now)

    # Metadatos
    calculation_method: str = "dynamic_slippage_v1"
    model_version: str = "1.0.0"

    @field_validator("total_slippage")
    @classmethod
    def validate_total_slippage(cls, v):
        """Validar slippage total razonable."""
        if v > Decimal("15.0"):  # Máximo 15% de slippage total
            raise ValueError("Total slippage cannot exceed 15%")
        return v

    def get_slippage_by_type(self, slippage_type: SlippageType) -> Optional[SlippageComponent]:
        """Obtener componente de slippage por tipo."""
        for component in self.slippage_components:
            if component.slippage_type == slippage_type:
                return component
        return None

    def get_adjusted_price(self) -> Decimal:
        """Obtener precio ajustado por slippage."""
        if self.order_side.lower() == "buy":
            return self.base_price * (1 + self.total_slippage / Decimal("100"))
        else:  # sell
            return self.base_price * (1 - self.total_slippage / Decimal("100"))

    def get_slippage_cost(self) -> Decimal:
        """Obtener costo total del slippage."""
        return self.base_price * self.order_size * self.total_slippage / Decimal("100")


class SlippageCalculationParams(BaseModel):
    """Parámetros para el cálculo de slippage dinámico."""

    # Parámetros de volatilidad
    volatility_lookback_days: int = Field(default=30, ge=1, le=365)
    volatility_threshold_high: Decimal = Field(default=Decimal("30.0"), ge=0)
    volatility_threshold_extreme: Decimal = Field(default=Decimal("50.0"), ge=0)

    # Parámetros de liquidez
    min_liquidity_score: float = Field(default=0.3, ge=0, le=1)
    max_spread_threshold: Decimal = Field(default=Decimal("2.0"), ge=0)

    # Parámetros de tamaño de orden
    max_order_size_ratio: Decimal = Field(default=Decimal("0.05"), ge=0, le=1)
    impact_scaling_factor: float = Field(default=1.5, ge=1)

    # Parámetros de cálculo
    base_slippage: Decimal = Field(default=Decimal("0.1"), ge=0)
    volatility_multiplier: float = Field(default=2.0, ge=1)
    liquidity_multiplier: float = Field(default=1.5, ge=1)

    @field_validator("volatility_threshold_extreme")
    @classmethod
    def validate_extreme_threshold(cls, v, info):
        """Validar que el threshold extremo sea mayor que el alto."""
        if "volatility_threshold_high" in info.data:
            if v <= info.data["volatility_threshold_high"]:
                raise ValueError("Extreme threshold must be greater than high threshold")
        return v


class SlippageHistory(BaseModel):
    """Historial de análisis de slippage."""

    asset_symbol: str
    analyses: List[DynamicSlippageAnalysis] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_analysis(self, analysis: DynamicSlippageAnalysis):
        """Agregar nuevo análisis al historial."""
        self.analyses.append(analysis)
        self.updated_at = datetime.now()

    def get_latest_analysis(self) -> Optional[DynamicSlippageAnalysis]:
        """Obtener el análisis más reciente."""
        if not self.analyses:
            return None
        return max(self.analyses, key=lambda x: x.calculation_timestamp)

    def get_average_slippage(self, days: int = 7) -> Optional[Decimal]:
        """Obtener slippage promedio de los últimos N días."""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_analyses = [a for a in self.analyses if a.calculation_timestamp >= cutoff_date]

        if not recent_analyses:
            return None

        total_slippage = sum(a.total_slippage for a in recent_analyses)
        return total_slippage / len(recent_analyses)

    def get_slippage_trend(self) -> str:
        """Obtener tendencia del slippage."""
        if len(self.analyses) < 2:
            return "insufficient_data"

        recent = self.analyses[-1].total_slippage
        previous = self.analyses[-2].total_slippage

        if recent > previous * Decimal("1.1"):
            return "increasing"
        elif recent < previous * Decimal("0.9"):
            return "decreasing"
        else:
            return "stable"
