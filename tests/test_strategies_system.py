"""
Tests para el Sistema de Estrategias Múltiples - TASK-31

Tests completos para el framework de estrategias múltiples,
incluyendo BaseStrategy, Factory, Registry, ConfigLoader, ExecutionEngine y Logger.
"""

import pytest
import json
import tempfile
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from app.strategies.base import BaseStrategy
from app.strategies.factory import StrategyFactory
from app.strategies.registry import StrategyRegistry
from app.strategies.config_loader import StrategyConfigLoader
from app.strategies.execution_engine import ExecutionEngine
from app.strategies.strategy_logger import StrategyLogger
from app.strategies.momentum import MomentumStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.pairs_trading import PairsTradingStrategy
from app.models.market_data import Quote
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.portfolio import Portfolio, Position


class TestMomentumStrategy(BaseStrategy):
    """Estrategia de prueba para testing."""
    
    def __init__(self, config):
        super().__init__(config)
        self.test_mode = True
    
    def generate_signals(self, market_data: Quote) -> list:
        """Generar señal de prueba."""
        return [Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=market_data.volume,
            timestamp=market_data.timestamp,
            metadata={"test": True}
        )]
    
    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """Risk check de prueba."""
        return True
    
    def get_required_parameters(self) -> list:
        """Parámetros requeridos de prueba."""
        return ["test_param"]


