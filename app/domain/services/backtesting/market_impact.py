"""
Market Impact Calculator

Implements market impact models for large orders:
- Temporary impact (price recovery during execution)
- Permanent impact (persistent price change)
- Almgren-Chriss model
- Square-root impact model

Reference: Rule 44-almgren-chriss-optimal-execution.md
Paper: Almgren, R., & Chriss, N. (2001) "Optimal Execution of Portfolio Transactions"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class ImpactModelType(str, Enum):
    """Type of market impact model."""

    ALMGREN_CHRISS = "almgren_chriss"
    SQUARE_ROOT = "square_root"
    LINEAR = "linear"
    NONLINEAR = "nonlinear"


@dataclass
class ImpactParameters:
    """Parameters for market impact calculation."""

    adv: Decimal  # Average daily volume
    volatility: float  # Annualized volatility (default 0.2 = 20%)
    market_cap: Optional[Decimal] = None  # Market capitalization
    spread: Optional[Decimal] = None  # Bid-ask spread
    price: Decimal = Decimal("0")  # Current price

    # Model-specific parameters
    gamma: float = 0.1  # Permanent impact coefficient
    eta: float = 0.05  # Temporary impact coefficient
    lambda_param: float = 0.5  # Volatility impact coefficient

    def __post_init__(self):
        """Set default values."""
        if self.price == Decimal("0"):
            self.price = Decimal("100")  # Default price


@dataclass
class TemporaryImpact:
    """Temporary market impact (recovers during execution)."""

    impact_per_share: Decimal
    recovery_time_hours: float = 1.0  # Time for price to recover
    decay_rate: float = 0.5  # Decay rate per hour

    def recover_after_hours(self, hours: float) -> Decimal:
        """Calculate remaining impact after given hours."""
        decay = np.exp(-self.decay_rate * hours)
        return self.impact_per_share * Decimal(str(decay))


@dataclass
class PermanentImpact:
    """Permanent market impact (persistent)."""

    impact_per_share: Decimal
    price_displacement: Decimal  # Total price displacement
    participation_rate: float  # Order participation rate


@dataclass
class MarketImpactResult:
    """Result of market impact calculation."""

    temporary: TemporaryImpact
    permanent: PermanentImpact
    total_impact: Decimal
    execution_price: Decimal
    expected_price: Decimal

    @property
    def impact_percentage(self) -> float:
        """Total impact as percentage of expected price."""
        if self.expected_price == 0:
            return 0.0
        return float(self.total_impact / self.expected_price)


class MarketImpactModel(ABC):
    """
    Base class for market impact models.

    Market impact is the price movement caused by trading a large order.
    It consists of two components:
    1. Temporary impact: Price recovers during/after execution
    2. Permanent impact: Persistent price change
    """

    @abstractmethod
    def calculate_impact(
        self,
        quantity: Decimal,
        side: str,
        params: ImpactParameters,
    ) -> MarketImpactResult:
        """
        Calculate market impact for an order.

        Args:
            quantity: Order size
            side: 'buy' or 'sell'
            params: Impact parameters

        Returns:
            MarketImpactResult
        """


class AlmgrenChristModel(MarketImpactModel):
    """
    Almgren-Chriss market impact model.

    Reference: Almgren, R., & Chriss, N. (2001)
    "Optimal Execution of Portfolio Transactions"

    Models impact as:
    - Permanent: gamma * (Q/ADV)
    - Temporary: eta * (Q/V) * sigma
    """

    def __init__(
        self,
        gamma: float = 0.1,  # Permanent impact coefficient
        eta: float = 0.05,  # Temporary impact coefficient
        lambda_param: float = 0.5,  # Volatility sensitivity
    ):
        """
        Initialize Almgren-Chriss model.

        Args:
            gamma: Permanent impact coefficient (typical 0.05-0.2)
            eta: Temporary impact coefficient (typical 0.01-0.1)
            lambda_param: Volatility sensitivity
        """
        self._gamma = gamma
        self._eta = eta
        self._lambda = lambda_param

    def calculate_impact(
        self,
        quantity: Decimal,
        side: str,
        params: ImpactParameters,
    ) -> MarketImpactResult:
        """Calculate Almgren-Chriss market impact."""
        qty_float = float(quantity)
        adv_float = float(params.adv)

        # Participation rate
        participation_rate = min(qty_float / adv_float, 1.0)

        # Daily volatility
        daily_vol = params.volatility / np.sqrt(252)

        # Permanent impact: gamma * (Q/ADV)
        permanent_pct = self._gamma * participation_rate
        permanent_amount = params.price * Decimal(str(permanent_pct))

        # Temporary impact: eta * (Q/ADV) * sigma_daily
        temporary_pct = self._eta * participation_rate * daily_vol
        temporary_amount = params.price * Decimal(str(temporary_pct))

        # Total impact
        total_impact = permanent_amount + temporary_amount

        # Calculate execution price
        if side == "buy":
            execution_price = params.price + total_impact
        else:
            execution_price = params.price - total_impact

        return MarketImpactResult(
            temporary=TemporaryImpact(
                impact_per_share=temporary_amount,
                recovery_time_hours=1.0,
                decay_rate=0.5,
            ),
            permanent=PermanentImpact(
                impact_per_share=permanent_amount,
                price_displacement=permanent_amount,
                participation_rate=participation_rate,
            ),
            total_impact=total_impact,
            execution_price=execution_price,
            expected_price=params.price,
        )


class SquareRootImpactModel(MarketImpactModel):
    """
    Square root market impact model.

    Based on empirical observation: Impact ~ (Q/ADV)^0.5

    This is a widely used model in practice.
    """

    def __init__(
        self,
        coefficient: float = 0.1,  # Impact coefficient (typical 0.05-0.2)
        volatility_factor: float = 0.5,  # Volatility multiplier
    ):
        """
        Initialize square root model.

        Args:
            coefficient: Base impact coefficient
            volatility_factor: How much volatility affects impact
        """
        self._coefficient = coefficient
        self._vol_factor = volatility_factor

    def calculate_impact(
        self,
        quantity: Decimal,
        side: str,
        params: ImpactParameters,
    ) -> MarketImpactResult:
        """Calculate square root market impact."""
        # Daily volatility
        daily_vol = params.volatility / np.sqrt(252)

        # Participation ratio
        participation_ratio = float(quantity) / float(params.adv)

        # Square root impact
        impact_pct = self._coefficient * daily_vol * np.sqrt(participation_ratio)

        # Adjust for volatility
        vol_adjustment = 1 + self._vol_factor * (params.volatility - 0.2) / 0.2
        impact_pct *= vol_adjustment

        total_impact = params.price * Decimal(str(impact_pct))

        # Split between temporary and permanent
        # Empirical studies suggest ~80% is temporary
        permanent_pct = impact_pct * 0.2
        temporary_pct = impact_pct * 0.8

        permanent_amount = params.price * Decimal(str(permanent_pct))
        temporary_amount = params.price * Decimal(str(temporary_pct))

        # Calculate execution price
        if side == "buy":
            execution_price = params.price + total_impact
        else:
            execution_price = params.price - total_impact

        return MarketImpactResult(
            temporary=TemporaryImpact(
                impact_per_share=temporary_amount,
                recovery_time_hours=0.5,
                decay_rate=1.0,
            ),
            permanent=PermanentImpact(
                impact_per_share=permanent_amount,
                price_displacement=permanent_amount,
                participation_rate=np.sqrt(participation_ratio),
            ),
            total_impact=total_impact,
            execution_price=execution_price,
            expected_price=params.price,
        )


class LinearImpactModel(MarketImpactModel):
    """
    Linear market impact model.

    Simplest model: Impact is linear in participation rate.

    Impact = coefficient * (Q/ADV)
    """

    def __init__(
        self,
        coefficient: float = 0.05,  # 5% impact at 100% participation
    ):
        """
        Initialize linear model.

        Args:
            coefficient: Impact coefficient
        """
        self._coefficient = coefficient

    def calculate_impact(
        self,
        quantity: Decimal,
        side: str,
        params: ImpactParameters,
    ) -> MarketImpactResult:
        """Calculate linear market impact."""
        participation_rate = min(float(quantity) / float(params.adv), 1.0)

        impact_pct = self._coefficient * participation_rate
        total_impact = params.price * Decimal(str(impact_pct))

        # All impact is permanent in this model
        permanent_amount = total_impact
        temporary_amount = Decimal("0")

        # Calculate execution price
        if side == "buy":
            execution_price = params.price + total_impact
        else:
            execution_price = params.price - total_impact

        return MarketImpactResult(
            temporary=TemporaryImpact(
                impact_per_share=temporary_amount,
                recovery_time_hours=0,
                decay_rate=0,
            ),
            permanent=PermanentImpact(
                impact_per_share=permanent_amount,
                price_displacement=permanent_amount,
                participation_rate=participation_rate,
            ),
            total_impact=total_impact,
            execution_price=execution_price,
            expected_price=params.price,
        )


class MarketImpactCalculator:
    """
    Calculator for market impact across multiple models.

    Provides a unified interface for calculating market impact
    using different models.
    """

    def __init__(
        self,
        default_model: ImpactModelType = ImpactModelType.SQUARE_ROOT,
    ):
        """
        Initialize calculator.

        Args:
            default_model: Default impact model to use
        """
        self._default_model = default_model
        self._models: Dict[ImpactModelType, MarketImpactModel] = {
            ImpactModelType.ALMGREN_CHRISS: AlmgrenChristModel(),
            ImpactModelType.SQUARE_ROOT: SquareRootImpactModel(),
            ImpactModelType.LINEAR: LinearImpactModel(),
        }

    def calculate_impact(
        self,
        quantity: Decimal,
        side: str,
        params: ImpactParameters,
        model: Optional[ImpactModelType] = None,
    ) -> MarketImpactResult:
        """
        Calculate market impact using specified model.

        Args:
            quantity: Order size
            side: 'buy' or 'sell'
            params: Impact parameters
            model: Model to use (default from constructor)

        Returns:
            MarketImpactResult
        """
        model_type = model or self._default_model
        impact_model = self._models[model_type]

        return impact_model.calculate_impact(quantity, side, params)

    def estimate_optimal_execution_size(
        self,
        target_price: Decimal,
        side: str,
        params: ImpactParameters,
        max_impact_pct: float = 0.01,  # Maximum 1% impact
        model: Optional[ImpactModelType] = None,
    ) -> Decimal:
        """
        Estimate optimal execution size to stay within impact threshold.

        Args:
            target_price: Target execution price
            side: 'buy' or 'sell'
            params: Impact parameters
            max_impact_pct: Maximum acceptable impact percentage
            model: Model to use

        Returns:
            Maximum order size
        """
        model_type = model or self._default_model

        # Binary search for optimal size
        low = Decimal("1")
        high = params.adv * Decimal("0.5")  # Max 50% of ADV

        best_size = low

        while low <= high:
            mid = (low + high) // 2
            result = self.calculate_impact(mid, side, params, model_type)

            impact_pct = abs(float(result.total_impact / params.price))

            if impact_pct <= max_impact_pct:
                best_size = mid
                low = mid + Decimal("1")
            else:
                high = mid - Decimal("1")

        return best_size

    def calculate_impact_curve(
        self,
        params: ImpactParameters,
        side: str,
        num_points: int = 20,
        model: Optional[ImpactModelType] = None,
    ) -> List[Tuple[Decimal, float]]:
        """
        Calculate impact curve (impact vs order size).

        Args:
            params: Impact parameters
            side: 'buy' or 'sell'
            num_points: Number of points to calculate
            model: Model to use

        Returns:
            List of (quantity, impact_percentage) tuples
        """
        model_type = model or self._default_model

        # Calculate impact for different sizes
        max_size = params.adv * Decimal("0.2")  # Up to 20% of ADV
        step = max_size / Decimal(str(num_points))

        curve = []
        for i in range(num_points):
            quantity = step * Decimal(str(i + 1))
            result = self.calculate_impact(quantity, side, params, model_type)
            impact_pct = result.impact_percentage
            curve.append((quantity, impact_pct))

        return curve
