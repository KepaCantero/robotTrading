"""
Configuration Loader for Meta-Analyzer

Loads and manages YAML configuration for all meta-analysis components.
Provides configuration access throughout the backtesting analysis pipeline.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and manage meta-analyzer configuration from YAML file."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to config YAML file. If None, uses default location.
        """
        self.config_path = Path(config_path or "config/meta_analyzer_config.yaml")
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}. Using defaults.")
            self.config = self._get_default_config()
            return

        try:
            with open(self.config_path, "r") as f:
                loaded = yaml.safe_load(f)
                self.config = loaded or {}
                logger.info(f"Loaded configuration from {self.config_path}")
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error loading config file: {e}. Using defaults.", exc_info=True)
            self.config = self._get_default_config()

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Return default configuration when file not available."""
        return {
            "metric_thresholds": {
                "sharpe_ratio": {
                    "excellent": 2.0,
                    "good": 1.0,
                    "warning": 0.5,
                    "critical": -0.5,
                },
                "max_drawdown": {"warning": -0.20, "critical": -0.50},
                "win_rate": {
                    "excellent": 0.60,
                    "good": 0.50,
                    "warning": 0.40,
                    "critical": 0.25,
                },
                "profit_factor": {
                    "excellent": 2.5,
                    "good": 1.5,
                    "warning": 1.0,
                    "critical": 0.5,
                },
            },
            "analysis": {
                "rolling_windows": {
                    "sharpe_calculation_days": 252,
                    "volatility_window_days": 20,
                },
                "seasonality": {
                    "min_history_months": 60,
                    "min_history_days": 1260,
                },
                "regime_detection": {
                    "enabled": True,
                    "n_regimes": 3,
                    "volatility_window": 20,
                    "min_data_points": 252,
                },
            },
            "visualization": {
                "static_plots": {"enabled": True, "dpi": 300},
                "interactive": {"enabled": True},
            },
            "reporting": {
                "include_sections": {
                    "performance_summary": True,
                    "statistical_insights": True,
                    "risk_warnings": True,
                    "recommendations": True,
                }
            },
            "advanced": {"random_state": 42, "logging": {"level": "INFO"}},
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated key.

        Args:
            key: Dot-separated key (e.g., "metric_thresholds.sharpe_ratio.excellent")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.

        Args:
            section: Section name (e.g., "metric_thresholds")

        Returns:
            Configuration section as dictionary
        """
        return self.config.get(section, {})

    def get_metric_thresholds(self, metric: str) -> Dict[str, float]:
        """
        Get thresholds for a specific metric.

        Args:
            metric: Metric name (e.g., "sharpe_ratio")

        Returns:
            Dictionary with threshold levels
        """
        return self.get_section("metric_thresholds").get(metric, {})

    def get_analysis_config(self) -> Dict[str, Any]:
        """Get analysis configuration section."""
        return self.get_section("analysis")

    def get_visualization_config(self) -> Dict[str, Any]:
        """Get visualization configuration section."""
        return self.get_section("visualization")

    def get_reporting_config(self) -> Dict[str, Any]:
        """Get reporting configuration section."""
        return self.get_section("reporting")

    def get_alerts_config(self) -> Dict[str, Any]:
        """Get alerts configuration section."""
        return self.get_section("alerts")

    def get_regime_detection_config(self) -> Dict[str, Any]:
        """Get regime detection configuration."""
        return self.get("analysis.regime_detection", {})

    def get_seasonality_config(self) -> Dict[str, Any]:
        """Get seasonality analysis configuration."""
        return self.get("analysis.seasonality", {})

    def get_clustering_config(self) -> Dict[str, Any]:
        """Get clustering analysis configuration."""
        return self.get("analysis.clustering", {})

    def get_walk_forward_config(self) -> Dict[str, Any]:
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

    def to_dict(self) -> Dict[str, Any]:
        """Get entire configuration as dictionary."""
        return self.config.copy()

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
        logger.info("Configuration reloaded")


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