class TestStrategySystem:
    """Tests para el sistema completo de estrategias."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.sample_config = {
            "name": "test_strategy",
            "description": "Test strategy",
            "version": "1.0.0",
            "test_param": "test_value"
        }
        
        self.sample_market_data = Quote(
            symbol="AAPL",
            bid=Decimal("149.50"),
            ask=Decimal("150.50"),
            last=Decimal("150.00"),
            open=Decimal("149.00"),
            high=Decimal("151.00"),
            low=Decimal("148.00"),
            close=Decimal("150.00"),
            volume=Decimal("1000000"),
            spread=Decimal("1.00"),
            feed_type="mock",
            timestamp=datetime.utcnow()
        )
        
        self.sample_portfolio = Portfolio(
            cash=Decimal("10000"),
            positions=[],
            broker="test_broker"
        )


class TestBaseStrategy(TestStrategySystem):
    """Tests para BaseStrategy."""
    
    def test_base_strategy_initialization(self):
        """Test inicialización de BaseStrategy."""
        strategy = TestMomentumStrategy(self.sample_config)
        
        assert strategy.name == "test_strategy"
        assert strategy.description == "Test strategy"
        assert strategy.version == "1.0.0"
        assert strategy.is_active is False
        assert strategy.test_mode is True
    
    def test_get_parameters(self):
        """Test obtención de parámetros."""
        strategy = TestMomentumStrategy(self.sample_config)
        params = strategy.get_parameters()
        
        assert params == self.sample_config
    
    def test_update_parameters(self):
        """Test actualización de parámetros."""
        strategy = TestMomentumStrategy(self.sample_config)
        strategy.update_parameters({"new_param": "new_value"})
        
        assert strategy.config["new_param"] == "new_value"
    
    def test_validate_config(self):
        """Test validación de configuración."""
        strategy = TestMomentumStrategy(self.sample_config)
        
        assert strategy.validate_config() is True
        
        # Test con configuración inválida
        invalid_config = {"name": "test"}
        invalid_strategy = TestMomentumStrategy(invalid_config)
        
        assert invalid_strategy.validate_config() is False
    


class TestStrategyFactory(TestStrategySystem):
    """Tests para StrategyFactory."""
    
    def test_factory_initialization(self):
        """Test inicialización del factory."""
        factory = StrategyFactory()
        
        assert isinstance(factory.strategy_registry, dict)
        assert len(factory.strategy_registry) > 0  # Debe tener estrategias por defecto
    
    def test_register_strategy(self):
        """Test registro de estrategia."""
        factory = StrategyFactory()
        
        factory.register_strategy("test", TestMomentumStrategy)
        
        assert "test" in factory.strategy_registry
        assert factory.strategy_registry["test"] == TestMomentumStrategy
    
    def test_register_invalid_strategy(self):
        """Test registro de estrategia inválida."""
        factory = StrategyFactory()
        
        with pytest.raises(ValueError, match="must inherit from BaseStrategy"):
            factory.register_strategy("invalid", str)
    
    def test_create_strategy(self):
        """Test creación de estrategia."""
        factory = StrategyFactory()
        factory.register_strategy("test", TestMomentumStrategy)
        
        strategy = factory.create_strategy("test", self.sample_config)
        
        assert isinstance(strategy, TestMomentumStrategy)
        assert strategy.name == "test_strategy"
    
    def test_create_nonexistent_strategy(self):
        """Test creación de estrategia inexistente."""
        factory = StrategyFactory()
        
        with pytest.raises(ValueError, match="not found"):
            factory.create_strategy("nonexistent", self.sample_config)
    
    def test_list_available_strategies(self):
        """Test listado de estrategias disponibles."""
        factory = StrategyFactory()
        
        strategies = factory.list_available_strategies()
        
        assert isinstance(strategies, list)
        assert len(strategies) > 0


class TestStrategyRegistry(TestStrategySystem):
    """Tests para StrategyRegistry."""
    
    def test_registry_initialization(self):
        """Test inicialización del registry."""
        registry = StrategyRegistry()
        
        assert isinstance(registry.strategies, dict)
        assert registry.active_strategy is None
        assert isinstance(registry.factory, StrategyFactory)
    
    def test_load_strategy(self):
        """Test carga de estrategia."""
        registry = StrategyRegistry()
        registry.factory.register_strategy("test", TestMomentumStrategy)
        
        strategy = registry.load_strategy("test", self.sample_config)
        
        assert isinstance(strategy, TestMomentumStrategy)
        assert "test" in registry.strategies
    
    def test_unload_strategy(self):
        """Test descarga de estrategia."""
        registry = StrategyRegistry()
        registry.factory.register_strategy("test", TestMomentumStrategy)
        registry.load_strategy("test", self.sample_config)
        
        registry.unload_strategy("test")
        
        assert "test" not in registry.strategies
    
    def test_set_active_strategy(self):
        """Test activación de estrategia."""
        registry = StrategyRegistry()
        registry.factory.register_strategy("test", TestMomentumStrategy)
        registry.load_strategy("test", self.sample_config)
        
        registry.set_active_strategy("test")
        
        assert registry.active_strategy == "test"
        assert registry.strategies["test"].is_active is True
    
    def test_get_active_strategy(self):
        """Test obtención de estrategia activa."""
        registry = StrategyRegistry()
        registry.factory.register_strategy("test", TestMomentumStrategy)
        registry.load_strategy("test", self.sample_config)
        registry.set_active_strategy("test")
        
        active_strategy = registry.get_active_strategy()
        
        assert active_strategy is not None
        assert active_strategy.name == "test_strategy"


class TestStrategyConfigLoader(TestStrategySystem):
    """Tests para StrategyConfigLoader."""
    
    def test_config_loader_initialization(self):
        """Test inicialización del config loader."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
strategies:
  test:
    class: "TestStrategy"
    config:
      name: "test"
      description: "Test strategy"
