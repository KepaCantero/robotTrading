"""
Tests de concurrencia para actualizaciones de portfolio.

Este módulo contiene tests para validar que el sistema maneja correctamente
múltiples actualizaciones de portfolio simultáneas sin race conditions.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import threading
import time

from app.models.portfolio import Portfolio, Position
from app.models.order import Order, OrderType, OrderSide, OrderStatus
from app.services.portfolio_service import PortfolioService
from app.services.paper_trading_service import PaperTradingService
from app.core.centralized_config import get_config


class TestPortfolioConcurrency:
    """Tests de concurrencia para portfolio."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.portfolio_service = PortfolioService()
        self.paper_trading_service = PaperTradingService()
        self.config = get_config()
    
    @pytest.mark.asyncio
    async def test_concurrent_position_updates(self):
        """Test actualizaciones concurrentes de posiciones."""
        
        # Crear múltiples actualizaciones de posición
        position_updates = []
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        
        for symbol in symbols:
            for i in range(3):  # 3 actualizaciones por símbolo
                update = {
                    'symbol': symbol,
                    'side': OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                    'quantity': Decimal('10'),
                    'price': Decimal('100.0'),
                    'timestamp': datetime.now(),
                    'order_id': f"update_{symbol}_{i}"
                }
                position_updates.append(update)
        
        # Actualizar posiciones concurrentemente
        results = []
        
        async def update_position(update: Dict[str, Any]):
            try:
                result = await self.portfolio_service.update_position(
                    symbol=update['symbol'],
                    side=update['side'],
                    quantity=update['quantity'],
                    price=update['price'],
                    timestamp=update['timestamp']
                )
                results.append({
                    'order_id': update['order_id'],
                    'symbol': update['symbol'],
                    'result': result,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'order_id': update['order_id'],
                    'symbol': update['symbol'],
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(update_position(update)) for update in position_updates]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(position_updates)
        
        # Verificar que todas las actualizaciones fueron exitosas
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(position_updates)
        
        # Verificar que no hay errores de concurrencia
        error_results = [r for r in results if 'error' in r]
        assert len(error_results) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_portfolio_calculations(self):
        """Test cálculos concurrentes de portfolio."""
        
        # Crear múltiples portfolios para calcular
        portfolios = []
        for i in range(8):
            positions = []
            for j in range(5):
                position = Position(
                    symbol=f"SYMBOL_{j}",
                    quantity=Decimal('100'),
                    average_price=Decimal('50.0'),
                    current_price=Decimal('55.0'),
                    unrealized_pnl=Decimal('500.0'),
                    realized_pnl=Decimal('0.0')
                )
                positions.append(position)
            
            portfolio = Portfolio(
                id=f"portfolio_{i}",
                name=f"Test Portfolio {i}",
                positions=positions,
                total_value=Decimal('27500.0'),
                cash=Decimal('10000.0'),
                total_pnl=Decimal('2500.0'),
                last_updated=datetime.now()
            )
            portfolios.append(portfolio)
        
        # Calcular métricas concurrentemente
        results = []
        
        async def calculate_portfolio_metrics(portfolio: Portfolio):
            try:
                metrics = await self.portfolio_service.calculate_portfolio_metrics(portfolio)
                results.append({
                    'portfolio_id': portfolio.id,
                    'metrics': metrics,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'portfolio_id': portfolio.id,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(calculate_portfolio_metrics(portfolio)) for portfolio in portfolios]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(portfolios)
        
        # Verificar que todos los cálculos fueron exitosos
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(portfolios)
        
        # Verificar que las métricas son válidas
        for result in successful_results:
            metrics = result['metrics']
            assert 'total_value' in metrics
            assert 'total_pnl' in metrics
            assert 'return_percentage' in metrics
    
    @pytest.mark.asyncio
    async def test_concurrent_portfolio_rebalancing(self):
        """Test rebalanceo concurrente de portfolios."""
        
        # Crear portfolios para rebalancear
        portfolios = []
        for i in range(6):
            positions = []
            for j in range(3):
                position = Position(
                    symbol=f"REBAL_{j}",
                    quantity=Decimal('100'),
                    average_price=Decimal('50.0'),
                    current_price=Decimal('60.0'),
                    unrealized_pnl=Decimal('1000.0'),
                    realized_pnl=Decimal('0.0')
                )
                positions.append(position)
            
            portfolio = Portfolio(
                id=f"rebal_portfolio_{i}",
                name=f"Rebal Portfolio {i}",
                positions=positions,
                total_value=Decimal('18000.0'),
                cash=Decimal('5000.0'),
                total_pnl=Decimal('3000.0'),
                last_updated=datetime.now()
            )
            portfolios.append(portfolio)
        
        # Rebalancear portfolios concurrentemente
        results = []
        
        async def rebalance_portfolio(portfolio: Portfolio):
            try:
                rebalanced = await self.portfolio_service.rebalance_portfolio(portfolio)
                results.append({
                    'portfolio_id': portfolio.id,
                    'rebalanced': rebalanced,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'portfolio_id': portfolio.id,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(rebalance_portfolio(portfolio)) for portfolio in portfolios]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(portfolios)
        
        # Verificar que todos los rebalanceos fueron exitosos
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(portfolios)
    
    @pytest.mark.asyncio
    async def test_concurrent_portfolio_risk_calculations(self):
        """Test cálculos concurrentes de riesgo de portfolio."""
        
        # Crear portfolios para análisis de riesgo
        portfolios = []
        for i in range(10):
            positions = []
            for j in range(4):
                position = Position(
                    symbol=f"RISK_{j}",
                    quantity=Decimal('50'),
                    average_price=Decimal('100.0'),
                    current_price=Decimal('105.0'),
                    unrealized_pnl=Decimal('250.0'),
                    realized_pnl=Decimal('0.0')
                )
                positions.append(position)
            
            portfolio = Portfolio(
                id=f"risk_portfolio_{i}",
                name=f"Risk Portfolio {i}",
                positions=positions,
                total_value=Decimal('21000.0'),
                cash=Decimal('2000.0'),
                total_pnl=Decimal('1000.0'),
                last_updated=datetime.now()
            )
            portfolios.append(portfolio)
        
        # Calcular riesgo concurrentemente
        results = []
        
        async def calculate_portfolio_risk(portfolio: Portfolio):
            try:
                risk_metrics = await self.portfolio_service.calculate_portfolio_risk(portfolio)
                results.append({
                    'portfolio_id': portfolio.id,
                    'risk_metrics': risk_metrics,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'portfolio_id': portfolio.id,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(calculate_portfolio_risk(portfolio)) for portfolio in portfolios]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(portfolios)
        
        # Verificar que todos los cálculos de riesgo fueron exitosos
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(portfolios)
        
        # Verificar que las métricas de riesgo son válidas
        for result in successful_results:
            risk_metrics = result['risk_metrics']
            assert 'var' in risk_metrics
            assert 'sharpe_ratio' in risk_metrics
            assert 'max_drawdown' in risk_metrics
    
    def test_thread_safety_portfolio_updates(self):
        """Test thread safety en actualizaciones de portfolio."""
        
        results = []
        errors = []
        
        def update_portfolio_thread(portfolio_id: str):
            try:
                # Simular actualización de portfolio
                portfolio = Portfolio(
                    id=portfolio_id,
                    name=f"Thread Portfolio {portfolio_id}",
                    positions=[],
                    total_value=Decimal('10000.0'),
                    cash=Decimal('10000.0'),
                    total_pnl=Decimal('0.0'),
                    last_updated=datetime.now()
                )
                
                # Simular procesamiento síncrono
                result = self.portfolio_service._update_portfolio_sync(portfolio)
                results.append(result)
                
            except Exception as e:
                errors.append(str(e))
        
        # Crear múltiples threads
        threads = []
        for i in range(15):
            thread = threading.Thread(target=update_portfolio_thread, args=(f"thread_portfolio_{i}",))
            threads.append(thread)
        
        # Iniciar todos los threads
        for thread in threads:
            thread.start()
        
        # Esperar a que terminen
        for thread in threads:
            thread.join()
        
        # Verificar resultados
        assert len(results) == 15
        assert len(errors) == 0
        
        # Verificar que no hay duplicados
        portfolio_ids = [r.get('portfolio_id') for r in results if isinstance(r, dict)]
        assert len(set(portfolio_ids)) == 15
    
    @pytest.mark.asyncio
    async def test_concurrent_portfolio_optimization(self):
        """Test optimización concurrente de portfolios."""
        
        # Crear portfolios para optimizar
        portfolios = []
        for i in range(5):
            positions = []
            for j in range(6):
                position = Position(
                    symbol=f"OPT_{j}",
                    quantity=Decimal('75'),
                    average_price=Decimal('80.0'),
                    current_price=Decimal('85.0'),
                    unrealized_pnl=Decimal('375.0'),
                    realized_pnl=Decimal('0.0')
                )
                positions.append(position)
            
            portfolio = Portfolio(
                id=f"opt_portfolio_{i}",
                name=f"Opt Portfolio {i}",
                positions=positions,
                total_value=Decimal('38250.0'),
                cash=Decimal('5000.0'),
                total_pnl=Decimal('1875.0'),
                last_updated=datetime.now()
            )
            portfolios.append(portfolio)
        
        # Optimizar portfolios concurrentemente
        results = []
        
        async def optimize_portfolio(portfolio: Portfolio):
            try:
                optimized = await self.portfolio_service.optimize_portfolio(portfolio)
                results.append({
                    'portfolio_id': portfolio.id,
                    'optimized': optimized,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'portfolio_id': portfolio.id,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(optimize_portfolio(portfolio)) for portfolio in portfolios]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(portfolios)
        
        # Verificar que todas las optimizaciones fueron exitosas
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(portfolios)
    
    @pytest.mark.asyncio
    async def test_concurrent_portfolio_reporting(self):
        """Test generación concurrente de reportes de portfolio."""
        
        # Crear portfolios para reportar
        portfolios = []
        for i in range(8):
            positions = []
            for j in range(3):
                position = Position(
                    symbol=f"REPORT_{j}",
                    quantity=Decimal('200'),
                    average_price=Decimal('25.0'),
                    current_price=Decimal('30.0'),
                    unrealized_pnl=Decimal('1000.0'),
                    realized_pnl=Decimal('500.0')
                )
                positions.append(position)
            
            portfolio = Portfolio(
                id=f"report_portfolio_{i}",
                name=f"Report Portfolio {i}",
                positions=positions,
                total_value=Decimal('18000.0'),
                cash=Decimal('2000.0'),
                total_pnl=Decimal('4500.0'),
                last_updated=datetime.now()
            )
            portfolios.append(portfolio)
        
        # Generar reportes concurrentemente
        results = []
        
        async def generate_portfolio_report(portfolio: Portfolio):
            try:
                report = await self.portfolio_service.generate_portfolio_report(portfolio)
                results.append({
                    'portfolio_id': portfolio.id,
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
        tasks = [asyncio.create_task(generate_portfolio_report(portfolio)) for portfolio in portfolios]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(portfolios)
        
        # Verificar que todos los reportes se generaron correctamente
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(portfolios)
        
        # Verificar que los reportes contienen información válida
        for result in successful_results:
            report = result['report']
            assert 'summary' in report
            assert 'positions' in report
            assert 'performance' in report
    
    @pytest.mark.asyncio
    async def test_concurrent_portfolio_validation(self):
        """Test validación concurrente de portfolios."""
        
        # Crear portfolios con diferentes características de validación
        portfolios = []
        
        # Portfolios válidos
        for i in range(5):
            positions = []
            for j in range(2):
                position = Position(
                    symbol=f"VALID_{j}",
                    quantity=Decimal('100'),
                    average_price=Decimal('50.0'),
                    current_price=Decimal('55.0'),
                    unrealized_pnl=Decimal('500.0'),
                    realized_pnl=Decimal('0.0')
                )
                positions.append(position)
            
            portfolio = Portfolio(
                id=f"valid_portfolio_{i}",
                name=f"Valid Portfolio {i}",
                positions=positions,
                total_value=Decimal('11000.0'),
                cash=Decimal('1000.0'),
                total_pnl=Decimal('1000.0'),
                last_updated=datetime.now()
            )
            portfolios.append(portfolio)
        
        # Portfolios con problemas de validación
        invalid_portfolios = [
            Portfolio(
                id="invalid_portfolio_1",
                name="",  # Nombre vacío
                positions=[],
                total_value=Decimal('10000.0'),
                cash=Decimal('10000.0'),
                total_pnl=Decimal('0.0'),
                last_updated=datetime.now()
            ),
            Portfolio(
                id="invalid_portfolio_2",
                name="Invalid Portfolio",
                positions=[],
                total_value=Decimal('-1000.0'),  # Valor negativo
                cash=Decimal('10000.0'),
                total_pnl=Decimal('0.0'),
                last_updated=datetime.now()
            )
        ]
        
        all_portfolios = portfolios + invalid_portfolios
        
        # Validar portfolios concurrentemente
        results = []
        
        async def validate_portfolio(portfolio: Portfolio):
            try:
                is_valid = await self.portfolio_service.validate_portfolio(portfolio)
                results.append({
                    'portfolio_id': portfolio.id,
                    'is_valid': is_valid,
                    'portfolio': portfolio,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'portfolio_id': portfolio.id,
                    'is_valid': False,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(validate_portfolio(portfolio)) for portfolio in all_portfolios]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(all_portfolios)
        
        # Verificar que los portfolios válidos pasaron la validación
        valid_results = [r for r in results if r.get('is_valid', False)]
        assert len(valid_results) == 5
        
        # Verificar que los portfolios inválidos fallaron la validación
        invalid_results = [r for r in results if not r.get('is_valid', False)]
        assert len(invalid_results) == 2
