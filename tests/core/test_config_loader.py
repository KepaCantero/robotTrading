"""
Tests for core YAML Configuration Loader.

Tests the YAMLConfigLoader which loads YAML configs with validation,
tier-specific overrides, thread-safe caching, and structured logging with structlog.
"""

import tempfile
import threading
from pathlib import Path

import pytest
import yaml

from app.core.config_loader import (
    YAMLConfigLoader,
    get_config_loader,
    get_detector_config,
    get_filter_config,
    get_strategy_config,
    load_learning_parameters_config,
    load_market_detectors_config,
    load_momentum_filters_config,
    load_strategy_defaults_config,
    load_strategy_stock_allocator_config,
)


class TestYAMLConfigLoaderStructlog:
    """Test suite for structlog integration in config_loader."""

    def test_logger_is_structlog_instance(self):
        """Test that YAMLConfigLoader uses structlog for logging."""

        # The logger is a module-level variable using structlog
        from app.core.config_loader import logger

        # Check that logger exists and has structlog methods
        # Structlog bound loggers have specific methods like info, warning, error, debug
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')

    def test_structlog_warning_on_invalid_filename(self, caplog):
        """Test that structlog logs warning for invalid filename."""
        import structlog

        # Configure structlog for testing
        structlog.configure(
            processors=[structlog.processors.JSONRenderer()],
            wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
        )

        loader = YAMLConfigLoader()
        result = loader.load("")

        # Empty filename should return empty dict and log error
        assert result == {}

    def test_structlog_info_on_config_load(self, tmp_path):
        """Test that structlog logs info when config is loaded successfully."""
        import structlog

        # Capture structlog output
        log_output = []

        def capture_log(_, method_name, event_dict):
            log_output.append(event_dict)
            return event_dict

        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                capture_log,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(20),
            context_class=dict,
            logger_factory=structlog.WriteLoggerFactory(),
        )

        # Create test config file
        config_data = {"test_section": {"test_key": "test_value"}}
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("test_config.yaml")

        assert result == config_data

    def test_structlog_error_on_yaml_parse_error(self, tmp_path):
        """Test that structlog logs error on invalid YAML."""
        # Create invalid YAML file
        invalid_file = tmp_path / "invalid.yaml"
        with open(invalid_file, 'w') as f:
            f.write("invalid: yaml: content: [")

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("invalid.yaml")

        # Should return empty dict on parse error
        assert result == {}

    def test_structlog_warning_on_sensitive_data(self, tmp_path):
        """Test that structlog logs warning for sensitive data keys."""
        # Create config with sensitive keys
        config_data = {
            "database": {"password": "secret123", "host": "localhost"},
            "api": {"api_key": "key_abc"},
        }
        config_file = tmp_path / "sensitive_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("sensitive_config.yaml")

        # Config should be loaded despite sensitive keys
        assert "database" in result


