"""
Data Models for Covered Calls Strategy

This module defines Pydantic models for covered call options trading including:
- Strategy configuration
- Call option data
- Covered call positions
- Greeks and pricing
- Roll opportunities
- Screening criteria and results
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OptionType(str, Enum):
    """Type of option."""

    CALL = "call"
    PUT = "put"


class OptionStyle(str, Enum):
    """Option exercise style."""

    AMERICAN = "american"
    EUROPEAN = "european"


class Moneyness(str, Enum):
    """Moneyness of an option."""

    DEEP_ITM = "deep_itm"  # Strike << Spot (for calls)
    ITM = "itm"  # Strike < Spot (for calls)
    ATM = "atm"  # Strike ≈ Spot
    OTM = "otm"  # Strike > Spot (for calls)
    DEEP_OTM = "deep_otm"  # Strike >> Spot (for calls)


class RollType(str, Enum):
    """Type of roll operation."""

    ROLL_UP_AND_OUT = "roll_up_and_out"  # Higher strike, later expiry (stock rallied)
    ROLL_DOWN_AND_OUT = "roll_down_and_out"  # Lower strike, later expiry (stock declined)
    ROLL_OUT = "roll_out"  # Same strike, later expiry (time decay management)
    CLOSE_AND_REOPEN = "close_and_reopen"  # Close existing, open new position


class AssignmentProbability(str, Enum):
    """Probability of assignment."""

    VERY_LOW = "very_low"  # < 10%
    LOW = "low"  # 10-30%
    MODERATE = "moderate"  # 30-60%
    HIGH = "high"  # 60-80%
    VERY_HIGH = "very_high"  # > 80%


class CallOption(BaseModel):
    """
    Datos de una opción de compra (call).

    Attributes:
        symbol: Símbolo del activo subyacente
        option_symbol: Símbolo de la opción (ej. AAPL240120C00150000)
        strike: Precio de ejercicio
        expiry_date: Fecha de vencimiento
        option_type: Tipo de opción (CALL/PUT)
        style: Estilo de ejercicio (American/European)
        bid: Precio de oferta
        ask: Precio de demanda
        last_price: Último precio negociado
        implied_volatility: Volatilidad implícita (%)
        volume: Volumen negociado
        open_interest: Interés abierto
        greeks: Greeks de la opción
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        use_enum_values=True,
    )

    symbol: str = Field(..., description="Símbolo del activo subyacente")
    option_symbol: Optional[str] = Field(None, description="Símbolo de la opción")
    strike: Decimal = Field(..., gt=0, description="Precio de ejercicio")
    expiry_date: date = Field(..., description="Fecha de vencimiento")
    option_type: OptionType = Field(OptionType.CALL, description="Tipo de opción")
    style: OptionStyle = Field(OptionStyle.AMERICAN, description="Estilo de ejercicio")
    bid: Optional[Decimal] = Field(None, ge=0, description="Precio de oferta")
    ask: Optional[Decimal] = Field(None, ge=0, description="Precio de demanda")
    last_price: Optional[Decimal] = Field(None, ge=0, description="Último precio negociado")
    implied_volatility: Optional[Decimal] = Field(
        None, ge=0, le=500, description="Volatilidad implícita (%)"
    )
    volume: Optional[int] = Field(None, ge=0, description="Volumen negociado")
    open_interest: Optional[int] = Field(None, ge=0, description="Interés abierto")
    underlying_price: Optional[Decimal] = Field(
        None, gt=0, description="Precio del activo subyacente"
    )

    @property
    def mid_price(self) -> Optional[Decimal]:
        """Precio medio (bid + ask) / 2."""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return self.last_price

    @property
    def days_to_expiry(self) -> int:
        """Días hasta el vencimiento."""
        return (self.expiry_date - date.today()).days

    @property
    def is_itm(self) -> bool:
        """Verificar si la opción está in-the-money."""
        if self.underlying_price is None:
            return False
        return self.underlying_price > self.strike

    @property
    def is_otm(self) -> bool:
        """Verificar si la opción está out-of-the-money."""
        if self.underlying_price is None:
            return True
        return self.underlying_price < self.strike

    @property
    def intrinsic_value(self) -> Decimal:
        """Valor intrínseco de la opción."""
        if self.underlying_price is None:
            return Decimal("0")
        return max(Decimal("0"), self.underlying_price - self.strike)

    @property
    def time_value(self) -> Optional[Decimal]:
        """Valor tiempo de la opción."""
        mid = self.mid_price
        if mid is None:
            return None
        return max(Decimal("0"), mid - self.intrinsic_value)

    @property
    def moneyness(self) -> Moneyness:
        """
        Determinar el moneyness de la opción.

        Returns:
            Moneyness basado en la relación strike/underlying
        """
        if self.underlying_price is None:
            return Moneyness.OTM

        ratio = float(self.strike / self.underlying_price)

        if ratio < 0.90:
            return Moneyness.DEEP_ITM
        elif ratio < 0.98:
            return Moneyness.ITM
        elif ratio <= 1.02:
            return Moneyness.ATM
        elif ratio <= 1.10:
            return Moneyness.OTM
        else:
            return Moneyness.DEEP_OTM


