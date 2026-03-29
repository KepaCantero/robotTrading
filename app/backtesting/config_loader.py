"""
Configuration Loader for Meta-Analyzer

Loads and manages YAML configuration for all meta-analysis components.
Provides configuration access throughout the backtesting analysis pipeline.

Design Note: Plain Dict Return Type
------------------------------------
This class intentionally returns Dict[str, Any] instead of value objects.
This is a deliberate design choice for the following reasons:

1. **Configuration is not a domain entity**: Configuration data represents
   external settings/parameters, not domain concepts like Money, Portfolio, or Order.

2. **Dynamic structure requirements**: The meta-analyzer configuration needs
   to support arbitrary nested structures (metric_thresholds.sharpe_ratio.excellent)
   that would require excessive boilerplate with value objects.

3. **Read-only access pattern**: This class provides read-only access to loaded
   configuration. All mutation happens through YAML file edits, not through
   the API, reducing the need for value object encapsulation.

4. **Downstream conversion**: When configuration values are used in domain
   operations, they ARE converted to value objects (e.g., Decimal for monetary
   values) by the consuming classes (BacktestConfig, strategies, etc.).

5. **Compatibility**: Many existing components expect dict-based configuration
   for compatibility with YAML serialization/deserialization.

See: BacktestConfigLoader (core/config_loader.py) for an example where
configuration IS converted to a typed value object (BacktestConfig) with
proper Decimal validation.
"""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


class MetricThresholdConfig(BaseModel):
    """Configuration for metric thresholds."""

    excellent: float = Field(gt=0)
    good: float = Field(gt=0)
    warning: float
    critical: float

    model_config = ConfigDict(extra="forbid")

    @field_validator("excellent", "good")
    @classmethod
    def validate_positive_thresholds(cls, v: float, info) -> float:
        """Validate that excellent/good thresholds are positive."""
        if v <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return v


class RollingWindowsConfig(BaseModel):
    """Configuration for rolling windows."""

    sharpe_calculation_days: int = Field(gt=0, default=252)
    volatility_window_days: int = Field(gt=0, default=20)

    model_config = ConfigDict(extra="forbid")


class SeasonalityConfig(BaseModel):
    """Configuration for seasonality analysis."""

    min_history_months: int = Field(gt=0, default=60)
    min_history_days: int = Field(gt=0, default=1260)

    model_config = ConfigDict(extra="forbid")


class RegimeDetectionConfig(BaseModel):
    """Configuration for regime detection."""

    enabled: bool = True
    n_regimes: int = Field(gt=0, default=3)
    volatility_window: int = Field(gt=0, default=20)
    min_data_points: int = Field(gt=0, default=252)

    model_config = ConfigDict(extra="forbid")


class AnalysisConfig(BaseModel):
    """Configuration for analysis settings."""

    rolling_windows: RollingWindowsConfig = Field(default_factory=RollingWindowsConfig)
    seasonality: SeasonalityConfig = Field(default_factory=SeasonalityConfig)
    regime_detection: RegimeDetectionConfig = Field(default_factory=RegimeDetectionConfig)

    model_config = ConfigDict(extra="forbid")


class StaticPlotsConfig(BaseModel):
    """Configuration for static plots."""

    enabled: bool = True
    dpi: int = Field(gt=0, default=300)

    model_config = ConfigDict(extra="forbid")


class InteractiveConfig(BaseModel):
    """Configuration for interactive plots."""

    enabled: bool = True

    model_config = ConfigDict(extra="forbid")


class VisualizationConfig(BaseModel):
    """Configuration for visualization."""

    static_plots: StaticPlotsConfig = Field(default_factory=StaticPlotsConfig)
    interactive: InteractiveConfig = Field(default_factory=InteractiveConfig)

    model_config = ConfigDict(extra="forbid")


class ReportingConfig(BaseModel):
    """Configuration for reporting."""

    include_sections: dict[str, bool] = Field(
        default_factory=lambda: {
            "performance_summary": True,
            "statistical_insights": True,
            "risk_warnings": True,
            "recommendations": True,
        }
    )

    model_config = ConfigDict(extra="forbid")


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = "INFO"

    model_config = ConfigDict(extra="forbid")

    @field_validator("level")
    @classmethod
    def validate_logging_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level: {v}")
        return v.upper()


