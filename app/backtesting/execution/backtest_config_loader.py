"""
Backtest Config Loader - Loads and validates backtest configurations

This module is responsible for loading backtest configurations from
YAML files and validating them according to business rules.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator, ConfigDict
import yaml

logger = logging.getLogger(__name__)


class InputConfig(BaseModel):
    """Configuration for input data."""

    start_date: str = Field(default="2020-01-01")
    end_date: str = Field(default="2023-12-31")
    symbols: List[str] = Field(default_factory=lambda: ["AAPL", "MSFT", "GOOGL"])

    model_config = ConfigDict(extra="forbid")

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v: list[str]) -> list[str]:
        """Validate that symbols list is non-empty."""
        if not v:
            raise ValueError("symbols list cannot be empty")
        return v


class StrategyConfig(BaseModel):
    """Configuration for strategy."""

    name: str = Field(default="momentum_modular")
    parameters: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that strategy name is non-empty."""
        if not v or not v.strip():
            raise ValueError("strategy name cannot be empty")
        return v


class CapitalConfig(BaseModel):
    """Configuration for capital."""

    initial: float = Field(default=100000, gt=0)
    currency: str = Field(default="USD")

    model_config = ConfigDict(extra="forbid")

    @field_validator("initial")
    @classmethod
    def validate_initial_capital(cls, v: float) -> float:
        """Validate that initial capital is positive."""
        if v <= 0:
            raise ValueError("initial capital must be positive")
        return v


class RiskConfig(BaseModel):
    """Configuration for risk management."""

    max_position_size: float = Field(default=0.10, ge=0, le=1)
    stop_loss: float = Field(default=0.03, ge=0, le=1)
    take_profit: float = Field(default=0.06, ge=0)

    model_config = ConfigDict(extra="forbid")


class ExecutionConfig(BaseModel):
    """Configuration for execution."""

    commission: float = Field(default=0.001, ge=0)
    slippage: float = Field(default=0.0001, ge=0)

    model_config = ConfigDict(extra="forbid")


class ReportingConfig(BaseModel):
    """Configuration for reporting."""

    output_directory: str = Field(default="results")
    save_results: bool = Field(default=True)

    model_config = ConfigDict(extra="forbid")


class ParallelizationConfig(BaseModel):
    """Configuration for parallelization."""

    enabled: bool = Field(default=True)
    max_workers: int | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")


class MetaAnalysisConfig(BaseModel):
    """Configuration for meta-analysis."""

    enabled: bool = Field(default=False)
    enable_audit: bool = Field(default=True)
    enable_storage: bool = Field(default=True)
    enable_analysis: bool = Field(default=True)

    model_config = ConfigDict(extra="forbid")


