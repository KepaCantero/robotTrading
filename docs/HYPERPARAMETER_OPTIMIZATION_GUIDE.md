# 🎯 Guía de Optimización Automatizada de Hiperparámetros

## 📋 Descripción

Sistema completo de optimización automatizada que ejecuta múltiples backtests variando parámetros del strategy y learning engines para encontrar la configuración óptima que maximice métricas de performance.

---

## 🚀 Uso Rápido

### Ejecutar Optimización

```bash
cd /Users/kepa.cantero/Projects/algoTrading
python scripts/run_hyperparameter_optimization.py
```

### Configurar Parámetros

Editar `scripts/run_hyperparameter_optimization.py`:

```python
symbol = "AAPL"  # Stock a optimizar
year = 2023  # Año de datos
optimization_metric = "sharpe_ratio"  # "sharpe_ratio", "total_pnl", "win_rate", "combined"
optimization_method = "random_search"  # "grid_search", "random_search"
max_iterations = 1000  # Número de configuraciones a probar
```

---

## 📊 Funcionalidades

### 1. Selección de Stock y Año

- Selecciona un stock específico (ej: "AAPL")
- Define un año completo de datos (1 año)
- Descarga datos históricos automáticamente

### 2. Variación de Parámetros

El sistema varía automáticamente:

**Estrategia:**

- Presets (conservative/balanced/aggressive)
- Parámetros de filtros (RSI, EMA, Momentum, Volume, ATR)
- Thresholds de compra/venta
- Parámetros de riesgo (position size, stop-loss, take-profit)

**Learning Engines:**

- Habilitar/deshabilitar learning
- Tipo de engine (supervised/deep/reinforcement)
- Algoritmos específicos (RandomForest, XGBoost, LSTM, PPO, etc.)
- Thresholds de probabilidad
- Frecuencia de reentrenamiento

### 3. Ejecución de Backtests

- Ejecuta backtest completo para cada configuración
- Registra métricas de performance:
  - Total PnL
  - Sharpe Ratio
  - Win Rate
  - Max Drawdown
  - Total Trades
  - Return anualizado

### 4. Selección de Mejor Configuración

- Calcula score basado en métrica objetivo
- Mantiene registro de mejor configuración
- Actualiza automáticamente cuando encuentra mejor resultado

### 5. Guardado de Resultados

Genera 3 archivos en `docs/OPTIMIZATION_RESULTS/`:

1. **best*config*{symbol}\_{timestamp}.json**

   - Mejor configuración encontrada
   - Parámetros óptimos
   - Score obtenido

2. **optimization*report*{symbol}\_{timestamp}.csv**

   - Reporte completo de todas las iteraciones
   - Métricas de cada configuración probada
   - Ordenado por score (mejor a peor)

3. **summary*{symbol}*{timestamp}.txt**
   - Resumen ejecutivo
   - Top 10 resultados
   - Configuración óptima

---

## ⚙️ Métodos de Optimización

### Grid Search

- Prueba todas las combinaciones de parámetros principales
- Exhaustivo pero puede ser lento
- Recomendado para espacios pequeños

### Random Search (Recomendado)

- Prueba configuraciones aleatorias del espacio de búsqueda
- Más eficiente para espacios grandes
- Recomendado para 1000+ iteraciones

---

## 🎯 Métricas de Optimización

### Sharpe Ratio (Recomendado)

```python
optimization_metric = "sharpe_ratio"
```

- Optimiza relación riesgo/retorno
- Mejor para estrategias balanceadas

### Total PnL

```python
optimization_metric = "total_pnl"
```

- Optimiza ganancias absolutas
- Puede favorecer estrategias de alto riesgo

### Win Rate

```python
optimization_metric = "win_rate"
```

- Optimiza porcentaje de trades ganadores
- Puede sacrificar tamaño de ganancias

### Combined

```python
optimization_metric = "combined"
```

- Score combinado: Sharpe _ 0.4 + PnL_norm _ 0.3 + WinRate_norm \* 0.3
- Balance entre todas las métricas

---

## 📈 Espacio de Búsqueda

El sistema varía estos parámetros:

