#!/bin/bash
# ===========================================
# run_backtest.sh - Script para ejecutar backtests
# ===========================================
# Uso: ./scripts/run_backtest.sh --strategy STRATEGY --start DATE --end DATE --capital AMOUNT
# ===========================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════════════════"
echo "🚀 AlgoTrading - Backtesting Runner"
echo "════════════════════════════════════════════════════════════"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "app/main.py" ]; then
    echo -e "${RED}❌ Error: Debe ejecutarse desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Verificar que el entorno virtual existe
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Creando entorno virtual...${NC}"
    python3 -m venv .venv
fi

# Activar entorno virtual
source .venv/bin/activate

# Instalar dependencias si es necesario
echo "📦 Verificando dependencias..."
if ! python -c "import pandas" 2>/dev/null; then
    echo "📥 Instalando dependencias..."
    pip install -q pandas numpy yfinance matplotlib scipy rich
fi

# Limpiar resultados anteriores
echo "🧹 Limpiando resultados anteriores..."
rm -rf reports/backtesting/*.json reports/backtesting/*.png 2>/dev/null || true
mkdir -p reports/backtesting

# Parsear argumentos
STRATEGY="${1:-momentum}"
START_DATE="${2:-2024-01-01}"
END_DATE="${3:-2025-01-01}"
CAPITAL="${4:-100000}"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "📊 Configuración de Backtest:"
echo "════════════════════════════════════════════════════════════"
echo "  Estrategia: $STRATEGY"
echo "  Período: $START_DATE → $END_DATE"
echo "  Capital: \$$(printf "%'.0f" ${CAPITAL})"
echo "════════════════════════════════════════════════════════════"
echo ""

# Ejecutar backtest
echo "🔬 Ejecutando backtest..."
python -c "
from datetime import datetime
from decimal import Decimal
from app.strategies.momentum import MomentumStrategy
from app.backtesting.data_loader import DataLoader
from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig

# Setup
config = BacktestConfig(
    strategy_name='$STRATEGY',
    initial_capital=Decimal('${CAPITAL}'),
    commission_per_trade=Decimal('1.0'),
    slippage_percentage=Decimal('0.1')
)

# Load data
loader = DataLoader()
quotes = loader.load_market_data('AAPL', datetime(2024, 1, 1), datetime(2025, 1, 1))

# Create strategy
strategy = MomentumStrategy({'name': 'momentum_strategy'})

# Generate signals
signals = []
for quote in quotes:
    signals.extend(strategy.generate_signals(quote))

# Run backtest
backtester = SimpleBacktester(config)
result = backtester.run_backtest(quotes, signals)

# Print results
print(f\"\\n✅ Backtest completado!\")
print(f\"  Total Trades: {result.performance.total_trades}\")
print(f\"  Win Rate: {result.performance.win_rate:.2f}%\")
print(f\"  Total PnL: \${result.performance.total_pnl:.2f}\")
print(f\"  Return: {result.total_return:.2f}%\")
print(f\"  Sharpe: {result.performance.sharpe_ratio or 0:.2f}\")
print(f\"  Max Drawdown: {result.performance.max_drawdown_percentage:.2f}%\")
print(f\"\\n📁 Resultados guardados en: reports/backtesting/\")
"
echo ""
echo -e "${GREEN}✅ Backtest completado exitosamente${NC}"
echo "════════════════════════════════════════════════════════════"

