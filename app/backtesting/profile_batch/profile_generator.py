"""
Profile Generator Module

Generates backtest profile combinations for batch testing.
Handles profile creation, configuration mapping, and tier conversions.

Responsibilities:
- Generate profile combinations (objectives × risks × tiers × horizons)
- Map profiles to backtest configurations
- Handle tier mapping conversions
- Load investment horizons from config
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Union

import yaml

from app.domain.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.services.profile_driven_trading.profile_strategy_mapper import create_profile_mapper
from app.shared.utils.tier_mapper import map_profile_tier_to_config

logger = logging.getLogger(__name__)

# Type aliases for better type safety
ConfigDict = Dict[str, Any]
MetricsDict = Dict[str, Union[float, int, str, bool, None]]
StrategyConfigDict = Dict[str, Any]


class ProfileGenerator:
    """
    Generates backtest profiles and configurations.

    Creates profile combinations from objectives, risk tolerances,
    capital tiers, and investment horizons. Maps profiles to
    backtest configurations using ProfileStrategyMapper.
    """

    def __init__(self, config_path: str | Path):
        """
        Initialize profile generator.

        Args:
            config_path: Path to configuration YAML file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Initialize ProfileStrategyMapper
        try:
            self.profile_mapper = create_profile_mapper()
            logger.info("ProfileStrategyMapper initialized successfully")
        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
            logger.warning(f"Failed to initialize ProfileStrategyMapper: {e}")
            self.profile_mapper = None

    def _load_config(self) -> ConfigDict:
        """Load configuration from YAML file."""
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _load_investment_horizons(self) -> List[int]:
        """
        Load investment horizons from configuration.

        Supports both dict format (with labels) and list format.
        Falls back to default values if not configured.

        Returns:
            List of horizon values in months (positive integers)
        """
        default_horizons = [12, 24, 36, 60]
        horizons_config = self.config.get("investment_horizons")

        if horizons_config is None:
            logger.warning("No investment_horizons in config, using defaults")
            return default_horizons

        # Handle dict format
        if isinstance(horizons_config, dict):
            horizons = list(horizons_config.values())
            logger.info(f"Loaded investment horizons from dict: {horizons_config}")
        elif isinstance(horizons_config, list):
            horizons = horizons_config
            logger.info(f"Loaded investment horizons from list: {horizons}")
        else:
            logger.error(f"Invalid investment_horizons format: {type(horizons_config)}")
            return default_horizons

        # Validate horizons
        validated_horizons = []
        for horizon in horizons:
            try:
                horizon_int = int(horizon)
            except (ValueError, TypeError):
                logger.error(f"Invalid horizon value '{horizon}', must be integer")
                continue

            if horizon_int <= 0:
                logger.error(f"Invalid horizon value {horizon_int}, must be positive")
                continue

            if horizon_int < 1 or horizon_int > 360:
                logger.warning(f"Horizon {horizon_int} is outside typical range")

            validated_horizons.append(horizon_int)

        if not validated_horizons:
            logger.error("No valid horizons found, using defaults")
            return default_horizons

        return validated_horizons

    def generate_all_profiles(self) -> List[InputProfile]:
        """
        Generate all profile combinations.

        Combinations:
        - 5 objectives
        - 3 risk tolerances (bajo, medio, alto)
        - 3 capital tiers (bajo, medio, alto)
        - N investment horizons (loaded from config)

        Returns:
            List of InputProfile objects
        """
        profiles = []

        # Generate combinations
        objectives = list(ObjectivoInversion)
        risk_tolerances = list(RiskTolerance)
        capital_tiers = ["bajo", "medio", "alto"]
        horizons = self._load_investment_horizons()

        capital_tiers_config = self.config.get("capital_tiers", {})

        for objective in objectives:
            for risk in risk_tolerances:
                for tier in capital_tiers:
                    for horizon in horizons:
                        capital = Decimal(str(capital_tiers_config.get(tier, 100000)))

                        profile = InputProfile(
                            capital_initial=capital,
                            objetivo_inversion=objective,
                            risk_tolerance=risk,
                            investment_horizon=horizon,
                        )

                        profiles.append(profile)

        expected_count = len(objectives) * len(risk_tolerances) * len(capital_tiers) * len(horizons)
        logger.info(
            f"Generated {len(profiles)} profile combinations "
            f"({len(objectives)} objectives × {len(risk_tolerances)} risks × "
            f"{len(capital_tiers)} tiers × {len(horizons)} horizons = {expected_count})"
        )
        return profiles

    def get_capital_tier_key(self, profile: InputProfile) -> str:
        """
        Map capital_flag to config tier key using unified tier mapping.

        Args:
            profile: InputProfile

        Returns:
            Mapped tier key for config lookups (bajo, medio, or alto)
        """
        try:
            return map_profile_tier_to_config(profile.capital_flag, target_format="spanish")
        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
            logger.warning(f"Tier mapper failed for {profile.capital_flag}: {e}")
            tier_map = {"small": "bajo", "medium": "medio", "large": "alto"}
            return tier_map.get(profile.capital_flag, "medio")

    def create_profile_config(self, profile: InputProfile, output_dir: Path) -> ConfigDict:
        """
        Create backtest configuration for a profile.

        Args:
            profile: InputProfile to create configuration for
            output_dir: Directory for temporary config files

        Returns:
            Configuration dictionary for backtesting
        """
        # Try to use ProfileStrategyMapper if available
        if self.profile_mapper is not None:
            try:
                strategy_config = self.profile_mapper.map_profile_to_strategies(profile)

                enabled_strategies = strategy_config.get("enabled_strategies", [])
                risk_params = strategy_config.get("risk_params", {})
                trading_params = strategy_config.get("trading_params", {})
                learning_engines = strategy_config.get("learning_engines", [])
                ensemble_config = strategy_config.get("ensemble_config", {})

                logger.info(
                    f"Profile {profile.input_id}: mapped to {len(enabled_strategies)} strategies, "
                    f"{len(learning_engines)} learning engines"
                )

                config = {
                    "input": {
                        "initial_capital": float(profile.capital_initial),
                        "start_date": self.config.get("backtest_period", {}).get(
                            "start_date", "2020-01-01"
                        ),
                        "end_date": self.config.get("backtest_period", {}).get(
                            "end_date", "2023-12-31"
                        ),
                        "symbols": self.config.get(
                            "symbols", ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
                        ),
                    },
                    "modules": {
                        "enabled_strategies": enabled_strategies,
                        **self.config.get("modules", {}),
                    },
                    "risk_management": {
                        "max_position_size": profile.capital_initial
                        * Decimal(str(risk_params.get("max_position_size", 0.20))),
                        "max_sector_allocation": risk_params.get("max_sector_allocation", 0.30),
                        "leverage": risk_params.get("leverage", 1.0),
                        "risk_profile": risk_params.get("risk_profile", 4),
                        **risk_params,
                    },
                    "strategy": {
                        "learning_mode": learning_engines[0] if learning_engines else "supervised",
                        "learning_engines": learning_engines,
                        "ensemble_config": ensemble_config,
                        "objective": strategy_config.get("objective"),
                        "capital_tier": strategy_config.get("capital_tier"),
                        **trading_params,
                    },
                    "reporting": self.config.get("reporting", {}),
                    "_strategy_mapping": {
                        "enabled_strategies": enabled_strategies,
                        "learning_engines": learning_engines,
                        "ensemble_config": ensemble_config,
                        "objective": strategy_config.get("objective"),
                        "capital_tier": strategy_config.get("capital_tier"),
                    },
                }

                return config

            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.warning(f"ProfileStrategyMapper failed: {e}, using manual config")

        # Fallback: Manual configuration
        logger.info(f"Using manual configuration for profile {profile.input_id}")

        risk_key = profile.risk_tolerance.value
        objective_key = profile.objetivo_inversion.value

        risk_params = self.config.get("risk_parameters", {}).get(risk_key, {})
        objective_params = self.config.get("objective_parameters", {}).get(objective_key, {})

        config = {
            "input": {
                "initial_capital": float(profile.capital_initial),
                "start_date": self.config.get("backtest_period", {}).get(
                    "start_date", "2020-01-01"
                ),
                "end_date": self.config.get("backtest_period", {}).get("end_date", "2023-12-31"),
                "symbols": self.config.get("symbols", ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]),
            },
            "modules": self.config.get("modules", {}),
            "risk_management": {
                **risk_params,
                "max_position_size": profile.capital_initial
                * Decimal(str(risk_params.get("max_position_pct", 0.1))),
            },
            "strategy": {
                **objective_params,
                "learning_mode": "supervised",
            },
            "reporting": self.config.get("reporting", {}),
            "_strategy_mapping": {
                "enabled_strategies": [],
                "learning_engines": [],
                "ensemble_config": {},
                "objective": objective_key,
                "capital_tier": self.get_capital_tier_key(profile),
            },
        }

        return config

    def create_profile_id(self, profile: InputProfile) -> str:
        """
        Create unique profile ID.

        Args:
            profile: InputProfile

        Returns:
            Profile ID string
        """
        capital_tier_key = self.get_capital_tier_key(profile)
        return (
            f"{profile.objetivo_inversion.value}_"
            f"{profile.risk_tolerance.value}_"
            f"{capital_tier_key}_"
            f"{profile.investment_horizon}m"
        )
