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
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import yaml

from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
from app.core.config.profile_config_loader import ProfileConfigLoader
from app.core.models.input_profile import InputProfile

logger = logging.getLogger(__name__)


class WalkForwardValidator:
    """
    Performs walk-forward validation.

    Tests strategy robustness by rolling through time windows
    with train/test splits.
    """

    def __init__(
        self,
        output_dir: Path,
        validation_config: Dict[str, Any],
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
        self, profile: InputProfile, config: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        n_windows = wf_config.get("n_windows", 5)
        train_pct = wf_config.get("train_percentage", 0.6)

        # Get dates
        start_date = pd.Timestamp(config.get("input", {}).get("start_date", "2020-01-01"))
        end_date = pd.Timestamp(config.get("input", {}).get("end_date", "2023-12-31"))
        total_days = (end_date - start_date).days

        if total_days < 365:
            return {"passed": False, "error": "Insufficient data"}

        # Calculate windows
        window_size = total_days / n_windows
        train_size = int(window_size * train_pct)
        test_size = int(window_size * (1 - train_pct))

        window_results = []
        for i in range(n_windows):
            try:
                window_start = start_date + pd.Timedelta(days=int(i * window_size))
                train_end = window_start + pd.Timedelta(days=train_size)
                test_end = train_end + pd.Timedelta(days=test_size)

                if test_end > end_date:
                    test_end = end_date

                window_config = config.copy()
                window_config["input"]["start_date"] = window_start.strftime("%Y-%m-%d")
                window_config["input"]["end_date"] = train_end.strftime("%Y-%m-%d")

                test_config = config.copy()
                test_config["input"]["start_date"] = train_end.strftime("%Y-%m-%d")
                test_config["input"]["end_date"] = test_end.strftime("%Y-%m-%d")

                train_results = self._run_backtest_with_params(profile, window_config, params)
                test_results = self._run_backtest_with_params(profile, test_config, params)

                train_sharpe = train_results.get("sharpe_ratio", 0)
                test_sharpe = test_results.get("sharpe_ratio", 0)

                window_results.append(
                    {
                        "window": i,
                        "train_sharpe": train_sharpe,
                        "test_sharpe": test_sharpe,
                        "sharpe_decay": train_sharpe - test_sharpe if train_sharpe > 0 else 0,
                    }
                )

            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.error(f"Window {i} failed: {e}")

        if not window_results:
            return {"passed": False, "error": "All windows failed"}

        test_sharpes = [w["test_sharpe"] for w in window_results]
        avg_sharpe = np.mean(test_sharpes)
        std_sharpe = np.std(test_sharpes)

        passed = avg_sharpe >= 0.5

        return {
            "passed": passed,
            "avg_sharpe": float(avg_sharpe),
            "std_sharpe": float(std_sharpe),
            "n_windows": len(window_results),
        }

    def _run_backtest_with_params(
        self, profile: InputProfile, config: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run backtest with specific parameters."""
        updated_config = config.copy()
        updated_config["strategy"].update(params)

        temp_config_path = self.output_dir / f"temp_wf_{uuid.uuid4().hex[:8]}.yaml"
        with open(temp_config_path, "w") as f:
            yaml.dump(updated_config, f)

        try:
            runner = ComprehensiveBacktestRunner(str(temp_config_path))
            results = runner.run_baseline_backtest()
            return results[0] if results else self._get_empty_metrics()
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Backtest failed: {e}")
            return self._get_empty_metrics()
        finally:
            if temp_config_path.exists():
                temp_config_path.unlink()

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics dict."""
        return {
            "sharpe_ratio": 0.0,
            "return_pct": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
        }


class MonteCarloSimulator:
    """
    Performs Monte Carlo simulation using bootstrapping.

    Evaluates strategy robustness through random sampling
    of historical returns.
    """

    def __init__(
        self,
        output_dir: Path,
        validation_config: Dict[str, Any],
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
        self, profile: InputProfile, config: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        n_simulations = mc_config.get("n_simulations", 1000)
        min_profitable_pct = mc_config.get("min_profitable_pct", 0.95)

        # Get backtest results
        try:
            backtest_results = self._run_backtest_with_params(profile, config, params)
            returns_series = backtest_results.get("returns_series")

            if returns_series is None or len(returns_series) == 0:
                total_return = backtest_results.get("return_pct", 0)
                total_trades = backtest_results.get("total_trades", 1)

                if total_trades > 0:
                    avg_return = total_return / total_trades
                    volatility = backtest_results.get("volatility", 0.15)
                    returns_series = np.random.normal(avg_return, volatility, total_trades)
                else:
                    return {"passed": False, "error": "No trade data"}
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Failed to get backtest results: {e}")
            return {"passed": False, "error": str(e)}

        # Bootstrap
        simulated_returns = []
        sample_size = len(returns_series)

        for _ in range(n_simulations):
            bootstrapped_returns = np.random.choice(returns_series, size=sample_size, replace=True)
            sim_cumulative_return = np.prod(1 + bootstrapped_returns) - 1
            simulated_returns.append(sim_cumulative_return)

        simulated_returns = np.array(simulated_returns)
        profitable_pct = np.sum(simulated_returns > 0) / n_simulations
        passed = profitable_pct >= min_profitable_pct

        return {
            "passed": passed,
            "n_simulations": n_simulations,
            "profitable_pct": profitable_pct,
            "avg_return": float(np.mean(simulated_returns)),
            "std_return": float(np.std(simulated_returns)),
        }

    def _run_backtest_with_params(
        self, profile: InputProfile, config: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run backtest with specific parameters."""
        import uuid

        updated_config = config.copy()
        updated_config["strategy"].update(params)

        temp_config_path = self.output_dir / f"temp_mc_{uuid.uuid4().hex[:8]}.yaml"
        with open(temp_config_path, "w") as f:
            yaml.dump(updated_config, f)

        try:
            runner = ComprehensiveBacktestRunner(str(temp_config_path))
            results = runner.run_baseline_backtest()
            return results[0] if results else self._get_empty_metrics()
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Backtest failed: {e}")
            return self._get_empty_metrics()
        finally:
            if temp_config_path.exists():
                temp_config_path.unlink()

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics dict."""
        return {
            "sharpe_ratio": 0.0,
            "return_pct": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
        }


class OutOfSampleValidator:
    """
    Performs out-of-sample validation.

    Tests strategy performance on unseen data to detect
    overfitting.
    """

    def __init__(
        self,
        output_dir: Path,
        validation_config: Dict[str, Any],
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
        self, profile: InputProfile, config: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        train_pct = oos_config.get("train_percentage", 0.7)
        min_oos_sharpe = oos_config.get("min_oos_sharpe", 0.5)
        max_performance_decay = oos_config.get("max_performance_decay", 0.3)

        start_date = pd.Timestamp(config.get("input", {}).get("start_date", "2020-01-01"))
        end_date = pd.Timestamp(config.get("input", {}).get("end_date", "2023-12-31"))
        total_days = (end_date - start_date).days

        split_date = start_date + pd.Timedelta(days=int(total_days * train_pct))

        train_config = config.copy()
        train_config["input"]["start_date"] = start_date.strftime("%Y-%m-%d")
        train_config["input"]["end_date"] = split_date.strftime("%Y-%m-%d")

        oos_test_config = config.copy()
        oos_test_config["input"]["start_date"] = split_date.strftime("%Y-%m-%d")
        oos_test_config["input"]["end_date"] = end_date.strftime("%Y-%m-%d")

        try:
            train_results = self._run_backtest_with_params(profile, train_config, params)
            oos_results = self._run_backtest_with_params(profile, oos_test_config, params)

            train_sharpe = train_results.get("sharpe_ratio", 0)
            oos_sharpe = oos_results.get("sharpe_ratio", 0)

            sharpe_decay = 0
            if train_sharpe > 0:
                sharpe_decay = (train_sharpe - oos_sharpe) / train_sharpe

            passed = (
                oos_sharpe >= min_oos_sharpe
                and sharpe_decay <= max_performance_decay
                and oos_sharpe > 0
            )

            return {
                "passed": passed,
                "train_sharpe": float(train_sharpe),
                "oos_sharpe": float(oos_sharpe),
                "sharpe_decay": float(sharpe_decay),
            }
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"OOS validation failed: {e}")
            return {"passed": False, "error": str(e)}

    def _run_backtest_with_params(
        self, profile: InputProfile, config: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run backtest with specific parameters."""
        import uuid

        updated_config = config.copy()
        updated_config["strategy"].update(params)

        temp_config_path = self.output_dir / f"temp_oos_{uuid.uuid4().hex[:8]}.yaml"
        with open(temp_config_path, "w") as f:
            yaml.dump(updated_config, f)

        try:
            runner = ComprehensiveBacktestRunner(str(temp_config_path))
            results = runner.run_baseline_backtest()
            return results[0] if results else self._get_empty_metrics()
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Backtest failed: {e}")
            return self._get_empty_metrics()
        finally:
            if temp_config_path.exists():
                temp_config_path.unlink()

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics dict."""
        return {
            "sharpe_ratio": 0.0,
            "return_pct": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
        }
