"""
Backtesting Configuration

Extracted from centralized_config.py for SRP compliance.
Contains BacktestingConfig and CommissionModels.

TASK-10: Centralización de Configuración
TASK-24: SRP Refactoring
"""

import logging
from decimal import Decimal
from typing import Dict, List

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class CommissionModel(BaseModel):
    """Commission model configuration."""

    type: str = Field(description="Commission type: fixed, hybrid, or tiered")
    description: str = Field(default="", description="Description of this commission model")


class FixedCommission(CommissionModel):
    """Fixed commission model."""

    type: str = "fixed"
    cost: Decimal = Field(description="Fixed cost per trade")


class HybridCommission(CommissionModel):
    """Hybrid commission model (rate + minimum)."""

    type: str = "hybrid"
    min_cost: Decimal = Field(description="Minimum cost per trade")
    rate: Decimal = Field(description="Commission rate as decimal (0.001 = 0.1%)")


class TierBracket(BaseModel):
    """Single tier bracket for tiered commission."""

    volume_max: float = Field(description="Maximum volume for this tier")
    rate: Decimal = Field(description="Commission rate for this tier")
    min: Decimal = Field(description="Minimum commission for this tier")


class TieredCommission(CommissionModel):
    """Tiered commission model."""

    type: str = "tiered"
    brackets: List[TierBracket] = Field(description="Commission brackets")


