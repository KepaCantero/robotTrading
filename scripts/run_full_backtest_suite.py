#!/usr/bin/env python3
"""
Full Backtest Suite for Single Investor Profile.

Runs ALL 10 backtesting types for a single investor profile with FULL
framework compliance.

Usage:
    python scripts/run_full_backtest_suite.py --capital 100000 --risk medio --horizon 12 --objetivo balanced_growth
    python scripts/run_full_backtest_suite.py --profile-json path/to/profile.json

Backtest Types (10 total - ALL ENABLED):
1.  Baseline        - Reference performance without ML
2.  Learning Engines - supervised, deep, reinforcement, transformer (ALL 4)
3.  Walk-Forward    - Time-window optimization
4.  Monte Carlo     - Stress test with simulations
5.  Grid Search     - Full parameter space exploration
6.  Ablation        - Individual module impact
7.  Out-of-Sample   - Forward validation (70/15/15 split)
8.  Multi-Strategy  - All 4 strategies
9.  Regime Test     - Market regime performance (HMM detection)
10. Hyperparameter  - Optuna optimization

Learning Engines:
- supervised: scikit-learn (Random Forest, XGBoost, LightGBM, CatBoost)
- deep: PyTorch (LSTM, GRU) - uses SubprocessLearningEngineWrapper for macOS
- reinforcement: stable-baselines3 (PPO, DQN) - uses SubprocessLearningEngineWrapper for macOS
- transformer: PyTorch Transformer - uses SubprocessLearningEngineWrapper for macOS
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import os
import random
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path

import numpy as np
import yaml

# Thread safety configuration (CRITICAL - must be BEFORE imports)
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
    TaxResidence,
)


# ============================================================================
# Enums and Data Classes
# ============================================================================


class BacktestType(Enum):
    """Types of backtesting methods."""

    BASELINE = "baseline"
    LEARNING_ENGINES = "learning_engines"
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"
    GRID_SEARCH = "grid_search"
    ABLATION = "ablation"
    OUT_OF_SAMPLE = "out_of_sample"
    MULTI_STRATEGY = "multi_strategy"
    REGIME_TEST = "regime_test"
    HYPERPARAMETER = "hyperparameter"


class TestStatus(Enum):
    """Test execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


@dataclass
class BacktestResult:
    """Result of a single backtest type execution."""

    backtest_type: BacktestType
    status: TestStatus
    execution_time: float = 0.0
    error_message: str | None = None
    # Performance metrics
    total_pnl: float | None = None
    return_pct: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    win_rate: float | None = None
    total_trades: int | None = None
    # Silent failure detection
    has_valid_metrics: bool = False
    nan_count: int = 0
    # Additional details
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "backtest_type": self.backtest_type.value,
            "status": self.status.value,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "metrics": {
                "total_pnl": self.total_pnl,
                "return_pct": self.return_pct,
                "sharpe_ratio": self.sharpe_ratio,
                "max_drawdown": self.max_drawdown,
                "win_rate": self.win_rate,
                "total_trades": self.total_trades,
            },
            "has_valid_metrics": self.has_valid_metrics,
            "nan_count": self.nan_count,
            "details": self.details,
        }


@dataclass
class FullSuiteResult:
    """Complete result of running all 10 backtest types."""

    run_id: str
    profile_id: str
    profile_details: dict
    test_period: str
    start_time: str
    end_time: str | None = None
    total_time: float = 0.0
    results: list[BacktestResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    warnings: int = 0

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        total = self.passed + self.failed
        return self.passed / total if total > 0 else 0.0

    def add_result(self, result: BacktestResult) -> None:
        """Add a test result."""
        self.results.append(result)
        if result.status == TestStatus.PASSED:
            self.passed += 1
        elif result.status == TestStatus.FAILED:
            self.failed += 1
        elif result.status == TestStatus.SKIPPED:
            self.skipped += 1
        elif result.status == TestStatus.WARNING:
            self.warnings += 1
            self.passed += 1

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "profile_id": self.profile_id,
            "profile_details": self.profile_details,
            "test_period": self.test_period,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_time_seconds": self.total_time,
            "summary": {
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "warnings": self.warnings,
                "pass_rate": self.pass_rate,
            },
            "results": [r.to_dict() for r in self.results],
        }