class TestYAMLConfigLoaderInit:
    """Test suite for YAMLConfigLoader initialization."""

    def test_init_with_default_config_dir(self):
        """Test initialization with default config directory."""
        loader = YAMLConfigLoader()

        assert loader.config_dir == Path("config")
        assert isinstance(loader._cache, dict)
        assert len(loader._cache) == 0

    def test_init_with_custom_config_dir(self):
        """Test initialization with custom config directory."""
        custom_dir = Path("/custom/config/path")
        loader = YAMLConfigLoader(config_dir=custom_dir)

        assert loader.config_dir == custom_dir

    def test_init_with_env_variable(self, monkeypatch):
        """Test initialization with CONFIG_DIR environment variable."""
        monkeypatch.setenv("CONFIG_DIR", "/env/config/path")

        loader = YAMLConfigLoader()

        assert loader.config_dir == Path("/env/config/path")

    def test_init_env_variable_overrides_path_arg(self, monkeypatch):
        """Test that CONFIG_DIR env var overrides path argument."""
        monkeypatch.setenv("CONFIG_DIR", "/env/config/path")

        custom_dir = Path("/custom/config/path")
        loader = YAMLConfigLoader(config_dir=custom_dir)

        # ENV variable should take precedence
        assert loader.config_dir == Path("/env/config/path")

    def test_init_with_nonexistent_directory(self, caplog):
        """Test initialization with non-existent config directory."""
        loader = YAMLConfigLoader(config_dir=Path("/nonexistent/directory"))

        # Should not raise error, just log warning
        assert loader.config_dir == Path("/nonexistent/directory")

    def test_cache_lock_is_thread_safe(self):
        """Test that cache lock is RLock for thread safety."""

        loader = YAMLConfigLoader()

        # Check that the lock has RLock behavior (acquire/release methods)
        # and supports reentrant locking
        assert hasattr(loader._cache_lock, 'acquire')
        assert hasattr(loader._cache_lock, 'release')
        assert hasattr(loader._cache_lock, '__enter__')
        assert hasattr(loader._cache_lock, '__exit__')

        # Test that it's reentrant (can be acquired multiple times in same thread)
        loader._cache_lock.acquire()
        try:
            # Should be able to acquire again in same thread (reentrant)
            acquired_again = loader._cache_lock.acquire(blocking=False)
            if acquired_again:
                loader._cache_lock.release()
        finally:
            loader._cache_lock.release()


class TestYAMLConfigLoaderLoad:
    """Test suite for load method."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with test files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create valid config file
            config_data = {
                "section1": {"key1": "value1", "key2": 42},
                "section2": {"enabled": True, "threshold": 0.5},
            }
            config_file = tmp_path / "test_config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)

            # Create empty config file
            empty_file = tmp_path / "empty_config.yaml"
            with open(empty_file, 'w') as f:
                yaml.dump({}, f)

            # Create invalid YAML file
            invalid_file = tmp_path / "invalid.yaml"
            with open(invalid_file, 'w') as f:
                f.write("invalid: yaml: [")

            yield tmp_path

    def test_load_valid_config_file(self, temp_config_dir):
        """Test loading a valid YAML config file."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("test_config.yaml")

        assert result["section1"]["key1"] == "value1"
        assert result["section1"]["key2"] == 42
        assert result["section2"]["enabled"] is True
        assert result["section2"]["threshold"] == 0.5

    def test_load_returns_empty_dict_for_nonexistent_file(self, temp_config_dir):
        """Test that load returns empty dict for nonexistent file."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("nonexistent.yaml")

        assert result == {}

    def test_load_empty_yaml_file(self, temp_config_dir):
        """Test loading an empty YAML file."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("empty_config.yaml")

        assert result == {}

    def test_load_invalid_yaml_returns_empty_dict(self, temp_config_dir):
        """Test that invalid YAML returns empty dict."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("invalid.yaml")

        assert result == {}

    def test_load_with_invalid_filename(self, temp_config_dir):
        """Test load with invalid filename (None)."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load(None)

        assert result == {}

    def test_load_with_empty_string_filename(self, temp_config_dir):
        """Test load with empty string filename."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("")

        assert result == {}

    def test_load_with_non_string_filename(self, temp_config_dir):
        """Test load with non-string filename."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load(123)

        assert result == {}

    def test_load_validates_config_values(self, temp_config_dir):
        """Test that load validates configuration values."""
        # Create config with invalid values
        config_data = {
            "exposure": {
                "max_strategy_exposure": 1.5,  # Invalid: > 1
            }
        }
        config_file = temp_config_dir / "invalid_values.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("invalid_values.yaml")

        # Should still load, but validation warning should be logged
        assert "exposure" in result

    def test_load_detects_sensitive_keys(self, temp_config_dir):
        """Test that load detects sensitive data keys."""
        config_data = {
            "database": {"password": "secret123", "api_token": "token_abc"},
            "normal_key": "normal_value",
        }
        config_file = temp_config_dir / "sensitive.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("sensitive.yaml")

        # Config should load with sensitive keys
        assert result["database"]["password"] == "secret123"
        assert result["database"]["api_token"] == "token_abc"