class BacktestingConfig(BaseModel):
    """
    Centralized backtesting configuration.

    This is THE SINGLE SOURCE OF TRUTH for all backtesting parameters.
    All hardcoded values in backtesting modules should reference this config.

    Usage:
        from app.shared.config.centralized_config import get_config
        config = get_config()
        slippage = config.backtesting.base_slippage_bps
        commission = config.backtesting.default_commission_rate
    """

    # ========== SLIPPAGE SETTINGS ==========
    # Consolidated from constants.py ExecutionEngineConstants and TradingThresholds

    base_slippage_bps: Decimal = Field(
        default=Decimal("10"),  # 10 bps = 0.1% (standard market impact)
        description="Base slippage in basis points",
    )
    optimistic_slippage_bps: Decimal = Field(
        default=Decimal("2"),  # 2 bps for optimistic mode
        description="Optimistic slippage in basis points",
    )
    stop_slippage_multiplier: Decimal = Field(
        default=Decimal("2"),  # 2x slippage on stop orders (worse execution)
        description="Slippage multiplier for stop orders",
    )
    volatility_multiplier: Decimal = Field(
        default=Decimal("2"),  # 2x slippage for high volatility
        description="Slippage multiplier for high volatility conditions",
    )

    # ========== COMMISSION SETTINGS ==========
    # Consolidated from constants.py CapitalScaleConstants.COMMISSION_MODELS

    default_commission_rate: Decimal = Field(
        default=Decimal("0.001"),  # 0.1% standard commission
        description="Default commission rate as decimal",
    )
    default_commission_per_share: Decimal = Field(
        default=Decimal("0.005"),  # $0.005/share (IBKR-like)
        description="Default commission per share",
    )
    default_commission_fixed: Decimal = Field(
        default=Decimal("5.0"), description="Default fixed commission per trade"  # $5 flat fee
    )
    min_commission: Decimal = Field(
        default=Decimal("1.0"), description="Minimum commission per trade"  # $1 minimum
    )

    # ========== CAPITAL SCALE SETTINGS ==========
    # Consolidated from constants.py CapitalScaleConstants

    default_capital_levels: List[Decimal] = Field(
        default_factory=lambda: [
            Decimal("1000"),  # Micro
            Decimal("5000"),  # Small
            Decimal("10000"),  # Medium
            Decimal("50000"),  # Pro
            Decimal("100000"),  # Fund
        ],
        description="Default capital levels for scale analysis",
    )
    default_initial_capital: Decimal = Field(
        default=Decimal("100000"),  # $100K default
        description="Default initial capital for backtests",
    )

    # ADV (Average Daily Volume) settings
    adv_limit_pct: Decimal = Field(
        default=Decimal("0.02"), description="Maximum position as percentage of ADV"  # 2% ADV rule
    )
    adv_fill_ratio_reject_threshold: Decimal = Field(
        default=Decimal("0.5"),  # Reject if fill < 50%
        description="Minimum fill ratio before rejecting",
    )

    # Commission impact thresholds
    commission_impact_warning_threshold: Decimal = Field(
        default=Decimal("0.15"),  # 15% - trigger warning
        description="Commission impact percentage to trigger warning",
    )
    commission_impact_critical_threshold: Decimal = Field(
        default=Decimal("0.20"),  # 20% - reject strategy
        description="Commission impact percentage to reject strategy",
    )

    # Alpha degradation
    alpha_degradation_threshold: Decimal = Field(
        default=Decimal("0.50"),  # 50% degradation max acceptable
        description="Maximum acceptable alpha degradation",
    )

    # ========== EXECUTION SETTINGS ==========

    enable_next_day_execution: bool = Field(
        default=True, description="Signal at close t, execute at open t+1"
    )
    max_execution_time_ms: int = Field(
        default=500, description="Maximum execution time in milliseconds"
    )

    # ========== POSITION SIZING ==========
    # Consolidated from multiple sources

    default_max_position_size: Decimal = Field(
        default=Decimal("0.10"),  # 10% max position
        description="Default maximum position size as decimal",
    )
    default_min_position_size: Decimal = Field(
        default=Decimal("0.01"),  # 1% min position
        description="Default minimum position size as decimal",
    )

    # Position limits by capital tier
    position_limits_by_tier: Dict[str, Decimal] = Field(
        default_factory=lambda: {
            "micro": Decimal("0.02"),  # 2% for micro accounts
            "small": Decimal("0.05"),  # 5% for small accounts
            "medium": Decimal("0.10"),  # 10% for medium accounts
            "large": Decimal("0.15"),  # 15% for large accounts
        },
        description="Maximum position size by capital tier",
    )

    # ========== SCALABILITY SCORING ==========

    scalability_alpha_max_points: Decimal = Field(
        default=Decimal("40"), description="Maximum points for alpha degradation score"
    )
    scalability_commission_max_points: Decimal = Field(
        default=Decimal("30"), description="Maximum points for commission impact score"
    )
    scalability_stability_max_points: Decimal = Field(
        default=Decimal("30"), description="Maximum points for win rate stability score"
    )

    # ========== RISK MANAGEMENT DEFAULTS ==========

    default_stop_loss_pct: Decimal = Field(
        default=Decimal("0.05"), description="Default stop loss percentage"  # 5% stop loss
    )
    default_take_profit_pct: Decimal = Field(
        default=Decimal("0.15"), description="Default take profit percentage"  # 15% take profit
    )
    default_risk_free_rate: Decimal = Field(
        default=Decimal("0.02"),  # 2% annual risk-free rate
        description="Default risk-free rate for Sharpe calculation",
    )
    annual_trading_days: int = Field(
        default=252, description="Number of trading days in a year for annualization"
    )
    default_daily_loss_limit: Decimal = Field(
        default=Decimal("0.05"), description="Default daily loss limit"  # 5% daily loss limit
    )

    # ========== PERFORMANCE METRICS ==========

    min_trades_for_statistics: int = Field(
        default=10, description="Minimum trades required for reliable statistics"
    )
    min_sharpe_ratio: Decimal = Field(
        default=Decimal("0.5"), description="Minimum acceptable Sharpe ratio"
    )
    max_acceptable_drawdown: Decimal = Field(
        default=Decimal("0.25"), description="Maximum acceptable drawdown"  # 25% max drawdown
    )

    # ========== DATA SETTINGS ==========

    default_start_date: str = Field(default="2018-01-01", description="Default backtest start date")
    default_end_date: str = Field(default="2023-12-31", description="Default backtest end date")

    # ========== URLs (External APIs) ==========

    yahoo_finance_base_url: str = Field(
        default="https://query1.finance.yahoo.com/v8/finance/chart",
        description="Yahoo Finance API base URL",
    )

    @field_validator("base_slippage_bps", "optimistic_slippage_bps")
    @classmethod
    def validate_slippage_bps(cls, v):
        if v < 0:
            raise ValueError("Slippage must be non-negative")
        return v

    @field_validator("default_commission_rate", "default_commission_per_share")
    @classmethod
    def validate_commission(cls, v):
        if v < 0:
            raise ValueError("Commission must be non-negative")
        return v

    def get_slippage_pct(self, is_stop: bool = False, is_volatile: bool = False) -> Decimal:
        """
        Calculate slippage percentage based on conditions.

        Args:
            is_stop: True if this is a stop order (worse execution)
            is_volatile: True if market is volatile

        Returns:
            Slippage as decimal percentage (e.g., 0.001 = 0.1%)
        """
        slippage = self.base_slippage_bps / Decimal("10000")  # Convert bps to decimal

        if is_stop:
            slippage *= self.stop_slippage_multiplier
        if is_volatile:
            slippage *= self.volatility_multiplier

        return slippage

    def get_commission_for_capital(self, capital: Decimal) -> Decimal:
        """
        Get appropriate commission rate based on capital level.

        Args:
            capital: Account capital

        Returns:
            Commission rate as decimal
        """
        if capital <= Decimal("5000"):
            return self.default_commission_fixed  # Fixed fee for small accounts
        elif capital <= Decimal("50000"):
            return self.default_commission_rate  # Standard rate
        else:
            return self.default_commission_rate * Decimal("0.5")  # Discount for large accounts

    def get_position_limit_for_capital(self, capital: Decimal) -> Decimal:
        """
        Get maximum position size based on capital tier.

        Args:
            capital: Account capital

        Returns:
            Maximum position size as decimal
        """
        if capital <= Decimal("5000"):
            return self.position_limits_by_tier["micro"]
        elif capital <= Decimal("20000"):
            return self.position_limits_by_tier["small"]
        elif capital <= Decimal("100000"):
            return self.position_limits_by_tier["medium"]
        else:
            return self.position_limits_by_tier["large"]


# Backwards compatibility aliases (reference BacktestingConfig)
BACKTESTING_CONSTANTS = None  # Will be set after CentralizedConfig instantiation


def get_backtesting_constants() -> "BacktestingConfig":
    """Get backtesting constants from centralized config."""
    global BACKTESTING_CONSTANTS
    if BACKTESTING_CONSTANTS is None:
        BACKTESTING_CONSTANTS = get_config().backtesting
    return BACKTESTING_CONSTANTS