class AdvancedConfig(BaseModel):
    """Configuration for advanced settings."""

    random_state: int = Field(default=42)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    model_config = ConfigDict(extra="forbid")


class MetaAnalyzerConfig(BaseModel):
    """
    Main configuration model for meta-analyzer.

    Uses Pydantic for validation and extra='forbid' to prevent
    unknown configuration keys.
    """

    metric_thresholds: dict[str, MetricThresholdConfig] = Field(
        default_factory=lambda: {
            "sharpe_ratio": MetricThresholdConfig(
                excellent=2.0, good=1.0, warning=0.5, critical=-0.5
            ),
            "max_drawdown": MetricThresholdConfig(
                excellent=-0.05, good=-0.10, warning=-0.20, critical=-0.50
            ),
            "win_rate": MetricThresholdConfig(
                excellent=0.60, good=0.50, warning=0.40, critical=0.25
            ),
            "profit_factor": MetricThresholdConfig(
                excellent=2.5, good=1.5, warning=1.0, critical=0.5
            ),
        }
    )
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)

    model_config = ConfigDict(extra="forbid")

    def validate_config(self) -> list[str]:
        """
        Validate configuration values and return list of errors.

        Returns:
            Empty list if valid, list of error messages otherwise
        """
        errors = []

        try:
            # Validate metric thresholds
            for metric_name, threshold in self.metric_thresholds.items():
                if threshold.warning <= threshold.critical:
                    errors.append(
                        f"{metric_name}: warning threshold ({threshold.warning}) "
                        f"must be greater than critical ({threshold.critical})"
                    )
                if threshold.good <= threshold.warning:
                    errors.append(
                        f"{metric_name}: good threshold ({threshold.good}) "
                        f"must be greater than warning ({threshold.warning})"
                    )
                if threshold.excellent <= threshold.good:
                    errors.append(
                        f"{metric_name}: excellent threshold ({threshold.excellent}) "
                        f"must be greater than good ({threshold.good})"
                    )

            # Validate analysis config
            if self.analysis.rolling_windows.sharpe_calculation_days < 50:
                errors.append("sharpe_calculation_days must be at least 50")
            if self.analysis.rolling_windows.volatility_window_days < 5:
                errors.append("volatility_window_days must be at least 5")
            if self.analysis.seasonality.min_history_days < 252:
                errors.append("min_history_days must be at least 252 (1 year)")
            if self.analysis.regime_detection.n_regimes < 2:
                errors.append("n_regimes must be at least 2")
            if self.analysis.regime_detection.min_data_points < 100:
                errors.append("min_data_points must be at least 100")

            # Validate visualization config
            if self.visualization.static_plots.dpi < 72:
                errors.append("DPI must be at least 72")

            # Validate logging config
            if self.advanced.logging.level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
                errors.append(f"Invalid logging level: {self.advanced.logging.level}")

        except Exception as e:
            errors.append(f"Validation error: {e}")

        return errors


