# 📊 Tests Ejecutados por Defecto

## Comando

```bash
python scripts/run_comprehensive_backtest.py
```

Sin argumentos, ejecuta **todos los backtests que tengan `enabled: true`** en `config/backtesting/comprehensive_backtest.yaml`.

---

## 🎯 Tests Ejecutados (en orden)

Según la configuración actual, se ejecutan los siguientes tests en este orden:

### 1️⃣ **Baseline Backtest** ✅

- **Descripción**: Línea base con todos los módulos activos
- **Config**: `backtests.baseline.enabled: true`
- **Qué hace**: Mide performance base sin optimización ni learning engines
- **Tiempo estimado**: ~30 segundos

### 2️⃣ **Learning Engines Backtest** ✅

- **Descripción**: Prueba cada learning engine individualmente
- **Config**: `backtests.learning_engines.enabled: true`
- **Qué hace**:
  - Ejecuta baseline SIN learning engine
  - Luego ejecuta CON cada learning engine habilitado (supervised, deep, reinforcement, transformer)
  - Compara métricas antes/después del entrenamiento
- **Learning engines habilitados**:
  - `supervised: enabled: true`
  - `deep: enabled: true`
  - `reinforcement: enabled: true`
  - `transformer: enabled: true`
- **Tiempo estimado**: ~2-5 minutos por engine

### 3️⃣ **Walk-Forward Backtest** ✅

- **Descripción**: Optimización por ventana temporal
- **Config**: `backtests.walk_forward.enabled: true`
- **Qué hace**: Evalúa optimización por ventana temporal (70% train, 30% test)
- **Tiempo estimado**: ~2 minutos

### 4️⃣ **Monte Carlo / Stress Test** ✅

- **Descripción**: Test de robustez con simulaciones aleatorias
- **Config**: `backtests.monte_carlo.enabled: true`
- **Qué hace**:
  - 100 simulaciones con volatilidad y shocks de precio aleatorios
  - Evalúa robustez frente a condiciones extremas
- **Paralelizable**: Sí (si `parallelization.enabled: true`)
- **Tiempo estimado**: ~5-10 minutos (paralelo) o ~30-60 minutos (secuencial)

### 5️⃣ **Grid Search** ✅

- **Descripción**: Búsqueda de parámetros óptimos (thresholds)
- **Config**: `backtests.grid_search.enabled: true`
- **Qué hace**:
  - Prueba 100 combinaciones aleatorias de thresholds
  - Optimiza: RSI buy/sell, momentum, volume
  - Métrica objetivo: sharpe_ratio
- **Paralelizable**: Sí (si `parallelization.enabled: true`)
- **Tiempo estimado**: ~10-20 minutos (paralelo) o ~1-2 horas (secuencial)

### 6️⃣ **Hyperparameter Optimization (Completo)** ✅ (NUEVO)

- **Descripción**: Optimización completa de hiperparámetros
- **Config**: `backtests.hyperparameter_optimization.enabled: true`
- **Qué hace**:
  - Optimiza presets (conservative/balanced/aggressive)
  - Optimiza learning engine params (algoritmos, thresholds)
  - Optimiza risk params (position size, stop-loss, take-profit)
  - Optimiza filter thresholds
- **Método**: random_search (100 iteraciones)
- **Tiempo estimado**: ~30-60 minutos

### 7️⃣ **Transformer Optimization** ✅

- **Descripción**: Optimización iterativa usando Transformer
- **Config**: `backtests.transformer_optimization.enabled: true`
- **Qué hace**: Optimización iterativa hasta convergencia (50 iteraciones máximo)
- **Tiempo estimado**: ~10-20 minutos

### 8️⃣ **Ablation Study** ✅

- **Descripción**: Impacto individual de cada módulo
- **Config**: `backtests.ablation.enabled: true`
- **Qué hace**: Desactiva cada módulo uno a uno para medir impacto
- **Módulos probados**: ema_filter, rsi_filter, stoch_rsi_filter, momentum_filter, volume_filter, atr_filter
- **Tiempo estimado**: ~3-5 minutos

### 9️⃣ **Out-of-Sample Backtest** ✅

- **Descripción**: Validación forward con parámetros optimizados
- **Config**: `backtests.out_of_sample.enabled: true`
- **Qué hace**:
  - Usa parámetros del grid_search si `use_optimized_params: true`
  - Divide datos 70% train / 30% test
- **Tiempo estimado**: ~1-2 minutos

### 🔟 **Multi-Strategy Backtest** ✅

- **Descripción**: Múltiples estrategias simultáneas con división de capital
- **Config**: `backtests.multi_strategy.enabled: true`
- **Qué hace**:
  - Prueba momentum + mean_reversion + pairs_trading simultáneamente
  - Divide capital entre estrategias
  - Reasignación dinámica cada 30 días (si `enable_dynamic_reallocation: true`)
- **Tiempo estimado**: ~2-3 minutos

### 1️⃣1️⃣ **Regime Test** ✅

- **Descripción**: Evaluar desempeño según régimen de mercado
- **Config**: `backtests.regime_test.enabled: true`
- **Qué hace**:
  - Evalúa en bull_market, bear_market, sideways_market
  - Compara performance por régimen
- **Tiempo estimado**: ~2-3 minutos

---

## 📊 Resumen Total

| Test                        | Habilitado | Paralelizable | Tiempo Estimado       |
| --------------------------- | ---------- | ------------- | --------------------- |
| Baseline                    | ✅ Sí      | ❌ No         | ~30s                  |
| Learning Engines            | ✅ Sí      | ⚠️ Parcial    | ~2-5 min              |
| Walk-Forward                | ✅ Sí      | ❌ No         | ~2 min                |
| Monte Carlo                 | ✅ Sí      | ✅ Sí         | ~5-10 min (paralelo)  |
| Grid Search                 | ✅ Sí      | ✅ Sí         | ~10-20 min (paralelo) |
| Hyperparameter Optimization | ✅ Sí      | ❌ No         | ~30-60 min            |
| Transformer Optimization    | ✅ Sí      | ❌ No         | ~10-20 min            |
| Ablation                    | ✅ Sí      | ❌ No         | ~3-5 min              |
| Out-of-Sample               | ✅ Sí      | ❌ No         | ~1-2 min              |
| Multi-Strategy              | ✅ Sí      | ❌ No         | ~2-3 min              |
| Regime Test                 | ✅ Sí      | ❌ No         | ~2-3 min              |

**Tiempo total estimado**: ~1-2 horas (con paralelización) o ~3-4 horas (sin paralelización)

---

## ⚙️ Configuración Actual

Todos los tests están habilitados por defecto. Para deshabilitar un test, edita `config/backtesting/comprehensive_backtest.yaml`:

```yaml
backtests:
  baseline:
    enabled: false # Deshabilitar baseline
```

---

## 🎯 Ejecutar Tests Específicos

Si quieres ejecutar solo algunos tests:

```bash
# Solo baseline y grid_search
python scripts/run_comprehensive_backtest.py baseline grid_search

# Solo learning engines
python scripts/run_comprehensive_backtest.py learning_engines

# Múltiples tests
python scripts/run_comprehensive_backtest.py baseline learning_engines ablation
```

---

## 📝 Notas

- **Paralelización**: Si `parallelization.enabled: true`, Monte Carlo, Grid Search y Learning Engines se ejecutan en paralelo
- **Meta-Analysis**: Al final se ejecuta análisis meta si `meta_analysis.enabled: true`
- **Comparación**: Al final se comparan resultados de `grid_search` vs `hyperparameter_optimization`
