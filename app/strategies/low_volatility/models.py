"""
Data Models for Low Volatility Strategy

This module defines Pydantic models for low volatility investing including:
- Strategy configuration
- Volatility metrics and data
- Low volatility profiles
- Screening criteria
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SectorDefensiveLevel(str, Enum):
    """Nivel defensivo de un sector."""

    HIGHLY_DEFENSIVE = "highly_defensive"  # Utilities, Consumer Staples
    DEFENSIVE = "defensive"  # Healthcare, Real Estate
    NEUTRAL = "neutral"  # Finance, Industrials
    CYCLICAL = "cyclical"  # Technology, Consumer Discretionary
    HIGHLY_CYCLICAL = "highly_cyclical"  # Energy, Materials, Financials


class VolatilityRegime(str, Enum):
    """Régimen de volatilidad del mercado."""

    LOW = "low"  # VIX < 15
    NORMAL = "normal"  # VIX 15-25
    ELEVATED = "elevated"  # VIX 25-35
    HIGH = "high"  # VIX > 35


class VolatilityMetrics(BaseModel):
    """
    Métricas de volatilidad de una acción.

    Attributes:
        symbol: Símbolo de la acción
        historical_volatility_20d: Volatilidad histórica 20 días (% anualizado)
        historical_volatility_60d: Volatilidad histórica 60 días (% anualizado)
        historical_volatility_252d: Volatilidad histórica 252 días (% anualizado)
        beta: Beta respecto al mercado (SPY)
        downside_risk: Riesgo downside (semi-deviation)
        max_drawdown: Máximo drawdown histórico
        sortino_ratio: Sortino ratio
        sharpe_ratio: Sharpe ratio
        correlation_to_market: Correlación con el mercado
        idiosyncratic_volatility: Volatilidad idiosincrática
        skewness: Skewness de retornos
        kurtosis: Kurtosis de retornos
        volatility_regime: Régimen de volatilidad actual
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        use_enum_values=True,
    )

    symbol: str = Field(..., description="Símbolo de la acción")
    historical_volatility_20d: Optional[Decimal] = Field(
        None, ge=0, le=200, description="Volatilidad histórica 20 días (% anualizado)"
    )
    historical_volatility_60d: Optional[Decimal] = Field(
        None, ge=0, le=200, description="Volatilidad histórica 60 días (% anualizado)"
    )
    historical_volatility_252d: Optional[Decimal] = Field(
        None, ge=0, le=200, description="Volatilidad histórica 252 días (% anualizado)"
    )
    beta: Optional[Decimal] = Field(None, description="Beta respecto al mercado")
    downside_risk: Optional[Decimal] = Field(
        None, ge=0, description="Riesgo downside (semi-deviation %)"
    )
    max_drawdown: Optional[Decimal] = Field(
        None, ge=-100, le=0, description="Máximo drawdown histórico (%)"
    )
    sortino_ratio: Optional[Decimal] = Field(None, description="Sortino ratio")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    correlation_to_market: Optional[Decimal] = Field(
        None, ge=-1, le=1, description="Correlación con el mercado"
    )
    idiosyncratic_volatility: Optional[Decimal] = Field(
        None, ge=0, description="Volatilidad idiosincrática (%)"
    )
    skewness: Optional[Decimal] = Field(None, description="Skewness de retornos")
    kurtosis: Optional[Decimal] = Field(None, description="Kurtosis de retornos")
    volatility_regime: VolatilityRegime = Field(
        VolatilityRegime.NORMAL, description="Régimen de volatilidad actual"
    )

    @property
    def average_volatility(self) -> Optional[Decimal]:
        """Volatilidad promedio ponderada."""
        vols = [
            (self.historical_volatility_20d, Decimal("0.5")),
            (self.historical_volatility_60d, Decimal("0.3")),
            (self.historical_volatility_252d, Decimal("0.2")),
        ]
        valid_vols = [(v, w) for v, w in vols if v is not None]
        if not valid_vols:
            return None
        total_weight = sum(w for _, w in valid_vols)
        weighted_sum = sum(v * w for v, w in valid_vols)
        return weighted_sum / total_weight

    @property
    def is_low_volatility(self) -> bool:
        """
        Determinar si es una acción de baja volatilidad.

        Criterios:
        - Volatilidad promedio < 25%
        - Beta < 0.8
        - Max drawdown > -40%
        """
        avg_vol = self.average_volatility
        if avg_vol is None or avg_vol > 25:
            return False
        if self.beta is None or self.beta > 0.8:
            return False
        if self.max_drawdown is not None and self.max_drawdown < -40:
            return False
        return True

    @property
    def volatility_score(self) -> Decimal:
        """
        Calcular score de volatilidad (0-100, más alto = mejor).

        Menor volatilidad = mayor score.
        """
        avg_vol = self.average_volatility or Decimal("50")
        beta = self.beta or Decimal("1.0")

        # Score de volatilidad (invertido)
        vol_score = max(Decimal("0"), Decimal("100") - avg_vol * Decimal("2"))

        # Score de beta (invertido)
        beta_score = max(Decimal("0"), Decimal("100") - beta * Decimal("50"))

        # Promedio ponderado
        return (vol_score * Decimal("0.7") + beta_score * Decimal("0.3")).quantize(Decimal("0.01"))


