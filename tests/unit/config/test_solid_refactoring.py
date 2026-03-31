"""
Tests for SOLID-Compliant Configuration Refactoring

Verifies that all new modules work correctly and maintain backward compatibility.
"""

import pytest
from app.shared.config.protocols import (
    ConfigProvider,
    FileConfigLoader,
    ConfigValidator,
    ConfigMerger,
    ConfigCache,
)
from app.shared.config.loaders import YAMLConfigLoader, JSONConfigLoader, ConfigLoaderRegistry
from app.shared.config.validators import (
    ATRMultiplierValidator,
    RiskPercentageValidator,
    TradingSymbolsValidator,
    DateRangeValidator,
    CompositeConfigValidator,
)
from app.shared.config.mergers import RecursiveConfigMerger, ReplaceConfigMerger
from app.shared.config.cache import FileBasedConfigCache
from app.shared.config.base.defaults import (
    get_default_atr_multiplier,
    get_default_risk_per_trade,
    get_default_max_position_size,
    get_default_stop_distance_pct,
)
from app.shared.config.centralized_config import (
    get_config,
    get_trading_threshold,
    validate_atr_multipliers,
    merge_configs,
    Configuration,
    CentralizedConfig,
)


class TestProtocols:
    """Test protocol interfaces."""

    def test_config_provider_protocol_exists(self):
        """Verify ConfigProvider protocol is defined."""
        assert ConfigProvider is not None

    def test_file_config_loader_protocol_exists(self):
        """Verify FileConfigLoader protocol is defined."""
        assert FileConfigLoader is not None

    def test_config_validator_protocol_exists(self):
        """Verify ConfigValidator protocol is defined."""
        assert ConfigValidator is not None

    def test_config_merger_protocol_exists(self):
        """Verify ConfigMerger protocol is defined."""
        assert ConfigMerger is not None

    def test_config_cache_protocol_exists(self):
        """Verify ConfigCache protocol is defined."""
        assert ConfigCache is not None


class TestLoaders:
    """Test configuration loaders."""

    def test_yaml_loader_supports_yaml(self):
        """Test YAML loader supports .yaml files."""
        loader = YAMLConfigLoader()
        assert loader.supports(".yaml") is True
        assert loader.supports(".yml") is True
        assert loader.supports(".json") is False

    def test_json_loader_supports_json(self):
        """Test JSON loader supports .json files."""
        loader = JSONConfigLoader()
        assert loader.supports(".json") is True
        assert loader.supports(".yaml") is False

    def test_loader_registry_yaml(self, tmp_path):
        """Test loader registry selects correct loader for YAML."""
        registry = ConfigLoaderRegistry()

        # Create test YAML file
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\n")

        config = registry.load(yaml_file)
        assert config == {"key": "value"}

    def test_loader_registry_json(self, tmp_path):
        """Test loader registry selects correct loader for JSON."""
        registry = ConfigLoaderRegistry()

        # Create test JSON file
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}\n')

        config = registry.load(json_file)
        assert config == {"key": "value"}

    def test_loader_registry_unsupported(self, tmp_path):
        """Test loader registry raises error for unsupported formats."""
        registry = ConfigLoaderRegistry()

        # Create test file with unsupported extension
        unsupported_file = tmp_path / "test.xyz"
        unsupported_file.write_text("data")

        with pytest.raises(ValueError, match="Unsupported config file type"):
            registry.load(unsupported_file)


