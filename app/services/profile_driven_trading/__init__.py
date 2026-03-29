"""
Profile-Driven Trading Algorithm Orchestrator

This module orchestrates the complete trading lifecycle from investor profile to trade execution.
It integrates all components of the algorithmic trading system into a unified workflow.

Main Components:
- ProfileDrivenTradingOrchestrator: Main orchestrator class
- WorkflowManager: Pipeline execution and state management
- SignalIntegrator: Multi-source signal integration
- Models: Data classes for configuration and results

Usage:
    from app.services.profile_driven_trading import (
        ProfileDrivenTradingOrchestrator,
        OrchestratorConfig,
        TradingResult,
    )

    config = OrchestratorConfig(
        enable_rl_signals=True,
        enable_tax_optimization=True,
        enable_backtest_validation=True,
        enable_risk_gates=True,
        auto_execute_trades=False,  # Dry-run by default
    )

    orchestrator = ProfileDrivenTradingOrchestrator(config)
    result = await orchestrator.execute_trading_lifecycle(input_profile)
"""

from .models import (
    ExecutionResult,
    OrchestratorConfig,
    RiskValidationResult,
    StageResult,
    TradingResult,
)
from .orchestrator import ProfileDrivenTradingOrchestrator
from .profile_strategy_mapper import (
    ProfileStrategyMapper,
    StrategyMapping,
    create_profile_mapper,
    get_capital_tier,
    map_profile_to_strategies,
)
from .signal_integrator import SignalIntegrator, SignalSet
from .workflow_manager import PipelineResult, WorkflowManager

__all__ = [
    "ExecutionResult",
    # Data models
    "OrchestratorConfig",
    "PipelineResult",
    # Main orchestrator
    "ProfileDrivenTradingOrchestrator",
    # Profile strategy mapping
    "ProfileStrategyMapper",
    "RiskValidationResult",
    # Signal integration
    "SignalIntegrator",
    "SignalSet",
    "StageResult",
    "StrategyMapping",
    "TradingResult",
    # Workflow management
    "WorkflowManager",
    "create_profile_mapper",
    "get_capital_tier",
    "map_profile_to_strategies",
]

__version__ = "1.0.0"
__author__ = "AlgoTrading System"
