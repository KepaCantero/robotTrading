"""
Tests de concurrencia para órdenes simultáneas.

Este módulo contiene tests para validar que el sistema maneja correctamente
múltiples órdenes simultáneas sin race conditions.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import threading
import time

from app.models.order import Order, OrderType, OrderSide, OrderStatus
from app.models.portfolio import Portfolio, Position
from app.services.paper_trading_service import PaperTradingService
from app.services.portfolio_service import PortfolioService
from app.core.centralized_config import get_config


class TestOrderConcurrency:
    """Tests de concurrencia para órdenes."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.paper_trading_service = PaperTradingService()
        self.portfolio_service = PortfolioService()
        self.config = get_config()
    
    @pytest.mark.asyncio
    async def test_concurrent_order_execution(self):
        """Test ejecución concurrente de múltiples órdenes."""
        
        # Crear múltiples órdenes simultáneas
        orders = []
        for i in range(10):
            order = Order(
                id=f"order_{i}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('10'),
                price=Decimal('150.0'),
                timestamp=datetime.now(),
                status=OrderStatus.PENDING
            )
            orders.append(order)
        
        # Ejecutar órdenes concurrentemente
        tasks = []
        results = []
        
        async def execute_order(order: Order):
            try:
                result = await self.paper_trading_service.execute_order(order)
                results.append(result)
                return result
            except Exception as e:
                results.append(f"Error: {str(e)}")
                return None
        
        # Crear tareas concurrentes
        for order in orders:
            task = asyncio.create_task(execute_order(order))
            tasks.append(task)
        
        # Esperar a que todas las tareas terminen
        await asyncio.gather(*tasks)
        
        # Verificar que todas las órdenes se procesaron
        assert len(results) == 10
        
        # Verificar que no hay duplicados o pérdidas
        successful_results = [r for r in results if isinstance(r, dict) and 'order_id' in r]
        assert len(successful_results) == 10
        
        # Verificar que los IDs son únicos
        order_ids = [r['order_id'] for r in successful_results]
        assert len(set(order_ids)) == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_order_cancellation(self):
        """Test cancelación concurrente de órdenes."""
        
        # Crear órdenes
        orders = []
        for i in range(5):
            order = Order(
                id=f"cancel_order_{i}",
                symbol="GOOGL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal('5'),
                price=Decimal('2800.0'),
                timestamp=datetime.now(),
                status=OrderStatus.PENDING
            )
            orders.append(order)
        
        # Ejecutar órdenes y cancelaciones concurrentemente
        results = []
        
        async def execute_and_cancel(order: Order):
            try:
                # Ejecutar orden
                execution_result = await self.paper_trading_service.execute_order(order)
                
                # Cancelar inmediatamente
                cancel_result = await self.paper_trading_service.cancel_order(order.id)
                
                results.append({
                    'order_id': order.id,
                    'execution': execution_result,
                    'cancellation': cancel_result
                })
                
            except Exception as e:
                results.append(f"Error: {str(e)}")
        
        # Ejecutar concurrentemente
        tasks = [asyncio.create_task(execute_and_cancel(order)) for order in orders]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == 5
        successful_results = [r for r in results if isinstance(r, dict)]
        assert len(successful_results) == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_portfolio_updates(self):
        """Test actualizaciones concurrentes del portfolio."""
        
        # Crear múltiples operaciones de portfolio
        operations = []
        for i in range(20):
            operation = {
                'symbol': f"SYMBOL_{i % 5}",  # 5 símbolos diferentes
                'side': OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                'quantity': Decimal('1'),
                'price': Decimal('100.0'),
                'timestamp': datetime.now()
            }
            operations.append(operation)
        
        # Ejecutar operaciones concurrentemente
        results = []
        
        async def update_portfolio(operation: Dict[str, Any]):
            try:
                # Simular actualización de portfolio
                result = await self.portfolio_service.update_position(
                    symbol=operation['symbol'],
                    side=operation['side'],
                    quantity=operation['quantity'],
                    price=operation['price'],
                    timestamp=operation['timestamp']
                )
                results.append(result)
            except Exception as e:
                results.append(f"Error: {str(e)}")
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(update_portfolio(op)) for op in operations]
        await asyncio.gather(*tasks)
        
        # Verificar que todas las operaciones se procesaron
        assert len(results) == 20
        
        # Verificar que no hay errores de concurrencia
        error_results = [r for r in results if isinstance(r, str) and "Error" in r]
        assert len(error_results) == 0
    
    def test_thread_safety_order_processing(self):
        """Test thread safety en procesamiento de órdenes."""
        
        results = []
        errors = []
        
        def process_order(order_id: str):
            try:
                order = Order(
                    id=order_id,
                    symbol="MSFT",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=Decimal('1'),
                    price=Decimal('300.0'),
                    timestamp=datetime.now(),
                    status=OrderStatus.PENDING
                )
                
                # Simular procesamiento síncrono
                result = self.paper_trading_service._process_order_sync(order)
                results.append(result)
                
            except Exception as e:
                errors.append(str(e))
        
        # Crear múltiples threads
        threads = []
        for i in range(15):
            thread = threading.Thread(target=process_order, args=(f"thread_order_{i}",))
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
        order_ids = [r.get('order_id') for r in results if isinstance(r, dict)]
        assert len(set(order_ids)) == 15
    
    @pytest.mark.asyncio
    async def test_concurrent_order_status_updates(self):
        """Test actualizaciones concurrentes de estado de órdenes."""
        
        # Crear órdenes
        orders = []
        for i in range(8):
            order = Order(
                id=f"status_order_{i}",
                symbol="TSLA",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('2'),
                price=Decimal('800.0'),
                timestamp=datetime.now(),
                status=OrderStatus.PENDING
            )
            orders.append(order)
        
        # Actualizar estados concurrentemente
        results = []
        
        async def update_order_status(order: Order, new_status: OrderStatus):
            try:
                # Simular actualización de estado
                order.status = new_status
                result = await self.paper_trading_service.update_order_status(
                    order.id, new_status
                )
                results.append({
                    'order_id': order.id,
                    'old_status': OrderStatus.PENDING,
                    'new_status': new_status,
                    'result': result
                })
            except Exception as e:
                results.append(f"Error: {str(e)}")
        
        # Crear tareas con diferentes estados
        tasks = []
        statuses = [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]
        
        for i, order in enumerate(orders):
            status = statuses[i % len(statuses)]
            task = asyncio.create_task(update_order_status(order, status))
            tasks.append(task)
        
        # Ejecutar concurrentemente
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == 8
        successful_results = [r for r in results if isinstance(r, dict)]
        assert len(successful_results) == 8
    
    @pytest.mark.asyncio
    async def test_concurrent_order_validation(self):
        """Test validación concurrente de órdenes."""
        
        # Crear órdenes con diferentes características
        orders = []
        
        # Órdenes válidas
        for i in range(5):
            order = Order(
                id=f"valid_order_{i}",
                symbol="AMZN",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('1'),
                price=Decimal('3200.0'),
                timestamp=datetime.now(),
                status=OrderStatus.PENDING
            )
            orders.append(order)
        
        # Órdenes con problemas potenciales
        invalid_orders = [
            Order(
                id="invalid_order_1",
                symbol="INVALID_SYMBOL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('0'),  # Cantidad inválida
                price=Decimal('100.0'),
                timestamp=datetime.now(),
                status=OrderStatus.PENDING
            ),
            Order(
                id="invalid_order_2",
                symbol="NVDA",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('1000000'),  # Cantidad excesiva
                price=Decimal('500.0'),
                timestamp=datetime.now(),
                status=OrderStatus.PENDING
            )
        ]
        
        all_orders = orders + invalid_orders
        
        # Validar órdenes concurrentemente
        results = []
        
        async def validate_order(order: Order):
            try:
                result = await self.paper_trading_service.validate_order(order)
                results.append({
                    'order_id': order.id,
                    'is_valid': result,
                    'order': order
                })
            except Exception as e:
                results.append({
                    'order_id': order.id,
                    'is_valid': False,
                    'error': str(e),
                    'order': order
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(validate_order(order)) for order in all_orders]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(all_orders)
        
        # Verificar que las órdenes válidas pasaron la validación
        valid_results = [r for r in results if r.get('is_valid', False)]
        assert len(valid_results) == 5
        
        # Verificar que las órdenes inválidas fallaron la validación
        invalid_results = [r for r in results if not r.get('is_valid', False)]
        assert len(invalid_results) == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_order_matching(self):
        """Test matching concurrente de órdenes."""
        
        # Crear órdenes de compra y venta que deberían hacer match
        buy_orders = []
        sell_orders = []
        
        for i in range(5):
            # Órdenes de compra
            buy_order = Order(
                id=f"buy_order_{i}",
                symbol="BTC",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal('0.1'),
                price=Decimal('50000.0'),
                timestamp=datetime.now(),
                status=OrderStatus.PENDING
            )
            buy_orders.append(buy_order)
            
            # Órdenes de venta
            sell_order = Order(
                id=f"sell_order_{i}",
                symbol="BTC",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal('0.1'),
                price=Decimal('50000.0'),
                timestamp=datetime.now(),
                status=OrderStatus.PENDING
            )
            sell_orders.append(sell_order)
        
        all_orders = buy_orders + sell_orders
        
        # Procesar órdenes concurrentemente para matching
        results = []
        
        async def process_order_for_matching(order: Order):
            try:
                result = await self.paper_trading_service.process_order_matching(order)
                results.append({
                    'order_id': order.id,
                    'matched': result.get('matched', False),
                    'result': result
                })
            except Exception as e:
                results.append({
                    'order_id': order.id,
                    'matched': False,
                    'error': str(e)
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(process_order_for_matching(order)) for order in all_orders]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(all_orders)
        
        # Verificar que algunas órdenes hicieron match
        matched_results = [r for r in results if r.get('matched', False)]
        assert len(matched_results) > 0
        
        # Verificar que no hay errores de concurrencia
        error_results = [r for r in results if 'error' in r]
        assert len(error_results) == 0
