#!/usr/bin/env python3
"""
Diagnóstico de señales de Momentum Strategy

Este script ayuda a entender por qué la estrategia Momentum no genera señales.
"""

import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.logging_config import setup_file_logging
from app.backtesting.data_loader import DataLoader
from app.strategies.momentum import MomentumStrategy

# Configuración
SYMBOL = "AAPL"
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 1, 1)

logger = logging.getLogger(__name__)

print("=" * 60)
print("🔍 Momentum Strategy Signal Diagnosis")
print("=" * 60)
print(f"Symbol: {SYMBOL}")
print(f"Period: {START_DATE.date()} → {END_DATE.date()}")
print("=" * 60)
print()

try:
    # Cargar datos
    print("📊 Loading market data...")
    loader = DataLoader()
    quotes = loader.load_market_data(SYMBOL, START_DATE, END_DATE)
    
    if not quotes:
        print("❌ No data available. Exiting.")
        exit(1)
    
    print(f"✅ Loaded {len(quotes)} quotes")
    print()
    
    # Crear estrategia
    print("📈 Initializing strategy...")
    strategy = MomentumStrategy({"name": "momentum"})
    
    # Analizar cada quote
    print("🔍 Analyzing signals...")
    print()
    
    signals_generated = 0
    insufficient_history = 0
    atr_filter_failed = 0
    stoch_rsi_failed = 0
    buy_conditions_failed = 0
    sell_conditions_failed = 0
    
    for i, quote in enumerate(quotes):
        try:
            # Generar señales
            quote_signals = strategy.generate_signals(quote)
            
            # Diagnosticar por qué no se generan señales
            if len(quote_signals) == 0:
                # Verificar histórico
                if len(strategy.price_history) < 14:
                    insufficient_history += 1
                    if i < 20:  # Solo mostrar primeros 20
                        print(f"Quote {i}: ⚠️ Insufficient history ({len(strategy.price_history)} < 14)")
                    continue
                
                # Verificar indicadores
                prices_list = list(strategy.price_history)
                highs_list = list(strategy.high_history)
                lows_list = list(strategy.low_history)
                volumes_list = list(strategy.volume_history)
                
                from app.services.momentum_analysis import TechnicalIndicatorCalculator
                calculator = TechnicalIndicatorCalculator()
                
                rsi = calculator.calculate_rsi(prices_list, 14)
                ema = calculator.calculate_ema(prices_list, 20)
                atr = calculator.calculate_atr(highs_list, lows_list, prices_list, period=14)
                
                if rsi is None or ema is None:
                    if i < 20:
                        print(f"Quote {i}: ⚠️ Indicators not ready (RSI={rsi}, EMA={ema})")
                    continue
                
                # Verificar condiciones
                current_price = float(quote.close or quote.last)
                volume_ratio = strategy._calculate_volume_ratio(quote)
                roc = calculator.calculate_roc(prices_list, period=12)
                obv = calculator.calculate_obv(prices_list, volumes_list)
                obv_trend = strategy._calculate_obv_trend_from_value(obv)
                
                # ATR filter
                if atr is None or len(strategy.atr_history) == 0:
                    atr_filter_failed += 1
                    if i < 20:
                        print(f"Quote {i}: ⚠️ ATR filter failed (ATR={atr})")
                    continue
                
                # Stochastic RSI (simplificado - solo verificar que existe)
                if not hasattr(strategy, 'rsi_history') or len(strategy.rsi_history) < 14:
                    stoch_rsi_failed += 1
                    if i < 20:
                        print(f"Quote {i}: ⚠️ Stochastic RSI not ready")
                    continue
                
                # Buy conditions
                buy_condition = strategy._is_buy_signal(rsi, ema, volume_ratio, roc, obv_trend, quote)
                sell_condition = strategy._is_sell_signal(rsi, ema, volume_ratio, roc, obv_trend, quote)
                
                if not buy_condition and not sell_condition:
                    buy_conditions_failed += 1
                    if i % 50 == 0:  # Mostrar cada 50 quotes
                        print(f"Quote {i}: 📊 RSI={rsi:.2f}, EMA={ema:.2f}, Price={current_price:.2f}, "
                              f"VolRatio={float(volume_ratio):.2f}, ROC={roc:.4f if roc else None}, "
                              f"OBV={obv_trend}, Buy={buy_condition}, Sell={sell_condition}")
                
            else:
                signals_generated += len(quote_signals)
                for sig in quote_signals:
                    print(f"✅ Quote {i}: Generated {sig.signal_type} signal at {sig.timestamp}, "
                          f"confidence={sig.confidence:.2f}%")
                    
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.debug(f"Quote {i}: Error - {e}")
    
    # Resumen
    print()
    print("=" * 60)
    print("📊 DIAGNOSIS SUMMARY")
    print("=" * 60)
    print(f"Total quotes analyzed: {len(quotes)}")
    print(f"Signals generated: {signals_generated}")
    print(f"Insufficient history: {insufficient_history}")
    print(f"ATR filter failed: {atr_filter_failed}")
    print(f"Stochastic RSI not ready: {stoch_rsi_failed}")
    print(f"Buy/Sell conditions not met: {buy_conditions_failed}")
    print("=" * 60)
    print()
    
    if signals_generated == 0:
        print("💡 RECOMMENDATIONS:")
        print("1. Verificar que hay suficiente histórico (al menos 60+ quotes)")
        print("2. Revisar configuración de thresholds en config/strategies/momentum.yaml")
        print("3. Considerar usar MomentumStrategyEngine que tiene condiciones menos estrictas")
        print("4. Probar con más datos históricos (año completo)")
        print()
    
    print("✅ Diagnosis completed!")

except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
    print(f"❌ Error: {e}")
    logger.exception("Diagnosis failed")
    exit(1)

