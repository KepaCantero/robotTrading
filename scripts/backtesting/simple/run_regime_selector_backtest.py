#!/usr/bin/env python3
"""
Regime Selector Ensemble Backtest

This script runs a backtest using the RegimeBasedSelector ensemble,
which automatically adapts to market conditions:
- trending_up -> uses trend_following, momentum
- trending_down -> uses trend_following
- mean_reverting -> uses mean_reversion
- high_volatility -> uses breakout, momentum
- low_volatility -> uses mean_reversion

This is Option B from the strategy analysis - using an adaptive strategy.
"""

import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
# scripts/backtesting/simple/ -> scripts/backtesting/ -> scripts/ -> project_root
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import yaml

from app.backtesting.engine import BacktestEngine
from app.models.market_data import Quote
from app.domain.strategies.factory import StrategyFactory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_market_data(symbol: str, start_date: str, end_date: str) -> List[Quote]:
    """Load market data for backtesting."""
    from app.backtesting.data_loader import load_market_data as _load_market_data

    logger.info(f"Loading data for {symbol} from {start_date} to {end_date}...")

    quotes = _load_market_data(
        symbol=symbol,
        start_date=datetime.strptime(start_date, "%Y-%m-%d"),
        end_date=datetime.strptime(end_date, "%Y-%m-%d"),
        timeframe="1d",
    )

    logger.info(f"Loaded {len(quotes)} quotes for {symbol}")
    return quotes


def create_regime_selector_ensemble() -> Any:
    """
    Create a RegimeBasedSelector ensemble with sub-strategies.

    This ensemble automatically detects market regime and selects
    the appropriate strategies:
    - trending_up: trend_following, momentum, breakout
    - trending_down: trend_following, momentum
    - mean_reverting: mean_reversion
    - high_volatility: breakout, momentum
    - low_volatility: mean_reversion
    """
    factory = StrategyFactory()

    # Ensemble configuration with improved parameters
    ensemble_config = {
        "name": "regime_selector",
        "description": "Adaptive strategy selector based on market regime",
        "min_strategies_for_signal": 1,
        "regime_lookback": 100,  # Increased from 50
        "trend_threshold": 0.02,  # 2% for trending
        "volatility_threshold": 0.30,  # 30% annualized (increased from 2.5%)
        "hysteresis_count": 3,  # Require 3 consecutive detections
        # Regime -> strategy mapping (using correct engine names)
        "regime_strategy_map": {
            "trending_up": ["trend_following", "momentum_engine", "breakout"],
            "trending_down": ["trend_following", "momentum_engine"],
            "mean_reverting": ["mean_reversion_engine"],
            "high_volatility": ["breakout", "momentum_engine"],
            "low_volatility": ["mean_reversion_engine"],
            "unknown": [],
        },
    }

    # Sub-strategies configuration
    strategies_config = [
        {
            "name": "trend_following",
            "weight": 1.0,
            "config": {
                "name": "trend_following",
                "adx_period": 14,
                "adx_threshold": 25.0,
                "macd_fast_period": 12,
                "macd_slow_period": 26,
                "macd_signal_period": 9,
                "min_volume_ratio": 1.2,
                "max_position_size": 0.10,
                "stop_loss_pct": 0.025,
                "take_profit_pct": 0.08,
            },
        },
        {
            "name": "momentum_engine",
            "weight": 1.0,
            "config": {
                "name": "momentum_engine",
                "lookback_period": 14,
                "momentum_threshold": 0.02,
                "rsi_period": 14,
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "max_position_size": 0.10,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.08,
            },
        },
        {
            "name": "breakout",
            "weight": 1.0,
            "config": {
                "name": "breakout",
                "lookback_period": 20,
                "breakout_threshold": 0.02,
                "volume_threshold": 1.5,
                "max_position_size": 0.10,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.10,
            },
        },
        {
            "name": "mean_reversion_engine",
            "weight": 1.0,
            "config": {
                "name": "mean_reversion_engine",
                "lookback_period": 20,
                "z_score_threshold": 2.0,
                "volatility_threshold": 0.02,
                "max_position_size": 0.07,
                "stop_loss": 0.015,
                "take_profit": 0.10,
                "min_z_score": 1.5,
            },
        },
    ]

    # Create the ensemble
    ensemble = factory.create_ensemble(
        ensemble_type="regime_selector",
        ensemble_config=ensemble_config,
        strategies_config=strategies_config,
    )

    logger.info(f"Created regime_selector ensemble with {len(strategies_config)} sub-strategies")
    return ensemble


