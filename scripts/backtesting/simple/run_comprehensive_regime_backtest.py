#!/usr/bin/env python3
"""
Comprehensive Regime Selector Backtest

This script performs:
1. Signal generation with adjusted thresholds for more signals
2. Sharpe ratio analysis and correction
3. Buy-and-hold benchmark comparison
4. Multi-symbol testing for diversification
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

import numpy as np
import yaml

from app.backtesting.data_loader import load_market_data as _load_market_data
from app.backtesting.engine import BacktestEngine
from app.backtesting.models import BacktestConfig
from app.models.market_data import Quote
from app.domain.strategies.factory import StrategyFactory

logging.basicConfig(
    level=logging.WARNING,  # Reduced logging for cleaner output
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_market_data(symbol: str, start_date: str, end_date: str) -> List[Quote]:
    """Load market data for backtesting."""
    return _load_market_data(
        symbol=symbol,
        start_date=datetime.strptime(start_date, "%Y-%m-%d"),
        end_date=datetime.strptime(end_date, "%Y-%m-%d"),
        timeframe="1d",
    )


def create_regime_selector_ensemble(
    adx_threshold: float = 20.0,  # Lowered from 25.0 for more signals
    min_volume_ratio: float = 1.0,  # Lowered from 1.2 for more signals
    regime_lookback: int = 100,
    volatility_threshold: float = 0.30,
) -> Any:
    """Create RegimeBasedSelector with adjustable thresholds."""

    factory = StrategyFactory()

    ensemble_config = {
        "name": "regime_selector",
        "description": "Adaptive strategy selector with adjusted thresholds",
        "min_strategies_for_signal": 1,
        "regime_lookback": regime_lookback,
        "trend_threshold": 0.02,
        "volatility_threshold": volatility_threshold,
        "hysteresis_count": 3,
        "regime_strategy_map": {
            "trending_up": ["trend_following", "momentum_engine", "breakout"],
            "trending_down": ["trend_following", "momentum_engine"],
            "mean_reverting": ["mean_reversion_engine"],
            "high_volatility": ["breakout", "momentum_engine"],
            "low_volatility": ["mean_reversion_engine"],
            "unknown": [],
        },
    }

    # Sub-strategies with lowered thresholds
    strategies_config = [
        {
            "name": "trend_following",
            "weight": 1.0,
            "config": {
                "name": "trend_following",
                "adx_period": 14,
                "adx_threshold": adx_threshold,  # Lowered for more signals
                "macd_fast_period": 12,
                "macd_slow_period": 26,
                "macd_signal_period": 9,
                "min_volume_ratio": min_volume_ratio,  # Lowered for more signals
                "max_position_size": 0.10,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.08,
                "min_signal_confidence": 30.0,  # Lowered from 50
            },
        },
        {
            "name": "momentum_engine",
            "weight": 1.0,
            "config": {
                "name": "momentum_engine",
                "lookback_period": 14,
                "momentum_threshold": 0.015,  # Lowered for more signals
                "rsi_period": 14,
                "rsi_oversold": 35,
                "rsi_overbought": 65,
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
                "lookback_period": 15,  # Shorter for more signals
                "breakout_threshold": 0.015,  # Lowered for more signals
                "volume_threshold": 1.0,  # Lowered for more signals
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
                "lookback_period": 15,
                "z_score_threshold": 1.5,  # Lowered for more signals
                "volatility_threshold": 0.02,
                "max_position_size": 0.07,
                "stop_loss": 0.02,
                "take_profit": 0.08,
                "min_z_score": 1.2,
            },
        },
    ]

    return factory.create_ensemble(
        ensemble_type="regime_selector",
        ensemble_config=ensemble_config,
        strategies_config=strategies_config,
    )


def calculate_buy_and_hold(quotes: List[Quote], initial_capital: float) -> Dict[str, Any]:
    """Calculate buy and hold benchmark."""
    if not quotes:
        return {"error": "No quotes"}

    prices = [float(q.close or q.last or 0) for q in quotes if (q.close or q.last)]
    if len(prices) < 2:
        return {"error": "Insufficient data"}

    start_price = prices[0]
    end_price = prices[-1]
    shares = initial_capital / start_price
    final_value = shares * end_price

    # Calculate max drawdown
    peak = prices[0]
    max_dd = 0.0
    for price in prices:
        if price > peak:
            peak = price
        dd = (peak - price) / peak
        if dd > max_dd:
            max_dd = dd

    total_return = (end_price - start_price) / start_price
    years = len(prices) / 252
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

    return {
        "start_price": start_price,
        "end_price": end_price,
        "shares": shares,
        "final_value": final_value,
        "total_return": total_return,
        "total_return_pct": total_return * 100,
        "annualized_return": annualized_return * 100,
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd * 100,
    }


def calculate_corrected_sharpe(
    trades: List, risk_free_rate: float = 0.02
) -> Dict[str, float]:
    """
    Calculate Sharpe ratio with proper handling of edge cases.

    Issues with original calculation:
    1. Too few trades causes unstable std dev
    2. Similar P&L values cause near-zero std dev
    3. Annualization can amplify errors
    """
    if not trades or len(trades) < 2:
        return {"sharpe": 0.0, "issue": "insufficient_trades"}

    # Get P&L from closed trades
    pnls = []
    for t in trades:
        if hasattr(t, "pnl") and t.pnl is not None:
            pnls.append(float(t.pnl))

    if len(pnls) < 2:
        return {"sharpe": 0.0, "issue": "insufficient_closed_trades"}

    # Calculate returns
    mean_pnl = np.mean(pnls)
    std_pnl = np.std(pnls)

    # Issue detection
    issues = []
    if len(pnls) < 10:
        issues.append("few_trades")
    if std_pnl < mean_pnl * 0.1:
        issues.append("low_volatility")
    if std_pnl < 1:
        issues.append("very_low_std")

    # Apply minimum volatility floor (5% annualized)
    MIN_VOL = 0.05 / np.sqrt(252)  # Daily minimum
    std_pnl = max(std_pnl, MIN_VOL)

    # Calculate Sharpe (simplified, using trade-level not time-series)
    if std_pnl > 0:
        sharpe = (mean_pnl / std_pnl) * np.sqrt(252) - risk_free_rate
    else:
        sharpe = 0.0

    return {
        "sharpe": sharpe,
        "mean_pnl": mean_pnl,
        "std_pnl": std_pnl,
        "num_trades": len(pnls),
        "issues": issues,
    }


def run_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000.0,
    adx_threshold: float = 20.0,
    min_volume_ratio: float = 1.0,
) -> Dict[str, Any]:
    """Run backtest with adjustable parameters."""

    # Load data
    quotes = load_market_data(symbol, start_date, end_date)
    if not quotes:
        return {"error": f"No data for {symbol}"}

    # Create ensemble
    ensemble = create_regime_selector_ensemble(
        adx_threshold=adx_threshold,
        min_volume_ratio=min_volume_ratio,
    )

    # Create config
    config = BacktestConfig(
        strategy_name="regime_selector",
        initial_capital=Decimal(str(initial_capital)),
        commission_per_trade=Decimal("0"),
        slippage_percentage=Decimal("0.1"),
        risk_free_rate=Decimal("0.02"),
        max_position_size=Decimal("0.10"),
    )

    # Create engine
    engine = BacktestEngine(
        config=config,
        strategy=ensemble,
        strategy_name="regime_selector",
        enable_risk_envelope=True,
    )

    # Generate signals
    signals = []
    for quote in quotes:
        try:
            quote_signals = ensemble.generate_signals(quote)
            if quote_signals:
                signals.extend(quote_signals)
        except Exception:
            pass

    # Run backtest
    result = engine.run_backtest(market_data=quotes, signals=signals)

    # Calculate buy and hold
    buy_hold = calculate_buy_and_hold(quotes, initial_capital)

    # Calculate corrected Sharpe
    sharpe_analysis = calculate_corrected_sharpe(result.trades)

    return {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": initial_capital,
        "final_capital": float(result.final_capital),
        "total_return": float(result.total_return),
        # BUG FIX: total_return is already in percentage (calculated as * 100 in engine)
        "total_return_pct": float(result.total_return),  # Already in %
        "max_drawdown_pct": float(result.performance.max_drawdown_percentage)
        if result.performance
        else 0,
        "total_trades": result.performance.total_trades if result.performance else 0,
        "winning_trades": result.performance.winning_trades if result.performance else 0,
        "losing_trades": result.performance.losing_trades if result.performance else 0,
        "win_rate": float(result.performance.win_rate) if result.performance else 0,
        "sharpe_original": float(result.performance.sharpe_ratio)
        if result.performance and result.performance.sharpe_ratio
        else 0,
        "sharpe_analysis": sharpe_analysis,
        "signals_generated": len(signals),
        "buy_hold": buy_hold,
    }


def main():
    """Run comprehensive backtest analysis."""

    print("=" * 70)
    print("COMPREHENSIVE REGIME SELECTOR BACKTEST ANALYSIS")
    print("=" * 70)
    print()

    # Test parameters
    symbols = ["AAPL", "MSFT", "GOOGL", "SPY", "QQQ"]
    start_date = "2020-01-01"
    end_date = "2024-12-31"
    initial_capital = 100000.0

    # Test 1: Original thresholds (ADX=25, vol=1.2)
    print("TEST 1: ORIGINAL THRESHOLDS (ADX=25, VolRatio=1.2)")
    print("-" * 70)

    results_original = {}
    for symbol in symbols:
        print(f"  Testing {symbol}...", end=" ", flush=True)
        try:
            result = run_backtest(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                adx_threshold=25.0,
                min_volume_ratio=1.2,
            )
            results_original[symbol] = result
            print(f"Return: {result['total_return_pct']:.2f}%, Trades: {result['total_trades']}")
        except Exception as e:
            print(f"Error: {e}")
            results_original[symbol] = {"error": str(e)}

    print()

    # Test 2: Lowered thresholds (ADX=20, vol=1.0)
    print("TEST 2: LOWERED THRESHOLDS (ADX=20, VolRatio=1.0)")
    print("-" * 70)

    results_lowered = {}
    for symbol in symbols:
        print(f"  Testing {symbol}...", end=" ", flush=True)
        try:
            result = run_backtest(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                adx_threshold=20.0,
                min_volume_ratio=1.0,
            )
            results_lowered[symbol] = result
            print(f"Return: {result['total_return_pct']:.2f}%, Trades: {result['total_trades']}")
        except Exception as e:
            print(f"Error: {e}")
            results_lowered[symbol] = {"error": str(e)}

    print()

    # Test 3: Buy and Hold Comparison
    print("TEST 3: BUY AND HOLD BENCHMARK")
    print("-" * 70)

    for symbol in symbols:
        if symbol in results_original and "buy_hold" in results_original[symbol]:
            bh = results_original[symbol]["buy_hold"]
            if "error" not in bh:
                print(
                    f"  {symbol}: Return={bh['total_return_pct']:.2f}%, "
                    f"MaxDD={bh['max_drawdown_pct']:.2f}%"
                )

    print()

    # Summary comparison
    print("=" * 70)
    print("SUMMARY COMPARISON")
    print("=" * 70)
    print()
    print(
        f"{'Symbol':<8} {'B&H Ret%':>10} {'Orig Ret%':>10} {'Orig Trds':>10} "
        f"{'Low Ret%':>10} {'Low Trds':>10}"
    )
    print("-" * 70)

    for symbol in symbols:
        bh_ret = (
            results_original.get(symbol, {})
            .get("buy_hold", {})
            .get("total_return_pct", 0)
        )
        orig_ret = results_original.get(symbol, {}).get("total_return_pct", 0)
        orig_trds = results_original.get(symbol, {}).get("total_trades", 0)
        low_ret = results_lowered.get(symbol, {}).get("total_return_pct", 0)
        low_trds = results_lowered.get(symbol, {}).get("total_trades", 0)

        print(
            f"{symbol:<8} {bh_ret:>10.2f} {orig_ret:>10.2f} {orig_trds:>10} "
            f"{low_ret:>10.2f} {low_trds:>10}"
        )

    # Sharpe Analysis
    print()
    print("=" * 70)
    print("SHARPE RATIO ANALYSIS")
    print("=" * 70)
    print()

    for symbol in symbols:
        if symbol in results_lowered:
            result = results_lowered[symbol]
            if "sharpe_analysis" in result:
                sa = result["sharpe_analysis"]
                issues = ", ".join(sa.get("issues", []))
                print(f"  {symbol}:")
                print(f"    Original Sharpe: {result.get('sharpe_original', 0):.2f}")
                print(f"    Corrected Sharpe: {sa.get('sharpe', 0):.2f}")
                print(f"    Issues: {issues if issues else 'None'}")
                print()

    # Save results
    output_dir = Path("results/regime_selector_backtest")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    with open(output_file, "w") as f:
        yaml.dump(
            {
                "original_thresholds": results_original,
                "lowered_thresholds": results_lowered,
            },
            f,
            default_flow_style=False,
        )

    print(f"Results saved to {output_file}")


if __name__ == "__main__":
    main()