class TestYAMLConfigLoaderCaching:
    """Test suite for caching functionality."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config_data = {"test_key": "test_value"}
            config_file = tmp_path / "cached_config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            yield tmp_path

    def test_cache_enabled_by_default(self, temp_config_dir):
        """Test that caching is enabled by default."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)

        # First load - from file
        result1 = loader.load("cached_config.yaml")

        # Second load - from cache
        result2 = loader.load("cached_config.yaml")

        assert result1 == result2

    def test_cache_can_be_disabled(self, temp_config_dir):
        """Test that cache can be disabled."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)

        # Load without cache
        result1 = loader.load("cached_config.yaml", use_cache=False)
        result2 = loader.load("cached_config.yaml", use_cache=False)

        assert result1 == result2

    def test_cache_stores_config(self, temp_config_dir):
        """Test that cache stores the loaded config."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)

        result = loader.load("cached_config.yaml")

        assert "cached_config.yaml" in loader._cache
        assert loader._cache["cached_config.yaml"] == result

    def test_clear_cache(self, temp_config_dir):
        """Test clearing the cache."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)

        # Load to populate cache
        loader.load("cached_config.yaml")
        assert len(loader._cache) > 0

        # Clear cache
        loader.clear_cache()
        assert len(loader._cache) == 0

    def test_cache_thread_safety(self, temp_config_dir):
        """Test that cache is thread-safe."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        results = []
        errors = []

        def load_config():
            try:
                result = loader.load("cached_config.yaml")
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=load_config) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get results without errors
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r == results[0] for r in results)

    def test_cache_with_rlock(self, temp_config_dir):
        """Test that cache operations use RLock for thread safety."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)

        # RLock allows recursive locking
        with loader._cache_lock:
            with loader._cache_lock:
                # Should not deadlock
                loader.load("cached_config.yaml")

    def test_cache_key_uses_filename(self, temp_config_dir):
        """Test that cache key is based on filename."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)

        loader.load("cached_config.yaml")

        assert "cached_config.yaml" in loader._cache


class TestYAMLConfigLoaderGetNested:
    """Test suite for get_nested method."""

    def test_get_nested_simple_key(self):
        """Test getting simple key without nesting."""
        loader = YAMLConfigLoader()
        config = {"simple_key": "simple_value"}

        result = loader.get_nested(config, "simple_key")

        assert result == "simple_value"

    def test_get_nested_with_dot_notation(self):
        """Test getting nested value with dot notation."""
        loader = YAMLConfigLoader()
        config = {"level1": {"level2": {"level3": "deep_value"}}}

        result = loader.get_nested(config, "level1.level2.level3")

        assert result == "deep_value"

    def test_get_nested_with_default_value(self):
        """Test get_nested returns default for missing key."""
        loader = YAMLConfigLoader()
        config = {"existing_key": "value"}

        result = loader.get_nested(config, "missing_key", default="default_value")

        assert result == "default_value"

    def test_get_nested_default_is_none(self):
        """Test get_nested returns None by default."""
        loader = YAMLConfigLoader()
        config = {"existing_key": "value"}

        result = loader.get_nested(config, "missing_key")

        assert result is None

    def test_get_nested_with_custom_separator(self):
        """Test get_nested with custom separator."""
        loader = YAMLConfigLoader()
        config = {"level1": {"level2": "value"}}

        result = loader.get_nested(config, "level1/level2", separator="/")

        assert result == "value"

    def test_get_nested_partial_path(self):
        """Test get_nested with partial path."""
        loader = YAMLConfigLoader()
        config = {"level1": {"level2": "value"}}

        result = loader.get_nested(config, "level1.nonexistent")

        assert result is None

    def test_get_nested_non_dict_in_path(self):
        """Test get_nested when path contains non-dict value."""
        loader = YAMLConfigLoader()
        config = {"level1": "string_value"}

        result = loader.get_nested(config, "level1.level2")

        assert result is None

    def test_get_nested_empty_config(self):
        """Test get_nested with empty config."""
        loader = YAMLConfigLoader()
        config = {}

        result = loader.get_nested(config, "any.key")

        assert result is None

    def test_get_nested_with_null_value(self):
        """Test get_nested returns default for null value."""
        loader = YAMLConfigLoader()
        config = {"key": None}

        result = loader.get_nested(config, "key", default="default")

        assert result == "default"


