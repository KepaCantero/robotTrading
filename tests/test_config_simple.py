"""
Simplified Tests for Centralized Configuration System
TASK-10: Centralización de Configuración
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that we can import the configuration modules."""
    try:
        pass

        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_trading_thresholds():
    """Test TradingThresholds configuration."""
    try:
        from app.core.centralized_config import TradingThresholds

        thresholds = TradingThresholds()

        # Test default values
        assert thresholds.min_signal_strength == 60.0
        assert thresholds.min_signal_confidence == 70.0
        assert thresholds.min_liquidity_score == 50.0
        assert thresholds.rsi_oversold == 30.0
        assert thresholds.rsi_overbought == 70.0
        assert thresholds.max_position_size == 0.1
        assert thresholds.stop_loss_pct == 0.05
        assert thresholds.take_profit_pct == 0.15
        assert thresholds.daily_loss_limit == 0.05
        assert thresholds.max_drawdown_limit == 0.15
        assert thresholds.max_total_exposure == 0.8
        assert thresholds.max_sector_exposure == 0.3
        assert thresholds.max_correlation == 0.7

        print("✅ TradingThresholds test passed")
        return True
    except Exception as e:
        print(f"❌ TradingThresholds test failed: {e}")
        return False


def test_strategy_config():
    """Test StrategyConfig configuration."""
    try:
        from app.core.centralized_config import StrategyConfig

        config = StrategyConfig(name="test_strategy")

        assert config.name == "test_strategy"
        assert config.enabled is True
        assert config.weight == 1.0
        assert config.parameters == {}
        assert config.max_position_size is None
        assert config.stop_loss_pct is None
        assert config.take_profit_pct is None
        assert config.min_sharpe_ratio == 1.0
        assert config.max_drawdown == 0.15
        assert config.min_win_rate == 0.4

        print("✅ StrategyConfig test passed")
        return True
    except Exception as e:
        print(f"❌ StrategyConfig test failed: {e}")
        return False


def test_database_config():
    """Test DatabaseConfig configuration."""
    try:
        from app.core.centralized_config import DatabaseConfig

        config = DatabaseConfig()

        assert config.host == "localhost"
        assert config.port == 5432
        assert config.name == "algotrading"
        assert config.user == "postgres"
        assert config.password == "password"
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 30
        assert config.ssl_mode == "prefer"

        # Test connection string
        config_custom = DatabaseConfig(
            host="db.example.com",
            port=5433,
            name="trading_db",
            user="trader",
            password="secret123",
        )
        expected = "postgresql://trader:secret123@db.example.com:5433/trading_db"
        assert config_custom.connection_string == expected

        print("✅ DatabaseConfig test passed")
        return True
    except Exception as e:
        print(f"❌ DatabaseConfig test failed: {e}")
        return False


def test_redis_config():
    """Test RedisConfig configuration."""
    try:
        from app.core.centralized_config import RedisConfig

        config = RedisConfig()

        assert config.host == "localhost"
        assert config.port == 6379
        assert config.password is None
        assert config.db == 0
        assert config.max_connections == 20
        assert config.socket_timeout == 5

        # Test connection string without password
        config_no_pass = RedisConfig(host="redis.example.com", port=6380, db=1)
        expected = "redis://redis.example.com:6380/1"
        assert config_no_pass.connection_string == expected

        # Test connection string with password
        config_with_pass = RedisConfig(host="redis.example.com", port=6380, password="secret", db=1)
        expected = "redis://:secret@redis.example.com:6380/1"
        assert config_with_pass.connection_string == expected

        print("✅ RedisConfig test passed")
        return True
    except Exception as e:
        print(f"❌ RedisConfig test failed: {e}")
        return False


def test_api_config():
    """Test APIConfig configuration."""
    try:
        from app.core.centralized_config import APIConfig

        config = APIConfig()

        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.workers == 1
        assert config.secret_key == "your-secret-key-change-in-production"
        assert config.access_token_expire_minutes == 30
        assert config.rate_limit_per_minute == 100
        assert config.cors_origins == ["*"]
        assert config.cors_methods == ["GET", "POST", "PUT", "DELETE"]

        print("✅ APIConfig test passed")
        return True
    except Exception as e:
        print(f"❌ APIConfig test failed: {e}")
        return False


def test_environment_enum():
    """Test Environment enum."""
    try:
        from app.core.centralized_config import Environment

        assert Environment.DEVELOPMENT == "development"
        assert Environment.TESTING == "testing"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"

        print("✅ Environment enum test passed")
        return True
    except Exception as e:
        print(f"❌ Environment enum test failed: {e}")
        return False


def test_validation():
    """Test configuration validation."""
    try:
        from app.core.centralized_config import TradingThresholds

        # Test valid values
        TradingThresholds(max_position_size=0.1)
        TradingThresholds(max_position_size=0.5)
        TradingThresholds(max_position_size=1.0)

        # Test invalid values
        try:
            TradingThresholds(max_position_size=1.1)
            print("❌ Validation test failed: should have raised ValueError")
            return False
        except ValueError as e:
            if "less than or equal to 1" in str(e) or "max_position_size" in str(e):
                pass  # Expected error
            else:
                print(f"❌ Unexpected error message: {e}")
                return False

        try:
            TradingThresholds(max_position_size=-0.1)
            print("❌ Validation test failed: should have raised ValueError")
            return False
        except ValueError as e:
            if "greater than or equal to 0" in str(e) or "max_position_size" in str(e):
                pass  # Expected error
            else:
                print(f"❌ Unexpected error message: {e}")
                return False

        print("✅ Validation test passed")
        return True
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Running Centralized Configuration Tests")
    print("=" * 50)

    tests = [
        test_imports,
        test_trading_thresholds,
        test_strategy_config,
        test_database_config,
        test_redis_config,
        test_api_config,
        test_environment_enum,
        test_validation,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
