"""
Tests para TASK-15: Refactorización de Servicios

Tests para los nuevos motores especializados y gestores centralizados.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from app.services.signal_evaluation_engine import SignalEvaluationEngine
from app.services.position_sizing_engine import PositionSizingEngine
from app.services.signal_execution_engine import SignalExecutionEngine
from app.services.circuit_breaker_manager import CircuitBreakerManager, CircuitBreakerType
from app.services.portfolio_risk_manager import PortfolioRiskManager, RiskLevel, RiskViolation

from app.models.signal import Signal, SignalType, MarketData
from app.models.portfolio import Portfolio, Position
from app.models.order import Order, OrderType, OrderSide, OrderStatus


class TestSignalEvaluationEngine:
    """Tests para SignalEvaluationEngine."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.engine = SignalEvaluationEngine()
    
    def test_engine_initialization(self):
        """Test inicialización del motor."""
        assert self.engine.min_signal_strength == 60.0
        assert self.engine.min_signal_confidence == 70.0
        assert self.engine.min_liquidity_score == 50.0
        assert self.engine.evaluations_count == 0
    
    def test_evaluate_signal_quality_acceptable(self):
        """Test evaluación de señal aceptable."""
        market_data = MarketData(
            symbol="AAPL",
            price=Decimal("150.00"),
            volume=1000000,
            timestamp=datetime.utcnow()
        )
        
        metadata = {
            "volatility": 0.25,
            "volume_ratio": 1.5,
            "data_quality": 0.9,
            "trend_consistency": 0.8,
            "spread_pct": 0.005,
            "avg_volume": 2000000
        }
        
        result = self.engine.evaluate_signal_quality(
            "AAPL", SignalType.BUY, market_data, metadata
        )
        
        assert result["symbol"] == "AAPL"
        assert result["signal_type"] == SignalType.BUY
        assert result["is_acceptable"] is True
        assert result["strength_score"] > 0
        assert result["confidence_score"] > 0
        assert result["liquidity_score"] > 0
        assert self.engine.evaluations_count == 1
        assert self.engine.accepted_signals == 1
    
    def test_evaluate_signal_quality_rejected(self):
        """Test evaluación de señal rechazada."""
        market_data = MarketData(
            symbol="AAPL",
            price=Decimal("150.00"),
            volume=1000000,
            timestamp=datetime.utcnow()
        )
        
        metadata = {
            "volatility": 0.1,  # Muy baja
            "volume_ratio": 0.5,  # Muy bajo
            "data_quality": 0.3,  # Muy baja
            "trend_consistency": 0.2,  # Muy baja
            "spread_pct": 0.05,  # Muy alto
            "avg_volume": 100000  # Muy bajo
        }
        
        result = self.engine.evaluate_signal_quality(
            "AAPL", SignalType.BUY, market_data, metadata
        )
        
        assert result["is_acceptable"] is False
        assert self.engine.rejected_signals == 1
    
    def test_update_thresholds(self):
        """Test actualización de thresholds."""
        self.engine.update_thresholds(
            min_strength=80.0,
            min_confidence=85.0,
            min_liquidity=60.0
        )
        
        assert self.engine.min_signal_strength == 80.0
        assert self.engine.min_signal_confidence == 85.0
        assert self.engine.min_liquidity_score == 60.0
    
    def test_get_evaluation_statistics(self):
        """Test obtención de estadísticas."""
        stats = self.engine.get_evaluation_statistics()
        
        assert "total_evaluations" in stats
        assert "accepted_signals" in stats
        assert "rejected_signals" in stats
        assert "acceptance_rate" in stats


