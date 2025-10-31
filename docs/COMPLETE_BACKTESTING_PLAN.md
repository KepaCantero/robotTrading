# 🧪 Plan Completo de Backtesting - Momentum Modular Strategy

## 📋 Resumen Ejecutivo

Este documento describe el plan completo de backtesting para la estrategia Momentum Modular con Learning Engines. El objetivo es validar y optimizar la estrategia mediante una serie sistemática de pruebas que cubren:

1. **Baseline Tests** - Performance base sin optimización
2. **Ablation Tests** - Impacto individual de cada módulo
3. **Parameter Optimization** - Encontrar parámetros óptimos
4. **ML Engine Tests** - Evaluar cada engine ML
5. **Combined Optimization** - Optimización completa integrada
6. **Walk-Forward Validation** - Validación temporal robusta
7. **Stress/Scenario Testing** - Resiliencia en condiciones extremas

---

## 1️⃣ Baseline Tests

**Objetivo:** Medir performance de la estrategia completa sin optimización.

### Configuración:

- **Todos los módulos activos:** `ema_filter`, `rsi_filter`, `stoch_rsi_filter`, `momentum_filter`, `volume_filter`, `atr_filter`
- **Sin ML:** `learning_engine: null`
- **Preset:** `balanced`
- **Período:** 1 año inicial (expandible a 2-3 años)
- **Símbolos:** Portafolio completo desde `config/portfolio.yaml`

### Métricas a Registrar:

- ✅ Total PnL
- ✅ Sharpe Ratio
- ✅ Win Rate
- ✅ Max Drawdown
- ✅ Total Trades
- ✅ Average Trade Duration
- ✅ Profit Factor
- ✅ Equity Curve

### Script de Ejecución:

```bash
python scripts/run_baseline_backtest.py \
    --symbol AAPL \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --output-dir docs/BACKTEST_RESULTS/baseline
```

### Archivos de Resultados:

- `baseline_results_{symbol}_{timestamp}.json`
- `baseline_equity_curve_{symbol}_{timestamp}.csv`
- `baseline_trades_{symbol}_{timestamp}.csv`

---

## 2️⃣ Ablation Tests

**Objetivo:** Identificar impacto individual de cada módulo desactivándolo uno a uno.

### Configuración:

- **Base:** Todos los módulos activos (baseline)
- **Tests:** Desactivar cada módulo individualmente:
  1. `ema_filter: disabled`
  2. `rsi_filter: disabled`
  3. `stoch_rsi_filter: disabled`
  4. `momentum_filter: disabled`
  5. `volume_filter: disabled`
  6. `atr_filter: disabled`

### Métricas a Comparar:

- **PnL Delta:** `PnL_without_module - PnL_baseline`
- **Sharpe Delta:** `Sharpe_without_module - Sharpe_baseline`
- **Trade Count Delta:** `Trades_without_module - Trades_baseline`
- **Drawdown Impact:** `Drawdown_without_module - Drawdown_baseline`

### Script de Ejecución:

```bash
python scripts/run_ablation_backtest.py \
    --symbol AAPL \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --modules ema_filter,rsi_filter,stoch_rsi_filter,momentum_filter,volume_filter,atr_filter \
    --output-dir docs/BACKTEST_RESULTS/ablation
```

### Archivos de Resultados:

- `ablation_report_{symbol}_{timestamp}.csv` - Comparación tabular
- `ablation_summary_{symbol}_{timestamp}.md` - Resumen ejecutivo
- `ablation_charts_{symbol}_{timestamp}.html` - Visualizaciones

### Interpretación:

- **Módulo con impacto positivo:** Mejor performance sin él → Considerar remover
- **Módulo con impacto negativo:** Peor performance sin él → Módulo crítico
- **Módulo neutral:** Sin cambio significativo → Evaluar si simplificar

---

## 3️⃣ Parameter Optimization Tests

**Objetivo:** Encontrar valores óptimos de parámetros para cada módulo.

### Estrategia de Búsqueda:

- **Método 1: Grid Search** (exhaustivo para espacios pequeños)
- **Método 2: Random Search** (más eficiente para espacios grandes)
- **Método 3: Optuna TPE** (Bayesian Optimization - recomendado)

### Parámetros a Optimizar:

#### EMA Filter:

- `ema_fast_period`: [10, 12, 14, 16, 18, 20]
- `ema_slow_period`: [24, 26, 28, 30, 32, 34]
- `min_distance_pct`: [0.001, 0.002, 0.003, 0.005, 0.01]

#### RSI Filter:

