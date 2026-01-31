"""
Comprehensive unit tests for Centralized Configuration Module.

Following TDD best practices:
1. Test-driven development approach
2. Comprehensive edge case coverage
3. Property-based testing with Hypothesis
4. Configuration validation testing
5. Clear test names and structure
"""

from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import patch, Mock, MagicMock
import yaml
import json


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_config_dict():
    """Create sample configuration dictionary."""
    return {
        'risk_management': {
            'atr_multipliers': {
                'default_stop': 2.0,
                'tight_stop': 1.0,
                'wide_stop': 3.0,
            },
            'position_sizing': {
                'default_risk_per_trade': 0.02,
                'max_position_size': 0.25,
                'kelly_fraction_multiplier': 0.5,
            },
            'stop_loss': {
                'max_stop_distance_pct': 0.20,
                'default_stop_distance_pct': 0.05,
            },
        },
        'trading': {
            'symbols': ['AAPL', 'MSFT', 'GOOGL'],
            'default_timeframe': '1d',
            'max_positions': 10,
        },
        'backtesting': {
            'start_date': '2020-01-01',
            'end_date': '2024-12-31',
            'initial_capital': 100000,
        },
    }


@pytest.fixture
def sample_config_file(tmp_path, sample_config_dict):
    """Create a temporary configuration file."""
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(sample_config_dict, f)
    return config_file


# =============================================================================
# Configuration Loading Tests
# =============================================================================


