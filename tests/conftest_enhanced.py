"""
Enhanced Test Fixtures and Categories
Testing Reviewer Audit - Phase 1: Critical Fixes
"""

import asyncio
import tempfile
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import Mock

import pytest

from app.core.centralized_config import CentralizedConfig, get_config, set_config
from app.core.test_config import TestConfigManager

# Test Categories
pytestmark = [
    pytest.mark.unit,
    pytest.mark.integration,
    pytest.mark.api,
    pytest.mark.performance,
    pytest.mark.configuration,
    pytest.mark.strategy,
    pytest.mark.database,
    pytest.mark.error_handling,
]


@pytest.fixture(scope="session")
def test_config_manager() -> Generator[TestConfigManager, None, None]:
    """Session-scoped test configuration manager."""
    manager = TestConfigManager()
    manager.setup_test_environment()
    yield manager
    manager.cleanup_test_environment()


@pytest.fixture(scope="function")
def isolated_config() -> Generator[CentralizedConfig, None, None]:
    """Provide isolated configuration for each test."""
    # Store original config
    original_config = get_config()

    # Create fresh config for test
    test_config = CentralizedConfig()
    set_config(test_config)

    yield test_config

    # Restore original config
    set_config(original_config)


@pytest.fixture(scope="function")
def temp_log_dir() -> Generator[Path, None, None]:
    """Provide temporary directory for logging tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture(scope="function")
def mock_market_data() -> Dict[str, Any]:
    """Mock market data for testing."""
    return {
        "symbol": "AAPL",
        "price": Decimal("150.00"),
        "volume": 1000000,
        "timestamp": datetime.now(),
        "bid": Decimal("149.95"),
        "ask": Decimal("150.05"),
        "spread": Decimal("0.10"),
        "high": Decimal("151.00"),
        "low": Decimal("149.00"),
        "open": Decimal("149.50"),
    }


@pytest.fixture(scope="function")
def mock_portfolio() -> Dict[str, Any]:
    """Mock portfolio data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "name": "Test Portfolio",
        "total_equity": Decimal("100000.00"),
        "cash": Decimal("50000.00"),
        "positions": [],
        "daily_pnl": Decimal("0.00"),
        "total_pnl": Decimal("0.00"),
        "max_drawdown": Decimal("0.00"),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


@pytest.fixture(scope="function")
def mock_signal() -> Dict[str, Any]:
    """Mock trading signal for testing."""
    return {
        "id": str(uuid.uuid4()),
        "symbol": "AAPL",
        "signal_type": "BUY",
        "strength": 75.0,
        "confidence": 80.0,
        "price": Decimal("150.00"),
        "volume": Decimal("100.00"),
        "timestamp": datetime.now(),
        "strategy": "momentum",
        "liquidity_score": 85.0,
        "priority_score": 90.0,
        "source": "technical_analysis",
    }


@pytest.fixture(scope="function")
def mock_order() -> Dict[str, Any]:
    """Mock trading order for testing."""
    return {
        "id": str(uuid.uuid4()),
        "symbol": "AAPL",
        "side": "BUY",
        "order_type": "LIMIT",
        "quantity": Decimal("100.00"),
        "price": Decimal("150.00"),
        "status": "PENDING",
        "timestamp": datetime.now(),
        "strategy": "momentum",
        "portfolio_id": str(uuid.uuid4()),
    }


@pytest.fixture(scope="function")
def mock_trade() -> Dict[str, Any]:
    """Mock trade execution for testing."""
    return {
        "id": str(uuid.uuid4()),
        "order_id": str(uuid.uuid4()),
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": Decimal("100.00"),
        "price": Decimal("150.00"),
        "commission": Decimal("1.50"),
        "slippage": Decimal("0.05"),
        "timestamp": datetime.now(),
        "status": "FILLED",
    }


@pytest.fixture(scope="function")
def mock_strategy_config() -> Dict[str, Any]:
    """Mock strategy configuration for testing."""
    return {
        "name": "test_strategy",
        "enabled": True,
        "weight": 1.0,
        "parameters": {
            "rsi_threshold": 40,
            "momentum_threshold": 0.02,
            "volume_threshold": 1.5,
        },
        "max_position_size": 0.1,
        "stop_loss_pct": 0.05,
        "take_profit_pct": 0.10,
        "min_sharpe_ratio": 1.0,
        "max_drawdown": 0.15,
        "min_win_rate": 0.4,
    }


@pytest.fixture(scope="function")
def mock_database_config() -> Dict[str, Any]:
    """Mock database configuration for testing."""
    return {
        "host": "localhost",
        "port": 5433,
        "name": "algotrading_test",
        "user": "test_user",
        "password": "test_password",
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "ssl_mode": "prefer",
    }