def run_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000.0,
    commission: float = 0.0,
    slippage: float = 0.001,
) -> Dict[str, Any]:
    """
    Run backtest with the regime_selector ensemble.

    Args:
        symbol: Stock symbol to test
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        initial_capital: Initial capital
        commission: Commission per trade (as decimal)
        slippage: Slippage per trade (as decimal)

    Returns:
        Dictionary with backtest results
    """
    from app.backtesting.models import BacktestConfig

    logger.info("=" * 60)
    logger.info("REGIME SELECTOR ENSEMBLE BACKTEST")
    logger.info("=" * 60)
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Period: {start_date} to {end_date}")
    logger.info(f"Initial Capital: ${initial_capital:,.2f}")
    logger.info(f"Commission: {commission * 100:.2f}%")
    logger.info(f"Slippage: {slippage * 100:.3f}%")
    logger.info("=" * 60)

    # Load market data
    quotes = load_market_data(symbol, start_date, end_date)
    if not quotes:
        logger.error(f"No data loaded for {symbol}")
        return {"error": "No data loaded"}

    # Create the regime_selector ensemble
    ensemble = create_regime_selector_ensemble()

    # Create backtest config
    config = BacktestConfig(
        strategy_name="regime_selector",
        initial_capital=Decimal(str(initial_capital)),
        commission_per_trade=Decimal(str(commission)),
        slippage_percentage=Decimal(str(slippage * 100)),  # As percentage
        risk_free_rate=Decimal("0.02"),
        max_position_size=Decimal("0.10"),
        stop_loss_percentage=Decimal("5.0"),
        take_profit_percentage=Decimal("10.0"),
    )

    # Create backtest engine
    engine = BacktestEngine(
        config=config,
        strategy=ensemble,
        strategy_name="regime_selector",
        enable_risk_envelope=True,
    )

    # Run backtest
    logger.info("Running backtest...")
    start_time = datetime.now()

    # Generate signals from the ensemble
    signals = []
    for quote in quotes:
        try:
            quote_signals = ensemble.generate_signals(quote)
            if quote_signals:
                signals.extend(quote_signals)
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.warning(f"Error generating signals for {quote.symbol}: {e}")

    logger.info(f"Generated {len(signals)} signals from ensemble")

    # Run backtest with signals
    result = engine.run_backtest(
        market_data=quotes,
        signals=signals,
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info(f"Backtest completed in {duration:.2f} seconds")

    # Extract metrics
    perf = result.performance
    metrics = {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": initial_capital,
        "final_capital": float(result.final_capital),
        "total_return": float(result.total_return),
        "total_return_pct": float(result.total_return) * 100 if result.total_return else 0,
        "total_trades": perf.total_trades if perf else 0,
        "winning_trades": perf.winning_trades if perf else 0,
        "losing_trades": perf.losing_trades if perf else 0,
        "win_rate": float(perf.win_rate) if perf and perf.win_rate else 0,
        "sharpe_ratio": float(perf.sharpe_ratio) if perf and perf.sharpe_ratio else 0,
        "max_drawdown": float(perf.max_drawdown) if perf and perf.max_drawdown else 0,
        "max_drawdown_pct": float(perf.max_drawdown_percentage) if perf and perf.max_drawdown_percentage else 0,
        "duration_seconds": duration,
    }

    # Print results
    print_results(metrics)

    return metrics


def print_results(metrics: Dict[str, Any]) -> None:
    """Print backtest results in a formatted table."""
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS - REGIME SELECTOR ENSEMBLE")
    print("=" * 60)
    print(f"Symbol:           {metrics['symbol']}")
    print(f"Period:           {metrics['start_date']} to {metrics['end_date']}")
    print("-" * 60)
    print("PERFORMANCE")
    print("-" * 60)
    print(f"Initial Capital:  ${metrics['initial_capital']:,.2f}")
    print(f"Final Capital:    ${metrics['final_capital']:,.2f}")
    print(f"Total Return:     {metrics['total_return_pct']:+.2f}%")
    print(f"Sharpe Ratio:     {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown:     {metrics['max_drawdown_pct']:.2f}%")
    print("-" * 60)
    print("TRADES")
    print("-" * 60)
    print(f"Total Trades:     {metrics['total_trades']}")
    print(f"Winning Trades:   {metrics['winning_trades']}")
    print(f"Losing Trades:    {metrics['losing_trades']}")
    print(f"Win Rate:         {metrics['win_rate'] * 100:.1f}%")
    print("=" * 60)

    # Recommendation based on metrics
    sharpe = metrics['sharpe_ratio']
    return_pct = metrics['total_return_pct']
    max_dd = abs(metrics['max_drawdown_pct'])

    if sharpe >= 1.0 and return_pct > 0 and max_dd < 20:
        recommendation = "APPROVED"
    elif sharpe >= 0.5 and return_pct > -10 and max_dd < 30:
        recommendation = "REVISION"
    else:
        recommendation = "REJECTED"

    print(f"Recommendation:   {recommendation}")
    print("=" * 60)


def main():
    """Main entry point."""
    # Test with AAPL for 5 years (2020-2024)
    # This covers various market conditions:
    # - 2020: COVID crash and recovery
    # - 2021: Bull market
    # - 2022: Bear market
    # - 2023: Recovery
    # - 2024: Continued growth
    results = run_backtest(
        symbol="AAPL",
        start_date="2020-01-01",
        end_date="2024-12-31",
        initial_capital=100000.0,
        commission=0.0,
        slippage=0.001,
    )

    # Save results
    output_dir = Path("results/regime_selector_backtest")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"backtest_5years_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    with open(output_file, "w") as f:
        yaml.dump(results, f, default_flow_style=False)

    logger.info(f"Results saved to {output_file}")

    return results


if __name__ == "__main__":
    main()