active_strategies: ["test"]
""")
            config_path = f.name
        
        try:
            loader = StrategyConfigLoader(config_path)
            assert loader.config_path == Path(config_path)
        finally:
            Path(config_path).unlink()
    
    def test_load_config(self):
        """Test carga de configuración."""
        config_data = {
            "strategies": {
                "test": {
                    "class": "TestStrategy",
                    "config": {"name": "test"}
                }
            },
            "active_strategies": ["test"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            loader = StrategyConfigLoader(config_path)
            config = loader.load_config()
            
            assert config == config_data
        finally:
            Path(config_path).unlink()
    
    def test_get_strategy_config(self):
        """Test obtención de configuración de estrategia."""
        config_data = {
            "strategies": {
                "test": {
                    "class": "TestStrategy",
                    "config": {"name": "test"}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            loader = StrategyConfigLoader(config_path)
            loader.load_config()
            
            strategy_config = loader.get_strategy_config("test")
            assert strategy_config == config_data["strategies"]["test"]
        finally:
            Path(config_path).unlink()
    
    def test_validate_config(self):
        """Test validación de configuración."""
        config_data = {
            "strategies": {
                "test": {
                    "class": "TestStrategy",
                    "config": {"name": "test"}
                }
            },
            "active_strategies": ["test"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            loader = StrategyConfigLoader(config_path)
            loader.load_config()
            
            assert loader.validate_config() is True
        finally:
            Path(config_path).unlink()


class TestStrategyLogger(TestStrategySystem):
    """Tests para StrategyLogger."""
    
    def test_logger_initialization(self):
        """Test inicialización del logger."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            log_path = f.name
        
        try:
            logger = StrategyLogger(log_path)
            
            assert logger.log_path == Path(log_path)
            assert isinstance(logger.logs, list)
        finally:
            Path(log_path).unlink()
    
    def test_log_signal_generated(self):
        """Test log de señal generada."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            log_path = f.name
        
        try:
            logger = StrategyLogger(log_path)
            signal = Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=80.0,
                liquidity_score=75.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150.00"),
                volume=Decimal("1000000"),
                timestamp=datetime.utcnow(),
                metadata={"test": True}
            )
            
            logger.log_signal_generated("test_strategy", signal)
            
            assert len(logger.logs) == 1
            assert logger.logs[0]["event"] == "signal_generated"
            assert logger.logs[0]["strategy"] == "test_strategy"
        finally:
            Path(log_path).unlink()
    
    def test_get_strategy_metrics(self):
        """Test obtención de métricas de estrategia."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            log_path = f.name
        
        try:
            logger = StrategyLogger(log_path)
            signal = Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=80.0,
                liquidity_score=75.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150.00"),
                volume=Decimal("1000000"),
                timestamp=datetime.utcnow(),
                metadata={"test": True}
            )
            
            logger.log_signal_generated("test_strategy", signal)
            logger.log_signal_executed("test_strategy", signal)
            
            metrics = logger.get_strategy_metrics("test_strategy")
            
            assert metrics["strategy"] == "test_strategy"
            assert metrics["signals_generated"] == 1
            assert metrics["signals_executed"] == 1
            assert metrics["execution_rate"] == 1.0
        finally:
            Path(log_path).unlink()


class TestExecutionEngine(TestStrategySystem):
    """Tests para ExecutionEngine."""
    
    def test_execution_engine_initialization(self):
        """Test inicialización del execution engine."""
        registry = StrategyRegistry()
        logger = StrategyLogger()
        
        engine = ExecutionEngine(registry, logger)
        
        assert engine.registry == registry
        assert engine.logger == logger
        assert engine.is_running is False
    
    def test_start_stop_engine(self):
        """Test inicio y parada del engine."""
        registry = StrategyRegistry()
        logger = StrategyLogger()
        engine = ExecutionEngine(registry, logger)
        
        engine.start()
        assert engine.is_running is True
        
        engine.stop()
        assert engine.is_running is False
    
    def test_run_cycle_no_active_strategy(self):
        """Test ejecución de ciclo sin estrategia activa."""
        registry = StrategyRegistry()
        logger = StrategyLogger()
        engine = ExecutionEngine(registry, logger)
        engine.start()
        
        signals = engine.run_cycle(self.sample_market_data, self.sample_portfolio)
        
        assert signals == []
    
    def test_execute_signal(self):
        """Test ejecución de señal."""
        registry = StrategyRegistry()
        logger = StrategyLogger()
        engine = ExecutionEngine(registry, logger)
        
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow(),
            metadata={"test": True}
        )
        
        success = engine.execute_signal(signal)
        
        assert success is True
        assert engine.total_signals_executed == 1
    
    def test_get_execution_stats(self):
        """Test obtención de estadísticas de ejecución."""
        registry = StrategyRegistry()
        logger = StrategyLogger()
        engine = ExecutionEngine(registry, logger)
        
        stats = engine.get_execution_stats()
        
        assert "is_running" in stats
        assert "cycle_count" in stats
        assert "total_signals_generated" in stats
        assert "total_signals_executed" in stats