| Categoría      | Parámetros               | Valores                                |
| -------------- | ------------------------ | -------------------------------------- |
| **Estrategia** | preset                   | conservative, balanced, aggressive     |
|                | ema_fast_period          | 10, 12, 14, 16                         |
|                | ema_slow_period          | 24, 26, 28, 30                         |
|                | rsi_period               | 12, 14, 16                             |
|                | rsi_buy_min              | 40, 45, 50                             |
|                | rsi_buy_max              | 65, 70, 75                             |
|                | momentum_threshold       | 0.01, 0.015, 0.02, 0.025               |
|                | volume_threshold         | 1.05, 1.1, 1.15, 1.2                   |
|                | atr_percentile_threshold | 55, 60, 65, 70                         |
| **Riesgo**     | max_position_size        | 0.05, 0.10, 0.15, 0.20                 |
|                | stop_loss_pct            | 0.02, 0.025, 0.03                      |
|                | take_profit_pct          | 0.06, 0.08, 0.10                       |
| **Learning**   | enable_learning          | True, False                            |
|                | learning_engine_type     | supervised, deep, reinforcement        |
|                | learning_algorithm       | RandomForest, XGBoost, LSTM, PPO, etc. |
|                | min_success_probability  | 0.5, 0.55, 0.6, 0.65                   |
|                | rebalance_frequency_days | 5, 7, 10, 14                           |

**Total de combinaciones posibles:** Millones

---

## 📝 Ejemplo de Salida

```
🚀 Iniciando optimización de hiperparámetros
   Símbolo: AAPL
   Período: 2023-01-01 - 2023-12-31
   Métrica objetivo: sharpe_ratio
   Método: random_search
   Máximo de iteraciones: 1000

📊 Generadas 1000 configuraciones a probar

================================================================================
🔄 Iteración 1/1000
   Config: preset=balanced, learning=True, engine=supervised, rsi_min=45, momentum=0.015, volume=1.1
   Score: 1.2345 | PnL: $5234.56 | Sharpe: 1.23 | Win Rate: 52.3%

✅ ¡Nuevo mejor resultado! Score: 1.2345

...

================================================================================
📊 RESULTADOS DE OPTIMIZACIÓN
================================================================================
Mejor Score: 2.4567
Total Iteraciones: 1000

Mejor Configuración:
.get('preset'): balanced
  'enable_learning': True
  'learning_engine_type': supervised
  'learning_algorithm': xgboost
  'rsi_buy_min': 45
  'momentum_threshold': 0.02
  ...
```

---

## 🔧 Personalización

### Agregar Nuevos Parámetros

Editar `hyperparameter_optimizer.py`:

```python
def _define_parameter_space(self) -> Dict[str, List[Any]]:
    return {
        # ... parámetros existentes ...
        'nuevo_parametro': [valor1, valor2, valor3],
    }
```

### Cambiar Métrica de Optimización

```python
optimizer = HyperparameterOptimizer(
    ...
    optimization_metric="total_pnl"  # Cambiar aquí
)
```

### Cambiar Método de Búsqueda

```python
optimizer = HyperparameterOptimizer(
    ...
    optimization_method="grid_search"  # Cambiar aquí
)
```

---

## ⚠️ Consideraciones

### Tiempo de Ejecución

- **1000 iteraciones** ≈ 2-4 horas (depende del hardware)
- Cada iteración ejecuta un backtest completo de 1 año
- Learning engines pueden aumentar tiempo significativamente

### Overfitting

- Los parámetros optimizados pueden estar sobreajustados al año seleccionado
- **Recomendación:** Validar en datos out-of-sample después de optimizar

### Recursos

- Requiere suficiente RAM para múltiples backtests
- Learning engines (especialmente Deep/RL) requieren más recursos

---

## 📊 Interpretación de Resultados

### Mejor Configuración

- Guardada en `best_config_{symbol}_{timestamp}.json`
- Lista para usar directamente en producción

### Reporte Completo

- CSV con todas las iteraciones
- Permite análisis de sensibilidad
- Identificar rangos de parámetros prometedores

### Top 10 Resultados

- Ver qué parámetros aparecen frecuentemente
- Identificar patrones en configuraciones exitosas

---

## 🎯 Próximos Pasos

1. **Ejecutar optimización** con diferentes stocks/años
2. **Validar** mejores configuraciones en datos out-of-sample
3. **Analizar** reportes para entender qué parámetros son más importantes
4. **Refinar** espacio de búsqueda basado en resultados
5. **Implementar** mejor configuración en producción

---

**✅ Sistema completamente funcional y listo para usar**
