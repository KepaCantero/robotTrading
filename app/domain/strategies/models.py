"""
Multi-Factor Strategy Data Models

This module defines Pydantic models for the multi-factor strategy implementing
the Fama-French 5-factor model plus Momentum factor.

Models include:
- FactorScores: Individual factor scores for each stock
- FactorProfile: Complete factor profile with all metrics
- FactorStrategyConfig: Strategy configuration
- FactorPortfolio: Factor-tilted portfolio representation

Reference:
- Fama-French 5-Factor Model: Market, Size, Value, Profitability, Investment
- Momentum factor (Carhart extension)
- Factor investing approach (Berkin & Swedroe)
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FactorType(str, Enum):
    """Factor types in the multi-factor model."""

    MARKET = "market"  # Market risk premium (Rm - Rf)
    SIZE = "size"  # SMB (Small Minus Big)
    VALUE = "value"  # HML (High Minus Low book-to-market)
    PROFITABILITY = "profitability"  # RMW (Robust Minus Weak)
    INVESTMENT = "investment"  # CMA (Conservative Minus Aggressive)
    MOMENTUM = "momentum"  # WML (Winners Minus Losers)


class FactorTiltDirection(str, Enum):
    """Factor tilt direction."""

    POSITIVE = "positive"  # Overweight positive factor exposure
    NEUTRAL = "neutral"  # Market-neutral exposure
    NEGATIVE = "negative"  # Underweight or short exposure


@dataclass
class FactorTilt:
    """Factor tilt specification."""

    factor: FactorType
    direction: FactorTiltDirection
    target_exposure: Decimal  # Target exposure (e.g., 0.2 for +20% tilt)
    max_exposure: Decimal  # Maximum allowed exposure
    weight: Decimal  # Weight in optimization (0-1)


class FactorScores(BaseModel):
    """
    Individual factor scores for a stock.

    Each score represents the stock's exposure to a specific factor.
    Scores are normalized to have mean=0, std=1 in the universe.
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        use_enum_values=True,
    )

    symbol: str = Field(..., description="Stock symbol")

    # Value factor metrics
    book_to_market: Optional[Decimal] = Field(None, description="Book-to-Market ratio")
    value_score: Optional[Decimal] = Field(
        None, ge=-3, le=3, description="Value factor score (standardized)"
    )

    # Size factor metrics
    market_cap: Optional[Decimal] = Field(
        None, ge=0, description="Market capitalization (millions)"
    )
    log_market_cap: Optional[Decimal] = Field(None, description="Log of market cap")
    size_score: Optional[Decimal] = Field(
        None, ge=-3, le=3, description="Size factor score (standardized)"
    )

    # Profitability factor metrics
    operating_profitability: Optional[Decimal] = Field(
        None, description="Operating profitability (ROA)"
    )
    roe: Optional[Decimal] = Field(None, description="Return on Equity")
    roa: Optional[Decimal] = Field(None, description="Return on Assets")
    profitability_score: Optional[Decimal] = Field(
        None, ge=-3, le=3, description="Profitability factor score"
    )

    # Investment factor metrics
    asset_growth: Optional[Decimal] = Field(None, description="Asset growth rate")
    investment_score: Optional[Decimal] = Field(
        None, ge=-3, le=3, description="Investment factor score (conservative = positive)"
    )

    # Momentum factor metrics
    momentum_12m: Optional[Decimal] = Field(
        None, description="12-month momentum (excluding last month)"
    )
    momentum_6m: Optional[Decimal] = Field(None, description="6-month momentum")
    momentum_score: Optional[Decimal] = Field(
        None, ge=-3, le=3, description="Momentum factor score"
    )

    # Composite scores
    composite_quality_score: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Composite quality score"
    )
    factor_momentum_score: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Factor momentum score"
    )

    # Factor model fit
    predicted_return: Optional[Decimal] = Field(
        None, description="Predicted return from factor model"
    )
    residual_return: Optional[Decimal] = Field(None, description="Residual (idiosyncratic) return")
    r_squared: Optional[Decimal] = Field(None, ge=0, le=1, description="R-squared of factor model")

    calculated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When scores were calculated"
    )