class ConfigLoader:
    """Load and manage meta-analyzer configuration from YAML file."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to config YAML file. If None, uses default location.
        """
        self.config_path = Path(config_path or "config/meta_analyzer_config.yaml")
        self._pydantic_config: Optional[MetaAnalyzerConfig] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}. Using defaults.")
            self._pydantic_config = MetaAnalyzerConfig()
            return

        try:
            with open(self.config_path) as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    self._pydantic_config = MetaAnalyzerConfig(**loaded)
                else:
                    self._pydantic_config = MetaAnalyzerConfig()
                logger.info(f"Loaded configuration from {self.config_path}")
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error loading config file: {e}. Using defaults.", exc_info=True)
            self._pydantic_config = MetaAnalyzerConfig()
        except Exception as e:
            logger.error(f"Unexpected error loading config: {e}. Using defaults.", exc_info=True)
            self._pydantic_config = MetaAnalyzerConfig()

    @staticmethod
    def _get_default_config() -> dict[str, Any]:
        """Return default configuration when file not available."""
        default = MetaAnalyzerConfig()
        return default.model_dump()

    def get(self, key: str, default: Optional[object] = None) -> Optional[object]:
        """
        Get configuration value by dot-separated key.

        Args:
            key: Dot-separated key (e.g., "metric_thresholds.sharpe_ratio.excellent")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if self._pydantic_config is None:
            return default

        keys = key.split(".")
        value = self._pydantic_config.model_dump()

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def get_section(self, section: str) -> dict[str, Any]:
        """
        Get entire configuration section.

        Args:
            section: Section name (e.g., "metric_thresholds")

        Returns:
            Configuration section as dictionary
        """
        if self._pydantic_config is None:
            return {}
        return self._pydantic_config.model_dump().get(section, {})

    def get_metric_thresholds(self, metric: str) -> dict[str, float]:
        """
        Get thresholds for a specific metric.

        Args:
            metric: Metric name (e.g., "sharpe_ratio")

        Returns:
            Dictionary with threshold levels
        """
        section = self.get_section("metric_thresholds")
        metric_config = section.get(metric, {})
        if isinstance(metric_config, dict):
            return metric_config
        # Handle Pydantic model
        return getattr(metric_config, "model_dump", lambda: metric_config)()

    def get_analysis_config(self) -> dict[str, Any]:
        """Get analysis configuration section."""
        return self.get_section("analysis")

    def get_visualization_config(self) -> dict[str, Any]:
        """Get visualization configuration section."""
        return self.get_section("visualization")

    def get_reporting_config(self) -> dict[str, Any]:
        """Get reporting configuration section."""
        return self.get_section("reporting")

    def get_alerts_config(self) -> dict[str, Any]:
        """Get alerts configuration section."""
        return self.get_section("alerts")

    def get_regime_detection_config(self) -> dict[str, Any]:
        """Get regime detection configuration."""
        return self.get("analysis.regime_detection", {})

    def get_seasonality_config(self) -> dict[str, Any]:
        """Get seasonality analysis configuration."""
        return self.get("analysis.seasonality", {})

    def get_clustering_config(self) -> dict[str, Any]:
        """Get clustering analysis configuration."""
        return self.get("analysis.clustering", {})

    def get_walk_forward_config(self) -> dict[str, Any]:
        """Get walk-forward validation configuration."""
        return self.get("analysis.walk_forward", {})

    def get_alert_threshold(self, metric: str, level: str = "warning") -> Optional[float]:
        """
        Get alert threshold for a metric at specific level.

        Args:
            metric: Metric name
            level: Threshold level ("excellent", "good", "warning", "critical")

        Returns:
            Threshold value or None if not found
        """
        thresholds = self.get_metric_thresholds(metric)
        return thresholds.get(level)

    def is_enabled(self, feature: str) -> bool:
        """
        Check if a feature is enabled in configuration.

        Args:
            feature: Feature path (e.g., "visualization.static_plots.enabled")

        Returns:
            True if enabled, False otherwise
        """
        return self.get(f"{feature}.enabled", False)

    def get_random_state(self) -> int:
        """Get random state for reproducibility."""
        return self.get("advanced.random_state", 42)

    def get_logging_level(self) -> str:
        """Get logging level from configuration."""
        return self.get("advanced.logging.level", "INFO")

    def to_dict(self) -> dict[str, Any]:
        """Get entire configuration as dictionary."""
        if self._pydantic_config is None:
            return {}
        return self._pydantic_config.model_dump()

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
        logger.info("Configuration reloaded")

    def validate_config(self) -> list[str]:
        """
        Validate configuration and return list of errors.

        Returns:
            Empty list if valid, list of error messages otherwise
        """
        if self._pydantic_config is None:
            return ["Configuration not loaded"]

        return self._pydantic_config.validate_config()


# Global configuration instance
_global_config: Optional[ConfigLoader] = None


def get_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    Get global configuration instance (singleton pattern).

    Args:
        config_path: Path to config file (only used on first call or after reset)

    Returns:
        ConfigLoader instance
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigLoader(config_path)

    return _global_config


def reset_config() -> None:
    """Reset global configuration instance."""
    global _global_config
    _global_config = None
