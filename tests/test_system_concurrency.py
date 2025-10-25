"""
Test suite principal de concurrencia para el sistema de trading.

Este módulo integra todos los tests de concurrencia y proporciona
tests de integración end-to-end para validar la concurrencia del sistema completo.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, date
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import threading
import time

from app.models.order import Order, OrderType, OrderSide, OrderStatus
from app.models.signal import Signal, SignalType, SignalStrength
from app.models.portfolio import Portfolio, Position
from app.models.market_data import Quote, MarketData
from app.models.backtesting import BacktestConfig, BacktestResult
from app.services.paper_trading_service import PaperTradingService
from app.services.signal_scorer import SignalScorer
from app.services.portfolio_service import PortfolioService
from app.services.market_data_service import MarketDataService
from app.backtesting.engine import BacktestingEngine
from app.core.centralized_config import get_config


class TestSystemConcurrency:
    """Tests de concurrencia del sistema completo."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.paper_trading_service = PaperTradingService()
        self.signal_scorer_service = SignalScorer()
        self.portfolio_service = PortfolioService()
        self.market_data_service = MarketDataService()
        self.backtesting_engine = BacktestingEngine()
        self.config = get_config()
    
    @pytest.mark.asyncio
    async def test_end_to_end_concurrent_trading_flow(self):
        """Test flujo completo de trading concurrente end-to-end."""
        
        # Crear datos de entrada para el flujo completo
        symbols = ["E2E1", "E2E2", "E2E3"]
        
        # 1. Generar señales concurrentemente
        signals = []
        async def generate_signal(symbol: str):
            signal = Signal(
                id=f"signal_{symbol}",
                symbol=symbol,
                signal_type=SignalType.BUY,
                strength=SignalStrength.HIGH,
                confidence=Decimal('0.8'),
                timestamp=datetime.now(),
                price=Decimal('100.0'),
                metadata={'test': True}
            )
            signals.append(signal)
            return signal
        
        signal_tasks = [asyncio.create_task(generate_signal(symbol)) for symbol in symbols]
        await asyncio.gather(*signal_tasks)
        
        # 2. Scorear señales concurrentemente
        scored_signals = []
        async def score_signal(signal: Signal):
            score = await self.signal_scorer_service.score_signal(signal)
            scored_signals.append((signal, score))
            return signal, score
        
        score_tasks = [asyncio.create_task(score_signal(signal)) for signal in signals]
        await asyncio.gather(*score_tasks)
        
        # 3. Crear órdenes basadas en señales concurrentemente
        orders = []
        async def create_order(signal: Signal, score: float):
            order = Order(
                id=f"order_{signal.symbol}",
                symbol=signal.symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('10'),
                price=signal.price,
                timestamp=datetime.now(),
                status=OrderStatus.PENDING
            )
            orders.append(order)
            return order
        
        order_tasks = [asyncio.create_task(create_order(signal, score)) 
                      for signal, score in scored_signals]
        await asyncio.gather(*order_tasks)
        
        # 4. Ejecutar órdenes concurrentemente
        execution_results = []
        async def execute_order(order: Order):
            result = await self.paper_trading_service.execute_order(order)
            execution_results.append(result)
            return result
        
        execution_tasks = [asyncio.create_task(execute_order(order)) for order in orders]
        await asyncio.gather(*execution_tasks)
        
        # 5. Actualizar portfolio concurrentemente
        portfolio_updates = []
        async def update_portfolio(result: Dict[str, Any]):
            if 'symbol' in result:
                update = await self.portfolio_service.update_position(
                    symbol=result['symbol'],
                    side=OrderSide.BUY,
                    quantity=Decimal('10'),
                    price=Decimal('100.0'),
                    timestamp=datetime.now()
                )
                portfolio_updates.append(update)
                return update
        
        portfolio_tasks = [asyncio.create_task(update_portfolio(result)) 
                          for result in execution_results]
        await asyncio.gather(*portfolio_tasks)
        
        # Verificar que todo el flujo se ejecutó correctamente
        assert len(signals) == len(symbols)
        assert len(scored_signals) == len(signals)
        assert len(orders) == len(signals)
        assert len(execution_results) == len(orders)
        assert len(portfolio_updates) == len(execution_results)
        
        # Verificar que no hay errores de concurrencia
        assert all(isinstance(result, dict) for result in execution_results)
        assert all(isinstance(update, dict) for update in portfolio_updates)
    
    @pytest.mark.asyncio
    async def test_concurrent_market_data_to_signal_pipeline(self):
        """Test pipeline concurrente de market data a señales."""
        
        # Crear datos de mercado
        market_data = []
        symbols = ["PIPE1", "PIPE2", "PIPE3", "PIPE4"]
        
        for symbol in symbols:
            data = MarketData(
                symbol=symbol,
                price=Decimal('100.0'),
                volume=Decimal('1000000'),
                timestamp=datetime.now(),
                high=Decimal('110.0'),
                low=Decimal('90.0'),
                open=Decimal('95.0'),
                close=Decimal('105.0')
            )
            market_data.append(data)
        
        # Procesar pipeline concurrentemente
        results = []
        
        async def process_market_data_to_signal(data: MarketData):
            try:
                # 1. Validar market data
                is_valid = await self.market_data_service.validate_market_data(data)
                if not is_valid:
                    return None
                
                # 2. Filtrar market data
                passed_filter = await self.market_data_service.filter_market_data(data)
                if not passed_filter:
                    return None
                
                # 3. Cachear market data
                cached = await self.market_data_service.cache_market_data(data.symbol, data)
                
                # 4. Generar señal basada en market data
                signal = Signal(
                    id=f"pipeline_signal_{data.symbol}",
                    symbol=data.symbol,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    confidence=Decimal('0.7'),
                    timestamp=datetime.now(),
                    price=data.price,
                    metadata={'source': 'pipeline'}
                )
                
                # 5. Scorear señal
                score = await self.signal_scorer_service.score_signal(signal)
                
                results.append({
                    'symbol': data.symbol,
                    'signal': signal,
                    'score': score,
                    'cached': cached,
                    'success': True
                })
                
            except Exception as e:
                results.append({
                    'symbol': data.symbol,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(process_market_data_to_signal(data)) for data in market_data]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(symbols)
        
        # Verificar que todas las operaciones fueron exitosas
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(symbols)
        
        # Verificar que las señales se generaron correctamente
        for result in successful_results:
            assert 'signal' in result
            assert 'score' in result
            assert 'cached' in result
    
    @pytest.mark.asyncio
    async def test_concurrent_backtesting_with_live_trading_simulation(self):
        """Test backtesting concurrente con simulación de trading en vivo."""
        
        # Crear configuraciones de backtest
        backtest_configs = []
        strategies = ["LIVE_SIM1", "LIVE_SIM2", "LIVE_SIM3"]
        
        for strategy in strategies:
            config = BacktestConfig(
                strategy_name=strategy,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                initial_capital=Decimal('100000.0'),
                symbols=[f"LIVE_SYMBOL_{i}" for i in range(3)],
                timeframe="1D",
                parameters={
                    "min_strength": Decimal('60.0'),
                    "min_confidence": Decimal('70.0'),
                    "max_position_size": Decimal('0.1')
                }
            )
            backtest_configs.append(config)
        
        # Ejecutar backtests concurrentemente
        backtest_results = []
        
        async def run_backtest_with_simulation(config: BacktestConfig):
            try:
                # 1. Ejecutar backtest
                result = await self.backtesting_service.run_backtest(config)
                
                # 2. Simular trading en vivo basado en resultados
                simulated_trades = []
                for i in range(5):  # Simular 5 trades
                    order = Order(
                        id=f"sim_trade_{config.strategy_name}_{i}",
                        symbol=config.symbols[i % len(config.symbols)],
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=Decimal('10'),
                        price=Decimal('100.0'),
                        timestamp=datetime.now(),
                        status=OrderStatus.PENDING
                    )
                    
                    # Ejecutar orden simulada
                    trade_result = await self.paper_trading_service.execute_order(order)
                    simulated_trades.append(trade_result)
                
                # 3. Analizar resultados combinados
                analysis = await self.backtesting_service.analyze_backtest_result(result)
                
                backtest_results.append({
                    'strategy': config.strategy_name,
                    'backtest_result': result,
                    'simulated_trades': simulated_trades,
                    'analysis': analysis,
                    'success': True
                })
                
            except Exception as e:
                backtest_results.append({
                    'strategy': config.strategy_name,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(run_backtest_with_simulation(config)) 
                for config in backtest_configs]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(backtest_results) == len(strategies)
        
        # Verificar que todos los backtests con simulación fueron exitosos
        successful_results = [r for r in backtest_results if r.get('success', False)]
        assert len(successful_results) == len(strategies)
        
        # Verificar que cada resultado contiene todos los componentes
        for result in successful_results:
            assert 'backtest_result' in result
            assert 'simulated_trades' in result
            assert 'analysis' in result
            assert len(result['simulated_trades']) == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_portfolio_rebalancing_with_risk_management(self):
        """Test rebalanceo concurrente de portfolios con gestión de riesgo."""
        
        # Crear portfolios para rebalancear
        portfolios = []
        portfolio_names = ["RISK_PORT1", "RISK_PORT2", "RISK_PORT3"]
        
        for name in portfolio_names:
            positions = []
            for i in range(4):
                position = Position(
                    symbol=f"RISK_SYMBOL_{i}",
                    quantity=Decimal('100'),
                    average_price=Decimal('50.0'),
                    current_price=Decimal('55.0'),
                    unrealized_pnl=Decimal('500.0'),
                    realized_pnl=Decimal('0.0')
                )
                positions.append(position)
            
            portfolio = Portfolio(
                id=f"risk_portfolio_{name}",
                name=name,
                positions=positions,
                total_value=Decimal('22000.0'),
                cash=Decimal('5000.0'),
                total_pnl=Decimal('2000.0'),
                last_updated=datetime.now()
            )
            portfolios.append(portfolio)
        
        # Rebalancear portfolios con gestión de riesgo concurrentemente
        results = []
        
        async def rebalance_with_risk_management(portfolio: Portfolio):
            try:
                # 1. Calcular métricas de riesgo
                risk_metrics = await self.portfolio_service.calculate_portfolio_risk(portfolio)
                
                # 2. Verificar límites de riesgo
                risk_ok = (risk_metrics.get('var', 0) < 0.1 and 
                          risk_metrics.get('max_drawdown', 0) < 0.15)
                
                if not risk_ok:
                    return {
                        'portfolio_id': portfolio.id,
                        'risk_exceeded': True,
                        'risk_metrics': risk_metrics,
                        'success': True
                    }
                
                # 3. Rebalancear portfolio
                rebalanced = await self.portfolio_service.rebalance_portfolio(portfolio)
                
                # 4. Optimizar portfolio
                optimized = await self.portfolio_service.optimize_portfolio(rebalanced)
                
                # 5. Generar reporte
                report = await self.portfolio_service.generate_portfolio_report(optimized)
                
                results.append({
                    'portfolio_id': portfolio.id,
                    'risk_metrics': risk_metrics,
                    'rebalanced': rebalanced,
                    'optimized': optimized,
                    'report': report,
                    'success': True
                })
                
            except Exception as e:
                results.append({
                    'portfolio_id': portfolio.id,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(rebalance_with_risk_management(portfolio)) 
                for portfolio in portfolios]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(portfolio_names)
        
        # Verificar que todas las operaciones fueron exitosas
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(portfolio_names)
        
        # Verificar que cada resultado contiene todos los componentes
        for result in successful_results:
            if not result.get('risk_exceeded', False):
                assert 'risk_metrics' in result
                assert 'rebalanced' in result
                assert 'optimized' in result
                assert 'report' in result
    
    def test_thread_safety_complete_system(self):
        """Test thread safety del sistema completo."""
        
        results = []
        errors = []
        
        def complete_trading_thread(thread_id: str):
            try:
                # Simular flujo completo de trading en un thread
                
                # 1. Crear señal
                signal = Signal(
                    id=f"thread_signal_{thread_id}",
                    symbol=f"THREAD_SYMBOL_{thread_id}",
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    confidence=Decimal('0.7'),
                    timestamp=datetime.now(),
                    price=Decimal('100.0'),
                    metadata={'thread': thread_id}
                )
                
                # 2. Crear orden
                order = Order(
                    id=f"thread_order_{thread_id}",
                    symbol=f"THREAD_SYMBOL_{thread_id}",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=Decimal('10'),
                    price=Decimal('100.0'),
                    timestamp=datetime.now(),
                    status=OrderStatus.PENDING
                )
                
                # 3. Simular procesamiento síncrono
                signal_result = self.signal_scorer_service._process_signal_sync(signal)
                order_result = self.paper_trading_service._process_order_sync(order)
                
                results.append({
                    'thread_id': thread_id,
                    'signal_result': signal_result,
                    'order_result': order_result,
                    'success': True
                })
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Crear múltiples threads
        threads = []
        thread_ids = [f"THREAD_{i}" for i in range(20)]
        
        for thread_id in thread_ids:
            thread = threading.Thread(target=complete_trading_thread, args=(thread_id,))
            threads.append(thread)
        
        # Iniciar todos los threads
        for thread in threads:
            thread.start()
        
        # Esperar a que terminen
        for thread in threads:
            thread.join()
        
        # Verificar resultados
        assert len(results) == 20
        assert len(errors) == 0
        
        # Verificar que no hay duplicados
        thread_ids_processed = [r['thread_id'] for r in results]
        assert len(set(thread_ids_processed)) == 20
        
        # Verificar que todos los resultados son válidos
        for result in results:
            assert result['success'] is True
            assert 'signal_result' in result
            assert 'order_result' in result
    
    @pytest.mark.asyncio
    async def test_concurrent_error_handling_and_recovery(self):
        """Test manejo concurrente de errores y recuperación."""
        
        # Crear operaciones que pueden fallar
        operations = []
        
        # Operaciones que deberían fallar
        for i in range(3):
            operations.append({
                'type': 'invalid_order',
                'data': {
                    'symbol': '',  # Símbolo inválido
                    'quantity': Decimal('0'),  # Cantidad inválida
                    'price': Decimal('-100.0')  # Precio inválido
                }
            })
        
        # Operaciones que deberían ser exitosas
        for i in range(5):
            operations.append({
                'type': 'valid_order',
                'data': {
                    'symbol': f"VALID_{i}",
                    'quantity': Decimal('10'),
                    'price': Decimal('100.0')
                }
            })
        
        # Procesar operaciones concurrentemente con manejo de errores
        results = []
        
        async def process_operation_with_error_handling(operation: Dict[str, Any]):
            try:
                if operation['type'] == 'invalid_order':
                    # Simular operación que falla
                    raise ValueError("Invalid operation data")
                else:
                    # Simular operación exitosa
                    order = Order(
                        id=f"op_{operation['data']['symbol']}",
                        symbol=operation['data']['symbol'],
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=operation['data']['quantity'],
                        price=operation['data']['price'],
                        timestamp=datetime.now(),
                        status=OrderStatus.PENDING
                    )
                    
                    result = await self.paper_trading_service.execute_order(order)
                    results.append({
                        'operation_type': operation['type'],
                        'symbol': operation['data']['symbol'],
                        'result': result,
                        'success': True
                    })
                    
            except Exception as e:
                # Manejar error y continuar
                results.append({
                    'operation_type': operation['type'],
                    'error': str(e),
                    'recovered': True,
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(process_operation_with_error_handling(op)) 
                for op in operations]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(operations)
        
        # Verificar que las operaciones válidas fueron exitosas
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == 5
        
        # Verificar que las operaciones inválidas fueron manejadas correctamente
        error_results = [r for r in results if not r.get('success', False)]
        assert len(error_results) == 3
        
        # Verificar que todos los errores fueron recuperados
        for result in error_results:
            assert result.get('recovered', False) is True
