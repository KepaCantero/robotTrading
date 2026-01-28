"""
Data Models for Dividend Strategy

This module defines Pydantic models for dividend investing including:
- Strategy configuration
- Dividend data and metrics
- Dividend profiles
- Ex-dividend date tracking
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DividendFrequency(str, Enum):
    """Dividend payment frequency."""

    ANNUAL = "annual"
    SEMI_ANNUAL = "semi_annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    IRREGULAR = "irregular"
    UNKNOWN = "unknown"


class DividendSafety(str, Enum):
    """Dividend safety assessment."""

    VERY_SAFE = "very_safe"  # Payout ratio < 40%
    SAFE = "safe"  # Payout ratio 40-60%
    MODERATE = "moderate"  # Payout ratio 60-80%
    RISKY = "risky"  # Payout ratio 80-100%
    DANGEROUS = "dangerous"  # Payout ratio > 100% or negative FCF


class DividendAristocratStatus(str, Enum):
    """Dividend aristocrat status based on consecutive years of increases."""

    NOT_ARISTOCRAT = "not_aristocrat"
    ARISTOCRAT_5 = "aristocrat_5"  # 5+ years
    ARISTOCRAT_10 = "aristocrat_10"  # 10+ years
    ARISTOCRAT_25 = "aristocrat_25"  # 25+ years (S&P 500 Aristocrats)
    KING = "king"  # 50+ years (Dividend Kings)
    LEGENDARY = "legendary"  # 50+ years with exceptional growth


class DividendData(BaseModel):
    """
    Datos fundamentales de dividendos de una acción.

    Attributes:
        symbol: Símbolo de la acción
        annual_dividend: Dividendo anual por acción (USD)
        dividend_yield: Dividend yield actual (%)
        payout_ratio: Payout ratio (dividendos / earnings)
        dividend_growth_rate_3y: CAGR dividendos 3 años (%)
        dividend_growth_rate_5y: CAGR dividendos 5 años (%)
        dividend_growth_rate_10y: CAGR dividendos 10 años (%)
        years_consecutive_increases: Años consecutivos de incremento
        frequency: Frecuencia de pago
        next_ex_dividend_date: Próxima fecha ex-dividendo
        next_payment_date: Próxima fecha de pago
        last_announcement_date: Última fecha de anuncio
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        use_enum_values=True,
    )

    symbol: str = Field(..., description="Símbolo de la acción")
    annual_dividend: Decimal = Field(..., ge=0, description="Dividendo anual por acción (USD)")
    dividend_yield: Decimal = Field(..., ge=0, le=100, description="Dividend yield actual (%)")
    payout_ratio: Optional[Decimal] = Field(
        None, ge=0, le=200, description="Payout ratio (%) - None si earnings negativos"
    )
    dividend_growth_rate_3y: Optional[Decimal] = Field(
        None, description="CAGR dividendos 3 años (%)"
    )
    dividend_growth_rate_5y: Optional[Decimal] = Field(
        None, description="CAGR dividendos 5 años (%)"
    )
    dividend_growth_rate_10y: Optional[Decimal] = Field(
        None, description="CAGR dividendos 10 años (%)"
    )
    years_consecutive_increases: int = Field(
        0, ge=0, le=100, description="Años consecutivos de incremento"
    )
    frequency: DividendFrequency = Field(
        DividendFrequency.QUARTERLY, description="Frecuencia de pago"
    )
    next_ex_dividend_date: Optional[date] = Field(None, description="Próxima fecha ex-dividendo")
    next_payment_date: Optional[date] = Field(None, description="Próxima fecha de pago")
    last_announcement_date: Optional[date] = Field(None, description="Última fecha de anuncio")
    earnings_per_share: Optional[Decimal] = Field(None, description="EPS (TTM)")
    free_cash_flow_per_share: Optional[Decimal] = Field(None, description="FCF por acción (TTM)")
    dividend_coverage_ratio: Optional[Decimal] = Field(
        None, ge=0, description="Ratio cobertura (FCF / dividendos)"
    )

    @field_validator("dividend_yield")
    @classmethod
    def validate_yield(cls, v: Decimal) -> Decimal:
        """Validar que el yield sea razonable."""
        if v > 20:  # Más de 20% es probablemente un dividend trap
            raise ValueError(f"Dividend yield sospechosamente alto ({v}%). Posible dividend trap.")
        return v

    @property
    def safety(self) -> DividendSafety:
        """
        Evaluar la seguridad del dividendo basado en payout ratio.

        Returns:
            Nivel de seguridad del dividendo
        """
        if self.payout_ratio is None:
            # Si no hay payout ratio, evaluar por dividend coverage ratio
            if self.dividend_coverage_ratio is None:
                return DividendSafety.MODERATE
            if self.dividend_coverage_ratio >= 2.0:
                return DividendSafety.VERY_SAFE
            elif self.dividend_coverage_ratio >= 1.5:
                return DividendSafe.SAFE
            elif self.dividend_coverage_ratio >= 1.0:
                return DividendSafety.MODERATE
            else:
                return DividendSafety.DANGEROUS

        # Evaluar por payout ratio
        if self.payout_ratio < 40:
            return DividendSafety.VERY_SAFE
        elif self.payout_ratio < 60:
            return DividendSafety.SAFE
        elif self.payout_ratio < 80:
            return DividendSafety.MODERATE
        elif self.payout_ratio <= 100:
            return DividendSafety.RISKY
        else:
            return DividendSafety.DANGEROUS

    @property
    def aristocrat_status(self) -> DividendAristocratStatus:
        """
        Determinar el estatus de aristócrata de dividendos.

        Returns:
            Estatus de aristócrata basado en años consecutivos
        """
        if self.years_consecutive_increases >= 50:
            return DividendAristocratStatus.LEGENDARY
        elif self.years_consecutive_increases >= 50:
            return DividendAristocratStatus.KING
        elif self.years_consecutive_increases >= 25:
            return DividendAristocratStatus.ARISTOCRAT_25
        elif self.years_consecutive_increases >= 10:
            return DividendAristocratStatus.ARISTOCRAT_10
        elif self.years_consecutive_increases >= 5:
            return DividendAristocratStatus.ARISTOCRAT_5
        else:
            return DividendAristocratStatus.NOT_ARISTOCRAT

    @property
    def monthly_dividend_estimate(self) -> Decimal:
        """Estimación de dividendo mensual."""
        annual = self.annual_dividend
        if self.frequency == DividendFrequency.MONTHLY:
            return annual / 12
        elif self.frequency == DividendFrequency.QUARTERLY:
            return annual / 4
        elif self.frequency == DividendFrequency.SEMI_ANNUAL:
            return annual / 2
        else:  # ANNUAL o UNKNOWN
            return annual


