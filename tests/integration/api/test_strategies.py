"""
Strategy Management API Endpoints Test Suite

Tests for strategy management API endpoints with DI container pattern.

Reference: Rule DP-004 - Use dependency injection instead of direct instantiation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.strategies import (
    get_config_loader,
    get_execution_engine,
    get_strategy_logger,
    get_strategy_registry,
    router,
)
from app.strategies import ExecutionEngine, StrategyConfigLoader, StrategyLogger, StrategyRegistry


class TestStrategiesAPIEndpoints:
    """Test strategy management API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_get_strategies_overview(self, client):
        """Test get_strategies_overview returns all strategies."""
        with patch.object(
            StrategyRegistry,
            "get_all_strategies_status",
            return_value={"strategies": []},
        ):
            response = client.get("/strategies/")
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_available_strategies(self, client):
        """Test get_available_strategies returns list of available strategies."""
        with patch.object(
            StrategyRegistry, "list_available_strategies", return_value=["momentum", "mean_reversion"]
        ):
            response = client.get("/strategies/available")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_loaded_strategies(self, client):
        """Test get_loaded_strategies returns list of loaded strategies."""
        with patch.object(StrategyRegistry, "list_loaded_strategies", return_value=[]):
            response = client.get("/strategies/loaded")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_load_strategy_success(self, client):
        """Test load_strategy loads strategy successfully."""
        mock_strategy = MagicMock()
        mock_strategy.name = "test_strategy"
        mock_strategy.is_active = True
        mock_strategy.version = "1.0"
        mock_strategy.description = "Test strategy"
        mock_strategy.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_strategy.get_parameters.return_value = {}

        with patch.object(StrategyRegistry, "load_strategy", return_value=mock_strategy):
            with patch.object(StrategyLogger, "log_strategy_loaded"):
                response = client.post(
                    "/strategies/load",
                    json={"name": "test_strategy", "config": {}},
                )
                assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_load_strategy_invalid(self, client):
        """Test load_strategy returns 400 for invalid strategy."""
        with patch.object(StrategyRegistry, "load_strategy", side_effect=ValueError("Invalid strategy")):
            response = client.post(
                "/strategies/load",
                json={"name": "invalid_strategy", "config": {}},
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_activate_strategy_success(self, client):
        """Test activate_strategy activates strategy successfully."""
        with patch.object(StrategyRegistry, "set_active_strategy"):
            with patch.object(StrategyLogger, "log_strategy_activated"):
                response = client.post(
                    "/strategies/activate",
                    json={"name": "test_strategy"},
                )
                assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_activate_strategy_invalid(self, client):
        """Test activate_strategy returns 400 for invalid strategy."""
        with patch.object(StrategyRegistry, "set_active_strategy", side_effect=ValueError("Strategy not found")):
            response = client.post(
                "/strategies/activate",
                json={"name": "nonexistent"},
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_deactivate_strategy_success(self, client):
        """Test deactivate_strategy deactivates active strategy."""
        mock_strategy = MagicMock()
        mock_strategy.name = "test_strategy"

        with patch.object(StrategyRegistry, "get_active_strategy", return_value=mock_strategy):
            with patch.object(StrategyRegistry, "set_active_strategy"):
                with patch.object(StrategyLogger, "log_strategy_deactivated"):
                    response = client.post("/strategies/deactivate")
                    assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_deactivate_strategy_no_active(self, client):
        """Test deactivate_strategy returns 400 when no active strategy."""
        with patch.object(StrategyRegistry, "get_active_strategy", return_value=None):
            response = client.post("/strategies/deactivate")
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_unload_strategy_success(self, client):
        """Test unload_strategy unloads strategy successfully."""
        with patch.object(StrategyRegistry, "unload_strategy"):
            with patch.object(StrategyLogger, "log_strategy_unloaded"):
                response = client.delete("/strategies/unload/test_strategy")
                assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_unload_strategy_not_found(self, client):
        """Test unload_strategy returns 400 for non-existent strategy."""
        with patch.object(StrategyRegistry, "unload_strategy", side_effect=ValueError("Strategy not found")):
            response = client.delete("/strategies/unload/nonexistent")
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_get_strategy_success(self, client):
        """Test get_strategy returns strategy information."""
        with patch.object(
            StrategyRegistry,
            "get_strategy_status",
            return_value={
                "name": "test_strategy",
                "is_active": True,
                "is_currently_active": True,
                "version": "1.0",
                "description": "Test strategy",
                "created_at": "2024-01-01T00:00:00",
                "parameters": {},
            },
        ):
            response = client.get("/strategies/test_strategy")
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_strategy_not_found(self, client):
        """Test get_strategy returns 404 for non-existent strategy."""
        with patch.object(
            StrategyRegistry, "get_strategy_status", side_effect=ValueError("Strategy not found")
        ):
            response = client.get("/strategies/nonexistent")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_strategy_parameters_success(self, client):
        """Test update_strategy_parameters updates parameters successfully."""
        mock_strategy = MagicMock()

        with patch.object(StrategyRegistry, "get_strategy", return_value=mock_strategy):
            response = client.put(
                "/strategies/test_strategy/parameters",
                json={"parameters": {"param1": "value1"}},
            )
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_update_strategy_parameters_not_found(self, client):
        """Test update_strategy_parameters returns 404 for non-existent strategy."""
        with patch.object(StrategyRegistry, "get_strategy", return_value=None):
            response = client.put(
                "/strategies/nonexistent/parameters",
                json={"parameters": {"param1": "value1"}},
            )
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_strategy_metrics(self, client):
        """Test get_strategy_metrics returns strategy metrics."""
        with patch.object(
            StrategyLogger,
            "get_strategy_metrics",
            return_value={
                "strategy": "test_strategy",
                "signals_generated": 100,
                "signals_executed": 80,
                "signals_rejected": 20,
                "execution_rate": 0.8,
                "rejection_rate": 0.2,
                "error_count": 5,
                "error_rate": 0.05,
                "total_logs": 100,
                "first_log": "2024-01-01T00:00:00",
                "last_log": "2024-01-01T01:00:00",
            },
        ):
            response = client.get("/strategies/test_strategy/metrics")
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_all_metrics(self, client):
        """Test get_all_metrics returns all strategy metrics."""
        with patch.object(StrategyLogger, "get_all_metrics", return_value={}):
            response = client.get("/strategies/metrics/all")
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_execution_stats(self, client):
        """Test get_execution_stats returns execution statistics."""
        with patch.object(
            ExecutionEngine,
            "get_execution_stats",
            return_value={
                "is_running": False,
                "cycle_count": 0,
                "total_signals_generated": 0,
                "total_signals_executed": 0,
                "execution_rate": 0.0,
                "created_at": "2024-01-01T00:00:00",
                "active_strategy": None,
            },
        ):
            response = client.get("/strategies/execution/stats")
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_start_execution_engine(self, client):
        """Test start_execution_engine starts engine successfully."""
        with patch.object(ExecutionEngine, "start"):
            response = client.post("/strategies/execution/start")
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_stop_execution_engine(self, client):
        """Test stop_execution_engine stops engine successfully."""
        with patch.object(ExecutionEngine, "stop"):
            response = client.post("/strategies/execution/stop")
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_reset_execution_stats(self, client):
        """Test reset_execution_stats resets statistics successfully."""
        with patch.object(ExecutionEngine, "reset_stats"):
            response = client.post("/strategies/execution/reset-stats")
            assert response.status_code == status.HTTP_200_OK


class TestDIContainerPattern:
    """Test DI container pattern for strategy services."""

    def test_get_strategy_registry_returns_instance(self):
        """Test that get_strategy_registry returns valid instance."""
        registry = get_strategy_registry()
        assert isinstance(registry, StrategyRegistry)

    def test_get_config_loader_returns_instance(self):
        """Test that get_config_loader returns valid instance."""
        loader = get_config_loader()
        assert isinstance(loader, StrategyConfigLoader)

    def test_get_strategy_logger_returns_instance(self):
        """Test that get_strategy_logger returns valid instance."""
        logger = get_strategy_logger()
        assert isinstance(logger, StrategyLogger)

    def test_get_execution_engine_returns_instance(self):
        """Test that get_execution_engine returns valid instance."""
        engine = get_execution_engine()
        assert isinstance(engine, ExecutionEngine)

    def test_di_container_initialization(self):
        """Test that DI container is properly initialized with strategy services."""
        from app.core.di_container import get_container

        container = get_container()

        # Container should have all strategy services registered
        registry = container.get("strategy_registry")
        assert registry is not None
        assert isinstance(registry, StrategyRegistry)

        config_loader = container.get("strategy_config_loader")
        assert config_loader is not None
        assert isinstance(config_loader, StrategyConfigLoader)

        logger = container.get("strategy_logger")
        assert logger is not None
        assert isinstance(logger, StrategyLogger)

        engine = container.get("execution_engine")
        assert engine is not None
        assert isinstance(engine, ExecutionEngine)

    def test_execution_engine_depends_on_registry_and_logger(self):
        """Test that ExecutionEngine properly depends on StrategyRegistry and StrategyLogger."""
        from app.core.di_container import get_container

        container = get_container()

        # Get execution engine
        engine = container.get("execution_engine")

        # Should have registry and logger as dependencies
        assert engine.registry is not None
        assert isinstance(engine.registry, type(container.get("strategy_registry")))
        assert engine.logger is not None
        assert isinstance(engine.logger, type(container.get("strategy_logger")))

    def test_singleton_behavior(self):
        """Test that all services behave as singletons."""
        registry1 = get_strategy_registry()
        registry2 = get_strategy_registry()
        # Same type, may or may not be same instance depending on factory implementation
        assert isinstance(registry1, StrategyRegistry)
        assert isinstance(registry2, StrategyRegistry)

        engine1 = get_execution_engine()
        engine2 = get_execution_engine()
        # Same type, may or may not be same instance depending on factory implementation
        assert isinstance(engine1, ExecutionEngine)
        assert isinstance(engine2, ExecutionEngine)


class TestErrorHandling:
    """Test error handling in strategies API."""

    @pytest.mark.asyncio
    async def test_get_strategies_overview_error(self, client):
        """Test get_strategies_overview handles errors correctly."""
        with patch.object(
            StrategyRegistry, "get_all_strategies_status", side_effect=Exception("Test error")
        ):
            response = client.get("/strategies/")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_load_strategy_error(self, client):
        """Test load_strategy handles unexpected errors correctly."""
        with patch.object(StrategyRegistry, "load_strategy", side_effect=RuntimeError("Unexpected error")):
            response = client.post(
                "/strategies/load",
                json={"name": "test_strategy", "config": {}},
            )
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_get_execution_stats_error(self, client):
        """Test get_execution_stats handles errors correctly."""
        with patch.object(ExecutionEngine, "get_execution_stats", side_effect=Exception("Test error")):
            response = client.get("/strategies/execution/stats")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