@pytest.fixture(scope="function")
def mock_redis_config() -> Dict[str, Any]:
    """Mock Redis configuration for testing."""
    return {
        "host": "localhost",
        "port": 6380,
        "password": None,
        "db": 15,
        "max_connections": 10,
        "socket_timeout": 5,
    }


@pytest.fixture(scope="function")
def mock_api_config() -> Dict[str, Any]:
    """Mock API configuration for testing."""
    return {
        "host": "127.0.0.1",
        "port": 8001,
        "workers": 1,
        "secret_key": "test-secret-key-32-characters-long",
        "access_token_expire_minutes": 30,
        "rate_limit_per_minute": 100,
        "cors_origins": ["http://localhost:3000"],
        "cors_methods": ["GET", "POST", "PUT", "DELETE"],
    }


@pytest.fixture(scope="function")
def mock_logging_config() -> Dict[str, Any]:
    """Mock logging configuration for testing."""
    return {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "log_file": None,
        "max_file_size": 1048576,  # 1MB for tests
        "backup_count": 3,
        "elk_enabled": False,
        "elk_host": "localhost",
        "elk_port": 9200,
        "elk_index": "algotrading-test-logs",
    }


@pytest.fixture(scope="function")
def mock_monitoring_config() -> Dict[str, Any]:
    """Mock monitoring configuration for testing."""
    return {
        "prometheus_enabled": False,
        "prometheus_port": 9091,
        "grafana_enabled": False,
        "grafana_port": 3001,
        "health_check_interval": 10,
        "health_check_timeout": 5,
        "alerts_enabled": False,
        "slack_webhook_url": None,
        "discord_webhook_url": None,
    }


@pytest.fixture(scope="function")
def mock_trading_thresholds() -> Dict[str, Any]:
    """Mock trading thresholds for testing."""
    return {
        "min_signal_strength": 60.0,
        "min_signal_confidence": 70.0,
        "min_liquidity_score": 50.0,
        "rsi_oversold": 30.0,
        "rsi_overbought": 70.0,
        "max_position_size": 0.05,  # Smaller for tests
        "min_position_size": 0.01,
        "stop_loss_pct": 0.02,  # Tighter for tests
        "take_profit_pct": 0.08,  # Smaller for tests
        "daily_loss_limit": 0.02,
        "max_drawdown_limit": 0.10,
        "max_total_exposure": 0.5,
        "max_sector_exposure": 0.2,
        "max_correlation": 0.6,
        "circuit_breaker_daily_loss": 0.01,
        "circuit_breaker_drawdown": 0.05,
        "circuit_breaker_volatility": 0.03,
        "circuit_breaker_error_rate": 0.02,
        "max_latency_ms": 500,
        "max_execution_time_ms": 250,
    }


@pytest.fixture(scope="function")
def mock_centralized_logger():
    """Mock centralized logger for testing."""
    mock_logger = Mock()
    mock_logger.info = Mock()
    mock_logger.warning = Mock()
    mock_logger.error = Mock()
    mock_logger.debug = Mock()
    mock_logger.critical = Mock()

    # Mock context managers
    mock_logger.performance_timer = Mock()
    mock_logger.performance_timer.return_value.__enter__ = Mock(return_value=None)
    mock_logger.performance_timer.return_value.__exit__ = Mock(return_value=None)

    return mock_logger


@pytest.fixture(scope="function")
def mock_database_session():
    """Mock database session for testing."""
    mock_session = Mock()
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.rollback = Mock()
    mock_session.close = Mock()
    mock_session.query = Mock()
    mock_session.execute = Mock()

    return mock_session


@pytest.fixture(scope="function")
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_redis = Mock()
    mock_redis.get = Mock(return_value=None)
    mock_redis.set = Mock(return_value=True)
    mock_redis.delete = Mock(return_value=True)
    mock_redis.exists = Mock(return_value=False)
    mock_redis.expire = Mock(return_value=True)
    mock_redis.ping = Mock(return_value=True)

    return mock_redis


