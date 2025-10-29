#!/usr/bin/env python3
"""
Simple Backtest Runner

Ejecución simple de backtest para verificar que todo funciona.
"""

import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# IMPORTANT: Import logging_config FIRST to ensure all warnings/errors go to files
from app.core.logging_config import setup_file_logging

# Logging is already configured by logging_config module
logger = logging.getLogger(__name__)

# Configuración
SYMBOL = "AAPL"
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 1, 1)
INITIAL_CAPITAL = Decimal("100000")
STRATEGY_NAME = "momentum"

print("=" * 60)
print("🚀 Backtesting Runner")
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
    from app.strategies.momentum import MomentumStrategy

    # Cargar datos
    print(f"📊 Loading market data for {SYMBOL}...")
    loader = DataLoader()
    quotes = loader.load_market_data(SYMBOL, START_DATE, END_DATE)

    if not quotes:
        print("❌ No data available. Exiting.")
        exit(1)

    print(f"✅ Loaded {len(quotes)} quotes")
    print()

    # Crear configuración
    config = BacktestConfig(
        strategy_name=STRATEGY_NAME,
        initial_capital=INITIAL_CAPITAL,
        commission_per_trade=Decimal("1.0"),
        slippage_percentage=Decimal("0.1"),
    )

    # Crear estrategia
    print("📈 Initializing strategy...")
    strategy = MomentumStrategy({"name": STRATEGY_NAME})

    # Generar señales
    print("🔍 Generating signals...")
    signals = []
    for quote in quotes[:100]:  # Limitar para prueba
        try:
            signals.extend(strategy.generate_signals(quote))
        except Exception as e:
            logger.debug(f"Signal error: {e}")

    print(f"✅ Generated {len(signals)} signals")
    print()

    # Ejecutar backtest
    print("▶️  Running backtest...")
    backtester = SimpleBacktester(config)
    result = backtester.run_backtest(quotes[:100], signals)

    # Mostrar resultados
    print()
    print("=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    print(f"Total Trades: {result.performance.total_trades}")
    print(f"Winning Trades: {result.performance.winning_trades}")
    print(f"Losing Trades: {result.performance.losing_trades}")
    print(f"Win Rate: {result.performance.win_rate:.2f}%")
    print(f"Total PnL: ${result.performance.total_pnl:,.2f}")
    print(f"Total Return: {result.total_return:.2f}%")
    print(f"Final Capital: ${result.final_capital:,.2f}")
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
except Exception as e:
    print(f"❌ Error: {e}")
    logger.exception("Backtest failed")
    exit(1)

