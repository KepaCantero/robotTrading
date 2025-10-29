"""
Grid Search Parameter Optimization with Walk-Forward Validation - TASK-PARAM-2

Implements grid search optimization combined with walk-forward validation
for robust parameter selection.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from itertools import product
import json

from app.backtesting.multi_strategy_engine import MultiStrategyBacktester
from app.backtesting.walk_forward_validator import WalkForwardValidator
from app.backtesting.data_loader import DataLoader
from app.models.market_data import Quote
from app.services.multi_strategy_allocation import MultiStrategyAllocationManager
from app.services.portfolio_config_manager import get_portfolio_config_manager
from app.strategies.momentum import MomentumStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.pairs_trading import PairsTradingStrategy
import yaml

logger = logging.getLogger(__name__)


class GridSearchOptimizer:
    """
    Grid Search Optimizer with Walk-Forward Validation - TASK-PARAM-2
    
    Performs exhaustive grid search over parameter combinations,
    validated using walk-forward analysis to prevent overfitting.
    """
    
    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        total_capital: Decimal = Decimal("100000"),
        preset_config_path: str = "config/parameter_presets.yaml",
        output_dir: Path = Path("docs/GRID_SEARCH_RESULTS"),
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.total_capital = total_capital
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load preset configuration
        self.preset_config = self._load_preset_config(preset_config_path)
        
        # Results storage
        self.results: List[Dict[str, Any]] = []
        self.best_config: Optional[Dict[str, Any]] = None
        self.best_score: float = -float('inf')
        
        # Load data once
        self.quotes: Dict[str, List[Quote]] = {}
        self._load_portfolio_data()
    
    def _load_preset_config(self, config_path: str) -> Dict[str, Any]:
        """Load parameter presets configuration."""
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"Preset config not found: {config_path}, using defaults")
            return {}
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_portfolio_data(self) -> None:
        """Load all portfolio symbols data."""
        config_manager = get_portfolio_config_manager()
        all_symbols = set()
        
        sector_symbols = config_manager.config.get("sectors", {})
        for sector_name, sector_data in sector_symbols.items():
            symbols = sector_data.get("symbols", [])
            all_symbols.update(symbols)
        
        loader = DataLoader()
        
        logger.info(f"Loading data for {len(all_symbols)} symbols...")
        for symbol in sorted(all_symbols):
            quotes = loader.load_market_data(
                symbol, self.start_date, self.end_date, source="csv"
            )
            if not quotes:
                quotes = loader.load_market_data(
                    symbol, self.start_date, self.end_date, source="yfinance"
                )
            
            if quotes:
                self.quotes[symbol] = quotes
                logger.debug(f"Loaded {len(quotes)} quotes for {symbol}")
        
        logger.info(f"Loaded data for {len(self.quotes)} symbols")
    
    def _get_parameter_grid(self, strategy_name: str) -> Dict[str, List[Any]]:
        """
        Get parameter grid for a strategy from config.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Dictionary mapping parameter names to lists of values
        """
        grid_config = self.preset_config.get("grid_search", {}).get("parameter_grids", {})
        return grid_config.get(strategy_name, {})
    
    def _generate_parameter_combinations(self, grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations from grid.
        
        Args:
            grid: Parameter grid dictionary
            
        Returns:
            List of parameter combination dictionaries
        """
        if not grid:
            return [{}]
        
        keys = list(grid.keys())
        values = [grid[key] for key in keys]
        
        combinations = []
        for combination in product(*values):
            param_dict = dict(zip(keys, combination))
            combinations.append(param_dict)
        
        logger.info(f"Generated {len(combinations)} parameter combinations")
        return combinations
    
    def _create_strategies_from_params(
        self, 
        momentum_params: Dict[str, Any],
        mean_rev_params: Dict[str, Any],
        pairs_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create strategy instances from parameter dictionaries."""
        strategies = {}
        
        # Momentum
        momentum_config = {
            "name": "momentum",
            "rsi_threshold": int(momentum_params.get("rsi_threshold", 40)),
            "momentum_threshold": momentum_params.get("momentum_threshold", 0.02),
            "volume_threshold": momentum_params.get("volume_threshold", 1.5),
            "ema_period": int(momentum_params.get("ema_period", 20)),
            "stop_loss": Decimal("0.03"),
            "take_profit": Decimal("0.10"),
            "max_position_size": Decimal("0.05"),
        }
        strategies["momentum"] = MomentumStrategy(momentum_config)
        
        # Mean Reversion
        mean_rev_config = {
            "name": "mean_reversion",
            "z_score_threshold": mean_rev_params.get("z_score_threshold", 1.5),
            "lookback_period": int(mean_rev_params.get("lookback_period", 20)),
            "stop_loss": Decimal(str(mean_rev_params.get("stop_loss_pct", 0.04))),
            "take_profit": Decimal(str(mean_rev_params.get("take_profit_pct", 0.10))),
            "max_position_size": Decimal("0.05"),
        }
        strategies["mean_reversion"] = MeanReversionStrategy(mean_rev_config)
        
        # Pairs Trading
        pairs_config = {
            "name": "pairs_trading",
            "spread_threshold": pairs_params.get("spread_threshold", 1.5),
            "lookback_period": int(pairs_params.get("lookback_period", 30)),
            "cointegration_threshold": pairs_params.get("cointegration_threshold", 0.05),
            "pair_symbols": [["AAPL", "MSFT"]],
            "stop_loss": Decimal("0.03"),
            "take_profit": Decimal("0.08"),
            "max_position_size": Decimal("0.05"),
        }
        strategies["pairs_trading"] = PairsTradingStrategy(pairs_config)
        
        return strategies
    
    def _run_walk_forward_backtest(
        self,
        strategies: Dict[str, Any],
        all_quotes: List[Quote]
    ) -> Dict[str, Any]:
        """Run backtest with walk-forward validation."""
        # Create allocation manager
        allocation_manager = MultiStrategyAllocationManager(total_capital=self.total_capital)
        
        # Create validator
        wf_config = self.preset_config.get("grid_search", {}).get("walk_forward", {})
        validator = WalkForwardValidator(
            train_years=wf_config.get("train_years", 4),
            validation_years=wf_config.get("validation_years", 1),
            step_years=wf_config.get("step_years", 1),
        )
        
        # Create windows
        windows = validator.create_windows(self.start_date, self.end_date)
        
        if not windows:
            logger.warning("No windows created for walk-forward validation")
            return {}
        
        # Run validation for each window
        results = []
        for window in windows:
            train_start = window["train_start"]
            train_end = window["train_end"]
            val_start = window["validation_start"]
            val_end = window["validation_end"]
            
            # Filter quotes for this window
            train_quotes = [q for q in all_quotes 
                          if train_start <= q.timestamp <= train_end]
            val_quotes = [q for q in all_quotes 
                        if val_start <= q.timestamp <= val_end]
            
            if not train_quotes or not val_quotes:
                continue
            
            # Run backtest on validation period
            from app.backtesting.simple_backtester import SimpleBacktester
            from app.backtesting.models import BacktestConfig
            
            config = BacktestConfig(
                strategy_name="multi_strategy",
                initial_capital=self.total_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.05"),
            )
            
            # Combine strategies and run
            backtester = MultiStrategyBacktester(
                allocation_manager=allocation_manager,
                strategies=strategies,
                config_params={
                    "commission": Decimal("1.0"),
                    "slippage": Decimal("0.05"),
                },
            )
            
            result = backtester.run_multi_strategy_backtest(
                val_quotes, val_start, val_end
            )
            
            if result and "combined" in result:
                combined = result["combined"]
                results.append({
                    "window": f"{val_start.date()} to {val_end.date()}",
                    "sharpe": combined.get("weighted_sharpe", 0.0) or 0.0,
                    "return": combined.get("total_return", 0.0) or 0.0,
                    "max_drawdown": abs(combined.get("weighted_max_drawdown", 0.0) or 0.0),
                    "trades": combined.get("total_trades", 0),
                })
        
        if not results:
            return {}
        
        # Aggregate results
        objective_metric = wf_config.get("objective_metric", "sharpe")
        
        if objective_metric == "sharpe":
            avg_score = sum(r["sharpe"] for r in results) / len(results)
        elif objective_metric == "return":
            avg_score = sum(r["return"] for r in results) / len(results)
        elif objective_metric == "calmar":
            returns = [r["return"] for r in results]
            drawdowns = [r["max_drawdown"] for r in results]
            avg_score = sum(r / max(dd, 0.01) for r, dd in zip(returns, drawdowns)) / len(results)
        else:
            avg_score = sum(r["sharpe"] for r in results) / len(results)
        
        return {
            "avg_score": avg_score,
            "windows": results,
            "score_type": objective_metric,
        }
    
    def optimize(self, max_combinations: Optional[int] = None) -> Dict[str, Any]:
        """
        Run grid search optimization with walk-forward validation.
        
        Args:
            max_combinations: Maximum number of combinations to test (None = all)
            
        Returns:
            Best configuration and results
        """
        # Get parameter grids
        momentum_grid = self._get_parameter_grid("momentum")
        mean_rev_grid = self._get_parameter_grid("mean_reversion")
        pairs_grid = self._get_parameter_grid("pairs_trading")
        
        # Generate combinations
        momentum_combos = self._generate_parameter_combinations(momentum_grid)
        mean_rev_combos = self._generate_parameter_combinations(mean_rev_grid)
        pairs_combos = self._generate_parameter_combinations(pairs_grid)
        
        # Prepare all quotes (flatten)
        all_quotes: List[Quote] = []
        for symbol_quotes in self.quotes.values():
            all_quotes.extend(symbol_quotes)
        all_quotes.sort(key=lambda q: q.timestamp)
        
        # Calculate total combinations
        total_combinations = len(momentum_combos) * len(mean_rev_combos) * len(pairs_combos)
        logger.info(f"Total parameter combinations: {total_combinations}")
        
        if max_combinations:
            logger.info(f"Limiting to {max_combinations} combinations")
            # Limit each grid proportionally
            momentum_limit = int((max_combinations ** 0.33) * len(momentum_combos) / (total_combinations ** 0.33))
            mean_rev_limit = int((max_combinations ** 0.33) * len(mean_rev_combos) / (total_combinations ** 0.33))
            pairs_limit = int((max_combinations ** 0.33) * len(pairs_combos) / (total_combinations ** 0.33))
            
            momentum_combos = momentum_combos[:max(1, momentum_limit)]
            mean_rev_combos = mean_rev_combos[:max(1, mean_rev_limit)]
            pairs_combos = pairs_combos[:max(1, pairs_limit)]
        
        # Get constraints
        constraints = self.preset_config.get("grid_search", {}).get("constraints", {})
        
        # Test all combinations
        combo_num = 0
        for mom_params in momentum_combos:
            for mr_params in mean_rev_combos:
                for pt_params in pairs_combos:
                    combo_num += 1
                    logger.info(f"Testing combination {combo_num}/{len(momentum_combos) * len(mean_rev_combos) * len(pairs_combos)}")
                    
                    # Create strategies
                    strategies = self._create_strategies_from_params(
                        mom_params, mr_params, pt_params
                    )
                    
                    # Run walk-forward validation
                    wf_result = self._run_walk_forward_backtest(strategies, all_quotes)
                    
                    if not wf_result:
                        logger.warning(f"Combination {combo_num} failed walk-forward validation")
                        continue
                    
                    # Check constraints
                    avg_drawdown = sum(w["max_drawdown"] for w in wf_result["windows"]) / len(wf_result["windows"])
                    avg_trades = sum(w["trades"] for w in wf_result["windows"]) / len(wf_result["windows"])
                    
                    if avg_drawdown > constraints.get("max_drawdown_pct", 0.25):
                        logger.debug(f"Combination {combo_num} exceeds max drawdown constraint")
                        continue
                    
                    if avg_trades < constraints.get("min_trades_per_strategy", 20):
                        logger.debug(f"Combination {combo_num} has insufficient trades")
                        continue
                    
                    # Store result
                    score = wf_result["avg_score"]
                    result_entry = {
                        "combination_id": combo_num,
                        "momentum_params": mom_params,
                        "mean_reversion_params": mr_params,
                        "pairs_trading_params": pt_params,
                        "score": score,
                        "score_type": wf_result["score_type"],
                        "windows": wf_result["windows"],
                        "avg_drawdown": avg_drawdown,
                        "avg_trades": avg_trades,
                    }
                    self.results.append(result_entry)
                    
                    # Update best
                    if score > self.best_score:
                        self.best_score = score
                        self.best_config = {
                            "momentum": mom_params,
                            "mean_reversion": mr_params,
                            "pairs_trading": pt_params,
                            "score": score,
                        }
                        logger.info(f"New best configuration found: score={score:.4f}")
        
        # Save results
        self._save_results()
        
        return {
            "best_config": self.best_config,
            "best_score": self.best_score,
            "total_tested": len(self.results),
        }
    
    def _save_results(self) -> None:
        """Save grid search results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save CSV
        csv_file = self.output_dir / f"grid_search_results_{timestamp}.csv"
        import csv
        with open(csv_file, 'w', newline='') as f:
            if self.results:
                fieldnames = list(self.results[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for result in self.results:
                    # Flatten params for CSV
                    row = {
                        "combination_id": result["combination_id"],
                        "score": result["score"],
                        "avg_drawdown": result["avg_drawdown"],
                        "avg_trades": result["avg_trades"],
                    }
                    # Add flattened params
                    for strategy in ["momentum", "mean_reversion", "pairs_trading"]:
                        params = result.get(f"{strategy}_params", {})
                        for key, value in params.items():
                            row[f"{strategy}_{key}"] = value
                    writer.writerow(row)
        
        # Save best config
        if self.best_config:
            json_file = self.output_dir / f"best_grid_search_config_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump(self.best_config, f, indent=2, default=str)
        
        # Save summary
        summary = {
            "timestamp": timestamp,
            "total_combinations_tested": len(self.results),
            "best_score": self.best_score,
            "best_config": self.best_config,
            "top_10_configs": sorted(
                self.results, 
                key=lambda x: x["score"], 
                reverse=True
            )[:10],
        }
        
        summary_file = self.output_dir / f"grid_search_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Results saved to {self.output_dir}")