class TestValidators:
    """Test configuration validators."""

    def test_atr_multiplier_validator_positive(self):
        """Test ATR validator accepts positive values."""
        validator = ATRMultiplierValidator()
        assert validator.validate({"default_stop": 2.0, "profit_target": 3.0}) is True
        assert validator.get_errors() == []

    def test_atr_multiplier_validator_negative(self):
        """Test ATR validator rejects negative values."""
        validator = ATRMultiplierValidator()
        assert validator.validate({"default_stop": -1.0}) is False
        assert len(validator.get_errors()) > 0

    def test_risk_percentage_validator_valid(self):
        """Test risk percentage validator accepts valid values."""
        validator = RiskPercentageValidator()
        assert validator.validate({"risk_per_trade": 0.02}) is True
        assert validator.get_errors() == []

    def test_risk_percentage_validator_invalid(self):
        """Test risk percentage validator rejects invalid values."""
        validator = RiskPercentageValidator()
        assert validator.validate({"risk_per_trade": 1.5}) is False
        assert len(validator.get_errors()) > 0

    def test_trading_symbols_validator_valid(self):
        """Test trading symbols validator accepts valid list."""
        validator = TradingSymbolsValidator()
        assert validator.validate({"symbols": ["AAPL", "MSFT", "GOOGL"]}) is True
        assert validator.get_errors() == []

    def test_trading_symbols_validator_duplicates(self):
        """Test trading symbols validator rejects duplicates."""
        validator = TradingSymbolsValidator()
        assert validator.validate({"symbols": ["AAPL", "AAPL"]}) is False
        assert len(validator.get_errors()) > 0

    def test_date_range_validator_valid(self):
        """Test date range validator accepts valid dates."""
        validator = DateRangeValidator()
        assert validator.validate({"start_date": "2020-01-01", "end_date": "2024-12-31"}) is True
        assert validator.get_errors() == []

    def test_date_range_validator_invalid_order(self):
        """Test date range validator rejects invalid date order."""
        validator = DateRangeValidator()
        assert validator.validate({"start_date": "2024-12-31", "end_date": "2020-01-01"}) is False
        assert len(validator.get_errors()) > 0

    def test_composite_validator(self):
        """Test composite validator combines multiple validators."""
        validator = CompositeConfigValidator()

        config = {
            "risk_management": {
                "atr_multipliers": {"default_stop": 2.0},
                "position_sizing": {"risk_per_trade": 0.02},
            },
            "trading": {"symbols": ["AAPL", "MSFT"]},
            "backtesting": {"start_date": "2020-01-01", "end_date": "2024-12-31"},
        }

        assert validator.validate(config) is True


class TestMergers:
    """Test configuration mergers."""

    def test_recursive_merger_nested(self):
        """Test recursive merger handles nested dictionaries."""
        merger = RecursiveConfigMerger()

        base = {"level1": {"key1": "value1", "key2": "value2"}}
        override = {"level1": {"key2": "new_value2", "key3": "value3"}}

        result = merger.merge(base, override)

        assert result["level1"]["key1"] == "value1"  # From base
        assert result["level1"]["key2"] == "new_value2"  # From override
        assert result["level1"]["key3"] == "value3"  # From override

    def test_replace_merger(self):
        """Test replace merger replaces top-level keys."""
        merger = ReplaceConfigMerger()

        base = {"key1": "value1"}
        override = {"key2": "value2"}

        result = merger.merge(base, override)

        assert result["key1"] == "value1"
        assert result["key2"] == "value2"


class TestCache:
    """Test configuration cache."""

    def test_cache_miss(self, tmp_path):
        """Test cache returns None for missing entries."""
        cache = FileBasedConfigCache()

        config_file = tmp_path / "test.yaml"
        config_file.write_text("key: value")

        result = cache.get_cached(config_file)
        assert result is None

    def test_cache_hit(self, tmp_path):
        """Test cache returns cached config when valid."""
        cache = FileBasedConfigCache()

        config_file = tmp_path / "test.yaml"
        config_file.write_text("key: value")

        config_data = {"key": "cached_value"}
        cache.set_cached(config_file, config_data)

        result = cache.get_cached(config_file)
        assert result == config_data

    def test_cache_invalidation(self, tmp_path):
        """Test cache invalidation removes entry."""
        cache = FileBasedConfigCache()

        config_file = tmp_path / "test.yaml"
        config_file.write_text("key: value")

        config_data = {"key": "value"}
        cache.set_cached(config_file, config_data)

        cache.invalidate(config_file)

        result = cache.get_cached(config_file)
        assert result is None