class TestConcreteStrategies(TestStrategySystem):
    """Tests para estrategias concretas."""
    
    def test_momentum_strategy(self):
        """Test estrategia de momentum."""
        config = {
            "name": "momentum",
            "description": "Momentum strategy",
            "version": "1.0.0",
            "rsi_threshold": 40,
            "momentum_threshold": 0.02,
            "stop_loss": 0.05,
            "take_profit": 0.10,
            "max_position_size": 0.1
        }
        
        strategy = MomentumStrategy(config)
        
        assert strategy.name == "momentum"
        assert strategy.rsi_threshold == Decimal("40")
        assert strategy.momentum_threshold == Decimal("0.02")
        
        signals = strategy.generate_signals(self.sample_market_data)
        assert isinstance(signals, list)
    
    def test_mean_reversion_strategy(self):
        """Test estrategia de mean reversion."""
        config = {
            "name": "mean_reversion",
            "description": "Mean reversion strategy",
            "version": "1.0.0",
            "z_score_threshold": 2.0,
            "lookback_period": 20,
            "stop_loss": 0.03,
            "take_profit": 0.06,
            "max_position_size": 0.08
        }
        
        strategy = MeanReversionStrategy(config)
        
        assert strategy.name == "mean_reversion"
        assert strategy.z_score_threshold == Decimal("2.0")
        assert strategy.lookback_period == 20
        
        signals = strategy.generate_signals(self.sample_market_data)
        assert isinstance(signals, list)
    
    def test_pairs_trading_strategy(self):
        """Test estrategia de pairs trading."""
        config = {
            "name": "pairs_trading",
            "description": "Pairs trading strategy",
            "version": "1.0.0",
            "cointegration_threshold": 0.05,
            "spread_threshold": 2.0,
            "stop_loss": 0.04,
            "take_profit": 0.08,
            "max_position_size": 0.06,
            "pair_symbols": ["AAPL", "MSFT"]
        }
        
        strategy = PairsTradingStrategy(config)
        
        assert strategy.name == "pairs_trading"
        assert strategy.cointegration_threshold == Decimal("0.05")
        assert strategy.pair_symbols == ["AAPL", "MSFT"]
        
        signals = strategy.generate_signals(self.sample_market_data)
        assert isinstance(signals, list)


class TestIntegration(TestStrategySystem):
    """Tests de integración del sistema completo."""
    
    def test_complete_strategy_workflow(self):
        """Test flujo completo de trabajo con estrategias."""
        # Crear componentes
        registry = StrategyRegistry()
        logger = StrategyLogger()
        engine = ExecutionEngine(registry, logger)
        
        # Registrar y cargar estrategia
        registry.factory.register_strategy("test", TestMomentumStrategy)
        strategy = registry.load_strategy("test", self.sample_config)
        
        # Activar estrategia
        registry.set_active_strategy("test")
        
        # Iniciar engine
        engine.start()
        
        # Ejecutar ciclo
        signals = engine.run_cycle(self.sample_market_data, self.sample_portfolio)
        
        # Verificar resultados
        assert len(signals) > 0
        assert engine.total_signals_generated > 0
        
        # Verificar logs
        metrics = logger.get_strategy_metrics("test_strategy")
        assert metrics["signals_generated"] > 0
        
        # Parar engine
        engine.stop()
        assert engine.is_running is False
    
    def test_strategy_switching(self):
        """Test cambio de estrategias."""
        registry = StrategyRegistry()
        
        # Registrar múltiples estrategias
        registry.factory.register_strategy("test1", TestMomentumStrategy)
        registry.factory.register_strategy("test2", TestMomentumStrategy)
        
        # Cargar estrategias
        config1 = {"name": "test1", "test_param": "value1"}
        config2 = {"name": "test2", "test_param": "value2"}
        
        registry.load_strategy("test1", config1)
        registry.load_strategy("test2", config2)
        
        # Activar primera estrategia
        registry.set_active_strategy("test1")
        assert registry.active_strategy == "test1"
        assert registry.strategies["test1"].is_active is True
        assert registry.strategies["test2"].is_active is False
        
        # Cambiar a segunda estrategia
        registry.set_active_strategy("test2")
        assert registry.active_strategy == "test2"
        assert registry.strategies["test1"].is_active is False
        assert registry.strategies["test2"].is_active is True
