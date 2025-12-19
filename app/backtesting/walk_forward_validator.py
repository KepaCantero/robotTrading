"""
Walk-Forward Validation & Stress Testing System (Task 3.5)

Comprehensive validation system including:
- Walk-forward validation with configurable windows
- Temporal cross-validation
- Stress testing with synthetic data generation
- Monte Carlo simulations
"""

import json
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import yaml

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, BacktestResult
from app.models.market_data import Quote

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Loading
# ============================================================================


def load_validation_config(config_path: str = "config/validation.yaml") -> Dict[str, Any]:
    """Load validation configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Validation config not found at {config_path}, using defaults")
        return get_default_config()

    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_default_config() -> Dict[str, Any]:
    """Return default validation configuration."""
    return {
        "walk_forward": {
            "enabled": True,
            "train_years": 4,
            "validation_years": 1,
            "step_years": 1,
            "min_windows": 3,
            "min_trades_per_window": 10,
            "thresholds": {
                "min_consistency": 0.6,
                "max_return_std": 0.3,
                "min_avg_sharpe": 0.5,
                "max_avg_drawdown": -0.20,
            },
        },
        "cross_validation": {
            "enabled": True,
            "n_folds": 5,
            "thresholds": {
                "min_consistency_score": 0.6,
                "max_return_variance": 0.25,
            },
        },
        "stress_testing": {
            "enabled": True,
            "n_scenarios": 100,
            "scenarios": {
                "flash_crash": {
                    "enabled": True,
                    "weight": 0.15,
                    "drop_percentage": -0.10,
                    "recovery_days": 5,
                },
                "high_volatility": {
                    "enabled": True,
                    "weight": 0.20,
                    "volatility_multiplier": 3.0,
                    "duration_days": 20,
                },
                "trending_bull": {
                    "enabled": True,
                    "weight": 0.15,
                    "daily_drift": 0.002,
                    "duration_days": 60,
                },
                "trending_bear": {
                    "enabled": True,
                    "weight": 0.15,
                    "daily_drift": -0.002,
                    "duration_days": 60,
                },
                "mean_reverting": {
                    "enabled": True,
                    "weight": 0.15,
                    "reversion_speed": 0.1,
                    "equilibrium_price": 100.0,
                },
                "gap_up": {"enabled": True, "weight": 0.10, "gap_percentage": 0.05, "n_gaps": 3},
                "gap_down": {"enabled": True, "weight": 0.10, "gap_percentage": -0.05, "n_gaps": 3},
            },
            "thresholds": {
                "max_scenario_drawdown": -0.30,
                "min_survival_rate": 0.80,
                "max_avg_loss": -0.15,
                "min_recovery_rate": 0.70,
            },
        },
        "synthetic_data": {
            "base_price": 100.0,
            "base_volume": 1000000,
            "price_model": "gbm",
            "annual_volatility": 0.20,
            "annual_drift": 0.05,
            "volume_noise": 0.30,
        },
        "monte_carlo": {
            "enabled": True,
            "n_simulations": 1000,
            "confidence_levels": [0.95, 0.99],
            "block_size": 20,
        },
    }


# ============================================================================
# Data Classes for Results
# ============================================================================


@dataclass
class ValidationWindow:
    """Represents a single validation window result."""

    window_id: int
    train_start: datetime
    train_end: datetime
    validate_start: datetime
    validate_end: datetime
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    win_rate: float
    passed: bool = True


@dataclass
class StressScenarioResult:
    """Result of a single stress test scenario."""

    scenario_type: str
    scenario_id: int
    total_return: float
    max_drawdown: float
    survived: bool
    recovered: bool
    final_capital: float
    trades_executed: int


@dataclass
class ValidationReport:
    """Complete validation report."""

    strategy_name: str
    timestamp: datetime
    walk_forward_results: Optional[Dict[str, Any]] = None
    cross_validation_results: Optional[Dict[str, Any]] = None
    stress_test_results: Optional[Dict[str, Any]] = None
    monte_carlo_results: Optional[Dict[str, Any]] = None
    overall_passed: bool = False
    summary: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Synthetic Data Generator
# ============================================================================


class SyntheticDataGenerator:
    """
    Generates synthetic market data for stress testing.

    Supports multiple price models:
    - GBM (Geometric Brownian Motion)
    - OU (Ornstein-Uhlenbeck for mean reversion)
    - Jump Diffusion
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config
        self.base_price = config.get("base_price", 100.0)
        self.base_volume = config.get("base_volume", 1000000)
        self.annual_volatility = config.get("annual_volatility", 0.20)
        self.annual_drift = config.get("annual_drift", 0.05)
        self.volume_noise = config.get("volume_noise", 0.30)

    def generate_gbm_prices(
        self,
        n_days: int,
        start_date: datetime,
        symbol: str = "SYNTH",
        drift: Optional[float] = None,
        volatility: Optional[float] = None,
    ) -> List[Quote]:
        """
        Generate prices using Geometric Brownian Motion.

        dS = mu*S*dt + sigma*S*dW
        """
        mu = drift if drift is not None else self.annual_drift / 252
        sigma = volatility if volatility is not None else self.annual_volatility / np.sqrt(252)

        prices = [self.base_price]
        for _ in range(n_days - 1):
            dW = np.random.normal(0, 1)
            price = prices[-1] * np.exp((mu - 0.5 * sigma**2) + sigma * dW)
            prices.append(max(price, 0.01))  # Floor at 0.01

        return self._prices_to_quotes(prices, start_date, symbol)

    def generate_ou_prices(
        self,
        n_days: int,
        start_date: datetime,
        symbol: str = "SYNTH",
        theta: float = 0.1,
        mu: Optional[float] = None,
    ) -> List[Quote]:
        """
        Generate mean-reverting prices using Ornstein-Uhlenbeck process.

        dX = theta*(mu - X)*dt + sigma*dW
        """
        mean = mu if mu is not None else self.base_price
        sigma = self.annual_volatility / np.sqrt(252)

        prices = [self.base_price]
        for _ in range(n_days - 1):
            dW = np.random.normal(0, 1)
            price = prices[-1] + theta * (mean - prices[-1]) + sigma * dW
            prices.append(max(price, 0.01))

        return self._prices_to_quotes(prices, start_date, symbol)

    def generate_jump_diffusion_prices(
        self,
        n_days: int,
        start_date: datetime,
        symbol: str = "SYNTH",
        jump_intensity: float = 0.1,
        jump_mean: float = 0.0,
        jump_std: float = 0.05,
    ) -> List[Quote]:
        """
        Generate prices with jumps (Merton jump-diffusion model).
        """
        mu = self.annual_drift / 252
        sigma = self.annual_volatility / np.sqrt(252)

        prices = [self.base_price]
        for _ in range(n_days - 1):
            dW = np.random.normal(0, 1)

            # Jump component
            jump = 0
            if np.random.random() < jump_intensity:
                jump = np.random.normal(jump_mean, jump_std)

            price = prices[-1] * np.exp((mu - 0.5 * sigma**2) + sigma * dW + jump)
            prices.append(max(price, 0.01))

        return self._prices_to_quotes(prices, start_date, symbol)

    def generate_flash_crash_scenario(
        self,
        n_days: int,
        start_date: datetime,
        symbol: str = "SYNTH",
        drop_pct: float = -0.10,
        recovery_days: int = 5,
    ) -> List[Quote]:
        """Generate a flash crash scenario."""
        # Normal trading until crash point (random between 30-70% of period)
        crash_day = int(n_days * random.uniform(0.3, 0.7))

        prices = [self.base_price]
        sigma = self.annual_volatility / np.sqrt(252) * 0.5  # Reduced volatility initially

        for i in range(n_days - 1):
            if i == crash_day:
                # Flash crash
                price = prices[-1] * (1 + drop_pct)
            elif crash_day < i < crash_day + recovery_days:
                # Recovery phase
                recovery_rate = (i - crash_day) / recovery_days
                target = prices[crash_day - 1]  # Pre-crash price
                price = prices[-1] + (target - prices[-1]) * recovery_rate * 0.3
                price += np.random.normal(0, sigma) * prices[-1]
            else:
                # Normal GBM
                dW = np.random.normal(0, 1)
                price = prices[-1] * np.exp(sigma * dW)

            prices.append(max(price, 0.01))

        return self._prices_to_quotes(prices, start_date, symbol)

    def generate_high_volatility_scenario(
        self,
        n_days: int,
        start_date: datetime,
        symbol: str = "SYNTH",
        volatility_multiplier: float = 3.0,
    ) -> List[Quote]:
        """Generate high volatility scenario."""
        return self.generate_gbm_prices(
            n_days,
            start_date,
            symbol,
            volatility=self.annual_volatility * volatility_multiplier / np.sqrt(252),
        )

    def generate_trending_scenario(
        self,
        n_days: int,
        start_date: datetime,
        symbol: str = "SYNTH",
        daily_drift: float = 0.002,
    ) -> List[Quote]:
        """Generate trending market scenario."""
        return self.generate_gbm_prices(
            n_days,
            start_date,
            symbol,
            drift=daily_drift,
        )

    def generate_gap_scenario(
        self,
        n_days: int,
        start_date: datetime,
        symbol: str = "SYNTH",
        gap_pct: float = 0.05,
        n_gaps: int = 3,
    ) -> List[Quote]:
        """Generate scenario with overnight gaps."""
        prices = [self.base_price]
        sigma = self.annual_volatility / np.sqrt(252)

        # Randomly place gaps
        gap_days = sorted(random.sample(range(1, n_days - 1), min(n_gaps, n_days - 2)))

        for i in range(n_days - 1):
            dW = np.random.normal(0, 1)
            price = prices[-1] * np.exp(sigma * dW)

            if i in gap_days:
                price *= 1 + gap_pct

            prices.append(max(price, 0.01))

        return self._prices_to_quotes(prices, start_date, symbol)

    def _prices_to_quotes(
        self,
        prices: List[float],
        start_date: datetime,
        symbol: str,
    ) -> List[Quote]:
        """Convert price list to Quote objects."""
        quotes = []

        for i, close_price in enumerate(prices):
            timestamp = start_date + timedelta(days=i)

            # Generate OHLC from close
            daily_range = close_price * self.annual_volatility / np.sqrt(252) / 2
            high = close_price + abs(np.random.normal(0, daily_range))
            low = close_price - abs(np.random.normal(0, daily_range))
            open_price = close_price + np.random.normal(0, daily_range * 0.5)

            # Ensure OHLC consistency
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)

            # Generate volume with noise
            volume = int(self.base_volume * (1 + np.random.normal(0, self.volume_noise)))
            volume = max(volume, 1000)

            quotes.append(
                Quote(
                    symbol=symbol,
                    timestamp=timestamp,
                    bid=Decimal(str(round(close_price * 0.9999, 2))),
                    ask=Decimal(str(round(close_price * 1.0001, 2))),
                    last=Decimal(str(round(close_price, 2))),
                    volume=Decimal(str(volume)),
                    open=Decimal(str(round(open_price, 2))),
                    high=Decimal(str(round(high, 2))),
                    low=Decimal(str(round(low, 2))),
                    close=Decimal(str(round(close_price, 2))),
                )
            )

        return quotes