@pytest.fixture(scope="function")
def mock_http_client():
    """Mock HTTP client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json = Mock(return_value={})
    mock_response.text = "OK"

    mock_client.get = Mock(return_value=mock_response)
    mock_client.post = Mock(return_value=mock_response)
    mock_client.put = Mock(return_value=mock_response)
    mock_client.delete = Mock(return_value=mock_response)

    return mock_client


@pytest.fixture(scope="function")
def mock_fastapi_app():
    """Mock FastAPI app for testing."""
    mock_app = Mock()
    mock_app.add_exception_handler = Mock()
    mock_app.add_middleware = Mock()
    mock_app.include_router = Mock()
    mock_app.get = Mock()
    mock_app.post = Mock()
    mock_app.put = Mock()
    mock_app.delete = Mock()

    return mock_app


@pytest.fixture(scope="function")
def mock_strategy():
    """Mock trading strategy for testing."""
    mock_strategy = Mock()
    mock_strategy.name = "test_strategy"
    mock_strategy.enabled = True
    mock_strategy.weight = 1.0
    mock_strategy.generate_signals = Mock(return_value=[])
    mock_strategy.risk_check = Mock(return_value=True)
    mock_strategy.get_required_parameters = Mock(return_value=["param1", "param2"])

    return mock_strategy


@pytest.fixture(scope="function")
def mock_portfolio_service():
    """Mock portfolio service for testing."""
    mock_service = Mock()
    mock_service.get_portfolio = Mock(return_value=None)
    mock_service.create_portfolio = Mock(return_value=None)
    mock_service.update_portfolio = Mock(return_value=None)
    mock_service.delete_portfolio = Mock(return_value=None)
    mock_service.get_positions = Mock(return_value=[])
    mock_service.add_position = Mock(return_value=None)
    mock_service.remove_position = Mock(return_value=None)

    return mock_service


@pytest.fixture(scope="function")
def mock_signal_service():
    """Mock signal service for testing."""
    mock_service = Mock()
    mock_service.generate_signals = Mock(return_value=[])
    mock_service.score_signal = Mock(return_value=75.0)
    mock_service.filter_signals = Mock(return_value=[])
    mock_service.get_signal_history = Mock(return_value=[])

    return mock_service


@pytest.fixture(scope="function")
def mock_market_data_service():
    """Mock market data service for testing."""
    mock_service = Mock()
    mock_service.get_quote = Mock(return_value=None)
    mock_service.get_historical_data = Mock(return_value=[])
    mock_service.get_top_liquid_assets = Mock(return_value=[])
    mock_service.subscribe_to_updates = Mock(return_value=None)
    mock_service.unsubscribe_from_updates = Mock(return_value=None)

    return mock_service


@pytest.fixture(scope="function")
def mock_paper_trading_service():
    """Mock paper trading service for testing."""
    mock_service = Mock()
    mock_service.execute_order = Mock(return_value=None)
    mock_service.get_portfolio = Mock(return_value=None)
    mock_service.get_trade_history = Mock(return_value=[])
    mock_service.get_performance_metrics = Mock(return_value={})
    mock_service.reset_portfolio = Mock(return_value=None)

    return mock_service


@pytest.fixture(scope="function")
def mock_backtest_service():
    """Mock backtest service for testing."""
    mock_service = Mock()
    mock_service.run_backtest = Mock(return_value=None)
    mock_service.get_backtest_results = Mock(return_value=None)
    mock_service.get_backtest_history = Mock(return_value=[])
    mock_service.cancel_backtest = Mock(return_value=None)

    return mock_service


@pytest.fixture(scope="function")
def mock_cost_analysis_service():
    """Mock cost analysis service for testing."""
    mock_service = Mock()
    mock_service.analyze_trade_costs = Mock(return_value=None)
    mock_service.analyze_portfolio_costs = Mock(return_value=None)
    mock_service.get_cost_recommendations = Mock(return_value=[])
    mock_service.calculate_cost_impact_ratio = Mock(return_value=Decimal("0.15"))

    return mock_service


@pytest.fixture(scope="function")
def mock_optimization_service():
    """Mock optimization service for testing."""
    mock_service = Mock()
    mock_service.optimize_parameters = Mock(return_value=None)
    mock_service.run_walk_forward_analysis = Mock(return_value=None)
    mock_service.run_purged_k_fold = Mock(return_value=None)
    mock_service.get_optimization_results = Mock(return_value=None)

    return mock_service


@pytest.fixture(scope="function")
def mock_asset_identification_service():
    """Mock asset identification service for testing."""
    mock_service = Mock()
    mock_service.get_top_liquid_assets = Mock(return_value=[])
    mock_service.get_asset_universe = Mock(return_value=None)
    mock_service.filter_assets = Mock(return_value=[])
    mock_service.rank_assets = Mock(return_value=[])

    return mock_service


@pytest.fixture(scope="function")
def mock_momentum_analysis_service():
    """Mock momentum analysis service for testing."""
    mock_service = Mock()
    mock_service.analyze_momentum = Mock(return_value=None)
    mock_service.generate_momentum_signals = Mock(return_value=[])
    mock_service.get_top_momentum_assets = Mock(return_value=[])
    mock_service.calculate_technical_indicators = Mock(return_value=None)

    return mock_service


@pytest.fixture(scope="function")
def mock_portfolio_analytics_service():
    """Mock portfolio analytics service for testing."""
    mock_service = Mock()
    mock_service.calculate_performance_metrics = Mock(return_value=None)
    mock_service.calculate_risk_metrics = Mock(return_value=None)
    mock_service.generate_performance_report = Mock(return_value=None)
    mock_service.calculate_correlation_matrix = Mock(return_value=None)

    return mock_service


# Async fixtures
@pytest.fixture(scope="function")
async def async_mock_service():
    """Async mock service for testing."""
    mock_service = Mock()
    mock_service.async_method = Mock(return_value=None)

    # Make it async
    async def async_mock(*args, **kwargs):
        return None

    mock_service.async_method.side_effect = async_mock

    return mock_service


@pytest.fixture(scope="function")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# Performance testing fixtures
@pytest.fixture(scope="function")
def performance_timer():
    """Timer for performance testing."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


