#!/usr/bin/env python3
"""
Simple Profile Comparison - Uses Local Historical Data

Compares different investor profiles to see which generates more money.
Uses a small time sample for quick verification.
"""

import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.models.signal import Signal, SignalSource, SignalType, SignalStrength
from app.models.market_data import Quote

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Define profile configurations
# Using momentum strategy - lower RSI is actually good for buying in uptrend
PROFILES = {
    "Aggressive Growth": {
        "rsi_threshold": 50,      # Buy when RSI crosses above 50 (momentum entry)
        "ema_crossover": True,     # Use EMA crossover signal
        "volume_threshold": 0.8,  # Lower volume requirement
        "stop_loss": 0.05,        # Wider stop loss
        "take_profit": 0.20,      # Higher profit target
        "max_position_pct": 0.20, # Larger positions
    },
    "Balanced": {
        "rsi_threshold": 45,      # Buy when RSI > 45
        "ema_crossover": True,     # Use EMA crossover signal
        "volume_threshold": 1.0,  # Standard volume
        "stop_loss": 0.03,        # Moderate stop loss
        "take_profit": 0.12,      # Moderate profit target
        "max_position_pct": 0.10, # Standard positions
    },
    "Conservative": {
        "rsi_threshold": 40,      # Buy when RSI > 40
        "ema_crossover": False,    # Wait for stronger confirmation
        "volume_threshold": 1.2,  # Higher volume requirement
        "stop_loss": 0.02,        # Tighter stop loss
        "take_profit": 0.08,      # Lower profit target
        "max_position_pct": 0.05, # Smaller positions
    },
}


def load_market_data(symbols, start_date, end_date):
    """Load market data from local CSV files."""
    print(f"Loading data for {symbols} from {start_date} to {end_date}...")
    all_data = {}
    data_dir = Path(__file__).parent.parent / "data" / "historical"

    for symbol in symbols:
        csv_path = data_dir / f"{symbol}.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

            if not df.empty:
                all_data[symbol] = df
                print(f"  ✓ {symbol}: {len(df)} bars ({df['date'].min().date()} to {df['date'].max().date()})")
            else:
                print(f"  ✗ {symbol}: No data in date range")
        else:
            print(f"  ✗ {symbol}: File not found ({csv_path})")

    return all_data


