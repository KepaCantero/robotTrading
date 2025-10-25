"""
Tests de concurrencia para señales simultáneas.

Este módulo contiene tests para validar que el sistema maneja correctamente
múltiples señales simultáneas sin race conditions.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import threading
import time

from app.models.signal import Signal, SignalType, SignalStrength
from app.services.signal_scorer import SignalScorer
from app.services.momentum_analysis import MomentumAnalysis
from app.core.centralized_config import get_config


class TestSignalConcurrency:
    """Tests de concurrencia para señales."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.signal_scorer_service = SignalScorer()
        self.momentum_strategy = MomentumAnalysis()
        self.config = get_config()
    
    @pytest.mark.asyncio
    async def test_concurrent_signal_generation(self):
        """Test generación concurrente de múltiples señales."""
        
        # Crear datos de mercado para múltiples símbolos
        market_data = []
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        
        for symbol in symbols:
            data = {
                'symbol': symbol,
                'price': Decimal('100.0'),
                'volume': Decimal('1000000'),
                'timestamp': datetime.now(),
                'rsi': Decimal('50.0'),
                'macd': Decimal('0.1'),
                'sma_20': Decimal('99.0'),
                'sma_50': Decimal('98.0')
            }
            market_data.append(data)
        
        # Generar señales concurrentemente
        results = []
        
        async def generate_signal(data: Dict[str, Any]):
            try:
                signal = await self.momentum_strategy.generate_signal(data)
                results.append({
                    'symbol': data['symbol'],
                    'signal': signal,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'symbol': data['symbol'],
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(generate_signal(data)) for data in market_data]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(symbols)
        
        # Verificar que todas las señales se generaron correctamente
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(symbols)
        
        # Verificar que no hay duplicados
        symbols_processed = [r['symbol'] for r in successful_results]
        assert len(set(symbols_processed)) == len(symbols)
    
    @pytest.mark.asyncio
    async def test_concurrent_signal_scoring(self):
        """Test scoring concurrente de múltiples señales."""
        
        # Crear señales para scoring
        signals = []
        for i in range(10):
            signal = Signal(
                id=f"signal_{i}",
                symbol=f"SYMBOL_{i % 5}",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=Decimal('0.7'),
                timestamp=datetime.now(),
                price=Decimal('100.0'),
                metadata={'rsi': Decimal('60.0'), 'volume': Decimal('1000000')}
            )
            signals.append(signal)
        
        # Score señales concurrentemente
        results = []
        
        async def score_signal(signal: Signal):
            try:
                score = await self.signal_scorer_service.score_signal(signal)
                results.append({
                    'signal_id': signal.id,
                    'score': score,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'signal_id': signal.id,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(score_signal(signal)) for signal in signals]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(signals)
        
        # Verificar que todas las señales se scorearon correctamente
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(signals)
        
        # Verificar que los scores son válidos
        for result in successful_results:
            score = result['score']
            assert isinstance(score, (int, float, Decimal))
            assert 0 <= float(score) <= 100
    
    @pytest.mark.asyncio
    async def test_concurrent_signal_filtering(self):
        """Test filtrado concurrente de señales."""
        
        # Crear señales con diferentes características
        signals = []
        
        # Señales que deberían pasar el filtro
        for i in range(5):
            signal = Signal(
                id=f"good_signal_{i}",
                symbol=f"GOOD_{i}",
                signal_type=SignalType.BUY,
                strength=SignalStrength.HIGH,
                confidence=Decimal('0.8'),
                timestamp=datetime.now(),
                price=Decimal('100.0'),
                metadata={'rsi': Decimal('30.0'), 'volume': Decimal('2000000')}
            )
            signals.append(signal)
        
        # Señales que deberían ser filtradas
        for i in range(3):
            signal = Signal(
                id=f"bad_signal_{i}",
                symbol=f"BAD_{i}",
                signal_type=SignalType.BUY,
                strength=SignalStrength.LOW,
                confidence=Decimal('0.3'),
                timestamp=datetime.now(),
                price=Decimal('100.0'),
                metadata={'rsi': Decimal('80.0'), 'volume': Decimal('100000')}
            )
            signals.append(signal)
        
        # Filtrar señales concurrentemente
        results = []
        
        async def filter_signal(signal: Signal):
            try:
                passed = await self.signal_scorer_service.filter_signal(signal)
                results.append({
                    'signal_id': signal.id,
                    'passed_filter': passed,
                    'signal': signal,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'signal_id': signal.id,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(filter_signal(signal)) for signal in signals]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(signals)
        
        # Verificar que las señales buenas pasaron el filtro
        passed_results = [r for r in results if r.get('passed_filter', False)]
        assert len(passed_results) >= 5  # Al menos las señales buenas
        
        # Verificar que las señales malas fueron filtradas
        filtered_results = [r for r in results if not r.get('passed_filter', False)]
        assert len(filtered_results) >= 3  # Al menos las señales malas
    
    @pytest.mark.asyncio
    async def test_concurrent_signal_ranking(self):
        """Test ranking concurrente de señales."""
        
        # Crear señales con diferentes scores
        signals = []
        for i in range(15):
            signal = Signal(
                id=f"rank_signal_{i}",
                symbol=f"RANK_{i % 3}",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=Decimal('0.5'),
                timestamp=datetime.now(),
                price=Decimal('100.0'),
                metadata={'score': Decimal(str(50 + i * 2))}  # Scores crecientes
            )
            signals.append(signal)
        
        # Rankear señales concurrentemente
        results = []
        
        async def rank_signal(signal: Signal):
            try:
                rank = await self.signal_scorer_service.rank_signal(signal)
                results.append({
                    'signal_id': signal.id,
                    'rank': rank,
                    'score': signal.metadata.get('score', 0),
                    'success': True
                })
            except Exception as e:
                results.append({
                    'signal_id': signal.id,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(rank_signal(signal)) for signal in signals]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(signals)
        
        # Verificar que todas las señales se rankearon correctamente
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(signals)
        
        # Verificar que los ranks son válidos
        ranks = [r['rank'] for r in successful_results]
        assert all(isinstance(rank, int) for rank in ranks)
        assert all(rank >= 1 for rank in ranks)
    
    def test_thread_safety_signal_processing(self):
        """Test thread safety en procesamiento de señales."""
        
        results = []
        errors = []
        
        def process_signal(signal_id: str):
            try:
                signal = Signal(
                    id=signal_id,
                    symbol="THREAD_TEST",
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    confidence=Decimal('0.6'),
                    timestamp=datetime.now(),
                    price=Decimal('100.0'),
                    metadata={'test': True}
                )
                
                # Simular procesamiento síncrono
                result = self.signal_scorer_service._process_signal_sync(signal)
                results.append(result)
                
            except Exception as e:
                errors.append(str(e))
        
        # Crear múltiples threads
        threads = []
        for i in range(12):
            thread = threading.Thread(target=process_signal, args=(f"thread_signal_{i}",))
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
        signal_ids = [r.get('signal_id') for r in results if isinstance(r, dict)]
        assert len(set(signal_ids)) == 12
    
    @pytest.mark.asyncio
    async def test_concurrent_signal_aggregation(self):
        """Test agregación concurrente de señales."""
        
        # Crear señales para agregar
        signals = []
        symbols = ["AGG1", "AGG2", "AGG3"]
        
        for symbol in symbols:
            for i in range(5):
                signal = Signal(
                    id=f"agg_{symbol}_{i}",
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    confidence=Decimal('0.6'),
                    timestamp=datetime.now(),
                    price=Decimal('100.0'),
                    metadata={'value': Decimal(str(i * 10))}
                )
                signals.append(signal)
        
        # Agregar señales concurrentemente
        results = []
        
        async def aggregate_signals(symbol: str, symbol_signals: List[Signal]):
            try:
                aggregated = await self.signal_scorer_service.aggregate_signals(symbol_signals)
                results.append({
                    'symbol': symbol,
                    'aggregated': aggregated,
                    'signal_count': len(symbol_signals),
                    'success': True
                })
            except Exception as e:
                results.append({
                    'symbol': symbol,
                    'error': str(e),
                    'success': False
                })
        
        # Agrupar señales por símbolo
        symbol_groups = {}
        for signal in signals:
            if signal.symbol not in symbol_groups:
                symbol_groups[signal.symbol] = []
            symbol_groups[signal.symbol].append(signal)
        
        # Crear tareas concurrentes para cada símbolo
        tasks = []
        for symbol, symbol_signals in symbol_groups.items():
            task = asyncio.create_task(aggregate_signals(symbol, symbol_signals))
            tasks.append(task)
        
        # Ejecutar concurrentemente
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(symbols)
        
        # Verificar que todas las agregaciones fueron exitosas
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(symbols)
        
        # Verificar que cada símbolo tiene 5 señales
        for result in successful_results:
            assert result['signal_count'] == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_signal_validation(self):
        """Test validación concurrente de señales."""
        
        # Crear señales con diferentes características de validación
        signals = []
        
        # Señales válidas
        for i in range(5):
            signal = Signal(
                id=f"valid_signal_{i}",
                symbol=f"VALID_{i}",
                signal_type=SignalType.BUY,
                strength=SignalStrength.HIGH,
                confidence=Decimal('0.8'),
                timestamp=datetime.now(),
                price=Decimal('100.0'),
                metadata={'valid': True}
            )
            signals.append(signal)
        
        # Señales con problemas de validación
        invalid_signals = [
            Signal(
                id="invalid_signal_1",
                symbol="",  # Símbolo vacío
                signal_type=SignalType.BUY,
                strength=SignalStrength.HIGH,
                confidence=Decimal('0.8'),
                timestamp=datetime.now(),
                price=Decimal('100.0'),
                metadata={'valid': False}
            ),
            Signal(
                id="invalid_signal_2",
                symbol="INVALID",
                signal_type=SignalType.BUY,
                strength=SignalStrength.HIGH,
                confidence=Decimal('1.5'),  # Confianza inválida (>1)
                timestamp=datetime.now(),
                price=Decimal('100.0'),
                metadata={'valid': False}
            )
        ]
        
        all_signals = signals + invalid_signals
        
        # Validar señales concurrentemente
        results = []
        
        async def validate_signal(signal: Signal):
            try:
                is_valid = await self.signal_scorer_service.validate_signal(signal)
                results.append({
                    'signal_id': signal.id,
                    'is_valid': is_valid,
                    'signal': signal,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'signal_id': signal.id,
                    'is_valid': False,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(validate_signal(signal)) for signal in all_signals]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(all_signals)
        
        # Verificar que las señales válidas pasaron la validación
        valid_results = [r for r in results if r.get('is_valid', False)]
        assert len(valid_results) == 5
        
        # Verificar que las señales inválidas fallaron la validación
        invalid_results = [r for r in results if not r.get('is_valid', False)]
        assert len(invalid_results) == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_signal_persistence(self):
        """Test persistencia concurrente de señales."""
        
        # Crear señales para persistir
        signals = []
        for i in range(20):
            signal = Signal(
                id=f"persist_signal_{i}",
                symbol=f"PERSIST_{i % 4}",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=Decimal('0.6'),
                timestamp=datetime.now(),
                price=Decimal('100.0'),
                metadata={'persist': True}
            )
            signals.append(signal)
        
        # Persistir señales concurrentemente
        results = []
        
        async def persist_signal(signal: Signal):
            try:
                result = await self.signal_scorer_service.persist_signal(signal)
                results.append({
                    'signal_id': signal.id,
                    'persisted': result,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'signal_id': signal.id,
                    'error': str(e),
                    'success': False
                })
        
        # Crear tareas concurrentes
        tasks = [asyncio.create_task(persist_signal(signal)) for signal in signals]
        await asyncio.gather(*tasks)
        
        # Verificar resultados
        assert len(results) == len(signals)
        
        # Verificar que todas las señales se persistieron correctamente
        successful_results = [r for r in results if r.get('success', False)]
        assert len(successful_results) == len(signals)
        
        # Verificar que no hay errores de concurrencia
        error_results = [r for r in results if 'error' in r]
        assert len(error_results) == 0
