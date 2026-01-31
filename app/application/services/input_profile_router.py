"""
InputProfile Router - Maps InputProfile to System Configuration

This service routes the InputProfile to the appropriate strategy,
risk configuration, and system settings.

This is a CRITICAL component for autonomous system operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from app.domain.models.input_profile import (
    InputProfile,
    InvestmentObjective,
    RiskTolerance,
)
from app.domain.value_objects.investment_horizon import InvestmentHorizon
from app.domain.value_objects.tax_residence import TaxResidence


class StrategyType(str, Enum):
    """Strategy types mapped from investment objectives."""

    MOMENTUM = "momentum"  # MAXIMIZAR_CAPITAL
    DIVIDEND = "dividend"  # MAXIMIZAR_DIVIDENDOS
    LOW_VOLATILITY = "low_volatility"  # CAPITAL_PRESERVATION
    MULTI_FACTOR = "multi_factor"  # BALANCED_GROWTH
    MEAN_REVERSION = "mean_reversion"  # Neutral/Balanced
    PAIRS_TRADING = "pairs_trading"  # Market neutral
    QUALITY = "quality"  # Long-term quality
    COVERED_CALL = "covered_call"  # INCOME_GENERATION


class OptimizationType(str, Enum):
    """Portfolio optimization types."""

    MEAN_VARIANCE = "mean_variance"  # Markowitz MVO
    HIERARCHICAL_RISK_PARITY = "hrp"  # HRP
    NESTED_CLUSTERED = "nco"  # NCO
    BLACK_LITTERMAN = "black_litterman"  # BL
    RISK_PARITY = "risk_parity"  # Inverse volatility
    EQUAL_WEIGHT = "equal_weight"  # Simple equal weight


class RebalancingFrequency(str, Enum):
    """Rebalancing frequencies."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


@dataclass
class RiskConfig:
    """Risk configuration derived from risk tolerance."""

    max_drawdown: Decimal  # Maximum drawdown allowed
    max_volatility: Decimal  # Maximum annualized volatility
    max_position_size: Decimal  # Maximum single position size
    leverage_allowed: bool  # Whether leverage is allowed
    max_leverage: Decimal  # Maximum leverage ratio
    stop_loss_atr_multiplier: Decimal  # ATR multiplier for stop loss
    take_profit_atr_multiplier: Decimal  # ATR multiplier for take profit
    var_confidence: float  # VaR confidence level (0.95, 0.99)
    expected_shortfall_confidence: float  # ES confidence level


@dataclass
class OptimizationConfig:
    """Portfolio optimization configuration."""

    optimization_type: OptimizationType
    lookback_period: int  # Days for covariance calculation
    rebalance_frequency: RebalancingFrequency
    min_weight: Decimal  # Minimum position weight
    max_weight: Decimal  # Maximum position weight
    max_turnover: Decimal  # Maximum portfolio turnover
    target_portfolio_volatility: Optional[Decimal]  # Target volatility for volatility targeting


@dataclass
class TaxConfig:
    """Tax configuration based on residence."""

    country: str
    method: str  # FIFO, LIFO, HIFO, etc.
    dividend_tax_rate: Decimal  # Dividend tax rate
    capital_gains_tax_rate: Decimal  # Capital gains tax rate
    short_term_holding_period: int  # Days for short-term classification
    tax_loss_harvesting: bool  # Whether to use tax loss harvesting
    witholding_tax_rate: Decimal  # Withholding tax on dividends


@dataclass
class SystemConfiguration:
    """Complete system configuration from InputProfile."""

    input_profile: InputProfile
    strategy_type: StrategyType
    risk_config: RiskConfig
    optimization_config: OptimizationConfig
    tax_config: TaxConfig

    # Additional constraints
    max_positions: int
    min_liquidity_score: float
    sector_diversification_required: bool
    max_sector_exposure: Decimal
    long_only: bool