@dataclass
class OptionGreeks:
    """
    Greeks de una opción.

    Attributes:
        delta: Sensibilidad del precio de la opción al precio del subyacente
        gamma: Sensibilidad de delta al precio del subyacente
        theta: Sensibilidad del precio de la opción al paso del tiempo
        vega: Sensibilidad del precio de la opción a la volatilidad
        rho: Sensibilidad del precio de la opción a la tasa de interés
    """

    delta: Decimal  # -1 to 1 for calls
    gamma: Decimal  # 0 to infinity
    theta: Decimal  # Negative for long options
    vega: Decimal  # Positive for all options
    rho: Optional[Decimal] = None  # Usually small

    def __post_init__(self):
        """Validar que los Greeks estén en rangos razonables."""
        if not -1 <= self.delta <= 1:
            raise ValueError(f"Delta debe estar entre -1 y 1: {self.delta}")
        if self.gamma < 0:
            raise ValueError(f"Gamma debe ser no-negativo: {self.gamma}")


class CoveredCallPosition(BaseModel):
    """
    Posición de covered call.

    Una posición de covered call consiste en:
    - Posición larga en el activo subyacente
    - Posición corta en una opción de compra (call)

    Attributes:
        symbol: Símbolo del activo subyacente
        shares_owned: Número de acciones poseídas
        average_cost: Costo promedio por acción
        call_option: Opción de compra vendida
        contracts_sold: Número de contratos vendidos (cada contrato = 100 acciones)
        premium_received: Prima recibida por la opción (neta de comisiones)
        open_date: Fecha de apertura de la posición
        status: Estado de la posición
        assignment_probability: Probabilidad de assignment
        expected_return: Retorno esperado si se mantiene hasta vencimiento
    """

    model_config = ConfigDict(strict=True, validate_assignment=True, extra="forbid")

    symbol: str = Field(..., description="Símbolo del activo subyacente")
    shares_owned: int = Field(..., gt=0, description="Número de acciones poseídas")
    average_cost: Decimal = Field(..., gt=0, description="Costo promedio por acción")
    call_option: CallOption = Field(..., description="Opción de compra vendida")
    contracts_sold: int = Field(..., gt=0, description="Número de contratos vendidos")
    premium_received: Decimal = Field(..., ge=0, description="Prima recibida por la opción")
    open_date: date = Field(default_factory=date.today, description="Fecha de apertura")
    current_price: Optional[Decimal] = Field(None, gt=0, description="Precio actual del subyacente")
    current_option_price: Optional[Decimal] = Field(
        None, ge=0, description="Precio actual de la opción"
    )
    assignment_probability: AssignmentProbability = Field(
        AssignmentProbability.MODERATE, description="Probabilidad de assignment"
    )
    expected_return: Optional[Decimal] = Field(None, description="Retorno esperado (%)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")

    @field_validator("contracts_sold")
    @classmethod
    def validate_contracts(cls, v: int, info) -> int:
        """Validar que los contratos no cubran más acciones de las poseídas."""
        shares_owned = info.data.get("shares_owned", 0)
        max_contracts = shares_owned // 100
        if v > max_contracts:
            raise ValueError(
                f"Contratos ({v}) exceden acciones disponibles ({shares_owned}). "
                f"Máximo: {max_contracts}"
            )
        return v

    @property
    def covered_shares(self) -> int:
        """Número de acciones cubiertas por la opción."""
        return self.contracts_sold * 100

    @property
    def uncovered_shares(self) -> int:
        """Número de acciones no cubiertas."""
        return self.shares_owned - self.covered_shares

    @property
    def total_cost(self) -> Decimal:
        """Costo total de la posición larga."""
        return self.average_cost * self.shares_owned

    @property
    def total_value(self) -> Optional[Decimal]:
        """Valor actual de la posición larga."""
        if self.current_price is None:
            return None
        return self.current_price * self.shares_owned

    @property
    def total_premium(self) -> Decimal:
        """Prima total recibida."""
        return self.premium_received * self.contracts_sold * 100

    @property
    def net_cost(self) -> Decimal:
        """Costo neto después de la prima."""
        return self.total_cost - self.total_premium

    @property
    def break_even_price(self) -> Decimal:
        """Precio de equilibrio (break-even)."""
        return self.average_cost - (self.total_premium / self.shares_owned)

    @property
    def max_profit(self) -> Optional[Decimal]:
        """
        Ganancia máxima si la opción se ejerce.

        Max profit = (strike - avg_cost) * shares + premium
        """
        return (
            self.call_option.strike - self.average_cost
        ) * self.shares_owned + self.total_premium

    @property
    def max_loss(self) -> Optional[Decimal]:
        """
        Pérdida máxima si el precio cae a 0.

        Max loss = net_cost
        """
        return self.net_cost

    @property
    def return_if_called(self) -> Optional[Decimal]:
        """
        Retorno si la opción se ejerce.

        Return if called = (strike - avg_cost + premium) / avg_cost
        """
        profit_per_share = (
            self.call_option.strike - self.average_cost + (self.total_premium / self.shares_owned)
        )
        return (profit_per_share / self.average_cost) * 100

    @property
    def return_if_unchanged(self) -> Optional[Decimal]:
        """
        Retorno si el precio permanece igual.

        Return if unchanged = premium / avg_cost
        """
        return (self.total_premium / self.total_cost) * 100

    @property
    def downside_protection(self) -> Optional[Decimal]:
        """
        Protección a la baja desde la prima.

        Downside protection = premium / avg_cost (%)
        """
        return (self.total_premium / self.total_cost) * 100

    @property
    def annualized_return(self) -> Optional[Decimal]:
        """
        Retorno anualizado.

        Annualized return = return_if_unchanged * (365 / days_to_expiry)
        """
        days = self.call_option.days_to_expiry
        if days == 0:
            return None
        return self.return_if_unchanged * (Decimal("365") / Decimal(str(days)))

    @property
    def time_decay_benefit(self) -> Optional[Decimal]:
        """
        Beneficio del decaimiento temporal (theta positivo).

        Para el vendedor de opciones, theta positivo genera ganancia.
        """
        if self.current_option_price is None:
            return None
        # Estimado: theta * contracts * 100 * (-1) para vendedor
        # Esto requeriría los Greeks del option
        return None  # Se calcula con GreeksCalculator