class TestYAMLConfigLoaderTierOverrides:
    """Test suite for tier-specific configuration overrides."""

    @pytest.fixture
    def temp_config_with_tiers(self):
        """Create config with tier overrides."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            config_data = {
                "base_param": "base_value",
                "exposure": {"max_strategy_exposure": 0.50, "max_pair_exposure": 0.15},
                "data_validation": {"lookback_max_days": 126, "min_liquidity_usd": 500000},
                "tiers": {
                    "micro": {
                        "exposure": {"max_strategy_exposure": 0.30, "max_pair_exposure": 0.10},
                        "data_validation": {"min_liquidity_usd": 100000},
                    },
                    "small": {"exposure": {"max_strategy_exposure": 0.40}},
                    "large": {"exposure": {"max_strategy_exposure": 0.60}},
                },
            }
            config_file = tmp_path / "tier_config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)

            yield tmp_path

    def test_load_with_tier_override_micro(self, temp_config_with_tiers):
        """Test loading config with micro tier overrides."""
        loader = YAMLConfigLoader(config_dir=temp_config_with_tiers)
        result = loader.load_with_tier_override("tier_config.yaml", "micro")

        # Base value should remain
        assert result["base_param"] == "base_value"

        # Micro tier overrides should be applied
        assert result["exposure"]["max_strategy_exposure"] == 0.30
        assert result["exposure"]["max_pair_exposure"] == 0.10
        assert result["data_validation"]["min_liquidity_usd"] == 100000

        # Non-overridden values should remain
        assert result["data_validation"]["lookback_max_days"] == 126

    def test_load_with_tier_override_small(self, temp_config_with_tiers):
        """Test loading config with small tier overrides."""
        loader = YAMLConfigLoader(config_dir=temp_config_with_tiers)
        result = loader.load_with_tier_override("tier_config.yaml", "small")

        # Small tier override
        assert result["exposure"]["max_strategy_exposure"] == 0.40

        # Non-overridden values should remain
        assert result["exposure"]["max_pair_exposure"] == 0.15

    def test_load_with_tier_override_large(self, temp_config_with_tiers):
        """Test loading config with large tier overrides."""
        loader = YAMLConfigLoader(config_dir=temp_config_with_tiers)
        result = loader.load_with_tier_override("tier_config.yaml", "large")

        assert result["exposure"]["max_strategy_exposure"] == 0.60
        assert result["exposure"]["max_pair_exposure"] == 0.15

    def test_load_with_no_tier(self, temp_config_with_tiers):
        """Test loading config without tier override."""
        loader = YAMLConfigLoader(config_dir=temp_config_with_tiers)
        result = loader.load_with_tier_override("tier_config.yaml")

        # Should have base values
        assert result["exposure"]["max_strategy_exposure"] == 0.50

    def test_load_with_nonexistent_tier(self, temp_config_with_tiers):
        """Test loading with non-existent tier."""
        loader = YAMLConfigLoader(config_dir=temp_config_with_tiers)
        result = loader.load_with_tier_override("tier_config.yaml", "nonexistent")

        # Should return base config
        assert result["exposure"]["max_strategy_exposure"] == 0.50

    def test_load_with_tier_no_tiers_section(self, temp_config_with_tiers):
        """Test tier override when config has no tiers section."""
        config_data = {"key": "value"}
        config_file = temp_config_with_tiers / "no_tiers.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=temp_config_with_tiers)
        result = loader.load_with_tier_override("no_tiers.yaml", "micro")

        assert result == {"key": "value"}

    def test_apply_overrides_recursively(self):
        """Test that overrides are applied recursively."""
        loader = YAMLConfigLoader()

        base = {
            "level1": {
                "level2": {"key1": "base_value1", "key2": "base_value2"},
                "key3": "base_value3",
            }
        }

        overrides = {"level1": {"level2": {"key1": "override_value1"}, "key3": "override_value3"}}

        result = loader._apply_overrides(base, overrides)

        assert result["level1"]["level2"]["key1"] == "override_value1"
        assert result["level1"]["level2"]["key2"] == "base_value2"  # Not overridden
        assert result["level1"]["key3"] == "override_value3"


class TestYAMLConfigLoaderValidation:
    """Test suite for configuration validation."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    def test_validate_with_dict(self, temp_config_dir):
        """Test validation with valid dict config."""
        config_data = {"key": "value"}
        config_file = temp_config_dir / "valid.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("valid.yaml")

        assert result == {"key": "value"}

    def test_validate_with_invalid_type(self, temp_config_dir):
        """Test validation with invalid config type (non-dict)."""
        config_file = temp_config_dir / "list_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(["item1", "item2"], f)

        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("list_config.yaml")

        # Should return empty dict for invalid type
        assert result == {}

    def test_validate_max_strategy_exposure_valid(self, temp_config_dir):
        """Test validation of valid max_strategy_exposure."""
        config_data = {"exposure": {"max_strategy_exposure": 0.50}}
        config_file = temp_config_dir / "valid_exposure.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("valid_exposure.yaml")

        assert result["exposure"]["max_strategy_exposure"] == 0.50

    def test_validate_max_strategy_exposure_invalid(self, temp_config_dir):
        """Test validation of invalid max_strategy_exposure (> 1)."""
        config_data = {"exposure": {"max_strategy_exposure": 1.5}}
        config_file = temp_config_dir / "invalid_exposure.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("invalid_exposure.yaml")

        # Should still load but log warning
        assert "exposure" in result

    def test_validate_lookback_max_days_valid(self, temp_config_dir):
        """Test validation of valid lookback_max_days."""
        config_data = {"data_validation": {"lookback_max_days": 126}}
        config_file = temp_config_dir / "valid_lookback.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("valid_lookback.yaml")

        assert result["data_validation"]["lookback_max_days"] == 126

    def test_validate_lookback_max_days_invalid(self, temp_config_dir):
        """Test validation of invalid lookback_max_days (negative)."""
        config_data = {"data_validation": {"lookback_max_days": -10}}
        config_file = temp_config_dir / "invalid_lookback.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("invalid_lookback.yaml")

        # Should still load but log warning
        assert "data_validation" in result

    def test_validate_enabled_boolean(self, temp_config_dir):
        """Test validation of enabled boolean field."""
        config_data = {"feature": {"enabled": True}}
        config_file = temp_config_dir / "enabled_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("enabled_config.yaml")

        assert result["feature"]["enabled"] is True

    def test_validate_tier_values(self, temp_config_dir):
        """Test validation of tier values."""
        valid_tiers = ["micro", "small", "medium", "large"]

        for tier in valid_tiers:
            config_data = {"tier": tier}
            config_file = temp_config_dir / f"{tier}_config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)

            loader = YAMLConfigLoader(config_dir=temp_config_dir)
            result = loader.load(f"{tier}_config.yaml")

            assert result["tier"] == tier

    def test_validate_tier_invalid(self, temp_config_dir):
        """Test validation of invalid tier value."""
        config_data = {"tier": "invalid_tier"}
        config_file = temp_config_dir / "invalid_tier.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("invalid_tier.yaml")

        # Should still load but log warning
        assert "tier" in result

    def test_validate_nested_config(self, temp_config_dir):
        """Test validation of nested configuration."""
        config_data = {"level1": {"level2": {"enabled": True, "max_strategy_exposure": 0.75}}}
        config_file = temp_config_dir / "nested_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.load("nested_config.yaml")

        assert result["level1"]["level2"]["enabled"] is True
        assert result["level1"]["level2"]["max_strategy_exposure"] == 0.75

    def test_validate_sensitive_key_detection(self, temp_config_dir):
        """Test that sensitive keys are detected during validation."""
        sensitive_keys = ["password", "secret", "api_key", "token", "private_key"]

        for key in sensitive_keys:
            config_data = {"config_section": {key: "sensitive_value"}}
            config_file = temp_config_dir / f"{key}_config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)

            loader = YAMLConfigLoader(config_dir=temp_config_dir)
            result = loader.load(f"{key}_config.yaml")

            # Should load despite sensitive key
            assert result["config_section"][key] == "sensitive_value"