def generate_signals(data, profile_config):
    """Generate trading signals based on profile configuration."""
    signals = []
    rsi_threshold = profile_config["rsi_threshold"]
    vol_min = profile_config["volume_threshold"]
    use_ema_cross = profile_config.get("ema_crossover", False)

    for symbol, df in data.items():
        # Calculate indicators
        df = df.copy()
        df['EMA_12'] = df['close'].ewm(span=12).mean()
        df['EMA_26'] = df['close'].ewm(span=26).mean()
        df['RSI'] = compute_rsi(df['close'], 14)
        df['Volume_MA'] = df['volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['volume'] / df['Volume_MA']

        # Detect EMA crossover (EMA_12 crosses above EMA_26)
        ema_cross = (df['EMA_12'] > df['EMA_26']) & (df['EMA_12'].shift(1) <= df['EMA_26'].shift(1))

        # Generate buy signals
        # For momentum: RSI crossing above threshold (bullish momentum building)
        rsi_cross_up = (df['RSI'] > rsi_threshold) & (df['RSI'].shift(1) <= rsi_threshold)

        if use_ema_cross:
            # Require EMA crossover + RSI confirmation
            buy_conditions = ema_cross & (df['RSI'] > 40) & (df['Volume_Ratio'] > vol_min)
        else:
            # Conservative: Require RSI cross up + volume + trend
            buy_conditions = rsi_cross_up & (df['Volume_Ratio'] > vol_min) & (df['EMA_12'] > df['EMA_26'])

        for i in range(1, len(df)):
            if buy_conditions.iloc[i]:
                signal = Signal(
                    signal_id=f"{symbol}_{i}_{df['date'].iloc[i].strftime('%Y%m%d')}",
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=70.0,
                    liquidity_score=80.0,
                    priority_score=70.0,
                    source=SignalSource.MOMENTUM,
                    price=Decimal(str(df['close'].iloc[i])),
                    volume=Decimal(str(df['volume'].iloc[i])),
                    timestamp=df['date'].iloc[i].to_pydatetime(),
                )
                signals.append(signal)

    return signals


def compute_rsi(prices, period=14):
    """Compute RSI indicator."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def run_backtest_for_profile(name, config, data, initial_capital):
    """Run backtest for a specific profile."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    print(f"  RSI Threshold: {config['rsi_threshold']}")
    print(f"  Volume Threshold: {config['volume_threshold']}x")
    print(f"  Stop Loss: {config['stop_loss']*100:.1f}%")
    print(f"  Take Profit: {config['take_profit']*100:.1f}%")
    print(f"  Max Position: {config['max_position_pct']*100:.0f}%")

    # Create backtest config
    backtest_config = BacktestConfig(
        strategy_name=f"profile_{name.lower().replace(' ', '_')}",
        initial_capital=Decimal(str(initial_capital)),
        commission_per_trade=Decimal("1.0"),
        slippage_percentage=Decimal("0.001"),
    )

    # Generate signals
    signals = generate_signals(data, config)
    print(f"  Signals generated: {len(signals)}")

    if not signals:
        print(f"  ⚠ No signals generated, skipping...")
        return None

    # Convert to quotes
    quotes = []
    for symbol, df in data.items():
        for _, row in df.iterrows():
            close_price = Decimal(str(row['close']))
            # Use close as proxy for bid/ask/last (simplified for backtesting)
            quote = Quote(
                symbol=symbol,
                timestamp=row['date'].to_pydatetime(),
                bid=close_price,
                ask=close_price,
                last=close_price,
                open=Decimal(str(row['open'])),
                high=Decimal(str(row['high'])),
                low=Decimal(str(row['low'])),
                close=close_price,  # Add close explicitly
                volume=Decimal(str(row['volume'])),
            )
            quotes.append(quote)

    # Run backtest
    try:
        backtester = SimpleBacktester(backtest_config)
        result = backtester.run_backtest(quotes, signals)
        return result
    except Exception as e:
        print(f"  ✗ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run profile comparison."""
    print("\n" + "=" * 70)
    print("SIMPLE PROFILE COMPARISON - Local Data")
    print("=" * 70)

    # Configuration
    SYMBOLS = ["AAPL", "MSFT", "GOOGL"]
    START_DATE = "2023-01-01"
    END_DATE = "2023-03-31"  # 3 months only
    INITIAL_CAPITAL = 100000

    print(f"\nConfiguration:")
    print(f"  Period: {START_DATE} to {END_DATE}")
    print(f"  Symbols: {', '.join(SYMBOLS)}")
    print(f"  Initial Capital: €{INITIAL_CAPITAL:,.0f}")

    # Load data
    data = load_market_data(SYMBOLS, START_DATE, END_DATE)

    if not data:
        print("\n✗ No data loaded. Exiting.")
        return

    # Run backtests for each profile
    results = []
    for name, config in PROFILES.items():
        result = run_backtest_for_profile(name, config, data, INITIAL_CAPITAL)
        if result:
            results.append((name, result))

    # Print comparison
    if results:
        print("\n" + "=" * 70)
        print("RESULTS COMPARISON")
        print("=" * 70)
        print(f"\n{'Profile':<25} {'Profit':<15} {'Return':<12} {'Sharpe':<10} {'Win Rate':<10}")
        print("-" * 80)

        # Sort by profit
        results_sorted = sorted(results, key=lambda x: x[1].total_return, reverse=True)

        for name, result in results_sorted:
            profit = float(result.performance.total_pnl)
            ret = result.total_return * 100
            sharpe = result.performance.sharpe_ratio or 0
            win_rate = result.performance.win_rate * 100

            marker = " 👑" if name == results_sorted[0][0] else ""
            print(f"{name:<25} €{profit:>12,.2f}{marker} {ret:>10.2f}% {sharpe:>9.2f} {win_rate:>9.1f}%")

        # Winner summary
        winner_name, winner_result = results_sorted[0]
        print("\n" + "=" * 70)
        print("WINNER:")
        print("=" * 70)
        print(f"  Profile: {winner_name}")
        print(f"  Profit: €{float(winner_result.performance.total_pnl):,.2f}")
        print(f"  Return: {winner_result.total_return*100:.2f}%")
        print(f"  Sharpe Ratio: {winner_result.performance.sharpe_ratio or 0:.2f}")
        print(f"  Max Drawdown: {winner_result.performance.max_drawdown_percentage:.2f}%")
        print(f"  Win Rate: {winner_result.performance.win_rate*100:.1f}%")
        print(f"  Total Trades: {winner_result.performance.total_trades}")

        # Config summary of winner
        print(f"\nWinning Configuration:")
        winner_config = PROFILES[winner_name]
        for k, v in winner_config.items():
            print(f"  {k}: {v}")

    print("\n✅ Comparison completed!")


if __name__ == "__main__":
    main()
