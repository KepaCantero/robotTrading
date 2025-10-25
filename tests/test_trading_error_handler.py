"""
Tests para Trading Error Handler Unificado
TASK-14: Unificación de Error Handling

Tests comprehensivos para el sistema unificado de manejo de errores del trading.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from app.services.trading_error_handler import (
    TradingErrorHandler,
    ErrorAction,
    ErrorContext,
    trading_error_handler,
    handle_trading_error,
    execute_with_retry,
    get_error_statistics,
    reset_circuit_breaker
)
from app.exceptions.trading_exceptions import (
    AlgoTradingError,
    ErrorSeverity,
    ErrorCategory,
    TradingError,
    SignalError,
    PortfolioError,
    RiskManagementError,
    MarketDataError,
    BrokerError,
    ValidationError,
    BusinessLogicError,
    ExternalAPIError,
    DatabaseError,
    NetworkError,
    ConfigurationError,
    SecurityError,
    PerformanceError,
    SystemError
)


class TestTradingErrorHandler:
    """Tests para TradingErrorHandler."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.handler = TradingErrorHandler()
    
    @pytest.mark.asyncio
    async def test_handle_error_basic(self):
        """Test manejo básico de errores."""
        
        # Crear un error de trading
        error = TradingError(
            message="Order placement failed",
            symbol="AAPL",
            operation="place_order"
        )
        
        # Manejar el error
        result = await self.handler.handle_error(
            error=error,
            context=ErrorContext.ORDER_PLACEMENT,
            operation_id="test_order_123",
            metadata={"symbol": "AAPL", "quantity": 100}
        )
        
        # Verificar resultado
        assert result["operation_id"] == "test_order_123"
        assert result["context"] == "order_placement"
        assert result["error"]["message"] == "Order placement failed"
        assert "actions_taken" in result
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_handle_error_with_circuit_breaker(self):
        """Test activación de circuit breaker."""
        
        # Simular múltiples errores para activar circuit breaker
        for i in range(6):  # Más que el threshold de 5
            error = SystemError(
                message=f"System error {i}",
                component="order_placement"
            )
            
            await self.handler.handle_error(
                error=error,
                context=ErrorContext.ORDER_PLACEMENT,
                operation_id=f"test_order_{i}"
            )
        
        # Verificar que circuit breaker está activado
        assert self.handler._is_circuit_breaker_open(ErrorContext.ORDER_PLACEMENT)
    
    @pytest.mark.asyncio
    async def test_handle_error_with_kill_switch(self):
        """Test activación de kill switch."""
        
        # Crear error crítico en live trading
        error = RiskManagementError(
            message="Risk limit exceeded",
            risk_type="position_size",
            limit=1000,
            current_value=1500
        )
        
        result = await self.handler.handle_error(
            error=error,
            context=ErrorContext.LIVE_TRADING,
            operation_id="test_live_123"
        )
        
        # Verificar que kill switch se activó
        assert "kill_switch" in result["actions_taken"]
        assert result["actions_taken"]["kill_switch"]["activated"] is True
    
    @pytest.mark.asyncio
    async def test_handle_with_retry_success(self):
        """Test retry exitoso."""
        
        call_count = 0
        
        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Network timeout")
            return "success"
        
        # Ejecutar con retry
        result = await self.handler.handle_with_retry(
            operation=mock_operation,
            context=ErrorContext.MARKET_DATA_FETCH,
            operation_id="test_retry_123"
        )
        
        # Verificar resultado
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_handle_with_retry_failure(self):
        """Test retry con fallo final."""
        
        async def mock_operation():
            raise NetworkError("Persistent network error")
        
        # Ejecutar con retry (debería fallar después de todos los reintentos)
        with pytest.raises(NetworkError):
            await self.handler.handle_with_retry(
                operation=mock_operation,
                context=ErrorContext.MARKET_DATA_FETCH,
                operation_id="test_retry_fail_123"
            )
    
    @pytest.mark.asyncio
    async def test_convert_to_algotrading_error(self):
        """Test conversión de errores genéricos."""
        
        # Test ValueError
        error = ValueError("Invalid value")
        converted = self.handler._convert_to_algotrading_error(
            error, ErrorContext.SIGNAL_GENERATION, {}
        )
        assert isinstance(converted, ValidationError)
        
        # Test ConnectionError
        error = ConnectionError("Connection failed")
        converted = self.handler._convert_to_algotrading_error(
            error, ErrorContext.MARKET_DATA_FETCH, {}
        )
        assert isinstance(converted, NetworkError)
        
        # Test TimeoutError
        error = TimeoutError("Operation timeout")
        converted = self.handler._convert_to_algotrading_error(
            error, ErrorContext.ORDER_PLACEMENT, {}
        )
        assert isinstance(converted, PerformanceError)
    
    def test_error_rules_initialization(self):
        """Test inicialización de reglas de error."""
        
        rules = self.handler.error_rules
        
        # Verificar que todas las reglas están definidas
        expected_contexts = [
            "signal_generation", "order_placement", "order_execution",
            "portfolio_update", "risk_check", "market_data_fetch",
            "backtesting", "paper_trading", "live_trading"
        ]
        
        for context in expected_contexts:
            assert context in rules
            assert "max_retries" in rules[context]
            assert "retry_delay" in rules[context]
            assert "circuit_breaker_threshold" in rules[context]
            assert "actions" in rules[context]
    
    def test_get_error_statistics(self):
        """Test obtención de estadísticas de error."""
        
        # Simular algunos errores
        self.handler.error_counts["test_context_system"] = 5
        self.handler.circuit_breakers["test_context_circuit_breaker"] = True
        self.handler.last_error_times["test_context_system"] = datetime.now()
        self.handler.retry_counts["test_operation"] = 3
        
        stats = self.handler.get_error_statistics()
        
        assert "error_counts" in stats
        assert "circuit_breakers" in stats
        assert "last_error_times" in stats
        assert "retry_counts" in stats
        assert "timestamp" in stats
        
        assert stats["error_counts"]["test_context_system"] == 5
        assert stats["circuit_breakers"]["test_context_circuit_breaker"] is True
        assert stats["retry_counts"]["test_operation"] == 3
    
    def test_reset_circuit_breaker(self):
        """Test reset de circuit breaker."""
        
        # Activar circuit breaker
        self.handler.circuit_breakers["order_placement_circuit_breaker"] = True
        self.handler.error_counts["order_placement_system"] = 5
        
        # Reset circuit breaker
        self.handler.reset_circuit_breaker(ErrorContext.ORDER_PLACEMENT)
        
        # Verificar que está cerrado
        assert not self.handler._is_circuit_breaker_open(ErrorContext.ORDER_PLACEMENT)
        assert self.handler.error_counts["order_placement_system"] == 0


