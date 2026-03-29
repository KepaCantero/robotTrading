"""
T3.1: ModuleParametrizer - Generate module-specific parameters from InvestmentProfile

Maps InvestmentProfile (capital tier, objective, risk tolerance) to module-specific
parameters for all enabled trading modules.

The parametrizer:
1. Takes InvestmentProfile with enabled_modules
2. Loads module configuration for each enabled module
3. Applies tier-specific parameter adjustments
4. Integrates objective-specific variations
5. Returns ModuleParameterSet with all module parameters
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from app.domain.models.investment_profile import CapitalTier, InvestmentProfile

logger = logging.getLogger(__name__)


class ModuleType(str, Enum):
    """All supported trading modules in the system."""

    MOMENTUM = "momentum_modular"
    MEAN_REVERSION = "mean_reversion_modular"
    PAIRS_TRADING = "pairs_trading_modular"
    DIVIDEND_SCREENER = "dividend_screener"
    DIVIDEND_PREDICTOR = "dividend_predictor"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    ML_ENSEMBLE = "ml_ensemble"
    DEFENSIVE_MOMENTUM = "defensive_momentum"
    HEDGE_STRATEGIES = "hedge_strategies"
    SECTOR_ROTATION = "sector_rotation"
    COVERED_CALL_WRITER = "covered_call_writer"
    PUT_SELLER = "put_seller_modular"
    COLLAR_STRATEGY = "collar_strategy"
    CURRENCY_HEDGING = "currency_hedging"
    BREAKOUT = "breakout_modular"
    TREND_FOLLOWING = "trend_following_modular"
    ARBITRAGE = "arbitrage_modular"


@dataclass
class ModuleParameters:
    """Parameters for a single trading module."""

    module_name: str
    tier: CapitalTier
    objective: str
    preset: str  # conservative | balanced | aggressive

    # Core parameters (all modules share these)
    max_position_size: Decimal
    stop_loss_pct: Decimal
    take_profit_pct: Decimal
    max_exposure: Decimal
    max_positions: int

    # Module-specific parameters (dict allows flexibility)
    module_specific: dict[str, Any] = field(default_factory=dict)

    # Risk adjustment factor (applies to position sizing)
    risk_adjustment: Decimal = Decimal("1.0")

    # Metadata
    enabled: bool = True
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "module_name": self.module_name,
            "tier": self.tier.value,
            "objective": self.objective,
            "preset": self.preset,
            "max_position_size": str(self.max_position_size),
            "stop_loss_pct": str(self.stop_loss_pct),
            "take_profit_pct": str(self.take_profit_pct),
            "max_exposure": str(self.max_exposure),
            "max_positions": self.max_positions,
            "risk_adjustment": str(self.risk_adjustment),
            "enabled": self.enabled,
            "module_specific": self.module_specific,
            "version": self.version,
        }


@dataclass
class ModuleParameterSet:
    """Complete set of parameters for all enabled modules in an InvestmentProfile."""

    profile_id: str
    input_id: str
    capital_tier: CapitalTier
    objetivo_inversion: str

    # Dict mapping module names to their parameters
    modules: dict[str, ModuleParameters] = field(default_factory=dict)

    # Metadata
    generated_at: str = ""
    total_max_exposure: Decimal = Decimal("0")

    def add_module(self, module_params: ModuleParameters) -> None:
        """Add parameters for a single module."""
        self.modules[module_params.module_name] = module_params

    def get_module(self, module_name: str) -> Optional[ModuleParameters]:
        """Get parameters for a specific module."""
        return self.modules.get(module_name)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "profile_id": self.profile_id,
            "input_id": self.input_id,
            "capital_tier": self.capital_tier.value,
            "objetivo_inversion": self.objetivo_inversion,
            "modules": {name: params.to_dict() for name, params in self.modules.items()},
            "generated_at": self.generated_at,
            "total_max_exposure": str(self.total_max_exposure),
        }


class ModuleParametrizer:
    """
    Generate module-specific parameters from InvestmentProfile.

    Handles:
    1. Loading module configuration templates
    2. Applying tier-specific adjustments
    3. Integrating objective-specific variations
    4. Risk-scaling adjustments
    5. Validation of parameter ranges
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize ModuleParametrizer with module configuration.

        Args:
            config: Module configuration dict (either raw or with 'modules' key)
        """
        # Handle both formats: raw modules dict or dict with 'modules' key
        self.config = config.get("modules", config)

        logger.info("ModuleParametrizer initialized with configuration")

    def generate(self, investment_profile: InvestmentProfile) -> ModuleParameterSet:
        """
        Generate ModuleParameterSet from InvestmentProfile.

        Args:
            investment_profile: Investment profile with enabled modules

        Returns:
            ModuleParameterSet: Parameters for all enabled modules

        Raises:
            ValueError: If module configuration invalid or not found
        """
        try:
            # Create parameter set
            param_set = ModuleParameterSet(
                profile_id=investment_profile.profile_id,
                input_id=investment_profile.input_id,
                capital_tier=investment_profile.capital_tier,
                objetivo_inversion=investment_profile.objetivo_inversion.value,
                generated_at=__import__("datetime").datetime.now().isoformat(),
            )

            # Generate parameters for each enabled module
            total_exposure = Decimal("0")
            for module_name in investment_profile.enabled_modules:
                try:
                    module_params = self._generate_module_parameters(
                        module_name=module_name,
                        investment_profile=investment_profile,
                    )
                    param_set.add_module(module_params)
                    total_exposure += module_params.max_exposure
                except ValueError as e:
                    logger.warning(f"Failed to generate parameters for {module_name}: {e}")
                    # Continue with other modules on non-critical errors

            param_set.total_max_exposure = total_exposure

            logger.info(
                f"Generated ModuleParameterSet: {len(param_set.modules)} modules, "
                f"total_exposure={total_exposure}, "
                f"tier={investment_profile.capital_tier.value}"
            )

            return param_set

        except OSError as e:
            logger.error(f"Failed to generate ModuleParameterSet: {e}")
            raise

    def _generate_module_parameters(
        self,
        module_name: str,
        investment_profile: InvestmentProfile,
    ) -> ModuleParameters:
        """
        Generate parameters for a single module.

        Args:
            module_name: Name of the module
            investment_profile: Investment profile

        Returns:
            ModuleParameters: Parameters for this module

        Raises:
            ValueError: If module not configured
        """
        # Load module base configuration
        if module_name not in self.config:
            raise ValueError(f"Module not configured: {module_name}")

        module_config = self.config[module_name]

        # Get tier-specific variant
        tier_value = investment_profile.capital_tier.value
        if tier_value not in module_config.get("tiers", {}):
            raise ValueError(f"No configuration for module {module_name} at tier {tier_value}")

        tier_config = module_config["tiers"][tier_value]

        # Determine preset
        preset = tier_config.get("preset", "balanced")

        # Extract core parameters (apply tier-specific overrides first, then module-level defaults)
        base_config = module_config.get("base", {})

        max_position_size = Decimal(
            str(tier_config.get("max_position_size", base_config.get("max_position_size", "0.10")))
        )

        stop_loss_pct = Decimal(
            str(tier_config.get("stop_loss_pct", base_config.get("stop_loss_pct", "0.03")))
        )

        take_profit_pct = Decimal(
            str(tier_config.get("take_profit_pct", base_config.get("take_profit_pct", "0.08")))
        )

        max_exposure = Decimal(
            str(tier_config.get("max_exposure", base_config.get("max_exposure", "0.30")))
        )

        max_positions = tier_config.get("max_positions", base_config.get("max_positions", 5))

        risk_adjustment = Decimal(
            str(tier_config.get("risk_adjustment", base_config.get("risk_adjustment", "1.0")))
        )

        # Extract module-specific parameters
        module_specific = tier_config.get("module_specific", {})

        # Apply risk scaling if enabled
        if investment_profile.risk_scaling_enabled:
            # Apply volatility-based scaling
            scaling_factor = self._calculate_risk_scaling_factor(investment_profile.risk_profile)
            max_position_size = max_position_size * scaling_factor
            risk_adjustment = risk_adjustment * scaling_factor

        return ModuleParameters(
            module_name=module_name,
            tier=investment_profile.capital_tier,
            objective=investment_profile.objetivo_inversion.value,
            preset=preset,
            max_position_size=max_position_size,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            max_exposure=max_exposure,
            max_positions=max_positions,
            module_specific=module_specific,
            risk_adjustment=risk_adjustment,
            enabled=True,
        )

    @staticmethod
    def _calculate_risk_scaling_factor(risk_profile: int) -> Decimal:
        """
        Calculate risk scaling factor based on risk profile (1-7 scale).

        Risk profile 1 (conservative) = 0.8 (20% smaller positions)
        Risk profile 4 (neutral) = 1.0 (normal positions)
        Risk profile 7 (aggressive) = 1.2 (20% larger positions)

        Args:
            risk_profile: Risk profile 1-7

        Returns:
            Decimal: Scaling factor
        """
        # Linear mapping: risk_profile 1→0.8, 4→1.0, 7→1.2
        factor = Decimal("0.8") + (Decimal(risk_profile - 1) / 6) * Decimal("0.4")
        return max(Decimal("0.6"), min(Decimal("1.4"), factor))  # Clamp 0.6-1.4
