"""
Tests de concurrencia para market data simultáneo.

Este módulo contiene tests para validar que el sistema maneja correctamente
múltiples actualizaciones de market data simultáneas sin race conditions.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import threading
import time

from app.models.market_data import Quote, MarketData
from app.services.market_data_service import MarketDataService
from app.core.centralized_config import get_config


class TestMarketDataConcurrency:
    """Tests de concurrencia para market data."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.market_data_service = MarketDataService()
        self.config = get_config()
    
    @pytest.mark.asyncio
    async def test_concurrent_quote_updates(self):
        """Test actualizaciones concurrentes de quotes."""
        
        # Crear múltiples quotes para actualizar
        quotes = []
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA", "META", "NFLX"]
        
        for symbol in symbols:
            quote = Quote(
                symbol=symbol,
                bid_price=Decimal('100.0'),
                ask_price=Decimal('101.0'),
                bid_size=Decimal('1000'),
                ask_size=Decimal('1000'),
                timestamp=datetime.now(),
                volume=Decimal('1000000'),
                last_price=Decimal('100.5')
            )
            quotes.append(quote)
        
        # Actualizar quotes concurrentemente
        results = []
        
        async def update_quote(quote: Quote):
            try:
                result = await self.market_data_service.update_quote(quote)
                results.append({
                    'symbol': quote.symbol,
                    'result': result,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'symbol': quote.symbol,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(update_quote(quote)) for quote in quotes]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(symbols)
        
        # Verificar que todas las actualizaciones fueron exitosas
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(symbols)
        
        # Verificar que no hay errores de concurrencia
        error_results = [r for r in results if 'error' in r]
        assert len(error_results) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_market_data_streaming(self):
        """Test streaming concurrente de market data."""
        
        # Simular múltiples streams de market data
        streams = []
        symbols = ["BTC", "ETH", "ADA", "SOL", "DOT"]
        
        for symbol in symbols:
            stream_data = []
            for i in range(10):  # 10 updates por stream
                data = MarketData(
                    symbol=symbol,
                    price=Decimal('100.0') + Decimal(str(i)),
                    volume=Decimal('1000000'),
                    timestamp=datetime.now(),
                    high=Decimal('110.0'),
                    low=Decimal('90.0'),
                    open=Decimal('95.0'),
                    close=Decimal('105.0')
                )
                stream_data.append(data)
            streams.append(stream_data)
        
        # Procesar streams concurrentemente
        results = []
        
        async def process_stream(symbol: str, stream_data: List[MarketData]):
            try:
                processed = await self.market_data_service.process_stream(symbol, stream_data)
                results.append({
                    'symbol': symbol,
                    'processed_count': len(processed),
                    'success': True
                })
            except Exception as e:
                results.append({
                    'symbol': symbol,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(process_stream(symbol, stream_data)) 
                for symbol, stream_data in zip(symbols, streams)]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(symbols)
        
        # Verificar que todos los streams se procesaron correctamente
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(symbols)
        
        # Verificar que cada stream procesó 10 updates
        for result in successful_results:
            assert result['processed_count'] == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_market_data_aggregation(self):
        """Test agregación concurrente de market data."""
        
        # Crear datos de mercado para agregar
        market_data_batches = []
        symbols = ["AGG1", "AGG2", "AGG3", "AGG4"]
        
        for symbol in symbols:
            batch = []
            for i in range(20):  # 20 datos por símbolo
                data = MarketData(
                    symbol=symbol,
                    price=Decimal('100.0') + Decimal(str(i * 0.1)),
                    volume=Decimal('1000000'),
                    timestamp=datetime.now(),
                    high=Decimal('110.0'),
                    low=Decimal('90.0'),
                    open=Decimal('95.0'),
                    close=Decimal('105.0')
                )
                batch.append(data)
            market_data_batches.append((symbol, batch))
        
        # Agregar datos concurrentemente
        results = []
        
        async def aggregate_market_data(symbol: str, data_batch: List[MarketData]):
            try:
                aggregated = await self.market_data_service.aggregate_market_data(symbol, data_batch)
                results.append({
                    'symbol': symbol,
                    'aggregated': aggregated,
                    'data_count': len(data_batch),
                    'success': True
                })
            except Exception as e:
                results.append({
                    'symbol': symbol,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(aggregate_market_data(symbol, batch)) 
                for symbol, batch in market_data_batches]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(symbols)
        
        # Verificar que todas las agregaciones fueron exitosas
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(symbols)
        
        # Verificar que cada agregación procesó 20 datos
        for result in successful_results:
            assert result['data_count'] == 20
    
    @pytest.mark.asyncio
    async def test_concurrent_market_data_caching(self):
        """Test caching concurrente de market data."""
        
        # Crear datos para cachear
        cache_operations = []
        symbols = ["CACHE1", "CACHE2", "CACHE3", "CACHE4", "CACHE5"]
        
        for symbol in symbols:
            for i in range(5):  # 5 operaciones por símbolo
                data = MarketData(
                    symbol=symbol,
                    price=Decimal('100.0') + Decimal(str(i)),
                    volume=Decimal('1000000'),
                    timestamp=datetime.now(),
                    high=Decimal('110.0'),
                    low=Decimal('90.0'),
                    open=Decimal('95.0'),
                    close=Decimal('105.0')
                )
                cache_operations.append((symbol, data))
        
        # Cachear datos concurrentemente
        results = []
        
        async def cache_market_data(symbol: str, data: MarketData):
            try:
                cached = await self.market_data_service.cache_market_data(symbol, data)
                results.append({
                    'symbol': symbol,
                    'cached': cached,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'symbol': symbol,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(cache_market_data(symbol, data)) 
                for symbol, data in cache_operations]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(cache_operations)
        
        # Verificar que todas las operaciones de cache fueron exitosas
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(cache_operations)
    
    def test_thread_safety_market_data_updates(self):
        """Test thread safety en actualizaciones de market data."""
        
        results = []
        errors = []
        
        def update_market_data_thread(symbol: str):
            try:
                # Simular actualización de market data
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
                
                # Simular procesamiento síncrono
                result = self.market_data_service._update_market_data_sync(data)
                results.append(result)
                
            except Exception as e:
                errors.append(str(e))
        
        # Crear múltiples threads
        threads = []
        symbols = [f"THREAD_{i}" for i in range(20)]
        
        for symbol in symbols:
            thread = threading.Thread(target=update_market_data_thread, args=(symbol,))
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
        symbols_processed = [r.get('symbol') for r in results if isinstance(r, dict)]
        assert len(set(symbols_processed)) == 20
    
    @pytest.mark.asyncio
    async def test_concurrent_market_data_validation(self):
        """Test validación concurrente de market data."""
        
        # Crear datos de mercado con diferentes características de validación
        market_data_list = []
        
        # Datos válidos
        for i in range(8):
            data = MarketData(
                symbol=f"VALID_{i}",
                price=Decimal('100.0'),
                volume=Decimal('1000000'),
                timestamp=datetime.now(),
                high=Decimal('110.0'),
                low=Decimal('90.0'),
                open=Decimal('95.0'),
                close=Decimal('105.0')
            )
            market_data_list.append(data)
        
        # Datos con problemas de validación
        invalid_data = [
            MarketData(
                symbol="",  # Símbolo vacío
                price=Decimal('100.0'),
                volume=Decimal('1000000'),
                timestamp=datetime.now(),
                high=Decimal('110.0'),
                low=Decimal('90.0'),
                open=Decimal('95.0'),
                close=Decimal('105.0')
            ),
            MarketData(
                symbol="INVALID",
                price=Decimal('-100.0'),  # Precio negativo
                volume=Decimal('1000000'),
                timestamp=datetime.now(),
                high=Decimal('110.0'),
                low=Decimal('90.0'),
                open=Decimal('95.0'),
                close=Decimal('105.0')
            )
        ]
        
        all_data = market_data_list + invalid_data
        
        # Validar datos concurrentemente
        results = []
        
        async def validate_market_data(data: MarketData):
            try:
                is_valid = await self.market_data_service.validate_market_data(data)
                results.append({
                    'symbol': data.symbol,
                    'is_valid': is_valid,
                    'data': data,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'symbol': data.symbol,
                    'is_valid': False,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(validate_market_data(data)) for data in all_data]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(all_data)
        
        # Verificar que los datos válidos pasaron la validación
        valid_results = [r for r in results if r.get('is_valid', False)]
        assert len(valid_results) == 8
        
        # Verificar que los datos inválidos fallaron la validación
        invalid_results = [r for r in results if not r.get('is_valid', False)]
        assert len(invalid_results) == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_market_data_filtering(self):
        """Test filtrado concurrente de market data."""
        
        # Crear datos de mercado para filtrar
        market_data_list = []
        
        # Datos que deberían pasar el filtro
        for i in range(6):
            data = MarketData(
                symbol=f"FILTER_{i}",
                price=Decimal('100.0'),
                volume=Decimal('2000000'),  # Volumen alto
                timestamp=datetime.now(),
                high=Decimal('110.0'),
                low=Decimal('90.0'),
                open=Decimal('95.0'),
                close=Decimal('105.0')
            )
            market_data_list.append(data)
        
        # Datos que deberían ser filtrados
        for i in range(4):
            data = MarketData(
                symbol=f"FILTER_OUT_{i}",
                price=Decimal('100.0'),
                volume=Decimal('100000'),  # Volumen bajo
                timestamp=datetime.now(),
                high=Decimal('110.0'),
                low=Decimal('90.0'),
                open=Decimal('95.0'),
                close=Decimal('105.0')
            )
            market_data_list.append(data)
        
        # Filtrar datos concurrentemente
        results = []
        
        async def filter_market_data(data: MarketData):
            try:
                passed_filter = await self.market_data_service.filter_market_data(data)
                results.append({
                    'symbol': data.symbol,
                    'passed_filter': passed_filter,
                    'data': data,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'symbol': data.symbol,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(filter_market_data(data)) for data in market_data_list]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(market_data_list)
        
        # Verificar que los datos con volumen alto pasaron el filtro
        passed_results = [r for r in results if r.get('passed_filter', False)]
        assert len(passed_results) >= 6
        
        # Verificar que los datos con volumen bajo fueron filtrados
        filtered_results = [r for r in results if not r.get('passed_filter', False)]
        assert len(filtered_results) >= 4
    
    @pytest.mark.asyncio
    async def test_concurrent_market_data_persistence(self):
        """Test persistencia concurrente de market data."""
        
        # Crear datos para persistir
        market_data_list = []
        symbols = ["PERSIST1", "PERSIST2", "PERSIST3", "PERSIST4"]
        
        for symbol in symbols:
            for i in range(5):  # 5 datos por símbolo
                data = MarketData(
                    symbol=symbol,
                    price=Decimal('100.0') + Decimal(str(i)),
                    volume=Decimal('1000000'),
                    timestamp=datetime.now(),
                    high=Decimal('110.0'),
                    low=Decimal('90.0'),
                    open=Decimal('95.0'),
                    close=Decimal('105.0')
                )
                market_data_list.append(data)
        
        # Persistir datos concurrentemente
        results = []
        
        async def persist_market_data(data: MarketData):
            try:
                persisted = await self.market_data_service.persist_market_data(data)
                results.append({
                    'symbol': data.symbol,
                    'persisted': persisted,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'symbol': data.symbol,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(persist_market_data(data)) for data in market_data_list]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(market_data_list)
        
        # Verificar que todos los datos se persistieron correctamente
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(market_data_list)
        
        # Verificar que no hay errores de concurrencia
        error_results = [r for r in results if 'error' in r]
        assert len(error_results) == 0
