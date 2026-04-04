"""
T18.1: Metrics Database Configuration Tests

Tests for metrics database configuration models and integration with
centralized configuration system.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.services.metrics_database.models import (
    MetricPoint,
    MetricsCollectorConfig,
    MetricsQueryEngineConfig,
    MetricType,
    QuestDBConfig,
)
from app.shared.config.centralized_config import get_config


class TestMetricsModelsConfiguration:
    """Test configuration models."""

    def test_questdb_config_defaults(self):
        """Test QuestDB config with default values."""
        config = QuestDBConfig()

        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "qdb"
        assert config.user == "admin"
        assert config.pool_size == 10
        assert config.batch_size == 1000
        assert config.retention_days == 90
        assert config.max_retries == 3

    def test_questdb_config_custom_values(self):
        """Test QuestDB config with custom values."""
        config = QuestDBConfig(
            host="db.example.com",
            port=5433,
            database="metrics",
            user="metrics_user",
            pool_size=20,
            batch_size=5000,
            retention_days=180,
        )

        assert config.host == "db.example.com"
        assert config.port == 5433
        assert config.database == "metrics"
        assert config.user == "metrics_user"
        assert config.pool_size == 20
        assert config.batch_size == 5000
        assert config.retention_days == 180

    def test_questdb_connection_string(self):
        """Test QuestDB connection string generation."""
        config = QuestDBConfig(
            host="localhost",
            port=5432,
            database="qdb",
            user="admin",
            password="quest",
        )

        expected = "postgresql://admin:quest@localhost:5432/qdb"
        assert config.connection_string == expected

    def test_questdb_config_to_dict(self):
        """Test QuestDB config serialization (excludes password)."""
        config = QuestDBConfig(
            host="localhost",
            user="admin",
            pool_size=10,
        )

        config_dict = config.to_dict()
        assert "host" in config_dict
        assert "user" in config_dict
        assert "pool_size" in config_dict
        assert "password" not in config_dict  # Password not included for security

    def test_metrics_collector_config_defaults(self):
        """Test MetricsCollector config with defaults."""
        config = MetricsCollectorConfig()

        assert config.enabled is True
        assert config.collection_interval_seconds == 60
        assert config.batch_size == 1000
        assert config.flush_interval_seconds == 30
        assert config.max_pending_metrics == 10000

    def test_metrics_collector_config_custom(self):
        """Test MetricsCollector config with custom values."""
        config = MetricsCollectorConfig(
            enabled=False,
            collection_interval_seconds=30,
            batch_size=500,
            flush_interval_seconds=15,
            max_pending_metrics=5000,
        )

        assert config.enabled is False
        assert config.collection_interval_seconds == 30
        assert config.batch_size == 500
        assert config.flush_interval_seconds == 15
        assert config.max_pending_metrics == 5000

    def test_metrics_collector_config_to_dict(self):
        """Test MetricsCollector config serialization."""
        config = MetricsCollectorConfig(
            enabled=True,
            collection_interval_seconds=45,
        )

        config_dict = config.to_dict()
        assert config_dict["enabled"] is True
        assert config_dict["collection_interval_seconds"] == 45

    def test_metrics_query_engine_config_defaults(self):
        """Test MetricsQueryEngine config with defaults."""
        config = MetricsQueryEngineConfig()

        assert config.cache_enabled is True
        assert config.cache_ttl_seconds == 300
        assert config.max_query_points == 100000
        assert config.max_cache_entries == 1000
        assert config.downsampling_enabled is True

    def test_metrics_query_engine_config_custom(self):
        """Test MetricsQueryEngine config with custom values."""
        config = MetricsQueryEngineConfig(
            cache_enabled=False,
            cache_ttl_seconds=600,
            max_query_points=50000,
            max_cache_entries=500,
            downsampling_enabled=False,
        )

        assert config.cache_enabled is False
        assert config.cache_ttl_seconds == 600
        assert config.max_query_points == 50000
        assert config.max_cache_entries == 500
        assert config.downsampling_enabled is False

    def test_metrics_query_engine_config_to_dict(self):
        """Test MetricsQueryEngine config serialization."""
        config = MetricsQueryEngineConfig(
            cache_enabled=True,
            cache_ttl_seconds=180,
        )

        config_dict = config.to_dict()
        assert config_dict["cache_enabled"] is True
        assert config_dict["cache_ttl_seconds"] == 180


class TestCentralizedMetricsConfiguration:
    """Test metrics configuration integration with centralized config."""

    def test_metrics_db_enabled_in_config(self):
        """Test metrics_db_enabled in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'metrics_db_enabled')
        assert config.trading.metrics_db_enabled is True

    def test_metrics_collection_interval_in_config(self):
        """Test metrics_collection_interval in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'metrics_collection_interval')
        assert config.trading.metrics_collection_interval == 60

    def test_metrics_batch_size_in_config(self):
        """Test metrics_batch_size in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'metrics_batch_size')
        assert config.trading.metrics_batch_size == 1000

    def test_metrics_retention_days_in_config(self):
        """Test metrics_retention_days in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'metrics_retention_days')
        assert config.trading.metrics_retention_days == 90

    def test_questdb_host_in_config(self):
        """Test questdb_host in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'questdb_host')
        assert config.trading.questdb_host == "localhost"

    def test_questdb_port_in_config(self):
        """Test questdb_port in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'questdb_port')
        assert config.trading.questdb_port == 5432

    def test_questdb_database_in_config(self):
        """Test questdb_database in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'questdb_database')
        assert config.trading.questdb_database == "qdb"

    def test_questdb_user_in_config(self):
        """Test questdb_user in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'questdb_user')
        assert config.trading.questdb_user == "admin"

    def test_questdb_password_in_config(self):
        """Test questdb_password in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'questdb_password')
        assert config.trading.questdb_password == "quest"

    def test_questdb_pool_size_in_config(self):
        """Test questdb_pool_size in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'questdb_pool_size')
        assert config.trading.questdb_pool_size == 10

    def test_questdb_max_retries_in_config(self):
        """Test questdb_max_retries in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'questdb_max_retries')
        assert config.trading.questdb_max_retries == 3

    def test_metrics_cache_enabled_in_config(self):
        """Test metrics_cache_enabled in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'metrics_cache_enabled')
        assert config.trading.metrics_cache_enabled is True

    def test_metrics_cache_ttl_in_config(self):
        """Test metrics_cache_ttl_seconds in centralized config."""
        config = get_config()
        assert hasattr(config.trading, 'metrics_cache_ttl_seconds')
        assert config.trading.metrics_cache_ttl_seconds == 300


class TestConfigFromCentralizedThresholds:
    """Test creating config objects from centralized thresholds."""

    def test_questdb_config_from_thresholds(self):
        """Test creating QuestDBConfig from centralized thresholds."""
        trading = get_config().trading

        config = QuestDBConfig(
            host=trading.questdb_host,
            port=trading.questdb_port,
            database=trading.questdb_database,
            user=trading.questdb_user,
            password=trading.questdb_password,
            pool_size=trading.questdb_pool_size,
            max_retries=trading.questdb_max_retries,
            batch_size=trading.metrics_batch_size,
            retention_days=trading.metrics_retention_days,
        )

        assert config.host == trading.questdb_host
        assert config.port == trading.questdb_port
        assert config.database == trading.questdb_database
        assert config.batch_size == trading.metrics_batch_size
        assert config.retention_days == trading.metrics_retention_days

    def test_metrics_collector_config_from_thresholds(self):
        """Test creating MetricsCollectorConfig from centralized thresholds."""
        trading = get_config().trading

        config = MetricsCollectorConfig(
            enabled=trading.metrics_db_enabled,
            collection_interval_seconds=trading.metrics_collection_interval,
            batch_size=trading.metrics_batch_size,
        )

        assert config.enabled == trading.metrics_db_enabled
        assert config.collection_interval_seconds == trading.metrics_collection_interval
        assert config.batch_size == trading.metrics_batch_size

    def test_metrics_query_engine_config_from_thresholds(self):
        """Test creating MetricsQueryEngineConfig from centralized thresholds."""
        trading = get_config().trading

        config = MetricsQueryEngineConfig(
            cache_enabled=trading.metrics_cache_enabled,
            cache_ttl_seconds=trading.metrics_cache_ttl_seconds,
        )

        assert config.cache_enabled == trading.metrics_cache_enabled
        assert config.cache_ttl_seconds == trading.metrics_cache_ttl_seconds


class TestConfigurationValidation:
    """Test configuration validation."""

    def test_questdb_config_pool_size_positive(self):
        """Test QuestDB pool size validation."""
        config = QuestDBConfig(pool_size=5)
        assert config.pool_size == 5

    def test_questdb_config_retention_positive(self):
        """Test QuestDB retention days validation."""
        config = QuestDBConfig(retention_days=30)
        assert config.retention_days == 30

    def test_metrics_collector_interval_positive(self):
        """Test MetricsCollector interval validation."""
        config = MetricsCollectorConfig(collection_interval_seconds=120)
        assert config.collection_interval_seconds == 120

    def test_metrics_query_cache_ttl_positive(self):
        """Test MetricsQueryEngine cache TTL validation."""
        config = MetricsQueryEngineConfig(cache_ttl_seconds=600)
        assert config.cache_ttl_seconds == 600


class TestConfigurationSerialization:
    """Test configuration serialization."""

    def test_questdb_config_round_trip(self):
        """Test QuestDB config serialization round-trip."""
        original = QuestDBConfig(
            host="db.local",
            port=5433,
            pool_size=15,
        )

        dict_repr = original.to_dict()
        restored = QuestDBConfig(**dict_repr)

        assert restored.host == original.host
        assert restored.port == original.port
        assert restored.pool_size == original.pool_size

    def test_metrics_collector_config_round_trip(self):
        """Test MetricsCollector config serialization round-trip."""
        original = MetricsCollectorConfig(
            enabled=False,
            collection_interval_seconds=45,
        )

        dict_repr = original.to_dict()
        restored = MetricsCollectorConfig(**dict_repr)

        assert restored.enabled == original.enabled
        assert restored.collection_interval_seconds == original.collection_interval_seconds

    def test_metrics_query_config_round_trip(self):
        """Test MetricsQueryEngine config serialization round-trip."""
        original = MetricsQueryEngineConfig(
            cache_ttl_seconds=180,
            max_query_points=50000,
        )

        dict_repr = original.to_dict()
        restored = MetricsQueryEngineConfig(**dict_repr)

        assert restored.cache_ttl_seconds == original.cache_ttl_seconds
        assert restored.max_query_points == original.max_query_points


class TestMetricPointConfiguration:
    """Test metric point creation with configurations."""

    def test_metric_point_with_all_fields(self):
        """Test MetricPoint with all fields populated."""
        now = datetime.utcnow()
        point = MetricPoint(
            timestamp=now,
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("5.25"),
            symbol="EUR/USD",
            portfolio_id="port_001",
            tags={"strategy": "momentum", "regime": "bull"},
        )

        assert point.timestamp == now
        assert point.metric_type == MetricType.PORTFOLIO_RETURN
        assert point.value == Decimal("5.25")
        assert point.symbol == "EUR/USD"
        assert point.portfolio_id == "port_001"
        assert point.tags["strategy"] == "momentum"

    def test_metric_point_serialization(self):
        """Test MetricPoint serialization to dict."""
        now = datetime.utcnow()
        point = MetricPoint(
            timestamp=now,
            metric_type=MetricType.PORTFOLIO_VOLATILITY,
            value=Decimal("12.5"),
            tags={"window": "20d"},
        )

        point_dict = point.to_dict()
        assert point_dict["metric_type"] == "portfolio_volatility"
        assert point_dict["value"] == "12.5"
        assert point_dict["tags"]["window"] == "20d"

    def test_metric_point_minimal(self):
        """Test MetricPoint with minimal fields."""
        now = datetime.utcnow()
        point = MetricPoint(
            timestamp=now,
            metric_type=MetricType.CPU_USAGE,
            value=Decimal("45.3"),
        )

        assert point.symbol is None
        assert point.portfolio_id is None
        assert point.tags == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
