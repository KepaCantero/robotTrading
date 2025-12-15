# 🧪 Comandos para Ejecutar Backtests en Local

Este archivo contiene todos los comandos para ejecutar backtests con diferentes configuraciones.

## 📋 Prerequisitos

```bash
# Activar entorno virtual
source venv/bin/activate

# Verificar que estás en el directorio raíz
cd /Users/kepa.cantero/Projects/algoTrading
```

---

## 🚀 Backtests Básicos

### 1. Backtest Simple (Momentum Strategy)

Backtest rápido con configuración básica:

```bash
python run_simple_backtest.py
```

**Configuración por defecto:**
- Estrategia: `momentum`
- Símbolo: `AAPL`
- Período: 2024-01-01 → 2025-01-01
- Capital inicial: $100,000
- Límite: 100 quotes (para prueba rápida)

---

### 2. Backtest Completo (Momentum Strategy)

Backtest completo con todos los datos históricos:

```bash
python run_backtest.py
```

**Configuración por defecto:**
- Estrategia: `momentum`
- Símbolo: `AAPL`
- Período: 2023-01-01 → 2024-12-31
- Capital inicial: $100,000
- Stop loss: 2%
- Take profit: 5%
- Parámetros más agresivos para más trades

---

## 📊 Backtests con Configuraciones Específicas

### 3. Comprehensive Backtest

Backtest completo con múltiples estrategias y análisis detallado:

```bash
python scripts/run_comprehensive_backtest.py
```

**O con configuración YAML específica:**

```bash
python scripts/run_comprehensive_backtest.py --config config/backtesting/comprehensive_backtest.yaml
```

**Características:**
- Múltiples estrategias
- Análisis de métricas avanzadas
- Reportes detallados
- Walk-forward validation

---

### 4. Baseline Backtest

Backtest de línea base para comparación:

```bash
python scripts/run_baseline_backtest.py
```

**Uso:**
- Establece línea base de performance
- Comparación con otras estrategias
- Métricas de referencia

---

### 5. Automated Momentum Backtest

Backtest automatizado de estrategia momentum con optimización:

```bash
python scripts/run_automated_momentum_backtest.py
```

**Características:**
- Optimización automática de parámetros
- Grid search de configuraciones
- Selección de mejores parámetros

---

## 🤖 Backtests con Machine Learning

### 6. Deep Learning Backtest

Backtest con modelos de deep learning:

```bash
python scripts/run_deep_learning_backtest.py
```

**Requisitos:**
- Modelos de deep learning entrenados
- Datos históricos suficientes
- GPU recomendada (opcional)

---

### 7. Transformer Backtest

Backtest con modelos Transformer:

```bash
python scripts/run_transformer_backtest.py
```

**Características:**
- Modelos Transformer para predicción
- Análisis de secuencias temporales
- Attention mechanisms

---

## 🎯 Backtests con Strategy Engines

### 8. Backtest con TrendFollowingStrategyEngine

```bash
# Primero, crear un script temporal o modificar run_backtest.py
python -c "
from datetime import datetime
from decimal import Decimal
from app.backtesting.data_loader import DataLoader
from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.engines.strategy_engines import TrendFollowingStrategyEngine

# Configuración
SYMBOL = 'AAPL'
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 1, 1)
INITIAL_CAPITAL = Decimal('100000')

# Cargar datos
loader = DataLoader()
quotes = loader.load_market_data(SYMBOL, START_DATE, END_DATE)

# Crear engine
engine = TrendFollowingStrategyEngine({
    'adx_period': 14,
    'adx_threshold': 25.0,
    'macd_fast_period': 12,
    'macd_slow_period': 26,
    'macd_signal_period': 9,
    'min_volume_ratio': 1.2,
})

# Generar señales
signals = []
for quote in quotes:
    signals.extend(engine.generate_signals(quote))

# Ejecutar backtest
config = BacktestConfig(
    strategy_name='trend_following',
    initial_capital=INITIAL_CAPITAL,
    commission_per_trade=Decimal('1.0'),
    slippage_percentage=Decimal('0.1'),
)

backtester = SimpleBacktester(config)
result = backtester.run_backtest(quotes, signals)

print(f'Total Trades: {result.performance.total_trades}')
print(f'Win Rate: {result.performance.win_rate:.2f}%')
print(f'Total Return: {result.total_return:.2f}%')
"
```

---

### 9. Backtest con BreakoutStrategyEngine

