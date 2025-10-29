#!/usr/bin/env python3
"""
Diagnostic Script: Validate Data and Universe for Multi-Strategy Backtest

Checks:
- All required symbols are present
- Data completeness (no gaps)
- Strategy-specific symbol requirements
- Pair compatibility for pairs_trading
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.portfolio_config_manager import get_portfolio_config_manager
from app.backtesting.data_loader import DataLoader
from app.models.market_data import Quote

def check_symbol_data(symbol: str, start_date: datetime, end_date: datetime) -> dict:
    """Check if symbol has complete data."""
    loader = DataLoader()
    quotes = loader.load_market_data(symbol, start_date, end_date, source="csv")
    
    if not quotes:
        # Try yfinance as fallback
        quotes = loader.load_market_data(symbol, start_date, end_date, source="yfinance")
    
    result = {
        "symbol": symbol,
        "available": len(quotes) > 0,
        "count": len(quotes),
        "date_range": None,
        "gaps": [],
        "coverage_pct": 0.0,
    }
    
    if quotes:
        dates = sorted([q.timestamp for q in quotes])
        result["date_range"] = {
            "start": dates[0].isoformat(),
            "end": dates[-1].isoformat(),
        }
        
        # Check for gaps (assuming daily data)
        # Calculate expected trading days (approximately 252 trading days per year)
        total_calendar_days = (end_date - start_date).days
        years = total_calendar_days / 365.25
        expected_trading_days = int(years * 252)  # 252 trading days per year
        
        # Coverage = actual quotes / expected trading days
        result["coverage_pct"] = (len(quotes) / expected_trading_days * 100) if expected_trading_days > 0 else 0
        
        # Detect gaps (more than 5 days missing - weekends + holidays are normal)
        # Only flag significant gaps that indicate data issues
        for i in range(len(dates) - 1):
            gap_days = (dates[i+1] - dates[i]).days
            if gap_days > 5:  # More than 5 days = likely data issue (not just weekend/holiday)
                result["gaps"].append({
                    "from": dates[i].isoformat(),
                    "to": dates[i+1].isoformat(),
                    "days": gap_days,
                })
    
    return result

def main():
    print("=" * 80)
    print("🔍 DIAGNÓSTICO: Validación de Datos y Universo para Backtest Multi-Estrategia")
    print("=" * 80)
    
    # Get portfolio configuration
    config_manager = get_portfolio_config_manager()
    
    # Calculate date range (10 years)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 10)
    
    print(f"\n📅 Rango de fechas: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
    
    # Get all symbols from portfolio
    all_symbols = set()
    sector_symbols = config_manager.config.get("sectors", {})
    for sector_name, sector_data in sector_symbols.items():
        symbols = sector_data.get("symbols", [])
        all_symbols.update(symbols)
    
    print(f"\n📊 Total de símbolos únicos en portfolio: {len(all_symbols)}")
    
    # Get strategy-specific symbols
    strategies = ["momentum", "mean_reversion", "pairs_trading"]
    strategy_symbols = {}
    
    for strategy in strategies:
        symbols = config_manager.get_strategy_symbols(strategy)
        strategy_symbols[strategy] = symbols
        print(f"\n📈 {strategy.upper()}: {len(symbols)} símbolos requeridos")
        if symbols:
            print(f"   {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    
    # Check data availability
    print("\n" + "=" * 80)
    print("🔍 VERIFICACIÓN DE DATOS")
    print("=" * 80)
    
    results = {}
    missing_symbols = []
    incomplete_symbols = []
    
    for symbol in sorted(all_symbols):
        result = check_symbol_data(symbol, start_date, end_date)
        results[symbol] = result
        
        if not result["available"]:
            missing_symbols.append(symbol)
            print(f"❌ {symbol}: DATOS NO DISPONIBLES")
        elif result["coverage_pct"] < 80:
            incomplete_symbols.append(symbol)
            print(f"⚠️  {symbol}: Cobertura {result['coverage_pct']:.1f}% ({result['count']} quotes)")
            if result["gaps"]:
                for gap in result["gaps"][:3]:  # Show first 3 gaps
                    print(f"      Gap: {gap['from']} → {gap['to']} ({gap['days']} days)")
        else:
            print(f"✅ {symbol}: {result['count']} quotes, {result['coverage_pct']:.1f}% cobertura")
    
    # Strategy-specific checks
    print("\n" + "=" * 80)
    print("🎯 VERIFICACIÓN POR ESTRATEGIA")
    print("=" * 80)
    
    for strategy in strategies:
        print(f"\n{strategy.upper()}:")
        required = strategy_symbols[strategy]
        available = []
        missing = []
        
        for symbol in required:
            if symbol in results and results[symbol]["available"]:
                if results[symbol]["coverage_pct"] >= 80:
                    available.append(symbol)
                else:
                    missing.append(f"{symbol} (incompleto)")
            else:
                missing.append(f"{symbol} (no disponible)")
        
        print(f"  ✅ Disponibles: {len(available)}/{len(required)}")
        if missing:
            print(f"  ❌ Faltantes: {', '.join(missing)}")
        else:
            print(f"  ✅ Todos los símbolos requeridos están disponibles")
    
    # Pairs Trading specific check
    print("\n" + "-" * 80)
    print("🔗 PAIRS TRADING: Verificación de Pares")
    print("-" * 80)
    
    pairs_config = config_manager.config.get("strategy_allocations", {}).get("pairs_trading", {})
    if "pair_symbols" in pairs_config:
        pairs_list = pairs_config["pair_symbols"]
        print(f"Pares configurados: {pairs_list}")
        
        for pair in pairs_list:
            if len(pair) == 2:
                s1, s2 = pair[0], pair[1]
                r1 = results.get(s1, {})
                r2 = results.get(s2, {})
                
                if r1.get("available") and r2.get("available"):
                    print(f"  ✅ Par [{s1}, {s2}]: Ambos disponibles")
                else:
                    missing_parts = []
                    if not r1.get("available"):
                        missing_parts.append(s1)
                    if not r2.get("available"):
                        missing_parts.append(s2)
                    print(f"  ❌ Par [{s1}, {s2}]: Faltan {', '.join(missing_parts)}")
    else:
        print("  ⚠️  No hay pair_symbols configurados en portfolio.yaml")
        print("  💡 Agrega pair_symbols como:")
        print("     pair_symbols:")
        print("       - [AAPL, MSFT]")
        print("       - [JPM, BAC]")
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 RESUMEN")
    print("=" * 80)
    
    total_symbols = len(all_symbols)
    available_count = total_symbols - len(missing_symbols) - len(incomplete_symbols)
    
    print(f"Total símbolos: {total_symbols}")
    print(f"✅ Disponibles: {available_count}")
    print(f"⚠️  Incompletos: {len(incomplete_symbols)}")
    print(f"❌ Faltantes: {len(missing_symbols)}")
    
    if missing_symbols:
        print(f"\n❌ Símbolos faltantes: {', '.join(missing_symbols)}")
        print("   💡 Ejecuta: python scripts/download_yahoo_v8.py " + " ".join(missing_symbols))
    
    if incomplete_symbols:
        print(f"\n⚠️  Símbolos incompletos: {', '.join(incomplete_symbols)}")
        print("   💡 Considera re-descargar estos símbolos")
    
    # Strategy readiness
    print("\n" + "=" * 80)
    print("🚀 READINESS DE ESTRATEGIAS")
    print("=" * 80)
    
    for strategy in strategies:
        required = strategy_symbols[strategy]
        ready = sum(1 for s in required if s in results and results[s].get("coverage_pct", 0) >= 80)
        pct_ready = (ready / len(required) * 100) if required else 0
        
        status = "✅ LISTO" if pct_ready >= 80 else "⚠️  PARCIAL" if pct_ready >= 50 else "❌ NO LISTO"
        print(f"{strategy.upper()}: {status} ({ready}/{len(required)} símbolos, {pct_ready:.1f}%)")
    
    print("\n" + "=" * 80)
    return 0 if len(missing_symbols) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