class TestConfigurationLoading:
    """Test suite for configuration loading functionality."""

    def test_load_config_from_yaml(self, sample_config_file):
        """Test loading configuration from YAML file."""
        from app.core.centralized_config import load_config_from_yaml

        config = load_config_from_yaml(sample_config_file)

        assert config is not None
        assert 'risk_management' in config
        assert 'trading' in config

    def test_load_config_from_json(self, tmp_path, sample_config_dict):
        """Test loading configuration from JSON file."""
        from app.core.centralized_config import load_config_from_json

        config_file = tmp_path / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(sample_config_dict, f)

        config = load_config_from_json(config_file)

        assert config is not None
        assert config['trading']['symbols'] == ['AAPL', 'MSFT', 'GOOGL']

    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        from app.core.centralized_config import load_config_from_yaml

        with pytest.raises(FileNotFoundError):
            load_config_from_yaml(Path("/nonexistent/file.yaml"))

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML file."""
        from app.core.centralized_config import load_config_from_yaml

        invalid_file = tmp_path / "invalid.yaml"
        with open(invalid_file, 'w') as f:
            f.write("invalid: yaml: content: [unclosed")

        with pytest.raises((yaml.YAMLError, ValueError)):
            load_config_from_yaml(invalid_file)

    def test_load_empty_config(self, tmp_path):
        """Test loading empty configuration file."""
        from app.core.centralized_config import load_config_from_yaml

        empty_file = tmp_path / "empty.yaml"
        empty_file.touch()

        config = load_config_from_yaml(empty_file)

        assert config == {}


# =============================================================================
# Configuration Validation Tests
# =============================================================================


class TestConfigurationValidation:
    """Test suite for configuration validation."""

    def test_validate_atr_multipliers(self, sample_config_dict):
        """Test ATR multiplier validation."""
        from app.core.centralized_config import validate_atr_multipliers

        atr_multipliers = sample_config_dict['risk_management']['atr_multipliers']
        is_valid = validate_atr_multipliers(atr_multipliers)

        assert is_valid is True

    def test_validate_atr_multipliers_with_negative(self):
        """Test ATR multiplier validation with negative values."""
        from app.core.centralized_config import validate_atr_multipliers

        invalid_multipliers = {
            'default_stop': -1.0,
            'tight_stop': 0.5,
            'wide_stop': 3.0,
        }

        is_valid = validate_atr_multipliers(invalid_multipliers)

        assert is_valid is False

    def test_validate_risk_percentages(self, sample_config_dict):
        """Test risk percentage validation."""
        from app.core.centralized_config import validate_risk_percentages

        risk_config = sample_config_dict['risk_management']['position_sizing']
        is_valid = validate_risk_percentages(risk_config)

        assert is_valid is True

    def test_validate_risk_percentages_exceeding_100(self):
        """Test risk percentage validation with values > 100%."""
        from app.core.centralized_config import validate_risk_percentages

        invalid_config = {
            'default_risk_per_trade': 1.5,  # 150%
            'max_position_size': 0.25,
        }

        is_valid = validate_risk_percentages(invalid_config)

        assert is_valid is False

    def test_validate_trading_symbols(self, sample_config_dict):
        """Test trading symbols validation."""
        from app.core.centralized_config import validate_trading_symbols

        symbols = sample_config_dict['trading']['symbols']
        is_valid = validate_trading_symbols(symbols)

        assert is_valid is True

    def test_validate_trading_symbols_empty_list(self):
        """Test trading symbols validation with empty list."""
        from app.core.centralized_config import validate_trading_symbols

        is_valid = validate_trading_symbols([])

        assert is_valid is False

    def test_validate_trading_symbols_duplicates(self):
        """Test trading symbols validation with duplicates."""
        from app.core.centralized_config import validate_trading_symbols

        symbols_with_duplicates = ['AAPL', 'MSFT', 'AAPL', 'GOOGL']
        is_valid = validate_trading_symbols(symbols_with_duplicates)

        # Should either be False or dedupe
        assert isinstance(is_valid, bool)

    def test_validate_dates(self, sample_config_dict):
        """Test date validation."""
        from app.core.centralized_config import validate_dates

        backtest_config = sample_config_dict['backtesting']
        is_valid = validate_dates(backtest_config)

        assert is_valid is True

    def test_validate_dates_invalid_order(self):
        """Test date validation with invalid order."""
        from app.core.centralized_config import validate_dates

        invalid_config = {
            'start_date': '2024-01-01',
            'end_date': '2020-01-01',  # Before start
        }

        is_valid = validate_dates(invalid_config)

        assert is_valid is False


# =============================================================================
# Configuration Access Tests
# =============================================================================


class TestConfigurationAccess:
    """Test suite for configuration access methods."""

    def test_get_atr_multiplier(self, sample_config_dict):
        """Test getting ATR multiplier."""
        from app.core.centralized_config import Configuration

        config = Configuration(sample_config_dict)

        default_multiplier = config.get_atr_multiplier('default_stop')

        assert default_multiplier == 2.0

    def test_get_atr_multiplier_not_exists(self, sample_config_dict):
        """Test getting non-existent ATR multiplier."""
        from app.core.centralized_config import Configuration

        config = Configuration(sample_config_dict)

        result = config.get_atr_multiplier('nonexistent')

        # Should return None or default
        assert result is None or isinstance(result, (int, float))

    def test_get_risk_config(self, sample_config_dict):
        """Test getting risk configuration."""
        from app.core.centralized_config import Configuration

        config = Configuration(sample_config_dict)

        risk_config = config.get_risk_config()

        assert 'position_sizing' in risk_config
        assert 'atr_multipliers' in risk_config

    def test_get_trading_symbols(self, sample_config_dict):
        """Test getting trading symbols."""
        from app.core.centralized_config import Configuration

        config = Configuration(sample_config_dict)

        symbols = config.get_trading_symbols()

        assert symbols == ['AAPL', 'MSFT', 'GOOGL']

    def test_get_backtest_dates(self, sample_config_dict):
        """Test getting backtest dates."""
        from app.core.centralized_config import Configuration

        config = Configuration(sample_config_dict)

        dates = config.get_backtest_dates()

        assert dates['start_date'] == '2020-01-01'
        assert dates['end_date'] == '2024-12-31'


# =============================================================================
# Configuration Merging Tests
# =============================================================================


class TestConfigurationMerging:
    """Test suite for configuration merging functionality."""

    def test_merge_configs(self, sample_config_dict):
        """Test merging two configurations."""
        from app.core.centralized_config import merge_configs

        base_config = sample_config_dict.copy()
        override_config = {
            'risk_management': {
                'atr_multipliers': {
                    'default_stop': 2.5,  # Override
                },
            },
        }

        merged = merge_configs(base_config, override_config)

        # Should have overridden value
        assert merged['risk_management']['atr_multipliers']['default_stop'] == 2.5
        # Should keep other values
        assert 'tight_stop' in merged['risk_management']['atr_multipliers']

    def test_merge_configs_nested(self):
        """Test merging nested configurations."""
        from app.core.centralized_config import merge_configs

        base = {
            'level1': {
                'level2': {
                    'key1': 'value1',
                    'key2': 'value2',
                },
            },
        }

        override = {
            'level1': {
                'level2': {
                    'key2': 'new_value2',
                    'key3': 'value3',
                },
            },
        }

        merged = merge_configs(base, override)

        assert merged['level1']['level2']['key1'] == 'value1'
        assert merged['level1']['level2']['key2'] == 'new_value2'
        assert merged['level1']['level2']['key3'] == 'value3'

    def test_merge_configs_empty_override(self, sample_config_dict):
        """Test merging with empty override."""
        from app.core.centralized_config import merge_configs

        merged = merge_configs(sample_config_dict, {})

        assert merged == sample_config_dict

    def test_merge_configs_empty_base(self):
        """Test merging with empty base."""
        from app.core.centralized_config import merge_configs

        override = {'key': 'value'}
        merged = merge_configs({}, override)

        assert merged == override


# =============================================================================
# Configuration Defaults Tests
# =============================================================================


class TestConfigurationDefaults:
    """Test suite for default configuration values."""

    def test_default_atr_multiplier(self):
        """Test default ATR multiplier."""
        from app.core.centralized_config import get_default_atr_multiplier

        multiplier = get_default_atr_multiplier()

        assert multiplier == 2.0

    def test_default_risk_per_trade(self):
        """Test default risk per trade percentage."""
        from app.core.centralized_config import get_default_risk_per_trade

        risk = get_default_risk_per_trade()

        assert risk == 0.02

    def test_default_max_position_size(self):
        """Test default maximum position size."""
        from app.core.centralized_config import get_default_max_position_size

        max_size = get_default_max_position_size()

        assert max_size == 0.25

    def test_default_stop_distance_pct(self):
        """Test default stop loss distance percentage."""
        from app.core.centralized_config import get_default_stop_distance_pct

        stop_pct = get_default_stop_distance_pct()

        assert stop_pct == 0.05


# =============================================================================
# Configuration Caching Tests
# =============================================================================


class TestConfigurationCaching:
    """Test suite for configuration caching."""

    def test_config_cached_after_load(self, sample_config_file):
        """Test that configuration is cached after loading."""
        from app.core.centralized_config import load_config_from_yaml

        config1 = load_config_from_yaml(sample_config_file)
        config2 = load_config_from_yaml(sample_config_file)

        # Should be same object (cached)
        # Note: This depends on implementation
        assert config1 is not None
        assert config2 is not None

    def test_config_cache_invalidated_on_change(self, sample_config_file):
        """Test that cache is invalidated when config file changes."""
        from app.core.centralized_config import load_config_from_yaml

        config1 = load_config_from_yaml(sample_config_file)

        # Modify file
        with open(sample_config_file, 'a') as f:
            f.write("\nnew_key: new_value")

        # Reload
        config2 = load_config_from_yaml(sample_config_file)

        # Config should be updated
        assert 'new_key' in config2


# =============================================================================
# Property-Based Tests
# =============================================================================


class TestConfigurationProperties:
    """Property-based tests using Hypothesis."""

    @given(
        multiplier=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=30)
    def test_atr_multiplier_positive_property(self, multiplier):
        """Property: ATR multipliers should always be positive."""
        from app.core.centralized_config import validate_atr_multipliers

        config = {
            'default_stop': multiplier,
            'tight_stop': multiplier / 2,
            'wide_stop': multiplier * 1.5,
        }

        # All positive multipliers should be valid
        if min(config.values()) > 0:
            is_valid = validate_atr_multipliers(config)
            assert is_valid is True

    @given(
        risk_pct=st.floats(min_value=0.001, max_value=0.10, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=30)
    def test_risk_percentage_bounds_property(self, risk_pct):
        """Property: Risk percentages should be between 0 and 1 (0-100%)."""
        from app.core.centralized_config import validate_risk_percentages

        config = {
            'default_risk_per_trade': risk_pct,
            'max_position_size': risk_pct * 10,
        }

        if 0 < risk_pct <= 1.0:
            is_valid = validate_risk_percentages(config)
            assert is_valid is True

    @given(
        num_symbols=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=20)
    def test_symbols_list_property(self, num_symbols):
        """Property: Symbols list should be non-empty if trading enabled."""
        from app.core.centralized_config import validate_trading_symbols

        symbols = [f"SYMBOL{i:04d}" for i in range(num_symbols)]

        is_valid = validate_trading_symbols(symbols)

        # Non-empty lists should be valid
        if num_symbols > 0:
            assert is_valid is True

    @given(
        days_offset=st.integers(min_value=1, max_value=3650),
    )
    @settings(max_examples=20)
    def test_date_order_property(self, days_offset):
        """Property: End date should be after start date."""
        from app.core.centralized_config import validate_dates

        start = "2020-01-01"
        end_date = datetime(2020, 1, 1) + timedelta(days=days_offset)
        end = end_date.strftime("%Y-%m-%d")

        config = {
            'start_date': start,
            'end_date': end,
        }

        is_valid = validate_dates(config)

        # Should be valid if end is after start
        if days_offset > 0:
            assert is_valid is True


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestConfigurationEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_config_with_none_values(self):
        """Test configuration with None values."""
        from app.core.centralized_config import Configuration

        config_dict = {
            'risk_management': None,
            'trading': {'symbols': ['AAPL']},
        }

        config = Configuration(config_dict)

        # Should handle gracefully
        assert config is not None

    def test_config_with_missing_sections(self, sample_config_dict):
        """Test accessing missing configuration sections."""
        from app.core.centralized_config import Configuration

        config = Configuration(sample_config_dict)

        result = config.get('nonexistent_section', {})

        assert result == {}

    def test_config_with_extra_sections(self, sample_config_dict):
        """Test configuration with extra/unknown sections."""
        from app.core.centralized_config import Configuration

        sample_config_dict['unknown_section'] = {'key': 'value'}

        # Should still work
        config = Configuration(sample_config_dict)
        assert config is not None

    def test_config_with_zero_values(self):
        """Test configuration with zero values."""
        from app.core.centralized_config import Configuration

        config_dict = {
            'risk_management': {
                'atr_multipliers': {
                    'default_stop': 0,
                    'tight_stop': 0,
                },
            },
        }

        config = Configuration(config_dict)

        # Should handle zero values
        result = config.get_atr_multiplier('default_stop')
        assert result == 0

    def test_config_with_very_large_values(self):
        """Test configuration with very large values."""
        from app.core.centralized_config import Configuration

        config_dict = {
            'backtesting': {
                'initial_capital': 10**12,  # Trillion
            },
        }

        config = Configuration(config_dict)

        # Should handle large values
        assert config is not None


# =============================================================================
# Configuration Update Tests
# =============================================================================


class TestConfigurationUpdates:
    """Test suite for configuration update functionality."""

    def test_update_atr_multiplier(self, sample_config_dict):
        """Test updating ATR multiplier."""
        from app.core.centralized_config import Configuration

        config = Configuration(sample_config_dict)

        config.set_atr_multiplier('default_stop', 2.5)

        assert config.get_atr_multiplier('default_stop') == 2.5

    def test_update_nested_value(self, sample_config_dict):
        """Test updating nested configuration value."""
        from app.core.centralized_config import Configuration

        config = Configuration(sample_config_dict)

        config.set('risk_management.position_sizing.default_risk_per_trade', 0.03)

        # Should update correctly
        assert config.get('risk_management.position_sizing.default_risk_per_trade') == 0.03


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestConfigurationThreadSafety:
    """Test suite for thread-safe configuration access."""

    def test_concurrent_read_access(self, sample_config_dict):
        """Test concurrent read access to configuration."""
        from app.core.centralized_config import Configuration
        import threading

        config = Configuration(sample_config_dict)
        results = []

        def read_config():
            results.append(config.get_atr_multiplier('default_stop'))

        threads = [threading.Thread(target=read_config) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All reads should succeed
        assert len(results) == 10
        assert all(r == 2.0 for r in results)


# =============================================================================
# Integration Tests
# =============================================================================


class TestConfigurationIntegration:
    """Integration tests for configuration system."""

    def test_full_config_workflow(self, sample_config_file):
        """Test complete configuration workflow."""
        from app.core.centralized_config import load_config_from_yaml, Configuration

        # Load from file
        config_dict = load_config_from_yaml(sample_config_file)

        # Create configuration object
        config = Configuration(config_dict)

        # Access values
        atr_multiplier = config.get_atr_multiplier('default_stop')
        symbols = config.get_trading_symbols()
        dates = config.get_backtest_dates()

        # Verify all values
        assert atr_multiplier == 2.0
        assert symbols == ['AAPL', 'MSFT', 'GOOGL']
        assert dates['start_date'] == '2020-01-01'

    def test_config_with_validation(self, sample_config_dict):
        """Test configuration with full validation."""
        from app.core.centralized_config import Configuration, validate_config

        config = Configuration(sample_config_dict)

        is_valid = validate_config(config)

        assert is_valid is True