class ExDividendDate(BaseModel):
    """
    Información de fecha ex-dividendo.

    Attributes:
        symbol: Símbolo de la acción
        ex_dividend_date: Fecha ex-dividendo
        record_date: Fecha de registro
        payment_date: Fecha de pago
        amount: Monto del dividendo por acción
        frequency: Frecuencia del dividendo
    """

    model_config = ConfigDict(strict=True, validate_assignment=True, extra="forbid")

    symbol: str = Field(..., description="Símbolo de la acción")
    ex_dividend_date: date = Field(..., description="Fecha ex-dividendo")
    record_date: Optional[date] = Field(None, description="Fecha de registro")
    payment_date: Optional[date] = Field(None, description="Fecha de pago")
    amount: Decimal = Field(..., gt=0, description="Monto del dividendo por acción")
    frequency: DividendFrequency = Field(
        DividendFrequency.QUARTERLY, description="Frecuencia del dividendo"
    )

    @property
    def days_until_ex_dividend(self, today: Optional[date] = None) -> int:
        """
        Calcular días hasta la fecha ex-dividendo.

        Args:
            today: Fecha de referencia (default: hoy)

        Returns:
            Días hasta ex-dividendo (negativo si ya pasó)
        """
        if today is None:
            today = date.today()
        return (self.ex_dividend_date - today).days