# ============================================================================
# Walk-Forward Validator (Enhanced)
# ============================================================================


class WalkForwardValidator:
    """
    Walk-Forward Validation (Task 3.5).

    Trains on historical window, validates on subsequent period, then rolls forward.
    Now with configurable thresholds and comprehensive reporting.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_path: str = "config/validation.yaml",
    ):
        """
        Initialize walk-forward validator.

        Args:
            config: Configuration dict (overrides config_path if provided)
            config_path: Path to YAML config file
        """
        if config is None:
            full_config = load_validation_config(config_path)
            config = full_config.get("walk_forward", {})

        self.train_years = config.get("train_years", 4)
        self.validation_years = config.get("validation_years", 1)
        self.step_years = config.get("step_years", 1)
        self.min_windows = config.get("min_windows", 3)
        self.min_trades_per_window = config.get("min_trades_per_window", 10)
        self.thresholds = config.get(
            "thresholds",
            {
                "min_consistency": 0.6,
                "max_return_std": 0.3,
                "min_avg_sharpe": 0.5,
                "max_avg_drawdown": -0.20,
            },
        )

    def create_windows(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, datetime]]:
        """Create walk-forward windows."""
        windows = []
        current_start = start_date

        while current_start < end_date:
            train_end = current_start + timedelta(days=365 * self.train_years)
            validate_start = train_end
            validate_end = validate_start + timedelta(days=365 * self.validation_years)

            if validate_end > end_date:
                break

            windows.append(
                {
                    "train_start": current_start,
                    "train_end": train_end,
                    "validate_start": validate_start,
                    "validate_end": validate_end,
                }
            )

            current_start += timedelta(days=365 * self.step_years)

        return windows

    def validate_strategy(
        self,
        quotes: List[Quote],
        signals: List[Any],
        config: BacktestConfig,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Run walk-forward validation for a strategy.

        Returns dictionary with validation results and pass/fail status.
        """
        windows = self.create_windows(start_date, end_date)

        if len(windows) < self.min_windows:
            logger.warning(f"Insufficient windows: {len(windows)} < {self.min_windows}")
            return {
                "passed": False,
                "reason": f"Insufficient windows: {len(windows)} < {self.min_windows}",
                "windows": [],
            }

        results: List[ValidationWindow] = []

        for i, window in enumerate(windows):
            logger.info(
                f"Walk-forward window {i+1}/{len(windows)}: "
                f"Validate {window['validate_start'].strftime('%Y-%m-%d')} to "
                f"{window['validate_end'].strftime('%Y-%m-%d')}"
            )

            # Filter quotes for validation period
            validate_quotes = [
                q
                for q in quotes
                if window["validate_start"] <= q.timestamp <= window["validate_end"]
            ]

            # Filter signals for validation period
            validate_signals = [
                s
                for s in signals
                if hasattr(s, 'timestamp')
                and window["validate_start"] <= s.timestamp <= window["validate_end"]
            ]

            if not validate_quotes or not validate_signals:
                logger.warning(f"Window {i+1}: Insufficient data, skipping")
                continue

            # Run backtest on validation period
            backtester = SimpleBacktester(config)
            result = backtester.run_backtest(
                validate_quotes,
                validate_signals,
                window["validate_start"],
                window["validate_end"],
            )

            window_result = ValidationWindow(
                window_id=i + 1,
                train_start=window["train_start"],
                train_end=window["train_end"],
                validate_start=window["validate_start"],
                validate_end=window["validate_end"],
                total_return=float(result.total_return),
                sharpe_ratio=float(result.performance.sharpe_ratio or 0),
                max_drawdown=float(result.performance.max_drawdown_percentage or 0),
                total_trades=result.performance.total_trades,
                win_rate=float(result.performance.win_rate),
                passed=result.performance.total_trades >= self.min_trades_per_window,
            )
            results.append(window_result)

        if not results:
            return {
                "passed": False,
                "reason": "No valid windows completed",
                "windows": [],
            }

        # Calculate aggregated metrics
        total_returns = [r.total_return for r in results]
        sharpe_ratios = [r.sharpe_ratio for r in results]
        max_drawdowns = [r.max_drawdown for r in results]

        avg_return = sum(total_returns) / len(total_returns)
        std_return = np.std(total_returns) if len(total_returns) > 1 else 0
        avg_sharpe = sum(sharpe_ratios) / len(sharpe_ratios)
        avg_drawdown = sum(max_drawdowns) / len(max_drawdowns)
        consistency = len([r for r in total_returns if r > 0]) / len(total_returns)

        # Check thresholds
        passed = True
        failures = []

        if consistency < self.thresholds.get("min_consistency", 0.6):
            passed = False
            failures.append(
                f"Consistency {consistency:.2%} < {self.thresholds['min_consistency']:.2%}"
            )

        if std_return > self.thresholds.get("max_return_std", 0.3):
            passed = False
            failures.append(
                f"Return std {std_return:.2%} > {self.thresholds['max_return_std']:.2%}"
            )

        if avg_sharpe < self.thresholds.get("min_avg_sharpe", 0.5):
            passed = False
            failures.append(
                f"Avg Sharpe {avg_sharpe:.2f} < {self.thresholds['min_avg_sharpe']:.2f}"
            )

        if avg_drawdown < self.thresholds.get("max_avg_drawdown", -0.20):
            passed = False
            failures.append(
                f"Avg Drawdown {avg_drawdown:.2%} < {self.thresholds['max_avg_drawdown']:.2%}"
            )

        return {
            "passed": passed,
            "failures": failures if not passed else [],
            "windows": [
                {
                    "window": r.window_id,
                    "train_period": {
                        "start": r.train_start.isoformat(),
                        "end": r.train_end.isoformat(),
                    },
                    "validate_period": {
                        "start": r.validate_start.isoformat(),
                        "end": r.validate_end.isoformat(),
                    },
                    "result": {
                        "total_return": r.total_return,
                        "sharpe_ratio": r.sharpe_ratio,
                        "max_drawdown": r.max_drawdown,
                        "total_trades": r.total_trades,
                        "win_rate": r.win_rate,
                    },
                }
                for r in results
            ],
            "aggregated": {
                "avg_return": avg_return,
                "std_return": std_return,
                "avg_sharpe": avg_sharpe,
                "avg_max_drawdown": avg_drawdown,
                "consistency": consistency,
            },
            "thresholds": self.thresholds,
        }


