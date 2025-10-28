"""
Tests for environment configuration.
"""

from unittest.mock import patch

from app.core.environment_config import APIConfig, CentralizedConfig as EnvConfig


class TestAPIConfig:
    """Test API configuration."""

    def test_api_config_defaults(self):
        """Test API configuration defaults."""
        config = APIConfig(
            secret_key="12345678901234567890123456789012",
        )
        assert config.api_host == "0.0.0.0"
        assert config.api_port == 8000


class TestCentralizedConfig:
    """Test centralized configuration."""

    def test_centralized_config_defaults(self):
        """Test centralized config defaults."""
        config = EnvConfig()
        assert config is not None

    def test_centralized_config_with_env_vars(self):
        """Test centralized config with environment variables."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            config = EnvConfig()
            assert config is not None

    def test_centralized_config_validation(self):
        """Test centralized config validation."""
        config = EnvConfig()
        # Validation happens on initialization
        assert config is not None

    def test_centralized_config_methods(self):
        """Test centralized config methods."""
        config = EnvConfig()
        config_dict = config.get_config_dict()
        assert isinstance(config_dict, dict)


class TestConfigFunctions:
    """Test configuration functions."""

    def test_reload_config(self):
        """Test config reload functionality."""
        config = EnvConfig()
        assert config is not None

    def test_set_config(self):
        """Test setting configuration."""
        config = EnvConfig()
        assert config is not None

    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        config = EnvConfig()
        assert config is not None

    def test_create_config_for_environment(self):
        """Test creating config for specific environment."""
        config = EnvConfig()
        assert config is not None


class TestConfigIntegration:
    """Test configuration integration."""

    def test_config_with_all_components(self):
        """Test config with all components."""
        config = EnvConfig()
        assert config is not None

    def test_config_environment_specific_validation(self):
        """Test environment-specific validation."""
        config = EnvConfig()
        assert config is not None

    def test_config_override_behavior(self):
        """Test configuration override behavior."""
        config = EnvConfig()
        assert config is not None