class DividendProfile(BaseModel):
    """
    Perfil completo de dividendos de una acción.

    Combina datos actuales con histórico y análisis.
    """

    model_config = ConfigDict(strict=True, validate_assignment=True, extra="forbid")

    symbol: str = Field(..., description="Símbolo de la acción")
    company_name: Optional[str] = Field(None, description="Nombre de la compañía")
    sector: Optional[str] = Field(None, description="Sector GICS")
    industry: Optional[str] = Field(None, description="Industria GICS")
    market_cap: Optional[Decimal] = Field(None, ge=0, description="Capitalización de mercado")
    current_price: Decimal = Field(..., gt=0, description="Precio actual de la acción")
    dividend_data: DividendData = Field(..., description="Datos de dividendos")

    # Métricas de calidad calculadas
    quality_score: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Score de calidad (0-100)"
    )
    sustainability_score: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Score de sostenibilidad (0-100)"
    )
    value_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Score de valor (0-100)")

    # Métricas de valoración
    pe_ratio: Optional[Decimal] = Field(None, ge=0, description="P/E ratio (TTM)")
    pb_ratio: Optional[Decimal] = Field(None, ge=0, description="P/B ratio")
    debt_to_equity: Optional[Decimal] = Field(None, ge=0, description="Debt-to-Equity")
    roe: Optional[Decimal] = Field(None, ge=-100, le=100, description="Return on Equity (%)")

    # Riesgo
    beta: Optional[Decimal] = Field(None, description="Beta (volatilidad relativa al mercado)")
    standard_deviation_1y: Optional[Decimal] = Field(
        None, ge=0, description="Desviación estándar 1 año"
    )

    @property
    def is_dividend_trap(self) -> bool:
        """
        Detectar si es un dividend trap potencial.

        Un dividend trap ocurre cuando:
        - Yield muy alto (>8-10%)
        - Payout ratio > 100%
        - Dividendos decreciendo
        - Problemas fundamentales

        Returns:
            True si parece un dividend trap
        """
        # Yield sospechosamente alto
        if self.dividend_data.dividend_yield > 10:
            return True

        # Payout ratio peligroso
        if self.dividend_data.payout_ratio is not None and self.dividend_data.payout_ratio > 100:
            return True

        # Dividend coverage ratio bajo
        if (
            self.dividend_data.dividend_coverage_ratio is not None
            and self.dividend_data.dividend_coverage_ratio < 1.0
        ):
            return True

        # Dividend growth negativo reciente
        if self.dividend_data.dividend_growth_rate_3y is not None:
            if self.dividend_data.dividend_growth_rate_3y < 0:
                return True

        return False

    @property
    def overall_score(self) -> Optional[Decimal]:
        """Score compuesto (promedio de calidad, sostenibilidad y valor)."""
        scores = [
            self.quality_score,
            self.sustainability_score,
            self.value_score,
        ]
        valid_scores = [s for s in scores if s is not None]
        if not valid_scores:
            return None
        return sum(valid_scores) / len(valid_scores)


class DividendStock(BaseModel):
    """
    Acción de dividendos con datos para toma de decisiones.

    Extiende DividendProfile con scores de decisión.
    """

    model_config = ConfigDict(strict=True, validate_assignment=True, extra="forbid")

    profile: DividendProfile = Field(..., description="Perfil completo de la acción")
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


