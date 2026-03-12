#!/usr/bin/env python3
"""
Script para ejecutar backtesting comprehensivo con múltiples símbolos y 25 años de datos.

Este script:
1. Usa un portafolio diversificado de todos los sectores de la economía
2. Ejecuta backtesting para cada símbolo
3. Compara rendimiento entre estrategias (momentum, mean_reversion, pairs_trading)
4. Optimiza parámetros centralizados y los guarda en YAML
5. Genera reporte agregado con análisis por sector

PERFIL DE INVERSOR:
- Objective: maximizar_capital (crecimiento de capital a largo plazo)
- Risk: medio (balanceado entre riesgo y retorno)
- Horizon: 12 meses (rebalanceo trimestral)
- Capital: €100,000 (tier: medium)

Uso:
    python scripts/run_multi_symbol_backtest.py
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd

# Configurar variables de entorno ANTES de imports
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TORCH_USE_CUDA_DSA'] = '0'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# Agregar raíz del proyecto al path
# scripts/backtesting/optimization/ -> scripts/backtesting/ -> scripts/ -> project_root
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# ============================================================================
# CONFIGURACIÓN DEL PORTAFOLIO DIVERSIFICADO
# ============================================================================
# Portafolio representativo de la economía estadounidense con 30 símbolos
# distribuidos en 11 sectores GICS

PORTFOLIO = {
    # TECHNOLOGY (20%) - 6 símbolos
    "AAPL": {"sector": "Technology", "industry": "Consumer Electronics", "weight": 0.04},
    "MSFT": {"sector": "Technology", "industry": "Software", "weight": 0.04},
    "GOOGL": {"sector": "Technology", "industry": "Internet Services", "weight": 0.03},
    "NVDA": {"sector": "Technology", "industry": "Semiconductors", "weight": 0.03},
    "META": {"sector": "Technology", "industry": "Social Media", "weight": 0.03},
    "CSCO": {"sector": "Technology", "industry": "Networking", "weight": 0.03},

    # FINANCIALS (15%) - 4 símbolos
    "JPM": {"sector": "Financials", "industry": "Banking", "weight": 0.04},
    "BAC": {"sector": "Financials", "industry": "Banking", "weight": 0.04},
    "V": {"sector": "Financials", "industry": "Payments", "weight": 0.04},
    "BRK.B": {"sector": "Financials", "industry": "Diversified Financials", "weight": 0.03},

    # HEALTHCARE (12%) - 3 símbolos
    "JNJ": {"sector": "Healthcare", "industry": "Pharmaceuticals", "weight": 0.04},
    "UNH": {"sector": "Healthcare", "industry": "Health Insurance", "weight": 0.04},
    "PFE": {"sector": "Healthcare", "industry": "Pharmaceuticals", "weight": 0.04},

    # CONSUMER DISCRETIONARY (10%) - 3 símbolos
    "AMZN": {"sector": "Consumer Discretionary", "industry": "E-commerce", "weight": 0.04},
    "TSLA": {"sector": "Consumer Discretionary", "industry": "Automotive", "weight": 0.03},
    "HD": {"sector": "Consumer Discretionary", "industry": "Home Improvement", "weight": 0.03},

    # CONSUMER STAPLES (8%) - 2 símbolos
    "PG": {"sector": "Consumer Staples", "industry": "Household Products", "weight": 0.04},
    "KO": {"sector": "Consumer Staples", "industry": "Beverages", "weight": 0.04},

    # INDUSTRIALS (10%) - 3 símbolos
    "CAT": {"sector": "Industrials", "industry": "Construction Machinery", "weight": 0.03},
    "BA": {"sector": "Industrials", "industry": "Aerospace", "weight": 0.03},
    "UPS": {"sector": "Industrials", "industry": "Logistics", "weight": 0.04},

    # ENERGY (8%) - 2 símbolos
    "XOM": {"sector": "Energy", "industry": "Oil & Gas Integrated", "weight": 0.04},
    "CVX": {"sector": "Energy", "industry": "Oil & Gas Integrated", "weight": 0.04},

    # UTILITIES (5%) - 2 símbolos
    "NEE": {"sector": "Utilities", "industry": "Electric Utilities", "weight": 0.03},
    "DUK": {"sector": "Utilities", "industry": "Electric Utilities", "weight": 0.02},

    # REAL ESTATE (5%) - 1 símbolo
    "AMT": {"sector": "Real Estate", "industry": "REIT", "weight": 0.05},

    # MATERIALS (4%) - 1 símbolo
    "LIN": {"sector": "Materials", "industry": "Chemicals", "weight": 0.04},

    # COMMUNICATION SERVICES (3%) - 1 símbolo
    "DIS": {"sector": "Communication Services", "industry": "Entertainment", "weight": 0.03},
}

# Convertir a lista de símbolos
SYMBOLS = list(PORTFOLIO.keys())

# Configuración de backtesting
START_DATE = "2000-01-01"  # 25 años de datos históricos
END_DATE = "2025-01-25"    # Fecha actual
INITIAL_CAPITAL = 100000.0 # $100,000 USD

# Tests a ejecutar
ENABLED_TESTS = ["baseline", "hyperparameter_optimization", "multi_strategy", "walk_forward", "out_of_sample"]

# Perfil de inversor (matching config/investment_profiles.yaml)
INVESTOR_PROFILE = {
    "objective": "maximizar_capital",
    "risk_tolerance": "medio",
    "investment_horizon_months": 12,
    "target_monthly_return": 2000,
    "tier": "medium"
}


def print_portfolio_summary():
    """Imprimir resumen del portafolio."""
    print("\n" + "="*80)
    print("📊 PORTFOLIO DIVERSIFICADO - BACKTESTING 25 AÑOS")
    print("="*80)

    # Agrupar por sector
    sectors = {}
    for symbol, info in PORTFOLIO.items():
        sector = info["sector"]
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(symbol)

    print(f"\n🔍 TOTAL SÍMBOLOS: {len(SYMBOLS)}")
    print(f"📅 PERIODO: {START_DATE} a {END_DATE} (25 años)")
    print(f"💰 CAPITAL INICIAL: ${INITIAL_CAPITAL:,.2f}")
    print(f"\n📊 DISTRIBUCIÓN POR SECTOR:")
    print("-"*80)

    for sector, symbols in sorted(sectors.items(), key=lambda x: x[0]):
        sector_weight = sum([PORTFOLIO[s]["weight"] for s in symbols])
        print(f"\n{sector:25} ({sector_weight*100:5.1f}%): {', '.join(symbols)}")

    print("\n" + "="*80)
    print(f"👤 PERFIL DE INVERSOR:")
    print(f"   • Objetivo: {INVESTOR_PROFILE['objective']}")
    print(f"   • Riesgo: {INVESTOR_PROFILE['risk_tolerance']}")
    print(f"   • Horizonte: {INVESTOR_PROFILE['investment_horizon_months']} meses")
    print(f"   • Tier: {INVESTOR_PROFILE['tier']}")
    print("="*80 + "\n")


def create_temp_config(symbol: str, config_dir: Path) -> Path:
    """Crear configuración temporal para un símbolo."""
    config_path = config_dir / f"temp_config_{symbol}.yaml"

    # Leer configuración base
    base_config_path = project_root / "config" / "backtesting" / "comprehensive_backtest.yaml"

    # Crear config específica para el símbolo
    import yaml

    with open(base_config_path) as f:
        config = yaml.safe_load(f)

    # Modificar para un solo símbolo
    config['input']['symbol'] = symbol
    config['input']['start_date'] = START_DATE
    config['input']['end_date'] = END_DATE
    config['input']['initial_capital'] = INITIAL_CAPITAL

    # Añadir información del perfil de inversor
    config['investor_profile'] = INVESTOR_PROFILE
    config['sector_info'] = PORTFOLIO[symbol]

    # Asegurar que los tests estén habilitados
    for test_name in ENABLED_TESTS:
        if test_name in config['backtests']:
            config['backtests'][test_name]['enabled'] = True

    # Guardar config temporal
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    logger.info(f"✅ Created temp config for {symbol} ({PORTFOLIO[symbol]['sector']}): {config_path}")
    return config_path


def run_backtest_for_symbol(symbol: str) -> Dict[str, Any]:
    """Ejecutar backtesting para un símbolo."""
    sector = PORTFOLIO[symbol]["sector"]
    logger.info(f"\n{'='*80}")
    logger.info(f"🔄 RUNNING BACKTEST FOR {symbol} ({sector})")
    logger.info(f"{'='*80}\n")

    # Crear config temporal
    config_dir = project_root / "config" / "backtesting" / "temp"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = create_temp_config(symbol, config_dir)

    try:
        # Importar el runner
        from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner

        # Crear runner
        runner = ComprehensiveBacktestRunner(str(config_path))

        # Ejecutar tests específicos
        logger.info(f"📊 Running enabled tests: {ENABLED_TESTS}")
        results_df = runner.run_specific_backtests(ENABLED_TESTS)

        # Extraer resultados clave
        result = {
            'symbol': symbol,
            'sector': sector,
            'industry': PORTFOLIO[symbol]['industry'],
            'weight': PORTFOLIO[symbol]['weight'],
            'total_tests': len(results_df) if not results_df.empty else 0,
            'tests': []
        }

        if not results_df.empty:
            # Guardar CSV completo
            csv_path = project_root / "reports" / "comprehensive_backtest_25years" / f"{symbol}_results.csv"
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            results_df.to_csv(csv_path, index=False)
            logger.info(f"💾 Saved {symbol} results to {csv_path}")

            # Extraer top resultados
            # VECTORIZED: Usar to_dict('records') en lugar de iterrows
            for row in results_df.head(5).to_dict('records'):
                test_result = {
                    'symbol': symbol,
                    'sector': sector,
                    'industry': PORTFOLIO[symbol]['industry'],
                    'test_name': row.get('test_name', 'Unknown'),
                    'test_type': row.get('test_type', 'Unknown'),
                    'strategy': row.get('strategy', 'N/A'),
                    'sharpe_ratio': float(row.get('sharpe_ratio', 0)),
                    'total_pnl': float(row.get('total_pnl', 0)),
                    'return_pct': float(row.get('return_pct', 0)),
                    'win_rate': float(row.get('win_rate', 0)),
                    'max_drawdown': float(row.get('max_drawdown', 0)),
                    'total_trades': int(row.get('total_trades', 0)),
                }
                result['tests'].append(test_result)

        return result

    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        logger.error(f"❌ Error running backtest for {symbol}: {e}", exc_info=True)
        return {
            'symbol': symbol,
            'sector': sector,
            'industry': PORTFOLIO[symbol]['industry'],
            'error': str(e),
            'tests': []
        }
    finally:
        # Limpiar config temporal
        if config_path.exists():
            config_path.unlink()


def create_aggregated_report(all_results: List[Dict[str, Any]]) -> None:
    """Crear reporte agregado con todos los resultados."""
    logger.info(f"\n{'='*80}")
    logger.info("📊 CREATING AGGREGATED REPORT")
    logger.info(f"{'='*80}\n")

    # Recolectar todos los tests
    all_tests = []
    strategy_performance = {
        'momentum': [],
        'mean_reversion': [],
        'pairs_trading': []
    }
    sector_performance = {}

    for result in all_results:
        if 'error' in result:
            continue

        sector = result['sector']
        if sector not in sector_performance:
            sector_performance[sector] = []

        for test in result['tests']:
            all_tests.append(test)

            # Agrupar por estrategia
            strategy = test.get('strategy', 'unknown')
            if strategy in strategy_performance:
                strategy_performance[strategy].append({
                    'symbol': test['symbol'],
                    'sector': test['sector'],
                    'sharpe_ratio': test['sharpe_ratio'],
                    'return_pct': test['return_pct'],
                    'total_pnl': test['total_pnl']
                })

            # Agrupar por sector
            sector_performance[sector].append({
                'symbol': test['symbol'],
                'sharpe_ratio': test['sharpe_ratio'],
                'return_pct': test['return_pct'],
                'total_pnl': test['total_pnl']
            })

    # Crear DataFrame
    if all_tests:
        df = pd.DataFrame(all_tests)

        # Guardar CSV agregado
        output_dir = project_root / "reports" / "comprehensive_backtest_25years"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = output_dir / f"aggregated_results_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"💾 Saved aggregated results to {csv_path}")

        # Imprimir resumen
        print("\n" + "="*80)
        print("📊 AGGREGATED BACKTESTING RESULTS (25 YEARS)")
        print("="*80)

        print(f"\n✅ Total tests executed: {len(all_tests)}")
        print(f"📈 Symbols tested: {len(set([t['symbol'] for t in all_tests]))}")
        print(f"🏢 Sectors covered: {len(set([t['sector'] for t in all_tests]))}")

        # Top 15 por Sharpe Ratio
        print("\n🏆 TOP 15 BY SHARPE RATIO:")
        print("-"*80)
        top_15 = df.nlargest(15, 'sharpe_ratio')
        # VECTORIZED: Usar to_dict('records') en lugar de iterrows
        for row in top_15.to_dict('records'):
            print(f"  {row['symbol']:6} ({row['sector']:20}): Sharpe {row['sharpe_ratio']:6.2f} | Return {row['return_pct']:6.1f}% | PnL ${row['total_pnl']:9,.2f}")

        # Comparación de estrategias
        print("\n⚔️  STRATEGY COMPARISON:")
        print("-"*80)
        for strategy, perf in strategy_performance.items():
            if perf:
                avg_sharpe = sum([p['sharpe_ratio'] for p in perf]) / len(perf)
                avg_return = sum([p['return_pct'] for p in perf]) / len(perf)
                total_pnl = sum([p['total_pnl'] for p in perf])
                print(f"  {strategy:20} | Avg Sharpe: {avg_sharpe:6.2f} | Avg Return: {avg_return:6.1f}% | Total PnL: ${total_pnl:10,.2f}")

        # Comparación por sector
        print("\n🏢 SECTOR PERFORMANCE:")
        print("-"*80)
        sector_avg = {}
        for sector, perf in sector_performance.items():
            if perf:
                avg_sharpe = sum([p['sharpe_ratio'] for p in perf]) / len(perf)
                avg_return = sum([p['return_pct'] for p in perf]) / len(perf)
                sector_avg[sector] = {
                    'avg_sharpe': avg_sharpe,
                    'avg_return': avg_return,
                    'num_tests': len(perf)
                }

        # Ordenar por Sharpe
        for sector, metrics in sorted(sector_avg.items(), key=lambda x: x[1]['avg_sharpe'], reverse=True):
            print(f"  {sector:25} | Avg Sharpe: {metrics['avg_sharpe']:6.2f} | Avg Return: {metrics['avg_return']:6.1f}% | Tests: {metrics['num_tests']}")

        # Guardar resumen en JSON
        summary = {
            'timestamp': timestamp,
            'portfolio': {
                'total_symbols': len(SYMBOLS),
                'sectors': list(set([PORTFOLIO[s]['sector'] for s in SYMBOLS])),
                'period': f"{START_DATE} to {END_DATE}",
                'initial_capital': INITIAL_CAPITAL,
                'investor_profile': INVESTOR_PROFILE
            },
            'total_tests': len(all_tests),
            'symbols_tested': list(set([t['symbol'] for t in all_tests])),
            'top_15_by_sharpe': top_15.to_dict('records'),
            'strategy_comparison': {
                strategy: {
                    'avg_sharpe_ratio': sum([p['sharpe_ratio'] for p in perf]) / len(perf) if perf else 0,
                    'avg_return_pct': sum([p['return_pct'] for p in perf]) / len(perf) if perf else 0,
                    'total_pnl': sum([p['total_pnl'] for p in perf]) if perf else 0,
                    'num_tests': len(perf)
                }
                for strategy, perf in strategy_performance.items()
            },
            'sector_comparison': sector_avg
        }

        json_path = output_dir / f"summary_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"💾 Saved summary to {json_path}")

    else:
        logger.warning("⚠️ No results to aggregate")


def main():
    """Ejecutar backtesting para todos los símbolos."""
    # Imprimir resumen del portafolio
    print_portfolio_summary()

    logger.info("🚀 MULTI-Symbol BACKTESTING STARTED")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info(f"Period: {START_DATE} to {END_DATE}")
    logger.info(f"Tests: {ENABLED_TESTS}")

    all_results = []

    for i, symbol in enumerate(SYMBOLS, 1):
        logger.info(f"\n{'#'*80}")
        logger.info(f"# PROGRESS: {i}/{len(SYMBOLS)} symbols completed")
        logger.info(f"{'#'*80}")
        result = run_backtest_for_symbol(symbol)
        all_results.append(result)

    # Crear reporte agregado
    create_aggregated_report(all_results)

    logger.info("\n✅ ALL BACKTESTS COMPLETED")


if __name__ == "__main__":
    main()
