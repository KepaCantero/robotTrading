"""
Momentum Auto-Optimization Engine - TASK-MOM-OPT-1

Automatically recalibrates RSI/EMA/MACD parameters monthly
based on recent performance using walk-forward validation.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import yaml

from app.backtesting.walk_forward_validator import WalkForwardValidator
from app.domain.models.market_data import Quote
from app.domain.strategies.momentum import MomentumStrategy

logger = logging.getLogger(__name__)


class MomentumAutoOptimizer:
    """
    Momentum Auto-Optimization Engine - TASK-MOM-OPT-1

    Recalibrates momentum strategy parameters (RSI, EMA, MACD) monthly
    using walk-forward validation to maintain optimal performance.
    """

    def __init__(
        self,
        preset_config_path: str = "config/parameter_presets.yaml",
        optimization_history_path: str = "logs/optimization_history.json",
    ):
        self.preset_config_path = preset_config_path
        self.optimization_history_path = Path(optimization_history_path)
        self.optimization_history_path.parent.mkdir(parents=True, exist_ok=True)

        # Load config
        self.preset_config = self._load_config()
        self.auto_opt_config = self.preset_config.get("auto_optimization", {})

        # Load optimization history
        self.history = self._load_history()

        # Current parameters
        self.current_params: Optional[Dict[str, Any]] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load preset configuration."""
        config_file = Path(self.preset_config_path)
        if not config_file.exists():
            logger.warning(f"Config not found: {self.preset_config_path}")
            return {}

        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load optimization history."""
        if not self.optimization_history_path.exists():
            return []

        try:
            with open(self.optimization_history_path, 'r') as f:
                return json.load(f)
        except OSError as e:
            logger.error(f"Error loading history: {e}")
            return []

    def _save_history(self) -> None:
        """Save optimization history."""
        try:
            with open(self.optimization_history_path, 'w') as f:
                json.dump(self.history, f, indent=2, default=str)
        except OSError as e:
            logger.error(f"Error saving history: {e}")

    def should_recalibrate(self) -> bool:
        """
        Check if recalibration is needed based on schedule.

        Returns:
            True if recalibration should run
        """
        if not self.auto_opt_config.get("enabled", False):
            return False

        frequency = self.auto_opt_config.get("recalibration", {}).get("frequency", "monthly")

        if not self.history:
            return True  # First time optimization

        last_opt = self.history[-1] if self.history else None
        if not last_opt:
            return True

        last_date = datetime.fromisoformat(last_opt.get("timestamp", "2000-01-01"))
        days_since = (datetime.now() - last_date).days

        return {
            "daily": days_since >= 1,
            "weekly": days_since >= 7,
            "monthly": days_since >= 30,
            "quarterly": days_since >= 90,
        }.get(frequency, False)

    def optimize_parameters(
        self,
        quotes: List[Quote],
        start_date: datetime,
        end_date: datetime,
        current_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimize momentum parameters using walk-forward validation.

        Args:
            quotes: Market data quotes
            start_date: Backtest start date
            end_date: Backtest end date
            current_params: Current parameter values (for stability check)

        Returns:
            Optimized parameters and results
        """
        logger.info("Starting momentum auto-optimization...")

        # Get optimization bounds
        bounds = self.auto_opt_config.get("optimization_bounds", {})

        # Use Optuna for optimization (simpler than full grid search)
        import optuna

        # Create study
        study = optuna.create_study(direction="maximize")

        def objective(trial: optuna.Trial) -> float:
            # Suggest parameters within bounds
            params = {
                "rsi_threshold": trial.suggest_int(
                    "rsi_threshold",
                    int(bounds.get("rsi_threshold", [25, 65])[0]),
                    int(bounds.get("rsi_threshold", [25, 65])[1]),
                ),
                "momentum_threshold": trial.suggest_float(
                    "momentum_threshold",
                    bounds.get("momentum_threshold", [0.01, 0.03])[0],
                    bounds.get("momentum_threshold", [0.01, 0.03])[1],
                ),
                "volume_threshold": trial.suggest_float(
                    "volume_threshold",
                    bounds.get("volume_threshold", [1.2, 2.0])[0],
                    bounds.get("volume_threshold", [1.2, 2.0])[1],
                ),
                "ema_period": trial.suggest_int(
                    "ema_period",
                    int(bounds.get("ema_period", [12, 30])[0]),
                    int(bounds.get("ema_period", [12, 30])[1]),
                ),
            }

            # Create strategy with trial parameters
            strategy_config = {
                "name": "momentum",
                **params,
                "stop_loss": Decimal("0.03"),
                "take_profit": Decimal("0.10"),
                "max_position_size": Decimal("0.05"),
            }

            strategy = MomentumStrategy(strategy_config)

            # Run walk-forward validation
            wf_config = self.auto_opt_config.get("recalibration", {}).get("walk_forward", {})
            validator = WalkForwardValidator(
                config=wf_config,
            )

            windows = validator.create_windows(start_date, end_date)
            if not windows:
                return -1000.0

            # Evaluate on validation windows
            scores = []
            for window in windows[:3]:  # Limit to 3 windows for speed
                val_start = window["validation_start"]
                val_end = window["validation_end"]

                val_quotes = [q for q in quotes if val_start <= q.timestamp <= val_end]
                if not val_quotes:
                    continue

                # Simple backtest on validation window
                from app.backtesting.engine import SimpleBacktester
                from app.backtesting.models import BacktestConfig

                # Generate signals
                signals = []
                for quote in val_quotes:
                    signals.extend(strategy.generate_signals(quote))

                if not signals:
                    continue

                # Run backtest
                config = BacktestConfig(
                    strategy_name="momentum",
                    initial_capital=Decimal("50000"),
                    commission_per_trade=Decimal("1.0"),
                    slippage_percentage=Decimal("0.05"),
                )

                backtester = SimpleBacktester(config)
                result = backtester.run_backtest(val_quotes, signals, val_start, val_end)

                if result and result.performance and result.performance.sharpe_ratio:
                    scores.append(float(result.performance.sharpe_ratio))

            if not scores:
                return -1000.0

            return float(np.mean(scores))

        # Run optimization
        study.optimize(objective, n_trials=20)  # Limited trials for monthly updates

        # Get best parameters
        best_params = study.best_params

        # Stability check
        if current_params:
            stability_check = self._check_stability(best_params, current_params)
            if not stability_check["stable"]:
                logger.warning(f"Parameters unstable: {stability_check['reason']}")
                # Use more conservative version
                best_params = self._apply_stability_constraint(best_params, current_params)

        # Performance threshold check
        best_score = study.best_value
        if current_params and self.history:
            last_performance = self.history[-1].get("performance", {})
            last_sharpe = last_performance.get("sharpe_ratio", 0.0)

            min_improvement = self.auto_opt_config.get("performance_thresholds", {}).get(
                "min_sharpe_improvement", 0.1
            )

            if best_score < last_sharpe + min_improvement:
                logger.info(
                    f"Optimization did not improve enough ({best_score:.3f} vs {last_sharpe:.3f}), keeping current params"
                )
                return current_params

        # Record optimization
        opt_record = {
            "timestamp": datetime.now().isoformat(),
            "parameters": best_params,
            "performance": {
                "sharpe_ratio": best_score,
                "trial_count": len(study.trials),
            },
            "improvement": best_score
            - (last_performance.get("sharpe_ratio", 0.0) if current_params else 0.0),
        }

        self.history.append(opt_record)
        self._save_history()

        logger.info(f"Optimization complete: new Sharpe={best_score:.4f}, params={best_params}")

        return best_params

    def _check_stability(
        self, new_params: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if parameter changes are within stability limits."""
        max_change = self.auto_opt_config.get("stability", {}).get("max_parameter_change", 0.20)

        for key in new_params.keys():
            if key not in current_params:
                continue

            new_val = float(new_params[key])
            old_val = float(current_params[key])

            if old_val == 0:
                continue

            change_pct = abs(new_val - old_val) / abs(old_val)

            if change_pct > max_change:
                return {
                    "stable": False,
                    "reason": f"{key} changed by {change_pct:.1%} (max {max_change:.1%})",
                }

        return {"stable": True}

    def _apply_stability_constraint(
        self, new_params: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply stability constraint to limit parameter changes."""
        max_change = self.auto_opt_config.get("stability", {}).get("max_parameter_change", 0.20)

        constrained_params = {}
        for key, new_val in new_params.items():
            if key in current_params:
                old_val = float(current_params[key])
                change_pct = abs(new_val - old_val) / abs(old_val) if old_val != 0 else 1.0

                if change_pct > max_change:
                    # Limit change to max_change
                    if new_val > old_val:
                        constrained_params[key] = old_val * (1 + max_change)
                    else:
                        constrained_params[key] = old_val * (1 - max_change)
                else:
                    constrained_params[key] = new_val
            else:
                constrained_params[key] = new_val

        return constrained_params

    def get_optimized_config(self) -> Dict[str, Any]:
        """
        Get optimized configuration for momentum strategy.

        Returns:
            Configuration dictionary
        """
        if not self.history:
            # Use default preset
            preset_name = "moderate"
            presets = self.preset_config.get("presets", {})
            preset = presets.get(preset_name, {})
            momentum_config = preset.get("momentum", {})
            return {
                "rsi_threshold": momentum_config.get("rsi_threshold", 40),
                "momentum_threshold": momentum_config.get("momentum_threshold", 0.015),
                "volume_threshold": momentum_config.get("volume_threshold", 1.3),
                "ema_period": momentum_config.get("ema_period", 20),
            }

        # Use latest optimized parameters
        latest = self.history[-1]
        return latest["parameters"]
