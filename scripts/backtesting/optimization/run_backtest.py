#!/usr/bin/env python3
"""
Backtesting Runner

Genera múltiples trades con parámetros ajustados para mejores métricas.
"""

import sys
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
# scripts/backtesting/optimization/ -> scripts/backtesting/ -> scripts/ -> project_root
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
SYMBOL = "AAPL"
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2024, 12, 31)
INITIAL_CAPITAL = Decimal("100000")
STRATEGY_NAME = "momentum"

print("=" * 60)
print("🚀 BACKTESTING RUNNER")
print("=" * 60)
print(f"Strategy: {STRATEGY_NAME}")
print(f"Symbol: {SYMBOL}")
print(f"Period: {START_DATE.date()} → {END_DATE.date()}")
print(f"Initial Capital: ${INITIAL_CAPITAL:,.0f}")
print("=" * 60)
print()

try:
    # Importar módulos
    print("📦 Importing modules...")
    from app.backtesting.data_loader import DataLoader
    from app.backtesting.engine import SimpleBacktester
    from app.backtesting.models import BacktestConfig
    from app.domain.strategies.momentum import MomentumStrategy

    # Cargar datos
    print(f"📊 Loading market data for {SYMBOL}...")
    loader = DataLoader()
    quotes = loader.load_market_data(SYMBOL, START_DATE, END_DATE)

    if not quotes:
        print("❌ No data available. Exiting.")
        exit(1)

    print(f"✅ Loaded {len(quotes)} quotes")
    print()

    # Crear configuración con stop loss y take profit
    print("⚙️  Configuring backtest...")
    config = BacktestConfig(
        strategy_name=STRATEGY_NAME,
        initial_capital=INITIAL_CAPITAL,
        commission_per_trade=Decimal("1.0"),
        slippage_percentage=Decimal("0.05"),  # Reducir slippage
        stop_loss_percentage=Decimal("2.0"),  # 2% stop loss - más ajustado
        take_profit_percentage=Decimal("5.0"),  # 5% take profit - más ajustado
        max_position_size=Decimal("0.05"),  # 5% max position
    )

    # Crear estrategia más agresiva para más trades
    print("📈 Initializing strategy...")
    strategy = MomentumStrategy({
        "name": STRATEGY_NAME,
        "rsi_threshold": 50,  # Más permisivo
        "momentum_threshold": 0.0001,  # Muy bajo para más señales
        "volume_threshold": 0.1,  # Bajo threshold
        "max_position_size": 0.2,  # Tamaño moderado para más trades
    })

    # Generar señales
    print("🔍 Generating signals...")
    signals = []
    for quote in quotes:  # Todos los quotes
        try:
            new_signals = strategy.generate_signals(quote)
            if new_signals:
                signals.extend(new_signals)
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.debug(f"Signal error: {e}")

    print(f"✅ Generated {len(signals)} total signals")
    
    # Analizar tipos de señales
    buy_signals = sum(1 for s in signals if s.signal_type == "buy" or str(s.signal_type) == "buy")
    sell_signals = sum(1 for s in signals if s.signal_type == "sell" or str(s.signal_type) == "sell")
    print(f"   Buy: {buy_signals}, Sell: {sell_signals}")
    print()

    # Ejecutar backtest
    print("▶️  Running backtest...")
    backtester = SimpleBacktester(config)
    result = backtester.run_backtest(quotes, signals)

    # Mostrar resultados
    print()
    print("=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print(f"Final Capital: ${result.final_capital:,.2f}")
    print(f"Total PnL: ${result.final_capital - INITIAL_CAPITAL:,.2f}")
    print(f"Total Return: {result.total_return:.2f}%")
    print()
    print(f"Total Trades: {result.performance.total_trades}")
    print(f"Winning Trades: {result.performance.winning_trades}")
    print(f"Losing Trades: {result.performance.losing_trades}")
    print(f"Win Rate: {result.performance.win_rate:.2f}%")
    print(f"Gross Profit: ${result.performance.gross_profit:,.2f}")
    print(f"Gross Loss: ${result.performance.gross_loss:,.2f}")
    print()
    if result.performance.sharpe_ratio:
        print(f"Sharpe Ratio: {result.performance.sharpe_ratio:.2f}")
    if result.performance.max_drawdown_percentage:
        print(f"Max Drawdown: {result.performance.max_drawdown_percentage:.2f}%")
    print("=" * 60)
    print()
    print("✅ Backtest completed successfully!")

except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("   Make sure you have installed all dependencies:")
    print("   pip install pandas numpy yfinance matplotlib scipy rich")
    exit(1)
except (ValueError, TypeError, KeyError, AttributeError) as e:
    print(f"❌ Error: {e}")
    logger.exception("Backtest failed")
    exit(1)

