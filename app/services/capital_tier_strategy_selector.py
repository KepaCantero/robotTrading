"""
PHASE 1 T1.1 - Capital Tier Strategy Selector

Maps account capital → optimal strategy configuration, risk profile, and feature enablement.

This service is the single source of truth for capital tier-based decisions:
- Which strategies to use
- Which ML modules to enable
- What risk profile to apply
- How to configure learning infrastructure

Architecture:
Integrates with:
- AccountConfiguration: Tier definitions and base recommendations
- DeploymentValidator: Safety gating and validation
- StrategyFactory/Registry: Strategy instantiation
- ExpensiveModuleGate: ML feature gating
- LearningCapitalGate: Learning viability checking
- RiskEngine: Risk configuration

Design Principles:
1. Single Source of Truth: Capital tier is THE source of truth
2. Conservative Defaults: Disable features when in doubt (fail-safe)
3. Graceful Degradation: System works even if features disabled
4. Audit Trail: Every decision logged with reasoning
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import ClassVar, Optional

from app.services.account_configuration import AccountConfiguration, AccountTier
from app.services.deployment_validator import DeploymentStatus, DeploymentValidator
from app.services.expensive_module_gate import ExpensiveModuleGate
from app.services.learning_capital_gate import LearningCapitalGate
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


def _get_tier_config_defaults():
    """Get default tier configuration values from centralized config."""
    tt = get_config().trading_thresholds
    return {
        "position_size_pct": Decimal(str(tt.tier_default_position_size)),
        "max_daily_loss_pct": Decimal(str(tt.tier_default_max_daily_loss)),
        "micro_max_drawdown": Decimal(str(tt.tier_micro_max_drawdown)),
        "small_max_drawdown": Decimal(str(tt.tier_small_max_drawdown)),
    }


class EnsembleType(str, Enum):
    """Types of ensemble strategies available"""

    WEIGHTED = "weighted"
    REGIME_BASED = "regime_based"
    VOTING = "voting"
    NONE = "none"  # For non-ensemble (single strategy)


class PositionSizingStrategy(str, Enum):
    """Position sizing strategies per tier"""

    FIXED_PCT = "fixed_pct"  # Fixed % of capital
    KELLY_CRITERION = "kelly_criterion"  # Kelly-based sizing
    VOLATILITY_ADJUSTED = "volatility_adjusted"  # Adjusted for volatility
    RISK_PARITY = "risk_parity"  # Risk parity across positions


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class StrategySelection:
    """
    What strategies to use for this capital tier.

    Attributes:
        primary_strategy: Name of primary strategy (e.g., "momentum_engine")
        secondary_strategies: Names of fallback strategies
        ensemble_type: Type of ensemble (weighted, regime_based, voting, none)
        config_variant: Risk variant (conservative, balanced, aggressive)
        reasoning: Explanation of why this selection was made
        tier: Account tier this selection is for
    """

    primary_strategy: str
    secondary_strategies: list[str]
    ensemble_type: EnsembleType
    config_variant: str
    reasoning: str
    tier: str = ""


@dataclass
class RiskProfile:
    """
    Risk limits appropriate for this capital tier.

    Attributes:
        tier: Account tier (micro, small, medium, large)
        max_position_size: Maximum position size as % of capital
        max_concurrent_trades: Maximum number of simultaneous trades
        max_daily_loss_pct: Maximum daily loss as % of capital
        max_drawdown_pct: Maximum drawdown tolerance
        leverage_allowed: Leverage multiplier allowed (1.0 = no leverage)
        learning_enabled: Whether ML learning is enabled
        modules_enabled: Dict of which ML modules are available
        position_sizing_strategy: How positions should be sized
    """

    tier: str
    max_position_size: Decimal
    max_concurrent_trades: int
    max_daily_loss_pct: Decimal
    max_drawdown_pct: Decimal
    leverage_allowed: Decimal
    learning_enabled: bool
    modules_enabled: dict[str, bool]
    position_sizing_strategy: PositionSizingStrategy

    # Risk parameter validations
    def validate(self) -> tuple[bool, str]:
        """Validate risk profile parameters"""
        if self.max_position_size <= Decimal("0"):
            return False, "max_position_size must be > 0"
        if self.max_position_size > Decimal("1"):
            return False, "max_position_size cannot exceed 100%"
        if self.max_concurrent_trades < 1:
            return False, "max_concurrent_trades must be >= 1"
        if self.max_daily_loss_pct <= Decimal("0"):
            return False, "max_daily_loss_pct must be > 0"
        if self.max_drawdown_pct <= Decimal("0"):
            return False, "max_drawdown_pct must be > 0"
        if self.leverage_allowed < Decimal("1"):
            return False, "leverage_allowed must be >= 1.0"
        return True, "Risk profile valid"


@dataclass
class StrategyCapabilities:
    """
    Features and capabilities available at this capital tier.

    Attributes:
        learning: Whether ML learning is available
        transfer_learning: Whether transfer learning is available
        deep_learning: Whether deep learning modules are available
        transformer_models: Whether transformer models are available
        ensemble_methods: Whether ensemble methods are available
        hyperparameter_optimization: Whether hyperparameter optimization is available
        feature_importance_analysis: Whether feature importance analysis is available
        advanced_risk_management: Whether advanced risk features are available
    """

    learning: bool
    transfer_learning: bool
    deep_learning: bool
    transformer_models: bool
    ensemble_methods: bool
    hyperparameter_optimization: bool
    feature_importance_analysis: bool
    advanced_risk_management: bool = True  # Available for most tiers


@dataclass
class DeploymentReport:
    """
    Result of deployment validation for this capital tier.

    Attributes:
        status: APPROVED, RESTRICTED, REJECTED, or REVIEW_REQUIRED
        account_id: Account identifier (optional)
        issues: List of critical issues blocking deployment
        warnings: List of warnings (non-blocking)
        recommendations: List of improvement recommendations
        tier: Account tier
        capital: Account capital amount
    """

    status: DeploymentStatus
    account_id: Optional[str]
    issues: list[str]
    warnings: list[str]
    recommendations: list[str]
    tier: str
    capital: Decimal


# ============================================================================
# CORE SERVICE CLASS
# ============================================================================


class CapitalTierStrategySelector:
    """
    Maps capital → strategy configuration + features + risk profile.

    This is the single source of truth for capital tier-based decisions.
    All downstream systems should query this service to determine capabilities.

    Usage:
        selector = CapitalTierStrategySelector(capital=Decimal("250000"), account_id="ACC001")
        strategy = selector.select_strategies()
        risk = selector.get_risk_profile()
        features = selector.get_enabled_features()
        validation = selector.validate_deployment(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("2500")
        )
    """

    # ========================================================================
    # STRATEGY RECOMMENDATIONS PER TIER
    # ========================================================================

    STRATEGY_RECOMMENDATIONS: ClassVar[dict] = {
        AccountTier.MICRO: {
            "primary": "momentum_engine",
            "secondary": ["mean_reversion_engine"],
            "ensemble_type": EnsembleType.NONE,
            "config_variant": "conservative",
            "reasoning": "Single simple strategy for micro accounts - momentum only, no ML overhead",
        },
        AccountTier.SMALL: {
            "primary": "momentum_engine",
            "secondary": ["mean_reversion_engine", "breakout_engine"],
            "ensemble_type": EnsembleType.WEIGHTED,
            "config_variant": "conservative",
            "reasoning": "Small accounts use weighted ensemble with conservative positioning",
        },
        AccountTier.MEDIUM: {
            "primary": "ensemble_selector",
            "secondary": ["momentum_engine"],
            "ensemble_type": EnsembleType.REGIME_BASED,
            "config_variant": "balanced",
            "reasoning": "Medium accounts use regime-based ensemble to adapt to market conditions",
        },
        AccountTier.LARGE: {
            "primary": "ensemble_selector",
            "secondary": ["momentum_engine", "trend_following_engine"],
            "ensemble_type": EnsembleType.REGIME_BASED,
            "config_variant": "aggressive",
            "reasoning": "Large accounts use full ensemble with regime detection for optimal alpha",
        },
    }

    # ========================================================================
    # LEVERAGE ALLOWANCES PER TIER
    # ========================================================================

    LEVERAGE_ALLOWANCES: ClassVar[dict] = {
        AccountTier.MICRO: Decimal("1.0"),  # No leverage
        AccountTier.SMALL: Decimal("1.25"),  # Up to 1.25x
        AccountTier.MEDIUM: Decimal("1.5"),  # Up to 1.5x
        AccountTier.LARGE: Decimal("2.5"),  # Up to 2.5x (for €250k+)
    }

    # ========================================================================
    # DRAWDOWN TOLERANCE PER TIER
    # ========================================================================

    DRAWDOWN_TOLERANCE: ClassVar[dict] = {
        AccountTier.MICRO: Decimal("0.05"),  # 5% max drawdown
        AccountTier.SMALL: Decimal("0.08"),  # 8% max drawdown
        AccountTier.MEDIUM: Decimal("0.10"),  # 10% max drawdown
        AccountTier.LARGE: Decimal("0.15"),  # 15% max drawdown (can sustain longer periods)
    }

    def __init__(self, capital: Decimal, account_id: Optional[str] = None):
        """
        Initialize Capital Tier Strategy Selector.

        Args:
            capital: Account capital amount (in EUR/USD)
            account_id: Optional account identifier for logging

        Raises:
            ValueError: If capital <= 0
        """
        if capital <= Decimal("0"):
            raise ValueError("Capital must be > 0")

        self.capital = capital
        self.account_id = account_id
        self.tier = AccountConfiguration.get_tier(capital)
        self.config = AccountConfiguration.get_configuration(capital)

        # Initialize gate checkers
        self._learning_gate = LearningCapitalGate()
        self._module_gate = ExpensiveModuleGate()

        logger.info(
            f"[{account_id or 'UNKNOWN'}] Initialized CapitalTierStrategySelector: "
            f"capital={capital:,.0f}, tier={self.tier.value}"
        )

    # ========================================================================
    # PRIMARY PUBLIC METHODS
    # ========================================================================

    def select_strategies(self) -> StrategySelection:
        """
        Select optimal strategies for this capital tier.

        Returns:
            StrategySelection with primary/secondary strategies and ensemble type

        Implementation Notes:
            - Micro: Single strategy (momentum) only
            - Small: Weighted ensemble with 2-3 strategies
            - Medium: Regime-based ensemble selector
            - Large: Full ensemble with all available strategies
        """
        rec = self.STRATEGY_RECOMMENDATIONS[self.tier]

        selection = StrategySelection(
            primary_strategy=rec["primary"],
            secondary_strategies=rec["secondary"],
            ensemble_type=rec["ensemble_type"],
            config_variant=rec["config_variant"],
            reasoning=rec["reasoning"],
            tier=self.tier.value,
        )

        logger.info(
            f"[{self.account_id or 'UNKNOWN'}] Strategy selection: "
            f"primary={selection.primary_strategy}, "
            f"ensemble={selection.ensemble_type.value}, "
            f"variant={selection.config_variant}"
        )

        return selection

    def get_risk_profile(self) -> RiskProfile:
        """
        Get risk limits appropriate for this capital tier.

        Returns:
            RiskProfile with position sizing, leverage, drawdown limits, etc.

        Implementation Notes:
            - Position size scales from 2% (micro) to 10% (large)
            - Leverage allowed scales from 1.0x (micro) to 2.5x (large)
            - Drawdown tolerance scales with capital stability
        """
        AccountConfiguration.get_safe_trading_limits(self.capital)

        # Determine position sizing strategy by tier
        if self.tier == AccountTier.MICRO or self.tier == AccountTier.SMALL:
            pos_sizing = PositionSizingStrategy.FIXED_PCT
        elif self.tier == AccountTier.MEDIUM:
            pos_sizing = PositionSizingStrategy.VOLATILITY_ADJUSTED
        else:  # LARGE
            pos_sizing = PositionSizingStrategy.KELLY_CRITERION

        # Get learning & module status
        learning_enabled = self.config.get("learning_enabled", False)
        modules_enabled = self._get_enabled_modules()

        # Get defaults from centralized config
        tier_defaults = _get_tier_config_defaults()

        risk_profile = RiskProfile(
            tier=self.tier.value,
            max_position_size=self.config.get(
                "position_size_pct", tier_defaults["position_size_pct"]
            ),
            max_concurrent_trades=self.config.get("max_concurrent_trades", 2),
            max_daily_loss_pct=self.config.get(
                "max_daily_loss_pct", tier_defaults["max_daily_loss_pct"]
            ),
            max_drawdown_pct=self.DRAWDOWN_TOLERANCE[self.tier],
            leverage_allowed=self.LEVERAGE_ALLOWANCES[self.tier],
            learning_enabled=learning_enabled,
            modules_enabled=modules_enabled,
            position_sizing_strategy=pos_sizing,
        )

        # Validate the profile
        is_valid, reason = risk_profile.validate()
        if not is_valid:
            logger.warning(
                f"[{self.account_id or 'UNKNOWN'}] Risk profile validation failed: {reason}"
            )

        logger.info(
            f"[{self.account_id or 'UNKNOWN'}] Risk profile: "
            f"max_pos={risk_profile.max_position_size:.0%}, "
            f"leverage={risk_profile.leverage_allowed}x, "
            f"max_dd={risk_profile.max_drawdown_pct:.0%}"
        )

        return risk_profile

    def get_enabled_features(self) -> StrategyCapabilities:
        """
        Get capabilities and features available at this capital tier.

        Returns:
            StrategyCapabilities with enabled/disabled features

        Implementation Notes:
            - Learning: Enabled for small+ tiers with sufficient alpha
            - Deep learning: Enabled for medium+ tiers only
            - Transformers: Enabled for large tiers only (expensive)
            - Ensemble methods: Enabled for small+ tiers
        """
        # Conservative defaults: assume features disabled unless conditions met

        # Learning availability
        learning_enabled = self.config.get("learning_enabled", False)

        # Transfer learning (medium+ only)
        transfer_learning = (
            self.tier in [AccountTier.MEDIUM, AccountTier.LARGE] and learning_enabled
        )

        # Deep learning (medium+ only, if enabled)
        deep_learning = self.tier in [AccountTier.MEDIUM, AccountTier.LARGE] and self.config.get(
            "expensive_modules_enabled", False
        )

        # Transformers (large only, if enabled)
        transformer_models = self.tier == AccountTier.LARGE and self.config.get(
            "expensive_modules_enabled", False
        )

        # Ensemble methods (small+ only)
        ensemble_methods = self.tier in [AccountTier.SMALL, AccountTier.MEDIUM, AccountTier.LARGE]

        # Hyperparameter optimization (medium+ only)
        hyperparameter_opt = self.tier in [
            AccountTier.MEDIUM,
            AccountTier.LARGE,
        ] and self.config.get("expensive_modules_enabled", False)

        # Feature importance (medium+ only)
        feature_importance = (
            self.tier in [AccountTier.MEDIUM, AccountTier.LARGE] and learning_enabled
        )

        capabilities = StrategyCapabilities(
            learning=learning_enabled,
            transfer_learning=transfer_learning,
            deep_learning=deep_learning,
            transformer_models=transformer_models,
            ensemble_methods=ensemble_methods,
            hyperparameter_optimization=hyperparameter_opt,
            feature_importance_analysis=feature_importance,
        )

        logger.info(
            f"[{self.account_id or 'UNKNOWN'}] Enabled features: "
            f"learning={capabilities.learning}, "
            f"deep_learning={capabilities.deep_learning}, "
            f"transformers={capabilities.transformer_models}, "
            f"ensemble={capabilities.ensemble_methods}"
        )

        return capabilities

    def validate_deployment(
        self,
        monthly_profit_goal: Decimal,
        expected_monthly_alpha: Decimal,
        tax_rate: Optional[Decimal] = None,
        commission_per_trade: Optional[Decimal] = None,
    ) -> DeploymentReport:
        """
        Validate if account is safe for live trading deployment.

        Args:
            monthly_profit_goal: Target monthly profit in EUR/USD
            expected_monthly_alpha: Expected monthly alpha from strategies
            tax_rate: Tax rate on profits (default 20%)
            commission_per_trade: Commission per trade (default $10)

        Returns:
            DeploymentReport with validation status and recommendations

        Implementation Notes:
            - Calls DeploymentValidator to orchestrate all gates
            - Returns APPROVED only if all gates pass
            - Features disabled if gates fail (graceful degradation)
        """
        if tax_rate is None:
            tax_rate = Decimal("0.20")
        if commission_per_trade is None:
            commission_per_trade = Decimal("10")
        status, validation = DeploymentValidator.validate_for_deployment(
            capital=self.capital,
            monthly_profit_goal=monthly_profit_goal,
            expected_monthly_alpha=expected_monthly_alpha,
            tax_rate=tax_rate,
            commission_per_trade=commission_per_trade,
            learning_enabled=self.config.get("learning_enabled", False),
            expensive_modules_enabled=self.config.get("expensive_modules_enabled", False),
            account_id=self.account_id,
        )

        report = DeploymentReport(
            status=status,
            account_id=self.account_id,
            issues=validation.get("issues", []),
            warnings=validation.get("warnings", []),
            recommendations=validation.get("recommendations", []),
            tier=self.tier.value,
            capital=self.capital,
        )

        logger.info(
            f"[{self.account_id or 'UNKNOWN'}] Deployment validation: "
            f"status={status.value}, "
            f"issues={len(report.issues)}, "
            f"warnings={len(report.warnings)}"
        )

        return report

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _get_enabled_modules(self) -> dict[str, bool]:
        """
        Get which expensive ML modules are enabled for this tier.

        Returns:
            Dict mapping module names to enabled status
        """
        # Micro: No modules enabled
        if self.tier == AccountTier.MICRO or self.tier == AccountTier.SMALL:
            return {
                "transfer_learning": False,
                "deep_learning": False,
                "reinforcement_learning": False,
                "multitask_learning": False,
                "transformer_engine": False,
                "hyperparameter_optimizer": False,
                "feature_importance_analysis": False,
            }

        # Medium: Selective expensive modules
        elif self.tier == AccountTier.MEDIUM:
            return {
                "transfer_learning": True,
                "deep_learning": False,  # Expensive, selective enable
                "reinforcement_learning": False,
                "multitask_learning": False,
                "transformer_engine": False,
                "hyperparameter_optimizer": True,
                "feature_importance_analysis": True,
            }

        # Large: All modules enabled (cost-benefit positive)
        else:  # LARGE
            return {
                "transfer_learning": True,
                "deep_learning": True,
                "reinforcement_learning": False,  # Very expensive, evaluate separately
                "multitask_learning": True,
                "transformer_engine": True,
                "hyperparameter_optimizer": True,
                "feature_importance_analysis": True,
            }

    def _gate_learning_viability(self) -> tuple[bool, str]:
        """
        Check if learning infrastructure is cost-effective for this account.

        Returns:
            (is_viable: bool, reason: str)
        """
        if self.tier == AccountTier.MICRO:
            return False, "Learning not viable for micro accounts (< €15k)"

        # For small+ tiers, learning is conditionally enabled
        # DeploymentValidator will check cost-benefit ratios
        return True, "Learning is potentially viable for this tier"

    def _get_position_sizing_strategy(self) -> PositionSizingStrategy:
        """
        Determine optimal position sizing strategy for this tier.

        Returns:
            Position sizing strategy enum
        """
        if self.tier == AccountTier.MICRO or self.tier == AccountTier.SMALL:
            return PositionSizingStrategy.FIXED_PCT
        elif self.tier == AccountTier.MEDIUM:
            return PositionSizingStrategy.VOLATILITY_ADJUSTED
        else:  # LARGE
            return PositionSizingStrategy.KELLY_CRITERION

    def _calculate_leverage_allowance(self) -> Decimal:
        """
        Calculate leverage multiplier allowed for this tier.

        Returns:
            Leverage allowance (e.g., 1.0 = no leverage, 2.5 = 2.5x leverage)
        """
        return self.LEVERAGE_ALLOWANCES[self.tier]

    # ========================================================================
    # INFORMATION METHODS
    # ========================================================================

    def get_tier_info(self) -> dict:
        """
        Get information about this tier's capabilities.

        Returns:
            Dict with tier details, recommendations, and limits
        """
        # Get defaults from centralized config
        tier_defaults = _get_tier_config_defaults()

        return {
            "tier": self.tier.value,
            "capital": float(self.capital),
            "capital_range": self._get_tier_range(),
            "position_size": float(
                self.config.get("position_size_pct", tier_defaults["position_size_pct"])
            ),
            "max_concurrent_trades": self.config.get("max_concurrent_trades", 2),
            "learning_enabled": self.config.get("learning_enabled", False),
            "expensive_modules_enabled": self.config.get("expensive_modules_enabled", False),
            "trading_frequency": self.config.get("trading_frequency", "medium"),
            "risk_level": self.config.get("risk_level", "moderate"),
            "recommendation": self.config.get("recommendation", ""),
        }

    def _get_tier_range(self) -> str:
        """Get human-readable tier range"""
        min_cap, max_cap = AccountConfiguration.TIER_BOUNDARIES[self.tier]
        if self.tier == AccountTier.LARGE:
            return f"€{min_cap:,.0f}+"
        else:
            return f"€{min_cap:,.0f} - €{max_cap:,.0f}"

    def get_upgrade_path(self) -> dict:
        """
        Get upgrade path to next tier.

        Returns:
            Dict with next tier info and capital needed
        """
        return AccountConfiguration.get_tier_upgrade_capital(self.capital)


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_selector_instances: dict[str, CapitalTierStrategySelector] = {}


def get_selector(capital: Decimal, account_id: Optional[str] = None) -> CapitalTierStrategySelector:
    """
    Get or create a CapitalTierStrategySelector instance.

    Caches instances by account_id to avoid recreation.

    Args:
        capital: Account capital
        account_id: Account identifier for caching

    Returns:
        CapitalTierStrategySelector instance
    """
    cache_key = account_id or f"anon_{capital}"

    if cache_key not in _selector_instances:
        _selector_instances[cache_key] = CapitalTierStrategySelector(capital, account_id)

    return _selector_instances[cache_key]