@pytest.fixture(scope="function")
def memory_profiler():
    """Memory profiler for testing."""
    import os

    import psutil

    class MemoryProfiler:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_memory = None
            self.end_memory = None

        def start(self):
            self.start_memory = self.process.memory_info().rss

        def stop(self):
            self.end_memory = self.process.memory_info().rss

        @property
        def memory_delta(self):
            if self.start_memory and self.end_memory:
                return self.end_memory - self.start_memory
            return None

        @property
        def current_memory(self):
            return self.process.memory_info().rss

    return MemoryProfiler()


# Test data generators
@pytest.fixture(scope="function")
def sample_market_data_generator():
    """Generate sample market data for testing."""

    def generate_data(symbol: str = "AAPL", count: int = 100):
        data = []
        base_price = Decimal("150.00")

        for i in range(count):
            price_change = Decimal(str(0.01 * (i % 10 - 5)))  # Oscillating price
            price = base_price + price_change

            data.append(
                {
                    "symbol": symbol,
                    "price": price,
                    "volume": 1000000 + (i * 1000),
                    "timestamp": datetime.now() - timedelta(minutes=count - i),
                    "bid": price - Decimal("0.05"),
                    "ask": price + Decimal("0.05"),
                    "spread": Decimal("0.10"),
                    "high": price + Decimal("0.50"),
                    "low": price - Decimal("0.50"),
                    "open": price,
                }
            )

        return data

    return generate_data


@pytest.fixture(scope="function")
def sample_signals_generator():
    """Generate sample signals for testing."""

    def generate_signals(count: int = 50):
        signals = []
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

        for i in range(count):
            symbol = symbols[i % len(symbols)]
            signal_types = ["BUY", "SELL", "HOLD"]
            signal_type = signal_types[i % len(signal_types)]

            signals.append(
                {
                    "id": str(uuid.uuid4()),
                    "symbol": symbol,
                    "signal_type": signal_type,
                    "strength": 60.0 + (i % 40),
                    "confidence": 70.0 + (i % 30),
                    "price": Decimal("150.00") + Decimal(str(i * 0.1)),
                    "volume": Decimal("100.00") + Decimal(str(i * 10)),
                    "timestamp": datetime.now() - timedelta(minutes=count - i),
                    "strategy": "test_strategy",
                    "liquidity_score": 80.0 + (i % 20),
                    "priority_score": 75.0 + (i % 25),
                    "source": "technical_analysis",
                }
            )

        return signals

    return generate_signals


# Test utilities
@pytest.fixture(scope="function")
def test_utils():
    """Test utilities for common operations."""

    class TestUtils:
        @staticmethod
        def assert_decimal_equal(actual: Decimal, expected: Decimal, precision: int = 2):
            """Assert two decimals are equal within precision."""
            actual_rounded = actual.quantize(Decimal(f"0.{'0' * precision}"))
            expected_rounded = expected.quantize(Decimal(f"0.{'0' * precision}"))
            assert actual_rounded == expected_rounded

        @staticmethod
        def assert_datetime_close(
            actual: datetime,
            expected: datetime,
            delta: timedelta = timedelta(seconds=1),
        ):
            """Assert two datetimes are close within delta."""
            assert abs(actual - expected) <= delta

        @staticmethod
        def create_mock_config(**overrides):
            """Create mock configuration with overrides."""
            config = {
                "environment": "testing",
                "debug": True,
                "max_position_size": 0.05,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.08,
                "daily_loss_limit": 0.02,
                "max_drawdown_limit": 0.10,
            }
            config.update(overrides)
            return config

    return TestUtils()
