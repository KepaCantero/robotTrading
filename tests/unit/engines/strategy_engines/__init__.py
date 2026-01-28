"""
Unit tests for strategy engines.

This package contains comprehensive unit tests for all strategy engines:
- BaseStrategyEngine: Abstract base class and core functionality
- MomentumStrategyEngine: Momentum-based trading signals
- MeanReversionStrategyEngine: Mean reversion signals
- PairsTradingStrategyEngine: Pairs trading with cointegration
- ModularMomentumStrategyEngine: Modular filter-based momentum

All tests follow TDD best practices with:
- Proper mocking of external dependencies
- Edge case coverage
- Clear test organization
- pytest.mark.unit decorator
"""

from .test_base import *
from .test_pairs_engine import *
from .test_momentum_engine import *
from .test_mean_reversion_engine import *
from .test_modular_momentum_engine import *

__all__ = [
    "TestBaseStrategyEngineInitialization",
    "TestLearningEngineIntegration",
    "TestCallbacks",
    "TestEnsembleWeights",
    "TestContextDataEngineIntegration",
    "TestSignalGeneration",
    "TestMetrics",
    "TestStatus",
    "TestAbstractMethods",
    "TestRepr",
    "TestEdgeCases",
]