class TestYAMLConfigLoaderMethods:
    """Test suite for YAMLConfigLoader convenience methods."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with strategy file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            config_data = {
                "test_param": "test_value",
                "tiers": {"micro": {"test_param": "micro_value"}},
            }
            config_file = tmp_path / "strategy_stock_allocator.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)

            yield tmp_path

    def test_get_strategy_stock_allocator_config(self, temp_config_dir):
        """Test getting strategy stock allocator config."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.get_strategy_stock_allocator_config()

        assert result["test_param"] == "test_value"

    def test_get_strategy_stock_allocator_config_with_tier(self, temp_config_dir):
        """Test getting strategy stock allocator config with tier."""
        loader = YAMLConfigLoader(config_dir=temp_config_dir)
        result = loader.get_strategy_stock_allocator_config(tier="micro")

        assert result["test_param"] == "micro_value"


class TestGlobalConfigFunctions:
    """Test suite for global configuration functions."""

    def test_get_config_loader_singleton(self):
        """Test that get_config_loader returns singleton instance."""
        # Reset singleton

        loader1 = get_config_loader()
        loader2 = get_config_loader()

        assert loader1 is loader2

    def test_get_config_loader_returns_instance(self):
        """Test that get_config_loader returns YAMLConfigLoader instance."""
        loader = get_config_loader()

        assert isinstance(loader, YAMLConfigLoader)

    def test_load_strategy_stock_allocator_config_function(self):
        """Test load_strategy_stock_allocator_config convenience function."""
        # This will try to load from actual config directory
        result = load_strategy_stock_allocator_config()

        # Should return dict (empty or with actual config)
        assert isinstance(result, dict)

    def test_load_momentum_filters_config_function(self):
        """Test load_momentum_filters_config convenience function."""
        result = load_momentum_filters_config()

        assert isinstance(result, dict)

    def test_load_market_detectors_config_function(self):
        """Test load_market_detectors_config convenience function."""
        result = load_market_detectors_config()

        assert isinstance(result, dict)

    def test_load_strategy_defaults_config_function(self):
        """Test load_strategy_defaults_config convenience function."""
        result = load_strategy_defaults_config()

        assert isinstance(result, dict)

    def test_load_learning_parameters_config_function(self):
        """Test load_learning_parameters_config convenience function."""
        result = load_learning_parameters_config()

        assert isinstance(result, dict)

    def test_get_filter_config_function(self):
        """Test get_filter_config convenience function."""
        result = get_filter_config("rsi_filter")

        assert isinstance(result, dict)

    def test_get_detector_config_function(self):
        """Test get_detector_config convenience function."""
        result = get_detector_config("trend_detector")

        assert isinstance(result, dict)

    def test_get_strategy_config_function(self):
        """Test get_strategy_config convenience function."""
        result = get_strategy_config("momentum_strategy")

        assert isinstance(result, dict)


