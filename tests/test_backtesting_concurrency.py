"""
Tests de concurrencia para backtesting simultáneo.

Este módulo contiene tests para validar que el sistema maneja correctamente
múltiples ejecuciones de backtesting simultáneas sin race conditions.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, date
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import threading
import time

from app.models.backtesting import BacktestConfig, BacktestResult
from app.models.strategy import StrategyConfig
from app.backtesting.engine import BacktestingEngine
from app.core.centralized_config import get_config


class TestBacktestingConcurrency:
    """Tests de concurrencia para backtesting."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.backtesting_engine = BacktestingEngine()
        self.config = get_config()
    
    @pytest.mark.asyncio
    async def test_concurrent_backtest_execution(self):
        """Test ejecución concurrente de múltiples backtests."""
        
        # Crear múltiples configuraciones de backtest
        backtest_configs = []
        strategies = ["Momentum", "MeanReversion", "PairsTrading", "Liquidity"]
        
        for i, strategy in enumerate(strategies):
            config = BacktestConfig(
                strategy_name=strategy,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                initial_capital=Decimal('100000.0'),
                symbols=[f"SYMBOL_{j}" for j in range(5)],
                timeframe="1D",
                parameters={
                    "min_strength": Decimal('60.0'),
                    "min_confidence": Decimal('70.0'),
                    "max_position_size": Decimal('0.1')
                }
            )
            backtest_configs.append(config)
        
        # Ejecutar backtests concurrentemente
        results = []
        
        async def execute_backtest(config: BacktestConfig):
            try:
                result = await self.backtesting_engine.run_backtest(config)
                results.append({
                    'strategy': config.strategy_name,
                    'result': result,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'strategy': config.strategy_name,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(execute_backtest(config)) for config in backtest_configs]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(strategies)
        
        # Verificar que todos los backtests se ejecutaron correctamente
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(strategies)
        
        # Verificar que no hay errores de concurrencia
        error_results = [r for r in results if 'error' in r]
        assert len(error_results) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_backtest_parameter_optimization(self):
        """Test optimización concurrente de parámetros de backtest."""
        
        # Crear configuraciones con diferentes parámetros para optimizar
        optimization_configs = []
        base_strategy = "Momentum"
        
        for i in range(6):
            config = BacktestConfig(
                strategy_name=base_strategy,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                initial_capital=Decimal('100000.0'),
                symbols=["OPT_SYMBOL"],
                timeframe="1D",
                parameters={
                    "min_strength": Decimal('50.0') + Decimal(str(i * 5)),
                    "min_confidence": Decimal('60.0') + Decimal(str(i * 2)),
                    "max_position_size": Decimal('0.05') + Decimal(str(i * 0.01))
                }
            )
            optimization_configs.append(config)
        
        # Optimizar parámetros concurrentemente
        results = []
        
        async def optimize_parameters(config: BacktestConfig):
            try:
                optimized = await self.backtesting_service.optimize_parameters(config)
                results.append({
                    'config_id': id(config),
                    'optimized': optimized,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'config_id': id(config),
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(optimize_parameters(config)) for config in optimization_configs]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(optimization_configs)
        
        # Verificar que todas las optimizaciones fueron exitosas
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(optimization_configs)
    
    @pytest.mark.asyncio
    async def test_concurrent_backtest_result_analysis(self):
        """Test análisis concurrente de resultados de backtest."""
        
        # Crear resultados de backtest para analizar
        backtest_results = []
        strategies = ["ANALYSIS1", "ANALYSIS2", "ANALYSIS3", "ANALYSIS4"]
        
        for strategy in strategies:
            result = BacktestResult(
                strategy_name=strategy,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                initial_capital=Decimal('100000.0'),
                final_capital=Decimal('110000.0'),
                total_return=Decimal('0.1'),
                sharpe_ratio=Decimal('1.5'),
                max_drawdown=Decimal('0.05'),
                win_rate=Decimal('0.6'),
                total_trades=100,
                profitable_trades=60,
                losing_trades=40,
                avg_win=Decimal('500.0'),
                avg_loss=Decimal('300.0'),
                profit_factor=Decimal('2.0'),
                execution_time=Decimal('10.0')
            )
            backtest_results.append(result)
        
        # Analizar resultados concurrentemente
        results = []
        
        async def analyze_backtest_result(result: BacktestResult):
            try:
                analysis = await self.backtesting_service.analyze_backtest_result(result)
                results.append({
                    'strategy': result.strategy_name,
                    'analysis': analysis,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'strategy': result.strategy_name,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(analyze_backtest_result(result)) for result in backtest_results]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(strategies)
        
        # Verificar que todos los análisis fueron exitosos
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(strategies)
        
        # Verificar que los análisis contienen información válida
        for result in successful_results:
            analysis = result['analysis']
            assert 'performance_metrics' in analysis
            assert 'risk_metrics' in analysis
            assert 'recommendations' in analysis
    
    @pytest.mark.asyncio
    async def test_concurrent_backtest_comparison(self):
        """Test comparación concurrente de múltiples backtests."""
        
        # Crear resultados para comparar
        backtest_results = []
        strategies = ["COMP1", "COMP2", "COMP3", "COMP4", "COMP5"]
        
        for i, strategy in enumerate(strategies):
            result = BacktestResult(
                strategy_name=strategy,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                initial_capital=Decimal('100000.0'),
                final_capital=Decimal('100000.0') + Decimal(str(i * 5000)),
                total_return=Decimal('0.05') + Decimal(str(i * 0.01)),
                sharpe_ratio=Decimal('1.0') + Decimal(str(i * 0.2)),
                max_drawdown=Decimal('0.1') - Decimal(str(i * 0.01)),
                win_rate=Decimal('0.5') + Decimal(str(i * 0.05)),
                total_trades=100,
                profitable_trades=50 + i * 5,
                losing_trades=50 - i * 5,
                avg_win=Decimal('400.0') + Decimal(str(i * 50)),
                avg_loss=Decimal('300.0'),
                profit_factor=Decimal('1.5') + Decimal(str(i * 0.1)),
                execution_time=Decimal('10.0')
            )
            backtest_results.append(result)
        
        # Comparar resultados concurrentemente
        results = []
        
        async def compare_backtest_results(result: BacktestResult, other_results: List[BacktestResult]):
            try:
                comparison = await self.backtesting_service.compare_backtest_results(result, other_results)
                results.append({
                    'strategy': result.strategy_name,
                    'comparison': comparison,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'strategy': result.strategy_name,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(compare_backtest_results(result, backtest_results)) 
                for result in backtest_results]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(strategies)
        
        # Verificar que todas las comparaciones fueron exitosas
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(strategies)
    
    def test_thread_safety_backtest_execution(self):
        """Test thread safety en ejecución de backtests."""
        
        results = []
        errors = []
        
        def execute_backtest_thread(strategy_name: str):
            try:
                # Simular ejecución de backtest
                config = BacktestConfig(
                    strategy_name=strategy_name,
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 1, 31),
                    initial_capital=Decimal('100000.0'),
                    symbols=["THREAD_SYMBOL"],
                    timeframe="1D",
                    parameters={}
                )
                
                # Simular procesamiento síncrono
                result = self.backtesting_service._execute_backtest_sync(config)
                results.append(result)
                
            except Exception as e:
                errors.append(str(e))
        
        # Crear múltiples threads
        threads = []
        strategies = [f"THREAD_STRATEGY_{i}" for i in range(12)]
        
        for strategy in strategies:
            thread = threading.Thread(target=execute_backtest_thread, args=(strategy,))
            threads.append(thread)
        
        # Iniciar todos los threads
        for thread in threads:
            thread.start()
        
        # Esperar a que terminen
        for thread in threads:
            thread.join()
        
        # Verificar resultados
        assert len(results) == 12
        assert len(errors) == 0
        
        # Verificar que no hay duplicados
        strategy_names = [r.get('strategy_name') for r in results if isinstance(r, dict)]
        assert len(set(strategy_names)) == 12
    
    @pytest.mark.asyncio
    async def test_concurrent_backtest_data_loading(self):
        """Test carga concurrente de datos para backtesting."""
        
        # Crear configuraciones para cargar datos
        data_loading_configs = []
        symbols = ["DATA1", "DATA2", "DATA3", "DATA4", "DATA5"]
        
        for symbol in symbols:
            config = {
                'symbol': symbol,
                'start_date': date(2025, 1, 1),
                'end_date': date(2025, 1, 31),
                'timeframe': '1D',
                'data_source': 'mock'
            }
            data_loading_configs.append(config)
        
        # Cargar datos concurrentemente
        results = []
        
        async def load_backtest_data(config: Dict[str, Any]):
            try:
                data = await self.backtesting_service.load_backtest_data(config)
                results.append({
                    'symbol': config['symbol'],
                    'data_count': len(data),
                    'success': True
                })
            except Exception as e:
                results.append({
                    'symbol': config['symbol'],
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(load_backtest_data(config)) for config in data_loading_configs]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(symbols)
        
        # Verificar que todos los datos se cargaron correctamente
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(symbols)
        
        # Verificar que cada símbolo tiene datos
        for result in successful_results:
            assert result['data_count'] > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_backtest_validation(self):
        """Test validación concurrente de configuraciones de backtest."""
        
        # Crear configuraciones con diferentes características de validación
        backtest_configs = []
        
        # Configuraciones válidas
        for i in range(6):
            config = BacktestConfig(
                strategy_name=f"VALID_{i}",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                initial_capital=Decimal('100000.0'),
                symbols=[f"VALID_SYMBOL_{j}" for j in range(3)],
                timeframe="1D",
                parameters={
                    "min_strength": Decimal('60.0'),
                    "min_confidence": Decimal('70.0'),
                    "max_position_size": Decimal('0.1')
                }
            )
            backtest_configs.append(config)
        
        # Configuraciones con problemas de validación
        invalid_configs = [
            BacktestConfig(
                strategy_name="",  # Nombre vacío
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                initial_capital=Decimal('100000.0'),
                symbols=[],
                timeframe="1D",
                parameters={}
            ),
            BacktestConfig(
                strategy_name="INVALID",
                start_date=date(2025, 1, 31),  # Fecha de inicio después del fin
                end_date=date(2025, 1, 1),
                initial_capital=Decimal('100000.0'),
                symbols=["INVALID_SYMBOL"],
                timeframe="1D",
                parameters={}
            )
        ]
        
        all_configs = backtest_configs + invalid_configs
        
        # Validar configuraciones concurrentemente
        results = []
        
        async def validate_backtest_config(config: BacktestConfig):
            try:
                is_valid = await self.backtesting_service.validate_backtest_config(config)
                results.append({
                    'strategy_name': config.strategy_name,
                    'is_valid': is_valid,
                    'config': config,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'strategy_name': config.strategy_name,
                    'is_valid': False,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(validate_backtest_config(config)) for config in all_configs]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(all_configs)
        
        # Verificar que las configuraciones válidas pasaron la validación
        valid_results = [r for r in results if r.get('is_valid', False)]
        assert len(valid_results) == 6
        
        # Verificar que las configuraciones inválidas fallaron la validación
        invalid_results = [r for r in results if not r.get('is_valid', False)]
        assert len(invalid_results) == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_backtest_reporting(self):
        """Test generación concurrente de reportes de backtest."""
        
        # Crear resultados para reportar
        backtest_results = []
        strategies = ["REPORT1", "REPORT2", "REPORT3", "REPORT4", "REPORT5"]
        
        for strategy in strategies:
            result = BacktestResult(
                strategy_name=strategy,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                initial_capital=Decimal('100000.0'),
                final_capital=Decimal('110000.0'),
                total_return=Decimal('0.1'),
                sharpe_ratio=Decimal('1.5'),
                max_drawdown=Decimal('0.05'),
                win_rate=Decimal('0.6'),
                total_trades=100,
                profitable_trades=60,
                losing_trades=40,
                avg_win=Decimal('500.0'),
                avg_loss=Decimal('300.0'),
                profit_factor=Decimal('2.0'),
                execution_time=Decimal('10.0')
            )
            backtest_results.append(result)
        
        # Generar reportes concurrentemente
        results = []
        
        async def generate_backtest_report(result: BacktestResult):
            try:
                report = await self.backtesting_service.generate_backtest_report(result)
                results.append({
                    'strategy': result.strategy_name,
                    'report': report,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'strategy': result.strategy_name,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(generate_backtest_report(result)) for result in backtest_results]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(strategies)
        
        # Verificar que todos los reportes se generaron correctamente
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(strategies)
        
        # Verificar que los reportes contienen información válida
        for result in successful_results:
            report = result['report']
            assert 'summary' in report
            assert 'performance' in report
            assert 'risk_metrics' in report
            assert 'recommendations' in report