class TestPositionSizingEngine:
    """Tests para PositionSizingEngine."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.engine = PositionSizingEngine()
        self.portfolio = Portfolio(
            portfolio_id="test_portfolio",
            user_id="test_user",
            cash=Decimal("100000"),
            total_value=Decimal("100000"),
            positions=[]
        )
    
    def test_engine_initialization(self):
        """Test inicialización del motor."""
        assert self.engine.max_position_size == 0.1
        assert self.engine.min_position_size == 0.01
        assert self.engine.max_total_exposure == 0.8
        assert self.engine.sizing_calculations == 0
    
    def test_calculate_position_size(self):
        """Test cálculo de tamaño de posición."""
        signal = Signal(
            signal_id="test_signal",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength="STRONG",
            confidence=80.0,
            price=Decimal("150.00"),
            volume=1000000,
            source="TECHNICAL_ANALYSIS",
            metadata={
                "volatility": 0.2,
                "sector": "technology",
                "market_cap": 2000000000000,
                "liquidity_score": 80.0,
                "correlation": 0.3
            }
        )
        
        available_capital = Decimal("100000")
        
        position_size, details = self.engine.calculate_position_size(
            signal, self.portfolio, available_capital, signal.metadata
        )
        
        assert position_size > 0
        assert position_size <= available_capital * self.engine.max_position_size
        assert details["symbol"] == "AAPL"
        assert details["final_size"] == position_size
        assert self.engine.sizing_calculations == 1
    
    def test_apply_risk_limits(self):
        """Test aplicación de límites de riesgo."""
        signal = Signal(
            signal_id="test_signal",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength="STRONG",
            confidence=80.0,
            price=Decimal("150.00"),
            volume=1000000,
            source="TECHNICAL_ANALYSIS",
            metadata={}
        )
        
        # Test con tamaño muy grande
        large_size = Decimal("50000")  # 50% del capital
        available_capital = Decimal("100000")
        
        position_size, details = self.engine.calculate_position_size(
            signal, self.portfolio, available_capital, signal.metadata
        )
        
        # Debe estar limitado por max_position_size
        max_allowed = available_capital * self.engine.max_position_size
        assert position_size <= max_allowed
    
    def test_update_limits(self):
        """Test actualización de límites."""
        self.engine.update_limits(
            max_position_size=0.2,
            min_position_size=0.02,
            max_total_exposure=0.9,
            max_sector_exposure=0.4
        )
        
        assert self.engine.max_position_size == 0.2
        assert self.engine.min_position_size == 0.02
        assert self.engine.max_total_exposure == 0.9
        assert self.engine.max_sector_exposure == 0.4


class TestSignalExecutionEngine:
    """Tests para SignalExecutionEngine."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.engine = SignalExecutionEngine()
        self.portfolio = Portfolio(
            portfolio_id="test_portfolio",
            user_id="test_user",
            cash=Decimal("100000"),
            total_value=Decimal("100000"),
            positions=[]
        )
    
    def test_engine_initialization(self):
        """Test inicialización del motor."""
        assert self.engine.max_execution_time_ms == 500
        assert self.engine.max_latency_ms == 1000
        assert self.engine.executions_attempted == 0
        assert self.engine.executions_successful == 0
    
    @pytest.mark.asyncio
    async def test_execute_signal_success(self):
        """Test ejecución exitosa de señal."""
        signal = Signal(
            signal_id="test_signal",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength="STRONG",
            confidence=80.0,
            price=Decimal("150.00"),
            volume=1000000,
            source="TECHNICAL_ANALYSIS",
            metadata={}
        )
        
        position_size = Decimal("1000")
        
        # Mock execution callback
        async def mock_callback(order, portfolio):
            return {
                "success": True,
                "order_status": "filled",
                "executed_price": order.price,
                "executed_quantity": order.quantity
            }
        
        success, details = await self.engine.execute_signal(
            signal, position_size, self.portfolio, mock_callback
        )
        
        assert success is True
        assert details["success"] is True
        assert details["symbol"] == "AAPL"
        assert self.engine.executions_successful == 1
        assert self.engine.executions_attempted == 1
    
    @pytest.mark.asyncio
    async def test_execute_signal_failure(self):
        """Test ejecución fallida de señal."""
        signal = Signal(
            signal_id="test_signal",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength="STRONG",
            confidence=80.0,
            price=Decimal("150.00"),
            volume=1000000,
            source="TECHNICAL_ANALYSIS",
            metadata={}
        )
        
        position_size = Decimal("1000")
        
        # Mock execution callback que falla
        async def mock_callback(order, portfolio):
            return {
                "success": False,
                "order_status": "failed",
                "executed_price": order.price,
                "executed_quantity": order.quantity
            }
        
        success, details = await self.engine.execute_signal(
            signal, position_size, self.portfolio, mock_callback
        )
        
        assert success is False
        assert details["success"] is False
        assert self.engine.executions_failed == 1
        assert self.engine.executions_attempted == 1
    
    def test_get_execution_statistics(self):
        """Test obtención de estadísticas."""
        stats = self.engine.get_execution_statistics()
        
        assert "total_executions" in stats
        assert "successful_executions" in stats
        assert "failed_executions" in stats
        assert "success_rate" in stats


