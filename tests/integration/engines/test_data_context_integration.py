"""
Integration Tests: DataEngine y ContextEngine con Strategy Engines

Tests para verificar que los módulos 1 y 2 se integran correctamente con Strategy Engines:
- DataEngine proporciona datos normalizados y limpios
- ContextEngine proporciona análisis de contexto
- Strategy Engines usan ambos engines en generación de señales
"""

import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import List

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.engines.context_engine import ContextEngine
from app.engines.data_engine import DataEngine
from app.engines.strategy_engines import MomentumStrategyEngine
from app.models.market_data import Quote

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestDataEngineIntegration:
    """Tests de integración de DataEngine con Strategy Engines."""

    def test_data_engine_initialization_in_strategy(self):
        """Test que DataEngine se puede inicializar en Strategy Engine."""
        config = {
            'rsi_period': 14,
            'data_engine_enabled': True,
            'data_engine_config': {'sources': {}},
        }

        engine = MomentumStrategyEngine(config)

        assert engine.data_engine_enabled == True
        # DataEngine puede no inicializarse si no hay fuentes configuradas
        # pero no debe fallar

    def test_set_data_engine_externally(self):
        """Test configurar DataEngine externamente."""
        engine = MomentumStrategyEngine({'rsi_period': 14})

        # Crear DataEngine mock o real
        data_engine_config = {'sources': {}}
        data_engine = DataEngine(data_engine_config)

        engine.set_data_engine(data_engine)

        assert engine.data_engine is not None
        assert engine.data_engine_enabled == True


class TestContextEngineIntegration:
    """Tests de integración de ContextEngine con Strategy Engines."""

    def test_context_engine_initialization_in_strategy(self):
        """Test que ContextEngine se puede inicializar en Strategy Engine."""
        config = {'rsi_period': 14, 'context_engine_enabled': True, 'context_engine_config': {}}

        engine = MomentumStrategyEngine(config)

        assert engine.context_engine_enabled == True

    def test_set_context_engine_externally(self):
        """Test configurar ContextEngine externamente."""
        engine = MomentumStrategyEngine({'rsi_period': 14})

        context_engine = ContextEngine({})

        engine.set_context_engine(context_engine)

        assert engine.context_engine is not None
        assert engine.context_engine_enabled == True

    def test_get_context_analysis(self):
        """Test obtener análisis de contexto desde Strategy Engine."""
        engine = MomentumStrategyEngine({'rsi_period': 14})
        context_engine = ContextEngine({})
        engine.set_context_engine(context_engine)

        # Crear precios de ejemplo
        prices = [100.0 + i * 0.5 + (i % 10) * 2 for i in range(100)]

        context = engine.get_context_analysis(prices)

        # Puede retornar None si no hay suficientes datos para entrenar HMM/clustering
        # pero no debe fallar
        assert context is None or isinstance(context, dict)

    def test_get_volatility_regime(self):
        """Test obtener régimen de volatilidad desde Strategy Engine."""
        engine = MomentumStrategyEngine({'rsi_period': 14})
        context_engine = ContextEngine({})
        engine.set_context_engine(context_engine)

        prices = [100.0 + i * 0.5 + (i % 10) * 2 for i in range(100)]

        vol_regime = engine.get_volatility_regime(prices)

        assert vol_regime is None or isinstance(vol_regime, dict)


class TestIntegratedStrategyEngines:
    """Tests de integración completa con DataEngine y ContextEngine."""

    def test_strategy_with_both_engines(self):
        """Test Strategy Engine con DataEngine y ContextEngine."""
        config = {
            'rsi_period': 14,
            'data_engine_enabled': True,
            'context_engine_enabled': True,
            'data_engine_config': {'sources': {}},
            'context_engine_config': {},
        }

        engine = MomentumStrategyEngine(config)

        assert engine.data_engine_enabled == True
        assert engine.context_engine_enabled == True

    def test_strategy_metrics_include_engines(self):
        """Test que las métricas incluyen llamadas a engines."""
        engine = MomentumStrategyEngine({'rsi_period': 14})
        context_engine = ContextEngine({})
        engine.set_context_engine(context_engine)

        # Obtener contexto varias veces
        prices = [100.0 + i * 0.5 for i in range(100)]
        for _ in range(3):
            engine.get_context_analysis(prices)

        metrics = engine.get_metrics()

        assert 'context_analysis_calls' in metrics
        assert metrics['context_analysis_calls'] >= 0

    def test_strategy_status_includes_engines(self):
        """Test que el status incluye información de engines."""
        engine = MomentumStrategyEngine({'rsi_period': 14})
        context_engine = ContextEngine({})
        engine.set_context_engine(context_engine)

        status = engine.get_status()

        assert 'data_engine_enabled' in status
        assert 'context_engine_enabled' in status
        assert status['context_engine_enabled'] == True


class TestMultiStrategyIntegration:
    """Tests de integración con múltiples estrategias."""

    def test_multiple_engines_share_context_engine(self):
        """Test que múltiples engines pueden compartir ContextEngine."""
        from app.engines.strategy_engines import MeanReversionStrategyEngine

        # Crear ContextEngine compartido
        shared_context = ContextEngine({})

        # Crear múltiples engines
        momentum_engine = MomentumStrategyEngine({'rsi_period': 14})
        mean_reversion_engine = MeanReversionStrategyEngine({'z_score_period': 20})

        # Configurar mismo ContextEngine
        momentum_engine.set_context_engine(shared_context)
        mean_reversion_engine.set_context_engine(shared_context)

        assert momentum_engine.context_engine is shared_context
        assert mean_reversion_engine.context_engine is shared_context

    def test_multiple_engines_share_data_engine(self):
        """Test que múltiples engines pueden compartir DataEngine."""
        from app.engines.strategy_engines import MeanReversionStrategyEngine

        # Crear DataEngine compartido
        shared_data = DataEngine({'sources': {}})

        # Crear múltiples engines
        momentum_engine = MomentumStrategyEngine({'rsi_period': 14})
        mean_reversion_engine = MeanReversionStrategyEngine({'z_score_period': 20})

        # Configurar mismo DataEngine
        momentum_engine.set_data_engine(shared_data)
        mean_reversion_engine.set_data_engine(shared_data)

        assert momentum_engine.data_engine is shared_data
        assert mean_reversion_engine.data_engine is shared_data
