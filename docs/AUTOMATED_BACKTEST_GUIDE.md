# Guía de Backtest Automatizado - Momentum Modular

## Descripción

Sistema de backtest automatizado que ejecuta múltiples configuraciones de la estrategia Momentum Modular, incluyendo:

1. **Baseline reviews**: Todos los módulos activos
2. **Ablation Study**: Desactivar módulos uno por uno para medir impacto
3. **Learning Engines**: Probar con Supervised Learning, Deep Learning y Reinforcement Learning

## Uso

### Ejecución Básica

```bash
python scripts/run_automated_momentum_backtest.py
```

### Ejecución Programática

```python
from app.strategies.momentum_modular.automated_backtest import run_automated_backtest
from decimal import Decimal
from datetime import datetime, timedelta

# Auto-seleccionar mejor stock
results = run_automated_backtest(
    symbol=None,
    criteria="momentum_signal",
    initial_capital=Decimal("100000")
)

# O especificar stock manualmente
results = run_automated_backtest(
    symbol="AAPL",
    start_date=datetime.now() - timedelta(days=365),
    end_date=datetime.now(),
    initial_capital=Decimal("100000")
)
```

## Estructura del Reporte

El sistema genera:

1. **Métricas por configuración**:

   - Total P&L
   - Win Rate (%)
   - Sharpe Ratio
   - Max Drawdown (%)
   - Total Trades
   - Return (%)

2. **Ranking**:

   - Ordenado por Sharpe Ratio (descendente)
   - Identifica mejor configuración automáticamente

3. **Archivo CSV**:
   - Guardado en `docs/BACKTEST_RESULTS/automated_backtest_{SYMBOL}_{TIMESTAMP}.csv`

## Configuraciones Probadas

### 1. Baseline

- Todos los módulos activos (EMAFilter, RSIFilter, StochRSIFilter, MomentumFilter, VolumeFilter, ATRFilter)

### 2. Ablation Study (6 configuraciones)

- Sin EMAFilter
- Sin RSIFilter
- Sin StochRSIFilter
- Sin MomentumFilter
- Sin VolumeFilter
- Sin ATRFilter

### 3. Learning Engines (3 configuraciones)

- Supervised Learning (RandomForest)
- Deep Learning (LSTM)
- Reinforcement Learning (PPO)

**Total: ~10 configuraciones probadas**

## Interpretación de Resultados

- **Sharpe Ratio**: Medida de retorno ajustado por riesgo (mayor es mejor)
- **Return %**: Retorno total del período
- **Win Rate**: % de trades ganadores (idealmente >45%)
- **Max Drawdown**: Pérdida máxima desde peak (menor es mejor, idealmente <15%)
- **Total Trades**: Número de trades ejecutados

## Requisitos

### Librerías necesarias:

```bash
pip install pandas numpy scikit-learn xgboost
pip install torch  # Para Deep Learning
pip install stable-baselines3 gym  # Para Reinforcement Learning
```

## Personalización

### Cambiar criterio de selección de stock:

```python
results = run_automated_backtest(
    criteria="performance",  # o "volatility"
    ...
)
```

### Cambiar algoritmo de learning:

Modificar en `automated_backtest.py`:

- Supervised: `"random_forest"`, `"xgboost"`, `"gradient_boosting"`
- Deep: `"lstm"`, `"gru"`
- RL: `"ppo"`, `"a2c"`, `"ddpg"`

## Troubleshooting

1. **No hay datos históricos**: Verificar conexión a proveedor de datos
2. **Error en learning engines**: Verificar que librerías estén instaladas
3. **Timeout**: Reducir número de símbolos analizados en `PortfolioAnalyzer`

## Output Example

```
================================================================================
RESUMEN COMPARATIVO DE BACKTESTS
================================================================================

                    name  total_pnl  win_rate  sharpe_ratio  max_drawdown  total_trades  return_pct
BASELINE - All Modules     5234.50     48.30         1.85         12.30           142        5.23
SUPERVISED - RANDOM_FOREST 4891.20     51.20         1.72         11.50           138        4.89
ABLATION - Without ATR     4210.30     46.80         1.58         13.20           155        4.21
...

🏆 MEJOR ESTRATEGIA: BASELINE - All Modules
   Sharpe Ratio: 1.850
   Return %: 5.23%
   Win Rate: 48.30%
```