class BacktestConfigSettings(BaseModel):
    """
    Complete backtest configuration settings.

    Uses Pydantic for validation and extra='forbid' to prevent
    unknown configuration keys.
    """

    input: InputConfig = Field(default_factory=InputConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    capital: CapitalConfig = Field(default_factory=CapitalConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    parallelization: ParallelizationConfig = Field(default_factory=ParallelizationConfig)
    meta_analysis: MetaAnalysisConfig = Field(default_factory=MetaAnalysisConfig)

    model_config = ConfigDict(extra="forbid")

    def validate_config(self) -> List[str]:
        """
        Validate configuration and return list of errors.

        Returns:
            Empty list if valid, list of error messages otherwise
        """
        errors = []

        try:
            # Validate input section
            if not self.input.symbols:
                errors.append("Input must have at least one symbol")

            # Validate strategy section
            if not self.strategy.name or not self.strategy.name.strip():
                errors.append("Strategy must have a name")

            # Validate capital section
            if self.capital.initial <= 0:
                errors.append("Initial capital must be positive")

            # Validate risk parameters
            if self.risk.max_position_size <= 0 or self.risk.max_position_size > 1:
                errors.append("Max position size must be between 0 and 1")
            if self.risk.stop_loss < 0 or self.risk.stop_loss > 1:
                errors.append("Stop loss must be between 0 and 1")
            if self.risk.take_profit < 0:
                errors.append("Take profit must be non-negative")

            # Validate execution parameters
            if self.execution.commission < 0:
                errors.append("Commission must be non-negative")
            if self.execution.slippage < 0:
                errors.append("Slippage must be non-negative")

        except Exception as e:
            errors.append(f"Validation error: {e}")

        return errors


class BacktestConfigLoader:
    """
    Loads and validates backtest configurations from YAML files.

    This class is responsible for:
    - Loading YAML configuration files
    - Validating required fields using Pydantic
    - Providing default values
    - Merging with base configurations
    """

    DEFAULT_CONFIG = {
        "input": {
            "start_date": "2020-01-01",
            "end_date": "2023-12-31",
            "symbols": ["AAPL", "MSFT", "GOOGL"],
        },
        "strategy": {
            "name": "momentum_modular",
            "parameters": {},
        },
        "capital": {
            "initial": 100000,
            "currency": "USD",
        },
        "risk": {
            "max_position_size": 0.10,
            "stop_loss": 0.03,
            "take_profit": 0.06,
        },
        "execution": {
            "commission": 0.001,
            "slippage": 0.0001,
        },
        "reporting": {
            "output_directory": "results",
            "save_results": True,
        },
        "parallelization": {
            "enabled": True,
            "max_workers": None,
        },
        "meta_analysis": {
            "enabled": False,
            "enable_audit": True,
            "enable_storage": True,
            "enable_analysis": True,
        },
    }

    def __init__(self, config_path: str):
        """
        Initialize config loader.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.raw_config: Dict[str, Any] = self._load_config()
        self._pydantic_config: BacktestConfigSettings | None = None

        # Try to create Pydantic config for validation
        try:
            self._pydantic_config = BacktestConfigSettings(**self.raw_config)
        except Exception as e:
            logger.warning(f"Failed to create Pydantic config: {e}")

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Configuration dictionary

        Raises:
            RuntimeError: If configuration cannot be loaded
        """
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            # Merge with defaults
            merged_config = self._merge_with_defaults(config or {})
            logger.info(f"Loaded configuration from {self.config_path}")
            return merged_config

        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_path}", exc_info=True)
            return self.DEFAULT_CONFIG.copy()
        except (ValueError, KeyError, TypeError) as e:
            logger.error(
                f"Error parsing YAML config from {self.config_path}: {e}",
                exc_info=True
            )
            return self.DEFAULT_CONFIG.copy()
        except OSError as e:
            logger.error(
                f"OS error reading config file {self.config_path}: {e}",
                exc_info=True
            )
            return self.DEFAULT_CONFIG.copy()

    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge loaded config with defaults.

        Args:
            config: Loaded configuration

        Returns:
            Merged configuration
        """
        merged = self.DEFAULT_CONFIG.copy()

        for key, value in config.items():
            if key in merged and isinstance(merged[key], dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value

        return merged

    def get_backtest_config(self) -> Dict[str, Any]:
        """
        Get backtest-specific configuration.

        Returns:
            Backtest configuration dictionary
        """
        return {
            "strategy_name": self.raw_config.get("strategy", {}).get("name", ""),
            "strategy_params": self.raw_config.get("strategy", {}).get("parameters", {}),
            "symbols": self.raw_config.get("input", {}).get("symbols", []),
            "start_date": self.raw_config.get("input", {}).get("start_date"),
            "end_date": self.raw_config.get("input", {}).get("end_date"),
            "initial_capital": self.raw_config.get("capital", {}).get("initial", 100000),
            "max_position_size": self.raw_config.get("risk", {}).get("max_position_size", 0.10),
            "stop_loss": self.raw_config.get("risk", {}).get("stop_loss", 0.03),
            "take_profit": self.raw_config.get("risk", {}).get("take_profit", 0.06),
            "commission": self.raw_config.get("execution", {}).get("commission", 0.001),
            "slippage": self.raw_config.get("execution", {}).get("slippage", 0.0001),
            "output_directory": self.raw_config.get("reporting", {}).get(
                "output_directory", "results"
            ),
        }

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Use Pydantic validation if available
        if self._pydantic_config:
            return self._pydantic_config.validate_config()

        # Fallback to manual validation
        # Validate required fields
        required_fields = ["input", "strategy", "capital"]
        for field in required_fields:
            if field not in self.raw_config:
                errors.append(f"Missing required field: {field}")

        # Validate input section
        if "input" in self.raw_config:
            input_config = self.raw_config["input"]
            if "symbols" not in input_config or not input_config["symbols"]:
                errors.append("Input must have at least one symbol")

        # Validate strategy section
        if "strategy" in self.raw_config:
            strategy_config = self.raw_config["strategy"]
            if "name" not in strategy_config or not strategy_config["name"]:
                errors.append("Strategy must have a name")

        # Validate capital section
        if "capital" in self.raw_config:
            capital_config = self.raw_config["capital"]
            initial_capital = capital_config.get("initial", 0)
            if initial_capital <= 0:
                errors.append("Initial capital must be positive")

        return errors

    def is_valid(self) -> bool:
        """
        Check if configuration is valid.

        Returns:
            True if configuration is valid
        """
        return len(self.validate()) == 0