class LowVolatilityProfile(BaseModel):
    """
    Perfil completo de baja volatilidad de una acción.

    Combina métricas de volatilidad con datos fundamentales.
    """

    model_config = ConfigDict(strict=True, validate_assignment=True, extra="forbid")

    symbol: str = Field(..., description="Símbolo de la acción")
    company_name: Optional[str] = Field(None, description="Nombre de la compañía")
    sector: Optional[str] = Field(None, description="Sector GICS")
    industry: Optional[str] = Field(None, description="Industria GICS")
    market_cap: Optional[Decimal] = Field(None, ge=0, description="Capitalización de mercado")
    current_price: Decimal = Field(..., gt=0, description="Precio actual de la acción")
    volatility_metrics: VolatilityMetrics = Field(..., description="Métricas de volatilidad")

    # Métricas de calidad calculadas
    low_vol_score: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Score de baja volatilidad (0-100)"
    )
    defensive_score: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Score defensivo (0-100)"
    )
    stability_score: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Score de estabilidad (0-100)"
    )

    # Métricas de valoración
    pe_ratio: Optional[Decimal] = Field(None, ge=0, description="P/E ratio (TTM)")
    pb_ratio: Optional[Decimal] = Field(None, ge=0, description="P/B ratio")
    debt_to_equity: Optional[Decimal] = Field(None, ge=0, description="Debt-to-Equity")
    roe: Optional[Decimal] = Field(None, ge=-100, le=100, description="Return on Equity (%)")

    # Sector defensivo
    sector_defensive_level: Optional[SectorDefensiveLevel] = Field(
        None, description="Nivel defensivo del sector"
    )

    @property
    def overall_score(self) -> Optional[Decimal]:
        """Score compuesto (promedio de scores)."""
        scores = [
            self.low_vol_score,
            self.defensive_score,
            self.stability_score,
        ]
        valid_scores = [s for s in scores if s is not None]
        if not valid_scores:
            return None
        return sum(valid_scores) / len(valid_scores)

    @property
    def is_defensive_stock(self) -> bool:
        """
        Determinar si es una acción defensiva.

        Criterios:
        - Sector defensivo o altamente defensivo
        - Beta < 0.8
        - Volatilidad < 25%
        """
        if self.sector_defensive_level in [
            SectorDefensiveLevel.DEFENSIVE,
            SectorDefensiveLevel.HIGHLY_DEFENSIVE,
        ]:
            return True
        if self.volatility_metrics.beta and self.volatility_metrics.beta < Decimal("0.8"):
            if (
                self.volatility_metrics.average_volatility
                and self.volatility_metrics.average_volatility < Decimal("25")
            ):
                return True
        return False


