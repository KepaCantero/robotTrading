#!/usr/bin/env python3
"""
Baseline Backtest - Performance base sin optimización.

Ejecuta backtest completo con todos los módulos activos y sin ML.
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.backtesting.data_loader import DataLoader
from app.backtesting.engine import SimpleBacktester
from app.strategies.momentum_modular.strategy import ModularMomentumStrategy
from app.core.centralized_config import get_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_baseline_backtest(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    initial_capital: Decimal = Decimal("100000"),
    output_dir: Path = Path("docs/BACKTEST_RESULTS/baseline")
):
    """
    Ejecutar baseline backtest.
    
    Args:
        symbol: Símbolo a backtestear
        start_date: Fecha de inicio
        end_date: Fecha de fin
        initial_capital: Capital inicial
        output_dir: Directorio de salida
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"BASELINE BACKTEST: {symbol}")
    logger.info(f"Período: {start_date.date()} a {end_date.date()}")
    logger.info(f"Capital inicial: ${initial_capital:,.2f}")
    logger.info(f"{'='*80}\n")
    
    # Crear directorio de salida
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Cargar datos
    logger.info(f"📥 Cargando datos para {symbol}...")
    loader = DataLoader()
    quotes = loader.load_market_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        timeframe="1d",
        source="csv"  # Intentar CSV primero, luego yfinance
    )
    
    if not quotes:
        logger.error(f"❌ No se encontraron datos para {symbol}")
        return None
    
    logger.info(f"✅ Cargados {len(quotes)} datos")
    
    # Crear estrategia con configuración baseline
    logger.info("🔧 Configurando estrategia baseline (todos los módulos activos, sin ML)...")
    config = get_config()
    strategy_config = config.get_strategy_config("momentum_modular")
    
    if not strategy_config:
        logger.error("❌ No se encontró configuración para momentum_modular")
        return None
    
    # Crear estrategia sin learning engine
    strategy = ModularMomentumStrategy(
        symbol=symbol,
        config=strategy_config.parameters,
        learning_engine=None  # Sin ML para baseline
    )
    
    # Crear backtester
    backtester = SimpleBacktester(
        strategy=strategy,
        initial_capital=initial_capital,
        enable_risk_envelope=True
    )
    
    # Ejecutar backtest
    logger.info("🚀 Ejecutando backtest...")
    result = backtester.run_backtest(quotes)
    
    if not result:
        logger.error("❌ Backtest falló")
        return None
    
    # Guardar resultados
    results_data = {
        "symbol": symbol,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "initial_capital": float(initial_capital),
        "final_capital": float(result.final_capital),
        "total_return": float(result.total_return),
        "total_return_pct": float(result.total_return_percentage),
        "performance": {
            "total_trades": result.performance.total_trades,
            "winning_trades": result.performance.winning_trades,
            "losing_trades": result.performance.losing_trades,
            "win_rate": float(result.performance.win_rate),
            "total_pnl": float(result.performance.total_pnl),
            "average_win": float(result.performance.average_win) if result.performance.average_win else 0,
            "average_loss": float(result.performance.average_loss) if result.performance.average_loss else 0,
            "profit_factor": float(result.performance.profit_factor) if result.performance.profit_factor else 0,
            "sharpe_ratio": float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0,
            "max_drawdown_percentage": float(result.performance.max_drawdown_percentage),
            "max_drawdown_duration_days": result.performance.max_drawdown_duration_days,
        },
        "equity_curve": [
            {"date": str(d), "value": float(v)} 
            for d, v in result.equity_curve
        ],
        "trades": [
            {
                "entry_time": str(t.entry_time),
                "exit_time": str(t.exit_time) if t.exit_time else None,
                "symbol": t.symbol,
                "side": t.side.value if hasattr(t.side, 'value') else str(t.side),
                "quantity": float(t.quantity),
                "entry_price": float(t.entry_price),
                "exit_price": float(t.exit_price) if t.exit_price else None,
                "pnl": float(t.pnl) if t.pnl else 0,
                "status": t.status.value if hasattr(t.status, 'value') else str(t.status),
            }
            for t in result.trades
        ],
        "config": {
            "preset": "balanced",
            "modules_enabled": {
                "ema_filter": True,
                "rsi_filter": True,
                "stoch_rsi_filter": True,
                "momentum_filter": True,
                "volume_filter": True,
                "atr_filter": True,
            },
            "learning_engine": None,
        }
    }
    
    # Guardar JSON
    json_path = output_dir / f"baseline_results_{symbol}_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(results_data, f, indent=2)
    logger.info(f"✅ Resultados guardados en: {json_path}")
    
    # Guardar equity curve CSV
    csv_path = output_dir / f"baseline_equity_curve_{symbol}_{timestamp}.csv"
    import pandas as pd
    equity_df = pd.DataFrame(results_data["equity_curve"])
    equity_df.to_csv(csv_path, index=False)
    logger.info(f"✅ Equity curve guardada en: {csv_path}")
    
    # Guardar trades CSV
    trades_path = output_dir / f"baseline_trades_{symbol}_{timestamp}.csv"
    trades_df = pd.DataFrame(results_data["trades"])
    trades_df.to_csv(trades_path, index=False)
    logger.info(f"✅ Trades guardados en: {trades_path}")
    
    # Imprimir resumen
    logger.info(f"\n{'='*80}")
    logger.info(f"RESUMEN BASELINE BACKTEST: {symbol}")
    logger.info(f"{'='*80}")
    logger.info(f"Capital inicial:      ${initial_capital:,.2f}")
    logger.info(f"Capital final:        ${result.final_capital:,.2f}")
    logger.info(f"Retorno total:        ${result.total_return:,.2f} ({result.total_return_percentage:.2f}%)")
    logger.info(f"Total trades:         {result.performance.total_trades}")
    logger.info(f"Win rate:             {result.performance.win_rate:.2%}")
    logger.info(f"PnL total:            ${result.performance.total_pnl:,.2f}")
    logger.info(f"Sharpe ratio:         {result.performance.sharpe_ratio:.2f}" if result.performance.sharpe_ratio else "Sharpe ratio:         N/A")
    logger.info(f"Max drawdown:         {result.performance.max_drawdown_percentage:.2%}")
    logger.info(f"{'='*80}\n")
    
    return results_data


def main():
    parser = argparse.ArgumentParser(description="Baseline Backtest")
    parser.add_argument("--symbol", type=str, required=True, help="Símbolo a backtestear (ej: AAPL)")
    parser.add_argument("--start-date", type=str, required=True, help="Fecha de inicio (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, required=True, help="Fecha de fin (YYYY-MM-DD)")
    parser.add_argument("--initial-capital", type=float, default=100000, help="Capital inicial (default: 100000)")
    parser.add_argument("--output-dir", type=str, default="docs/BACKTEST_RESULTS/baseline", help="Directorio de salida")
    
    args = parser.parse_args()
    
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    initial_capital = Decimal(str(args.initial_capital))
    output_dir = Path(args.output_dir)
    
    run_baseline_backtest(
        symbol=args.symbol,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        output_dir=output_dir
    )


if __name__ == "__main__":
    main()
