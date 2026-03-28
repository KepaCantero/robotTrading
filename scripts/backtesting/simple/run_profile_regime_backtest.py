#!/usr/bin/env python3
"""
Profile-Based Regime Selector Backtest

Tests the new ProfileBasedRegimeSelector with:
- Different investor profiles (SURVIVAL, GROWTH, OPTIMIZATION)
- Hurst exponent-based regime detection
- Multi-window momentum (Gray & Vogel)
- Kelly Criterion position sizing

Compares against the original RegimeBasedSelector.
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

from app.backtesting.data_loader import load_market_data as _load_market_data
from app.backtesting.engine import BacktestEngine
from app.backtesting.models import BacktestConfig
from app.engines.strategy_engines.profile_regime_selector import (
    ProfileBasedRegimeSelector,
)
from app.models.market_data import Quote
from app.domain.strategies.factory import StrategyFactory

logging.basicConfig(
    level=logging.WARNING,
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


def create_profile_selector(
    capital: float,
    adx_threshold: float = 20.0,
    min_volume_ratio: float = 1.0,
) -> ProfileBasedRegimeSelector:
    """Create ProfileBasedRegimeSelector with sub-strategies."""

    factory = StrategyFactory()

    # Create the profile selector
    selector = ProfileBasedRegimeSelector(
        config={
            "name": "profile_regime_selector",
            "capital": capital,
            "regime_lookback": 100,
            "hysteresis_count": 3,
        }
    )

    # Sub-strategies with profile-adjusted thresholds
    strategies_config = [
        {
            "name": "trend_following",
            "config": {
                "name": "trend_following",
                "adx_period": 14,
                "adx_threshold": adx_threshold,
                "macd_fast_period": 12,
                "macd_slow_period": 26,
                "macd_signal_period": 9,
                "min_volume_ratio": min_volume_ratio,
                "max_position_size": 0.10,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.08,
                "min_signal_confidence": 30.0,
            },
        },
        {
            "name": "momentum_engine",
            "config": {
                "name": "momentum_engine",
                "lookback_period": 14,
                "momentum_threshold": 0.015,
                "rsi_period": 14,
                "rsi_oversold": 35,
                "rsi_overbought": 65,
                "max_position_size": 0.10,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.08,
            },
        },
        {
            "name": "mean_reversion_engine",
            "config": {
                "name": "mean_reversion_engine",
                "lookback_period": 15,
                "z_score_threshold": 1.5,
                "volatility_threshold": 0.02,
                "max_position_size": 0.07,
                "stop_loss": 0.02,
                "take_profit": 0.08,
                "min_z_score": 1.2,
            },
        },
        {
            "name": "breakout",
            "config": {
                "name": "breakout",
                "lookback_period": 15,
                "breakout_threshold": 0.015,
                "volume_threshold": 1.0,
                "max_position_size": 0.10,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.10,
            },
        },
    ]

    # Create and add strategies
    for strat_config in strategies_config:
        try:
            strategy = factory.create_strategy(
                name=strat_config["name"],
                config=strat_config["config"],
            )
            selector.add_strategy(strat_config["name"], strategy)
        except Exception as e:
            logger.warning(f"Could not add strategy {strat_config['name']}: {e}")

    return selector


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


def run_profile_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    capital: float,
    profile_name: str,
) -> Dict[str, Any]:
    """Run backtest with specific investor profile."""

    # Load data
    quotes = load_market_data(symbol, start_date, end_date)
    if not quotes:
        return {"error": f"No data for {symbol}"}

    # Create profile selector
    selector = create_profile_selector(capital=capital)

    # Create config
    config = BacktestConfig(
        strategy_name="profile_regime_selector",
        initial_capital=Decimal(str(capital)),
        commission_per_trade=Decimal("0"),
        slippage_percentage=Decimal("0.1"),
        risk_free_rate=Decimal("0.02"),
        max_position_size=Decimal(str(selector.get_profile_config().max_position_size)),
    )

    # Create engine
    engine = BacktestEngine(
        config=config,
        strategy=selector,
        strategy_name="profile_regime_selector",
        enable_risk_envelope=True,
    )

    # Generate signals
    signals = []
    for quote in quotes:
        try:
            quote_signals = selector.generate_signals(quote)
            if quote_signals:
                signals.extend(quote_signals)
        except Exception:
            pass

    # Run backtest
    result = engine.run_backtest(market_data=quotes, signals=signals)

    # Get final regime info
    regime, regime_conf = selector.get_current_regime()
    profile_config = selector.get_profile_config()

    return {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "profile": profile_name,
        "capital": capital,
        "final_capital": float(result.final_capital),
        "total_return": float(result.total_return),
        "total_return_pct": float(result.total_return),
        "max_drawdown_pct": float(result.performance.max_drawdown_percentage)
        if result.performance
        else 0,
        "total_trades": result.performance.total_trades if result.performance else 0,
        "winning_trades": result.performance.winning_trades if result.performance else 0,
        "losing_trades": result.performance.losing_trades if result.performance else 0,
        "win_rate": float(result.performance.win_rate) if result.performance else 0,
        "sharpe_ratio": float(result.performance.sharpe_ratio)
        if result.performance and result.performance.sharpe_ratio
        else 0,
        "signals_generated": len(signals),
        "final_regime": regime.value,
        "regime_confidence": regime_conf,
        "hurst_exponent": selector.hurst_exponent,
        "strategies_enabled": profile_config.strategies_enabled,
        "max_risk_per_trade": float(profile_config.max_risk_per_trade),
        "max_positions": profile_config.max_positions,
    }


def main():
    """Run profile-based regime selector backtest."""

    print("=" * 80)
    print("PROFILE-BASED REGIME SELECTOR BACKTEST")
    print("=" * 80)
    print()

    # Test parameters
    symbols = ["AAPL", "MSFT", "GOOGL"]
    start_date = "2020-01-01"
    end_date = "2024-12-31"

    # Test different profiles
    profiles = [
        ("SURVIVAL", 5000),
        ("GROWTH", 25000),
        ("OPTIMIZATION", 100000),
    ]

    results = {}

    for profile_name, capital in profiles:
        print(f"\n{'=' * 80}")
        print(f"PROFILE: {profile_name} (Capital: ${capital:,})")
        print("=" * 80)
        print()

        profile_results = {}

        for symbol in symbols:
            print(f"  Testing {symbol}...", end=" ", flush=True)
            try:
                result = run_profile_backtest(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    capital=capital,
                    profile_name=profile_name,
                )
                profile_results[symbol] = result

                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print(
                        f"Return: {result['total_return_pct']:.2f}%, "
                        f"Trades: {result['total_trades']}, "
                        f"Sharpe: {result['sharpe_ratio']:.2f}"
                    )

            except Exception as e:
                print(f"Error: {e}")
                profile_results[symbol] = {"error": str(e)}

        results[profile_name] = profile_results

    # Summary comparison
    print("\n" + "=" * 80)
    print("SUMMARY COMPARISON")
    print("=" * 80)
    print()

    # Header
    header = (
        f"{'Profile':<15} {'Symbol':<8} {'Return%':>10} {'Sharpe':>8} {'Trades':>8} {'Win%':>8}"
    )
    print(header)
    print("-" * len(header))

    for profile_name, _ in profiles:
        for symbol in symbols:
            result = results.get(profile_name, {}).get(symbol, {})
            if "error" not in result:
                print(
                    f"{profile_name:<15} {symbol:<8} "
                    f"{result['total_return_pct']:>10.2f} "
                    f"{result['sharpe_ratio']:>8.2f} "
                    f"{result['total_trades']:>8} "
                    f"{result['win_rate']:>8.1f}"
                )

    # Profile analysis
    print("\n" + "=" * 80)
    print("PROFILE CONFIGURATIONS")
    print("=" * 80)
    print()

    for profile_name, capital in profiles:
        selector = create_profile_selector(capital=capital)
        config = selector.get_profile_config()

        print(f"  {profile_name}:")
        print(f"    Max Risk/Trade: {float(config.max_risk_per_trade)*100:.1f}%")
        print(f"    Max Positions: {config.max_positions}")
        print(f"    Target Volatility: {float(config.target_volatility)*100:.1f}%")
        print(f"    Strategies: {', '.join(config.strategies_enabled)}")
        print()

    # Regime analysis
    print("=" * 80)
    print("REGIME DETECTION ANALYSIS")
    print("=" * 80)
    print()

    for profile_name, capital in profiles:
        for symbol in symbols:
            result = results.get(profile_name, {}).get(symbol, {})
            if "error" not in result:
                hurst_str = (
                    f"{result['hurst_exponent']:.3f}"
                    if result.get('hurst_exponent') is not None
                    else "N/A"
                )
                print(
                    f"  {profile_name} / {symbol}: "
                    f"Regime={result['final_regime']}, "
                    f"Confidence={result['regime_confidence']:.1f}%, "
                    f"Hurst={hurst_str}"
                )

    # Save results
    output_dir = Path("results/profile_regime_backtest")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    with open(output_file, "w") as f:
        yaml.dump(results, f, default_flow_style=False)

    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()