- `rsi_period`: [12, 14, 16, 18]
- `rsi_buy_min`: [40, 45, 50, 55]
- `rsi_buy_max`: [65, 70, 75, 80]

#### Momentum Filter:

- `momentum_threshold`: [0.01, 0.015, 0.02, 0.025, 0.03]
- `lookback_period`: [10, 12, 14, 16]

#### Volume Filter:

- `volume_threshold`: [1.05, 1.1, 1.15, 1.2, 1.25]
- `volume_period`: [10, 14, 20]

#### ATR Filter:

- `atr_period`: [10, 14, 20]
- `atr_percentile_threshold`: [55, 60, 65, 70, 75]
- `min_atr_threshold`: [0.005, 0.006, 0.007, 0.008]

#### Risk Parameters:

- `max_position_size`: [0.05, 0.10, 0.15, 0.20]
- `stop_loss_pct`: [0.02, 0.025, 0.03, 0.035]
- `take_profit_pct`: [0.06, 0.08, 0.10, 0.12]

### Métrica de Optimización:

```python
# Opción 1: Sharpe Ratio (recomendado)
optimization_metric = "sharpe_ratio"

# Opción 2: Total PnL ajustado por drawdown
optimization_metric = "pnl_adjusted_drawdown"
score = total_pnl * (1 - max_drawdown)

# Opción 3: Combinado
optimization_metric = "combined"
score = sharpe_ratio * 0.4 + pnl_norm * 0.3 + win_rate_norm * 0.3
```

### Script de Ejecución:

```bash
# Usando el hyperparameter optimizer existente
python scripts/run_hyperparameter_optimization.py \
    --symbol AAPL \
    --start-date 2023-.cloud-01 \
    --end-date 2024-01-01 \
    --method random_search \
    --iterations 1000 \
    --metric sharpe_ratio \
    --output-dir docs/OPTIMIZATION_RESULTS
```

### Archivos de Resultados:

- `best_config_{symbol}_{timestamp}.json` - Mejor configuración
- `optimization_report_{symbol}_{timestamp}.csv` - Todas las iteraciones
- `parameter_importance_{symbol}_{timestamp}.html` - Importancia de parámetros
- `optimization_summary_{symbol}_{timestamp}.md` - Resumen

---

## 4️⃣ Machine Learning Engine Tests

**Objetivo:** Evaluar impacto de cada engine ML en el rendimiento.

### 4.1 Supervised Learning Engine

#### Algoritmos a Probar:

1. **RandomForest**

   - `n_estimators`: [50, 100, 200, 300]
   - `max_depth`: [5, 10, 15, None]
   - `min_samples_split`: [2, 5, 10]

2. **GradientBoosting**

   - `n_estimators`: [50, 100, 200]
   - `learning_rate`: [0.01, 0.1, 0.2]
   - `max_depth`: [3, 5, 7]

3. **XGBoost** (si disponible)
   - `n_estimators`: [50, 100, 200]
   - `learning_rate`: [0.01, 0.1, 0.2]
   - `max_depth`: [3, 5, 7]

#### Configuración:

- **Train/Test Split:** 70% / 30%
- **Feature Engineering:** Completo (indicadores técnicos + filtros)
- **Target:** Probabilidad de éxito del trade (>0 significa ganancia)

#### Script:

```bash
python scripts/run_ml_backtest.py \
    --symbol AAPL \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --engine-type supervised \
    --algorithm random_forest \
    --train-split 0.7 \
    --optimize-hyperparams \
    --output-dir docs/BACKTEST_RESULTS/ml_supervised
```

### 4.2 Deep Learning Engine

#### Arquitecturas:

1. **LSTM**

   - `hidden_size`: [32, 64, 128]
   - `num_layers`: [1, 2, 3]
   - `sequence_length`: [30, 60, 90]
   - `dropout`: [0.1, 0.2, 0.3]

2. **GRU**
   - `hidden_size`: [32, 64, 128]
   - `num_layers`: [1, 2, 3]
   - `sequence_length`: [30, 60, 90]
   - `dropout`: [0.1, 0.2, 0.3]

#### Configuración:

- **Backend:** PyTorch (o TensorFlow si PyTorch no disponible)
- **Train/Test Split:** 70% / 30%
- **Features:** Secuencias temporales de indicadores
- **Epochs:** 50-100 con early stopping

#### Script:

```bash
python scripts/run_ml_backtest.py \
    --symbol AAPL \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --engine-type deep \
    --architecture lstm \
    --sequence-length 60 \
    --epochs 100 \
    --output-dir docs/BACKTEST_RESULTS/ml_deep
```

### 4.3 Reinforcement Learning Engine

#### Algoritmos:

