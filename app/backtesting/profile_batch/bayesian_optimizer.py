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
        """Run backtest with specific parameters.

        Maps optimization parameters to the strategy's nested configuration structure:
        - rsi_threshold → modules.rsi_filter.adaptive_thresholds.*.buy_threshold
        - ema_short → modules.ema_filter.parameters.fast_period
        - ema_long → modules.ema_filter.parameters.slow_period
        - volume_threshold → modules.volume_filter.thresholds.*.min_volume_ratio
        - stop_loss → risk_manager.stop_loss.fixed_percentage.value
        - take_profit → risk_manager.take_profit.fixed_percentage.value
        """
        import copy
        from uuid import uuid4

        updated_config = copy.deepcopy(config)
        strategy = updated_config.get("strategy", {})

        # Ensure modules structure exists
        if "modules" not in strategy:
            strategy["modules"] = {}

        # Map RSI threshold to all adaptive thresholds
        rsi_threshold = params.get("rsi_threshold")
        if rsi_threshold is not None:
            if "rsi_filter" not in strategy["modules"]:
                strategy["modules"]["rsi_filter"] = {}
            if "adaptive_thresholds" not in strategy["modules"]["rsi_filter"]:
                strategy["modules"]["rsi_filter"]["adaptive_thresholds"] = {}

            # Update buy_threshold for all contexts
            for context in ["trend_up", "trend_down", "range", "high_vol"]:
                if context not in strategy["modules"]["rsi_filter"]["adaptive_thresholds"]:
                    strategy["modules"]["rsi_filter"]["adaptive_thresholds"][context] = {}
                strategy["modules"]["rsi_filter"]["adaptive_thresholds"][context]["buy_threshold"] = rsi_threshold

        # Map EMA periods
        ema_short = params.get("ema_short")
        ema_long = params.get("ema_long")
        if ema_short is not None or ema_long is not None:
            if "ema_filter" not in strategy["modules"]:
                strategy["modules"]["ema_filter"] = {"parameters": {}}
            if "parameters" not in strategy["modules"]["ema_filter"]:
                strategy["modules"]["ema_filter"]["parameters"] = {}
            if ema_short is not None:
                strategy["modules"]["ema_filter"]["parameters"]["fast_period"] = ema_short
            if ema_long is not None:
                strategy["modules"]["ema_filter"]["parameters"]["slow_period"] = ema_long

        # Map volume threshold
        volume_threshold = params.get("volume_threshold")
        if volume_threshold is not None:
            if "volume_filter" not in strategy["modules"]:
                strategy["modules"]["volume_filter"] = {"thresholds": {}}
            if "thresholds" not in strategy["modules"]["volume_filter"]:
                strategy["modules"]["volume_filter"]["thresholds"] = {}
            # Update for all presets
            for preset in ["conservative", "balanced", "aggressive"]:
                strategy["modules"]["volume_filter"]["thresholds"][preset] = {
                    "min_volume_ratio": volume_threshold
                }

        # Map stop_loss and take_profit
        stop_loss = params.get("stop_loss")
        take_profit = params.get("take_profit")

        if stop_loss is not None or take_profit is not None:
            if "risk_manager" not in strategy:
                strategy["risk_manager"] = {}

            if stop_loss is not None:
                if "stop_loss" not in strategy["risk_manager"]:
                    strategy["risk_manager"]["stop_loss"] = {"fixed_percentage": {}}
                if "fixed_percentage" not in strategy["risk_manager"]["stop_loss"]:
                    strategy["risk_manager"]["stop_loss"]["fixed_percentage"] = {}
                strategy["risk_manager"]["stop_loss"]["fixed_percentage"]["value"] = stop_loss

            if take_profit is not None:
                if "take_profit" not in strategy["risk_manager"]:
                    strategy["risk_manager"]["take_profit"] = {"fixed_percentage": {}}
                if "fixed_percentage" not in strategy["risk_manager"]["take_profit"]:
                    strategy["risk_manager"]["take_profit"]["fixed_percentage"] = {}
                strategy["risk_manager"]["take_profit"]["fixed_percentage"]["value"] = take_profit

        updated_config["strategy"] = strategy

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
