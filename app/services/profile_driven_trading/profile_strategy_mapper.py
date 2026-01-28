"""
ProfileStrategyMapper - Connects InputProfile to Strategy Combinations

This module maps user investment profiles to appropriate strategy combinations,
learning engines, capital allocation, and ensemble configurations based on
centralized configuration files.

Key Responsibilities:
- Map investment objectives to strategy combinations
- Map capital tiers to allocation schemes
- Map risk tolerance to ensemble modes
- Configure and instantiate learning engines
- Generate comprehensive trading configurations

Configuration Sources:
- config/investment_profiles.yaml - Profile-based strategy mappings
- config/learning_parameters.yaml - Learning engine parameters
- config/strategies/ensemble.yaml - Ensemble configurations
"""

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.core.centralized_config import get_config
from app.core.tier_mapper import TierMapper, get_tier, normalize_tier
from app.services.multi_strategy_allocation import (
    MultiStrategyAllocationManager,
    StrategyCapitalAllocation,
)
from app.strategies.momentum_modular.learning.base_learning_engine import BaseLearningEngine

logger = logging.getLogger(__name__)


# Capital tier definitions (must match config/investment_profiles.yaml)
# The thresholds represent the upper bound of each tier (exclusive)
CAPITAL_TIER_THRESHOLDS = {
    "small": Decimal("15000"),    # micro: < €15k
    "medium": Decimal("50000"),   # small: €15k - €50k
    "large": Decimal("250000"),   # medium: €50k - €250k
}  # large: >= €250k


def get_capital_tier(capital: Decimal) -> str:
    """
    Determine capital tier from capital amount.

    Tier boundaries (from config/investment_profiles.yaml):
    - micro: < €15k
    - small: €15k - €50k
    - medium: €50k - €250k
    - large: >= €250k

    This function uses the centralized TierMapper for consistency
    across all tier determinations in the system.

    Args:
        capital: Capital amount in EUR

    Returns:
        Capital tier: "micro", "small", "medium", or "large"

    Examples:
        >>> get_capital_tier(Decimal("10000"))
        'micro'
        >>> get_capital_tier(Decimal("30000"))
        'small'
        >>> get_capital_tier(Decimal("100000"))
        'medium'
        >>> get_capital_tier(Decimal("500000"))
        'large'
    """
    try:
        # Use the centralized tier mapper
        return TierMapper.get_tier_from_capital(capital)
    except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
        # Fallback to manual calculation if tier mapper fails
        logger.warning(f"TierMapper.get_tier_from_capital failed for {capital}: {e}, using fallback")
        if capital < CAPITAL_TIER_THRESHOLDS["small"]:
            return "micro"
        elif capital < CAPITAL_TIER_THRESHOLDS["medium"]:
            return "small"
        elif capital < CAPITAL_TIER_THRESHOLDS["large"]:
            return "medium"
        else:
            return "large"


