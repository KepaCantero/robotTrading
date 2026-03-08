"""
Portfolio, Signal, and Asset services - TASK-15: Refactorización de Servicios

Este módulo exporta los servicios refactorizados con motores especializados
y gestores centralizados para mejor mantenibilidad.
"""

# Nuevos gestores centralizados
from .api_circuit_breaker import CircuitBreakerManager, CircuitBreakerType

# Asset & Market Universe
from .asset_identification import AssetIdentificationService, get_asset_identification_service
from .circuit_breaker_manager import (
    CircuitBreakerConfig,
    CircuitBreakerLevel,
    CircuitBreakerManager as MarketHaltManager,
    MarketState,
    TradingStatus,
)
from .market_universe_loader import MarketUniverseLoader, get_market_universe_loader
from .market_universe_orchestrator import (
    MarketUniverseOrchestrator,
    get_market_universe_orchestrator,
)
from .momentum_analysis import MomentumAnalysisService, get_momentum_analysis_service
from .portfolio_risk_manager import PortfolioRiskManager, RiskLevel, RiskViolation
from .portfolio_service import PortfolioService
from .position_sizing_engine import PositionSizingEngine

# Nuevos motores especializados
from .signal_evaluation_engine import SignalEvaluationEngine
from .signal_execution_engine import SignalExecutionEngine
from .signal_scorer import SignalScorerService

# Servicios principales
__all__ = [
    "PortfolioService",
    "SignalScorerService",
    "MomentumAnalysisService",
    "get_momentum_analysis_service",
    # Motores especializados
    "SignalEvaluationEngine",
    "PositionSizingEngine",
    "SignalExecutionEngine",
    # Gestores centralizados
    "CircuitBreakerManager",  # API circuit breaker (resilience pattern)
    "CircuitBreakerType",
    "MarketHaltManager",  # Market halt detection (renamed from v2)
    "CircuitBreakerConfig",
    "CircuitBreakerLevel",
    "MarketState",
    "TradingStatus",
    "PortfolioRiskManager",
    "RiskLevel",
    "RiskViolation",
    # Asset & Market Universe
    "AssetIdentificationService",
    "get_asset_identification_service",
    "MarketUniverseLoader",
    "get_market_universe_loader",
    "MarketUniverseOrchestrator",
    "get_market_universe_orchestrator",
]
