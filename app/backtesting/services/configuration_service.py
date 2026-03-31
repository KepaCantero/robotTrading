"""
Configuration Service

Handles loading, validation, and management of configuration files
for profile batch backtesting.

Responsibilities:
- Load YAML configurations
- Validate configuration settings
- Load and validate investment horizons
- Provide configuration access methods
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import yaml

logger = logging.getLogger(__name__)

ConfigDict = dict[str, Any]


class ConfigurationService:
    """
    Service for managing configuration loading and validation.

    Handles loading YAML configuration files and validating that
    all required settings are present and valid.
    """

    def __init__(self, config_path: str) -> None:
        """
        Initialize configuration service.

        Args:
            config_path: Path to configuration YAML file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._validate_configurations()

    def _load_config(self) -> ConfigDict:
        """
        Load configuration from YAML file.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        try:
            with open(self.config_path) as f:
                loaded = yaml.safe_load(f)
                return cast("ConfigDict", loaded if isinstance(loaded, dict) else {})
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML configuration: {e}")
            raise

    def _validate_configurations(self) -> None:
        """
        Validate that all required configurations are present and valid.

        This method checks:
        1. Capital tiers configuration exists
        2. Investment horizons configuration exists
        3. Optimization configuration exists
        4. Validation configuration exists

        Raises:
            ValueError: If a required configuration is missing or invalid
        """
        # Validate capital tiers
        capital_tiers = self.get_capital_tiers()
        if not capital_tiers:
            raise ValueError("Capital tiers configuration is missing")
        required_tier_keys = ["micro", "small", "medium", "large", "institutional"]
        for tier in required_tier_keys:
            if tier not in capital_tiers:
                logger.warning(f"Missing capital tier: {tier}")

        # Validate investment horizons
        horizons = self.get_horizons_config()
        if not horizons:
            raise ValueError("Investment horizons configuration is missing")
        required_horizon_keys = ["short", "medium", "long"]
        for horizon in required_horizon_keys:
            if horizon not in horizons:
                logger.warning(f"Missing investment horizon: {horizon}")

        # Validate optimization config
        optimization_config = self.get_optimization_config()
        if not optimization_config:
            logger.warning("Optimization configuration is missing, using defaults")

        # Validate validation config
        validation_config = self.get_validation_config()
        if not validation_config:
            logger.warning("Validation configuration is missing, using defaults")

        logger.debug("Configuration validation completed")

    def get_capital_tiers(self) -> ConfigDict:
        """Get capital tiers configuration."""
        result = self.config.get("capital_tiers", {})
        return result if isinstance(result, dict) else {}

    def get_horizons_config(self) -> ConfigDict:
        """Get investment horizons configuration."""
        result = self.config.get("investment_horizons", {})
        return result if isinstance(result, dict) else {}

    def get_optimization_config(self) -> ConfigDict:
        """Get optimization configuration."""
        result = self.config.get("optimization", {})
        return result if isinstance(result, dict) else {}

    def get_validation_config(self) -> ConfigDict:
        """Get validation configuration."""
        result = self.config.get("validation", {})
        return result if isinstance(result, dict) else {}

    def get_acceptance_criteria(self) -> ConfigDict:
        """Get acceptance criteria configuration."""
        result = self.config.get("acceptance_criteria", {})
        return result if isinstance(result, dict) else {}

    def get_backtest_period(self) -> ConfigDict:
        """Get backtest period configuration."""
        result = self.config.get("backtest_period", {})
        return result if isinstance(result, dict) else {}

    def get_symbols(self) -> list[str]:
        """Get symbols configuration."""
        result = self.config.get("symbols", ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"])
        return result if isinstance(result, list) else ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    def get_output_dir(self) -> str:
        """Get output directory configuration."""
        result = self.config.get("output_dir", "results/profile_batch_backtesting")
        return str(result) if result is not None else "results/profile_batch_backtesting"

    def get_database_url(self) -> str:
        """Get database URL configuration."""
        db_config = self.config.get("database", {})
        if isinstance(db_config, dict):
            url = db_config.get("url", "sqlite:///profile_backtest_results.db")
            return str(url) if url is not None else "sqlite:///profile_backtest_results.db"
        return "sqlite:///profile_backtest_results.db"

    def get_risk_parameters(self, risk_key: str) -> ConfigDict:
        """
        Get risk parameters for a specific risk level.

        Args:
            risk_key: Risk level key (e.g., "bajo", "medio", "alto")

        Returns:
            Risk parameters dictionary
        """
        params = self.config.get("risk_parameters", {})
        if not isinstance(params, dict):
            return {}
        result = params.get(risk_key, {})
        return result if isinstance(result, dict) else {}

    def get_objective_parameters(self, objective_key: str) -> ConfigDict:
        """
        Get objective parameters for a specific objective.

        Args:
            objective_key: Objective key (e.g., "maximizar_capital")

        Returns:
            Objective parameters dictionary
        """
        params = self.config.get("objective_parameters", {})
        if not isinstance(params, dict):
            return {}
        result = params.get(objective_key, {})
        return result if isinstance(result, dict) else {}

    def get_modules_config(self) -> ConfigDict:
        """Get modules configuration."""
        result = self.config.get("modules", {})
        return result if isinstance(result, dict) else {}

    def get_reporting_config(self) -> ConfigDict:
        """Get reporting configuration."""
        result = self.config.get("reporting", {})
        return result if isinstance(result, dict) else {}

    def load_investment_horizons(self) -> list[int]:
        """
        Load investment horizons from configuration.

        Supports both dict format (with labels) and list format.
        Falls back to default values if not configured.

        Returns:
            List of horizon values in months (positive integers)

        Examples:
            Dict format:
                investment_horizons:
                    short: 12
                    medium: 24
                    long: 36
                    very_long: 60

            List format:
                investment_horizons: [12, 24, 36, 60]
        """
        default_horizons = [12, 24, 36, 60]

        # Get horizons from config
        horizons_config = self.get_horizons_config()
        if horizons_config is None:
            logger.warning("No investment_horizons in config, using defaults: [12, 24, 36, 60]")
            return default_horizons

        # Handle dict format (e.g., {short: 12, medium: 24, ...})
        if isinstance(horizons_config, dict):
            horizons = list(horizons_config.values())
            logger.info(f"Loaded investment horizons from dict: {horizons_config}")
        # Handle list format (e.g., [12, 24, 36, 60])
        elif isinstance(horizons_config, list):
            horizons = horizons_config
            logger.info(f"Loaded investment horizons from list: {horizons}")
        else:
            logger.error(
                f"Invalid investment_horizons format: {type(horizons_config)}. "
                f"Expected dict or list, using defaults."
            )
            return default_horizons

        # Validate horizons
        validated_horizons = []
        for horizon in horizons:
            # Must be integer or convertible to integer
            try:
                horizon_int = int(horizon)
            except (ValueError, TypeError):
                logger.error(f"Invalid horizon value '{horizon}', must be integer. Skipping.")
                continue

            # Must be positive
            if horizon_int <= 0:
                logger.error(f"Invalid horizon value {horizon_int}, must be positive. Skipping.")
                continue

            # Reasonable range check (1 month to 30 years)
            if horizon_int < 1 or horizon_int > 360:
                logger.warning(
                    f"Horizon {horizon_int} months is outside typical range (1-360). "
                    f"Using anyway, but please verify."
                )
            validated_horizons.append(horizon_int)

        if not validated_horizons:
            logger.error("No valid horizons found after validation, using defaults")
            return default_horizons

        logger.info(f"Validated investment horizons: {validated_horizons}")
        return validated_horizons