# ============================================================================
# Cross-Validation Temporal (Enhanced)
# ============================================================================


class CrossValidationTemporal:
    """
    Cross-Validation Temporal (Task 3.5).

    Evaluates consistency of strategies across different time periods.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_path: str = "config/validation.yaml",
    ):
        """Initialize temporal cross-validator."""
        if config is None:
            full_config = load_validation_config(config_path)
            config = full_config.get("cross_validation", {})

        self.n_folds = config.get("n_folds", 5)
        self.thresholds = config.get(
            "thresholds",
            {
                "min_consistency_score": 0.6,
                "max_return_variance": 0.25,
            },
        )

    def create_folds(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, datetime]]:
        """Create temporal folds for cross-validation."""
        total_days = (end_date - start_date).days
        fold_days = total_days // self.n_folds

        folds = []
        for i in range(self.n_folds):
            fold_start = start_date + timedelta(days=i * fold_days)
            fold_end = start_date + timedelta(days=(i + 1) * fold_days)

            if i == self.n_folds - 1:
                fold_end = end_date

            folds.append(
                {
                    "fold": i + 1,
                    "start": fold_start,
                    "end": fold_end,
                }
            )

        return folds

    def cross_validate(
        self,
        quotes: List[Quote],
        signals: List[Any],
        config: BacktestConfig,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Run temporal cross-validation."""
        folds = self.create_folds(start_date, end_date)
        results = []

        for fold in folds:
            logger.info(
                f"Fold {fold['fold']}/{self.n_folds}: "
                f"{fold['start'].strftime('%Y-%m-%d')} to {fold['end'].strftime('%Y-%m-%d')}"
            )

            fold_quotes = [q for q in quotes if fold["start"] <= q.timestamp <= fold["end"]]

            fold_signals = [
                s
                for s in signals
                if hasattr(s, 'timestamp') and fold["start"] <= s.timestamp <= fold["end"]
            ]

            if not fold_quotes or not fold_signals:
                continue

            backtester = SimpleBacktester(config)
            result = backtester.run_backtest(
                fold_quotes,
                fold_signals,
                fold["start"],
                fold["end"],
            )

            results.append(
                {
                    "fold": fold["fold"],
                    "period": {
                        "start": fold["start"].isoformat(),
                        "end": fold["end"].isoformat(),
                    },
                    "result": {
                        "total_return": float(result.total_return),
                        "sharpe_ratio": float(result.performance.sharpe_ratio or 0),
                        "max_drawdown": float(result.performance.max_drawdown_percentage or 0),
                        "total_trades": result.performance.total_trades,
                        "win_rate": float(result.performance.win_rate),
                    },
                }
            )

        if not results:
            return {"passed": False, "reason": "No valid folds", "folds": []}

        # Calculate aggregated metrics
        total_returns = [r["result"]["total_return"] for r in results]
        avg_return = sum(total_returns) / len(total_returns)
        return_variance = np.var(total_returns) if len(total_returns) > 1 else 0
        consistency_score = len([r for r in total_returns if r > 0]) / len(total_returns)

        # Check thresholds
        passed = True
        failures = []

        if consistency_score < self.thresholds.get("min_consistency_score", 0.6):
            passed = False
            failures.append(
                f"Consistency {consistency_score:.2%} < {self.thresholds['min_consistency_score']:.2%}"
            )

        if return_variance > self.thresholds.get("max_return_variance", 0.25):
            passed = False
            failures.append(
                f"Return variance {return_variance:.4f} > {self.thresholds['max_return_variance']}"
            )

        return {
            "passed": passed,
            "failures": failures if not passed else [],
            "folds": results,
            "aggregated": {
                "avg_return": avg_return,
                "return_variance": return_variance,
                "std_return": np.std(total_returns) if len(total_returns) > 1 else 0,
                "min_return": min(total_returns),
                "max_return": max(total_returns),
                "consistency_score": consistency_score,
            },
            "thresholds": self.thresholds,
        }


