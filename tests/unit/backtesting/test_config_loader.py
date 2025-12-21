"""
Tests for Configuration Loader - YAML configuration management.

Tests config loading, parsing, access patterns, and error handling.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from app.backtesting.config_loader import ConfigLoader, get_config, reset_config


class TestConfigLoader:
    """Tests for ConfigLoader class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config YAML file."""
        config_data = {
            "metric_thresholds": {
                "sharpe_ratio": {
                    "excellent": 2.0,
                    "good": 1.0,
                    "warning": 0.5,
                    "critical": -0.5,
                },
                "max_drawdown": {"warning": -0.20, "critical": -0.50},
            },
            "analysis": {
                "rolling_windows": {
                    "sharpe_calculation_days": 252,
                    "volatility_window_days": 20,
                },
                "regime_detection": {
                    "enabled": True,
                    "n_regimes": 3,
                    "volatility_window": 20,
                },
            },
            "visualization": {
                "static_plots": {"enabled": True, "dpi": 300},
                "interactive": {"enabled": True, "template": "plotly_dark"},
            },
            "reporting": {
                "include_sections": {
                    "performance_summary": True,
                    "risk_warnings": True,
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink()

    @pytest.fixture
    def loader(self, temp_config_file):
        """Create ConfigLoader with temporary config."""
        return ConfigLoader(temp_config_file)

    def test_config_file_loading(self, loader):
        """Test that config file is loaded correctly."""
        assert loader.config is not None
        assert len(loader.config) > 0
        assert "metric_thresholds" in loader.config

    def test_get_metric_thresholds(self, loader):
        """Test getting metric thresholds."""
        thresholds = loader.get_metric_thresholds("sharpe_ratio")
        assert thresholds["excellent"] == 2.0
        assert thresholds["good"] == 1.0
        assert thresholds["warning"] == 0.5

    def test_get_with_dot_notation(self, loader):
        """Test accessing nested config with dot notation."""
        value = loader.get("metric_thresholds.sharpe_ratio.excellent")
        assert value == 2.0

    def test_get_nested_section(self, loader):
        """Test getting nested configuration section."""
        analysis = loader.get_section("analysis")
        assert "rolling_windows" in analysis
        assert analysis["rolling_windows"]["sharpe_calculation_days"] == 252

    def test_get_with_default(self, loader):
        """Test get with default value for missing key."""
        value = loader.get("nonexistent.key", default=99)
        assert value == 99

    def test_get_analysis_config(self, loader):
        """Test getting analysis configuration."""
        config = loader.get_analysis_config()
        assert "rolling_windows" in config
        assert "regime_detection" in config

    def test_get_visualization_config(self, loader):
        """Test getting visualization configuration."""
        config = loader.get_visualization_config()
        assert "static_plots" in config
        assert "interactive" in config

    def test_get_reporting_config(self, loader):
        """Test getting reporting configuration."""
        config = loader.get_reporting_config()
        assert "include_sections" in config

    def test_get_regime_detection_config(self, loader):
        """Test getting regime detection configuration."""
        config = loader.get_regime_detection_config()
        assert config["enabled"] is True
        assert config["n_regimes"] == 3

    def test_get_alert_threshold(self, loader):
        """Test getting alert threshold for metric."""
        threshold = loader.get_alert_threshold("sharpe_ratio", "excellent")
        assert threshold == 2.0

        threshold = loader.get_alert_threshold("max_drawdown", "critical")
        assert threshold == -0.50

    def test_get_alert_threshold_missing_metric(self, loader):
        """Test getting threshold for missing metric."""
        threshold = loader.get_alert_threshold("nonexistent_metric", "warning")
        assert threshold is None

    def test_is_enabled_true(self, loader):
        """Test checking if feature is enabled (true case)."""
        assert loader.is_enabled("visualization.static_plots") is True
        assert loader.is_enabled("analysis.regime_detection") is True

    def test_is_enabled_false(self, loader):
        """Test checking if feature is enabled (false case)."""
        # Create loader with feature disabled
        config_data = {
            "some_feature": {"enabled": False},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            assert loader.is_enabled("some_feature") is False
        finally:
            Path(temp_path).unlink()

    def test_is_enabled_missing_feature(self, loader):
        """Test checking if missing feature is enabled."""
        assert loader.is_enabled("nonexistent.feature") is False

    def test_get_random_state(self, loader):
        """Test getting random state value."""
        # Default should be available
        state = loader.get_random_state()
        assert isinstance(state, int)

    def test_get_logging_level(self, loader):
        """Test getting logging level."""
        level = loader.get_logging_level()
        assert isinstance(level, str)
        assert level in ["DEBUG", "INFO", "WARNING", "ERROR"]

    def test_to_dict(self, loader):
        """Test converting config to dictionary."""
        config_dict = loader.to_dict()
        assert isinstance(config_dict, dict)
        assert "metric_thresholds" in config_dict
        assert len(config_dict) > 0

    def test_missing_config_file(self):
        """Test loading non-existent config file."""
        loader = ConfigLoader("/nonexistent/path/config.yaml")
        # Should use defaults
        assert loader.config is not None
        assert len(loader.config) > 0

    def test_invalid_yaml_file(self):
        """Test loading invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            # Should fall back to defaults
            assert loader.config is not None
        finally:
            Path(temp_path).unlink()

    def test_empty_config_file(self):
        """Test loading empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            # Should use defaults
            assert loader.config is not None
        finally:
            Path(temp_path).unlink()

    def test_reload_config(self, temp_config_file):
        """Test reloading configuration."""
        loader = ConfigLoader(temp_config_file)
        original_value = loader.get("metric_thresholds.sharpe_ratio.excellent")

        # Modify config file
        config_data = {
            "metric_thresholds": {
                "sharpe_ratio": {
                    "excellent": 3.0,  # Changed value
                }
            }
        }
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        loader.reload()
        new_value = loader.get("metric_thresholds.sharpe_ratio.excellent")
        assert new_value == 3.0
        assert original_value != new_value

    def test_default_config_structure(self):
        """Test that default config has expected structure."""
        loader = ConfigLoader("/nonexistent/path")
        config = loader.to_dict()

        # Check main sections exist
        assert "metric_thresholds" in config
        assert "analysis" in config
        assert "visualization" in config
        assert "reporting" in config
        assert "advanced" in config

    def test_metric_thresholds_levels(self, loader):
        """Test all threshold levels for a metric."""
        levels = ["excellent", "good", "warning", "critical"]
        for level in levels:
            threshold = loader.get_alert_threshold("sharpe_ratio", level)
            if threshold is not None:
                assert isinstance(threshold, (int, float))

    def test_get_section_nonexistent(self, loader):
        """Test getting non-existent section returns empty dict."""
        section = loader.get_section("nonexistent_section")
        assert section == {}

    def test_multiple_loaders_independence(self, temp_config_file):
        """Test that multiple loader instances are independent."""
        loader1 = ConfigLoader(temp_config_file)
        loader2 = ConfigLoader(temp_config_file)

        # Modify one loader's config in memory (not the file)
        loader1.config["metric_thresholds"]["sharpe_ratio"]["excellent"] = 5.0

        # Other loader should not be affected
        assert (
            loader2.get("metric_thresholds.sharpe_ratio.excellent") == 2.0
        )

    def test_clustering_config(self, loader):
        """Test getting clustering configuration."""
        config = loader.get_clustering_config()
        assert isinstance(config, dict)

    def test_walk_forward_config(self, loader):
        """Test getting walk-forward configuration."""
        config = loader.get_walk_forward_config()
        assert isinstance(config, dict)

    def test_seasonality_config(self, loader):
        """Test getting seasonality configuration."""
        config = loader.get_seasonality_config()
        assert isinstance(config, dict)

    def test_config_with_none_values(self):
        """Test config handling with None values."""
        config_data = {
            "test_section": {
                "test_key": None,
                "another_key": "value",
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            # Should handle None values gracefully
            assert loader.get("test_section.test_key") is None
            assert loader.get("test_section.another_key") == "value"
        finally:
            Path(temp_path).unlink()


class TestGlobalConfig:
    """Tests for global configuration singleton."""

    def test_get_config_singleton(self):
        """Test that get_config returns singleton instance."""
        reset_config()

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reset_config(self):
        """Test resetting global config instance."""
        reset_config()

        config1 = get_config()
        reset_config()
        config2 = get_config()

        assert config1 is not config2

    def test_get_config_with_path(self):
        """Test providing custom config path to get_config."""
        reset_config()

        config_data = {
            "test": "value",
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            config = get_config(temp_path)
            assert config.get("test") == "value"
        finally:
            Path(temp_path).unlink()
            reset_config()


class TestConfigIntegration:
    """Integration tests for config usage patterns."""

    @pytest.fixture
    def loader(self):
        """Create loader with default config."""
        return ConfigLoader("/nonexistent/path")

    def test_complete_workflow(self, loader):
        """Test typical config access workflow."""
        # Get analysis config
        analysis = loader.get_analysis_config()
        assert analysis is not None

        # Get regime detection config
        regime_config = loader.get_regime_detection_config()
        assert regime_config.get("enabled") in [True, False]

        # Check if visualization is enabled
        viz_enabled = loader.is_enabled("visualization.static_plots")
        assert isinstance(viz_enabled, bool)

        # Get random state for reproducibility
        random_state = loader.get_random_state()
        assert isinstance(random_state, int)

    def test_alert_threshold_workflow(self, loader):
        """Test typical alert threshold access workflow."""
        # Get thresholds for a metric
        thresholds = loader.get_metric_thresholds("sharpe_ratio")
        assert len(thresholds) > 0

        # Check specific level
        excellent = loader.get_alert_threshold("sharpe_ratio", "excellent")
        assert excellent is None or isinstance(excellent, (int, float))

    def test_config_dict_export(self, loader):
        """Test exporting entire config as dictionary."""
        config_dict = loader.to_dict()

        # Verify it's a complete, navigable dictionary
        assert isinstance(config_dict, dict)
        assert all(isinstance(k, str) for k in config_dict.keys())

    def test_metric_threshold_hierarchy(self, loader):
        """Test accessing metric thresholds in hierarchy."""
        thresholds = loader.get_metric_thresholds("sharpe_ratio")

        # Verify structure
        if thresholds:
            assert any(k in thresholds for k in ["excellent", "good", "warning", "critical"])