```bash
python -c "
from datetime import datetime
from decimal import Decimal
from app.backtesting.data_loader import DataLoader
from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.engines.strategy_engines import BreakoutStrategyEngine

# Configuración
SYMBOL = 'AAPL'
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 1, 1)
INITIAL_CAPITAL = Decimal('100000')

# Cargar datos
loader = DataLoader()
quotes = loader.load_market_data(SYMBOL, START_DATE, END_DATE)

# Crear engine
engine = BreakoutStrategyEngine({
    'lookback_period': 20,
    'breakout_threshold_pct': 0.01,
    'min_volume_ratio': 1.5,
})

# Generar señales
signals = []
for quote in quotes:
    signals.extend(engine.generate_signals(quote))

# Ejecutar backtest
config = BacktestConfig(
    strategy_name='breakout',
    initial_capital=INITIAL_CAPITAL,
    commission_per_trade=Decimal('1.0'),
    slippage_percentage=Decimal('0.1'),
)

backtester = SimpleBacktester(config)
result = backtester.run_backtest(quotes, signals)

print(f'Total Trades: {result.performance.total_trades}')
print(f'Win Rate: {result.performance.win_rate:.2f}%')
print(f'Total Return: {result.total_return:.2f}%')
"
```

---

## 🔄 Ejecutar Todos los Backtests

### 10. Run All Backtests

Ejecutar todos los backtests disponibles:

```bash
python scripts/run_all_backtests.py
```

**Características:**
- Ejecuta todos los backtests en secuencia
- Genera reportes comparativos
- Resumen de resultados

---

## ⚙️ Configuraciones Personalizadas

### Modificar Parámetros en run_backtest.py

Edita `run_backtest.py` para cambiar:

```python
# Símbolo
SYMBOL = "MSFT"  # o "GOOGL", "TSLA", etc.

# Período
START_DATE = datetime(2023, 6, 1)
END_DATE = datetime(2024, 6, 1)

# Capital inicial
INITIAL_CAPITAL = Decimal("50000")

# Estrategia
STRATEGY_NAME = "mean_reversion"  # o "pairs_trading"

# Parámetros de estrategia
strategy = MomentumStrategy({
    "name": STRATEGY_NAME,
    "rsi_threshold": 45,  # Ajustar threshold
    "momentum_threshold": 0.02,
    "volume_threshold": 1.5,
})
```

---

### Usar Configuración YAML

```bash
# Comprehensive backtest con YAML
python scripts/run_comprehensive_backtest.py \
    --config config/backtesting/comprehensive_backtest.yaml \
    --symbol AAPL \
    --start-date 2024-01-01 \
    --end-date 2025-01-01
```

---

## 📈 Backtests con Múltiples Símbolos

### Script para múltiples símbolos

```bash
python -c "
from datetime import datetime
from decimal import Decimal
from app.backtesting.data_loader import DataLoader
from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.strategies.momentum import MomentumStrategy

SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 1, 1)
INITIAL_CAPITAL = Decimal('100000')

for symbol in SYMBOLS:
    print(f'\n=== {symbol} ===')
    loader = DataLoader()
    quotes = loader.load_market_data(symbol, START_DATE, END_DATE)
    
    if not quotes:
        print(f'No data for {symbol}')
        continue
    
    strategy = MomentumStrategy({'name': 'momentum'})
    signals = []
    for quote in quotes:
        signals.extend(strategy.generate_signals(quote))
    
    config = BacktestConfig(
        strategy_name='momentum',
        initial_capital=INITIAL_CAPITAL,
        commission_per_trade=Decimal('1.0'),
        slippage_percentage=Decimal('0.1'),
    )
    
    backtester = SimpleBacktester(config)
    result = backtester.run_backtest(quotes, signals)
    
    print(f'Trades: {result.performance.total_trades}')
    print(f'Return: {result.total_return:.2f}%')
"
```

---

## 🎛️ Opciones Avanzadas

### Con logging detallado

```bash
# Activar logging verbose
export LOG_LEVEL=DEBUG
python run_backtest.py
```

### Con salida a archivo

```bash
python run_backtest.py > backtest_results.txt 2>&1
```

### Con métricas específicas

```bash
python run_backtest.py --metrics sharpe,sortino,calmar
```

---

## 📝 Notas

1. **Datos históricos**: Asegúrate de tener datos históricos en `data/historical/` o que el DataLoader pueda descargarlos.

2. **Tiempo de ejecución**: Los backtests completos pueden tardar varios minutos dependiendo del período y número de quotes.

3. **Memoria**: Backtests con muchos datos pueden requerir bastante RAM. Considera limitar el número de quotes si hay problemas.

4. **Resultados**: Los resultados se muestran en consola. Para guardarlos, redirige la salida o modifica los scripts para escribir a archivos.

5. **Configuración**: Todos los parámetros están centralizados en `config/` y pueden modificarse sin cambiar código.

---

## 🔍 Troubleshooting

### Error: "No data available"

```bash
# Verificar que existen datos históricos
ls -la data/historical/

# O descargar datos
python scripts/download_historical_data.py
```

### Error: "Module not found"

```bash
# Asegurar que el entorno virtual está activado
source venv/bin/activate

# Verificar dependencias
pip install -r requirements.txt
```

### Error: "Out of memory"

```bash
# Limitar número de quotes en el script
quotes = quotes[:500]  # Solo primeros 500
```

---

## 📚 Referencias

- Documentación de backtesting: `docs/AUTOMATED_BACKTEST_GUIDE.md`
- Configuraciones: `config/backtesting/`
- Scripts: `scripts/run_*_backtest.py`