# ============================================================================
# Stress Tester
# ============================================================================


class StressTester:
    """
    Stress Testing System (Task 3.5).

    Tests strategy robustness against synthetic market scenarios.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_path: str = "config/validation.yaml",
    ):
        """Initialize stress tester."""
        if config is None:
            full_config = load_validation_config(config_path)
            config = full_config.get("stress_testing", {})

        self.n_scenarios = config.get("n_scenarios", 100)
        self.scenarios_config = config.get("scenarios", {})
        self.thresholds = config.get(
            "thresholds",
            {
                "max_scenario_drawdown": -0.30,
                "min_survival_rate": 0.80,
                "max_avg_loss": -0.15,
                "min_recovery_rate": 0.70,
            },
        )

        # Load synthetic data config
        full_config = load_validation_config(config_path)
        self.data_generator = SyntheticDataGenerator(full_config.get("synthetic_data", {}))

    def _generate_scenario(
        self,
        scenario_type: str,
        scenario_config: Dict[str, Any],
        n_days: int,
        start_date: datetime,
        symbol: str,
    ) -> List[Quote]:
        """Generate synthetic data for a specific scenario type."""
        generators = {
            "flash_crash": lambda: self.data_generator.generate_flash_crash_scenario(
                n_days,
                start_date,
                symbol,
                drop_pct=scenario_config.get("drop_percentage", -0.10),
                recovery_days=scenario_config.get("recovery_days", 5),
            ),
            "high_volatility": lambda: self.data_generator.generate_high_volatility_scenario(
                n_days,
                start_date,
                symbol,
                volatility_multiplier=scenario_config.get("volatility_multiplier", 3.0),
            ),
            "trending_bull": lambda: self.data_generator.generate_trending_scenario(
                n_days,
                start_date,
                symbol,
                daily_drift=scenario_config.get("daily_drift", 0.002),
            ),
            "trending_bear": lambda: self.data_generator.generate_trending_scenario(
                n_days,
                start_date,
                symbol,
                daily_drift=scenario_config.get("daily_drift", -0.002),
            ),
            "mean_reverting": lambda: self.data_generator.generate_ou_prices(
                n_days,
                start_date,
                symbol,
                theta=scenario_config.get("reversion_speed", 0.1),
                mu=scenario_config.get("equilibrium_price", 100.0),
            ),
            "gap_up": lambda: self.data_generator.generate_gap_scenario(
                n_days,
                start_date,
                symbol,
                gap_pct=scenario_config.get("gap_percentage", 0.05),
                n_gaps=scenario_config.get("n_gaps", 3),
            ),
            "gap_down": lambda: self.data_generator.generate_gap_scenario(
                n_days,
                start_date,
                symbol,
                gap_pct=scenario_config.get("gap_percentage", -0.05),
                n_gaps=scenario_config.get("n_gaps", 3),
            ),
        }

        generator = generators.get(scenario_type)
        if generator:
            return generator()

        # Default: GBM
        return self.data_generator.generate_gbm_prices(n_days, start_date, symbol)

    def run_stress_tests(
        self,
        strategy,
        backtest_config: BacktestConfig,
        n_days: int = 252,
        symbol: str = "STRESS_TEST",
    ) -> Dict[str, Any]:
        """
        Run comprehensive stress tests.

        Args:
            strategy: Strategy instance to test
            backtest_config: Backtest configuration
            n_days: Number of days per scenario
            symbol: Symbol to use for synthetic data

        Returns:
            Dictionary with stress test results
        """
        start_date = datetime(2020, 1, 1)
        end_date = start_date + timedelta(days=n_days)

        # Calculate scenario distribution
        enabled_scenarios = {
            k: v for k, v in self.scenarios_config.items() if v.get("enabled", True)
        }

        total_weight = sum(s.get("weight", 0.1) for s in enabled_scenarios.values())
        scenario_counts = {
            k: max(1, int(self.n_scenarios * v.get("weight", 0.1) / total_weight))
            for k, v in enabled_scenarios.items()
        }

        results: List[StressScenarioResult] = []

        for scenario_type, count in scenario_counts.items():
            scenario_config = enabled_scenarios[scenario_type]
            logger.info(f"Running {count} {scenario_type} scenarios...")

            for i in range(count):
                try:
                    # Generate synthetic data
                    quotes = self._generate_scenario(
                        scenario_type, scenario_config, n_days, start_date, symbol
                    )

                    # Generate signals
                    signals = []
                    for quote in quotes:
                        try:
                            signal = strategy.analyze(quote)
                            if signal:
                                signals.append(signal)
                        except Exception:
                            pass

                    if not signals:
                        continue

                    # Run backtest
                    backtester = SimpleBacktester(backtest_config)
                    result = backtester.run_backtest(quotes, signals, start_date, end_date)

                    # Analyze result
                    total_return = float(result.total_return)
                    max_dd = float(result.performance.max_drawdown_percentage or 0)
                    final_capital = float(result.final_capital)
                    initial_capital = float(backtest_config.initial_capital)

                    survived = max_dd > self.thresholds.get("max_scenario_drawdown", -0.30)
                    recovered = final_capital >= initial_capital * 0.9  # 90% recovery

                    results.append(
                        StressScenarioResult(
                            scenario_type=scenario_type,
                            scenario_id=i + 1,
                            total_return=total_return,
                            max_drawdown=max_dd,
                            survived=survived,
                            recovered=recovered,
                            final_capital=final_capital,
                            trades_executed=result.performance.total_trades,
                        )
                    )

                except Exception as e:
                    logger.warning(f"Error in {scenario_type} scenario {i+1}: {e}")

        if not results:
            return {"passed": False, "reason": "No scenarios completed", "scenarios": []}

        # Aggregate results
        total_scenarios = len(results)
        survivors = sum(1 for r in results if r.survived)
        recovered = sum(1 for r in results if r.recovered)
        avg_return = sum(r.total_return for r in results) / total_scenarios
        avg_drawdown = sum(r.max_drawdown for r in results) / total_scenarios

        survival_rate = survivors / total_scenarios
        recovery_rate = recovered / total_scenarios

        # Check thresholds
        passed = True
        failures = []

        if survival_rate < self.thresholds.get("min_survival_rate", 0.80):
            passed = False
            failures.append(
                f"Survival rate {survival_rate:.2%} < {self.thresholds['min_survival_rate']:.2%}"
            )

        if avg_return < self.thresholds.get("max_avg_loss", -0.15):
            passed = False
            failures.append(f"Avg return {avg_return:.2%} < {self.thresholds['max_avg_loss']:.2%}")

        if recovery_rate < self.thresholds.get("min_recovery_rate", 0.70):
            passed = False
            failures.append(
                f"Recovery rate {recovery_rate:.2%} < {self.thresholds['min_recovery_rate']:.2%}"
            )

        # Group results by scenario type
        by_scenario = {}
        for r in results:
            if r.scenario_type not in by_scenario:
                by_scenario[r.scenario_type] = []
            by_scenario[r.scenario_type].append(
                {
                    "scenario_id": r.scenario_id,
                    "total_return": r.total_return,
                    "max_drawdown": r.max_drawdown,
                    "survived": r.survived,
                    "recovered": r.recovered,
                    "trades_executed": r.trades_executed,
                }
            )

        return {
            "passed": passed,
            "failures": failures if not passed else [],
            "summary": {
                "total_scenarios": total_scenarios,
                "survival_rate": survival_rate,
                "recovery_rate": recovery_rate,
                "avg_return": avg_return,
                "avg_drawdown": avg_drawdown,
            },
            "by_scenario_type": {
                scenario: {
                    "count": len(scenarios),
                    "avg_return": sum(s["total_return"] for s in scenarios) / len(scenarios),
                    "survival_rate": sum(1 for s in scenarios if s["survived"]) / len(scenarios),
                    "scenarios": scenarios,
                }
                for scenario, scenarios in by_scenario.items()
            },
            "thresholds": self.thresholds,
        }


# ============================================================================
# Monte Carlo Simulator
# ============================================================================


class MonteCarloSimulator:
    """
    Monte Carlo Simulation for strategy robustness testing.

    Uses bootstrap resampling to estimate confidence intervals.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_path: str = "config/validation.yaml",
    ):
        """Initialize Monte Carlo simulator."""
        if config is None:
            full_config = load_validation_config(config_path)
            config = full_config.get("monte_carlo", {})

        self.n_simulations = config.get("n_simulations", 1000)
        self.confidence_levels = config.get("confidence_levels", [0.95, 0.99])
        self.block_size = config.get("block_size", 20)

    def run_simulation(
        self,
        historical_returns: List[float],
        initial_capital: float = 100000.0,
        n_periods: int = 252,
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation with bootstrap resampling.

        Args:
            historical_returns: Historical daily returns
            initial_capital: Starting capital
            n_periods: Number of periods to simulate

        Returns:
            Dictionary with simulation results
        """
        if len(historical_returns) < self.block_size:
            return {"passed": False, "reason": "Insufficient historical data"}

        returns_array = np.array(historical_returns)
        simulation_results = []

        for _ in range(self.n_simulations):
            # Block bootstrap
            simulated_returns = self._block_bootstrap(returns_array, n_periods)

            # Calculate equity curve
            equity = [initial_capital]
            for ret in simulated_returns:
                equity.append(equity[-1] * (1 + ret))

            # Calculate metrics
            final_value = equity[-1]
            total_return = (final_value - initial_capital) / initial_capital
            max_drawdown = self._calculate_max_drawdown(equity)

            simulation_results.append(
                {
                    "final_value": final_value,
                    "total_return": total_return,
                    "max_drawdown": max_drawdown,
                }
            )

        # Aggregate results
        returns = [r["total_return"] for r in simulation_results]
        drawdowns = [r["max_drawdown"] for r in simulation_results]

        var_results = {}
        cvar_results = {}

        for conf in self.confidence_levels:
            percentile = (1 - conf) * 100
            var_results[f"VaR_{conf}"] = float(np.percentile(returns, percentile))
            # CVaR is mean of returns below VaR
            var_threshold = np.percentile(returns, percentile)
            cvar_results[f"CVaR_{conf}"] = float(
                np.mean([r for r in returns if r <= var_threshold])
            )

        return {
            "passed": True,
            "n_simulations": self.n_simulations,
            "summary": {
                "mean_return": float(np.mean(returns)),
                "std_return": float(np.std(returns)),
                "median_return": float(np.median(returns)),
                "mean_max_drawdown": float(np.mean(drawdowns)),
                "worst_drawdown": float(min(drawdowns)),
            },
            "var": var_results,
            "cvar": cvar_results,
            "percentiles": {
                "p5": float(np.percentile(returns, 5)),
                "p25": float(np.percentile(returns, 25)),
                "p50": float(np.percentile(returns, 50)),
                "p75": float(np.percentile(returns, 75)),
                "p95": float(np.percentile(returns, 95)),
            },
            "drawdown_distribution": {
                "p5": float(np.percentile(drawdowns, 5)),
                "p50": float(np.percentile(drawdowns, 50)),
                "p95": float(np.percentile(drawdowns, 95)),
            },
        }

    def _block_bootstrap(self, returns: np.ndarray, n_periods: int) -> np.ndarray:
        """Perform block bootstrap resampling."""
        n_blocks = int(np.ceil(n_periods / self.block_size))
        sampled = []

        for _ in range(n_blocks):
            start_idx = np.random.randint(0, len(returns) - self.block_size + 1)
            sampled.extend(returns[start_idx : start_idx + self.block_size])

        return np.array(sampled[:n_periods])

    def _calculate_max_drawdown(self, equity: List[float]) -> float:
        """Calculate maximum drawdown from equity curve."""
        peak = equity[0]
        max_dd = 0

        for value in equity[1:]:
            if value > peak:
                peak = value
            dd = (value - peak) / peak
            if dd < max_dd:
                max_dd = dd

        return max_dd


# ============================================================================
# Comprehensive Validator (Facade)
# ============================================================================


class ComprehensiveValidator:
    """
    Facade class that combines all validation methods.

    Provides a single interface for running complete validation suite.
    """

    def __init__(self, config_path: str = "config/validation.yaml"):
        """Initialize comprehensive validator."""
        self.config = load_validation_config(config_path)
        self.config_path = config_path

        self.walk_forward = WalkForwardValidator(config_path=config_path)
        self.cross_validation = CrossValidationTemporal(config_path=config_path)
        self.stress_tester = StressTester(config_path=config_path)
        self.monte_carlo = MonteCarloSimulator(config_path=config_path)

    def run_full_validation(
        self,
        strategy,
        strategy_name: str,
        quotes: List[Quote],
        signals: List[Any],
        backtest_config: BacktestConfig,
        start_date: datetime,
        end_date: datetime,
    ) -> ValidationReport:
        """
        Run complete validation suite.

        Args:
            strategy: Strategy instance
            strategy_name: Name of the strategy
            quotes: Historical market data
            signals: Trading signals
            backtest_config: Backtest configuration
            start_date: Start date
            end_date: End date

        Returns:
            Complete ValidationReport
        """
        report = ValidationReport(
            strategy_name=strategy_name,
            timestamp=datetime.now(),
        )

        all_passed = True

        # 1. Walk-Forward Validation
        if self.config.get("walk_forward", {}).get("enabled", True):
            logger.info("Running walk-forward validation...")
            report.walk_forward_results = self.walk_forward.validate_strategy(
                quotes, signals, backtest_config, start_date, end_date
            )
            if not report.walk_forward_results.get("passed", False):
                all_passed = False

        # 2. Cross-Validation
        if self.config.get("cross_validation", {}).get("enabled", True):
            logger.info("Running cross-validation...")
            report.cross_validation_results = self.cross_validation.cross_validate(
                quotes, signals, backtest_config, start_date, end_date
            )
            if not report.cross_validation_results.get("passed", False):
                all_passed = False

        # 3. Stress Testing
        if self.config.get("stress_testing", {}).get("enabled", True):
            logger.info("Running stress tests...")
            report.stress_test_results = self.stress_tester.run_stress_tests(
                strategy, backtest_config
            )
            if not report.stress_test_results.get("passed", False):
                all_passed = False

        # 4. Monte Carlo Simulation
        if self.config.get("monte_carlo", {}).get("enabled", True):
            logger.info("Running Monte Carlo simulation...")
            # Extract returns from signals/trades
            returns = self._extract_returns(quotes)
            if returns:
                report.monte_carlo_results = self.monte_carlo.run_simulation(
                    returns,
                    initial_capital=float(backtest_config.initial_capital),
                )

        report.overall_passed = all_passed
        report.summary = {
            "walk_forward_passed": report.walk_forward_results.get("passed")
            if report.walk_forward_results
            else None,
            "cross_validation_passed": report.cross_validation_results.get("passed")
            if report.cross_validation_results
            else None,
            "stress_test_passed": report.stress_test_results.get("passed")
            if report.stress_test_results
            else None,
            "monte_carlo_completed": report.monte_carlo_results is not None,
            "overall_passed": all_passed,
        }

        return report

    def _extract_returns(self, quotes: List[Quote]) -> List[float]:
        """Extract daily returns from quotes."""
        if len(quotes) < 2:
            return []

        sorted_quotes = sorted(quotes, key=lambda q: q.timestamp)
        returns = []

        for i in range(1, len(sorted_quotes)):
            prev_close = float(sorted_quotes[i - 1].close or sorted_quotes[i - 1].last)
            curr_close = float(sorted_quotes[i].close or sorted_quotes[i].last)
            if prev_close > 0:
                returns.append((curr_close - prev_close) / prev_close)

        return returns

    def save_report(self, report: ValidationReport, output_path: Optional[str] = None) -> str:
        """Save validation report to JSON file."""
        if output_path is None:
            output_dir = Path(
                self.config.get("reporting", {}).get("output_directory", "reports/validation")
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            output_path = str(output_dir / f"validation_{report.strategy_name}_{timestamp}.json")

        report_dict = {
            "strategy_name": report.strategy_name,
            "timestamp": report.timestamp.isoformat(),
            "overall_passed": report.overall_passed,
            "summary": report.summary,
            "walk_forward_results": report.walk_forward_results,
            "cross_validation_results": report.cross_validation_results,
            "stress_test_results": report.stress_test_results,
            "monte_carlo_results": report.monte_carlo_results,
        }

        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2, default=str)

        logger.info(f"Validation report saved to {output_path}")
        return output_path
