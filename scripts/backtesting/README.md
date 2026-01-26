# Backtesting Scripts

Scripts para ejecutar diferentes tipos de backtesting en el sistema de trading algorítmico.

## 📋 Scripts Disponibles

### 1. `run_comprehensive_backtest.py` ⭐ PRINCIPAL
Ejecuta un pipeline completo de backtesting con múltiples tipos de tests.

**Tipos de backtests soportados:**
- `baseline` - Línea base con todos los módulos activos
- `learning_engines` - Prueba cada learning engine individualmente
- `walk_forward` - Optimización por ventana temporal
- `monte_carlo` - Stress test con simulaciones aleatorias
- `transformer_optimization` - Optimización iterativa con Transformer
- `ablation` - Impacto individual de cada módulo
- `grid_search` - Búsqueda de parámetros óptimos
- `out_of_sample` - Validación forward
- `regime_test` - Desempeño por régimen de mercado

**Uso:**
```bash
# Ejecutar todos los backtests habilitados en la configuración
python scripts/backtesting/run_comprehensive_backtest.py

# Ejecutar backtests específicos
python scripts/backtesting/run_comprehensive_backtest.py baseline ablation grid_search

# Usar configuración personalizada
python scripts/backtesting/run_comprehensive_backtest.py --config config/backtesting/custom.yaml
```

### 2. `run_all_backtests.py`
Ejecuta backtesting de todas las estrategias disponibles generando resultados detallados, métricas, logs, gráficos y documentación.

**Uso:**
```bash
python scripts/backtesting/run_all_backtests.py
```

### 3. `run_baseline_backtest.py`
Ejecuta un backtest base sin optimización ML ni módulos adicionales.

**Uso:**
```bash
python scripts/backtesting/run_baseline_backtest.py --symbol AAPL
```

### 4. `run_multi_symbol_backtest.py`
Ejecuta backtesting para múltiples símbolos simultáneamente.

**Uso:**
```bash
python scripts/backtesting/run_multi_symbol_backtest.py
```

### 5. `run_deep_learning_backtest.py`
Ejecuta backtesting con modelos de deep learning (RNN, LSTM, GRU).

**Uso:**
```bash
python scripts/backtesting/run_deep_learning_backtest.py
```

### 6. `run_transformer_backtest.py`
Ejecuta backtesting con arquitectura Transformer para optimización.

**Uso:**
```bash
python scripts/backtesting/run_transformer_backtest.py
```

### 7. `run_automated_momentum_backtest.py`
Ejecuta backtesting automatizado específico para estrategia de momentum.

**Uso:**
```bash
python scripts/backtesting/run_automated_momentum_backtest.py
```

## ⚙️ Configuración

La mayoría de los scripts leen su configuración desde:
- `config/backtesting/comprehensive_backtest.yaml` - Configuración principal
- `config/trading_strategies.yaml` - Configuración de estrategias

## 📁 Estructura de Directorios

```
scripts/backtesting/
├── README.md                                    # Este archivo
├── run_comprehensive_backtest.py               # Script principal
├── run_all_backtests.py                         # Todas las estrategias
├── run_baseline_backtest.py                    # Backtest base
├── run_multi_symbol_backtest.py                # Multi-símbolo
├── run_deep_learning_backtest.py               # Deep Learning
├── run_transformer_backtest.py                 # Transformer
└── run_automated_momentum_backtest.py          # Momentum automatizado
```

## 📊 Resultados

Los resultados se guardan en:
- `docs/BACKTEST_RESULTS/` - Resultados principales
- `reports/backtesting/` - Reportes JSON
- `results/` - Resultados adicionales

## 🔧 Requisitos Previos

1. Datos históricos descargados en `data/historical/`
2. Configuración YAML válida en `config/backtesting/`
3. Dependencias instaladas (ver `requirements.txt`)

## ⚡ Ejecución Rápida

```bash
# Desde la raíz del proyecto
python scripts/backtesting/run_comprehensive_backtest.py baseline
```

## 📝 Notas

- Todos los scripts están configurados para manejar threading correctamente
- Los scripts utilizan `AggressiveMemoryManager` para manejo eficiente de memoria
- Los resultados incluyen métricas: Sharpe Ratio, Win Rate, Max Drawdown, Total P&L

## 🐛 Solución de Problemas

Si obtienes errores de importación:
```bash
# Asegúrate de estar en la raíz del proyecto
cd /Users/kepa.cantero/Projects/algoTrading

# Ejecuta con la ruta correcta
python scripts/backtesting/run_comprehensive_backtest.py
```

## 📚 Documentación Relacionada

- `app/backtesting/comprehensive_backtest_runner.py` - Implementación principal
- `app/backtesting/README.md` - Documentación del módulo de backtesting
- `config/backtesting/comprehensive_backtest.yaml` - Configuración ejemplo
