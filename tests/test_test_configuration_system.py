"""
Enhanced Test Configuration System
Testing Reviewer Audit - Phase 1: Critical Fixes
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch

from app.core.test_config import (
    TestConfigManager,
    TestEnvironmentConfig,
    setup_test_environment,
    cleanup_test_environment,
    get_test_config
)
from app.core.centralized_config import CentralizedConfig, get_config


class TestTestConfigurationSystem:
    """Test the test configuration system."""
    
    def test_test_config_manager_creation(self):
        """Test TestConfigManager creation."""
        manager = TestConfigManager()
        assert manager is not None
        assert manager._temp_dirs == {}
        assert manager._original_env == {}
        assert manager._test_config is None
    
    def test_setup_test_environment(self):
        """Test test environment setup."""
        manager = TestConfigManager()
        config = manager.setup_test_environment()
        
        assert isinstance(config, TestEnvironmentConfig)
        assert config.environment == "testing"
        assert config.debug is True
        assert config.test_db_port == 5433
        assert config.test_redis_port == 6380
        assert config.test_api_port == 8001
        
        # Check temp directories were created
        assert len(manager._temp_dirs) == 4
        assert "logs" in manager._temp_dirs
        assert "data" in manager._temp_dirs
        assert "cache" in manager._temp_dirs
        assert "config" in manager._temp_dirs
        
        # Check directories exist
        for temp_dir in manager._temp_dirs.values():
            assert temp_dir.exists()
        
        manager.cleanup_test_environment()
    
    def test_cleanup_test_environment(self):
        """Test test environment cleanup."""
        manager = TestConfigManager()
        manager.setup_test_environment()
        
        # Store temp dirs before cleanup
        temp_dirs = manager._temp_dirs.copy()
        
        manager.cleanup_test_environment()
        
        # Check temp dirs were cleaned up
        for temp_dir in temp_dirs.values():
            assert not temp_dir.exists()
        
        assert manager._temp_dirs == {}
        assert manager._original_env == {}
        assert manager._test_config is None
    
    def test_environment_variables_setting(self):
        """Test environment variables are set correctly."""
        manager = TestConfigManager()
        
        # Store original environment
        original_env = {
            "ENVIRONMENT": "development",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO"
        }
        
        for key, value in original_env.items():
            import os
            os.environ[key] = value
        
        manager.setup_test_environment()
        
        # Check test environment variables
        import os
        assert os.environ["ENVIRONMENT"] == "testing"
        assert os.environ["DEBUG"] == "true"
        assert os.environ["LOG_LEVEL"] == "DEBUG"
        assert os.environ["DB_PORT"] == "5433"
        assert os.environ["REDIS_PORT"] == "6380"
        assert os.environ["API_PORT"] == "8001"
        
        manager.cleanup_test_environment()
        
        # Check original environment restored
        assert os.environ["ENVIRONMENT"] == "development"
        assert os.environ["DEBUG"] == "false"
        assert os.environ["LOG_LEVEL"] == "INFO"
    
    def test_test_config_property(self):
        """Test test_config property access."""
        manager = TestConfigManager()
        
        # Should raise error when not setup
        with pytest.raises(Exception):  # ConfigurationError
            _ = manager.test_config
        
        # Setup and test
        manager.setup_test_environment()
        config = manager.test_config
        assert isinstance(config, TestEnvironmentConfig)
        
        manager.cleanup_test_environment()
    
    def test_temp_dirs_property(self):
        """Test temp_dirs property access."""
        manager = TestConfigManager()
        manager.setup_test_environment()
        
        temp_dirs = manager.temp_dirs
        assert isinstance(temp_dirs, dict)
        assert len(temp_dirs) == 4
        
        # Should be a copy
        temp_dirs["new_key"] = "new_value"
        assert "new_key" not in manager._temp_dirs
        
        manager.cleanup_test_environment()
    
    def test_global_functions(self):
        """Test global test configuration functions."""
        # Test setup
        config = setup_test_environment()
        assert isinstance(config, TestEnvironmentConfig)
        
        # Test get_test_config
        retrieved_config = get_test_config()
        assert retrieved_config is config
        
        # Test cleanup
        cleanup_test_environment()
        
        # Should raise error after cleanup
        with pytest.raises(Exception):  # ConfigurationError
            _ = get_test_config()


class TestTestEnvironmentConfig:
    """Test TestEnvironmentConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = TestEnvironmentConfig()
        
        assert config.environment == "testing"
        assert config.debug is True
        assert config.test_db_port == 5433
        assert config.test_redis_port == 6380
        assert config.test_api_port == 8001
        assert config.test_max_position_size == 0.05
        assert config.test_stop_loss_pct == 0.02
        assert config.test_take_profit_pct == 0.08
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = TestEnvironmentConfig(
            environment="custom_test",
            debug=False,
            test_db_port=5434,
            test_redis_port=6381,
            test_api_port=8002
        )
        
        assert config.environment == "custom_test"
        assert config.debug is False
        assert config.test_db_port == 5434
        assert config.test_redis_port == 6381
        assert config.test_api_port == 8002
    
    def test_validation(self):
        """Test configuration validation."""
        # Test valid values
        config = TestEnvironmentConfig(
            test_db_port=5432,
            test_redis_port=6379,
            test_api_port=8000
        )
        assert config.test_db_port == 5432
        assert config.test_redis_port == 6379
        assert config.test_api_port == 8000
        
        # Test invalid values (should raise validation errors)
        with pytest.raises(Exception):  # ValidationError
            TestEnvironmentConfig(test_db_port=-1)
        
        with pytest.raises(Exception):  # ValidationError
            TestEnvironmentConfig(test_redis_port=0)
        
        with pytest.raises(Exception):  # ValidationError
            TestEnvironmentConfig(test_api_port=1023)  # Below valid range