class LowVolatilityStock(BaseModel):
    """
    Acción de baja volatilidad con datos para toma de decisiones.

    Extiende LowVolatilityProfile con scores de decisión.
    """

    model_config = ConfigDict(strict=True, validate_assignment=True, extra="forbid")

    profile: LowVolatilityProfile = Field(..., description="Perfil completo de la acción")
    decision_score: Decimal = Field(..., ge=0, le=100, description="Score de decisión (0-100)")
    decision_reason: str = Field(..., description="Razón de la decisión")
    recommendation: str = Field(..., description="Recomendación: buy/hold/avoid")

    # Datos para backtesting
    data_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de los datos"
    )
    metrics_history: Optional[Dict[str, List[Decimal]]] = Field(
        None, description="Histórico de métricas"
    )


class LowVolatilityStrategyConfig(BaseModel):
    """
    Configuración de la estrategia de baja volatilidad.

    Define parámetros para screening, análisis y construcción de portafolio.
    """

    model_config = ConfigDict(
        strict=False,
        validate_assignment=True,
        extra="ignore",  # Ignorar campos extra como name, description, version
    )

    # Parámetros de screening de volatilidad
    max_historical_volatility: Decimal = Field(
        Decimal("25.0"), ge=0, le=100, description="Volatilidad histórica máxima (%)"
    )
    max_beta: Decimal = Field(Decimal("0.8"), ge=0, le=2, description="Beta máximo")
    min_beta: Optional[Decimal] = Field(
        None, ge=-1, le=1, description="Beta mínimo (None = sin límite)"
    )
    max_downside_risk: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Riesgo downside máximo (%)"
    )
    min_sortino_ratio: Optional[Decimal] = Field(
        None, ge=-10, le=10, description="Sortino ratio mínimo"
    )
    max_max_drawdown: Optional[Decimal] = Field(
        None, ge=-100, le=0, description="Máximo drawdown tolerado (%)"
    )

    # Sectores defensivos
    preferred_sectors: List[str] = Field(
        default_factory=lambda: ["Utilities", "Consumer Staples", "Healthcare"],
        description="Sectores defensivos preferidos",
    )
    avoid_sectors: List[str] = Field(
        default_factory=lambda: ["Technology", "Biotechnology", "Energy"],
        description="Sectores a evitar",
    )
    require_defensive_sector: bool = Field(False, description="Requerir sector defensivo")

    # Parámetros de portafolio
    portfolio_size: int = Field(
        30, ge=20, le=50, description="Número objetivo de acciones en el portafolio"
    )
    max_sector_weight: Decimal = Field(
        Decimal("0.35"), ge=0.05, le=1.0, description="Peso máximo por sector"
    )
    max_single_position: Decimal = Field(
        Decimal("0.06"), ge=0.01, le=0.5, description="Peso máximo por posición"
    )
    rebalance_threshold: Decimal = Field(
        Decimal("0.05"), ge=0.01, le=0.20, description="Umbral de rebalanceo"
    )

    # Parámetros de calidad
    min_low_vol_score: Decimal = Field(
        Decimal("60.0"), ge=0, le=100, description="Score mínimo de baja volatilidad"
    )
    min_defensive_score: Decimal = Field(
        Decimal("50.0"), ge=0, le=100, description="Score mínimo defensivo"
    )
    min_stability_score: Decimal = Field(
        Decimal("50.0"), ge=0, le=100, description="Score mínimo de estabilidad"
    )

    # Parámetros de valoración
    max_pe_ratio: Optional[Decimal] = Field(
        None, ge=0, description="P/E ratio máximo (None = sin límite)"
    )
    max_pb_ratio: Optional[Decimal] = Field(
        None, ge=0, description="P/B ratio máximo (None = sin límite)"
    )
    max_debt_to_equity: Optional[Decimal] = Field(None, ge=0, description="Debt-to-Equity máximo")

    # Parámetros de optimización
    optimization_method: str = Field(
        "min_variance",
        description="Método de optimización: min_variance, equal_weight, risk_parity",
    )
    target_volatility: Optional[Decimal] = Field(
        None, ge=5, le=30, description="Volatilidad objetivo del portafolio (%)"
    )
    use_sector_constraints: bool = Field(
        True, description="Usar restricciones sectoriales en optimización"
    )

    # Pesos de scoring
    volatility_weight: Decimal = Field(
        Decimal("0.40"), ge=0, le=1, description="Peso de volatilidad en scoring"
    )
    defensive_weight: Decimal = Field(
        Decimal("0.30"), ge=0, le=1, description="Peso de defensividad en scoring"
    )
    stability_weight: Decimal = Field(
        Decimal("0.20"), ge=0, le=1, description="Peso de estabilidad en scoring"
    )
    quality_weight: Decimal = Field(
        Decimal("0.10"), ge=0, le=1, description="Peso de calidad en scoring"
    )

    # Mínimos de capitalización y liquidez
    min_market_cap: Optional[Decimal] = Field(
        None, ge=0, description="Capitalización mínima (millones USD)"
    )
    min_daily_volume: Optional[Decimal] = Field(None, ge=0, description="Volumen diario mínimo")

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "LowVolatilityStrategyConfig":
        """Validar que los pesos sumen 1.0."""
        total = (
            self.volatility_weight
            + self.defensive_weight
            + self.stability_weight
            + self.quality_weight
        )
        if abs(total - Decimal("1.0")) > Decimal("0.01"):
            raise ValueError(f"Los pesos de scoring deben sumar 1.0, suman {total}")
        return self

    @model_validator(mode="after")
    def validate_volatility_range(self) -> "LowVolatilityStrategyConfig":
        """Validar rangos de volatilidad."""
        if self.max_historical_volatility < 10:
            raise ValueError("max_historical_volatility debe ser al menos 10%")
        if self.max_beta < 0.1:
            raise ValueError("max_beta debe ser al menos 0.1")
        return self

    def get_screening_description(self) -> str:
        """Obtener descripción legible de los criterios de screening."""
        return (
            f"Criterios de screening:\n"
            f"  - Volatilidad máxima: {self.max_historical_volatility}%\n"
            f"  - Beta máximo: {self.max_beta}\n"
            f"  - Sectores preferidos: {', '.join(self.preferred_sectors)}\n"
            f"  - Sectores evitados: {', '.join(self.avoid_sectors)}\n"
            f"  - Low Vol Score: ≥{self.min_low_vol_score}\n"
            f"  - Defensive Score: ≥{self.min_defensive_score}\n"
        )