class StrategyMapping(BaseModel):
    """
    Result of mapping profile to strategies.

    Contains the complete configuration for trading based on user profile.
    """

    # Profile information
    objective: ObjectivoInversion
    capital_tier: str
    risk_tolerance: RiskTolerance

    # Strategy configuration
    enabled_strategies: List[str] = Field(
        description="List of enabled strategy modules"
    )
    strategy_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Weight allocation for each strategy"
    )

    # Risk parameters
    risk_profile: int = Field(
        ge=1, le=6,
        description="Risk profile level (1-6)"
    )
    leverage: float = Field(
        ge=0, le=3,
        description="Leverage multiplier"
    )
    max_position_size: float = Field(
        ge=0, le=0.5,
        description="Maximum position size per trade"
    )
    max_sector_allocation: float = Field(
        ge=0, le=0.5,
        description="Maximum allocation per sector"
    )

    # Trading configuration
    order_splitting_strategy: str = Field(
        description="Order execution strategy"
    )
    commission_negotiation: bool = Field(
        description="Whether commission negotiation is enabled"
    )

    # Learning configuration
    enabled_learning_engines: List[str] = Field(
        default_factory=list,
        description="List of enabled learning engine types"
    )

    # Ensemble configuration
    ensemble_mode: str = Field(
        description="Ensemble voting mode"
    )
    ensemble_min_strategies: int = Field(
        ge=1, le=10,
        description="Minimum strategies required for signal"
    )
    ensemble_confidence_threshold: float = Field(
        ge=0, le=1,
        description="Minimum confidence for ensemble signal"
    )

    # Capital allocation
    capital_allocation: Optional[Dict[str, Decimal]] = Field(
        default=None,
        description="Capital allocated to each strategy"
    )

    @field_validator("strategy_weights")
    @classmethod
    def validate_weights_sum(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate that weights sum approximately to 1.0."""
        if v:
            total = sum(v.values())
            if not 0.95 <= total <= 1.05:
                logger.warning(f"Strategy weights sum to {total:.3f}, expected ~1.0")
        return v


class ProfileStrategyMapper:
    """
    Maps InputProfile to strategy combinations and configurations.

    This is the core component that translates user investment goals
    into concrete trading configurations using centralized config files.

    Usage:
        mapper = ProfileStrategyMapper()
        profile = InputProfile(
            capital_initial=100000,
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24
        )
        mapping = mapper.map_profile_to_strategies(profile)
        strategies = mapping.enabled_strategies
        allocation = mapper.get_capital_allocation(profile)
    """

    def __init__(
        self,
        investment_profiles_path: str = "config/investment_profiles.yaml",
        learning_params_path: str = "config/learning_parameters.yaml",
        ensemble_config_path: str = "config/strategies/ensemble.yaml",
    ):
        """
        Initialize the mapper with configuration paths.

        Args:
            investment_profiles_path: Path to investment profiles YAML
            learning_params_path: Path to learning parameters YAML
            ensemble_config_path: Path to ensemble configurations YAML
        """
        self.investment_profiles_path = Path(investment_profiles_path)
        self.learning_params_path = Path(learning_params_path)
        self.ensemble_config_path = Path(ensemble_config_path)

        # Load configurations
        self.investment_profiles = self._load_yaml(self.investment_profiles_path)
        self.learning_params = self._load_yaml(self.learning_params_path)
        self.ensemble_configs = self._load_yaml(self.ensemble_config_path)

        # Get centralized config
        self.central_config = get_config()

        logger.info("ProfileStrategyMapper initialized with configurations")

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """
        Load YAML configuration file.

        Args:
            path: Path to YAML file

        Returns:
            Dictionary with configuration data
        """
        if not path.exists():
            logger.warning(f"Configuration file not found: {path}")
            return {}

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            logger.debug(f"Loaded configuration from {path}")
            return data
        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
            logger.error(f"Error loading {path}: {e}")
            return {}

    def map_profile_to_strategies(self, profile: InputProfile) -> Dict[str, Any]:
        """
        Map InputProfile to strategy combination.

        Args:
            profile: Validated user input profile

        Returns:
            Dictionary with strategy configuration:
            {
                'enabled_strategies': List[str],
                'strategy_config': Dict[str, Any],
                'risk_params': Dict[str, Any],
                'learning_config': Dict[str, Any]
            }

        Raises:
            ValueError: If profile configuration cannot be determined
        """
        # Determine capital tier
        capital_tier = get_capital_tier(profile.capital_initial)

        # Get objective key (handle enum)
        objective_key = profile.objetivo_inversion.value if isinstance(
            profile.objetivo_inversion, ObjectivoInversion
        ) else profile.objetivo_inversion

        logger.info(
            f"Mapping profile: objective={objective_key}, "
            f"tier={capital_tier}, risk={profile.risk_tolerance.value}"
        )

        # Get profile configuration from YAML
        profile_config = self._get_profile_config(objective_key, capital_tier)

        if not profile_config:
            raise ValueError(
                f"No configuration found for objective={objective_key}, tier={capital_tier}"
            )

        # Extract strategy configuration
        enabled_strategies = profile_config.get("enabled_modules", [])
        risk_profile = profile_config.get("risk_profile", 4)
        leverage = profile_config.get("leverage", 1.0)
        max_position_size = profile_config.get("max_position_size", 0.20)
        max_sector_allocation = profile_config.get("max_sector_allocation", 0.30)
        order_splitting = profile_config.get("order_splitting_strategy", "vwap")
        commission_negotiation = profile_config.get("commission_negotiation", True)

        # Get learning engines for this profile
        learning_engines = self.get_learning_engines(profile)

        # Get ensemble configuration
        ensemble_config = self.get_ensemble_config(profile)

        # Build strategy configuration
        strategy_config = {
            "enabled_strategies": enabled_strategies,
            "objective": objective_key,
            "capital_tier": capital_tier,
            "risk_tolerance": profile.risk_tolerance.value,
            "risk_params": {
                "risk_profile": risk_profile,
                "leverage": leverage,
                "max_position_size": max_position_size,
                "max_sector_allocation": max_sector_allocation,
            },
            "trading_params": {
                "order_splitting_strategy": order_splitting,
                "commission_negotiation": commission_negotiation,
            },
            "learning_engines": learning_engines,
            "ensemble_config": ensemble_config,
            "investment_horizon": profile.investment_horizon,
        }

        logger.info(
            f"Mapped profile to {len(enabled_strategies)} strategies: "
            f"{', '.join(enabled_strategies)}"
        )

        return strategy_config

    def _get_profile_config(
        self,
        objective: str,
        capital_tier: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get profile configuration from investment_profiles.yaml.

        Args:
            objective: Investment objective key
            capital_tier: Capital tier (micro, small, medium, large)

        Returns:
            Configuration dictionary or None if not found
        """
        profiles = self.investment_profiles.get("profiles", {})
        objective_config = profiles.get(objective, {})

        if not objective_config:
            # Try defaults
            defaults = self.investment_profiles.get("defaults", {})
            if defaults:
                logger.warning(
                    f"Objective '{objective}' not found, using defaults"
                )
                return defaults
            return None

        tier_config = objective_config.get(capital_tier)
        if not tier_config:
            # Fall back to closest tier
            for fallback_tier in ["small", "medium", "large"]:
                if fallback_tier in objective_config:
                    logger.warning(
                        f"Tier '{capital_tier}' not found for {objective}, "
                        f"using {fallback_tier}"
                    )
                    return objective_config[fallback_tier]

            # Use defaults
            defaults = self.investment_profiles.get("defaults", {})
            if defaults:
                logger.warning(f"Using default configuration for {objective}")
                return defaults

            return None

        return tier_config

    def get_capital_allocation(
        self,
        profile: InputProfile
    ) -> MultiStrategyAllocationManager:
        """
        Get capital allocation for strategies based on profile.

        Creates a MultiStrategyAllocationManager with appropriate
        allocations based on the profile's capital tier and objective.

        Args:
            profile: User input profile

        Returns:
            MultiStrategyAllocationManager configured for the profile
        """
        # Get strategy configuration
        strategy_config = self.map_profile_to_strategies(profile)
        enabled_strategies = strategy_config["enabled_strategies"]

        # Create allocation manager
        manager = MultiStrategyAllocationManager(profile.capital_initial)

        # Clear default allocations
        manager.strategy_allocations = {}

        # Get profile-specific allocation weights
        capital_tier = get_capital_tier(profile.capital_initial)
        objective_key = profile.objetivo_inversion.value
        profile_config = self._get_profile_config(objective_key, capital_tier)

        # Define strategy weights based on profile
        strategy_weights = self._calculate_strategy_weights(
            enabled_strategies,
            profile_config,
            profile.risk_tolerance
        )

        # Create strategy allocations
        for strategy_name, weight in strategy_weights.items():
            # Convert float weight to Decimal with full precision
            weight_decimal = Decimal(str(weight))

            # Get risk-adjusted min/max weights
            min_weight = max(Decimal("0.05"), weight_decimal * Decimal("0.5"))
            max_weight = min(Decimal("0.70"), weight_decimal * Decimal("1.5"))

            allocation = StrategyCapitalAllocation(
                strategy_name=strategy_name,
                target_weight=weight_decimal,
                min_weight=min_weight,
                max_weight=max_weight,
            )
            manager.strategy_allocations[strategy_name] = allocation

        # Calculate capital allocation
        allocations = manager.allocate_capital()

        logger.info(
            f"Capital allocation for €{profile.capital_initial:,.2f}: "
            f"{len(allocations)} strategies"
        )
        for strategy, capital in allocations.items():
            logger.info(f"  {strategy}: €{capital:,.2f}")

        return manager

    def _calculate_strategy_weights(
        self,
        strategies: List[str],
        profile_config: Dict[str, Any],
        risk_tolerance: RiskTolerance
    ) -> Dict[str, float]:
        """
        Calculate strategy weights based on profile and risk tolerance.

        Args:
            strategies: List of enabled strategies
            profile_config: Profile configuration from YAML
            risk_tolerance: User's risk tolerance

        Returns:
            Dictionary mapping strategy names to weights
        """
        # Base weights from strategy count (use Decimal for precision)
        num_strategies = len(strategies)
        if num_strategies == 0:
            return {}

        base_weight = float(Decimal("1.0") / Decimal(str(num_strategies)))

        # Risk-adjusted weights
        risk_adjustments = {
            RiskTolerance.BAJO: {  # Conservative: more balanced
                "momentum_modular": 0.8,
                "mean_reversion_modular": 1.2,
                "dividend_screener": 1.5,
                "defensive_momentum": 1.5,
            },
            RiskTolerance.MEDIO: {  # Balanced
                "momentum_modular": 1.0,
                "mean_reversion_modular": 1.0,
                "dividend_screener": 1.0,
                "pairs_trading_modular": 1.0,
            },
            RiskTolerance.ALTO: {  # Aggressive: momentum focus
                "momentum_modular": 1.3,
                "mean_reversion_modular": 0.7,
                "dividend_screener": 0.5,
                "pairs_trading_modular": 1.0,
            }
        }

        # Calculate adjusted weights
        weights = {}
        adjustments = risk_adjustments.get(risk_tolerance, {})

        for strategy in strategies:
            adjustment = adjustments.get(strategy, 1.0)
            weights[strategy] = base_weight * adjustment

        # Normalize to sum to 1.0 (using Decimal for precision)
        total = sum(weights.values())
        if total > 0:
            # Use Decimal normalization to ensure weights sum exactly to 1.0
            total_decimal = Decimal(str(total))
            weights = {
                k: float(Decimal(str(v)) / total_decimal)
                for k, v in weights.items()
            }

        return weights

    def get_learning_engines(
        self,
        profile: InputProfile
    ) -> List[str]:
        """
        Get list of enabled learning engines for the profile.

        Determines which learning engines (supervised, deep learning, RL)
        should be enabled based on capital tier and objective.

        Args:
            profile: User input profile

        Returns:
            List of learning engine types to enable
        """
        capital_tier = get_capital_tier(profile.capital_initial)
        objective_key = profile.objetivo_inversion.value

        # Check if ML ensemble is enabled in profile
        profile_config = self._get_profile_config(objective_key, capital_tier)
        enabled_modules = profile_config.get("enabled_modules", [])

        learning_engines = []

        # ML ensemble only available for large capital
        if "ml_ensemble" in enabled_modules and capital_tier == "large":
            # Get tier-specific learning config
            tier_config = self.learning_params.get("tiers", {}).get(capital_tier, {})

            # Supervised learning
            supervised_config = self.learning_params.get("supervised_learning", {})
            if supervised_config:
                learning_engines.append("supervised")

            # Reinforcement learning (only for medium+)
            if capital_tier in ["medium", "large"]:
                rl_config = self.learning_params.get("reinforcement_learning", {})
                if rl_config:
                    learning_engines.append("reinforcement")

            # Deep learning (only for large)
            if capital_tier == "large":
                learning_engines.append("deep")

        logger.info(
            f"Learning engines for {capital_tier} tier: {learning_engines}"
        )

        return learning_engines

    def get_ensemble_config(self, profile: InputProfile) -> Dict[str, Any]:
        """
        Get ensemble configuration based on risk tolerance and profile.

        Maps risk tolerance to ensemble voting mode and parameters.

        Args:
            profile: User input profile

        Returns:
            Dictionary with ensemble configuration
        """
        risk_tolerance = profile.risk_tolerance
        capital_tier = get_capital_tier(profile.capital_initial)

        # Map risk tolerance to ensemble mode
        risk_to_ensemble = {
            RiskTolerance.BAJO: {
                "mode": "voting_ensemble",  # Conservative: requires majority
                "min_strategies": 3,
                "min_confidence": 0.70,
                "require_majority": True,
                "conflict_resolution": "majority",
            },
            RiskTolerance.MEDIO: {
                "mode": "weighted_ensemble",  # Balanced: weighted voting
                "min_strategies": 2,
                "min_confidence": 0.50,
                "require_majority": True,
                "conflict_resolution": "weighted",
            },
            RiskTolerance.ALTO: {
                "mode": "regime_selector",  # Aggressive: adapts to market
                "min_strategies": 1,
                "min_confidence": 0.40,
                "require_majority": False,
                "conflict_resolution": "strongest",
            }
        }

        # Get base ensemble config
        ensemble_base = risk_to_ensemble.get(risk_tolerance, risk_to_ensemble[RiskTolerance.MEDIO])

        # Get ensemble-specific configuration from YAML
        ensemble_mode = ensemble_base["mode"]
        ensemble_yaml_config = self.ensemble_configs.get(ensemble_mode, {})

        # Merge configurations
        ensemble_config = {
            **ensemble_base,
            **ensemble_yaml_config,
        }

        # Adjust for capital tier
        if capital_tier == "micro":
            # Micro: more conservative, fewer strategies
            ensemble_config["min_strategies"] = max(1, ensemble_config["min_strategies"] - 1)
            ensemble_config["min_confidence"] += 0.10
        elif capital_tier == "large":
            # Large: can handle more strategies
            ensemble_config["min_strategies"] = min(5, ensemble_config["min_strategies"] + 1)

        # Clamp confidence to valid range
        ensemble_config["min_confidence"] = max(0.0, min(1.0, ensemble_config["min_confidence"]))

        logger.info(
            f"Ensemble config for {risk_tolerance.value} risk: "
            f"mode={ensemble_mode}, min_strategies={ensemble_config['min_strategies']}"
        )

        return ensemble_config

    def create_strategy_mapping(
        self,
        profile: InputProfile
    ) -> StrategyMapping:
        """
        Create complete StrategyMapping from InputProfile.

        This is the main entry point that creates a comprehensive
        strategy mapping for the given profile.

        Args:
            profile: User input profile

        Returns:
            StrategyMapping with complete configuration

        Raises:
            ValueError: If configuration cannot be determined
        """
        # Get strategy configuration
        strategy_config = self.map_profile_to_strategies(profile)

        # Get capital allocation
        allocation_manager = self.get_capital_allocation(profile)
        capital_allocation = allocation_manager.allocate_capital()

        # Calculate strategy weights
        profile_config = self._get_profile_config(
            profile.objetivo_inversion.value,
            get_capital_tier(profile.capital_initial)
        )
        strategy_weights = self._calculate_strategy_weights(
            strategy_config["enabled_strategies"],
            profile_config,
            profile.risk_tolerance
        )

        # Get ensemble configuration
        ensemble_config = self.get_ensemble_config(profile)

        # Create mapping
        capital_tier = get_capital_tier(profile.capital_initial)

        mapping = StrategyMapping(
            objective=profile.objetivo_inversion,
            capital_tier=capital_tier,
            risk_tolerance=profile.risk_tolerance,
            enabled_strategies=strategy_config["enabled_strategies"],
            strategy_weights=strategy_weights,
            risk_profile=strategy_config["risk_params"]["risk_profile"],
            leverage=strategy_config["risk_params"]["leverage"],
            max_position_size=strategy_config["risk_params"]["max_position_size"],
            max_sector_allocation=strategy_config["risk_params"]["max_sector_allocation"],
            order_splitting_strategy=strategy_config["trading_params"]["order_splitting_strategy"],
            commission_negotiation=strategy_config["trading_params"]["commission_negotiation"],
            enabled_learning_engines=strategy_config["learning_engines"],
            ensemble_mode=ensemble_config["mode"],
            ensemble_min_strategies=ensemble_config["min_strategies"],
            ensemble_confidence_threshold=ensemble_config["min_confidence"],
            capital_allocation=capital_allocation,
        )

        logger.info(
            f"Created strategy mapping for {profile.objetivo_inversion.value} "
            f"with {len(mapping.enabled_strategies)} strategies"
        )

        return mapping

    def get_learning_parameters(
        self,
        profile: InputProfile,
        engine_type: str
    ) -> Dict[str, Any]:
        """
        Get learning parameters for a specific engine type.

        Args:
            profile: User input profile
            engine_type: Type of learning engine (supervised, reinforcement, deep)

        Returns:
            Dictionary with learning parameters for the engine
        """
        capital_tier = get_capital_tier(profile.capital_initial)

        # Get base parameters
        if engine_type == "supervised":
            base_params = self.learning_params.get("supervised_learning", {})
        elif engine_type == "reinforcement":
            base_params = self.learning_params.get("reinforcement_learning", {})
        elif engine_type == "deep":
            base_params = self.learning_params.get("deep_learning", {})
        else:
            logger.warning(f"Unknown engine type: {engine_type}")
            return {}

        # Apply tier-specific overrides
        tier_overrides = self.learning_params.get("tiers", {}).get(capital_tier, {})
        if engine_type in tier_overrides:
            # Deep merge tier overrides
            base_params = self._deep_merge(base_params, tier_overrides[engine_type])

        return base_params

    def _deep_merge(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


# Convenience functions

def create_profile_mapper(
    investment_profiles_path: str = "config/investment_profiles.yaml",
    learning_params_path: str = "config/learning_parameters.yaml",
    ensemble_config_path: str = "config/strategies/ensemble.yaml",
) -> ProfileStrategyMapper:
    """
    Create a ProfileStrategyMapper instance.

    Args:
        investment_profiles_path: Path to investment profiles YAML
        learning_params_path: Path to learning parameters YAML
        ensemble_config_path: Path to ensemble configurations YAML

    Returns:
        Configured ProfileStrategyMapper instance
    """
    return ProfileStrategyMapper(
        investment_profiles_path=investment_profiles_path,
        learning_params_path=learning_params_path,
        ensemble_config_path=ensemble_config_path,
    )


def map_profile_to_strategies(profile: InputProfile) -> StrategyMapping:
    """
    Convenience function to map profile to strategies.

    Args:
        profile: User input profile

    Returns:
        StrategyMapping with complete configuration
    """
    mapper = create_profile_mapper()
    return mapper.create_strategy_mapping(profile)