class TestTestIsolation:
    """Test test isolation features."""
    
    def test_temp_directory_isolation(self):
        """Test that temp directories are isolated."""
        manager1 = TestConfigManager()
        manager2 = TestConfigManager()
        
        config1 = manager1.setup_test_environment()
        config2 = manager2.setup_test_environment()
        
        # Should have different temp directories
        assert manager1._temp_dirs != manager2._temp_dirs
        
        # But same configuration values
        assert config1.environment == config2.environment
        assert config1.test_db_port == config2.test_db_port
        
        manager1.cleanup_test_environment()
        manager2.cleanup_test_environment()
    
    def test_environment_isolation(self):
        """Test that environment variables are isolated."""
        import os
        
        # Set initial environment
        os.environ["TEST_VAR"] = "initial_value"
        
        manager = TestConfigManager()
        manager.setup_test_environment()
        
        # Modify environment during test
        os.environ["TEST_VAR"] = "modified_value"
        
        manager.cleanup_test_environment()
        
        # Should be restored to original
        assert os.environ["TEST_VAR"] == "initial_value"
        
        # Clean up
        del os.environ["TEST_VAR"]


class TestTestConfigurationIntegration:
    """Test integration with centralized configuration."""
    
    def test_configuration_override(self):
        """Test that test configuration overrides centralized config."""
        # Setup test environment
        test_config = setup_test_environment()
        
        # Get centralized config
        centralized_config = get_config()
        
        # Test configuration should override centralized config
        assert centralized_config.environment == "testing"
        assert centralized_config.debug is True
        
        cleanup_test_environment()
    
    def test_configuration_isolation(self):
        """Test that test configuration doesn't affect production config."""
        # Store original config
        original_config = get_config()
        
        # Setup test environment
        test_config = setup_test_environment()
        test_centralized_config = get_config()
        
        # Should be different instances
        assert test_centralized_config is not original_config
        
        # Cleanup
        cleanup_test_environment()
        
        # Should restore original
        restored_config = get_config()
        assert restored_config is original_config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