class TestCircuitBreakerManager:
    """Tests para CircuitBreakerManager."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.manager = CircuitBreakerManager()
    
    def test_manager_initialization(self):
        """Test inicialización del gestor."""
        assert len(self.manager.circuit_breakers) > 0
        assert CircuitBreakerType.API_ERRORS.value in self.manager.circuit_breakers
        assert CircuitBreakerType.SLIPPAGE.value in self.manager.circuit_breakers
        assert CircuitBreakerType.PERFORMANCE.value in self.manager.circuit_breakers
    
    def test_record_error_and_trip(self):
        """Test registro de error y activación."""
        breaker_name = CircuitBreakerType.API_ERRORS.value
        
        # Registrar errores hasta activar
        for i in range(6):  # Más que el límite de 5
            should_block = self.manager.record_error(breaker_name, f"Error {i}")
            
            if i < 4:  # Antes del límite
                assert should_block is False
            else:  # Después del límite
                assert should_block is True
        
        # Verificar que está activo
        assert breaker_name in self.manager.get_active_breakers()
        assert self.manager.is_breaker_open(breaker_name)
    
    def test_record_success_and_close(self):
        """Test registro de éxito y cierre."""
        breaker_name = CircuitBreakerType.API_ERRORS.value
        
        # Activar circuit breaker
        for i in range(6):
            self.manager.record_error(breaker_name, f"Error {i}")
        
        assert self.manager.is_breaker_open(breaker_name)
        
        # Registrar suficientes éxitos para cerrar
        for i in range(3):
            self.manager.record_success(breaker_name)
        
        # Debería estar cerrado ahora
        assert not self.manager.is_breaker_open(breaker_name)
        assert breaker_name not in self.manager.get_active_breakers()
    
    def test_add_custom_circuit_breaker(self):
        """Test agregar circuit breaker personalizado."""
        custom_name = "custom_breaker"
        
        self.manager.add_circuit_breaker(
            custom_name, 
            max_errors=3, 
            cooldown_seconds=300,
            description="Custom breaker for testing"
        )
        
        assert custom_name in self.manager.circuit_breakers
        assert not self.manager.is_breaker_open(custom_name)
    
    def test_get_breaker_status(self):
        """Test obtención de estado de circuit breaker."""
        breaker_name = CircuitBreakerType.API_ERRORS.value
        
        status = self.manager.get_breaker_status(breaker_name)
        
        assert status is not None
        assert "name" in status
        assert "state" in status
        assert "error_count" in status
        assert "success_count" in status


class TestPortfolioRiskManager:
    """Tests para PortfolioRiskManager."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.manager = PortfolioRiskManager()
        self.portfolio = Portfolio(
            portfolio_id="test_portfolio",
            user_id="test_user",
            cash=Decimal("100000"),
            total_value=Decimal("100000"),
            positions=[]
        )
    
    def test_manager_initialization(self):
        """Test inicialización del gestor."""
        assert self.manager.max_position_size == 0.1
        assert self.manager.max_total_exposure == 0.8
        assert self.manager.max_sector_exposure == 0.3
        assert self.manager.current_risk_level == RiskLevel.LOW
    
    def test_assess_portfolio_risk_low(self):
        """Test evaluación de riesgo bajo."""
        assessment = self.manager.assess_portfolio_risk(self.portfolio)
        
        assert assessment["risk_level"] == RiskLevel.LOW
        assert len(assessment["violations"]) == 0
        assert len(assessment["recommendations"]) == 0
        assert self.manager.current_risk_level == RiskLevel.LOW
    
    def test_assess_portfolio_risk_with_violations(self):
        """Test evaluación de riesgo con violaciones."""
        # Crear posición que exceda límites
        large_position = Position(
            symbol="AAPL",
            quantity=Decimal("1000"),
            market_value=Decimal("90000"),  # 90% del capital
            cost_basis=Decimal("90.00"),
            unrealized_pnl=Decimal("0")
        )
        
        assessment = self.manager.assess_portfolio_risk(self.portfolio, large_position)
        
        # Debería detectar violación de exposición total
        violations = assessment["violations"]
        total_exposure_violations = [
            v for v in violations 
            if v["type"] == RiskViolation.TOTAL_EXPOSURE
        ]
        
        assert len(total_exposure_violations) > 0
        assert assessment["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    def test_get_risk_statistics(self):
        """Test obtención de estadísticas de riesgo."""
        stats = self.manager.get_risk_statistics()
        
        assert "risk_checks_performed" in stats
        assert "risk_violations_detected" in stats
        assert "current_risk_level" in stats
        assert "max_position_size" in stats
        assert "max_total_exposure" in stats
    
    def test_recent_violations(self):
        """Test obtención de violaciones recientes."""
        # Crear violación
        large_position = Position(
            symbol="AAPL",
            quantity=Decimal("1000"),
            market_value=Decimal("90000"),
            cost_basis=Decimal("90.00"),
            unrealized_pnl=Decimal("0")
        )
        
        self.manager.assess_portfolio_risk(self.portfolio, large_position)
        
        recent_violations = self.manager.get_recent_violations()
        assert len(recent_violations) > 0
        assert "violations" in recent_violations[0]
        assert "risk_level" in recent_violations[0]


class TestRefactoredServicesIntegration:
    """Tests de integración para servicios refactorizados."""
    
    @pytest.mark.asyncio
    async def test_signal_scorer_service_integration(self):
        """Test integración del SignalScorerService refactorizado."""
        from app.services.signal_scorer import SignalScorerService
        from app.services.portfolio_service import PortfolioService
        from app.providers.paper_trading import PaperTradingPortfolioProvider
        
        # Crear servicios
        provider = PaperTradingPortfolioProvider()
        portfolio_service = PortfolioService(provider)
        signal_service = SignalScorerService(portfolio_service)
        
        # Test que los motores están inicializados
        assert signal_service.evaluation_engine is not None
        assert signal_service.sizing_engine is not None
        assert signal_service.execution_engine is not None
        
        # Test estadísticas
        stats = await signal_service.get_signal_statistics()
        assert "service" in stats
        assert "evaluation_engine" in stats
        assert "sizing_engine" in stats
        assert "execution_engine" in stats
    
    @pytest.mark.asyncio
    async def test_portfolio_service_integration(self):
        """Test integración del PortfolioService refactorizado."""
        from app.services.portfolio_service import PortfolioService
        from app.providers.paper_trading import PaperTradingPortfolioProvider
        
        # Crear servicio
        provider = PaperTradingPortfolioProvider()
        portfolio_service = PortfolioService(provider)
        
        # Test que los gestores están inicializados
        assert portfolio_service.circuit_breaker_manager is not None
        assert portfolio_service.risk_manager is not None
        
        # Test estadísticas
        stats = portfolio_service.get_service_statistics()
        assert "service" in stats
        assert "circuit_breaker_manager" in stats
        assert "risk_manager" in stats