class DividendStrategyConfig(BaseModel):
    """
    Configuración de la estrategia de dividendos.

    Define parámetros para screening, análisis y construcción de portafolio.
    """

    model_config = ConfigDict(
        strict=False,
        validate_assignment=True,
        extra="ignore",  # Ignorar campos extra como name, description, version
    )

    # Parámetros de screening
    min_dividend_yield: Decimal = Field(Decimal("3.0"), ge=0, le=20, description="Yield mínimo (%)")
    max_dividend_yield: Decimal = Field(
        Decimal("15.0"), ge=0, le=50, description="Yield máximo (para evitar traps)"
    )
    max_payout_ratio: Decimal = Field(
        Decimal("70.0"), ge=0, le=150, description="Payout ratio máximo (%)"
    )
    min_dividend_growth: Optional[Decimal] = Field(
        None, ge=-50, le=100, description="Crecimiento mínimo de dividendos (%/año)"
    )
    min_years_consecutive: int = Field(
        3, ge=0, le=50, description="Mínimos años de incrementos consecutivos"
    )
    min_market_cap: Optional[Decimal] = Field(
        None, ge=0, description="Capitalización mínima (millones USD)"
    )
    min_daily_volume: Optional[Decimal] = Field(None, ge=0, description="Volumen diario mínimo")

    # Sectores a excluir
    excluded_sectors: List[str] = Field(
        default_factory=lambda: ["Utilities", "Real Estate"],
        description="Sectores a excluir (opcional)",
    )

    # Parámetros de portafolio
    portfolio_size: int = Field(
        25, ge=10, le=50, description="Número objetivo de acciones en el portafolio"
    )
    max_sector_weight: Decimal = Field(
        Decimal("0.30"), ge=0.05, le=1.0, description="Peso máximo por sector"
    )
    max_single_position: Decimal = Field(
        Decimal("0.05"), ge=0.01, le=0.5, description="Peso máximo por posición"
    )
    rebalance_threshold: Decimal = Field(
        Decimal("0.05"), ge=0.01, le=0.20, description="Umbral de rebalanceo"
    )

    # Parámetros de calidad
    min_quality_score: Decimal = Field(
        Decimal("50.0"), ge=0, le=100, description="Score mínimo de calidad"
    )
    min_sustainability_score: Decimal = Field(
        Decimal("50.0"), ge=0, le=100, description="Score mínimo de sostenibilidad"
    )
    require_profitable: bool = Field(True, description="Requerir earnings positivos (EPS > 0)")
    require_positive_fcf: bool = Field(True, description="Requerir FCF positivo")

    # Parámetros de valoración
    max_pe_ratio: Optional[Decimal] = Field(
        None, ge=0, description="P/E ratio máximo (None = sin límite)"
    )
    max_pb_ratio: Optional[Decimal] = Field(
        None, ge=0, description="P/B ratio máximo (None = sin límite)"
    )

    # Parámetros de riesgo
    max_beta: Optional[Decimal] = Field(None, ge=0, description="Beta máximo (None = sin límite)")
    min_dividend_safety: DividendSafety = Field(
        DividendSafety.MODERATE, description="Nivel mínimo de seguridad de dividendo"
    )

    # Pesos de scoring
    yield_weight: Decimal = Field(
        Decimal("0.30"), ge=0, le=1, description="Peso de yield en scoring"
    )
    growth_weight: Decimal = Field(
        Decimal("0.25"), ge=0, le=1, description="Peso de crecimiento en scoring"
    )
    sustainability_weight: Decimal = Field(
        Decimal("0.25"), ge=0, le=1, description="Peso de sostenibilidad en scoring"
    )
    value_weight: Decimal = Field(
        Decimal("0.20"), ge=0, le=1, description="Peso de valor en scoring"
    )

    # Captura de dividendos
    enable_dividend_capture: bool = Field(
        False, description="Habilitar estrategia de captura de dividendos"
    )
    min_days_before_ex_dividend: int = Field(
        7, ge=1, le=30, description="Días mínimos antes de ex-dividendo para comprar"
    )
    max_days_after_ex_dividend: int = Field(
        1, ge=0, le=10, description="Días máximos después de ex-dividendo para vender"
    )

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "DividendStrategyConfig":
        """Validar que los pesos sumen 1.0."""
        total = (
            self.yield_weight + self.growth_weight + self.sustainability_weight + self.value_weight
        )
        if abs(total - Decimal("1.0")) > Decimal("0.01"):
            raise ValueError(f"Los pesos de scoring deben sumar 1.0, suman {total}")
        return self

    @model_validator(mode="after")
    def validate_yield_range(self) -> "DividendStrategyConfig":
        """Validar que min_yield < max_yield."""
        if self.min_dividend_yield >= self.max_dividend_yield:
            raise ValueError("min_dividend_yield debe ser menor que max_dividend_yield")
        return self

    def get_screening_description(self) -> str:
        """Obtener descripción legible de los criterios de screening."""
        return (
            f"Criterios de screening:\n"
            f"  - Yield: {self.min_dividend_yield}% - {self.max_dividend_yield}%\n"
            f"  - Payout ratio: ≤{self.max_payout_ratio}%\n"
            f"  - Crecimiento: ≥{self.min_dividend_growth or 0}%/año\n"
            f"  - Años consecutivos: ≥{self.min_years_consecutive}\n"
            f"  - Market cap: ≥{self.min_market_cap or 'Sin límite'}M\n"
            f"  - Quality score: ≥{self.min_quality_score}\n"
            f"  - Sustainability: ≥{self.min_sustainability_score}\n"
        )


@dataclass
class DividendScreeningCriteria:
    """Criterios de screening des-normalizados desde config."""

    min_yield: Decimal
    max_yield: Decimal
    max_payout: Decimal
    min_growth: Optional[Decimal]
    min_years: int
    min_market_cap: Optional[Decimal]
    min_quality: Decimal
    min_sustainability: Decimal
    require_profitable: bool
    require_positive_fcf: bool
    min_safety: DividendSafety
    excluded_sectors: List[str]


@dataclass
class ScreeningResult:
    """
    Resultado del screening de dividendos.

    Attributes:
        passed_stocks: Lista de acciones que pasaron el screening
        failed_stocks: Dict con acciones que fallaron y razón
        total_evaluated: Total de acciones evaluadas
        screening_time: Tiempo que tomó el screening (ms)
        criteria: Criterios usados
    """

    passed_stocks: List[DividendStock]
    failed_stocks: Dict[str, List[str]]
    total_evaluated: int
    screening_time_ms: float
    criteria: DividendScreeningCriteria

    @property
    def pass_rate(self) -> float:
        """Tasa de aprobación (%)"""
        if self.total_evaluated == 0:
            return 0.0
        return (len(self.passed_stocks) / self.total_evaluated) * 100