1. **PPO (Proximal Policy Optimization)**

   - `learning_rate`: [1e-4, 3e-4, 1e-3]
   - `batch_size`: [32, 64, 128]
   - `n_steps`: [2048, 4096]

2. **A2C (Advantage Actor-Critic)**

   - `learning_rate`: [1e-4, 3e-4, 1e-3]
   - `n_steps`: [5, 10, 20]

3. **DQN** (si aplicable)
   - `learning_rate`: [1e-4, 1e-3]
   - `buffer_size`: [10000, 50000]

#### Configuración:

- **Environment:** Custom Trading Environment
- **Reward Function:** Sharpe-adjusted returns
- **Training Steps:** 100K - 500K steps

#### Script:

```bash
python scripts/run_ml_backtest.py \
    --symbol AAPL \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --engine-type reinforcement \
    --algorithm ppo \
    --training-steps 200000 \
    --output-dir docs/BACKTEST_RESULTS/ml_rl
```

### Métricas ML-Specific:

- ✅ **Model Accuracy:** Para Supervised (classification accuracy)
- ✅ **Training/Validation Loss:** Para Deep Learning
- ✅ **Episode Rewards:** Para Reinforcement Learning
- ✅ **Feature Importance:** Para Supervised (si aplicable)
- ✅ **Prediction Confidence:** Confidence scores de predicciones

---

## 5️⃣ Combined Optimization + ML

**Objetivo:** Maximizar retorno integrando módulos optimizados + ML.

### Estrategia:

1. **Fase 1:** Optimizar parámetros de módulos técnicos (sin ML)
2. **Fase 2:** Entrenar y optimizar engine ML con módulos técnicos fijos
3. **Fase 3:** Fine-tuning conjunto de parámetros técnicos + ML

### Configuración:

- **Módulos técnicos:** Parámetros óptimos de Fase 3
- **ML Engine:** Mejor engine de Fase 4
- **Reentrenamiento:** Automático cada 7 días (LearningEngineUpdater)

### Script:

```bash
python scripts/run_combined_optimization.py \
    --symbol AAPL \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --phase all \
    --output-dir docs/BACKTEST_RESULTS/combined
```

### Archivos:

- `combined_phase1_technical_opt.json` - Parámetros técnicos óptimos
- `combined_phase2_ml_opt.json` - Parámetros ML óptimos
- `combined_phase3_final.json` - Configuración final
- `combined_results_comparison.md` - Comparación de fases

---

## 6️⃣ Rolling / Walk-Forward Validation

**Objetivo:** Evitar sobreajuste y asegurar consistencia temporal.

### Configuración:

- **Training Window:** 3 meses
- **Testing Window:** 1 mes
- **Step:** 1 mes (rolling window)
- **Total Period:** 1 año (4-6 iteraciones)

### Proceso:

1. **Iteración 1:**

   - Train: 2023-01-01 a 2023-04-01
   - Test: 2023-04-01 a 2023-05-01

2. **Iteración 2:**

   - Train: 2023-02-01 a 2023-05-01
   - Test: 2023-05-01 a 2023-06-01

3. **...continuar hasta cubrir todo el año**

### Métricas:

- ✅ **Sharpe Promedio:** Promedio de Sharpe en todas las ventanas
- ✅ **Consistencia:** Desviación estándar de Sharpe (menor = más consistente)
- ✅ **Estabilidad PnL:** Coeficiente de variación de PnL mensual
- ✅ **Drawdown Máximo:** Mayor drawdown observado en cualquier ventana

### Script:

```bash
python scripts/run_walkforward_backtest.py \
    --symbol AAPL \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --train-window-months 3 \
    --test-window-months 1 \
    --step-months 1 \
    --output-dir docs/BACKTEST_RESULTS/walkforward
```

### Archivos:

- `walkforward_results_{symbol}_{timestamp}.csv` - Resultados por ventana
- `walkforward_consistency_report_{symbol}_{timestamp}.md` - Análisis de consistencia
- `walkforward_equity_curves_{symbol}_{timestamp}.html` - Curvas de equity por ventana

---

## 7️⃣ Stress / Scenario Testing

**Objetivo:** Evaluar resiliencia en mercados extremos.

### Escenarios:

#### 7.1 Alta Volatilidad (Market Crash)

- **Período:** Marzo 2020 (COVID crash)
- **Indicadores:** VIX > 30, caídas > 5% diarias
- **Objetivo:** Verificar drawdown controlado y recuperación

#### 7.2 Rally Alcista Extremo