class RollOpportunity(BaseModel):
    """
    Oportunidad de rolling (cerrar y abrir nueva posición).

    Attributes:
        position: Posición actual
        new_option: Nueva opción a abrir
        roll_type: Tipo de roll
        additional_premium: Prima adicional (o menor) a recibir/pagar
        days_to_expiry_new: Días al vencimiento de la nueva opción
        reason: Razón del roll
        expected_benefit: Beneficio esperado del roll
        probability_delta: Cambio en probabilidad de assignment
    """

    model_config = ConfigDict(strict=True, validate_assignment=True, extra="forbid")

    position: CoveredCallPosition = Field(..., description="Posición actual")
    new_option: CallOption = Field(..., description="Nueva opción a abrir")
    roll_type: RollType = Field(..., description="Tipo de roll")
    additional_premium: Decimal = Field(..., description="Prima adicional (positiva = recibir más)")
    days_to_expiry_new: int = Field(..., ge=0, description="Días al vencimiento nueva opción")
    reason: str = Field(..., description="Razón del roll")
    expected_benefit: str = Field(..., description="Beneficio esperado")
    probability_delta: Optional[str] = Field(
        None, description="Cambio en probabilidad de assignment"
    )


class OptionScreeningCriteria(BaseModel):
    """
    Criterios de screening para opciones.

    Attributes:
        min_days_to_expiry: Días mínimos al vencimiento
        max_days_to_expiry: Días máximos al vencimiento
        min_moneyness: Moneyness mínimo (OTM distance %)
        max_moneyness: Moneyness máximo
        min_premium: Prima mínima (% del precio del subyacente)
        min_open_interest: Interés abierto mínimo
        min_volume: Volumen mínimo
        min_iv_rank: Rango de IV mínimo
        max_iv_rank: Rango de IV máximo
        exclude_earnings: Excluir periodos de earnings
        target_delta: Delta objetivo (0.3-0.5 típico)
        target_theta: Theta objetivo (decadimiento temporal)
    """

    model_config = ConfigDict(strict=True, validate_assignment=True, extra="forbid")

    min_days_to_expiry: int = Field(7, ge=1, description="Días mínimos al vencimiento")
    max_days_to_expiry: int = Field(60, ge=7, description="Días máximos al vencimiento")
    min_moneyness: Decimal = Field(Decimal("0.02"), ge=0, description="Moneyness mínimo (2% OTM)")
    max_moneyness: Decimal = Field(Decimal("0.10"), ge=0, description="Moneyness máximo (10% OTM)")
    min_premium: Decimal = Field(Decimal("0.01"), ge=0, description="Prima mínima (% del precio)")
    min_open_interest: int = Field(10, ge=0, description="Interés abierto mínimo")
    min_volume: int = Field(0, ge=0, description="Volumen mínimo")
    min_iv_rank: Optional[Decimal] = Field(None, ge=0, le=100, description="Rango de IV mínimo")
    max_iv_rank: Optional[Decimal] = Field(None, ge=0, le=100, description="Rango de IV máximo")
    exclude_earnings: bool = Field(True, description="Excluir periodos de earnings")
    target_delta: Optional[Decimal] = Field(
        None, ge=0, le=1, description="Delta objetivo (0.3-0.5)"
    )
    target_theta: Optional[Decimal] = Field(None, description="Theta objetivo (decadimiento)")

    @model_validator(mode="after")
    def validate_ranges(self) -> "OptionScreeningCriteria":
        """Validar que min < max."""
        if self.min_moneyness >= self.max_moneyness:
            raise ValueError("min_moneyness debe ser menor que max_moneyness")
        if self.min_days_to_expiry >= self.max_days_to_expiry:
            raise ValueError("min_days_to_expiry debe ser menor que max_days_to_expiry")
        if self.min_iv_rank is not None and self.max_iv_rank is not None:
            if self.min_iv_rank >= self.max_iv_rank:
                raise ValueError("min_iv_rank debe ser menor que max_iv_rank")
        return self