class FactorProfile(BaseModel):
    """
    Complete factor profile for a stock.

    Combines fundamental data with calculated factor scores
    for multi-factor investment decisions.
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    symbol: str = Field(..., description="Stock symbol")
    company_name: Optional[str] = Field(None, description="Company name")
    sector: Optional[str] = Field(None, description="GICS sector")
    industry: Optional[str] = Field(None, description="GICS industry")

    # Market data
    current_price: Decimal = Field(..., gt=0, description="Current market price")
    market_cap: Optional[Decimal] = Field(None, ge=0, description="Market cap (millions)")
    shares_outstanding: Optional[Decimal] = Field(None, ge=0, description="Shares outstanding")

    # Value metrics
    book_value_per_share: Optional[Decimal] = Field(None, ge=0, description="Book value per share")
    book_to_market: Optional[Decimal] = Field(None, ge=0, description="Book-to-market ratio")
    pe_ratio: Optional[Decimal] = Field(None, ge=0, description="P/E ratio (TTM)")
    pb_ratio: Optional[Decimal] = Field(None, ge=0, description="P/B ratio")
    ps_ratio: Optional[Decimal] = Field(None, ge=0, description="P/S ratio")
    ev_ebitda: Optional[Decimal] = Field(None, ge=0, description="EV/EBITDA")

    # Profitability metrics
    revenue: Optional[Decimal] = Field(None, ge=0, description="Total revenue (TTM)")
    ebitda: Optional[Decimal] = Field(None, ge=0, description="EBITDA (TTM)")
    operating_income: Optional[Decimal] = Field(None, ge=0, description="Operating income (TTM)")
    net_income: Optional[Decimal] = Field(None, ge=0, description="Net income (TTM)")
    roe: Optional[Decimal] = Field(None, description="Return on Equity (%)")
    roa: Optional[Decimal] = Field(None, description="Return on Assets (%)")
    roic: Optional[Decimal] = Field(None, description="Return on Invested Capital (%)")
    gross_margin: Optional[Decimal] = Field(None, ge=0, le=100, description="Gross margin (%)")
    operating_margin: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Operating margin (%)"
    )
    net_margin: Optional[Decimal] = Field(None, ge=0, le=100, description="Net margin (%)")

    # Investment metrics
    total_assets: Optional[Decimal] = Field(None, ge=0, description="Total assets")
    total_assets_py: Optional[Decimal] = Field(None, ge=0, description="Total assets prior year")
    asset_growth: Optional[Decimal] = Field(None, description="Asset growth rate (%)")
    capex: Optional[Decimal] = Field(None, ge=0, description="Capital expenditures")
    capex_py: Optional[Decimal] = Field(None, ge=0, description="Capex prior year")

    # Price history for momentum
    price_1m_ago: Optional[Decimal] = Field(None, gt=0, description="Price 1 month ago")
    price_3m_ago: Optional[Decimal] = Field(None, gt=0, description="Price 3 months ago")
    price_6m_ago: Optional[Decimal] = Field(None, gt=0, description="Price 6 months ago")
    price_12m_ago: Optional[Decimal] = Field(None, gt=0, description="Price 12 months ago")

    # Momentum calculations
    momentum_1m: Optional[Decimal] = Field(None, description="1-month return")
    momentum_3m: Optional[Decimal] = Field(None, description="3-month return")
    momentum_6m: Optional[Decimal] = Field(None, description="6-month return")
    momentum_12m: Optional[Decimal] = Field(None, description="12-month return")

    # Volatility and risk
    beta: Optional[Decimal] = Field(None, description="Beta (5-year monthly)")
    volatility_1y: Optional[Decimal] = Field(None, ge=0, description="1-year volatility")
    max_drawdown_1y: Optional[Decimal] = Field(None, le=0, description="1-year max drawdown")

    # Factor scores (calculated)
    factor_scores: Optional[FactorScores] = Field(None, description="Calculated factor scores")

    # Composite scores
    overall_factor_score: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Overall factor score"
    )
    quality_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Quality score")
    value_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Value score")
    growth_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Growth score")

    @property
    def momentum_excluding_last_month(self) -> Optional[Decimal]:
        """Calculate 12-month momentum excluding last month (standard Fama-French momentum)."""
        if self.price_12m_ago and self.price_1m_ago and self.current_price:
            # (P_t / P_{t-12}) - 1, excluding last month
            momentum_11m = (self.price_1m_ago / self.price_12m_ago) - 1
            return momentum_11m * 100
        return None

    @property
    def is_value_stock(self) -> bool:
        """Determine if stock is classified as value (high B/M)."""
        if self.book_to_market is None:
            return False
        # Value stocks typically have B/M > 0.5 (varies by market)
        return self.book_to_market > Decimal("0.5")

    @property
    def is_small_cap(self) -> bool:
        """Determine if stock is small cap."""
        if self.market_cap is None:
            return False
        # Small cap typically < $2B (varies by market)
        return self.market_cap < Decimal("2000")

    @property
    def is_profitable(self) -> bool:
        """Determine if stock is profitable (positive ROA)."""
        if self.roa is None:
            return False
        return self.roa > 0

    @property
    def is_conservative_investor(self) -> bool:
        """Determine if stock is a conservative investor (low asset growth)."""
        if self.asset_growth is None:
            return False
        # Conservative investors have low/negative asset growth
        return self.asset_growth < Decimal("5")

    @property
    def is_winner(self) -> bool:
        """Determine if stock is a momentum winner."""
        if self.momentum_excluding_last_month is None:
            return False
        # Winners: top 30% of returns
        return self.momentum_excluding_last_month > Decimal("15")


class FactorStrategyConfig(BaseModel):
    """
    Configuration for the multi-factor strategy.

    Implements Fama-French 5-factor model + Momentum with factor tilt optimization.
    """

    model_config = ConfigDict(
        strict=False,
        validate_assignment=True,
        extra="ignore",
    )

    # Strategy identification
    name: str = Field(default="MultiFactorStrategy", description="Strategy name")
    description: str = Field(
        default="Multi-factor strategy based on Fama-French 5-factor + Momentum model",
        description="Strategy description",
    )
    version: str = Field(default="1.0.0", description="Strategy version")
    objetivo_inversion: str = Field(default="BALANCED_GROWTH", description="Investment objective")

    # Universe and screening
    min_market_cap: Optional[Decimal] = Field(
        None, ge=0, description="Minimum market cap (millions, None = no filter)"
    )
    max_market_cap: Optional[Decimal] = Field(
        None, ge=0, description="Maximum market cap (millions, None = no filter)"
    )
    min_price: Decimal = Field(Decimal("5"), ge=0, description="Minimum stock price")
    min_daily_volume: Optional[Decimal] = Field(
        None, ge=0, description="Minimum daily volume (shares)"
    )

    # Factor tilt settings
    value_tilt: Decimal = Field(
        Decimal("0.2"),
        ge=-1,
        le=1,
        description="Value factor tilt (+0.2 = overweight value by 20%)",
    )
    size_tilt: Decimal = Field(
        Decimal("0"), ge=-1, le=1, description="Size factor tilt (+0.2 = overweight small caps)"
    )
    profitability_tilt: Decimal = Field(
        Decimal("0.2"),
        ge=-1,
        le=1,
        description="Profitability factor tilt (+0.2 = overweight profitable firms)",
    )
    investment_tilt: Decimal = Field(
        Decimal("0"),
        ge=-1,
        le=1,
        description="Investment factor tilt (+0.2 = overweight conservative investors)",
    )
    momentum_tilt: Decimal = Field(
        Decimal("0.1"), ge=-1, le=1, description="Momentum factor tilt (+0.1 = overweight winners)"
    )

    # Portfolio construction
    portfolio_size: int = Field(
        40, ge=10, le=100, description="Target number of stocks in portfolio"
    )
    max_sector_weight: Decimal = Field(
        Decimal("0.25"), ge=0.05, le=1.0, description="Maximum weight per sector"
    )
    max_single_position: Decimal = Field(
        Decimal("0.04"), ge=0.01, le=0.5, description="Maximum weight per position"
    )
    min_position: Decimal = Field(
        Decimal("0.01"), ge=0.005, le=0.1, description="Minimum position size"
    )

    # Factor constraints
    max_factor_exposure: Decimal = Field(
        Decimal("0.3"), ge=0.1, le=1.0, description="Maximum exposure to any single factor"
    )
    factor_neutral: bool = Field(
        False, description="Require market-neutral factor exposure (sum to zero)"
    )

    # Rebalancing
    rebalance_frequency: str = Field(
        "quarterly", description="Rebalancing frequency (monthly, quarterly, semi_annual)"
    )
    rebalance_threshold: Decimal = Field(
        Decimal("0.05"),
        ge=0.01,
        le=0.2,
        description="Rebalance threshold (drift before rebalancing)",
    )

    # Risk management
    max_beta: Optional[Decimal] = Field(
        None, ge=0, description="Maximum portfolio beta (None = no constraint)"
    )
    max_volatility: Optional[Decimal] = Field(
        None, ge=0, description="Maximum portfolio volatility (None = no constraint)"
    )
    stop_loss_factor: Decimal = Field(
        Decimal("0.15"), ge=0, le=1, description="Stop loss as factor of portfolio volatility"
    )

    # Factor scoring weights
    value_weight: Decimal = Field(
        Decimal("0.25"), ge=0, le=1, description="Weight of value factor in scoring"
    )
    profitability_weight: Decimal = Field(
        Decimal("0.25"), ge=0, le=1, description="Weight of profitability factor in scoring"
    )
    momentum_weight: Decimal = Field(
        Decimal("0.20"), ge=0, le=1, description="Weight of momentum factor in scoring"
    )
    size_weight: Decimal = Field(
        Decimal("0.15"), ge=0, le=1, description="Weight of size factor in scoring"
    )
    investment_weight: Decimal = Field(
        Decimal("0.15"), ge=0, le=1, description="Weight of investment factor in scoring"
    )

    # Minimum scores
    min_quality_score: Decimal = Field(
        Decimal("40"), ge=0, le=100, description="Minimum quality score to include"
    )
    min_factor_score: Decimal = Field(
        Decimal("30"), ge=0, le=100, description="Minimum composite factor score to include"
    )

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "FactorStrategyConfig":
        """Validate that factor weights sum approximately to 1."""
        from app.core.centralized_config import get_config

        total = (
            self.value_weight
            + self.profitability_weight
            + self.momentum_weight
            + self.size_weight
            + self.investment_weight
        )
        # Get tolerance from config
        cfg = get_config()
        tolerance = Decimal(str(getattr(cfg.trading, 'factor_weights_tolerance', 0.05)))
        if abs(total - Decimal("1.0")) > tolerance:
            raise ValueError(f"Factor weights must sum to 1.0, sum to {total}")
        return self

    @model_validator(mode="after")
    def validate_tilt_ranges(self) -> "FactorStrategyConfig":
        """Validate that tilts are within reasonable ranges."""
        from app.core.centralized_config import get_config

        total_tilt = abs(self.value_tilt) + abs(self.size_tilt) + abs(self.profitability_tilt)
        # Get tilt limit from config
        cfg = get_config()
        max_tilt = Decimal(str(getattr(cfg.trading, 'max_total_tilt', 0.8)))
        if total_tilt > max_tilt:
            raise ValueError(f"Total absolute tilt exceeds {max_tilt}: {total_tilt}")
        return self

    def get_factor_tilts(self) -> List[FactorTilt]:
        """Get list of factor tilts as dataclasses."""
        return [
            FactorTilt(
                factor=FactorType.VALUE,
                direction=(
                    FactorTiltDirection.POSITIVE
                    if self.value_tilt > 0
                    else (
                        FactorTiltDirection.NEGATIVE
                        if self.value_tilt < 0
                        else FactorTiltDirection.NEUTRAL
                    )
                ),
                target_exposure=abs(self.value_tilt),
                max_exposure=self.max_factor_exposure,
                weight=self.value_weight,
            ),
            FactorTilt(
                factor=FactorType.SIZE,
                direction=(
                    FactorTiltDirection.POSITIVE
                    if self.size_tilt > 0
                    else (
                        FactorTiltDirection.NEGATIVE
                        if self.size_tilt < 0
                        else FactorTiltDirection.NEUTRAL
                    )
                ),
                target_exposure=abs(self.size_tilt),
                max_exposure=self.max_factor_exposure,
                weight=self.size_weight,
            ),
            FactorTilt(
                factor=FactorType.PROFITABILITY,
                direction=(
                    FactorTiltDirection.POSITIVE
                    if self.profitability_tilt > 0
                    else (
                        FactorTiltDirection.NEGATIVE
                        if self.profitability_tilt < 0
                        else FactorTiltDirection.NEUTRAL
                    )
                ),
                target_exposure=abs(self.profitability_tilt),
                max_exposure=self.max_factor_exposure,
                weight=self.profitability_weight,
            ),
            FactorTilt(
                factor=FactorType.INVESTMENT,
                direction=(
                    FactorTiltDirection.POSITIVE
                    if self.investment_tilt > 0
                    else (
                        FactorTiltDirection.NEGATIVE
                        if self.investment_tilt < 0
                        else FactorTiltDirection.NEUTRAL
                    )
                ),
                target_exposure=abs(self.investment_tilt),
                max_exposure=self.max_factor_exposure,
                weight=self.investment_weight,
            ),
            FactorTilt(
                factor=FactorType.MOMENTUM,
                direction=(
                    FactorTiltDirection.POSITIVE
                    if self.momentum_tilt > 0
                    else (
                        FactorTiltDirection.NEGATIVE
                        if self.momentum_tilt < 0
                        else FactorTiltDirection.NEUTRAL
                    )
                ),
                target_exposure=abs(self.momentum_tilt),
                max_exposure=self.max_factor_exposure,
                weight=self.momentum_weight,
            ),
        ]

    def get_config_description(self) -> str:
        """Get human-readable configuration description."""
        return (
            f"Multi-Factor Strategy Configuration:\n"
            f"  Objective: {self.objetivo_inversion}\n"
            f"  Portfolio Size: {self.portfolio_size}\n"
            f"  Max Sector Weight: {self.max_sector_weight:.1%}\n"
            f"  Max Position: {self.max_single_position:.1%}\n"
            f"  Rebalance: {self.rebalance_frequency}\n"
            f"  Factor Tilts:\n"
            f"    Value: {self.value_tilt:+.1%}\n"
            f"    Size: {self.size_tilt:+.1%}\n"
            f"    Profitability: {self.profitability_tilt:+.1%}\n"
            f"    Investment: {self.investment_tilt:+.1%}\n"
            f"    Momentum: {self.momentum_tilt:+.1%}\n"
        )


class FactorPosition(BaseModel):
    """Position in factor portfolio."""

    symbol: str = Field(..., description="Stock symbol")
    weight: Decimal = Field(..., ge=0, le=1, description="Portfolio weight")
    factor_exposure: Dict[str, Decimal] = Field(
        default_factory=dict, description="Factor exposures"
    )
    expected_return: Optional[Decimal] = Field(
        None, description="Expected return from factor model"
    )
    sector: Optional[str] = Field(None, description="Sector classification")


class FactorPortfolio(BaseModel):
    """Factor-tilted portfolio."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    positions: List[FactorPosition] = Field(default_factory=list, description="Portfolio positions")
    total_value: Decimal = Field(..., ge=0, description="Total portfolio value")
    cash: Decimal = Field(Decimal("0"), ge=0, description="Cash balance")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    rebalance_at: Optional[datetime] = Field(None, description="Next rebalance date")

    # Factor exposures
    factor_exposures: Dict[str, Decimal] = Field(
        default_factory=dict, description="Portfolio factor exposures"
    )

    # Sector weights
    sector_weights: Dict[str, Decimal] = Field(default_factory=dict, description="Sector weights")

    @property
    def positions_count(self) -> int:
        """Number of positions."""
        return len(self.positions)

    @property
    def invested_capital(self) -> Decimal:
        """Invested capital (excluding cash)."""
        return self.total_value - self.cash

    @property
    def is_diversified(self) -> bool:
        """Check if portfolio is sufficiently diversified."""
        return len(self.positions) >= 20

    @property
    def max_position_weight(self) -> Decimal:
        """Maximum position weight."""
        if not self.positions:
            return Decimal("0")
        return max(pos.weight for pos in self.positions)

    @property
    def herfindahl_index(self) -> Decimal:
        """Calculate Herfindahl-Hirschman Index (concentration measure)."""
        if not self.positions:
            return Decimal("0")
        hhi = sum(pos.weight**2 for pos in self.positions)
        return hhi


@dataclass
class FactorOptimizationResult:
    """Result of factor optimization."""

    weights: Dict[str, Decimal]  # Optimized weights
    expected_return: Decimal
    expected_risk: Decimal
    factor_exposures: Dict[str, Decimal]
    optimization_status: str  # "optimal", "suboptimal", "failed"
    iterations: int
    objective_value: Decimal


@dataclass
class FactorRebalanceRecommendation:
    """Recommendation for portfolio rebalancing."""

    needs_rebalance: bool
    reason: str
    current_weights: Dict[str, Decimal]
    target_weights: Dict[str, Decimal]
    trades_required: List[tuple[str, Decimal, Decimal]]  # (symbol, current, target)
    estimated_cost: Decimal
    expected_benefit: Decimal
