"""
Test Configuration and Environment Isolation
Testing Reviewer Audit - Phase 1: Critical Fixes
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

from app.core.exceptions import ConfigurationError


class TestEnvironmentConfig(BaseSettings):
    """Test-specific configuration to avoid conflicts with production."""
    
    # Test environment
    environment: str = Field(default="testing")
    debug: bool = Field(default=True)
    
    # Test database
    test_db_host: str = Field(default="localhost")
    test_db_port: int = Field(default=5433)  # Different port for tests
    test_db_name: str = Field(default="algotrading_test")
    test_db_user: str = Field(default="test_user")
    test_db_password: str = Field(default="test_password")
    
    # Test Redis
    test_redis_host: str = Field(default="localhost")
    test_redis_port: int = Field(default=6380)  # Different port for tests
    test_redis_db: int = Field(default=15)  # Use last DB slot
    
    # Test logging
    test_log_dir: str = Field(default="")
    test_log_level: str = Field(default="DEBUG")
    
    # Test API
    test_api_host: str = Field(default="127.0.0.1")
    test_api_port: int = Field(default=8001)  # Different port for tests
    
    # Test trading thresholds
    test_max_position_size: float = Field(default=0.05)  # Smaller for tests
    test_stop_loss_pct: float = Field(default=0.02)  # Tighter for tests
    test_take_profit_pct: float = Field(default=0.08)  # Smaller for tests
    
    @field_validator('test_db_port', 'test_redis_port', 'test_api_port')
    @classmethod
    def validate_ports(cls, v):
        if v < 1024 or v > 65535:
            raise ValueError("Port must be between 1024 and 65535")
        return v
    
    model_config = {
        "env_file": ".env.test",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


class TestConfigManager:
    """Manages test configuration and environment isolation."""
    
    def __init__(self):
        self._temp_dirs: Dict[str, Path] = {}
        self._original_env: Dict[str, Optional[str]] = {}
        self._test_config: Optional[TestEnvironmentConfig] = None
    
    def setup_test_environment(self) -> TestEnvironmentConfig:
        """Setup isolated test environment."""
        # Create temporary directories
        self._create_temp_directories()
        
        # Store original environment
        self._store_original_environment()
        
        # Set test environment variables
        self._set_test_environment()
        
        # Load test configuration
        self._test_config = TestEnvironmentConfig()
        
        return self._test_config
    
    def cleanup_test_environment(self) -> None:
        """Cleanup test environment and restore original state."""
        # Restore original environment
        self._restore_original_environment()
        
        # Cleanup temporary directories
        self._cleanup_temp_directories()
        
        self._test_config = None
    
    def _create_temp_directories(self) -> None:
        """Create temporary directories for test isolation."""
        import uuid
        
        temp_base = Path(tempfile.gettempdir()) / f"algotrading_tests_{uuid.uuid4().hex[:8]}"
        temp_base.mkdir(exist_ok=True)
        
        self._temp_dirs = {
            "logs": temp_base / "logs",
            "data": temp_base / "data", 
            "cache": temp_base / "cache",
            "config": temp_base / "config"
        }
        
        for temp_dir in self._temp_dirs.values():
            temp_dir.mkdir(exist_ok=True)
    
    def _cleanup_temp_directories(self) -> None:
        """Cleanup temporary directories."""
        import shutil
        
        for temp_dir in self._temp_dirs.values():
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        self._temp_dirs.clear()
    
    def _store_original_environment(self) -> None:
        """Store original environment variables."""
        env_vars = [
            "ENVIRONMENT", "DEBUG", "LOG_LEVEL", "LOG_DIR",
            "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
            "REDIS_HOST", "REDIS_PORT", "REDIS_DB",
            "API_HOST", "API_PORT",
            "MAX_POSITION_SIZE", "STOP_LOSS_PCT", "TAKE_PROFIT_PCT"
        ]
        
        for var in env_vars:
            self._original_env[var] = os.environ.get(var)
    
    def _set_test_environment(self) -> None:
        """Set test environment variables."""
        test_env_vars = {
            "ENVIRONMENT": "testing",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "LOG_DIR": str(self._temp_dirs["logs"]),
            "DB_HOST": "localhost",
            "DB_PORT": "5433",
            "DB_NAME": "algotrading_test",
            "DB_USER": "test_user", 
            "DB_PASSWORD": "test_password",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6380",
            "REDIS_DB": "15",
            "API_HOST": "127.0.0.1",
            "API_PORT": "8001",
            "MAX_POSITION_SIZE": "0.05",
            "STOP_LOSS_PCT": "0.02",
            "TAKE_PROFIT_PCT": "0.08"
        }
        
        for key, value in test_env_vars.items():
            os.environ[key] = value
    
    def _restore_original_environment(self) -> None:
        """Restore original environment variables."""
        import os
        
        for key, original_value in self._original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
        
        self._original_env.clear()
    
    @property
    def test_config(self) -> TestEnvironmentConfig:
        """Get current test configuration."""
        if self._test_config is None:
            raise ConfigurationError("Test environment not setup. Call setup_test_environment() first.")
        return self._test_config
    
    @property
    def temp_dirs(self) -> Dict[str, Path]:
        """Get temporary directories."""
        return self._temp_dirs.copy()


# Global test config manager instance
_test_config_manager: Optional[TestConfigManager] = None


def get_test_config_manager() -> TestConfigManager:
    """Get global test configuration manager."""
    global _test_config_manager
    if _test_config_manager is None:
        _test_config_manager = TestConfigManager()
    return _test_config_manager


def setup_test_environment() -> TestEnvironmentConfig:
    """Setup test environment."""
    return get_test_config_manager().setup_test_environment()


def cleanup_test_environment() -> None:
    """Cleanup test environment."""
    global _test_config_manager
    if _test_config_manager is not None:
        _test_config_manager.cleanup_test_environment()
        _test_config_manager = None


def get_test_config() -> TestEnvironmentConfig:
    """Get current test configuration."""
    return get_test_config_manager().test_config


def get_test_temp_dir(name: str) -> Path:
    """Get temporary directory for tests."""
    return get_test_config_manager().temp_dirs[name]