# ============================================================================
# Full Backtest Suite Runner
# ============================================================================


class FullBacktestSuite:
    """Runs all 10 backtest types for a single investor profile."""

    RANDOM_SEED: int = 42

    def __init__(
        self,
        profile: InputProfile,
        start_date: str,
        end_date: str,
        config_path: str | None = None,
        random_seed: int | None = None,
        output_dir: str = "results/full_suite",
    ):
        """Initialize the full backtest suite.

        Args:
            profile: Investor profile to test
            start_date: Test start date (YYYY-MM-DD)
            end_date: Test end date (YYYY-MM-DD)
            config_path: Path to base configuration YAML (optional)
            random_seed: Random seed for reproducibility
            output_dir: Directory for output files
        """
        self._profile = profile
        self._start_date = start_date
        self._end_date = end_date
        self._config_path = config_path
        self._output_dir = Path(output_dir)
        self._run_id = uuid.uuid4().hex[:8]
        self._random_seed = random_seed or self.RANDOM_SEED

        # Configure reproducibility
        self._configure_reproducibility()

        # Create test configuration
        self._test_config_path = self._create_test_config()

        # Initialize runner
        self._runner: ComprehensiveBacktestRunner | None = None

        # Results
        self._result: FullSuiteResult | None = None

    def _configure_reproducibility(self) -> None:
        """Configure random seeds for reproducibility."""
        random.seed(self._random_seed)
        np.random.seed(self._random_seed)
        logging.info("Reproducibility configured with random_seed=%d", self._random_seed)

    def _create_test_config(self) -> str:
        """Create test configuration YAML with ALL backtest types enabled."""
        config = {
            "database": {"url": f"sqlite:///{self._output_dir}/test_results.db"},
            "output_dir": str(self._output_dir),
            "backtest_period": {
                "start_date": self._start_date,
                "end_date": self._end_date,
            },
            "input": {
                "symbols": [
                    "AAPL",
                    "MSFT",
                    "GOOGL",
                    "AMZN",
                    "TSLA",
                    "META",
                    "NVDA",
                    "JPM",
                    "JNJ",
                    "NEE",
                ],
                "start_date": self._start_date,
                "end_date": self._end_date,
                "source": "csv",
            },
            "backtest": {
                "stop_loss": 5.0,
                "take_profit": 10.0,
                "max_position_size": 0.10,
                "commission_per_trade": 0.0,
                "slippage": 0.1,
                "risk_free_rate": 0.02,
                "strategy_name": "momentum_modular",
            },
            "parallel_execution": {
                "enabled": False,
                "max_workers": 1,
            },
            # ALL 4 Learning Engines ENABLED
            "learning_engines": {
                "enabled": True,
                "supervised": {
                    "enabled": True,
                    "lookahead_days": 5,
                    "parameters": {
                        "algorithm": "random_forest",
                        "n_estimators": 50,
                        "max_depth": 10,
                        "train_test_split": 0.7,
                    },
                },
                "deep": {
                    "enabled": True,  # ENABLED - uses SubprocessLearningEngineWrapper
                    "parameters": {
                        "architecture": "lstm",
                        "sequence_length": 30,
                        "hidden_size": 32,
                        "num_layers": 2,
                        "epochs": 20,
                        "batch_size": 16,
                        "learning_rate": 0.001,
                    },
                },
                "reinforcement": {
                    "enabled": True,  # ENABLED - uses SubprocessLearningEngineWrapper
                    "parameters": {
                        "algorithm": "ppo",
                        "training_steps": 10000,
                        "learning_rate": 0.0003,
                    },
                },
                "transformer": {
                    "enabled": True,  # ENABLED - uses SubprocessLearningEngineWrapper
                    "parameters": {
                        "nhead": 4,
                        "num_layers": 2,
                        "dim_feedforward": 128,
                        "dropout": 0.1,
                        "epochs": 20,
                        "batch_size": 16,
                        "learning_rate": 0.0001,
                    },
                },
            },
            # Module filters
            "modules": {
                "filters": {
                    "ema_filter": {
                        "enabled": True,
                        "parameters": {
                            "fast_period": {"default": 12},
                            "slow_period": {"default": 26},
                        },
                    },
                    "rsi_filter": {
                        "enabled": True,
                        "parameters": {
                            "period": {"default": 14},
                            "buy_threshold": {"default": 30},
                            "sell_threshold": {"default": 70},
                        },
                    },
                    "stoch_rsi_filter": {
                        "enabled": True,
                        "parameters": {
                            "rsi_period": {"default": 14},
                            "stoch_period": {"default": 14},
                            "oversold_threshold": {"default": 20},
                            "overbought_threshold": {"default": 80},
                        },
                    },
                    "momentum_filter": {
                        "enabled": True,
                        "parameters": {
                            "threshold": {"default": 0.015},
                        },
                    },
                    "volume_filter": {
                        "enabled": True,
                        "parameters": {
                            "threshold": {"default": 1.1},
                        },
                    },
                    "atr_filter": {
                        "enabled": True,
                        "parameters": {
                            "min_threshold": {"default": 0.006},
                        },
                    },
                }
            },
            # ALL 10 Backtest Types ENABLED
            "backtests": {
                "baseline": {
                    "enabled": True,
                    "description": "Reference performance without ML",
                },
                "learning_engines": {
                    "enabled": True,
                    "description": "All 4 learning engines (supervised, deep, reinforcement, transformer)",
                },
                "walk_forward": {
                    "enabled": True,
                    "description": "Time-window optimization",
                    "min_train_days": 60,
                    "test_size_days": 20,
                    "step_size_days": 30,
                    "n_folds": 3,
                    "train_pct": 0.70,
                    "test_pct": 0.30,
                },
                "monte_carlo": {
                    "enabled": True,
                    "description": "Stress test with simulations",
                    "num_simulations": 100,  # Reduced for faster testing
                    "volatility_multiplier": {
                        "default": 1.0,
                        "min": 0.5,
                        "max": 2.0,
                    },
                    "confidence_levels": [0.95, 0.99],
                },
                "grid_search": {
                    "enabled": True,
                    "description": "Parameter space exploration",
                    "parameters": {
                        "rsi_buy_threshold": [25, 30, 35],
                        "rsi_sell_threshold": [65, 70, 75],
                        "ema_fast": [10, 12, 15],
                        "ema_slow": [20, 26, 30],
                    },
                    "optimization_metric": "sharpe_ratio",
                    "max_combinations": 50,
                },
                "ablation": {
                    "enabled": True,
                    "description": "Individual module impact",
                    "modules": [
                        "ema_filter",
                        "rsi_filter",
                        "stoch_rsi_filter",
                        "momentum_filter",
                        "volume_filter",
                        "atr_filter",
                    ],
                    "baseline_modules": "all",
                },
                "out_of_sample": {
                    "enabled": True,
                    "description": "Forward validation (70/15/15 split)",
                    "train_ratio": 0.70,
                    "val_ratio": 0.15,
                    "test_ratio": 0.15,
                    "min_test_size": 30,
                },
                "multi_strategy": {
                    "enabled": True,
                    "description": "All 4 strategies",
                    "strategies": [
                        "modular_momentum",
                        "momentum",
                        "mean_reversion",
                        "pairs_trading",
                    ],
                    "allocation_method": "equal_weight",
                    "rebalance_frequency": "monthly",
                },
                "regime_test": {
                    "enabled": True,
                    "description": "Market regime performance (HMM detection)",
                    "detection_method": "hmm",
                    "n_regimes": 3,
                    "min_regime_samples": 30,
                },
                "hyperparameter_optimization": {
                    "enabled": True,
                    "description": "Optuna optimization",
                    "optimizer": "optuna",
                    "n_trials": 20,  # Reduced for faster testing
                    "timeout": 600,
                    "sampler": "TPE",
                    "pruner": "median",
                    "direction": "maximize",
                    "metric": "sharpe_ratio",
                },
            },
            "reporting": {
                "output_directory": str(self._output_dir / "reports"),
                "generate_html": True,
                "generate_json": True,
            },
            "random_seed": self._random_seed,
        }

        # Create output directory
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Write config
        config_path = self._output_dir / f"config_{self._run_id}.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        logging.info("Test configuration written to: %s", config_path)
        return str(config_path)

    def _initialize_runner(self) -> None:
        """Initialize the backtest runner."""
        if self._runner is None:
            self._runner = ComprehensiveBacktestRunner(self._test_config_path)

    def _run_single_backtest(self, bt_type: BacktestType) -> BacktestResult:
        """Run a single backtest type."""
        start_time = time.time()

        try:
            result_data = None

            if bt_type == BacktestType.BASELINE:
                result_data = self._runner.run_baseline_backtest()

            elif bt_type == BacktestType.LEARNING_ENGINES:
                result_data = self._runner.run_learning_engines_backtest()

            elif bt_type == BacktestType.WALK_FORWARD:
                wf_config = self._runner.raw_config.get('backtests', {}).get('walk_forward', {})
                if not wf_config.get('enabled', False):
                    return BacktestResult(
                        backtest_type=bt_type,
                        status=TestStatus.SKIPPED,
                        execution_time=time.time() - start_time,
                        error_message="Walk-forward not enabled",
                    )
                result_data = self._runner.run_walk_forward_backtest()

            elif bt_type == BacktestType.MONTE_CARLO:
                mc_config = self._runner.raw_config.get('backtests', {}).get('monte_carlo', {})
                if not mc_config.get('enabled', False):
                    return BacktestResult(
                        backtest_type=bt_type,
                        status=TestStatus.SKIPPED,
                        execution_time=time.time() - start_time,
                        error_message="Monte Carlo not enabled",
                    )
                result_data = self._runner.run_monte_carlo_backtest()

            elif bt_type == BacktestType.GRID_SEARCH:
                gs_config = self._runner.raw_config.get('backtests', {}).get('grid_search', {})
                if not gs_config.get('enabled', False):
                    return BacktestResult(
                        backtest_type=bt_type,
                        status=TestStatus.SKIPPED,
                        execution_time=time.time() - start_time,
                        error_message="Grid search not enabled",
                    )
                result_data = self._runner.run_grid_search_backtest()

            elif bt_type == BacktestType.ABLATION:
                ab_config = self._runner.raw_config.get('backtests', {}).get('ablation', {})
                if not ab_config.get('enabled', False):
                    return BacktestResult(
                        backtest_type=bt_type,
                        status=TestStatus.SKIPPED,
                        execution_time=time.time() - start_time,
                        error_message="Ablation not enabled",
                    )
                result_data = self._runner.run_ablation_backtest()

            elif bt_type == BacktestType.OUT_OF_SAMPLE:
                oos_config = self._runner.raw_config.get('backtests', {}).get('out_of_sample', {})
                if not oos_config.get('enabled', False):
                    return BacktestResult(
                        backtest_type=bt_type,
                        status=TestStatus.SKIPPED,
                        execution_time=time.time() - start_time,
                        error_message="Out-of-sample not enabled",
                    )
                result_data = self._runner.run_out_of_sample_backtest()

            elif bt_type == BacktestType.MULTI_STRATEGY:
                ms_config = self._runner.raw_config.get('backtests', {}).get('multi_strategy', {})
                if not ms_config.get('enabled', False):
                    return BacktestResult(
                        backtest_type=bt_type,
                        status=TestStatus.SKIPPED,
                        execution_time=time.time() - start_time,
                        error_message="Multi-strategy not enabled",
                    )
                result_data = self._runner.run_multi_strategy_backtest()

            elif bt_type == BacktestType.REGIME_TEST:
                rt_config = self._runner.raw_config.get('backtests', {}).get('regime_test', {})
                if not rt_config.get('enabled', False):
                    return BacktestResult(
                        backtest_type=bt_type,
                        status=TestStatus.SKIPPED,
                        execution_time=time.time() - start_time,
                        error_message="Regime test not enabled",
                    )
                result_data = self._runner.run_regime_test_backtest()

            elif bt_type == BacktestType.HYPERPARAMETER:
                hp_config = self._runner.raw_config.get('backtests', {}).get(
                    'hyperparameter_optimization', {}
                )
                if not hp_config.get('enabled', False):
                    return BacktestResult(
                        backtest_type=bt_type,
                        status=TestStatus.SKIPPED,
                        execution_time=time.time() - start_time,
                        error_message="Hyperparameter optimization not enabled",
                    )
                # Use Optuna optimization (new implementation)
                result_data = self._runner.run_optuna_optimization()

            # Process results
            if result_data:
                # Handle list results (e.g., learning engines returns list)
                if isinstance(result_data, list) and len(result_data) > 0:
                    # Aggregate metrics from list
                    total_pnl = sum(
                        r.get('total_pnl', 0) or 0 for r in result_data if isinstance(r, dict)
                    )
                    sharpe_values = [
                        r.get('sharpe_ratio', 0)
                        for r in result_data
                        if isinstance(r, dict) and r.get('sharpe_ratio')
                    ]
                    sharpe_ratio = (
                        sum(sharpe_values) / len(sharpe_values) if sharpe_values else None
                    )

                    # Detect NaN values
                    nan_count = 0
                    for r in result_data:
                        if isinstance(r, dict):
                            for val in r.values():
                                if isinstance(val, float) and math.isnan(val):
                                    nan_count += 1

                    return BacktestResult(
                        backtest_type=bt_type,
                        status=TestStatus.WARNING if nan_count > 0 else TestStatus.PASSED,
                        execution_time=time.time() - start_time,
                        total_pnl=total_pnl,
                        sharpe_ratio=sharpe_ratio,
                        has_valid_metrics=nan_count == 0,
                        nan_count=nan_count,
                        details={
                            "results_count": len(result_data),
                            "results": result_data[:3],
                        },  # First 3 results
                    )

                # Handle single dict result
                elif isinstance(result_data, dict):
                    # Detect NaN values
                    nan_count = sum(
                        1 for v in result_data.values() if isinstance(v, float) and math.isnan(v)
                    )

                    return BacktestResult(
                        backtest_type=bt_type,
                        status=TestStatus.WARNING if nan_count > 0 else TestStatus.PASSED,
                        execution_time=time.time() - start_time,
                        total_pnl=result_data.get('total_pnl'),
                        return_pct=result_data.get('return_pct'),
                        sharpe_ratio=result_data.get('sharpe_ratio'),
                        max_drawdown=result_data.get('max_drawdown'),
                        win_rate=result_data.get('win_rate'),
                        total_trades=result_data.get('total_trades'),
                        has_valid_metrics=nan_count == 0,
                        nan_count=nan_count,
                        details=result_data,
                    )

            # No results returned
            return BacktestResult(
                backtest_type=bt_type,
                status=TestStatus.FAILED,
                execution_time=time.time() - start_time,
                error_message="No results returned",
            )

        except Exception as e:
            logging.error("Exception in %s: %s", bt_type.value, e, exc_info=True)
            return BacktestResult(
                backtest_type=bt_type,
                status=TestStatus.FAILED,
                execution_time=time.time() - start_time,
                error_message=str(e),
            )

    def run_all(self) -> FullSuiteResult:
        """Run all 10 backtest types for the investor profile.

        Returns:
            FullSuiteResult with all backtest results
        """
        # Initialize result
        profile_details = {
            "capital_initial": str(self._profile.capital_initial),
            "objetivo_inversion": self._profile.objetivo_inversion.value,
            "risk_tolerance": self._profile.risk_tolerance.value,
            "investment_horizon": self._profile.investment_horizon,
            "tax_residence": self._profile.tax_residence.country_name,
        }

        self._result = FullSuiteResult(
            run_id=self._run_id,
            profile_id=self._profile.input_id,
            profile_details=profile_details,
            test_period=f"{self._start_date} to {self._end_date}",
            start_time=datetime.now().isoformat(),
        )

        # Log start
        logging.info("=" * 80)
        logging.info("FULL BACKTEST SUITE - Starting")
        logging.info("=" * 80)
        logging.info("Run ID: %s", self._run_id)
        logging.info("Profile ID: %s", self._profile.input_id)
        logging.info("Profile Details:")
        logging.info("  Capital: %s", self._profile.capital_initial)
        logging.info("  Objective: %s", self._profile.objetivo_inversion.value)
        logging.info("  Risk Tolerance: %s", self._profile.risk_tolerance.value)
        logging.info("  Horizon: %d months", self._profile.investment_horizon)
        logging.info("Test Period: %s to %s", self._start_date, self._end_date)
        logging.info("Backtest Types: 10 total")
        logging.info("=" * 80)

        # Initialize runner
        self._initialize_runner()

        # Run all backtest types in order
        backtest_order = [
            BacktestType.BASELINE,
            BacktestType.LEARNING_ENGINES,
            BacktestType.WALK_FORWARD,
            BacktestType.MONTE_CARLO,
            BacktestType.GRID_SEARCH,
            BacktestType.ABLATION,
            BacktestType.OUT_OF_SAMPLE,
            BacktestType.MULTI_STRATEGY,
            BacktestType.REGIME_TEST,
            BacktestType.HYPERPARAMETER,
        ]

        for i, bt_type in enumerate(backtest_order, 1):
            logging.info("")
            logging.info("[%d/10] Running %s...", i, bt_type.value)

            result = self._run_single_backtest(bt_type)
            self._result.add_result(result)

            # Log result
            status_icon = {
                TestStatus.PASSED: "✅",
                TestStatus.WARNING: "⚠️",
                TestStatus.SKIPPED: "⏭️",
                TestStatus.FAILED: "❌",
            }.get(result.status, "❓")

            logging.info(
                "  %s %s: %.2fs | Sharpe: %s | PnL: %s",
                status_icon,
                result.status.value,
                result.execution_time,
                f"{result.sharpe_ratio:.2f}" if result.sharpe_ratio else "N/A",
                f"${result.total_pnl:.2f}" if result.total_pnl else "N/A",
            )

            if result.error_message:
                logging.info("  Error: %s", result.error_message)

            # Garbage collection between tests
            gc.collect()

        # Finalize
        self._result.end_time = datetime.now().isoformat()
        self._result.total_time = sum(r.execution_time for r in self._result.results)

        # Print summary
        self._print_summary()

        # Save results
        self._save_results()

        return self._result

    def _print_summary(self) -> None:
        """Print final summary."""
        if not self._result:
            return

        logging.info("")
        logging.info("=" * 80)
        logging.info("FULL BACKTEST SUITE - FINAL SUMMARY")
        logging.info("=" * 80)
        logging.info("Run ID: %s", self._result.run_id)
        logging.info("Profile ID: %s", self._result.profile_id)
        logging.info("Total Time: %.2f seconds", self._result.total_time)
        logging.info("")
        logging.info("Results Summary:")
        logging.info("  Passed:   %d", self._result.passed)
        logging.info("  Failed:   %d", self._result.failed)
        logging.info("  Skipped:  %d", self._result.skipped)
        logging.info("  Warnings: %d", self._result.warnings)
        logging.info("  Pass Rate: %.1f%%", 100 * self._result.pass_rate)
        logging.info("")
        logging.info("Results by Backtest Type:")

        for r in self._result.results:
            status_icon = {
                TestStatus.PASSED: "✅",
                TestStatus.WARNING: "⚠️",
                TestStatus.SKIPPED: "⏭️",
                TestStatus.FAILED: "❌",
            }.get(r.status, "❓")

            logging.info(
                "  %s %-20s | Sharpe: %-8s | PnL: %-12s | Time: %.2fs",
                status_icon,
                r.backtest_type.value,
                f"{r.sharpe_ratio:.2f}" if r.sharpe_ratio else "N/A",
                f"${r.total_pnl:.2f}" if r.total_pnl else "N/A",
                r.execution_time,
            )

        logging.info("=" * 80)

    def _save_results(self) -> None:
        """Save results to JSON file."""
        if not self._result:
            return

        output_file = self._output_dir / f"results_{self._run_id}.json"
        with open(output_file, 'w') as f:
            json.dump(self._result.to_dict(), f, indent=2, default=str)

        logging.info("Results saved to: %s", output_file)