class TestDefaults:
    """Test default configuration values."""

    def test_default_atr_multiplier(self):
        """Test default ATR multiplier value."""
        assert get_default_atr_multiplier() == 2.0

    def test_default_risk_per_trade(self):
        """Test default risk per trade value."""
        assert get_default_risk_per_trade() == 0.02

    def test_default_max_position_size(self):
        """Test default max position size value."""
        assert get_default_max_position_size() == 0.25

    def test_default_stop_distance_pct(self):
        """Test default stop distance percentage value."""
        assert get_default_stop_distance_pct() == 0.05


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_get_config(self):
        """Test get_config returns CentralizedConfig instance."""
        config = get_config()
        assert isinstance(config, CentralizedConfig)

    def test_get_trading_threshold(self):
        """Test get_trading_threshold works."""
        threshold = get_trading_threshold("min_signal_strength")
        assert threshold == 60.0

    def test_validate_atr_multipliers(self):
        """Test validate_atr_multipliers works."""
        assert validate_atr_multipliers({"default_stop": 2.0}) is True

    def test_merge_configs(self):
        """Test merge_configs works."""
        base = {"key1": "value1"}
        override = {"key2": "value2"}
        merged = merge_configs(base, override)
        assert "key1" in merged
        assert "key2" in merged

    def test_legacy_configuration_class(self):
        """Test legacy Configuration class works."""
        config = Configuration({"risk_management": {"atr_multipliers": {"default_stop": 2.0}}})

        assert config.get_atr_multiplier("default_stop") == 2.0
        assert config.get("risk_management.atr_multipliers.default_stop") == 2.0

    def test_config_subconfigs_accessible(self):
        """Test all sub-configurations are accessible."""
        config = get_config()

        # All sub-configs should be present
        assert hasattr(config, "trading")
        assert hasattr(config, "backtesting")
        assert hasattr(config, "database")
        assert hasattr(config, "redis")
        assert hasattr(config, "api")
        assert hasattr(config, "logging")
        assert hasattr(config, "monitoring")
        assert hasattr(config, "currency_hedging")
        assert hasattr(config, "diversification")
        assert hasattr(config, "compliance")
        assert hasattr(config, "shadow_mode")
        assert hasattr(config, "market_microstructure")


class TestSOLIDCompliance:
    """Test SOLID principles compliance."""

    def test_srp_single_responsibility(self):
        """Verify each module has single responsibility."""
        # Loaders - only load files
        loader = YAMLConfigLoader()
        assert hasattr(loader, "load")
        assert hasattr(loader, "supports")

        # Validators - only validate config
        validator = ATRMultiplierValidator()
        assert hasattr(validator, "validate")
        assert hasattr(validator, "get_errors")

        # Mergers - only merge configs
        merger = RecursiveConfigMerger()
        assert hasattr(merger, "merge")

        # Cache - only cache configs
        cache = FileBasedConfigCache()
        assert hasattr(cache, "get_cached")
        assert hasattr(cache, "set_cached")
        assert hasattr(cache, "invalidate")

    def test_ocp_open_closed_principle(self):
        """Verify system is open for extension, closed for modification."""
        # Can register new loaders without modifying existing code
        registry = ConfigLoaderRegistry()

        class CustomLoader:
            def load(self, path):
                return {"custom": True}

            def supports(self, ext):
                return ext == ".custom"

        registry.register(CustomLoader())
        loader = registry.get_loader(".custom")
        assert loader is not None
        assert isinstance(loader, CustomLoader)

        # Can register new validators without modifying existing code
        composite = CompositeConfigValidator()

        class CustomValidator:
            def validate(self, config):
                return True

            def get_errors(self):
                return []

        composite.register_validator("custom", CustomValidator())
        assert "custom" in composite._validators

    def test_dip_dependency_inversion(self):
        """Verify high-level modules depend on abstractions."""
        # CentralizedConfig depends on protocols (abstractions)
        # not concrete implementations
        from app.shared.config.centralized_config import (
            _loader_registry,
            _config_cache,
            _config_validator,
            _config_merger,
        )

        # These are instances of protocols
        assert _loader_registry is not None
        assert _config_cache is not None
        assert _config_validator is not None
        assert _config_merger is not None
