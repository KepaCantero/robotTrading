"""
Multi-Strategy Parameter Optimization System.

Optimizes parameters for all strategies simultaneously using Optuna,
considering capital allocation and maximizing combined Sharpe ratio.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, Optional

import optuna

from app.backtesting.data_loader import DataLoader
from app.backtesting.engines.multi_strategy_engine import MultiStrategyBacktester
from app.domain.strategies.factory import StrategyFactory
from app.domain.strategies.mean_reversion import MeanReversionStrategy
from app.domain.strategies.momentum import MomentumStrategy
from app.domain.strategies.pairs_trading import PairsTrading

if TYPE_CHECKING:
    from app.services.multi_strategy_allocation import MultiStrategyAllocationManager

logger = logging.getLogger(__name__)


class MultiStrategyOptimizer:
    """
    Optimizes parameters for multiple trading strategies simultaneously.

    Uses Optuna for Bayesian optimization across:
    - Momentum strategy parameters
    - Mean Reversion strategy parameters
    - Pairs Trading strategy parameters (optional)
    - Capital allocation weights
    """

    def __init__(
        self,
        total_capital: Optional[Decimal] = None,
        symbol: str = "AAPL",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        n_trials: int = 50,
        optimization_direction: str = "maximize",
        objective_metric: str = "sharpe",  # "sharpe", "return", "calmar"
    ):
        """
        Initialize multi-strategy optimizer.

        Args:
            total_capital: Total portfolio capital
            symbol: Symbol to backtest
            start_date: Backtest start date (default: 10 years ago)
            end_date: Backtest end date (default: now)
            n_trials: Number of optimization trials
            optimization_direction: "maximize" or "minimize"
            objective_metric: Metric to optimize ("sharpe", "return", "calmar")
        """
        if total_capital is None:
            total_capital = Decimal("100000")
        self.total_capital = total_capital
        self.symbol = symbol

        # Default to 10-year backtest
        self.end_date = end_date or datetime.now()
        self.start_date = start_date or (self.end_date - timedelta(days=365 * 10))

        self.n_trials = n_trials
        self.optimization_direction = optimization_direction
        self.objective_metric = objective_metric

        self.data_loader = DataLoader()
        self.strategy_factory = StrategyFactory()

        # Load market data once
        logger.info(f"Loading market data for {symbol} from {self.start_date} to {self.end_date}")
        self.market_data = self.data_loader.load_market_data(symbol, self.start_date, self.end_date)

        if not self.market_data:
            raise ValueError(f"No market data available for {symbol}")

        logger.info(f"Loaded {len(self.market_data)} market data points")

        self.best_params: Optional[Dict[str, Any]] = None
        self.best_value: Optional[float] = None

    def _suggest_strategy_params(self, trial: optuna.Trial) -> Dict[str, Dict[str, Any]]:
        """
        Suggest parameters for all strategies using Optuna.

        Args:
            trial: Optuna trial object

        Returns:
            Dictionary with strategy configs
        """
        # Momentum Strategy Parameters
        # Capital Allocation Weights (must sum to 1.0)
        momentum_weight = trial.suggest_float("alloc_momentum", 0.4, 0.7, step=0.05)
        mean_reversion_weight = trial.suggest_float("alloc_mean_reversion", 0.15, 0.4, step=0.05)
        # Pairs trading gets remainder to ensure sum = 1.0
        pairs_weight = max(0.05, 1.0 - momentum_weight - mean_reversion_weight)

        params = {
            "momentum": {
                "name": "momentum",
                "rsi_threshold": trial.suggest_float("momentum_rsi_threshold", 30.0, 50.0, step=1.0),
                "momentum_threshold": trial.suggest_float(
                    "momentum_momentum_threshold", 0.01, 0.05, step=0.01
                ),
                "volume_threshold": trial.suggest_float(
                    "momentum_volume_threshold", 1.0, 2.5, step=0.1
                ),
                "ema_period": trial.suggest_int("momentum_ema_period", 10, 50, step=5),
                "rsi_period": trial.suggest_int("momentum_rsi_period", 10, 20, step=2),
                "lookback_period": trial.suggest_int("momentum_lookback_period", 3, 10, step=1),
            },
            "mean_reversion": {
                "name": "mean_reversion",
                "z_score_threshold": trial.suggest_float("mr_z_score_threshold", 0.5, 3.0, step=0.25),
                "volatility_threshold": trial.suggest_float(
                    "mr_volatility_threshold", 0.01, 0.05, step=0.01
                ),
                "lookback_period": trial.suggest_int("mr_lookback_period", 10, 30, step=5),
                "mean_reversion_speed": trial.suggest_float(
                    "mr_mean_reversion_speed", 0.05, 0.2, step=0.05
                ),
                "min_z_score": trial.suggest_float("mr_min_z_score", 1.0, 2.5, step=0.25),
            },
            "pairs_trading": {
                "name": "pairs_trading",
                "spread_threshold": trial.suggest_float("pt_spread_threshold", 0.1, 1.0, step=0.1),
                "cointegration_threshold": trial.suggest_float(
                    "pt_cointegration_threshold", 0.01, 0.1, step=0.01
                ),
                "min_correlation": trial.suggest_float("pt_min_correlation", 0.3, 0.8, step=0.1),
                "lookback_period": trial.suggest_int("pt_lookback_period", 20, 50, step=5),
                "pair_symbols": ["AAPL", "MSFT"],  # Fixed pair for now
                "hedge_ratio": Decimal("1.0"),
                "max_spread_deviation": Decimal("3.0"),
            },
            "allocation": {
                "momentum": momentum_weight,
                "mean_reversion": mean_reversion_weight,
                "pairs_trading": pairs_weight,
            },
        }

        return params

    def _create_strategies(self, params: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create strategy instances with optimized parameters.

        Args:
            params: Strategy parameters dictionary

        Returns:
            Dictionary of strategy instances
        """
        strategies = {}

        # Create Momentum strategy
        momentum_config = params["momentum"].copy()
        momentum_config.update(
            {
                "stop_loss": Decimal("0.05"),
                "take_profit": Decimal("0.10"),
                "max_position_size": Decimal("0.1"),
            }
        )
        strategies["momentum"] = MomentumStrategy(momentum_config)

        # Create Mean Reversion strategy
        mr_config = params["mean_reversion"].copy()
        mr_config.update(
            {
                "stop_loss": Decimal("0.03"),
                "take_profit": Decimal("0.06"),
                "max_position_size": Decimal("0.08"),
            }
        )
        strategies["mean_reversion"] = MeanReversionStrategy(mr_config)

        # Create Pairs Trading strategy
        pt_config = params["pairs_trading"].copy()
        pt_config.update(
            {
                "stop_loss": Decimal("0.03"),
                "take_profit": Decimal("0.06"),
                "max_position_size": Decimal("0.08"),
                "max_pair_exposure": Decimal("0.2"),
                "max_total_exposure": Decimal("0.4"),
                "hedge_ratio_threshold": Decimal("0.1"),
            }
        )
        # PairsTrading accepts individual keyword args, not a config dict
        strategies["pairs_trading"] = PairsTrading(
            formation_period=pt_config.get("lookback_period", 252),
            z_score_entry=pt_config.get("spread_threshold", 2.0),
            z_score_exit=0.5,
            min_half_life=5.0,
            max_half_life=60.0,
            num_pairs=20,
        )

        return strategies

    def _create_allocation_manager(
        self, allocation_params: Dict[str, float]
    ) -> "MultiStrategyAllocationManager":
        """
        Create allocation manager with optimized weights.

        Args:
            allocation_params: Allocation weights dictionary

        Returns:
            MultiStrategyAllocationManager instance
        """
        # Late import to avoid domain layer depending on services layer
        from app.services.multi_strategy_allocation import MultiStrategyAllocationManager

        manager = MultiStrategyAllocationManager(self.total_capital)

        # Update allocation weights
        for strategy_name, weight in allocation_params.items():
            if strategy_name in manager.strategy_allocations:
                allocation = manager.strategy_allocations[strategy_name]
                allocation.target_weight = Decimal(str(weight))
                allocation.min_weight = Decimal(str(max(0.05, weight - 0.15)))
                allocation.max_weight = Decimal(str(min(0.7, weight + 0.15)))

        return manager

    def _objective_function(self, trial: optuna.Trial) -> float:
        """
        Objective function for Optuna optimization.

        Args:
            trial: Optuna trial object

        Returns:
            Objective value (Sharpe ratio, return, or Calmar ratio)
        """
        try:
            # Suggest parameters for this trial
            params = self._suggest_strategy_params(trial)

            # Create strategies with optimized parameters
            strategies = self._create_strategies(params)

            # Create allocation manager
            allocation_manager = self._create_allocation_manager(params["allocation"])

            # Create backtester
            backtester = MultiStrategyBacktester(
                allocation_manager=allocation_manager,
                strategies=strategies,
                config_params={
                    "commission": Decimal("1.0"),
                    "slippage": Decimal("0.05"),
                    "max_position_size": Decimal("0.1"),
                },
            )

            # Run backtest
            results = backtester.run_multi_strategy_backtest(
                self.market_data, self.start_date, self.end_date
            )

            # Extract metric based on objective
            if self.objective_metric == "sharpe":
                metric_value = results["combined"].get("weighted_sharpe", 0.0)
            elif self.objective_metric == "return":
                metric_value = results["combined"].get("total_return", 0.0)
            elif self.objective_metric == "calmar":
                # Calmar = Annualized Return / Max Drawdown
                total_return = results["combined"].get("total_return", 0.0)
                max_dd = abs(results["combined"].get("weighted_max_dd", 1.0))
                metric_value = total_return / max_dd if max_dd > 0 else 0.0
            else:
                metric_value = results["combined"].get("weighted_sharpe", 0.0)

            # Store intermediate results
            trial.set_user_attr("total_return", results["combined"].get("total_return", 0.0))
            trial.set_user_attr("total_trades", results["combined"].get("total_trades", 0))
            trial.set_user_attr("max_drawdown", results["combined"].get("weighted_max_dd", 0.0))

            logger.debug(
                f"Trial {trial.number}: {self.objective_metric}={metric_value:.4f}, "
                f"return={results['combined'].get('total_return', 0.0):.2f}%, "
                f"trades={results['combined'].get('total_trades', 0)}"
            )

            return float(metric_value)

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error in trial {trial.number}: {e}", exc_info=True)
            # Return worst possible value
            return -999.0 if self.optimization_direction == "maximize" else 999.0

    def optimize(
        self,
        storage: Optional[str] = None,
        study_name: str = "multi_strategy_optimization",
        resume: bool = False,
    ) -> optuna.Study:
        """
        Run optimization study.

        Args:
            storage: Path to SQLite storage (optional, for resume capability)
            study_name: Name of the study
            resume: Whether to resume from existing study

        Returns:
            Optimized Optuna study
        """
        logger.info(f"Starting optimization with {self.n_trials} trials")
        logger.info(f"Optimizing: {self.objective_metric} ({self.optimization_direction})")
        logger.info(f"Period: {self.start_date.date()} to {self.end_date.date()}")

        # Create or load study
        if storage:
            study = optuna.create_study(
                study_name=study_name,
                direction=self.optimization_direction,
                storage=storage,
                load_if_exists=resume,
            )
        else:
            study = optuna.create_study(
                study_name=study_name,
                direction=self.optimization_direction,
            )

        # Run optimization
        study.optimize(
            self._objective_function,
            n_trials=self.n_trials,
            show_progress_bar=True,
        )

        # Store best results
        if study.best_trial:
            self.best_params = study.best_params
            self.best_value = study.best_value

            logger.info("Optimization complete!")
            logger.info(f"Best {self.objective_metric}: {self.best_value:.4f}")
            logger.info(f"Best parameters: {self.best_params}")

        return study

    def get_best_config(self) -> Dict[str, Any]:
        """
        Get best configuration from optimization.

        Returns:
            Dictionary with best strategy configs and allocation
        """
        if not self.best_params:
            raise ValueError("No optimization has been run yet")

        # Reconstruct best config from best params
        # Extract strategy params
        momentum_config = {
            k.replace("momentum_", ""): v
            for k, v in self.best_params.items()
            if k.startswith("momentum_")
        }
        momentum_config["name"] = "momentum"

        mean_reversion_config = {
            k.replace("mr_", ""): v for k, v in self.best_params.items() if k.startswith("mr_")
        }
        mean_reversion_config["name"] = "mean_reversion"

        pairs_trading_config = {
            k.replace("pt_", ""): v for k, v in self.best_params.items() if k.startswith("pt_")
        }
        pairs_trading_config["name"] = "pairs_trading"
        pairs_trading_config["pair_symbols"] = ["AAPL", "MSFT"]

        # Extract allocation
        allocation_config = {
            k.replace("alloc_", ""): v
            for k, v in self.best_params.items()
            if k.startswith("alloc_")
        }

        best_config = {
            "momentum": momentum_config,
            "mean_reversion": mean_reversion_config,
            "pairs_trading": pairs_trading_config,
            "allocation": allocation_config,
        }

        return best_config

    def run_backtest_with_best_params(self) -> Dict[str, Any]:
        """
        Run a final backtest with optimized parameters.

        Returns:
            Consolidated backtest results
        """
        if not self.best_params:
            raise ValueError("No optimization has been run yet")

        # Get best config
        best_config = self.get_best_config()

        # Create strategies
        strategies = self._create_strategies(best_config)

        # Create allocation manager
        allocation_manager = self._create_allocation_manager(best_config["allocation"])

        # Run backtest
        backtester = MultiStrategyBacktester(
            allocation_manager=allocation_manager,
            strategies=strategies,
            config_params={
                "commission": Decimal("1.0"),
                "slippage": Decimal("0.05"),
                "max_position_size": Decimal("0.1"),
            },
        )

        results = backtester.run_multi_strategy_backtest(
            self.market_data, self.start_date, self.end_date
        )

        return results