# ============================================================================
# Profile Creation Helpers
# ============================================================================


def create_profile(
    capital: float,
    objetivo: str,
    riesgo: str,
    horizon: int,
    country_code: str = "US",
) -> InputProfile:
    """Create an InputProfile from parameters.

    Args:
        capital: Initial capital amount
        objetivo: Investment objective (spanish value)
        riesgo: Risk tolerance (bajo, medio, alto)
        horizon: Investment horizon in months
        country_code: Tax residence country code

    Returns:
        InputProfile instance
    """
    # Map objective strings to enum
    objetivo_map = {
        "maximizar_capital": ObjectivoInversion.MAXIMIZAR_CAPITAL,
        "maximizar_dividendos": ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
        "capital_preservation": ObjectivoInversion.CAPITAL_PRESERVATION,
        "balanced_growth": ObjectivoInversion.BALANCED_GROWTH,
        "income_generation": ObjectivoInversion.INCOME_GENERATION,
    }

    # Map risk strings to enum
    riesgo_map = {
        "bajo": RiskTolerance.BAJO,
        "medio": RiskTolerance.MEDIO,
        "alto": RiskTolerance.ALTO,
    }

    # Create tax residence
    country_names = {
        "US": "United States",
        "ES": "Spain",
        "MX": "Mexico",
    }

    tax_residence = TaxResidence(
        country_code=country_code,
        country_name=country_names.get(country_code, country_code),
        base_currency="USD" if country_code == "US" else "EUR",
    )

    # Create profile
    run_id = uuid.uuid4().hex[:8]
    profile = InputProfile(
        input_id=f"profile_{run_id}_{objetivo}_{riesgo}_h{horizon}",
        capital_initial=Decimal(str(capital)),
        objetivo_inversion=objetivo_map.get(objetivo.lower(), ObjectivoInversion.BALANCED_GROWTH),
        risk_tolerance=riesgo_map.get(riesgo.lower(), RiskTolerance.MEDIO),
        investment_horizon=horizon,
        tax_residence=tax_residence,
    )

    return profile


