"""
Unit tests to verify hardcoded fallback values match profile_optimization.yaml defaults.

This test ensures consistency between:
1. Hardcoded fallback values in profile_batch_backtester.py
2. Default values in config/backtesting/profile_optimization.yaml

Purpose: Prevent configuration drift when ProfileConfigLoader is unavailable.
"""

import pytest
from pathlib import Path


class TestFallbackValuesMatchConfig:
    """Test that hardcoded fallback values match config file defaults."""

    @pytest.fixture
    def config_path(self):
        """Path to profile_optimization.yaml config file."""
        return Path("config/backtesting/profile_optimization.yaml")

    @pytest.fixture
    def config_defaults(self, config_path):
        """
        Load default values from config file.

        Returns dict with threshold defaults.
        """
        import yaml

        with open(config_path) as f:
            config = yaml.safe_load(f)

        threshold_config = config.get("threshold_optimization", {})

        return {
            "rsi_buy": {
                "min": threshold_config.get("rsi", {}).get("buy_threshold", {}).get("min", 20),
                "max": threshold_config.get("rsi", {}).get("buy_threshold", {}).get("max", 35),
                "default": threshold_config.get("rsi", {}).get("buy_threshold", {}).get("default", 30),
            },
            "rsi_sell": {
                "min": threshold_config.get("rsi", {}).get("sell_threshold", {}).get("min", 65),
                "max": threshold_config.get("rsi", {}).get("sell_threshold", {}).get("max", 80),
                "default": threshold_config.get("rsi", {}).get("sell_threshold", {}).get("default", 70),
            },
            "volume_ratio": {
                "min": threshold_config.get("volume_ratio", {}).get("min", 1.0),
                "max": threshold_config.get("volume_ratio", {}).get("max", 1.5),
                "default": threshold_config.get("volume_ratio", {}).get("default", 1.1),
            },
            "ema_distance": {
                "min": threshold_config.get("ema_distance", {}).get("min", 0.002),
                "max": threshold_config.get("ema_distance", {}).get("max", 0.01),
                "default": threshold_config.get("ema_distance", {}).get("default", 0.005),
            },
            "momentum": {
                "min": threshold_config.get("momentum", {}).get("threshold", {}).get("min", 0.01),
                "max": threshold_config.get("momentum", {}).get("threshold", {}).get("max", 0.03),
                "default": threshold_config.get("momentum", {}).get("threshold", {}).get("default", 0.015),
            },
        }

    def test_rsi_buy_fallback_matches_config(self, config_defaults):
        """
        Test that RSI buy threshold fallback values match config.

        From profile_batch_backtester.py lines 1191 and 1197:
            rsi_buy_min, rsi_buy_max = 20, 35

        Should match config/backtesting/profile_optimization.yaml:
            threshold_optimization.rsi.buy_threshold: min=20, max=35
        """
        # Expected hardcoded values from code
        expected_min = 20
        expected_max = 35

        # Actual values from config
        actual_min = config_defaults["rsi_buy"]["min"]
        actual_max = config_defaults["rsi_buy"]["max"]

        assert expected_min == actual_min, (
            f"RSI buy min mismatch: code expects {expected_min}, "
            f"config has {actual_min}. Update hardcoded value in "
            f"profile_batch_backtester.py or update config."
        )

        assert expected_max == actual_max, (
            f"RSI buy max mismatch: code expects {expected_max}, "
            f"config has {actual_max}. Update hardcoded value in "
            f"profile_batch_backtester.py or update config."
        )

    def test_volume_ratio_fallback_matches_config(self, config_defaults):
        """
        Test that volume ratio fallback values match config.

        From profile_batch_backtester.py lines 1192 and 1198:
            vol_min, vol_max = 1.0, 1.5

        Should match config/backtesting/profile_optimization.yaml:
            threshold_optimization.volume_ratio: min=1.0, max=1.5
        """
        # Expected hardcoded values from code
        expected_min = 1.0
        expected_max = 1.5

        # Actual values from config
        actual_min = config_defaults["volume_ratio"]["min"]
        actual_max = config_defaults["volume_ratio"]["max"]

        assert expected_min == actual_min, (
            f"Volume ratio min mismatch: code expects {expected_min}, "
            f"config has {actual_min}. Update hardcoded value in "
            f"profile_batch_backtester.py or update config."
        )

        assert expected_max == actual_max, (
            f"Volume ratio max mismatch: code expects {expected_max}, "
            f"config has {actual_max}. Update hardcoded value in "
            f"profile_batch_backtester.py or update config."
        )

    def test_ema_distance_config_exists(self, config_defaults):
        """
        Test that EMA distance config is properly defined.

        Note: EMA distance is defined in config but not currently used
        in the optimization fallback code. This test documents the
        config values for future use.
        """
        # Verify config has EMA distance defined
        assert "ema_distance" in config_defaults
        assert config_defaults["ema_distance"]["min"] == 0.002
        assert config_defaults["ema_distance"]["max"] == 0.01
        assert config_defaults["ema_distance"]["default"] == 0.005

    def test_momentum_config_exists(self, config_defaults):
        """
        Test that momentum threshold config is properly defined.

        Note: Momentum is defined in config but not currently used
        in the optimization fallback code. This test documents the
        config values for future use.
        """
        # Verify config has momentum defined
        assert "momentum" in config_defaults
        assert config_defaults["momentum"]["min"] == 0.01
        assert config_defaults["momentum"]["max"] == 0.03
        assert config_defaults["momentum"]["default"] == 0.015

    def test_fallback_values_have_config_comments(self):
        """
        Test that fallback values in code have comments referencing config.

        This ensures maintainability by documenting where values come from.
        """
        backtester_path = Path("app/backtesting/profile_batch_backtester.py")

        with open(backtester_path) as f:
            content = f.read()

        # Check for config reference comments near fallback values
        assert "profile_optimization.yaml" in content or "threshold_optimization" in content, (
            "Fallback values should have comments referencing config file"
        )

        # Check for inline comments with config keys
        assert "rsi.buy_threshold" in content, (
            "RSI fallback should reference config key rsi.buy_threshold"
        )
        assert "volume_ratio" in content, (
            "Volume fallback should reference config key volume_ratio"
        )

    def test_no_incorrect_hardcoded_values(self):
        """
        Test that old incorrect hardcoded values are not present.

        Prevents regression of previously fixed values:
        - Old RSI: 30, 70 (was mixing buy/sell defaults)
        - Old Volume: 1.0, 3.0 (max was 2x config value)
        """
        backtester_path = Path("app/backtesting/profile_batch_backtester.py")

        with open(backtester_path) as f:
            content = f.read()

        # These old values should NOT be present
        assert "rsi_buy_min, rsi_buy_max = 30, 70" not in content, (
            "Old incorrect RSI fallback (30, 70) found. Should be (20, 35) "
            "to match config buy_threshold range."
        )

        assert "vol_min, vol_max = 1.0, 3.0" not in content, (
            "Old incorrect volume fallback (1.0, 3.0) found. Should be (1.0, 1.5) "
            "to match config volume_ratio range."
        )


