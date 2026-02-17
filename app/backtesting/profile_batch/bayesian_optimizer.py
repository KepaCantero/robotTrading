"""
Bayesian Optimizer Module

Performs Bayesian optimization using Optuna for hyperparameter tuning.

Responsibilities:
- Run Bayesian optimization with Optuna
- Optimize strategy parameters
- Track optimization history
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import optuna
import yaml

from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
from app.core.config.profile_config_loader import ProfileConfigLoader
from app.core.models.input_profile import InputProfile

logger = logging.getLogger(__name__)


class BayesianOptimizer:
    """
    Performs Bayesian optimization using Optuna.

    Optimizes strategy parameters by efficiently exploring
    the parameter space using Bayesian optimization.
    """

    def __init__(
        self,
        output_dir: Path,
        optimization_config: Dict[str, Any],
        profile_config_loader: ProfileConfigLoader | None = None,
    ):
        """
        Initialize Bayesian optimizer.

        Args:
            output_dir: Directory for temporary files
            optimization_config: Optimization configuration
            profile_config_loader: Profile config loader for parameter ranges
        """
        self.output_dir = output_dir
        self.optimization_config = optimization_config
        self.profile_config_loader = profile_config_loader

    def optimize(
        self, profile: InputProfile, config: Dict[str, Any], multi_strategy: bool = False
    ) -> Dict[str, Any]:
        """
        Run Bayesian optimization.

        Args:
            profile: InputProfile
            config: Configuration dict
            multi_strategy: If True, use multi-strategy mode

        Returns:
            Optimization results with best parameters
        """
        logger.info(
            f"Running Bayesian optimization for {profile.objetivo_inversion.value} "
            f"({'multi-strategy' if multi_strategy else 'single-strategy'})"
        )

        n_trials = self.optimization_config.get("n_trials", 100)
        timeout = self.optimization_config.get("timeout", None)

        # Get parameter ranges
        rsi_buy_min, rsi_buy_max, vol_min, vol_max = self._get_parameter_ranges()

        def objective(trial: optuna.Trial) -> float:
            """Objective function for optimization."""
            params = {
                "rsi_threshold": trial.suggest_int("rsi_threshold", rsi_buy_min, rsi_buy_max),
                "ema_short": trial.suggest_int("ema_short", 5, 20),
                "ema_long": trial.suggest_int("ema_long", 20, 50),
                "volume_threshold": trial.suggest_float("volume_threshold", vol_min, vol_max),
                "stop_loss": trial.suggest_float("stop_loss", 0.01, 0.05),
                "take_profit": trial.suggest_float("take_profit", 0.05, 0.20),
            }

            try:
                metrics = self._run_backtest_with_params(
                    profile, config, params, multi_strategy=multi_strategy
                )
                if multi_strategy and "combined" in metrics:
                    return metrics["combined"].get("sharpe_ratio", -1.0)
                return metrics.get("sharpe_ratio", -1.0)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.warning(f"Trial failed: {e}")
                return -1.0

        study = optuna.create_study(
            direction="maximize",
            study_name=f"{profile.objetivo_inversion.value}_{profile.input_id[:8]}",
        )

        study.optimize(objective, n_trials=n_trials, timeout=timeout)

        best_params = study.best_params
        best_value = study.best_value
        best_metrics = self._run_backtest_with_params(profile, config, best_params)

        history = [{"trial": t.number, "value": t.value, "params": t.params} for t in study.trials]

        logger.info(f"Optimization complete: Best Sharpe={best_value:.2f}")

        return {
            "best_params": best_params,
            "best_metrics": best_metrics,
            "best_value": best_value,
            "history": history,
            "n_trials": len(study.trials),
        }

    def _get_parameter_ranges(self) -> tuple:
        """Get parameter ranges from config or defaults."""
        if self.profile_config_loader is not None:
            try:
                rsi_buy_config = self.profile_config_loader.get_threshold_config("rsi").get(
                    "buy_threshold", {}
                )
                rsi_buy_min = rsi_buy_config.get("min", 20)
                rsi_buy_max = rsi_buy_config.get("max", 35)

                vol_config = self.profile_config_loader.get_threshold_config("volume_ratio")
                vol_min = vol_config.get("min", 1.0)
                vol_max = vol_config.get("max", 1.5)

                logger.debug("Loaded parameter ranges from ProfileConfigLoader")
                return rsi_buy_min, rsi_buy_max, vol_min, vol_max
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                logger.warning(f"Failed to load parameter ranges: {e}")

        logger.info("Using default parameter ranges")
        return 20, 35, 1.0, 1.5

    def _run_backtest_with_params(
        self,
        profile: InputProfile,
        config: Dict[str, Any],
        params: Dict[str, Any],
        multi_strategy: bool = False,
    ) -> Dict[str, Any]:
        """Run backtest with specific parameters."""
        from uuid import uuid4

        updated_config = config.copy()
        updated_config["strategy"].update(params)

        temp_config_path = self.output_dir / f"temp_opt_{uuid4().hex[:8]}.yaml"
        with open(temp_config_path, "w") as f:
            yaml.dump(updated_config, f)

        try:
            runner = ComprehensiveBacktestRunner(str(temp_config_path))

            if multi_strategy:
                results = runner.run_multi_strategy_backtest()
                for r in results:
                    if r.get("strategy_name") == "combined":
                        return r
                return results[0] if results else self._get_empty_metrics()
            else:
                results = runner.run_baseline_backtest()
                return results[0] if results else self._get_empty_metrics()

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Backtest with params failed: {e}")
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