def load_profile_from_json(json_path: str) -> InputProfile:
    """Load an InputProfile from a JSON file.

    Args:
        json_path: Path to JSON file

    Returns:
        InputProfile instance
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    objetivo_map = {
        "maximizar_capital": ObjectivoInversion.MAXIMIZAR_CAPITAL,
        "maximizar_dividendos": ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
        "capital_preservation": ObjectivoInversion.CAPITAL_PRESERVATION,
        "balanced_growth": ObjectivoInversion.BALANCED_GROWTH,
        "income_generation": ObjectivoInversion.INCOME_GENERATION,
    }

    riesgo_map = {
        "bajo": RiskTolerance.BAJO,
        "medio": RiskTolerance.MEDIO,
        "alto": RiskTolerance.ALTO,
    }

    return InputProfile(
        input_id=data.get("input_id", f"profile_{uuid.uuid4().hex[:8]}"),
        capital_initial=Decimal(str(data.get("capital_initial", 100000))),
        objetivo_inversion=objetivo_map.get(
            data.get("objetivo_inversion", "balanced_growth").lower(),
            ObjectivoInversion.BALANCED_GROWTH,
        ),
        risk_tolerance=riesgo_map.get(
            data.get("risk_tolerance", "medio").lower(), RiskTolerance.MEDIO
        ),
        investment_horizon=data.get("investment_horizon", 12),
        tax_residence=TaxResidence(
            country_code=data.get("tax_residence", {}).get("country_code", "US"),
            country_name=data.get("tax_residence", {}).get("country_name", "United States"),
            base_currency=data.get("tax_residence", {}).get("base_currency", "USD"),
        ),
    )


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run full backtest suite for a single investor profile"
    )

    # Profile options
    parser.add_argument(
        "--capital", type=float, default=100000, help="Initial capital (default: 100000)"
    )
    parser.add_argument(
        "--objetivo",
        type=str,
        default="balanced_growth",
        choices=[
            "maximizar_capital",
            "maximizar_dividendos",
            "capital_preservation",
            "balanced_growth",
            "income_generation",
        ],
        help="Investment objective (default: balanced_growth)",
    )
    parser.add_argument(
        "--risk",
        type=str,
        default="medio",
        choices=["bajo", "medio", "alto"],
        help="Risk tolerance (default: medio)",
    )
    parser.add_argument(
        "--horizon", type=int, default=12, help="Investment horizon in months (default: 12)"
    )
    parser.add_argument(
        "--profile-json", type=str, default=None, help="Path to JSON file with profile definition"
    )

    # Date options
    parser.add_argument(
        "--start-date", type=str, default=None, help="Start date (YYYY-MM-DD, default: 1 year ago)"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="End date (YYYY-MM-DD, default: today)"
    )
    parser.add_argument(
        "--days", type=int, default=365, help="Number of days to test (default: 365)"
    )

    # Other options
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/full_suite",
        help="Output directory (default: results/full_suite)",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument("--config", type=str, default=None, help="Path to base configuration YAML")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging (show all signals)"
    )

    args = parser.parse_args()

    # Configure logging with rotation to prevent massive log files
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create rotating file handler (10MB max, keep 3 backups)
    log_file = output_dir / "full_suite.log"
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=3)  # 10MB
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-8s] %(message)s"))

    # Console handler with less verbose format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler],
    )

    # Reduce verbosity from noisy external libraries (unless verbose mode)
    if not args.verbose:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("app.engines").setLevel(logging.WARNING)
        logging.getLogger("app.core.compliance_engine").setLevel(logging.WARNING)
        logging.getLogger("app.backtesting.core.executor").setLevel(logging.WARNING)
        # Suppress individual signal logs
        logging.getLogger("app.strategies").setLevel(logging.WARNING)

    # Determine dates
    if args.end_date:
        end_date = datetime.fromisoformat(args.end_date).date()
    else:
        end_date = datetime.now().date()

    if args.start_date:
        start_date = datetime.fromisoformat(args.start_date).date()
    else:
        start_date = end_date - timedelta(days=args.days)

    # Create profile
    if args.profile_json:
        logging.info("Loading profile from: %s", args.profile_json)
        profile = load_profile_from_json(args.profile_json)
    else:
        profile = create_profile(
            capital=args.capital,
            objetivo=args.objetivo,
            riesgo=args.risk,
            horizon=args.horizon,
        )

    logging.info("Created profile: %s", profile.input_id)

    # Run full suite
    try:
        suite = FullBacktestSuite(
            profile=profile,
            start_date=str(start_date),
            end_date=str(end_date),
            config_path=args.config,
            random_seed=args.seed,
            output_dir=args.output_dir,
        )

        result = suite.run_all()

        # Return exit code
        return 0 if result.failed == 0 else 1

    except Exception as e:
        logging.error("Fatal error: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
