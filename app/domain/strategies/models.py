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

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger(__name__)


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
        from app.shared.config.centralized_config import get_config

        total = (
            self.value_weight
            + self.profitability_weight
            + self.momentum_weight
            + self.size_weight
            + self.investment_weight
        )
        # Get tolerance from config
        cfg = get_config()
        tolerance = Decimal(str(getattr(cfg.trading, "factor_weights_tolerance", 0.05)))
        if abs(total - Decimal("1.0")) > tolerance:
            logger.error(
                "Factor weights validation failed",
                extra={
                    "total": float(total),
                    "tolerance": float(tolerance),
                    "weights": {
                        "value": float(self.value_weight),
                        "profitability": float(self.profitability_weight),
                        "momentum": float(self.momentum_weight),
                        "size": float(self.size_weight),
                        "investment": float(self.investment_weight),
                    },
                },
            )
            raise ValueError(f"Factor weights must sum to 1.0, sum to {total}")
        logger.debug(
            "Factor weights validated successfully",
            extra={"total": float(total)},
        )
        return self

    @model_validator(mode="after")
    def validate_tilt_ranges(self) -> "FactorStrategyConfig":
        """Validate that tilts are within reasonable ranges."""
        from app.shared.config.centralized_config import get_config

        total_tilt = abs(self.value_tilt) + abs(self.size_tilt) + abs(self.profitability_tilt)
        # Get tilt limit from config
        cfg = get_config()
        max_tilt = Decimal(str(getattr(cfg.trading, "max_total_tilt", 0.8)))
        if total_tilt > max_tilt:
            logger.error(
                "Factor tilt validation failed",
                extra={
                    "total_tilt": float(total_tilt),
                    "max_tilt": float(max_tilt),
                    "tilts": {
                        "value": float(self.value_tilt),
                        "size": float(self.size_tilt),
                        "profitability": float(self.profitability_tilt),
                    },
                },
            )
            raise ValueError(f"Total absolute tilt exceeds {max_tilt}: {total_tilt}")
        logger.debug(
            "Factor tilts validated successfully",
            extra={"total_tilt": float(total_tilt)},
        )
        return self

    def get_factor_tilts(self) -> list[FactorTilt]:
        """Get list of factor tilts as dataclasses."""
        logger.debug(
            "Generating factor tilts",
            extra={
                "value_tilt": float(self.value_tilt),
                "size_tilt": float(self.size_tilt),
                "profitability_tilt": float(self.profitability_tilt),
                "investment_tilt": float(self.investment_tilt),
                "momentum_tilt": float(self.momentum_tilt),
            },
        )
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
    factor_exposure: dict[str, Decimal] = Field(
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

    positions: list[FactorPosition] = Field(default_factory=list, description="Portfolio positions")
    total_value: Decimal = Field(..., ge=0, description="Total portfolio value")
    cash: Decimal = Field(Decimal("0"), ge=0, description="Cash balance")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    rebalance_at: Optional[datetime] = Field(None, description="Next rebalance date")

    # Factor exposures
    factor_exposures: dict[str, Decimal] = Field(
        default_factory=dict, description="Portfolio factor exposures"
    )

    # Sector weights
    sector_weights: dict[str, Decimal] = Field(default_factory=dict, description="Sector weights")

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
        # Calculate sum of squared weights
        hhi = Decimal("0")
        for pos in self.positions:
            hhi += pos.weight**2
        return hhi


@dataclass
class FactorOptimizationResult:
    """Result of factor optimization."""

    weights: dict[str, Decimal]  # Optimized weights
    expected_return: Decimal
    expected_risk: Decimal
    factor_exposures: dict[str, Decimal]
    optimization_status: str  # "optimal", "suboptimal", "failed"
    iterations: int
    objective_value: Decimal


@dataclass
class FactorRebalanceRecommendation:
    """Recommendation for portfolio rebalancing."""

    needs_rebalance: bool
    reason: str
    current_weights: dict[str, Decimal]
    target_weights: dict[str, Decimal]
    trades_required: list[tuple[str, Decimal, Decimal]]  # (symbol, current, target)
    estimated_cost: Decimal
    expected_benefit: Decimal


# =============================================================================
# DIVIDEND STRATEGY MODELS
# =============================================================================


class DividendSafety(str, Enum):
    """Dividend safety rating."""

    SAFE = "safe"
    MODERATE = "moderate"
    AT_RISK = "at_risk"
    HIGH_RISK = "high_risk"
    UNSUSTAINABLE = "unsustainable"


@dataclass
class DividendProfile:
    """Profile of a dividend-paying stock."""

    symbol: str
    company_name: str
    dividend_yield: Decimal
    annual_dividend: Decimal
    payout_ratio: Decimal
    dividend_growth_rate: Decimal
    years_of_growth: int
    ex_dividend_date: Optional[datetime] = None
    payment_date: Optional[datetime] = None
    safety_rating: DividendSafety = DividendSafety.MODERATE
    quality_score: Decimal = Decimal("0")


@dataclass
class DividendStock:
    """Extended dividend stock information."""

    profile: DividendProfile
    price: Decimal
    market_cap: Decimal
    sector: str
    pe_ratio: Decimal
    eps: Decimal
    free_cash_flow: Decimal
    total_debt: Decimal
    fcf_coverage: Decimal  # FCF / Dividend


class DividendStrategyConfig(BaseModel):
    """Configuration for dividend strategy."""

    model_config = ConfigDict(extra="ignore")

    # Strategy identification
    name: str = Field(default="DividendStrategy", description="Strategy name")
    description: str = Field(
        default="Dividend investing strategy", description="Strategy description"
    )
    version: str = Field(default="1.0.0", description="Strategy version")

    # Dividend yield thresholds
    min_yield: Decimal = Field(default=Decimal("2.0"), description="Minimum dividend yield (%)")
    max_yield: Decimal = Field(default=Decimal("8.0"), description="Maximum dividend yield (%)")
    min_dividend_yield: Decimal = Field(
        default=Decimal("2.0"), description="Minimum dividend yield (alias)"
    )
    max_dividend_yield: Decimal = Field(
        default=Decimal("8.0"), description="Maximum dividend yield (alias)"
    )

    # Payout and coverage
    max_payout_ratio: Decimal = Field(
        default=Decimal("75.0"), description="Maximum payout ratio (%)"
    )
    min_fcf_coverage: Decimal = Field(default=Decimal("1.5"), description="Minimum FCF coverage")
    min_years_of_growth: int = Field(default=3, description="Minimum years of dividend growth")
    min_years_consecutive: int = Field(
        default=3, description="Minimum consecutive years of dividend payments"
    )

    # Portfolio construction
    max_positions: int = Field(default=25, description="Maximum positions in portfolio")
    portfolio_size: int = Field(default=25, description="Target portfolio size")
    max_sector_weight: Decimal = Field(default=Decimal("0.30"), description="Maximum sector weight")
    max_single_position: Decimal = Field(
        default=Decimal("0.05"), description="Maximum single position"
    )
    sector_diversification: bool = Field(default=True, description="Enable sector diversification")

    # Quality thresholds
    min_quality_score: Decimal = Field(default=Decimal("60.0"), description="Minimum quality score")
    min_sustainability_score: Decimal = Field(
        default=Decimal("50.0"), description="Minimum sustainability score"
    )

    # Dividend capture settings
    enable_dividend_capture: bool = Field(default=False, description="Enable dividend capture mode")
    min_days_before_ex_dividend: int = Field(
        default=3, description="Min days before ex-dividend to buy"
    )
    min_dividend_growth: Decimal = Field(
        default=Decimal("5.0"), description="Minimum dividend growth rate (%)"
    )
    min_market_cap: Decimal = Field(
        default=Decimal("1000000000"), description="Minimum market cap for dividend stocks"
    )
    require_profitable: bool = Field(default=True, description="Require profitable companies")
    require_positive_fcf: bool = Field(default=True, description="Require positive free cash flow")
    min_dividend_safety: str = Field(
        default="moderate", description="Minimum dividend safety rating"
    )
    excluded_sectors: list[str] = Field(default_factory=list, description="Sectors to exclude")
    exclude_reits: bool = Field(default=False, description="Exclude REITs from screening")
    exclude_mlps: bool = Field(default=False, description="Exclude MLPs from screening")
    max_pe_ratio: Optional[Decimal] = Field(
        default=Decimal("25.0"), description="Maximum P/E ratio"
    )
    max_pb_ratio: Optional[Decimal] = Field(default=Decimal("3.0"), description="Maximum P/B ratio")
    max_beta: Optional[Decimal] = Field(default=Decimal("1.2"), description="Maximum beta")
    # Scoring weights
    yield_weight: Decimal = Field(default=Decimal("0.3"), description="Yield score weight")
    growth_weight: Decimal = Field(default=Decimal("0.25"), description="Growth score weight")
    sustainability_weight: Decimal = Field(
        default=Decimal("0.25"), description="Sustainability score weight"
    )
    value_weight: Decimal = Field(default=Decimal("0.2"), description="Value score weight")

    # Rebalancing
    rebalance_threshold: Decimal = Field(default=Decimal("0.05"), description="Rebalance threshold")
    rebalance_frequency_days: int = Field(default=90, description="Rebalance frequency in days")


@dataclass
class ExDividendDate:
    """Ex-dividend date information."""

    symbol: str
    ex_date: datetime
    payment_date: datetime
    record_date: datetime
    declared_date: datetime
    dividend_amount: Decimal
    frequency: str  # quarterly, annual, etc.


# =============================================================================
# LOW VOLATILITY STRATEGY MODELS
# =============================================================================


class VolatilityRegime(str, Enum):
    """Volatility regime classification."""

    LOW = "low"
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class VolatilityMetrics:
    """Comprehensive volatility metrics for a stock."""

    symbol: str = ""
    average_volatility: Decimal = Decimal("0.15")  # Average daily volatility (%)
    annualized_volatility: Decimal = Decimal("0.20")  # Annualized volatility (%)
    beta: Decimal = Decimal("1.0")  # Market beta
    downside_risk: Decimal = Decimal("0.10")  # Downside deviation
    max_drawdown: Decimal = Decimal("0.10")  # Maximum drawdown (%)
    sortino_ratio: Decimal = Decimal("1.0")  # Sortino ratio
    volatility_regime: VolatilityRegime = VolatilityRegime.NORMAL  # Current regime
    calculated_at: Optional[datetime] = None
    # Extended volatility metrics
    historical_volatility_20d: Optional[Decimal] = None  # 20-day historical volatility (%)
    historical_volatility_60d: Optional[Decimal] = None  # 60-day historical volatility (%)
    historical_volatility_252d: Optional[Decimal] = None  # 252-day historical volatility (%)
    sharpe_ratio: Optional[Decimal] = None  # Sharpe ratio
    correlation_to_market: Optional[Decimal] = None  # Correlation with market
    idiosyncratic_volatility: Optional[Decimal] = None  # Idiosyncratic volatility (%)
    skewness: Optional[Decimal] = None  # Return distribution skewness
    kurtosis: Optional[Decimal] = None  # Return distribution kurtosis

    def __post_init__(self):
        # Ensure all fields are properly initialized
        if self.average_volatility is None:
            self.average_volatility = Decimal("0.15")
        if self.annualized_volatility is None:
            self.annualized_volatility = Decimal("0.20")
        if self.beta is None:
            self.beta = Decimal("1.0")
        if self.downside_risk is None:
            self.downside_risk = Decimal("0.10")
        if self.max_drawdown is None:
            self.max_drawdown = Decimal("0.10")
        if self.sortino_ratio is None:
            self.sortino_ratio = Decimal("1.0")


@dataclass
class LowVolatilityProfile:
    """Profile of a low volatility stock."""

    symbol: str
    company_name: str = ""
    sector: str = ""
    current_price: Optional[Decimal] = None
    daily_volatility: Decimal = Decimal("0")
    annualized_volatility: Decimal = Decimal("0")
    beta: Decimal = Decimal("1.0")
    downside_deviation: Decimal = Decimal("0")
    max_drawdown: Decimal = Decimal("0")
    sharpe_ratio: Decimal = Decimal("0")
    sortino_ratio: Decimal = Decimal("0")
    percentile_rank: Decimal = Decimal("0.5")  # Volatility rank (0-1)
    volatility_metrics: Optional[VolatilityMetrics] = None
    low_vol_score: Optional[Decimal] = None
    defensive_score: Optional[Decimal] = None
    stability_score: Optional[Decimal] = None
    overall_score: Optional[Decimal] = None
    is_defensive_stock: bool = False

    def __post_init__(self):
        """Initialize volatility_metrics with default values if not provided."""
        if self.volatility_metrics is None:
            self.volatility_metrics = VolatilityMetrics(
                symbol=self.symbol,
                average_volatility=self.daily_volatility,
                annualized_volatility=self.annualized_volatility,
                beta=self.beta,
                downside_risk=self.downside_deviation,
                max_drawdown=self.max_drawdown,
                sortino_ratio=self.sortino_ratio,
            )


@dataclass
class LowVolatilityStock:
    """Extended low volatility stock information."""

    profile: LowVolatilityProfile
    price: Decimal
    market_cap: Decimal
    dividend_yield: Decimal
    pe_ratio: Decimal
    is_defensive_sector: bool = False


@dataclass
class LowVolatilityStockResult:
    """Low volatility stock with decision information."""

    profile: LowVolatilityProfile
    decision_score: Decimal
    decision_reason: str
    recommendation: str


@dataclass
class LowVolatilityScreeningResult:
    """Result of low volatility stock screening operation."""

    passed_stocks: list[LowVolatilityStockResult]
    failed_stocks: dict[str, list[str]]
    total_evaluated: int
    screening_time_ms: float
    criteria: "LowVolatilityScreeningCriteria"

    @property
    def pass_rate(self) -> float:
        """Calculate the percentage of stocks that passed screening."""
        if self.total_evaluated == 0:
            return 0.0
        return (len(self.passed_stocks) / self.total_evaluated) * 100.0


class LowVolatilityStrategyConfig(BaseModel):
    """Configuration for low volatility strategy."""

    model_config = ConfigDict(extra="ignore")  # Allow extra fields for flexibility

    # Strategy identification
    name: str = Field(default="LowVolatilityStrategy", description="Strategy name")
    description: str = Field(default="Low volatility strategy", description="Strategy description")
    version: str = Field(default="1.0.0", description="Strategy version")

    # Volatility thresholds
    max_volatility_percentile: Decimal = Field(
        default=Decimal("0.3"), description="Maximum volatility percentile (0-1)"
    )
    max_historical_volatility: Decimal = Field(
        default=Decimal("25.0"), description="Maximum historical volatility (%)"
    )
    max_beta: Decimal = Field(default=Decimal("0.8"), description="Maximum beta")
    min_beta: Decimal = Field(default=Decimal("0.0"), description="Minimum beta")
    max_downside_deviation: Decimal = Field(
        default=Decimal("0.15"), description="Maximum downside deviation"
    )
    max_downside_risk: Decimal = Field(default=Decimal("0.20"), description="Maximum downside risk")
    max_max_drawdown: Decimal = Field(default=Decimal("0.30"), description="Maximum drawdown limit")
    target_volatility: Optional[Decimal] = Field(
        default=None, description="Target portfolio volatility"
    )

    # Performance thresholds
    min_sharpe_ratio: Decimal = Field(default=Decimal("0.5"), description="Minimum Sharpe ratio")
    min_sortino_ratio: Optional[Decimal] = Field(default=None, description="Minimum Sortino ratio")

    # Score thresholds
    min_low_vol_score: Decimal = Field(default=Decimal("60.0"), description="Minimum low vol score")
    min_defensive_score: Decimal = Field(
        default=Decimal("50.0"), description="Minimum defensive score"
    )
    min_stability_score: Decimal = Field(
        default=Decimal("50.0"), description="Minimum stability score"
    )

    # Portfolio construction
    portfolio_size: int = Field(default=30, description="Number of positions in portfolio")
    max_positions: int = Field(default=30, description="Maximum positions in portfolio")
    max_sector_weight: Decimal = Field(
        default=Decimal("0.35"), description="Maximum weight per sector"
    )
    max_single_position: Decimal = Field(
        default=Decimal("0.06"), description="Maximum weight per position"
    )

    # Sector preferences
    defensive_sector_bias: bool = Field(default=True, description="Bias toward defensive sectors")
    require_defensive_sector: bool = Field(
        default=False, description="Require stocks to be in defensive sectors"
    )
    preferred_sectors: list[str] = Field(
        default_factory=lambda: ["Utilities", "Consumer Staples", "Healthcare", "Real Estate"],
        description="Preferred defensive sectors",
    )
    avoid_sectors: list[str] = Field(
        default_factory=lambda: ["Technology", "Biotechnology", "Energy", "Materials"],
        description="Sectors to avoid",
    )

    # Optimization settings
    optimization_method: str = Field(default="min_variance", description="Optimization method")
    risk_free_rate: Decimal = Field(default=Decimal("0.04"), description="Risk-free rate")

    # Rebalancing
    rebalance_threshold: Decimal = Field(default=Decimal("0.05"), description="Rebalance threshold")

    # Universe settings
    min_market_cap: Optional[Decimal] = Field(default=None, description="Minimum market cap")

    # Scoring weights
    volatility_weight: Decimal = Field(
        default=Decimal("0.4"), description="Volatility score weight"
    )
    defensive_weight: Decimal = Field(default=Decimal("0.3"), description="Defensive score weight")
    stability_weight: Decimal = Field(default=Decimal("0.2"), description="Stability score weight")
    quality_weight: Decimal = Field(default=Decimal("0.1"), description="Quality score weight")


# =============================================================================
# SCREENING CRITERIA MODELS
# =============================================================================


class DividendScreeningCriteria(BaseModel):
    """Screening criteria for dividend stocks."""

    model_config = ConfigDict(extra="ignore")  # Allow extra fields for flexibility

    min_market_cap: Decimal = Field(default=Decimal("1000000000"), description="Minimum market cap")
    min_dividend_yield: Decimal = Field(
        default=Decimal("2.0"), description="Minimum dividend yield (%)"
    )
    max_dividend_yield: Decimal = Field(
        default=Decimal("10.0"), description="Maximum dividend yield (%)"
    )
    max_payout_ratio: Decimal = Field(
        default=Decimal("75.0"), description="Maximum payout ratio (%)"
    )
    min_years_of_growth: int = Field(default=3, description="Minimum years of dividend growth")
    min_fcf_coverage: Decimal = Field(default=Decimal("1.5"), description="Minimum FCF coverage")
    exclude_sectors: list[str] = Field(default_factory=list, description="Sectors to exclude")
    excluded_sectors: list[str] = Field(
        default_factory=list, description="Sectors to exclude (alias)"
    )
    min_yield: Decimal = Field(default=Decimal("2.0"), description="Minimum yield")
    max_yield: Decimal = Field(default=Decimal("10.0"), description="Maximum yield")
    max_payout: Decimal = Field(default=Decimal("75.0"), description="Maximum payout")
    min_growth: Optional[Decimal] = Field(default=None, description="Minimum growth")
    min_years: int = Field(default=3, description="Minimum years")
    min_quality: Decimal = Field(default=Decimal("50.0"), description="Minimum quality score")
    min_sustainability: Decimal = Field(
        default=Decimal("50.0"), description="Minimum sustainability score"
    )
    require_profitable: bool = Field(default=True, description="Require profitable companies")
    require_positive_fcf: bool = Field(default=True, description="Require positive FCF")
    min_safety: str = Field(default="moderate", description="Minimum safety rating")


class LowVolatilityScreeningCriteria(BaseModel):
    """Screening criteria for low volatility stocks."""

    model_config = ConfigDict(extra="ignore")  # Allow extra fields for flexibility

    min_market_cap: Optional[Decimal] = Field(
        default=Decimal("1000000000"), description="Minimum market cap"
    )
    max_volatility_percentile: Decimal = Field(
        default=Decimal("0.3"), description="Maximum volatility percentile (0-1)"
    )
    max_volatility: Decimal = Field(default=Decimal("25.0"), description="Maximum volatility")
    max_beta: Decimal = Field(default=Decimal("0.8"), description="Maximum beta")
    min_beta: Decimal = Field(default=Decimal("0.0"), description="Minimum beta")
    max_downside_risk: Decimal = Field(default=Decimal("0.20"), description="Maximum downside risk")
    max_downside_deviation: Decimal = Field(
        default=Decimal("0.15"), description="Maximum downside deviation"
    )
    max_drawdown: Decimal = Field(default=Decimal("0.30"), description="Maximum drawdown")
    min_sortino: Optional[Decimal] = Field(default=None, description="Minimum Sortino ratio")
    min_sharpe_ratio: Decimal = Field(default=Decimal("0.0"), description="Minimum Sharpe ratio")
    min_avg_volume: Decimal = Field(default=Decimal("500000"), description="Minimum average volume")
    min_low_vol_score: Decimal = Field(default=Decimal("60.0"), description="Minimum low vol score")
    min_defensive_score: Decimal = Field(
        default=Decimal("50.0"), description="Minimum defensive score"
    )
    min_stability_score: Decimal = Field(
        default=Decimal("50.0"), description="Minimum stability score"
    )
    preferred_sectors: list[str] = Field(
        default_factory=lambda: ["Utilities", "Consumer Staples", "Healthcare", "Real Estate"],
        description="Preferred defensive sectors",
    )
    avoid_sectors: list[str] = Field(default_factory=list, description="Sectors to avoid")
    require_defensive: bool = Field(default=False, description="Require defensive sector")


# =============================================================================
# GENERIC SCREENING RESULT
# =============================================================================


class SectorDefensiveLevel(str, Enum):
    """Sector defensive level classification."""

    HIGHLY_DEFENSIVE = "highly_defensive"  # Utilities, Consumer Staples
    DEFENSIVE = "defensive"  # Healthcare, Real Estate
    NEUTRAL = "neutral"  # Industrials, Financials, Communication Services
    CYCLICAL = "cyclical"  # Technology, Communication Services
    HIGHLY_CYCLICAL = "highly_cyclical"  # Consumer Discretionary
    SENSITIVE = "sensitive"  # Energy, Materials


@dataclass
class ScreeningResult:
    """Generic result of a screening operation."""

    passed: bool
    symbol: str
    score: Decimal
    reasons: list[str]
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DividendStockResult:
    """Dividend stock with decision information."""

    profile: DividendProfile
    decision_score: Decimal
    decision_reason: str
    recommendation: str


@dataclass
class DividendScreeningResult:
    """Result of dividend stock screening operation."""

    passed_stocks: list[DividendStockResult]
    failed_stocks: dict[str, list[str]]
    total_evaluated: int
    screening_time_ms: float
    criteria: DividendScreeningCriteria

    @property
    def pass_rate(self) -> float:
        """Calculate the percentage of stocks that passed screening."""
        if self.total_evaluated == 0:
            return 0.0
        return (len(self.passed_stocks) / self.total_evaluated) * 100.0


# =============================================================================
# OPTION STRATEGY MODELS
# =============================================================================


class Moneyness(str, Enum):
    """Option moneyness classification."""

    ITM = "in_the_money"  # In-the-money
    ATM = "at_the_money"  # At-the-money
    OTM = "out_of_the_money"  # Out-of-the-money
    DEEP_ITM = "deep_in_the_money"  # Deep in-the-money
    DEEP_OTM = "deep_out_of_the_money"  # Deep out-of-the-money


class AssignmentProbability(str, Enum):
    """Probability of option assignment."""

    VERY_LOW = "very_low"  # < 10%
    LOW = "low"  # 10-25%
    MODERATE = "moderate"  # 25-50%
    HIGH = "high"  # 50-75%
    VERY_HIGH = "very_high"  # > 75%


@dataclass
class OptionGreeks:
    """Option Greeks (sensitivities)."""

    delta: Decimal  # Price sensitivity to underlying
    gamma: Decimal  # Delta sensitivity to underlying
    theta: Decimal  # Price sensitivity to time (daily decay)
    vega: Decimal  # Price sensitivity to volatility
    rho: Decimal = Decimal("0")  # Price sensitivity to interest rate


@dataclass
class CallOption:
    """Call option data for covered call screening."""

    # Basic option data
    symbol: str  # Underlying symbol
    option_symbol: Optional[str]  # Option ticker/symbol
    strike: Decimal  # Strike price
    expiry: datetime  # Expiration date
    option_type: str = "call"  # Option type (call/put)

    # Price data
    bid: Optional[Decimal] = None  # Bid price
    ask: Optional[Decimal] = None  # Ask price
    last_price: Optional[Decimal] = None  # Last trade price
    mid_price: Optional[Decimal] = None  # Mid price (bid+ask)/2

    # Greeks and metrics
    implied_volatility: Optional[Decimal] = None  # Implied volatility
    delta: Optional[Decimal] = None  # Option delta
    gamma: Optional[Decimal] = None  # Option gamma
    theta: Optional[Decimal] = None  # Option theta
    vega: Optional[Decimal] = None  # Option vega

    # Liquidity metrics
    volume: Optional[int] = None  # Trading volume
    open_interest: Optional[int] = None  # Open interest

    # Calculated fields
    days_to_expiry: int = 0  # Days until expiration
    underlying_price: Optional[Decimal] = None  # Current underlying price
    moneyness: Moneyness = Moneyness.ATM  # Moneyness classification
    intrinsic_value: Optional[Decimal] = None  # Intrinsic value
    time_value: Optional[Decimal] = None  # Time value
    metadata: dict[str, Any] = field(default_factory=dict)  # Additional metadata

    def __post_init__(self):
        """Calculate derived fields after initialization."""
        # Calculate days to expiry
        if self.expiry:
            time_diff = self.expiry - datetime.utcnow()
            self.days_to_expiry = max(0, time_diff.days)

        # Calculate mid price if not provided
        if self.mid_price is None and self.bid is not None and self.ask is not None:
            self.mid_price = (self.bid + self.ask) / Decimal("2")

        # Calculate moneyness
        if self.underlying_price is not None:
            moneyness_ratio = self.strike / self.underlying_price
            if moneyness_ratio < Decimal("0.95"):
                self.moneyness = Moneyness.DEEP_ITM
            elif moneyness_ratio < Decimal("0.98"):
                self.moneyness = Moneyness.ITM
            elif moneyness_ratio <= Decimal("1.02"):
                self.moneyness = Moneyness.ATM
            elif moneyness_ratio <= Decimal("1.05"):
                self.moneyness = Moneyness.OTM
            else:
                self.moneyness = Moneyness.DEEP_OTM

            # Calculate intrinsic value for call
            intrinsic = max(Decimal("0"), self.underlying_price - self.strike)
            self.intrinsic_value = intrinsic

            # Calculate time value
            if self.mid_price is not None:
                self.time_value = max(Decimal("0"), self.mid_price - intrinsic)


@dataclass
class OptionScreeningCriteria:
    """Screening criteria for covered call options."""

    # Days to expiry
    min_days_to_expiry: int = 30
    max_days_to_expiry: int = 45

    # Moneyness (as decimal, e.g., 0.02 = 2% OTM)
    min_moneyness: Decimal = Decimal("0.02")  # 2% OTM minimum
    max_moneyness: Decimal = Decimal("0.05")  # 5% OTM maximum

    # Premium
    min_premium: Decimal = Decimal("0.01")  # Minimum 1% premium

    # Liquidity
    min_open_interest: int = 100  # Minimum open interest
    min_volume: int = 10  # Minimum daily volume

    # Greeks (optional)
    target_delta: Optional[Decimal] = None  # Target delta (e.g., 0.30)
    max_theta_decay: Optional[Decimal] = None  # Maximum theta decay

    # Risk management
    avoid_earnings: bool = True  # Avoid options before earnings
    avoid_events: bool = True  # Avoid options before major events


@dataclass
class OptionScreenerResult:
    """Result of option screening operation."""

    symbol: str  # Underlying symbol
    underlying_price: Decimal  # Current price
    options_passed: list[CallOption]  # Options that passed screening
    options_failed: dict[str, list[str]]  # Options that failed with reasons
    total_evaluated: int  # Total options evaluated
    screening_time_ms: float  # Screening time in milliseconds
    criteria: OptionScreeningCriteria  # Criteria used for screening

    @property
    def pass_rate(self) -> float:
        """Calculate the percentage of options that passed screening."""
        if self.total_evaluated == 0:
            return 0.0
        return (len(self.options_passed) / self.total_evaluated) * 100.0

    @property
    def best_option(self) -> Optional[CallOption]:
        """Get the best option from passed options."""
        if not self.options_passed:
            return None
        # Return option with highest premium (could use other criteria)
        return max(self.options_passed, key=lambda opt: opt.mid_price or Decimal("0"))


@dataclass
class OnChainMetrics:
    """
    On-chain metrics for cryptocurrency assets.

    Captures blockchain-specific data that provides insight into
    network health, adoption, and market sentiment for crypto assets.

    Attributes:
        symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
        active_addresses: Number of active addresses on the network
        transaction_count: Number of transactions in the period
        transaction_volume: Total transaction volume in native units
        nvt_ratio: Network Value to Transactions ratio
        network_health_score: Pre-calculated network health score (0-100)
        hash_rate: Network hash rate (for PoW coins)
        staking_ratio: Percentage of supply being staked (for PoS coins)
        token_velocity: Token velocity metric
        timestamp: When these metrics were recorded
    """

    symbol: str
    active_addresses: Optional[int] = None
    transaction_count: Optional[int] = None
    transaction_volume: Optional[Decimal] = None
    nvt_ratio: Optional[Decimal] = None
    network_health_score: Optional[Decimal] = None
    hash_rate: Optional[Decimal] = None
    staking_ratio: Optional[Decimal] = None
    token_velocity: Optional[Decimal] = None
    timestamp: Optional[datetime] = None


class CryptoAssetType(str, Enum):
    """Types of cryptocurrency assets."""

    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    STABLECOIN = "stablecoin"
    DEFI = "defi"
    L1_BLOCKCHAIN = "l1_blockchain"
    L2_SCALING = "l2_scaling"
    UTILITY = "utility"
    EXCHANGE = "exchange"
    NFT_PLATFORM = "nft_platform"
    MEME = "meme"
    PRIVACY = "privacy"
    OTHER = "other"


class CryptoExchange(str, Enum):
    """Cryptocurrency exchanges."""

    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    BITSTAMP = "bitstamp"
    GEMINI = "gemini"
    BITFINEX = "bitfinex"
    OKEX = "okex"
    HUOBI = "huobi"
    KUCOIN = "kucoin"


@dataclass
class CryptoAsset:
    """
    Cryptocurrency asset representation.

    Captures essential data for crypto assets including market data,
    listing information, and crypto-specific metrics.

    Attributes:
        symbol: Trading symbol (e.g., 'BTC', 'ETH')
        name: Full name of the cryptocurrency
        asset_type: Type classification of the asset
        market_cap: Current market capitalization in USD
        price: Current price in USD
        avg_daily_volume: Average daily trading volume in USD
        exchanges: List of exchanges where asset is listed
        btc_correlation: Correlation with Bitcoin price
        volatility_30d: 30-day volatility
        circulating_supply: Circulating supply
        total_supply: Total supply
    """

    symbol: str
    name: str
    asset_type: CryptoAssetType
    market_cap: Decimal
    price: Decimal
    avg_daily_volume: Decimal
    exchanges: list[CryptoExchange]
    btc_correlation: Optional[float] = None
    volatility_30d: Optional[Decimal] = None
    circulating_supply: Optional[Decimal] = None
    total_supply: Optional[Decimal] = None


@dataclass
class CryptoScreeningResult:
    """
    Result of crypto asset screening operation.

    Attributes:
        passed_assets: Assets that passed all screening criteria
        failed_assets: Assets that failed with reasons
        total_evaluated: Total number of assets evaluated
        screening_time_ms: Time taken for screening in milliseconds
        min_market_cap: Minimum market cap used for screening
        min_daily_volume: Minimum daily volume used for screening
        min_liquidity_score: Minimum liquidity score used for screening
    """

    passed_assets: list[CryptoAsset]
    failed_assets: dict[str, list[str]]
    total_evaluated: int
    screening_time_ms: float
    min_market_cap: Optional[Decimal] = None
    min_daily_volume: Optional[Decimal] = None
    min_liquidity_score: Optional[Decimal] = None


@dataclass
class CryptoMomentumConfig:
    """
    Configuration for crypto momentum strategy.

    Attributes:
        min_market_cap: Minimum market cap for consideration
        min_volume: Minimum daily volume
        max_volatility: Maximum acceptable volatility
        momentum_period_days: Lookback period for momentum calculation
        rebalance_frequency: How often to rebalance
        max_position_size: Maximum position size as decimal
    """

    min_market_cap: Decimal = Decimal("100000000")
    min_volume: Decimal = Decimal("1000000")
    max_volatility: Decimal = Decimal("2.0")
    momentum_period_days: int = 30
    rebalance_frequency: str = "weekly"
    max_position_size: Decimal = Decimal("0.1")


@dataclass
class CryptoMomentumScore:
    """
    Momentum score for a crypto asset.

    Attributes:
        symbol: Asset symbol
        raw_momentum: Raw momentum score
        final_score: Final weighted score
        confidence: Confidence level of the score
        price_momentum: Price momentum score
        volume_momentum: Volume momentum score
        on_chain_momentum: On-chain activity momentum
        social_momentum: Social sentiment momentum
        composite_score: Weighted composite score
        rank: Ranking within universe
    """

    symbol: str
    raw_momentum: Decimal
    final_score: Decimal
    confidence: Decimal
    volatility_adjusted_momentum: Optional[Decimal] = None
    btc_adjusted_momentum: Optional[Decimal] = None
    price_momentum: Optional[Decimal] = None
    volume_momentum: Optional[Decimal] = None
    on_chain_momentum: Optional[Decimal] = None
    social_momentum: Optional[Decimal] = None
    composite_score: Optional[Decimal] = None
    rank: Optional[int] = None


@dataclass
class CryptoPortfolio:
    """
    Crypto portfolio representation.

    Attributes:
        positions: Current positions
        total_value: Total portfolio value in USD
        btc_weight: Weight of Bitcoin
        eth_weight: Weight of Ethereum
        altcoin_weight: Weight of altcoins
        cash_weight: Cash/stablecoin weight
        last_rebalanced: When portfolio was last rebalanced
    """

    positions: dict[str, Decimal]
    total_value: Decimal
    btc_weight: Decimal
    eth_weight: Decimal
    altcoin_weight: Decimal
    cash_weight: Decimal
    last_rebalanced: Optional[datetime] = None


class RollType(str, Enum):
    """Types of covered call roll operations."""

    ROLL_OUT = "roll_out"  # Extend to later expiry
    ROLL_UP = "roll_up"  # Roll to higher strike
    ROLL_DOWN = "roll_down"  # Roll to lower strike
    ROLL_OUT_UP = "roll_out_up"  # Extend expiry and higher strike
    ROLL_OUT_DOWN = "roll_out_down"  # Extend expiry and lower strike
    CLOSE = "close"  # Close position without rolling


@dataclass
class CoveredCallConfig:
    """
    Configuration for covered call strategy.

    Attributes:
        min_premium: Minimum premium to collect
        min_days_to_expiry: Minimum days to expiry
        max_days_to_expiry: Maximum days to expiry
        target_delta: Target delta for option selection
        max_position_size: Maximum position size
        roll_threshold: Threshold for rolling (as decimal of strike)
        assignment_buffer: Buffer before assignment risk
    """

    min_premium: Decimal = Decimal("0.01")
    min_days_to_expiry: int = 30
    max_days_to_expiry: int = 45
    target_delta: Decimal = Decimal("0.30")
    max_position_size: Decimal = Decimal("0.05")
    roll_threshold: Decimal = Decimal("0.02")
    assignment_buffer: int = 7


@dataclass
class CoveredCallPosition:
    """
    Covered call position representation.

    Attributes:
        symbol: Underlying symbol
        shares: Number of shares owned
        strike: Option strike price
        expiry: Option expiration date
        premium_received: Premium received per share
        contracts: Number of contracts
        position_value: Current position value
        unrealized_pnl: Unrealized profit/loss
        status: Current position status
    """

    symbol: str
    shares: int
    strike: Decimal
    expiry: datetime
    premium_received: Decimal
    contracts: int
    position_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    status: str = "active"


@dataclass
class RollDecision:
    """
    Decision on whether to roll a covered call position.

    Attributes:
        should_roll: Whether to roll the position
        roll_type: Type of roll to execute
        new_strike: New strike price (if rolling)
        new_expiry: New expiration date (if rolling)
        estimated_credit: Estimated credit/debit for roll
        reasoning: Reasoning behind the decision
    """

    should_roll: bool
    roll_type: Optional[RollType] = None
    new_strike: Optional[Decimal] = None
    new_expiry: Optional[datetime] = None
    estimated_credit: Optional[Decimal] = None
    reasoning: str = ""


@dataclass
class RollOpportunity:
    """
    Roll opportunity for a covered call position.

    Attributes:
        current_position: Current covered call position
        current_price: Current underlying price
        roll_type: Type of roll
        new_strike: New strike price
        new_expiry: New expiration date
        estimated_credit: Estimated credit from roll
        annualized_return: Estimated annualized return
        days_to_expiry: Days to new expiry
        probability_itm: Probability of finishing in the money
    """

    current_position: CoveredCallPosition
    current_price: Decimal
    roll_type: RollType
    new_strike: Decimal
    new_expiry: datetime
    estimated_credit: Decimal
    annualized_return: Optional[Decimal] = None
    days_to_expiry: Optional[int] = None
    probability_itm: Optional[Decimal] = None