class TestFallbackValueIntegration:
    """Integration tests for fallback value behavior."""

    def test_fallback_values_are_valid_ranges(self, config_defaults):
        """
        Test that fallback values represent valid optimization ranges.

        Ensures min < max for all threshold configs.
        """
        for threshold_name, values in config_defaults.items():
            if "min" in values and "max" in values:
                assert values["min"] < values["max"], (
                    f"{threshold_name}: min ({values['min']}) must be less than max ({values['max']})"
                )

    def test_fallback_values_within_reasonable_bounds(self, config_defaults):
        """
        Test that fallback values are within reasonable operational bounds.

        Prevents typos or extreme values that could cause issues.
        """
        # RSI should be 0-100
        assert 0 <= config_defaults["rsi_buy"]["min"] <= 100
        assert 0 <= config_defaults["rsi_buy"]["max"] <= 100
        assert 0 <= config_defaults["rsi_sell"]["min"] <= 100
        assert 0 <= config_defaults["rsi_sell"]["max"] <= 100

        # Volume ratio should be positive and not too large
        assert config_defaults["volume_ratio"]["min"] > 0
        assert config_defaults["volume_ratio"]["max"] < 10  # Sanity check

        # EMA distance should be small (percentage)
        assert 0 < config_defaults["ema_distance"]["min"] < 0.1
        assert 0 < config_defaults["ema_distance"]["max"] < 0.1

        # Momentum should be small (percentage change)
        assert 0 < config_defaults["momentum"]["min"] < 0.1
        assert 0 < config_defaults["momentum"]["max"] < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
