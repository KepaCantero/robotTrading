"""
Tests for centralized configuration system.

This module contains comprehensive tests for the centralized configuration
system that eliminates hardcoded values throughout the application.
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from app.core.centralized_config import (
    ConfigEnvironment, TradingThresholds, RiskManagementThresholds,
    CircuitBreakerThresholds, DatabaseConfig, RedisConfig, APIConfig,
    MonitoringConfig, CentralizedConfig, ConfigManager,
    get_config, get_trading_thresholds, get_risk_thresholds,
    get_circuit_breaker_thresholds, get_database_config, get_redis_config,
    get_api_config, get_monitoring_config, load_config, save_config
)


class TestConfigModels:
    """Test configuration models validation."""
    
    def test_trading_thresholds_validation(self):
        """Test trading thresholds validation."""
        # Valid configuration
        config = TradingThresholds(
            min_strength=60.0,
            min_confidence=70.0,
            rsi_oversold=30.0,
            rsi_overbought=70.0,
            max_position_size=0.1,
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )
        assert config.min_strength == 60.0
        assert config.rsi_oversold == 30.0
        assert config.rsi_overbought == 70.0
    
    def test_trading_thresholds_invalid_rsi_oversold(self):
        """Test invalid RSI oversold threshold."""
        with pytest.raises(ValueError, match="RSI oversold threshold must be below 50"):
            TradingThresholds(
                min_strength=60.0,
                min_confidence=70.0,
                rsi_oversold=60.0,  # Invalid: above 50
                rsi_overbought=70.0,
                max_position_size=0.1,
                stop_loss_pct=0.05,
                take_profit_pct=0.15
            )
    
    def test_trading_thresholds_invalid_rsi_overbought(self):
        """Test invalid RSI overbought threshold."""
        with pytest.raises(ValueError, match="RSI overbought threshold must be above 50"):
            TradingThresholds(
                min_strength=60.0,
                min_confidence=70.0,
                rsi_oversold=30.0,
                rsi_overbought=40.0,  # Invalid: below 50
                max_position_size=0.1,
                stop_loss_pct=0.05,
                take_profit_pct=0.15
            )
    
    def test_risk_management_thresholds_validation(self):
        """Test risk management thresholds validation."""
        config = RiskManagementThresholds(
            daily_loss_limit=0.05,
            max_drawdown_limit=0.15,
            single_trade_risk_pct=0.02,
            correlation_limit=0.7,
            sector_exposure_limit=0.3
        )
        assert config.daily_loss_limit == 0.05
        assert config.max_drawdown_limit == 0.15
    
    def test_risk_management_thresholds_invalid_daily_loss(self):
        """Test invalid daily loss limit."""
        with pytest.raises(ValueError, match="Daily loss limit should not exceed 10%"):
            RiskManagementThresholds(
                daily_loss_limit=0.15,  # Invalid: exceeds 10%
                max_drawdown_limit=0.15,
                single_trade_risk_pct=0.02,
                correlation_limit=0.7,
                sector_exposure_limit=0.3
            )
    
    def test_circuit_breaker_thresholds_validation(self):
        """Test circuit breaker thresholds validation."""
        config = CircuitBreakerThresholds(
            daily_loss=0.03,
            drawdown=0.1,
            volatility=0.05,
            error_rate=0.05,
            latency_ms=1000
        )
        assert config.daily_loss == 0.03
        assert config.latency_ms == 1000
    
    def test_database_config_validation(self):
        """Test database configuration validation."""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="algotrading",
            username="postgres",
            password="",
            pool_size=10,
            max_overflow=20
        )
        assert config.host == "localhost"
        assert config.port == 5432
    
    def test_redis_config_validation(self):
        """Test Redis configuration validation."""
        config = RedisConfig(
            host="localhost",
            port=6379,
            password=None,
            db=0,
            max_connections=20
        )
        assert config.host == "localhost"
        assert config.port == 6379
    
    def test_api_config_validation(self):
        """Test API configuration validation."""
        config = APIConfig(
            host="0.0.0.0",
            port=8000,
            workers=1,
            reload=False,
            log_level="INFO",
            cors_origins=["*"]
        )
        assert config.host == "0.0.0.0"
        assert config.port == 8000
    
    def test_monitoring_config_validation(self):
        """Test monitoring configuration validation."""
        config = MonitoringConfig(
            enable_metrics=True,
            metrics_port=9090,
            health_check_interval=30,
            alert_email=None,
            slack_webhook=None
        )
        assert config.enable_metrics is True
        assert config.metrics_port == 9090


class TestConfigManager:
    """Test configuration manager functionality."""
    
    def test_config_manager_initialization(self):
        """Test configuration manager initialization."""
        manager = ConfigManager()
        assert manager.config_path is not None
        assert manager._config is None
    
    def test_config_manager_with_custom_path(self):
        """Test configuration manager with custom path."""
        custom_path = "/custom/path/config.json"
        manager = ConfigManager(custom_path)
        assert manager.config_path == custom_path
    
    def test_load_config_default(self):
        """Test loading default configuration."""
        manager = ConfigManager()
        config = manager.load_config()
        
        assert isinstance(config, CentralizedConfig)
        assert config.environment == ConfigEnvironment.DEVELOPMENT
        assert isinstance(config.trading, TradingThresholds)
        assert isinstance(config.risk_management, RiskManagementThresholds)
        assert isinstance(config.circuit_breakers, CircuitBreakerThresholds)
    
    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        test_config = {
            "environment": "production",
            "trading": {
                "min_strength": 65.0,
                "min_confidence": 75.0,
                "rsi_oversold": 25.0,
                "rsi_overbought": 75.0,
                "max_position_size": 0.08,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.12
            },
            "risk_management": {
                "daily_loss_limit": 0.03,
                "max_drawdown_limit": 0.10,
                "single_trade_risk_pct": 0.015,
                "correlation_limit": 0.6,
                "sector_exposure_limit": 0.25
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(temp_path)
            config = manager.load_config()
            
            assert config.environment == ConfigEnvironment.PRODUCTION
            assert config.trading.min_strength == 65.0
            assert config.trading.min_confidence == 75.0
            assert config.risk_management.daily_loss_limit == 0.03
        finally:
            os.unlink(temp_path)
    
    def test_save_config(self):
        """Test saving configuration to file."""
        config = CentralizedConfig()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            manager = ConfigManager(temp_path)
            manager.save_config(config)
            
            # Verify file was created and contains valid JSON
            assert os.path.exists(temp_path)
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data["environment"] == "development"
            assert "trading" in saved_data
            assert "risk_management" in saved_data
        finally:
            os.unlink(temp_path)
    
    def test_update_config(self):
        """Test updating configuration."""
        manager = ConfigManager()
        config = manager.load_config()
        
        # Update trading thresholds
        updates = {
            "trading": TradingThresholds(
                min_strength=65.0,
                min_confidence=75.0,
                rsi_oversold=25.0,
                rsi_overbought=75.0,
                max_position_size=0.08,
                stop_loss_pct=0.03,
                take_profit_pct=0.12
            )
        }
        
        updated_config = manager.update_config(updates)
        assert updated_config.trading.min_strength == 65.0
        assert updated_config.trading.min_confidence == 75.0
    
    def test_validate_config(self):
        """Test configuration validation."""
        manager = ConfigManager()
        config = manager.load_config()
        
        # Valid configuration should pass
        assert manager.validate_config(config) is True
        
        # Invalid configuration should fail
        invalid_config = CentralizedConfig()
        invalid_config.trading.rsi_oversold = 60.0  # Invalid value
        assert manager.validate_config(invalid_config) is False
    
    def test_get_specific_configs(self):
        """Test getting specific configuration sections."""
        manager = ConfigManager()
        config = manager.load_config()
        
        trading = manager.get_trading_thresholds()
        assert isinstance(trading, TradingThresholds)
        
        risk = manager.get_risk_thresholds()
        assert isinstance(risk, RiskManagementThresholds)
        
        circuit_breakers = manager.get_circuit_breaker_thresholds()
        assert isinstance(circuit_breakers, CircuitBreakerThresholds)
        
        database = manager.get_database_config()
        assert isinstance(database, DatabaseConfig)
        
        redis = manager.get_redis_config()
        assert isinstance(redis, RedisConfig)
        
        api = manager.get_api_config()
        assert isinstance(api, APIConfig)
        
        monitoring = manager.get_monitoring_config()
        assert isinstance(monitoring, MonitoringConfig)


class TestGlobalFunctions:
    """Test global configuration functions."""
    
    def test_get_config(self):
        """Test getting global configuration."""
        config = get_config()
        assert isinstance(config, CentralizedConfig)
    
    def test_get_trading_thresholds(self):
        """Test getting trading thresholds."""
        thresholds = get_trading_thresholds()
        assert isinstance(thresholds, TradingThresholds)
        assert thresholds.min_strength == 60.0
    
    def test_get_risk_thresholds(self):
        """Test getting risk management thresholds."""
        thresholds = get_risk_thresholds()
        assert isinstance(thresholds, RiskManagementThresholds)
        assert thresholds.daily_loss_limit == 0.05
    
    def test_get_circuit_breaker_thresholds(self):
        """Test getting circuit breaker thresholds."""
        thresholds = get_circuit_breaker_thresholds()
        assert isinstance(thresholds, CircuitBreakerThresholds)
        assert thresholds.daily_loss == 0.03
    
    def test_get_database_config(self):
        """Test getting database configuration."""
        config = get_database_config()
        assert isinstance(config, DatabaseConfig)
        assert config.host == "localhost"
    
    def test_get_redis_config(self):
        """Test getting Redis configuration."""
        config = get_redis_config()
        assert isinstance(config, RedisConfig)
        assert config.host == "localhost"
    
    def test_get_api_config(self):
        """Test getting API configuration."""
        config = get_api_config()
        assert isinstance(config, APIConfig)
        assert config.host == "0.0.0.0"
    
    def test_get_monitoring_config(self):
        """Test getting monitoring configuration."""
        config = get_monitoring_config()
        assert isinstance(config, MonitoringConfig)
        assert config.enable_metrics is True
    
    def test_load_config_with_environment(self):
        """Test loading configuration for specific environment."""
        config = load_config(ConfigEnvironment.PRODUCTION)
        assert isinstance(config, CentralizedConfig)
    
    def test_save_config(self):
        """Test saving configuration."""
        config = CentralizedConfig()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            save_config(config, temp_path)
            assert os.path.exists(temp_path)
        finally:
            os.unlink(temp_path)


class TestEnvironmentSpecificConfigs:
    """Test environment-specific configuration loading."""
    
    def test_development_config(self):
        """Test development configuration."""
        config = load_config(ConfigEnvironment.DEVELOPMENT)
        assert config.environment == ConfigEnvironment.DEVELOPMENT
        assert config.api.reload is False  # Default value
    
    def test_production_config(self):
        """Test production configuration."""
        config = load_config(ConfigEnvironment.PRODUCTION)
        assert config.environment == ConfigEnvironment.PRODUCTION
    
    def test_testing_config(self):
        """Test testing configuration."""
        config = load_config(ConfigEnvironment.TESTING)
        assert config.environment == ConfigEnvironment.TESTING


class TestConfigurationIntegration:
    """Test configuration integration with services."""
    
    def test_trading_thresholds_integration(self):
        """Test trading thresholds integration."""
        thresholds = get_trading_thresholds()
        
        # Verify all required fields are present
        assert hasattr(thresholds, 'min_strength')
        assert hasattr(thresholds, 'min_confidence')
        assert hasattr(thresholds, 'rsi_oversold')
        assert hasattr(thresholds, 'rsi_overbought')
        assert hasattr(thresholds, 'max_position_size')
        assert hasattr(thresholds, 'stop_loss_pct')
        assert hasattr(thresholds, 'take_profit_pct')
        
        # Verify values are within expected ranges
        assert 0 <= thresholds.min_strength <= 100
        assert 0 <= thresholds.min_confidence <= 100
        assert 0 <= thresholds.rsi_oversold < 50
        assert 50 < thresholds.rsi_overbought <= 100
        assert 0 <= thresholds.max_position_size <= 1
        assert 0 <= thresholds.stop_loss_pct <= 1
        assert 0 <= thresholds.take_profit_pct <= 1
    
    def test_risk_management_integration(self):
        """Test risk management thresholds integration."""
        thresholds = get_risk_thresholds()
        
        # Verify all required fields are present
        assert hasattr(thresholds, 'daily_loss_limit')
        assert hasattr(thresholds, 'max_drawdown_limit')
        assert hasattr(thresholds, 'single_trade_risk_pct')
        assert hasattr(thresholds, 'correlation_limit')
        assert hasattr(thresholds, 'sector_exposure_limit')
        
        # Verify values are within expected ranges
        assert 0 <= thresholds.daily_loss_limit <= 0.1
        assert 0 <= thresholds.max_drawdown_limit <= 1
        assert 0 <= thresholds.single_trade_risk_pct <= 1
        assert 0 <= thresholds.correlation_limit <= 1
        assert 0 <= thresholds.sector_exposure_limit <= 1
    
    def test_circuit_breaker_integration(self):
        """Test circuit breaker thresholds integration."""
        thresholds = get_circuit_breaker_thresholds()
        
        # Verify all required fields are present
        assert hasattr(thresholds, 'daily_loss')
        assert hasattr(thresholds, 'drawdown')
        assert hasattr(thresholds, 'volatility')
        assert hasattr(thresholds, 'error_rate')
        assert hasattr(thresholds, 'latency_ms')
        
        # Verify values are within expected ranges
        assert 0 <= thresholds.daily_loss <= 1
        assert 0 <= thresholds.drawdown <= 1
        assert 0 <= thresholds.volatility <= 1
        assert 0 <= thresholds.error_rate <= 1
        assert 0 <= thresholds.latency_ms


class TestConfigurationEdgeCases:
    """Test configuration edge cases and error handling."""
    
    def test_missing_config_file(self):
        """Test behavior when config file is missing."""
        manager = ConfigManager("/nonexistent/path/config.json")
        config = manager.load_config()
        
        # Should load default configuration
        assert isinstance(config, CentralizedConfig)
        assert config.environment == ConfigEnvironment.DEVELOPMENT
    
    def test_invalid_json_config(self):
        """Test behavior with invalid JSON in config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name
        
        try:
            manager = ConfigManager(temp_path)
            # Should raise an exception for invalid JSON
            with pytest.raises(Exception):
                manager.load_config()
        finally:
            os.unlink(temp_path)
    
    def test_partial_config_override(self):
        """Test partial configuration override."""
        test_config = {
            "trading": {
                "min_strength": 65.0,
                "min_confidence": 75.0
                # Other fields should use defaults
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(temp_path)
            config = manager.load_config()
            
            # Overridden values
            assert config.trading.min_strength == 65.0
            assert config.trading.min_confidence == 75.0
            
            # Default values should still be present
            assert config.trading.rsi_oversold == 30.0
            assert config.trading.rsi_overbought == 70.0
        finally:
            os.unlink(temp_path)
    
    def test_config_serialization(self):
        """Test configuration serialization to dict."""
        config = CentralizedConfig()
        config_dict = config.dict()
        
        assert isinstance(config_dict, dict)
        assert "environment" in config_dict
        assert "trading" in config_dict
        assert "risk_management" in config_dict
        assert "circuit_breakers" in config_dict
        assert "database" in config_dict
        assert "redis" in config_dict
        assert "api" in config_dict
        assert "monitoring" in config_dict

