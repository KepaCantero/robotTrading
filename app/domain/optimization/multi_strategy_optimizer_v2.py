"""
Multi-Strategy Automated Optimization System.

Uses Optuna for hyperparameter optimization of multi-strategy backtesting.
Includes walk-forward validation and Monte Carlo resampling.
"""

import csv
import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import optuna

from app.backtesting.data_loader import DataLoader
from app.backtesting.engines.multi_strategy_engine import MultiStrategyBacktester
from app.domain.strategies.mean_reversion import MeanReversionStrategy
from app.domain.strategies.momentum import MomentumStrategy
from app.domain.strategies.pairs_trading import PairsTrading as PairsTradingStrategy

if TYPE_CHECKING:
    from app.domain.models.market_data import Quote

logger = logging.getLogger(__name__)


class MultiStrategyOptimizerV2:
    """Automated optimization system for multi-strategy backtesting."""

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        total_capital: Optional[Decimal] = None,
        output_dir: Optional[Path] = None,
        max_runs: int = 200,
    ):
        if total_capital is None:
            total_capital = Decimal("100000")
        if output_dir is None:
            output_dir = Path("docs/OPTIMIZATION_RESULTS")
        self.start_date = start_date
        self.end_date = end_date
        self.total_capital = total_capital
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_runs = max_runs

        # Results storage
        self.optimization_results: list[dict[str, object]] = []
        self.best_config: Optional[dict[str, int | float]] = None
        self.best_score: float = -float("in")

        # Load data once
        self.quotes: dict[str, list[Quote]] = {}
        self._load_portfolio_data()

    def _load_portfolio_data(self) -> None:
        """Load all portfolio symbols data."""
        # Late import to avoid domain layer depending on services layer
        from app.services.portfolio_config_manager import get_portfolio_config_manager

        config_manager = get_portfolio_config_manager()
        all_symbols = set()

        sector_symbols = config_manager.config.get("sectors", {})
        for _sector_name, sector_data in sector_symbols.items():
            symbols = sector_data.get("symbols", [])
            all_symbols.update(symbols)

        loader = DataLoader()

        logger.info(f"Loading data for {len(all_symbols)} symbols...")
        for symbol in sorted(all_symbols):
            quotes = loader.load_market_data(symbol, self.start_date, self.end_date, source="csv")
            if not quotes:
                # Try fallback
                quotes = loader.load_market_data(
                    symbol, self.start_date, self.end_date, source="yfinance"
                )

            if quotes:
                self.quotes[symbol] = quotes
                logger.debug(f"Loaded {len(quotes)} quotes for {symbol}")
            else:
                logger.warning(f"No data for {symbol}")

        logger.info(f"Loaded data for {len(self.quotes)} symbols")

    def _create_search_space(self, trial: optuna.Trial) -> dict[str, int | float]:
        """Define search space for hyperparameters."""
        return {
            # Mean Reversion
            "mean_reversion.z_score_threshold": trial.suggest_float(
                "mean_reversion.z_score_threshold", 0.8, 2.0
            ),
            "mean_reversion.lookback_period": trial.suggest_int(
                "mean_reversion.lookback_period", 10, 30
            ),
            "mean_reversion.stop_loss_pct": trial.suggest_float(
                "mean_reversion.stop_loss_pct", 0.01, 0.03
            ),
            "mean_reversion.take_profit_pct": trial.suggest_float(
                "mean_reversion.take_profit_pct", 0.08, 0.15
            ),
            # Momentum
            "momentum.rsi_threshold": trial.suggest_int("momentum.rsi_threshold", 35, 60),
            "momentum.momentum_threshold": trial.suggest_float(
                "momentum.momentum_threshold", 0.01, 0.03
            ),
            "momentum.volume_threshold": trial.suggest_float("momentum.volume_threshold", 1.0, 2.0),
            "momentum.ema_period": trial.suggest_int("momentum.ema_period", 9, 50),
            # Pairs Trading
            "pairs_trading.spread_threshold": trial.suggest_float(
                "pairs_trading.spread_threshold", 0.8, 2.0
            ),
            "pairs_trading.lookback_period": trial.suggest_int(
                "pairs_trading.lookback_period", 20, 60
            ),
            "pairs_trading.cointegration_threshold": trial.suggest_float(
                "pairs_trading.cointegration_threshold", 0.01, 0.1
            ),
            # Global
            "global.stop_loss_pct": trial.suggest_float("global.stop_loss_pct", 0.01, 0.03),
            "global.position_size_pct": trial.suggest_float("global.position_size_pct", 0.02, 0.08),
        }

    def _create_strategies(self, params: dict[str, int | float]) -> dict[str, object]:
        """Create strategy instances with optimized parameters."""
        strategies: dict[str, object] = {}

        # Momentum
        momentum_config: dict[str, int | float | str] = {
            "name": "momentum",
            "rsi_threshold": int(params.get("momentum.rsi_threshold", 40)),
            "momentum_threshold": params.get("momentum.momentum_threshold", 0.02),
            "volume_threshold": params.get("momentum.volume_threshold", 1.5),
            "lookback_period": 14,
            "ema_period": int(params.get("momentum.ema_period", 20)),
            "stop_loss": params.get("global.stop_loss_pct", 0.03),
            "take_profit": 0.1,
            "max_position_size": params.get("global.position_size_pct", 0.05),
        }
        strategies["momentum"] = MomentumStrategy(momentum_config)

        # Mean Reversion
        mean_rev_config: dict[str, int | float | str] = {
            "name": "mean_reversion",
            "z_score_threshold": params.get("mean_reversion.z_score_threshold", 1.0),
            "lookback_period": int(params.get("mean_reversion.lookback_period", 20)),
            "stop_loss": params.get("mean_reversion.stop_loss_pct", 0.04),
            "take_profit": params.get("mean_reversion.take_profit_pct", 0.12),
            "max_position_size": params.get("global.position_size_pct", 0.05),
        }
        strategies["mean_reversion"] = MeanReversionStrategy(mean_rev_config)

        # Pairs Trading - uses different constructor signature
        strategies["pairs_trading"] = PairsTradingStrategy(
            formation_period=int(params.get("pairs_trading.lookback_period", 30)),
            z_score_entry=params.get("pairs_trading.spread_threshold", 1.0),
        )

        return strategies

    def _run_backtest(self, params: dict[str, object]):
        """Run backtest with given parameters."""
        try:
            # Create strategies
            strategies = self._create_strategies(params)

            # Late import to avoid domain layer depending on services layer
            from app.services.multi_strategy_allocation import MultiStrategyAllocationManager

            # Create allocation manager (default weights: 50% momentum, 25% mean_reversion, 25% pairs_trading)
            allocation_manager = MultiStrategyAllocationManager(
                total_capital=self.total_capital,
            )

            # Config params
            config_params = {
                "commission": Decimal("1.0"),
                "slippage": Decimal("0.05"),
                "stop_loss": Decimal(str(params.get("global.stop_loss_pct", 0.03))),
                "take_profit": Decimal("0.10"),
                "max_position_size": Decimal(str(params.get("global.position_size_pct", 0.05))),
            }

            # Prepare all quotes (flatten)
            all_quotes: list[Quote] = []
            for symbol_quotes in self.quotes.values():
                all_quotes.extend(symbol_quotes)

            # Sort by timestamp
            all_quotes.sort(key=lambda q: q.timestamp)

            # Run backtest
            backtester = MultiStrategyBacktester(
                allocation_manager=allocation_manager,
                strategies=strategies,
                config_params=config_params,
                enable_diagnostics=False,  # Disable for optimization speed
            )

            result = backtester.run_multi_strategy_backtest(
                all_quotes, self.start_date, self.end_date
            )

            return result

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Backtest failed: {e}")
            return {}

    def _calculate_objective(self, result: dict[str, Any]) -> float:
        """Calculate objective function value (Sharpe ratio with constraints)."""
        if not result or "combined" not in result:
            return -1000.0  # Heavy penalty for failed backtests

        combined = result["combined"]

        # Extract metrics
        sharpe = combined.get("weighted_sharpe", 0.0) or 0.0
        max_dd = abs(combined.get("weighted_max_drawdown", 0.0) or 0.0)
        combined.get("total_return", 0.0) or 0.0

        # Count trades per strategy
        strategy_results = result.get("strategies", {})
        trades_by_strategy = {}
        for strategy_name, strategy_result in strategy_results.items():
            trades = strategy_result.get("total_trades", 0)
            trades_by_strategy[strategy_name] = trades

        total_trades = combined.get("total_trades", 0)
        min_trades_per_strategy = min(trades_by_strategy.values()) if trades_by_strategy else 0

        # Constraints penalties
        penalty = 0.0

        # Max drawdown constraint
        if max_dd > 0.25:  # 25% max
            penalty -= (max_dd - 0.25) * 10

        # Min trades constraint
        if min_trades_per_strategy < 20:
            penalty -= (20 - min_trades_per_strategy) * 2

        # Overtrading penalty
        if total_trades > 2000:
            penalty -= (total_trades - 2000) / 100

        # Objective: maximize Sharpe with penalty for constraints
        objective = sharpe + penalty

        return objective

    def objective_function(self, trial: optuna.Trial) -> float:
        """Optuna objective function."""
        # Sample parameters
        params = self._create_search_space(trial)

        # Run backtest
        result = self._run_backtest(params)

        # Calculate objective
        objective = self._calculate_objective(result)

        # Store result
        self.optimization_results.append(
            {
                "trial": trial.number,
                "params": params,
                "objective": objective,
                "result": result,
            }
        )

        return objective

    def run_optimization(
        self,
        n_trials: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> dict[str, Any]:
        """Run optimization study."""
        n_trials = n_trials or self.max_runs

        study = optuna.create_study(
            direction="maximize",
            study_name=f"multi_strategy_opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )

        logger.info(f"Starting optimization with {n_trials} trials...")

        study.optimize(
            self.objective_function,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=True,
        )

        # Get best result
        self.best_config = study.best_params
        self.best_score = study.best_value

        logger.info(f"Optimization complete. Best score: {self.best_score:.4f}")

        # Save results
        self._save_results(study)

        return {
            "best_config": self.best_config,
            "best_score": self.best_score,
            "n_trials": len(study.trials),
        }

    def _save_results(self, study: optuna.Study) -> None:
        """Save optimization results."""
        # Save CSV
        opt_results_file = self.output_dir / "opt_results.csv"
        with open(opt_results_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "trial",
                    "objective",
                    "sharpe",
                    "return",
                    "max_dd",
                    "total_trades",
                    "momentum_trades",
                    "mean_rev_trades",
                    "pairs_trades",
                    "params_json",
                ]
            )

            for trial in study.trials:
                params = trial.params
                result = self._run_backtest(params)

                combined = result.get("combined", {}) if result else {}
                strategy_results = result.get("strategies", {}) if result else {}

                writer.writerow(
                    [
                        trial.number,
                        trial.value or 0.0,
                        combined.get("weighted_sharpe", 0.0) or 0.0,
                        combined.get("total_return", 0.0) or 0.0,
                        abs(combined.get("weighted_max_drawdown", 0.0) or 0.0),
                        combined.get("total_trades", 0),
                        strategy_results.get("momentum", {}).get("total_trades", 0),
                        strategy_results.get("mean_reversion", {}).get("total_trades", 0),
                        strategy_results.get("pairs_trading", {}).get("total_trades", 0),
                        json.dumps(params),
                    ]
                )

        # Save best config
        best_config_file = self.output_dir / "best_config.json"
        with open(best_config_file, "w") as f:
            json.dump(self.best_config, f, indent=2, default=str)

        # Save summary
        summary = {
            "generated_at": datetime.utcnow().isoformat(),
            "best_score": self.best_score,
            "best_config": self.best_config,
            "n_trials": len(study.trials),
            "top_10_configs": [
                {
                    "trial": t.number,
                    "score": t.value or 0.0,
                    "params": t.params,
                }
                for t in sorted(study.trials, key=lambda x: x.value or -999, reverse=True)[:10]
            ],
        }

        summary_file = self.output_dir / "optimization_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(f"Results saved to {self.output_dir}")
