# Backtesting Scripts

Scripts para ejecutar diferentes tipos de backtesting en el sistema de trading algorítmico.

## Estructura de Directorios

```
scripts/backtesting/
├── README.md                           # Este archivo
├── simple/                             # Backtests sin optimización
│   ├── run_simple_backtest.py          # Backtest básico de verificación
│   ├── run_baseline_backtest.py        # Backtest base sin ML/optimización
│   ├── run_deep_learning_backtest.py   # Prueba de Deep Learning (RNN, LSTM, GRU)
│   ├── run_transformer_backtest.py     # Prueba de arquitectura Transformer
│   ├── run_automated_momentum_backtest.py  # Backtest automatizado de momentum
│   ├── run_comprehensive_regime_backtest.py # Backtest con selector de régimen
│   ├── run_profile_regime_backtest.py  # Backtest con perfiles y regímenes
│   ├── run_regime_selector_backtest.py # Backtest con selector adaptativo
│   └── run_progressive_backtest.py     # Tests progresivos de simple a complejo
└── optimization/                       # Backtests con optimización
    ├── run_comprehensive_backtest.py   # Pipeline completo con múltiples optimizaciones
    ├── run_profile_batch_backtester.py # Batch con Bayesian optimization
    ├── run_profile_driven_trading.py   # Trading basado en perfiles
    ├── run_backtesting_with_real_data.py # Con datos reales de Alpha Vantage
    ├── run_multi_symbol_backtest.py    # Multi-símbolo con optimización
    ├── run_all_backtests.py            # Ejecuta todas las estrategias
    ├── run_full_compliance_test.py     # Suite completa de 10 tipos de backtest
    └── run_backtest.py                 # Runner genérico con ajuste de parámetros
```

---

## Simple Backtests (sin optimización)

Scripts para pruebas rápidas sin optimización de parámetros.

### `simple/run_simple_backtest.py`
Backtest básico para verificar que todo funciona correctamente.

```bash
python scripts/backtesting/simple/run_simple_backtest.py
```

### `simple/run_baseline_backtest.py`
Ejecuta un backtest base sin optimización ML ni módulos adicionales.

```bash
python scripts/backtesting/simple/run_baseline_backtest.py --symbol AAPL
```

### `simple/run_deep_learning_backtest.py`
Ejecuta backtesting con modelos de deep learning (RNN, LSTM, GRU).

```bash
python scripts/backtesting/simple/run_deep_learning_backtest.py
```

### `simple/run_transformer_backtest.py`
Ejecuta backtesting con arquitectura Transformer.

```bash
python scripts/backtesting/simple/run_transformer_backtest.py
```

### `simple/run_automated_momentum_backtest.py`
Ejecuta backtesting automatizado específico para estrategia de momentum.

```bash
python scripts/backtesting/simple/run_automated_momentum_backtest.py
```

### `simple/run_progressive_backtest.py`
Tests progresivos de simple a complejo (5 niveles).

```bash
# Ejecutar todos los niveles
python scripts/backtesting/simple/run_progressive_backtest.py

# Ejecutar nivel específico
python scripts/backtesting/simple/run_progressive_backtest.py --level 3

# Modo rápido
python scripts/backtesting/simple/run_progressive_backtest.py --quick
```

---

## Optimization Backtests (con optimización)

Scripts que incluyen optimización de parámetros.

### `optimization/run_comprehensive_backtest.py` ⭐ PRINCIPAL
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
python scripts/backtesting/optimization/run_comprehensive_backtest.py

# Ejecutar backtests específicos
python scripts/backtesting/optimization/run_comprehensive_backtest.py baseline ablation grid_search
```

### `optimization/run_profile_batch_backtester.py`
Ejecuta batch de 180 perfiles con Bayesian optimization.

```bash
# Run all 180 profiles (parallel)
python scripts/backtesting/optimization/run_profile_batch_backtester.py --all --parallel

# Run a single profile
python scripts/backtesting/optimization/run_profile_batch_backtester.py --single --objective maximizar_capital --risk medio

# Generate comparison report only
python scripts/backtesting/optimization/run_profile_batch_backtester.py --report

# Get best strategy
python scripts/backtesting/optimization/run_profile_batch_backtester.py --best --objective maximizar_capital --risk medio --tier medio
```

### `optimization/run_multi_symbol_backtest.py`
Ejecuta backtesting para múltiples símbolos con optimización.

```bash
python scripts/backtesting/optimization/run_multi_symbol_backtest.py
```

### `optimization/run_all_backtests.py`
Ejecuta backtesting de todas las estrategias disponibles.

```bash
python scripts/backtesting/optimization/run_all_backtests.py
```

### `optimization/run_full_compliance_test.py`
Suite completa de 10 tipos de backtest con compliance total.

```bash
python scripts/backtesting/optimization/run_full_compliance_test.py
```

### `optimization/run_profile_driven_trading.py`
CLI para el algoritmo de trading basado en perfiles.

```bash
# Run with default parameters (dry-run mode)
python scripts/backtesting/optimization/run_profile_driven_trading.py run

# Run with custom parameters
python scripts/backtesting/optimization/run_profile_driven_trading.py run --capital 50000 --objective maximizar_capital --risk medio
```

### `optimization/run_backtesting_with_real_data.py`
Backtesting con datos reales de Alpha Vantage.

```bash
# Run with default parameters
python scripts/backtesting/optimization/run_backtesting_with_real_data.py run

# Run with custom parameters
python scripts/backtesting/optimization/run_backtesting_with_real_data.py run --capital 50000 --symbols 20 --days 180
```

---

## Configuración

La mayoría de los scripts leen su configuración desde:
- `config/backtesting/comprehensive_backtest.yaml` - Configuración principal
- `config/trading_strategies.yaml` - Configuración de estrategias

## Resultados

Los resultados se guardan en:
- `docs/BACKTEST_RESULTS/` - Resultados principales
- `reports/backtesting/` - Reportes JSON
- `results/` - Resultados adicionales
- `results/profile_batch_backtesting/` - Resultados de batch optimization

## Requisitos Previos

1. Datos históricos descargados en `data/historical/`
2. Configuración YAML válida en `config/backtesting/`
3. Dependencias instaladas (ver `requirements.txt`)

## Notas

- Todos los scripts están configurados para manejar threading correctamente
- Los scripts utilizan `AggressiveMemoryManager` para manejo eficiente de memoria
- Los resultados incluyen métricas: Sharpe Ratio, Win Rate, Max Drawdown, Total P&L

## Solución de Problemas

Si obtienes errores de importación:
```bash
# Asegúrate de estar en la raíz del proyecto
cd /Users/kepa.cantero/Projects/algoTrading

# Ejecuta con la ruta correcta
python scripts/backtesting/simple/run_simple_backtest.py
```

## Documentación Relacionada

- `app/backtesting/README.md` - Documentación del módulo de backtesting
- `config/backtesting/comprehensive_backtest.yaml` - Configuración ejemplo
