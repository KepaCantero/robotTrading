# 🎯 Sistema de Optimización Automática Multi-Estrategia

Sistema de optimización bayesiana que ajusta parámetros de las tres estrategias simultáneamente usando Optuna, considerando asignación de capital y maximizando métricas combinadas.

## 📋 Características

- **Optimización Bayesiana**: Usa Optuna para explorar espacios de parámetros eficientemente
- **Multi-Estrategia Simultánea**: Optimiza Momentum, Mean Reversion y Pairs Trading al mismo tiempo
- **Asignación de Capital**: Optimiza pesos de capital entre estrategias
- **Múltiples Métricas**: Maximiza Sharpe ratio, retorno total, o Calmar ratio
- **Backtest de 10 Años**: Valida optimización sobre período extenso
- **Persistencia**: Guarda estudios Optuna para reanudar optimizaciones

## 🚀 Uso Rápido

### Instalación de Dependencias

```bash
pip install optuna plotly kaleido  # Para visualizaciones
```

### Ejecutar Optimización

```bash
# Optimización básica (50 trials, Sharpe ratio)
python scripts/optimize_multi_strategy.py --symbol AAPL

# Optimización extendida (100 trials)
python scripts/optimize_multi_strategy.py --symbol AAPL --trials 100

# Optimizar para retorno total en vez de Sharpe
python scripts/optimize_multi_strategy.py --symbol AAPL --metric return

# Con persistencia (permite reanudar)
python scripts/optimize_multi_strategy.py --symbol AAPL --trials 100 --storage sqlite:///optimization.db --study-name my_study
python scripts/optimize_multi_strategy.py --symbol AAPL --storage sqlite:///optimization.db --study-name my_study --resume
```

## 📊 Parámetros Optimizados

### Momentum Strategy

- `rsi_threshold`: 30.0 - 50.0
- `momentum_threshold`: 0.01 - 0.05
- `volume_threshold`: 1.0 - 2.5
- `ema_period`: 10 - 50
- `rsi_period`: 10 - 20
- `lookback_period`: 3 - 10

### Mean Reversion Strategy

- `z_score_threshold`: 0.5 - 3.0
- `volatility_threshold`: 0.01 - 0.05
- `lookback_period`: 10 - 30
- `mean_reversion_speed`: 0.05 - 0.2
- `min_z_score`: 1.0 - 2.5

### Pairs Trading Strategy

- `spread_threshold`: 0.1 - 1.0
- `cointegration_threshold`: 0.01 - 0.1
- `min_correlation`: 0.3 - 0.8
- `lookback_period`: 20 - 50

### Capital Allocation

- `momentum`: 40% - 70%
- `mean_reversion`: 15% - 40%
- `pairs_trading`: Resto (5% mínimo)

## 🎯 Métricas Objetivo

### Sharpe Ratio (default)
Maximiza el ratio de Sharpe combinado ponderado por capital:

```python
weighted_sharpe = Σ(strategy_sharpe × strategy_weight)
```

### Total Return
Maximiza el retorno total combinado del portfolio.

### Calmar Ratio
Ratio de retorno anualizado vs. máximo drawdown:

```python
calmar = annualized_return / max_drawdown
```

## 📈 Resultados

El script genera:

1. **Configuración Óptima**: `optimized_strategy_config.json`
2. **Visualizaciones Optuna** (si están disponibles):
   - `docs/OPTIMIZATION_RESULTS/optimization_history.html`
   - `docs/OPTIMIZATION_RESULTS/param_importances.html`
3. **Resumen en consola** con:
   - Mejores parámetros por estrategia
   - Asignación de capital óptima
   - Resultados del backtest final

## 🔧 Uso Programático

```python
from decimal import Decimal
from datetime import datetime, timedelta
from app.optimization.multi_strategy_optimizer import MultiStrategyOptimizer

# Crear optimizador
optimizer = MultiStrategyOptimizer(
    total_capital=Decimal("100000"),
    symbol="AAPL",
    start_date=datetime.now() - timedelta(days=365 * 10),
    end_date=datetime.now(),
    n_trials=50,
    objective_metric="sharpe",
)

# Ejecutar optimización
study = optimizer.optimize(
    study_name="my_optimization",
    storage=None,  # o "sqlite:///optimization.db" para persistencia
)

# Obtener mejor configuración
best_config = optimizer.get_best_config()
print(f"Best Sharpe: {optimizer.best_value:.4f}")
print(f"Best params: {optimizer.best_params}")

# Ejecutar backtest final con parámetros óptimos
results = optimizer.run_backtest_with_best_params()
print(f"Final return: {results['combined']['total_return']:.2f}%")
```

## 📝 Ejemplo de Output

```
================================================================================
OPTIMIZATION SUMMARY
================================================================================
Best sharpe: 0.3421

Best Parameters:

MOMENTUM:
  rsi_threshold: 42.0
  momentum_threshold: 0.03
  volume_threshold: 1.8
  ema_period: 25
  rsi_period: 14
  lookback_period: 5

MEAN_REVERSION:
  z_score_threshold: 1.5
  volatility_threshold: 0.03
  lookback_period: 20
  mean_reversion_speed: 0.1
  min_z_score: 1.5

CAPITAL ALLOCATION:
  momentum: 55.0% ($55,000.00)
  mean_reversion: 30.0% ($30,000.00)
  pairs_trading: 15.0% ($15,000.00)

FINAL BACKTEST RESULTS:
  Total Return: 12.34%
  Total Trades: 437
  Weighted Sharpe: 0.3421
  Weighted Max DD: -14.09%
```

## ⚙️ Configuración Avanzada

### Personalizar Espacios de Búsqueda

Edita `app/optimization/multi_strategy_optimizer.py` método `_suggest_strategy_params`:

```python
# Ejemplo: reducir rango de RSI threshold
params["momentum"] = {
    "rsi_threshold": trial.suggest_float("momentum_rsi_threshold", 35.0, 45.0, step=1.0),
    # ...
}
```

### Añadir Nuevas Métricas

Extiende el método `_objective_function`:

```python
elif self.objective_metric == "sortino":
    # Calcular Sortino ratio
    metric_value = calculate_sortino(results)
```

## 🎓 Referencias

- **Optuna**: https://optuna.org/
- **Bayesian Optimization**: https://en.wikipedia.org/wiki/Bayesian_optimization
- **Multi-Strategy Allocation**: Ver `app/services/multi_strategy_allocation.py`

---

*Última actualización: 2025-10-28*

