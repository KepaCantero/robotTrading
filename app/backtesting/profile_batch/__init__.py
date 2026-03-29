"""
Profile Batch Backtesting Module

This module provides refactored components for batch backtesting with profile-driven
strategy optimization. The architecture follows the Single Responsibility Principle
with separate classes for each concern:

- ProfileGenerator: Creates backtest profile combinations
- BaselineBacktestExecutor: Executes single backtests
- BayesianOptimizer: Hyperparameter optimization with Optuna
- WalkForwardValidator: Time-series cross-validation
- MonteCarloSimulator: Monte Carlo simulations
- OutOfSampleValidator: Out-of-sample testing
- OptimizationPipeline: Orchestrates optimization workflows
- ResultAggregator: Aggregates and analyzes results
- ReportGenerator: Generates HTML reports
- ProfileBatchBacktester: Main orchestrator

Usage:
    ```python
    from app.backtesting.profile_batch import ProfileBatchBacktester

    backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")
    profiles = backtester.generate_all_profiles()
    results = backtester.run_all_profiles(parallel=True)
    ```
"""

from .baseline_executor import BaselineBacktestExecutor
from .bayesian_optimizer import BayesianOptimizer
from .optimization_pipeline import OptimizationPipeline
from .optimization_validators import MonteCarloSimulator, OutOfSampleValidator, WalkForwardValidator
from .orchestrator import ProfileBatchBacktester
from .profile_generator import ProfileGenerator
from .report_generator import ReportGenerator
from .result_aggregator import ResultAggregator

__all__ = [
    "BaselineBacktestExecutor",
    "BayesianOptimizer",
    "MonteCarloSimulator",
    "OptimizationPipeline",
    "OutOfSampleValidator",
    "ProfileBatchBacktester",
    "ProfileGenerator",
    "ReportGenerator",
    "ResultAggregator",
    "WalkForwardValidator",
]