@dataclass
class LowVolatilityScreeningCriteria:
    """Criterios de screening des-normalizados desde config."""

    max_volatility: Decimal
    max_beta: Decimal
    min_beta: Optional[Decimal]
    max_downside_risk: Optional[Decimal]
    min_sortino: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    min_low_vol_score: Decimal
    min_defensive_score: Decimal
    min_stability_score: Decimal
    preferred_sectors: List[str]
    avoid_sectors: List[str]
    require_defensive: bool
    min_market_cap: Optional[Decimal]


@dataclass
class ScreeningResult:
    """
    Resultado del screening de baja volatilidad.

    Attributes:
        passed_stocks: Lista de acciones que pasaron el screening
        failed_stocks: Dict con acciones que fallaron y razón
        total_evaluated: Total de acciones evaluadas
        screening_time: Tiempo que tomó el screening (ms)
        criteria: Criterios usados
    """

    passed_stocks: List[LowVolatilityStock]
    failed_stocks: Dict[str, List[str]]
    total_evaluated: int
    screening_time_ms: float
    criteria: LowVolatilityScreeningCriteria

    @property
    def pass_rate(self) -> float:
        """Tasa de aprobación (%)"""
        if self.total_evaluated == 0:
            return 0.0
        return (len(self.passed_stocks) / self.total_evaluated) * 100
