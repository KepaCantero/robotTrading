"""
Optimization Validators Module

Provides validation components for the optimization pipeline:
- Walk-forward validation
- Monte Carlo simulation
- Out-of-sample validation

Responsibilities:
- Perform walk-forward validation for robustness
- Execute Monte Carlo simulations
- Run out-of-sample validation
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Union

import numpy as np
import pandas as pd
import yaml

from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
from app.backtesting.shared import MetricsDict, get_empty_metrics

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from app.domain.models.input_profile import InputProfile
    from app.shared.config.profile_config_loader import ProfileConfigLoader

logger = logging.getLogger(__name__)

# Type aliases (additional ones not in shared module)
ConfigDict = dict[str, object]
ValidationResultDict = dict[str, Union[bool, int, float, str, object]]


def _safe_float(value: float | int | str | bool | None, default: float = 0.0) -> float:
    """Extract a float from a MetricsDict value, returning default if not numeric."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return default


def _safe_int(value: float | int | str | bool | None, default: int = 0) -> int:
    """Extract an int from a MetricsDict value, returning default if not numeric."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    return default


class WalkForwardValidator:
    """
    Performs walk-forward validation.

    Tests strategy robustness by rolling through time windows
    with train/test splits.

    Note: This is a profile-batch specific implementation.
    See also: app.backtesting.walk_forward_validator.WalkForwardValidator
    for the main implementation.
    """

    def __init__(
        self,
        output_dir: Path,
        validation_config: dict[str, object],
        profile_config_loader: ProfileConfigLoader | None = None,
    ):
        """
        Initialize walk-forward validator.

        Args:
            output_dir: Directory for temporary files
            validation_config: Validation configuration
            profile_config_loader: Profile config loader
        """
        self.output_dir = output_dir
        self.validation_config = validation_config
        self.profile_config_loader = profile_config_loader

    def validate(
        self, profile: InputProfile, config: ConfigDict, params: dict[str, object]
    ) -> ValidationResultDict:
        """
        Run walk-forward validation.

        Args:
            profile: InputProfile
            config: Configuration dict
            params: Strategy parameters

        Returns:
            Validation results
        """
        logger.info("Running walk-forward validation")

        # Load config
        wf_config = self.validation_config.get("walk_forward", {})
        n_windows = (
            _safe_int(wf_config.get("n_windows", 5), 5) if isinstance(wf_config, dict) else 5
        )
        train_pct_raw = (
            wf_config.get("train_percentage", 0.6) if isinstance(wf_config, dict) else 0.6
        )
        train_pct = _safe_float(train_pct_raw, 0.6)

        # Get dates
        input_cfg = config.get("input", {})
        input_dict = input_cfg if isinstance(input_cfg, dict) else {}
        start_date = pd.Timestamp(input_dict.get("start_date", "2020-01-01"))
        end_date = pd.Timestamp(input_dict.get("end_date", "2023-12-31"))
        total_days = (end_date - start_date).days

        if total_days < 365:
            return {"passed": False, "error": "Insufficient data"}

        # Calculate windows
        window_size = total_days / n_windows
        train_size = int(window_size * train_pct)
        test_size = int(window_size * (1 - train_pct))

        window_results: list[dict[str, float]] = []
        for i in range(n_windows):
            try:
                window_start = start_date + pd.Timedelta(days=int(i * window_size))
                train_end = window_start + pd.Timedelta(days=train_size)
                test_end = train_end + pd.Timedelta(days=test_size)

                if test_end > end_date:
                    test_end = end_date

                window_config = dict(config)
                window_config["input"] = {
                    "start_date": window_start.strftime("%Y-%m-%d"),
                    "end_date": train_end.strftime("%Y-%m-%d"),
                }

                test_config = dict(config)
                test_config["input"] = {
                    "start_date": train_end.strftime("%Y-%m-%d"),
                    "end_date": test_end.strftime("%Y-%m-%d"),
                }

                train_results = self._run_backtest_with_params(profile, window_config, params)
                test_results = self._run_backtest_with_params(profile, test_config, params)

                train_sharpe = _safe_float(train_results.get("sharpe_ratio", 0))
                test_sharpe = _safe_float(test_results.get("sharpe_ratio", 0))

                window_results.append(
                    {
                        "window": float(i),
                        "train_sharpe": train_sharpe,
                        "test_sharpe": test_sharpe,
                        "sharpe_decay": train_sharpe - test_sharpe if train_sharpe > 0 else 0.0,
                    }
                )

            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.error(f"Window {i} failed: {e}")

        if not window_results:
            return {"passed": False, "error": "All windows failed"}

        test_sharpes = [w["test_sharpe"] for w in window_results]
        avg_sharpe = float(np.mean(test_sharpes))
        std_sharpe = float(np.std(test_sharpes))

        passed = avg_sharpe >= 0.5

        return {
            "passed": passed,
            "avg_sharpe": avg_sharpe,
            "std_sharpe": std_sharpe,
            "n_windows": float(len(window_results)),
        }

    def _run_backtest_with_params(
        self, profile: InputProfile, config: ConfigDict, params: dict[str, object]
    ) -> MetricsDict:
        """Run backtest with specific parameters."""
        updated_config = dict(config)
        strategy_cfg = updated_config.get("strategy", {})
        if isinstance(strategy_cfg, dict):
            strategy_cfg.update(params)
            updated_config["strategy"] = strategy_cfg

        temp_config_path = self.output_dir / f"temp_wf_{uuid.uuid4().hex[:8]}.yaml"
        with open(temp_config_path, "w") as f:
            yaml.dump(updated_config, f)

        try:
            runner = ComprehensiveBacktestRunner(str(temp_config_path))
            results = runner.run_baseline_backtest()
            if results:
                return self._coerce_to_metrics_dict(results[0])
            return self._get_empty_metrics()
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Backtest failed: {e}")
            return self._get_empty_metrics()
        finally:
            if temp_config_path.exists():
                temp_config_path.unlink()

    @staticmethod
    def _coerce_to_metrics_dict(raw: Mapping[str, object]) -> MetricsDict:
        """Coerce a ResultDict to MetricsDict by filtering values to valid types."""
        out: MetricsDict = {}
        for key, value in raw.items():
            if isinstance(value, (float, int, str, bool)) or value is None:
                out[key] = value
        return out

    # Delegates to shared MetricsFactory (eliminates duplicate code)
    def _get_empty_metrics(self) -> MetricsDict:
        """Return empty metrics dict. Delegates to shared MetricsFactory."""
        return get_empty_metrics(include_pnl=False)


class MonteCarloSimulator:
    """
    Performs Monte Carlo simulation using bootstrapping.

    Evaluates strategy robustness through random sampling
    of historical returns.

    Note: This is a profile-batch specific implementation.
    See also: app.backtesting.walk_forward_validator.MonteCarloSimulator
    for the main implementation.
    """

    def __init__(
        self,
        output_dir: Path,
        validation_config: dict[str, object],
        profile_config_loader: ProfileConfigLoader | None = None,
    ):
        """
        Initialize Monte Carlo simulator.

        Args:
            output_dir: Directory for temporary files
            validation_config: Validation configuration
            profile_config_loader: Profile config loader
        """
        self.output_dir = output_dir
        self.validation_config = validation_config
        self.profile_config_loader = profile_config_loader

    def simulate(
        self, profile: InputProfile, config: ConfigDict, params: dict[str, object]
    ) -> ValidationResultDict:
        """
        Run Monte Carlo simulation.

        Args:
            profile: InputProfile
            config: Configuration dict
            params: Strategy parameters

        Returns:
            Simulation results
        """
        logger.info("Running Monte Carlo simulation")

        mc_config = self.validation_config.get("monte_carlo", {})
        if not isinstance(mc_config, dict):
            mc_config = {}
        n_simulations = _safe_int(mc_config.get("n_simulations", 1000), 1000)
        min_profitable_pct = _safe_float(mc_config.get("min_profitable_pct", 0.95), 0.95)

        # Get backtest results
        returns_series: np.ndarray[tuple[int], np.dtype[np.float64]]
        try:
            backtest_results = self._run_backtest_with_params(profile, config, params)
            raw_returns = backtest_results.get("returns_series")

            if raw_returns is None or (
                isinstance(raw_returns, (list, np.ndarray)) and len(raw_returns) == 0
            ):
                total_return = _safe_float(backtest_results.get("return_pct", 0))
                total_trades = _safe_int(backtest_results.get("total_trades", 1))

                if total_trades > 0:
                    avg_return = total_return / total_trades
                    volatility = _safe_float(backtest_results.get("volatility", 0.15), 0.15)
                    returns_series = np.random.normal(avg_return, volatility, total_trades)
                else:
                    return {"passed": False, "error": "No trade data"}
            elif isinstance(raw_returns, np.ndarray):
                returns_series = raw_returns.astype(np.float64)
            elif isinstance(raw_returns, (list, tuple)):
                returns_series = np.array(raw_returns, dtype=np.float64)
            else:
                total_return = _safe_float(backtest_results.get("return_pct", 0))
                total_trades = _safe_int(backtest_results.get("total_trades", 1))
                if total_trades > 0:
                    avg_return = total_return / total_trades
                    volatility = _safe_float(backtest_results.get("volatility", 0.15), 0.15)
                    returns_series = np.random.normal(avg_return, volatility, total_trades)
                else:
                    return {"passed": False, "error": "No trade data"}
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Failed to get backtest results: {e}")
            return {"passed": False, "error": str(e)}

        # Bootstrap
        simulated_returns_list: list[float] = []
        sample_size = len(returns_series)

        for _ in range(n_simulations):
            bootstrapped_returns = np.random.choice(returns_series, size=sample_size, replace=True)
            sim_cumulative_return = float(np.prod(1 + bootstrapped_returns) - 1)
            simulated_returns_list.append(sim_cumulative_return)

        simulated_returns_arr = np.array(simulated_returns_list)
        profitable_pct = float(np.sum(simulated_returns_arr > 0)) / n_simulations
        passed = profitable_pct >= min_profitable_pct

        return {
            "passed": passed,
            "n_simulations": float(n_simulations),
            "profitable_pct": profitable_pct,
            "avg_return": float(np.mean(simulated_returns_arr)),
            "std_return": float(np.std(simulated_returns_arr)),
        }

    def _run_backtest_with_params(
        self, profile: InputProfile, config: ConfigDict, params: dict[str, object]
    ) -> MetricsDict:
        """Run backtest with specific parameters."""
        updated_config = dict(config)
        strategy_cfg = updated_config.get("strategy", {})
        if isinstance(strategy_cfg, dict):
            strategy_cfg.update(params)
            updated_config["strategy"] = strategy_cfg

        temp_config_path = self.output_dir / f"temp_mc_{uuid.uuid4().hex[:8]}.yaml"
        with open(temp_config_path, "w") as f:
            yaml.dump(updated_config, f)

        try:
            runner = ComprehensiveBacktestRunner(str(temp_config_path))
            results = runner.run_baseline_backtest()
            if results:
                return self._coerce_to_metrics_dict(results[0])
            return self._get_empty_metrics()
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Backtest failed: {e}")
            return self._get_empty_metrics()
        finally:
            if temp_config_path.exists():
                temp_config_path.unlink()

    @staticmethod
    def _coerce_to_metrics_dict(raw: Mapping[str, object]) -> MetricsDict:
        """Coerce a ResultDict to MetricsDict by filtering values to valid types."""
        out: MetricsDict = {}
        for key, value in raw.items():
            if isinstance(value, (float, int, str, bool)) or value is None:
                out[key] = value
        return out

    # Delegates to shared MetricsFactory (eliminates duplicate code)
    def _get_empty_metrics(self) -> MetricsDict:
        """Return empty metrics dict. Delegates to shared MetricsFactory."""
        return get_empty_metrics(include_pnl=False)


class OutOfSampleValidator:
    """
    Performs out-of-sample validation.

    Tests strategy performance on unseen data to detect
    overfitting.
    """

    def __init__(
        self,
        output_dir: Path,
        validation_config: dict[str, object],
        profile_config_loader: ProfileConfigLoader | None = None,
    ):
        """
        Initialize OOS validator.

        Args:
            output_dir: Directory for temporary files
            validation_config: Validation configuration
            profile_config_loader: Profile config loader
        """
        self.output_dir = output_dir
        self.validation_config = validation_config
        self.profile_config_loader = profile_config_loader

    def validate(
        self, profile: InputProfile, config: ConfigDict, params: dict[str, object]
    ) -> ValidationResultDict:
        """
        Run out-of-sample validation.

        Args:
            profile: InputProfile
            config: Configuration dict
            params: Strategy parameters

        Returns:
            Validation results
        """
        logger.info("Running out-of-sample validation")

        oos_config = self.validation_config.get("out_of_sample", {})
        if not isinstance(oos_config, dict):
            oos_config = {}
        train_pct = _safe_float(oos_config.get("train_percentage", 0.7), 0.7)
        min_oos_sharpe = _safe_float(oos_config.get("min_oos_sharpe", 0.5), 0.5)
        max_performance_decay = _safe_float(oos_config.get("max_performance_decay", 0.3), 0.3)

        input_cfg = config.get("input", {})
        input_dict = input_cfg if isinstance(input_cfg, dict) else {}
        start_date = pd.Timestamp(input_dict.get("start_date", "2020-01-01"))
        end_date = pd.Timestamp(input_dict.get("end_date", "2023-12-31"))
        total_days = (end_date - start_date).days

        split_date = start_date + pd.Timedelta(days=int(total_days * train_pct))

        train_config = dict(config)
        train_config["input"] = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": split_date.strftime("%Y-%m-%d"),
        }

        oos_test_config = dict(config)
        oos_test_config["input"] = {
            "start_date": split_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }

        try:
            train_results = self._run_backtest_with_params(profile, train_config, params)
            oos_results = self._run_backtest_with_params(profile, oos_test_config, params)

            train_sharpe = _safe_float(train_results.get("sharpe_ratio", 0))
            oos_sharpe = _safe_float(oos_results.get("sharpe_ratio", 0))

            sharpe_decay: float = 0.0
            if train_sharpe > 0:
                sharpe_decay = (train_sharpe - oos_sharpe) / train_sharpe

            passed = (
                oos_sharpe >= min_oos_sharpe
                and sharpe_decay <= max_performance_decay
                and oos_sharpe > 0
            )

            return {
                "passed": passed,
                "train_sharpe": train_sharpe,
                "oos_sharpe": oos_sharpe,
                "sharpe_decay": sharpe_decay,
            }
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"OOS validation failed: {e}")
            return {"passed": False, "error": str(e)}

    def _run_backtest_with_params(
        self, profile: InputProfile, config: ConfigDict, params: dict[str, object]
    ) -> MetricsDict:
        """Run backtest with specific parameters."""
        updated_config = dict(config)
        strategy_cfg = updated_config.get("strategy", {})
        if isinstance(strategy_cfg, dict):
            strategy_cfg.update(params)
            updated_config["strategy"] = strategy_cfg

        temp_config_path = self.output_dir / f"temp_oos_{uuid.uuid4().hex[:8]}.yaml"
        with open(temp_config_path, "w") as f:
            yaml.dump(updated_config, f)

        try:
            runner = ComprehensiveBacktestRunner(str(temp_config_path))
            results = runner.run_baseline_backtest()
            if results:
                return self._coerce_to_metrics_dict(results[0])
            return self._get_empty_metrics()
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Backtest failed: {e}")
            return self._get_empty_metrics()
        finally:
            if temp_config_path.exists():
                temp_config_path.unlink()

    @staticmethod
    def _coerce_to_metrics_dict(raw: Mapping[str, object]) -> MetricsDict:
        """Coerce a ResultDict to MetricsDict by filtering values to valid types."""
        out: MetricsDict = {}
        for key, value in raw.items():
            if isinstance(value, (float, int, str, bool)) or value is None:
                out[key] = value
        return out

    # Delegates to shared MetricsFactory (eliminates duplicate code)
    def _get_empty_metrics(self) -> MetricsDict:
        """Return empty metrics dict. Delegates to shared MetricsFactory."""
        return get_empty_metrics(include_pnl=False)