@dataclass
class OptionScreenerResult:
    """
    Resultado del screening de opciones.

    Attributes:
        symbol: Símbolo del subyacente
        underlying_price: Precio del subyacente
        options_passed: Lista de opciones que pasaron el screening
        options_failed: Dict con opciones que fallaron y razón
        total_evaluated: Total de opciones evaluadas
        screening_time_ms: Tiempo de screening (ms)
        criteria: Criterios usados
    """

    symbol: str
    underlying_price: Decimal
    options_passed: List[CallOption]
    options_failed: Dict[str, List[str]]
    total_evaluated: int
    screening_time_ms: float
    criteria: OptionScreeningCriteria

    @property
    def pass_rate(self) -> float:
        """Tasa de aprobación (%)."""
        if self.total_evaluated == 0:
            return 0.0
        return (len(self.options_passed) / self.total_evaluated) * 100


class CoveredCallConfig(BaseModel):
    """
    Configuración de la estrategia de covered calls.

    Attributes:
        max_position_size: Tamaño máximo de posición (% del portfolio)
        max_contracts_per_position: Contratos máximo por posición
        min_shares_required: Acciones mínimas requeridas
        target_dte: Días objetivo al vencimiento
        target_otm_pct: Porcentaje objetivo OTM
        min_premium_pct: Prima mínima (% del precio)
        roll_threshold_days: Días antes del vencimiento para considerar roll
        roll_threshold_itm: % ITM para considerar roll up
        roll_threshold_otm: % OTM para considerar roll down
        assignment_probability_threshold: Umbral de probabilidad de assignment
        auto_roll: Habilitar rolling automático
        avoid_earnings: Evitar periodos de earnings
        max_iv_percentile: Percentil máximo de IV
        min_liquidity_rank: Rango mínimo de liquidez
    """

    model_config = ConfigDict(
        strict=False,
        validate_assignment=True,
        extra="ignore",
    )

    # Gestión de posición
    max_position_size: Decimal = Field(
        Decimal("0.10"), ge=0.01, le=1.0, description="Tamaño máximo de posición (% del portfolio)"
    )
    max_contracts_per_position: int = Field(
        10, ge=1, le=100, description="Contratos máximo por posición"
    )
    min_shares_required: int = Field(
        100, ge=100, description="Acciones mínimas requeridas (múltiplo de 100)"
    )

    # Parámetros de selección de opciones
    target_dte: int = Field(30, ge=7, le=90, description="Días objetivo al vencimiento")
    target_otm_pct: Decimal = Field(
        Decimal("0.03"), ge=0, le=0.20, description="Porcentaje objetivo OTM (3%)"
    )
    min_premium_pct: Decimal = Field(
        Decimal("0.01"), ge=0, le=0.10, description="Prima mínima (% del precio, 1%)"
    )

    # Parámetros de rolling
    roll_threshold_days: int = Field(
        7, ge=1, le=30, description="Días antes del vencimiento para considerar roll"
    )
    roll_threshold_itm: Decimal = Field(
        Decimal("0.02"), ge=0, le=0.10, description="% ITM para considerar roll up"
    )
    roll_threshold_otm: Decimal = Field(
        Decimal("0.05"), ge=0, le=0.20, description="% OTM para considerar roll down"
    )

    # Gestión de riesgo
    assignment_probability_threshold: AssignmentProbability = Field(
        AssignmentProbability.HIGH, description="Umbral de probabilidad de assignment"
    )
    auto_roll: bool = Field(False, description="Habilitar rolling automático")

    # Filtros de calidad
    avoid_earnings: bool = Field(True, description="Evitar periodos de earnings")
    max_iv_percentile: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Percentil máximo de IV"
    )
    min_liquidity_rank: int = Field(5, ge=1, le=10, description="Rango mínimo de liquidez (1-10)")

    @model_validator(mode="after")
    def validate_config(self) -> "CoveredCallConfig":
        """Validar configuración."""
        if self.target_dte < 7:
            raise ValueError("target_dte debe ser al menos 7 días")
        if self.min_premium_pct < Decimal("0.005"):
            raise ValueError("min_premium_pct debe ser al menos 0.5%")
        return self


@dataclass
class RollDecision:
    """
    Decisión de rolling.

    Attributes:
        should_roll: Si se debe hacer roll
        roll_type: Tipo de roll recomendado
        new_strike: Strike recomendado
        new_expiry: Vencimiento recomendado
        reason: Razón de la decisión
        confidence: Confianza en la decisión (0-100)
    """

    should_roll: bool
    roll_type: Optional[RollType]
    new_strike: Optional[Decimal]
    new_expiry: Optional[date]
    reason: str
    confidence: Decimal  # 0-100
