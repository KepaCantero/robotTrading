"""
Backtesting Runners Module

Extracted from comprehensive_backtest_runner.py for SRP compliance.

Provides modular components for backtesting:
- RegimeAnalyzer: Market regime detection and analysis
- MonteCarloSimulator: Monte Carlo simulation for stress testing
- ResultAggregator: Result aggregation and persistence
"""

from app.backtesting.runners.monte_carlo_simulator import (
    MonteCarloSimulator,
    generate_monte_carlo_quotes,
)
from app.backtesting.runners.regime_analyzer import RegimeAnalyzer, detect_regimes
from app.backtesting.runners.result_aggregator import (
    ResultAggregator,
    aggregate_results,
    save_results,
)

__all__ = [
    # Regime Analysis
    "RegimeAnalyzer",
    "detect_regimes",
    # Monte Carlo Simulation
    "MonteCarloSimulator",
    "generate_monte_carlo_quotes",
    # Result Aggregation
    "ResultAggregator",
    "aggregate_results",
    "save_results",
]