class InputProfileRouter:
    """
    InputProfile Router - Maps InputProfile to SystemConfiguration.

    This is the KEY insight - InputProfile drives EVERYTHING in the system.
    The router automatically determines:
    1. Which strategy to use
    2. Risk parameters
    3. Portfolio optimization method
    4. Tax handling
    5. All constraints

    Reference: AUDIT_PLAN_COMPLETO.md sections 4-6
    """

    def __call__(self, profile: InputProfile) -> SystemConfiguration:
        """
        Generate complete system configuration from InputProfile.

        Args:
            profile: User's InputProfile

        Returns:
            Complete SystemConfiguration
        """
        # 1. Select strategy type from investment objective
        strategy_type = self._select_strategy_type(profile.objective)

        # 2. Select risk configuration from risk tolerance
        risk_config = self._select_risk_config(profile.risk_tolerance)

        # 3. Select optimization configuration from horizon and capital
        optimization_config = self._select_optimization_config(
            profile.horizon,
            profile.risk_tolerance,
        )

        # 4. Create tax configuration from residence
        tax_config = self._create_tax_config(profile.tax_residence)

        # 5. Generate additional constraints
        constraints = self._generate_constraints(profile)

        return SystemConfiguration(
            input_profile=profile,
            strategy_type=strategy_type,
            risk_config=risk_config,
            optimization_config=optimization_config,
            tax_config=tax_config,
            **constraints,
        )

    def _select_strategy_type(self, objective: InvestmentObjective) -> StrategyType:
        """
        Select strategy type from investment objective.

        Mapping:
        - MAXIMIZAR_CAPITAL -> Momentum (aggressive growth)
        - MAXIMIZAR_DIVIDENDOS -> Dividend
        - CAPITAL_PRESERVATION -> Low Volatility
        - BALANCED_GROWTH -> Multi-Factor
        - INCOME_GENERATION -> Covered Call
        """
        strategy_map = {
            InvestmentObjective.MAXIMIZAR_CAPITAL: StrategyType.MOMENTUM,
            InvestmentObjective.MAXIMIZAR_DIVIDENDOS: StrategyType.DIVIDEND,
            InvestmentObjective.CAPITAL_PRESERVATION: StrategyType.LOW_VOLATILITY,
            InvestmentObjective.BALANCED_GROWTH: StrategyType.MULTI_FACTOR,
            InvestmentObjective.INCOME_GENERATION: StrategyType.COVERED_CALL,
        }
        return strategy_map.get(objective, StrategyType.MULTI_FACTOR)

    def _select_risk_config(self, tolerance: RiskTolerance) -> RiskConfig:
        """
        Select risk configuration from risk tolerance.

        Mapping:
        - BAJO -> 15% max drawdown, no leverage, 5% max position
        - MEDIO -> 25% max drawdown, 1.5x leverage, 10% max position
        - ALTO -> 40% max drawdown, 2x leverage, 20% max position
        """
        if tolerance == RiskTolerance.BAJO:
            return RiskConfig(
                max_drawdown=Decimal("0.15"),  # 15%
                max_volatility=Decimal("0.20"),  # 20%
                max_position_size=Decimal("0.05"),  # 5%
                leverage_allowed=False,
                max_leverage=Decimal("1.0"),
                stop_loss_atr_multiplier=Decimal("2.0"),
                take_profit_atr_multiplier=Decimal("3.0"),
                var_confidence=0.95,
                expected_shortfall_confidence=0.95,
            )
        elif tolerance == RiskTolerance.MEDIO:
            return RiskConfig(
                max_drawdown=Decimal("0.25"),  # 25%
                max_volatility=Decimal("0.30"),  # 30%
                max_position_size=Decimal("0.10"),  # 10%
                leverage_allowed=True,
                max_leverage=Decimal("1.5"),
                stop_loss_atr_multiplier=Decimal("2.5"),
                take_profit_atr_multiplier=Decimal("4.0"),
                var_confidence=0.95,
                expected_shortfall_confidence=0.95,
            )
        else:  # ALTO
            return RiskConfig(
                max_drawdown=Decimal("0.40"),  # 40%
                max_volatility=Decimal("0.50"),  # 50%
                max_position_size=Decimal("0.20"),  # 20%
                leverage_allowed=True,
                max_leverage=Decimal("2.0"),
                stop_loss_atr_multiplier=Decimal("3.0"),
                take_profit_atr_multiplier=Decimal("6.0"),
                var_confidence=0.99,
                expected_shortfall_confidence=0.975,
            )

    def _select_optimization_config(
        self,
        horizon: InvestmentHorizon,
        tolerance: RiskTolerance,
    ) -> OptimizationConfig:
        """
        Select optimization configuration from horizon and tolerance.

        Rules:
        - Short horizon (< 12 months) -> Equal weight or Risk Parity
        - Medium horizon (12-60 months) -> HRP or NCO
        - Long horizon (> 60 months) -> MVO or Black-Litterman
        - Low tolerance -> More conservative optimization
        """
        # Determine lookback period based on horizon
        if horizon.months < 12:
            lookback = 63  # 3 months
            rebalance = RebalancingFrequency.WEEKLY
            opt_type = OptimizationType.EQUAL_WEIGHT
        elif horizon.months < 60:
            lookback = 126  # 6 months
            rebalance = RebalancingFrequency.MONTHLY
            opt_type = OptimizationType.HIERARCHICAL_RISK_PARITY
        else:
            lookback = 252  # 1 year
            rebalance = RebalancingFrequency.QUARTERLY
            opt_type = OptimizationType.MEAN_VARIANCE

        # Adjust for risk tolerance
        if tolerance == RiskTolerance.BAJO:
            opt_type = OptimizationType.RISK_PARITY
            min_weight = Decimal("0.01")
            max_weight = Decimal("0.05")
        elif tolerance == RiskTolerance.ALTO:
            min_weight = Decimal("0.02")
            max_weight = Decimal("0.20")
        else:
            min_weight = Decimal("0.02")
            max_weight = Decimal("0.10")

        return OptimizationConfig(
            optimization_type=opt_type,
            lookback_period=lookback,
            rebalance_frequency=rebalance,
            min_weight=min_weight,
            max_weight=max_weight,
            max_turnover=Decimal("0.50"),  # 50% max turnover
            target_portfolio_volatility=None,
        )

    def _create_tax_config(self, residence: TaxResidence) -> TaxConfig:
        """
        Create tax configuration from tax residence.

        Supports:
        - Spain: FIFO, 19-28% dividend tax, 19-28% capital gains
        - USA: LIFO/HIFO, 15-20% dividend tax, 15-20% capital gains
        - UK: FIFO, 0-38.1% dividend tax, 10-28% capital gains
        """
        country = residence.country

        if country == "Spain":
            return TaxConfig(
                country="Spain",
                method="FIFO",
                dividend_tax_rate=Decimal("0.19"),  # 19% standard rate
                capital_gains_tax_rate=Decimal("0.19"),
                short_term_holding_period=365,  # 1 year
                tax_loss_harvesting=True,
                witholding_tax_rate=Decimal("0.19"),
            )
        elif country == "USA":
            return TaxConfig(
                country="USA",
                method="HIFO",  # Highest In, First Out
                dividend_tax_rate=Decimal("0.15"),  # 15% qualified dividends
                capital_gains_tax_rate=Decimal("0.15"),  # 15% long-term
                short_term_holding_period=365,  # 1 year for long-term
                tax_loss_harvesting=True,
                witholding_tax_rate=Decimal("0.0"),  # No withholding on US stocks
            )
        elif country == "UK":
            return TaxConfig(
                country="UK",
                method="FIFO",
                dividend_tax_rate=Decimal("0.0875"),  # 8.75% basic rate
                capital_gains_tax_rate=Decimal("0.10"),  # 10% basic rate
                short_term_holding_period=0,  # No distinction
                tax_loss_harvesting=True,
                witholding_tax_rate=Decimal("0.0"),
            )
        else:  # Default
            return TaxConfig(
                country=country,
                method="FIFO",
                dividend_tax_rate=Decimal("0.15"),
                capital_gains_tax_rate=Decimal("0.15"),
                short_term_holding_period=365,
                tax_loss_harvesting=True,
                witholding_tax_rate=Decimal("0.15"),
            )

    def _generate_constraints(self, profile: InputProfile) -> Dict[str, Any]:
        """
        Generate additional constraints from InputProfile.

        Constraints include:
        - Maximum positions
        - Minimum liquidity
        - Sector diversification
        - Long-only vs long-short
        """
        # Max positions based on capital
        capital = float(profile.capital.amount)
        if capital < 10000:
            max_positions = 10
        elif capital < 100000:
            max_positions = 25
        else:
            max_positions = 50

        # Liquidity requirements
        min_liquidity = 0.5 if capital < 50000 else 0.7

        # Sector diversification
        sector_diversification = profile.risk_tolerance in (
            RiskTolerance.BAJO,
            RiskTolerance.MEDIO,
        )

        # Sector exposure limits
        if profile.risk_tolerance == RiskTolerance.BAJO:
            max_sector = Decimal("0.25")  # 25% max per sector
        else:
            max_sector = Decimal("0.40")  # 40% max per sector

        # Long-only for capital preservation and dividend objectives
        long_only = profile.objective in (
            InvestmentObjective.CAPITAL_PRESERVATION,
            InvestmentObjective.MAXIMIZAR_DIVIDENDOS,
        )

        return {
            "max_positions": max_positions,
            "min_liquidity_score": min_liquidity,
            "sector_diversification_required": sector_diversification,
            "max_sector_exposure": max_sector,
            "long_only": long_only,
        }

    def get_strategy_config(
        self,
        profile: InputProfile,
    ) -> Dict[str, Any]:
        """
        Get strategy-specific configuration.

        Args:
            profile: User's InputProfile

        Returns:
            Dictionary of strategy configuration parameters
        """
        config = self(profile)
        strategy_type = config.strategy_type

        # Base configuration
        strategy_config = {
            "strategy_type": strategy_type.value,
            "risk_tolerance": profile.risk_tolerance.value,
            "investment_horizon_months": profile.horizon.months,
            "capital": float(profile.capital.amount),
            "currency": profile.capital.currency,
        }

        # Strategy-specific parameters
        if strategy_type == StrategyType.MOMENTUM:
            strategy_config.update(
                {
                    "lookback_period": 252,  # 12 months
                    "rebalance_frequency": "monthly",
                    "top_percentile": 0.3,
                    "bottom_percentile": 0.3,
                    "long_only": config.long_only,
                }
            )
        elif strategy_type == StrategyType.DIVIDEND:
            strategy_config.update(
                {
                    "min_yield": 0.02,
                    "max_yield": 0.10,
                    "min_dividend_growth": 0.0,
                    "max_payout_ratio": 0.8,
                    "min_dividend_years": 5,
                }
            )
        elif strategy_type == StrategyType.LOW_VOLATILITY:
            strategy_config.update(
                {
                    "max_beta": 0.8,
                    "max_volatility": 0.25,
                    "rebalance_frequency": "monthly",
                }
            )
        elif strategy_type == StrategyType.MULTI_FACTOR:
            strategy_config.update(
                {
                    "factor_weights": {
                        "value": 0.25,
                        "size": 0.25,
                        "momentum": 0.25,
                        "quality": 0.25,
                    },
                    "rebalance_frequency": "quarterly",
                }
            )

        # Add risk parameters
        strategy_config.update(
            {
                "max_drawdown": float(config.risk_config.max_drawdown),
                "max_position_size": float(config.risk_config.max_position_size),
                "leverage_allowed": config.risk_config.leverage_allowed,
                "max_leverage": float(config.risk_config.max_leverage),
                "stop_loss_atr_multiplier": float(config.risk_config.stop_loss_atr_multiplier),
                "take_profit_atr_multiplier": float(config.risk_config.take_profit_atr_multiplier),
            }
        )

        return strategy_config