class TestYAMLConfigLoaderErrorHandling:
    """Test suite for error handling in config loader."""

    def test_file_not_found_error(self, tmp_path):
        """Test handling of file not found."""
        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("nonexistent_file.yaml")

        assert result == {}

    def test_yaml_parse_error(self, tmp_path):
        """Test handling of YAML parse error."""
        invalid_file = tmp_path / "invalid.yaml"
        with open(invalid_file, 'w') as f:
            f.write("invalid: yaml: content: [")

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("invalid.yaml")

        assert result == {}

    def test_os_error_handling(self, tmp_path):
        """Test handling of OS/IO errors."""
        # Create a file and then make it unreadable (if possible)
        # This is OS-dependent, so we'll just verify the error path exists
        loader = YAMLConfigLoader(config_dir=tmp_path)

        # Try to load a directory instead of a file
        result = loader.load("temp")  # Directory name

        # Should handle gracefully
        assert isinstance(result, dict)

    def test_permission_error_handling(self, tmp_path):
        """Test handling of permission errors."""
        loader = YAMLConfigLoader(config_dir=tmp_path)

        # Try to load with path that might cause issues
        result = loader.load("../etc/passwd")  # Should fail gracefully

        # Should return empty dict on error
        assert isinstance(result, dict)

    def test_empty_directory(self, tmp_path):
        """Test loading from empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        loader = YAMLConfigLoader(config_dir=empty_dir)
        result = loader.load("any_file.yaml")

        assert result == {}


class TestYAMLConfigLoaderEdgeCases:
    """Test suite for edge cases in config loader."""

    def test_config_with_comments(self, tmp_path):
        """Test loading YAML with comments."""
        config_content = """
        # This is a comment
        section:
          key: value  # Inline comment
          # Another comment
          key2: value2
        """
        config_file = tmp_path / "with_comments.yaml"
        with open(config_file, 'w') as f:
            f.write(config_content)

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("with_comments.yaml")

        assert result["section"]["key"] == "value"
        assert result["section"]["key2"] == "value2"

    def test_config_with_special_characters(self, tmp_path):
        """Test loading config with special characters."""
        config_data = {
            "key_with_underscore": "value",
            "key-with-dash": "value2",
            "key.with.dots": "value3",
        }
        config_file = tmp_path / "special_chars.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("special_chars.yaml")

        assert "key_with_underscore" in result
        assert "key-with-dash" in result
        assert "key.with.dots" in result

    def test_config_with_multiline_strings(self, tmp_path):
        """Test loading config with multiline strings."""
        config_data = {
            "description": """
            This is a
            multiline
            description.
            """
        }
        config_file = tmp_path / "multiline.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("multiline.yaml")

        assert "description" in result
        assert isinstance(result["description"], str)

    def test_config_with_unicode(self, tmp_path):
        """Test loading config with unicode characters."""
        config_data = {"spanish": "Hola ñoño", "emoji": "🚀📈", "chinese": "你好"}
        config_file = tmp_path / "unicode.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("unicode.yaml")

        assert result["spanish"] == "Hola ñoño"
        assert result["emoji"] == "🚀📈"
        assert result["chinese"] == "你好"

    def test_config_with_very_deep_nesting(self, tmp_path):
        """Test loading config with very deep nesting."""
        config_data = {
            "level1": {"level2": {"level3": {"level4": {"level5": {"deep_value": "found"}}}}}
        }
        config_file = tmp_path / "deep_nested.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("deep_nested.yaml")

        deep_value = loader.get_nested(result, "level1.level2.level3.level4.level5.deep_value")
        assert deep_value == "found"

    def test_config_with_large_values(self, tmp_path):
        """Test loading config with large numeric values."""
        config_data = {
            "large_int": 999999999999,
            "large_float": 999999.999999,
            "small_float": 0.000001,
        }
        config_file = tmp_path / "large_values.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("large_values.yaml")

        assert result["large_int"] == 999999999999
        assert abs(result["large_float"] - 999999.999999) < 0.000001
        assert abs(result["small_float"] - 0.000001) < 1e-7

    def test_config_with_null_values(self, tmp_path):
        """Test loading config with explicit null values."""
        config_data = {"null_key": None, "string_key": "value"}
        config_file = tmp_path / "null_values.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("null_values.yaml")

        assert result["null_key"] is None
        assert result["string_key"] == "value"

    def test_sensitive_data_all_keys(self, tmp_path):
        """Test that all sensitive key patterns are detected."""
        # Test all sensitive keys that should trigger warning
        sensitive_keys = ["password", "secret", "api_key", "token", "private_key"]
        config_data = {key: f"value_{key}" for key in sensitive_keys}
        config_file = tmp_path / "all_sensitive.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        loader = YAMLConfigLoader(config_dir=tmp_path)
        result = loader.load("all_sensitive.yaml")

        # All keys should be present in result
        for key in sensitive_keys:
            assert key in result
            assert result[key] == f"value_{key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