class TestTradingErrorHandlerIntegration:
    """Tests de integración para TradingErrorHandler."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_error_handling(self):
        """Test manejo de errores end-to-end."""
        
        # Simular un flujo completo de trading con errores
        results = []
        
        # 1. Error en generación de señal
        signal_error = SignalError(
            message="Invalid signal parameters",
            signal_type="momentum",
            strategy="momentum_strategy"
        )
        
        result1 = await handle_trading_error(
            error=signal_error,
            context=ErrorContext.SIGNAL_GENERATION,
            operation_id="signal_123"
        )
        results.append(result1)
        
        # 2. Error en colocación de orden
        order_error = BrokerError(
            message="Order rejected by broker",
            broker="test_broker",
            operation="place_order",
            order_id="order_456"
        )
        
        result2 = await handle_trading_error(
            error=order_error,
            context=ErrorContext.ORDER_PLACEMENT,
            operation_id="order_456"
        )
        results.append(result2)
        
        # 3. Error en actualización de portfolio
        portfolio_error = PortfolioError(
            message="Portfolio update failed",
            operation="update_position",
            portfolio_id="portfolio_789"
        )
        
        result3 = await handle_trading_error(
            error=portfolio_error,
            context=ErrorContext.PORTFOLIO_UPDATE,
            operation_id="portfolio_789"
        )
        results.append(result3)
        
        # Verificar que todos los errores fueron manejados
        assert len(results) == 3
        for result in results:
            assert "operation_id" in result
            assert "context" in result
            assert "error" in result
            assert "actions_taken" in result
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_integration(self):
        """Test integración de execute_with_retry."""
        
        # Simular operación que falla las primeras veces
        call_count = 0
        
        async def mock_market_data_fetch():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MarketDataError("Market data unavailable")
            return {"price": 100.0, "volume": 1000}
        
        # Ejecutar con retry
        result = await execute_with_retry(
            operation=mock_market_data_fetch,
            context=ErrorContext.MARKET_DATA_FETCH,
            operation_id="market_data_123"
        )
        
        # Verificar resultado
        assert result["price"] == 100.0
        assert result["volume"] == 1000
        assert call_count == 3
    
    def test_get_error_statistics_integration(self):
        """Test integración de get_error_statistics."""
        
        stats = get_error_statistics()
        
        assert isinstance(stats, dict)
        assert "error_counts" in stats
        assert "circuit_breakers" in stats
        assert "last_error_times" in stats
        assert "retry_counts" in stats
        assert "timestamp" in stats
    
    def test_reset_circuit_breaker_integration(self):
        """Test integración de reset_circuit_breaker."""
        
        # Activar circuit breaker primero
        trading_error_handler.circuit_breakers["signal_generation_circuit_breaker"] = True
        
        # Reset circuit breaker
        reset_circuit_breaker(ErrorContext.SIGNAL_GENERATION)
        
        # Verificar que está cerrado
        assert not trading_error_handler._is_circuit_breaker_open(ErrorContext.SIGNAL_GENERATION)


class TestTradingErrorHandlerAPI:
    """Tests para la API del Trading Error Handler."""
    
    @pytest.fixture
    def client(self):
        """Cliente de prueba para la API."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    def test_handle_error_endpoint(self, client):
        """Test endpoint de manejo de errores."""
        
        request_data = {
            "error_message": "Test error message",
            "error_type": "TradingError",
            "context": "order_placement",
            "operation_id": "test_123",
            "metadata": {"symbol": "AAPL", "quantity": 100}
        }
        
        response = client.post("/trading-error-handler/handle-error", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "operation_id" in data
        assert "context" in data
        assert "error" in data
        assert "actions_taken" in data
    
    def test_get_error_statistics_endpoint(self, client):
        """Test endpoint de estadísticas de error."""
        
        response = client.get("/trading-error-handler/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert "error_counts" in data
        assert "circuit_breakers" in data
        assert "last_error_times" in data
        assert "retry_counts" in data
    
    def test_get_circuit_breaker_status_endpoint(self, client):
        """Test endpoint de estado de circuit breakers."""
        
        response = client.get("/trading-error-handler/circuit-breakers")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_reset_circuit_breaker_endpoint(self, client):
        """Test endpoint de reset de circuit breaker."""
        
        request_data = {
            "context": "signal_generation"
        }
        
        response = client.post("/trading-error-handler/circuit-breakers/reset", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "context" in data
    
    def test_get_error_contexts_endpoint(self, client):
        """Test endpoint de contextos de error."""
        
        response = client.get("/trading-error-handler/contexts")
        
        assert response.status_code == 200
        data = response.json()
        assert "contexts" in data
        assert "count" in data
        assert data["count"] > 0
    
    def test_get_error_actions_endpoint(self, client):
        """Test endpoint de acciones de error."""
        
        response = client.get("/trading-error-handler/actions")
        
        assert response.status_code == 200
        data = response.json()
        assert "actions" in data
        assert "count" in data
        assert data["count"] > 0
    
    def test_get_error_rules_endpoint(self, client):
        """Test endpoint de reglas de error."""
        
        response = client.get("/trading-error-handler/rules/signal_generation")
        
        assert response.status_code == 200
        data = response.json()
        assert "context" in data
        assert "rules" in data
    
    def test_health_check_endpoint(self, client):
        """Test endpoint de health check."""
        
        response = client.get("/trading-error-handler/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data
        assert "timestamp" in data


class TestTradingErrorHandlerEdgeCases:
    """Tests para casos edge del Trading Error Handler."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.handler = TradingErrorHandler()
    
    @pytest.mark.asyncio
    async def test_handle_error_with_none_metadata(self):
        """Test manejo de error con metadata None."""
        
        error = TradingError("Test error")
        
        result = await self.handler.handle_error(
            error=error,
            context=ErrorContext.SIGNAL_GENERATION,
            operation_id="test_none_metadata",
            metadata=None
        )
        
        assert result["operation_id"] == "test_none_metadata"
        assert result["context"] == "signal_generation"
    
    @pytest.mark.asyncio
    async def test_handle_error_with_empty_metadata(self):
        """Test manejo de error con metadata vacía."""
        
        error = TradingError("Test error")
        
        result = await self.handler.handle_error(
            error=error,
            context=ErrorContext.SIGNAL_GENERATION,
            operation_id="test_empty_metadata",
            metadata={}
        )
        
        assert result["operation_id"] == "test_empty_metadata"
        assert result["context"] == "signal_generation"
    
    @pytest.mark.asyncio
    async def test_handle_error_with_none_operation_id(self):
        """Test manejo de error con operation_id None."""
        
        error = TradingError("Test error")
        
        result = await self.handler.handle_error(
            error=error,
            context=ErrorContext.SIGNAL_GENERATION,
            operation_id=None
        )
        
        # Debería generar un operation_id automáticamente
        assert "operation_id" in result
        assert result["context"] == "signal_generation"
    
    @pytest.mark.asyncio
    async def test_handle_error_with_unknown_context(self):
        """Test manejo de error con contexto desconocido."""
        
        # Usar un contexto existente pero con comportamiento inesperado
        error = TradingError("Test error")
        
        result = await self.handler.handle_error(
            error=error,
            context=ErrorContext.API_CALL,  # Usar contexto existente
            operation_id="test_unknown_context"
        )
        
        # Debería manejar el error sin fallar
        assert result["operation_id"] == "test_unknown_context"
    
    @pytest.mark.asyncio
    async def test_handle_error_with_custom_error(self):
        """Test manejo de error personalizado."""
        
        class CustomError(Exception):
            def __init__(self, message: str):
                self.message = message
                super().__init__(message)
        
        error = CustomError("Custom error message")
        
        result = await self.handler.handle_error(
            error=error,
            context=ErrorContext.SIGNAL_GENERATION,
            operation_id="test_custom_error"
        )
        
        # Debería convertir el error personalizado a AlgoTradingError
        assert result["operation_id"] == "test_custom_error"
        assert result["error"]["message"] == "Custom error message"
    
    def test_get_error_statistics_empty_state(self):
        """Test estadísticas de error en estado vacío."""
        
        # Crear handler nuevo sin errores
        handler = TradingErrorHandler()
        
        stats = handler.get_error_statistics()
        
        assert stats["error_counts"] == {}
        assert stats["circuit_breakers"] == {}
        assert stats["last_error_times"] == {}
        assert stats["retry_counts"] == {}
        assert "timestamp" in stats
    
    def test_reset_circuit_breaker_not_open(self):
        """Test reset de circuit breaker que no está abierto."""
        
        # Reset circuit breaker que no está abierto
        self.handler.reset_circuit_breaker(ErrorContext.SIGNAL_GENERATION)
        
        # No debería fallar
        assert not self.handler._is_circuit_breaker_open(ErrorContext.SIGNAL_GENERATION)


if __name__ == "__main__":
    # Ejecutar tests
    pytest.main([__file__, "-v"])
