"""
Walk-Forward Validation System (TASK-BV-1, BV-2)

Implements walk-forward validation and cross-validation temporal for backtesting.
Trains on historical window, tests on subsequent period, then rolls forward.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, BacktestResult
from app.backtesting.multi_strategy_engine import MultiStrategyBacktester
from app.models.market_data import Quote

logger = logging.getLogger(__name__)


class WalkForwardValidator:
    """
    Walk-Forward Validation (TASK-BV-1).
    
    Trains on historical window, validates on subsequent period, then rolls forward.
    """
    
    def __init__(
        self,
        train_years: int = 4,
        validation_years: int = 1,
        step_years: int = 1,
    ):
        """
        Initialize walk-forward validator.
        
        Args:
            train_years: Years of training data (default: 4)
            validation_years: Years of validation data (default: 1)
            step_years: Years to step forward each iteration (default: 1)
        """
        self.train_years = train_years
        self.validation_years = validation_years
        self.step_years = step_years
    
    def create_windows(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, datetime]]:
        """
        Create walk-forward windows.
        
        Args:
            start_date: Overall start date
            end_date: Overall end date
            
        Returns:
            List of window dicts with 'train_start', 'train_end', 'validate_start', 'validate_end'
        """
        windows = []
        current_start = start_date
        
        while current_start < end_date:
            train_end = current_start + timedelta(days=365 * self.train_years)
            validate_start = train_end
            validate_end = validate_start + timedelta(days=365 * self.validation_years)
            
            # Don't create window if validation period extends beyond end_date
            if validate_end > end_date:
                break
            
            windows.append({
                "train_start": current_start,
                "train_end": train_end,
                "validate_start": validate_start,
                "validate_end": validate_end,
            })
            
            # Step forward
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
        
        Args:
            quotes: Historical market data
            signals: Trading signals
            start_date: Overall start date
            end_date: Overall end date
            config: Backtest configuration
            
        Returns:
            Dictionary with validation results
        """
        windows = self.create_windows(start_date, end_date)
        
        if not windows:
            logger.warning("No walk-forward windows created")
            return {}
        
        results = []
        
        for i, window in enumerate(windows):
            logger.info(
                f"Walk-forward window {i+1}/{len(windows)}: "
                f"Train {window['train_start'].strftime('%Y-%m-%d')} to {window['train_end'].strftime('%Y-%m-%d')}, "
                f"Validate {window['validate_start'].strftime('%Y-%m-%d')} to {window['validate_end'].strftime('%Y-%m-%d')}"
            )
            
            # Filter quotes for validation period
            validate_quotes = [
                q for q in quotes
                if window["validate_start"] <= q.timestamp <= window["validate_end"]
            ]
            
            # Filter signals for validation period
            validate_signals = [
                s for s in signals
                if hasattr(s, 'timestamp') and window["validate_start"] <= s.timestamp <= window["validate_end"]
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
            
            results.append({
                "window": i + 1,
                "train_period": {
                    "start": window["train_start"].isoformat(),
                    "end": window["train_end"].isoformat(),
                },
                "validate_period": {
                    "start": window["validate_start"].isoformat(),
                    "end": window["validate_end"].isoformat(),
                },
                "result": {
                    "total_return": float(result.total_return),
                    "sharpe_ratio": float(result.performance.sharpe_ratio or 0),
                    "max_drawdown": float(result.performance.max_drawdown_percentage or 0),
                    "total_trades": result.performance.total_trades,
                    "win_rate": float(result.performance.win_rate),
                },
            })
        
        # Aggregate results
        if results:
            total_returns = [r["result"]["total_return"] for r in results]
            sharpe_ratios = [r["result"]["sharpe_ratio"] for r in results]
            max_drawdowns = [r["result"]["max_drawdown"] for r in results]
            
            return {
                "windows": results,
                "aggregated": {
                    "avg_return": sum(total_returns) / len(total_returns),
                    "std_return": (
                        (sum((x - sum(total_returns)/len(total_returns))**2 for x in total_returns) / len(total_returns)) ** 0.5
                        if len(total_returns) > 1 else 0
                    ),
                    "avg_sharpe": sum(sharpe_ratios) / len(sharpe_ratios),
                    "avg_max_drawdown": sum(max_drawdowns) / len(max_drawdowns),
                    "consistency": len([r for r in total_returns if r > 0]) / len(total_returns) if total_returns else 0,
                },
            }
        
        return {}


class CrossValidationTemporal:
    """
    Cross-Validation Temporal (TASK-BV-2).
    
    Evaluates consistency of strategies across different time periods.
    """
    
    def __init__(
        self,
        n_folds: int = 5,
    ):
        """
        Initialize temporal cross-validator.
        
        Args:
            n_folds: Number of folds (default: 5)
        """
        self.n_folds = n_folds
    
    def create_folds(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, datetime]]:
        """
        Create temporal folds for cross-validation.
        
        Args:
            start_date: Overall start date
            end_date: Overall end date
            
        Returns:
            List of fold dicts
        """
        total_days = (end_date - start_date).days
        fold_days = total_days // self.n_folds
        
        folds = []
        for i in range(self.n_folds):
            fold_start = start_date + timedelta(days=i * fold_days)
            fold_end = start_date + timedelta(days=(i + 1) * fold_days)
            
            if i == self.n_folds - 1:
                fold_end = end_date  # Last fold goes to end
            
            folds.append({
                "fold": i + 1,
                "start": fold_start,
                "end": fold_end,
            })
        
        return folds
    
    def cross_validate(
        self,
        quotes: List[Quote],
        signals: List[Any],
        config: BacktestConfig,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Run temporal cross-validation.
        
        Args:
            quotes: Historical market data
            signals: Trading signals
            config: Backtest configuration
            start_date: Overall start date
            end_date: Overall end date
            
        Returns:
            Dictionary with cross-validation results
        """
        folds = self.create_folds(start_date, end_date)
        
        results = []
        
        for fold in folds:
            logger.info(
                f"Fold {fold['fold']}/{self.n_folds}: "
                f"{fold['start'].strftime('%Y-%m-%d')} to {fold['end'].strftime('%Y-%m-%d')}"
            )
            
            # Filter data for fold
            fold_quotes = [
                q for q in quotes
                if fold["start"] <= q.timestamp <= fold["end"]
            ]
            
            fold_signals = [
                s for s in signals
                if hasattr(s, 'timestamp') and fold["start"] <= s.timestamp <= fold["end"]
            ]
            
            if not fold_quotes or not fold_signals:
                continue
            
            # Run backtest on fold
            backtester = SimpleBacktester(config)
            result = backtester.run_backtest(
                fold_quotes,
                fold_signals,
                fold["start"],
                fold["end"],
            )
            
            results.append({
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
            })
        
        # Aggregate results
        if results:
            total_returns = [r["result"]["total_return"] for r in results]
            
            return {
                "folds": results,
                "aggregated": {
                    "avg_return": sum(total_returns) / len(total_returns),
                    "std_return": (
                        (sum((x - sum(total_returns)/len(total_returns))**2 for x in total_returns) / len(total_returns)) ** 0.5
                        if len(total_returns) > 1 else 0
                    ),
                    "min_return": min(total_returns),
                    "max_return": max(total_returns),
                    "consistency_score": len([r for r in total_returns if r > 0]) / len(total_returns) if total_returns else 0,
                },
            }
        
        return {}

