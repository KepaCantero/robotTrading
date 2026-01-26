#!/usr/bin/env python3
"""
Ejecutar backtesting automático de todas las estrategias disponibles.
Genera resultados detallados, métricas, logs, gráficos y documentación.
"""

import asyncio
import hashlib
import json
import logging
import subprocess
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

# Add project root to path
# scripts/backtesting/ -> scripts/ -> project_root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.backtesting.data_loader import DataLoader
from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, BacktestResult
from app.strategies.factory import StrategyFactory
from app.strategies.momentum import MomentumStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.pairs_trading import PairsTradingStrategy
from app.engines.strategy_engines import (
    BreakoutStrategyEngine,
    TrendFollowingStrategyEngine,
    ArbitrageStrategyEngine,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BacktestRunner:
    """Ejecutar backtesting completo de todas las estrategias."""
    
    def __init__(self, strategies_config_path: str = "config/trading_strategies.yaml"):
        """Inicializar runner."""
        # project_root ya está definido globalmente
        self.results_dir = project_root / "docs" / "BACKTEST_RESULTS"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Load strategies configuration
        with open(project_root / strategies_config_path, 'r') as f:
            config = yaml.safe_load(f)
            self.strategies_config = config['strategies']
        
        self.factory = StrategyFactory()
        
    def run_all_backtests(self):
        """Ejecutar backtesting para todas las estrategias."""
        results = []
        
        for strategy_name, strategy_config in self.strategies_config.items():
            logger.info(f"\n{'='*80}")
            logger.info(f"Running backtest for strategy: {strategy_name}")
            logger.info(f"{'='*80}\n")
            
            try:
                result = self.run_strategy_backtest(strategy_name, strategy_config)
                if result:
                    results.append(result)
                    logger.info(f"✅ Completed backtest for {strategy_name}")
                else:
                    logger.warning(f"⚠️ No results for {strategy_name}")
            except Exception as e:
                logger.error(f"❌ Error in backtest for {strategy_name}: {e}")
        
        # Generate summary
        self.generate_summary_index(results)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Completed backtesting for {len(results)} strategies")
        logger.info(f"{'='*80}\n")
        
        return results
    
    def run_strategy_backtest(self, strategy_name: str, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar backtest para una estrategia."""
        # Load data
        symbol = "AAPL"  # Default symbol
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        loader = DataLoader()
        quotes = loader.load_market_data(symbol, start_date, end_date)
        
        if not quotes:
            logger.error(f"No data available for {strategy_name}")
            return None
        
        # Create strategy
        config = strategy_config.get('config', {})
        config['name'] = strategy_name
        
        if strategy_name == 'momentum':
            strategy = MomentumStrategy(config)
        elif strategy_name == 'mean_reversion':
            strategy = MeanReversionStrategy(config)
        elif strategy_name == 'pairs_trading':
            strategy = PairsTradingStrategy(config)
        elif strategy_name == 'breakout':
            strategy = BreakoutStrategyEngine(config)
        elif strategy_name == 'trend_following':
            strategy = TrendFollowingStrategyEngine(config)
        elif strategy_name == 'arbitrage':
            strategy = ArbitrageStrategyEngine(config)
        else:
            logger.error(f"Unknown strategy: {strategy_name}")
            return None
        
        # Generate signals
        signals = []
        for quote in quotes:
            try:
                signals.extend(strategy.generate_signals(quote))
            except Exception as e:
                logger.debug(f"Signal error: {e}")
        
        if not signals:
            logger.warning(f"No signals generated for {strategy_name}")
            return None
        
        # Create backtest config
        backtest_config = BacktestConfig(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=100000,
            stop_loss=float(config.get('stop_loss', 0.02)),
            take_profit=float(config.get('take_profit', 0.05)),
            commission=0.001,
            slippage=0.0005,
        )
        
        # Run backtest
        backtester = SimpleBacktester(backtest_config)
        result = backtester.run_backtest(quotes, signals)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_strategy_results(strategy_name, result, timestamp)
        
        return {
            'strategy_name': strategy_name,
            'result': result,
            'timestamp': timestamp,
        }
    
    def save_strategy_results(self, strategy_name: str, result: BacktestResult, timestamp: str):
        """Guardar resultados de backtest."""
        # Create strategy directory
        strategy_dir = self.results_dir / strategy_name
        strategy_dir.mkdir(exist_ok=True)
        
        # Save metrics JSON
        metrics = self.extract_detailed_metrics(result)
        metrics_path = strategy_dir / f"metrics_{timestamp}.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        
        # Save trades CSV
        if result.trades:
            trades_df = pd.DataFrame([
                {
                    'timestamp': t.entry_time,
                    'type': t.side,
                    'symbol': t.symbol,
                    'entry_price': float(t.entry_price),
                    'exit_price': float(t.exit_price) if t.exit_price else 0,
                    'quantity': float(t.quantity),
                    'pnl': float(t.pnl) if t.pnl else 0,
                    'reason': t.reason if t.reason else '',
                    'status': t.status.value,
                }
                for t in result.trades
            ])
            
            trades_path = strategy_dir / f"trades_{timestamp}.csv"
            trades_df.to_csv(trades_path, index=False)
        
        # Save summary report
        report_path = strategy_dir / f"summary_{timestamp}.md"
        self.generate_strategy_report(strategy_name, result, metrics, report_path)
        
        logger.info(f"Saved results to {strategy_dir}")
    
    def extract_detailed_metrics(self, result: BacktestResult) -> Dict[str, Any]:
        """Extraer métricas detalladas del resultado."""
        performance = result.performance
        config = result.config
        
        metrics = {
            # General Performance
            'strategy': result.strategy_name,
            'period': f"{result.start_date} to {result.end_date}",
            'initial_capital': float(config.initial_capital) if config else 100000,
            'final_capital': float(result.final_capital),
            'total_pnl': float(performance.total_pnl),
            'total_return_pct': float(result.total_return),
            'annualized_return_pct': float(result.annualized_return) if result.annualized_return else 0,
            'total_trades': performance.total_trades,
            'winning_trades': performance.winning_trades,
            'losing_trades': performance.losing_trades,
            'win_rate_pct': float(performance.win_rate),
            'avg_trade_pnl': float(performance.total_pnl) / performance.total_trades if performance.total_trades > 0 else 0,
            'profit_factor': float(performance.profit_factor) if hasattr(performance, 'profit_factor') and performance.profit_factor else 0,
            
            # Risk and Volatility
            'max_drawdown_pct': float(performance.max_drawdown_percentage),
            'volatility_annualized': 0,  # Would need to calculate
            'sharpe_ratio': float(performance.sharpe_ratio) if performance.sharpe_ratio else 0,
            'sortino_ratio': float(performance.sortino_ratio) if performance.sortino_ratio else 0,
            
            # Metadata
            'timestamp_utc': datetime.utcnow().isoformat(),
            'code_hash': self.get_git_hash(),
            'commit_sha': self.get_git_hash(),
            'environment': 'local',
        }
        
        return metrics
    
    def get_git_hash(self) -> str:
        """Get current git hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            return result.stdout.strip()[:12]
        except Exception:
            return "unknown"
    
    def generate_strategy_report(self, strategy_name: str, result: BacktestResult, metrics: Dict[str, Any], report_path: Path):
        """Generate detailed report for a strategy."""
        report = f"""# Backtest Report: {strategy_name}

**Generated:** {metrics['timestamp_utc']}
**Period:** {metrics['period']}
**Strategy:** {result.strategy_name}

## Executive Summary

This backtest executed **{metrics['total_trades']}** trades with a win rate of **{metrics['win_rate_pct']:.1f}%**.

### Key Metrics

- **Total P&L:** ${metrics['total_pnl']:,.2f}
- **Return:** {metrics['total_return_pct']:.2f}%
- **Sharpe Ratio:** {metrics['sharpe_ratio']:.2f}
- **Max Drawdown:** {metrics['max_drawdown_pct']:.2f}%
- **Final Capital:** ${metrics['final_capital']:,.2f}

## Performance Metrics

| Metric | Value |
|--------|-------|
| Initial Capital | ${metrics['initial_capital']:,.2f} |
| Final Capital | ${metrics['final_capital']:,.2f} |
| Total P&L | ${metrics['total_pnl']:,.2f} |
| Total Return | {metrics['total_return_pct']:.2f}% |
| Win Rate | {metrics['win_rate_pct']:.1f}% |
| Sharpe Ratio | {metrics['sharpe_ratio']:.2f} |
| Sortino Ratio | {metrics['sortino_ratio']:.2f} |
| Max Drawdown | {metrics['max_drawdown_pct']:.2f}% |

## Audit Information

- **Code Hash:** {metrics['code_hash']}
- **Commit SHA:** {metrics['commit_sha']}
- **Environment:** {metrics['environment']}
- **Timestamp:** {metrics['timestamp_utc']}
"""
        
        with open(report_path, 'w') as f:
            f.write(report)
    
    def generate_summary_index(self, results: List[Dict[str, Any]]):
        """Generate summary index of all backtests."""
        summary_path = self.results_dir / "summary_index.md"
        
        summary = """# Backtest Results Summary

Automated backtesting of all available strategies.

## Results Overview

| Strategy | Period | Trades | Win% | PnL | Sharpe | Max DD | Return | Final Capital |
|----------|--------|--------|------|-----|--------|--------|--------|---------------|
"""
        
        for result in results:
            backtest_result = result['result']
            perf = backtest_result.performance
            
            sharpe = f"{perf.sharpe_ratio:.2f}" if perf.sharpe_ratio else "N/A"
            
            summary += f"""| {result['strategy_name']} | {backtest_result.start_date.year}-{backtest_result.end_date.year} | {perf.total_trades} | {perf.win_rate:.1f}% | ${perf.total_pnl:,.2f} | {sharpe} | {perf.max_drawdown_percentage:.2f}% | {backtest_result.total_return:.2f}% | ${backtest_result.final_capital:,.2f} |\n"""
        
        with open(summary_path, 'w') as f:
            f.write(summary)


if __name__ == "__main__":
    runner = BacktestRunner()
    results = runner.run_all_backtests()
    print(f"\n✅ Completed {len(results)} backtests\n")