- **Período:** Noviembre 2020 - Enero 2021
- **Características:** Subidas sostenidas > 2% diarias
- **Objetivo:** Verificar no sobre-exposición y take-profit efectivo

#### 7.3 Mercado Lateral (Choppy)

- **Período:** Mayo-Julio 2023 (rango estrecho)
- **Características:** Volatilidad baja, sin tendencia clara
- **Objetivo:** Verificar que filtros detecten y eviten trades en rango

#### 7.4 Flash Crash / Gap Events

- **Eventos específicos:** Gaps > 5%, flash crashes
- **Objetivo:** Verificar ejecución con slippage controlado

### Métricas:

- ✅ **Max Drawdown:** Durante evento extremo
- ✅ **Recovery Time:** Días para recuperar pérdidas
- ✅ **Consecutive Losses:** Número máximo de trades perdedores consecutivos
- ✅ **Slippage Impact:** Impacto de slippage en PnL durante eventos

### Script:

```bash
python scripts/run_stress_backtest.py \
    --scenario market_crash \
    --symbol SPY \
    --start-date 2020-02-01 \
    --end-date 2020-04-30 \
    --output-dir docs/BACKTEST_RESULTS/stress
```

### Archivos:

- `stress_{scenario}_{symbol}_{timestamp}.json` - Resultados del escenario
- `stress_comparison_report_{timestamp}.md` - Comparación de todos los escenarios

---

## 📊 Reporte Final Consolidado

### Generación:

```bash
python scripts/generate_final_backtest_report.py \
    --results-dir docs/BACKTEST_RESULTS \
    --output docs/BACKTEST_RESULTS/FINAL_REPORT.md
```

### Contenido:

1. **Resumen Ejecutivo**

   - Mejor configuración encontrada
   - Métricas clave consolidadas
   - Recomendaciones de producción

2. **Comparación de Tests**

   - Tabla comparativa de todos los tests
   - Visualizaciones de performance

3. **Análisis de Robustez**

   - Consistencia temporal (walk-forward)
   - Resiliencia (stress tests)
   - Parámetros críticos identificados

4. **Recomendaciones**
   - Configuración recomendada para producción
   - Parámetros que deben monitorearse
   - Red flags identificados

---

## 🚀 Ejecución Completa (All-in-One)

Para ejecutar TODOS los backtests automáticamente:

```bash
python scripts/run_complete_backtest_suite.py \
    --symbol AAPL \
    --start-date 2023-01-01 \
    --end-date 2024-01-01 \
    --include baseline,ablation,optimization,ml,combined,walkforward,stress \
    --parallel-workers 4 \
    --output-dir docs/BACKTEST_RESULTS/complete_suite_{timestamp}
```

**Tiempo estimado:** 6-12 horas (depende de hardware y número de iteraciones)

---

## 📁 Estructura de Resultados

```
docs/BACKTEST_RESULTS/
├── baseline/
│   ├── baseline_results_AAPL_20240101.json
│   └── baseline_equity_curve_AAPL_20240101.csv
├── ablation/
│   ├── ablation_report_AAPL_20240101.csv
│   └── ablation_summary_AAPL_20240101.md
├── optimization/
│   ├── best_config_AAPLoplasm_20240101.json
│   └── optimization_report_AAPL_20240101.csv
├── ml_supervised/
│   ├── ml_results_RandomForest_AAPL_20240101.json
│   └── ml_feature_importance_AAPL_20240101.html
├── ml_deep/
│   ├── ml_results_LSTM_AAPL_20240101.json
│   └── ml_training_curves_AAPL_20240101.html
├── ml_rl/
│   └── ml_results_PPO_AAPL_20240101.json
├── combined/
│   └── combined_final_config_AAPL_20240101.json
├── walkforward/
│   └── walkforward_consistency_report_AAPL_20240101.md
├── stress/
│   ├── stress_market_crash_SPY_20240101.json
│   └── stress_comparison_20240101.md
└── FINAL_REPORT.md
```

---

## ✅ Checklist de Implementación

- [ ] Script 1: `run_baseline_backtest.py`
- [ ] Script 2: `run_ablation_backtest.py`
- [ ] Script 3: `run_hyperparameter_optimization.py` (✅ Ya existe)
- [ ] Script 4: `run_ml_backtest.py`
- [ ] Script 5: `run_combined_optimization.py`
- [ ] Script 6: `run_walkforward_backtest.py`
- [ ] Script 7: `run_stress_backtest.py`
- [ ] Script 8: `generate_final_backtest_report.py`
- [ ] Script 9: `run_complete_backtest_suite.py` (orquestador)

---

**🎯 Este plan asegura una validación completa y robusta de la estrategia antes de producción.**
