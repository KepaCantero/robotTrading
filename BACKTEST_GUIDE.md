# Guía Completa: Backtesting en algoTrading

**Documento**: Guía de uso para backtests y visualizaciones
**Versión**: 1.0
**Última actualización**: 2025-12-27
**Autor**: Plan Maestro

---

## 📋 Índice

1. [Introducción](#introducción)
2. [Script Principal: run_backtest.py](#script-principal-run_backtestpy)
3. [Los 5 Objetivos de Inversión](#los-5-objetivos-de-inversión)
4. [Los 4 Capital Tiers](#los-4-capital-tiers)
5. [Cómo Usar los Backtests](#cómo-usar-los-backtests)
6. [Los 10 Tipos de Backtests](#los-10-tipos-de-backtests)
7. [Visualizaciones Disponibles](#visualizaciones-disponibles)
8. [Ejemplos Prácticos](#ejemplos-prácticos)
9. [Interpretar Resultados](#interpretar-resultados)
10. [API REST para Backtests](#api-rest-para-backtests)

---

## Introducción

El sistema de backtesting de algoTrading permite validar estrategias de inversión con **5 objetivos distintos** adaptados a **4 niveles de capital** diferentes. El script principal es `run_backtest.py`, que orquesta todo el proceso de backtesting y proporciona múltiples visualizaciones.

### Características Principales:

✅ **5 Objetivos de Inversión**: Cada uno optimizado para diferentes perfiles de inversor
✅ **4 Capital Tiers**: Micro, Small, Medium, Large (€1k - €10M)
✅ **10 Tipos de Backtests**: Desde baseline hasta stress testing avanzado
✅ **Visualizaciones Interactivas**: Plotly, matplotlib, NetworkX
✅ **Metrics Avanzadas**: Sharpe ratio, Calmar ratio, Value at Risk, etc.
✅ **API REST**: Acceso programático a todos los backtests

---

## Script Principal: `run_backtest.py`

### Ubicación
```
/Users/kepa.cantero/Projects/algoTrading/run_backtest.py
```

### Parámetros Principales

```python
INITIAL_CAPITAL = Decimal("100000")  # Capital inicial en EUR
STRATEGY_NAME = "momentum"            # Nombre de la estrategia
```

### Cómo Ejecutar Desde Terminal

#### Opción 1: Ejecución Directa (valores por defecto)
```bash
cd /Users/kepa.cantero/Projects/algoTrading
python run_backtest.py
```

Esto ejecutará un backtest con:
- Capital inicial: €100,000
- Estrategia: momentum
- Objetivo: maximizar_capital (por defecto)

#### Opción 2: Con Parámetros Personalizados

Editar directamente el archivo antes de ejecutar:

```python
# En run_backtest.py, líneas iniciales:
INITIAL_CAPITAL = Decimal("500000")      # Tu capital
STRATEGY_NAME = "mean_reversion"          # Tu estrategia
INVESTMENT_OBJECTIVE = "balanced_growth"  # Tu objetivo
```

Luego ejecutar:
```bash
python run_backtest.py
```

#### Opción 3: Desde Script Python
```python
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
from app.models.investment_profile import InvestmentProfile, CapitalTier

# Crear perfil de inversión
profile = InvestmentProfile(
    capital_initial=Decimal("250000"),
    capital_tier=CapitalTier.LARGE,
    objetivo_inversion="maximizar_capital",
    risk_tolerance="medio"
)

# Ejecutar backtest
runner = ComprehensiveBacktestRunner()
results = runner.run_comprehensive_backtest(
    profile=profile,
    strategy_name="momentum",
    backtest_types=["baseline", "walk_forward"]  # Especificar tipos
)

# Visualizar
runner.visualize_results(results)
```

---

## Los 5 Objetivos de Inversión

Cada objetivo está diseñado para un tipo diferente de inversor y optimiza métricas distintas.

### 1. 📈 MAXIMIZAR_CAPITAL - "Capital Growth"

**Perfil**: Para inversores agresivos buscando máximo retorno

**Características**:
- Enfoque en máximo rendimiento total (total return)
- Leverage hasta 2.5x para cuentas grandes
- Aceptación de volatilidad moderada-alta
- Horizonte: 1-3 años

**Métricas Clave Optimizadas**:
- Sharpe ratio (retorno ajustado por riesgo)
- Total return %
- CAGR (Compound Annual Growth Rate)

**Módulos Activados**:
- Momentum Strategies (principal)
- Mean Reversion (secundario)
- Machine Learning (avanzado)
- Risk Scaling (máximo 2.5x)

**Restricciones**:
- Max drawdown permitido: 30%
- Max concentración sector: 40%
- Max posición individual: 20% del capital

**Ejemplo de Configuración**:
```yaml
objetivo: maximizar_capital
capital_inicial: 250000
risk_tolerance: alto
leverage_factor: 2.0
modules:
  momentum: enabled
  mean_reversion: enabled
  ml_models: enabled
  risk_scaling: enabled
```

---

### 2. 💰 MAXIMIZAR_DIVIDENDOS - "Dividend Income"

**Perfil**: Para inversores buscando ingresos pasivos recurrentes

**Características**:
- Enfoque en rendimiento por dividendos (dividend yield)
- Bajo movimiento de capital (buy & hold)
- Ingresos mensuales/trimestrales consistentes
- Horizonte: 3-10 años

**Métricas Clave Optimizadas**:
- Dividend yield %
- Income consistency (Sortino ratio)
- Capital preservation
- Volatility

**Módulos Activados**:
- Dividend Screener
- Dividend Predictor
- Income Generator (covered calls)
- Conservative Risk Scaling

**Restricciones**:
- Max drawdown permitido: 15%
- Min dividend yield: 3%
- Min credit rating: BBB
- Max sector allocation: 25%

**Ejemplo de Configuración**:
```yaml
objetivo: maximizar_dividendos
capital_inicial: 500000
risk_tolerance: bajo
leverage_factor: 0.5
modules:
  dividend_screener: enabled
  dividend_predictor: enabled
  income_generator: enabled
  risk_scaling: conservative
```

---

### 3. 🛡️ CAPITAL_PRESERVATION - "Protect Capital"

**Perfil**: Para inversores conservadores priorizando seguridad

**Características**:
- Objetivo: Minimizar pérdidas (capital preservation)
- Baja volatilidad y retornos consistentes
- Protección contra caídas de mercado
- Horizonte: 5-10+ años

**Métricas Clave Optimizadas**:
- Max drawdown (minimizar)
- Calmar ratio (retorno / max drawdown)
- Volatility (minimizar)
- Win rate

**Módulos Activados**:
- Defensive Momentum
- Hedge Strategies
- Volatility Management
- Drawdown Control (límite duro en 10%)

**Restricciones**:
- Max drawdown: 10% (límite duro)
- Max leverage: 0.5x
- Min allocation stocks: 30%
- Max allocation stocks: 60%
- Hedging obligatorio en volatilidad alta

**Ejemplo de Configuración**:
```yaml
objetivo: capital_preservation
capital_inicial: 1000000
risk_tolerance: bajo
leverage_factor: 0.3
modules:
  defensive_momentum: enabled
  hedge_strategies: enabled
  volatility_control: enabled
  drawdown_control: enabled
max_drawdown: 10%
```

---

### 4. ⚖️ BALANCED_GROWTH - "Balance Risk & Return"

**Perfil**: Para inversores moderados buscando balance

**Características**:
- Balance entre retorno y riesgo
- Volatilidad moderada
- Retornos consistentes
- Horizonte: 3-5 años

**Métricas Clave Optimizadas**:
- Sharpe ratio (balance principal)
- Max drawdown (moderado ~15%)
- Total return
- Consistency

**Módulos Activados**:
- Momentum Strategies (60%)
- Mean Reversion (40%)
- Machine Learning
- Balanced Risk Scaling (máximo 1.5x)

**Restricciones**:
- Max drawdown permitido: 15%
- Max leverage: 1.5x
- Min / Max allocation stocks: 40% / 70%
- Sector diversification requerida

**Ejemplo de Configuración**:
```yaml
objetivo: balanced_growth
capital_inicial: 250000
risk_tolerance: medio
leverage_factor: 1.3
modules:
  momentum: enabled
  mean_reversion: enabled
  ml_models: enabled
  risk_scaling: moderate
max_drawdown: 15%
```

---

### 5. 💵 INCOME_GENERATION - "Steady Income Stream"

**Perfil**: Para inversores buscando ingresos frecuentes y predecibles

**Características**:
- Generación de ingresos mensuales/trimestrales
- Combinación de dividendos + opciones (covered calls, puts)
- Baja volatilidad, retornos predecibles
- Horizonte: 5-10 años

**Métricas Clave Optimizadas**:
- Monthly income / capital ratio
- Income consistency
- Income predictability
- Capital preservation

**Módulos Activados**:
- Dividend Collector
- Covered Call Writer
- Put Seller (conservador)
- Collar Strategies
- Income Risk Management

**Restricciones**:
- Max drawdown permitido: 12%
- Max leverage: 0.5x
- Min monthly income: 0.3% of capital
- Max delta (options): 0.3
- Sector limits: 20% máximo

**Ejemplo de Configuración**:
```yaml
objetivo: income_generation
capital_inicial: 500000
risk_tolerance: bajo-medio
leverage_factor: 0.4
modules:
  dividend_collector: enabled
  covered_call_writer: enabled
  put_seller: enabled
  collar_strategies: enabled
  income_risk_mgmt: enabled
min_monthly_income: 0.003
```

---

## Los 4 Capital Tiers

El sistema automáticamente ajusta la estrategia según el capital inicial:

### 1. 🔹 MICRO: < €15,000

**Características**:
- Comisiones porcentuales impactan más
- Posiciones pequeñas, slippage mayor
- Menos opciones de ejecución (sin smart order routing)
- Liquidez limitada en algunos activos

**Restricciones Automáticas**:
- Max posición: 2-5% del capital
- Min posición: €100-500
- Max sector: 20%
- Leverage: 0.5-1.0x máximo
- Sin opciones complejas

**Estrategias Recomendadas**:
- Momentum simple
- ETF largo plazo
- Dividendo pasivo

---

### 2. 🟡 SMALL: €15,000 - €50,000

**Características**:
- Comisiones flat se vuelven significativas
- Posiciones medianas
- Acceso a smart order routing
- Opciones básicas disponibles

**Restricciones Automáticas**:
- Max posición: 5-10% del capital
- Min posición: €500-1,000
- Max sector: 25%
- Leverage: 1.0-1.5x máximo
- Opciones básicas permitidas

**Estrategias Recomendadas**:
- Momentum/Mean Reversion
- Covered calls básicas
- Pairs trading
- Multi-estrategia

---

### 3. 🟠 MEDIUM: €50,000 - €250,000

**Características**:
- Negociación profesional posible
- Comisiones reducidas
- Slippage mínimo
- Acceso a todas las estrategias

**Restricciones Automáticas**:
- Max posición: 8-15% del capital
- Min posición: €1,000-5,000
- Max sector: 30%
- Leverage: 1.0-2.0x máximo
- Todas las opciones permitidas
- Stress testing recomendado

**Estrategias Recomendadas**:
- Todas las estrategias soportadas
- Advanced ML models
- Complex options strategies
- Portfolio optimization

---

### 4. 🟢 LARGE: >= €250,000

**Características**:
- Mejor ejecución de mercado
- Comisiones mínimas
- Relación directa con brokers
- Máxima flexibilidad

**Restricciones Automáticas**:
- Max posición: 10-20% del capital
- Min posición: €5,000-20,000
- Max sector: 35%
- Leverage: 1.5-2.5x máximo
- Todas las estrategias
- Market impact analysis obligatorio

**Estrategias Recomendadas**:
- Todas sin restricciones
- Algorithmic execution
- Multi-asset portfolios
- Hedge fund strategies

---

## Cómo Usar los Backtests

### Paso 1: Preparar Datos de Mercado

Los backtests necesitan datos de OHLCV (Open, High, Low, Close, Volume).

```bash
# Descargar datos históricos
python -c "
from app.services.data_service import DataService
import asyncio

async def download():
    service = DataService()
    await service.download_historical_data(
        symbols=['AAPL', 'MSFT', 'GOOGL'],
        start_date='2020-01-01',
        end_date='2025-12-27'
    )

asyncio.run(download())
"
```

### Paso 2: Definir Perfil de Inversión

```python
from app.core.models.investment_profile import InvestmentProfile, CapitalTier

profile = InvestmentProfile(
    # Parámetros básicos
    capital_initial=Decimal("250000"),     # Tu capital inicial
    capital_tier=CapitalTier.LARGE,        # Automático basado en capital
    objetivo_inversion="maximizar_capital", # O uno de los otros 4
    risk_tolerance="medio",                # bajo, medio, alto
    investment_horizon=24,                 # Meses

    # Parámetros opcionales
    min_annual_return=Decimal("12"),       # Target retorno %
    max_annual_volatility=Decimal("20"),   # Target volatilidad %
    max_drawdown=Decimal("20"),            # Máximo drawdown %
)
```

### Paso 3: Ejecutar Backtest Básico

```python
from app.services.backtesting_orchestration.backtest_orchestrator import BacktestOrchestrator

orchestrator = BacktestOrchestrator()

result = orchestrator.run_backtest(
    profile=profile,
    strategy_name="momentum",
    start_date="2023-01-01",
    end_date="2025-12-27"
)

print(f"Sharpe Ratio: {result.sharpe_ratio}")
print(f"Total Return: {result.total_return}%")
print(f"Max Drawdown: {result.max_drawdown}%")
print(f"Win Rate: {result.win_rate}%")
```

### Paso 4: Ejecutar Backtests Múltiples

```python
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner

runner = ComprehensiveBacktestRunner()

# Todos los 10 tipos
results = runner.run_comprehensive_backtest(
    profile=profile,
    strategy_name="momentum",
    backtest_types=[
        "baseline",
        "walk_forward",
        "monte_carlo",
        "ablation"
    ]
)

# Analizar resultados
for backtest_type, result in results.items():
    print(f"\n{backtest_type.upper()}:")
    print(f"  Return: {result.total_return}%")
    print(f"  Sharpe: {result.sharpe_ratio}")
    print(f"  Drawdown: {result.max_drawdown}%")
```

### Paso 5: Guardar y Exportar Resultados

```python
import json
from datetime import datetime

# Guardar en JSON
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"docs/BACKTEST_RESULTS/backtest_{timestamp}.json"

with open(filename, 'w') as f:
    json.dump(results.dict(), f, indent=2, default=str)

# También disponible: CSV, Excel, HTML
runner.export_to_csv(results, f"backtest_{timestamp}.csv")
runner.export_to_excel(results, f"backtest_{timestamp}.xlsx")
runner.export_to_html(results, f"backtest_{timestamp}.html")
```

---

## Los 10 Tipos de Backtests

El `ComprehensiveBacktestRunner` ejecuta estos 10 tipos de backtests:

### 1️⃣ BASELINE - Test Simple

**Qué es**: Ejecución directa de la estrategia con parámetros por defecto

**Cuándo usarlo**:
- Evaluación inicial rápida
- Establecer métrica de referencia
- Prueba de concepto

**Parámetros**:
```python
backtest_types=["baseline"]
```

**Salida**:
- Total return, Sharpe ratio, Max drawdown
- Trade statistics (total trades, win rate)
- Basic visualizations

**Ejemplo de Resultado**:
```
Baseline Performance:
- Total Return: 45.32%
- Sharpe Ratio: 1.82
- Max Drawdown: 12.5%
- Total Trades: 127
- Win Rate: 58%
- Profit Factor: 2.1
```

---

### 2️⃣ LEARNING_ENGINES - Individual Module Testing

**Qué es**: Prueba cada módulo de aprendizaje por separado

**Cuándo usarlo**:
- Entender qué módulos funcionan mejor
- Identificar módulos que perjudican la estrategia
- Debugging de módulos específicos

**Módulos Probados**:
- Momentum Learner
- Mean Reversion Learner
- Pattern Recognizer
- Anomaly Detector
- ML Models

**Parámetros**:
```python
backtest_types=["learning_engines"]
```

**Salida por módulo**:
```
Momentum Learner:
  - Return: 38.2%, Sharpe: 1.65, Drawdown: 15%
  - Contribution: 25% of total return

Mean Reversion Learner:
  - Return: 12.5%, Sharpe: 0.95, Drawdown: 8%
  - Contribution: 8% of total return

ML Models:
  - Return: 18.7%, Sharpe: 1.42, Drawdown: 10%
  - Contribution: 12% of total return
```

---

### 3️⃣ WALK_FORWARD - Temporal Window Optimization

**Qué es**: Divide el tiempo en ventanas, entrena en una y prueba en siguiente

**Cuándo usarlo**:
- Validar que la estrategia se generaliza en el tiempo
- Detectar overfitting temporal
- Verificar robustez en diferentes períodos

**Método**:
```
Periodo 1:     Entrena [2020-2021] → Prueba [2021-2022]
Periodo 2:     Entrena [2021-2022] → Prueba [2022-2023]
Periodo 3:     Entrena [2022-2023] → Prueba [2023-2024]
Resultado:     Promedio de los 3 períodos
```

**Parámetros**:
```python
backtest_types=["walk_forward"]
# Parámetros internos:
training_window=252*2  # 2 años
testing_window=252     # 1 año
```

**Salida**:
```
Walk-Forward Performance:
- Average Return: 42.1%
- Std Dev: 8.3%
- Out-of-Sample Sharpe: 1.71
- Consistency: 87% (períodos rentables)

Detalles por período:
  Period 1 (2020-2022): Return 48%, Sharpe 1.8
  Period 2 (2021-2023): Return 35%, Sharpe 1.5
  Period 3 (2022-2024): Return 43%, Sharpe 1.8
```

---

### 4️⃣ MONTE_CARLO - Stress Testing Probabilístico

**Qué es**: Simula miles de escenarios de mercado alternativos

**Cuándo usarlo**:
- Entender riesgo de cola (tail risk)
- Evaluar resiliencia ante crashes
- Calcular Value at Risk (VaR)
- Stress testing de eventos extremos

**Método**:
```
Toma los retornos históricos
Genera 10,000 secuencias aleatorias
Calcula estadísticas en el peor 5% de casos
```

**Parámetros**:
```python
backtest_types=["monte_carlo"]
# Internos:
num_simulations=10000
percentiles=[5, 25, 50, 75, 95]
```

**Salida**:
```
Monte Carlo Analysis (10,000 simulations):

Percentile Analysis:
  5th percentile (worst 5%):  -25.3% (Value at Risk)
  25th percentile:            -8.5%
  Median (50th):              +42.1%
  75th percentile:            +78.3%
  95th percentile (best 5%):  +118.2%

Risk Metrics:
  Conditional VaR (95%):      -28.5%
  Probability of Loss:        12%
  Probability of >50% gain:   28%
  Max Loss in simulation:      -42.3%
```

---

### 5️⃣ TRANSFORMER_OPTIMIZATION - Optimización Iterativa

**Qué es**: Optimiza parámetros usando algoritmo genético/Bayesian

**Cuándo usarlo**:
- Encontrar mejores parámetros
- Fine-tuning de estrategia
- Preparar para live trading

**Método**:
```
Generación 1: Prueba 50 sets de parámetros aleatorios
Generación 2: Cría los 10 mejores + mutaciones
Generación 3: Itera hasta convergencia
```

**Parámetros**:
```python
backtest_types=["transformer_optimization"]
# Internos:
population_size=50
generations=20
mutation_rate=0.1
```

**Salida**:
```
Optimized Parameters:
  Best Return: 52.3% (vs baseline 45.3%)
  Best Sharpe: 1.95 (vs baseline 1.82)
  Best Calmar: 4.18 (vs baseline 3.62)

Optimal Parameter Set:
  momentum_period: 18 days (vs default 20)
  mean_reversion_threshold: 1.85 std (vs default 2.0)
  position_size_pct: 3.2% (vs default 3.0%)
  stop_loss: 4.8% (vs default 5.0%)
  take_profit: 8.2% (vs default 8.0%)

Warning: Verify out-of-sample performance!
```

---

### 6️⃣ ABLATION - Análisis de Impacto de Módulos

**Qué es**: Ejecuta la estrategia sin cada módulo para medir su contribución

**Cuándo usarlo**:
- Identificar módulos críticos
- Eliminar módulos que dañan retornos
- Optimizar arquitectura
- Reducir latencia eliminando módulos innecesarios

**Método**:
```
Baseline (todos):        Return 45.3%
Sin Momentum:            Return 42.1% → Contribución: 3.2%
Sin Mean Reversion:      Return 44.8% → Contribución: 0.5%
Sin Risk Scaling:        Return 38.2% → Contribución: 7.1%
Sin Machine Learning:    Return 40.5% → Contribución: 4.8%
```

**Parámetros**:
```python
backtest_types=["ablation"]
```

**Salida**:
```
Ablation Analysis - Module Contribution:

┌─────────────────────────┬──────────┬────────────┬───────────┐
│ Module Removed          │ Return   │ Change     │ Impact    │
├─────────────────────────┼──────────┼────────────┼───────────┤
│ Baseline (all)          │ 45.3%    │ -          │ -         │
│ - Momentum Learner      │ 42.1%    │ -3.2%      │ CRITICAL  │
│ - Mean Reversion        │ 44.8%    │ -0.5%      │ MINIMAL   │
│ - Risk Scaling          │ 38.2%    │ -7.1%      │ CRITICAL  │
│ - ML Models             │ 40.5%    │ -4.8%      │ IMPORTANT │
│ - Volatility Monitor    │ 43.2%    │ -2.1%      │ USEFUL    │
└─────────────────────────┴──────────┴────────────┴───────────┘

Recommendation:
✅ Keep: Momentum, Risk Scaling, ML Models (critical)
⚠️ Evaluate: Volatility Monitor (marginal benefit)
❌ Remove: Mean Reversion (minimal impact, adds latency)
```

---

### 7️⃣ GRID_SEARCH - Optimización Exhaustiva

**Qué es**: Prueba todas las combinaciones de parámetros en una malla

**Cuándo usarlo**:
- Búsqueda exhaustiva de mejores parámetros
- Entiender sensibilidad a parámetros
- Encontrar regiones óptimas en espacio de parámetros

**Método**:
```
Parámetro 1: momentum_period = [10, 15, 20, 25, 30]
Parámetro 2: threshold = [1.5, 1.75, 2.0, 2.25, 2.5]
Parámetro 3: position_size = [2%, 3%, 4%, 5%]

Total combinaciones: 5 × 5 × 4 = 100 backtests
```

**Parámetros**:
```python
backtest_types=["grid_search"]
param_grid={
    "momentum_period": [10, 15, 20, 25, 30],
    "threshold": [1.5, 1.75, 2.0, 2.25, 2.5],
    "position_size_pct": [0.02, 0.03, 0.04, 0.05]
}
```

**Salida**:
```
Grid Search Results (100 combinations):

Best Parameters (by Sharpe Ratio):
  momentum_period: 18 days
  threshold: 1.85σ
  position_size: 3.2%
  → Sharpe: 1.98 | Return: 48.2% | Drawdown: 11.3%

Top 10 Combinations:
  1. momentum=18, threshold=1.85, size=3.2% → Sharpe: 1.98
  2. momentum=20, threshold=1.75, size=3.5% → Sharpe: 1.96
  3. momentum=18, threshold=2.0, size=3.0% → Sharpe: 1.94
  ...

Parameter Sensitivity Analysis:
  momentum_period: High sensitivity (Sharpe: 1.6-1.98)
  threshold: Medium sensitivity (Sharpe: 1.8-1.95)
  position_size: Low sensitivity (Sharpe: 1.90-1.98)
```

---

### 8️⃣ OUT_OF_SAMPLE - Forward Validation

**Qué es**: Entrena en período histórico y prueba en período future sin entrenamiento

**Cuándo usarlo**:
- Validación realista de overfitting
- Verificar que parámetros generalizan
- Simular future performance
- Pre-live trading validation

**Método**:
```
Entrenamiento: 2020-2023 (3 años de data)
Prueba:        2024-2025 (2 años sin tocar modelo)
Comparar:      In-sample return vs out-of-sample return
```

**Parámetros**:
```python
backtest_types=["out_of_sample"]
train_end_date="2023-12-31"
test_start_date="2024-01-01"
test_end_date="2025-12-27"
```

**Salida**:
```
Out-of-Sample Validation:

Training Period (2020-2023):
  - Total Return: 48.3%
  - Sharpe Ratio: 1.95
  - Max Drawdown: 13.2%

Testing Period (2024-2025):
  - Total Return: 38.7% ⚠️ (9.6% lower)
  - Sharpe Ratio: 1.71 ⚠️ (0.24 lower)
  - Max Drawdown: 15.8% (2.6% higher)

Overfitting Assessment:
  - Return degradation: 20% (MODERATE)
  - Sharpe degradation: 12% (ACCEPTABLE)
  - Conclusion: Strategy generalizes reasonably well

⚠️ CAVEAT: 2024-2025 includes bear market, may be unfair comparison
```

---

### 9️⃣ MULTI_STRATEGY - Comparación Simultánea

**Qué es**: Prueba múltiples estrategias en paralelo en el mismo período

**Cuándo usarlo**:
- Comparar qué estrategia es mejor
- Encontrar estrategia óptima para tu perfil
- Análisis comparativo
- Decisión de cuál implementar

**Estrategias Disponibles**:
- Momentum
- Mean Reversion
- Pairs Trading
- Statistical Arbitrage
- Machine Learning
- Dividend Income
- Volatility Selling

**Parámetros**:
```python
backtest_types=["multi_strategy"]
strategies=["momentum", "mean_reversion", "pairs", "ml_models"]
```

**Salida**:
```
Multi-Strategy Comparison:

┌──────────────────────┬──────────┬───────┬───────────┬──────────┐
│ Strategy             │ Return   │ Sharpe│ Drawdown  │ Trades   │
├──────────────────────┼──────────┼───────┼───────────┼──────────┤
│ Momentum             │ 45.3%    │ 1.82  │ 12.5%     │ 127      │
│ Mean Reversion       │ 28.4%    │ 1.45  │ 18.2%     │ 89       │
│ Pairs Trading        │ 22.6%    │ 1.28  │ 22.1%     │ 156      │
│ ML Models            │ 51.2% ✓  │ 1.95  │ 11.3%     │ 142      │
└──────────────────────┴──────────┴───────┴───────────┴──────────┘

Winner: ML Models
  - Best return and Sharpe ratio
  - Lowest drawdown
  - Reasonable trade frequency

Recommendation: Deploy ML Models as primary strategy
```

---

### 🔟 REGIME_TEST - Análisis por Régimen de Mercado

**Qué es**: Divide el histórico en regímenes (bull, bear, sideways) y prueba

**Cuándo usarlo**:
- Entender cómo se comporta en diferentes mercados
- Identificar regímenes problemáticos
- Risk management por régimen
- Hedge strategies para regímenes débiles

**Regímenes Detectados**:
```
2020:     Bull market (COVID recovery)
2021:     Bull market (continued)
2022:     Bear market (-18% annual decline)
2023:     Bull market (recovery)
2024-25:  Mixed (recovery vs recession concerns)
```

**Parámetros**:
```python
backtest_types=["regime_test"]
regime_detection="volatility_based"  # o "return_based"
```

**Salida**:
```
Regime Performance Analysis:

BULL MARKET (2020-2021, 2023):
  Return: 52.3% | Sharpe: 2.12 | Drawdown: 8.5%
  ✅ Strategy excels in bull markets

BEAR MARKET (2022):
  Return: -5.2% | Sharpe: -0.45 | Drawdown: 22.1%
  ❌ Strategy struggles in bear markets
  → Recommendation: Add hedges or reduce allocation

SIDEWAYS (2024-2025):
  Return: 18.3% | Sharpe: 1.35 | Drawdown: 12.3%
  ⚠️ Strategy underperforms in range-bound markets

Overall Regime Robustness:
  Bull: Excellent (5/5 stars)
  Bear: Poor (2/5 stars) - RISK
  Sideways: Fair (3/5 stars)

⚠️ ACTION: Add bear market hedge or tactical allocation
```

---

## Visualizaciones Disponibles

El sistema proporciona múltiples visualizaciones automáticas usando **Plotly** (interactivo), **Matplotlib** (static), y **NetworkX** (gráficos de red).

### 1. 📊 Cumulative Returns Chart

**Qué muestra**: Evolución del valor del portafolio en el tiempo

```
€250,000 initial
      │     /─────────────╱
€350K │    /
      │   /
€300K │  /
      │ ╱
€250K ├────────────────────
    2023      2024      2025

Interpretación:
- Línea suave: volatilidad baja
- Oscilaciones grandes: alta volatilidad
- Pendiente: velocidad de ganancias
```

**Cuándo usarlo**: Evaluación rápida visual de performance

**Cómo acceder**:
```python
runner.visualize_results(results)
# O específicamente:
from app.backtesting.advanced_visualizations import AdvancedVisualizer
viz = AdvancedVisualizer()
viz.plot_cumulative_returns(results.returns)
```

---

### 2. 📉 Underwater Drawdown Chart

**Qué muestra**: Cuánto está por debajo del pico histórico en cada momento

```
% Below Peak
    0│─────────────────────────────
      │         ╱╲
   -5 │        ╱  ╲──╱╲
      │       ╱       ╲
  -10 │      ╱         ╲╱╲
      │     ╱              ╲
  -15 │    ╱                ╲
    2023    2024    2025

Interpretación:
- Profundidad: max drawdown
- Duración: cuánto tardó recuperarse
- Frecuencia: cuántos drawdowns hay
```

**Cuándo usarlo**: Entender riesgo y recuperación

**Cómo acceder**:
```python
viz.plot_underwater_drawdown(results.returns)
```

---

### 3. 📈 Rolling Metrics (Sharpe, Volatility)

**Qué muestra**: Evolución de métricas en ventanas rodantes (ej. Sharpe a 63 días)

```
Rolling Sharpe Ratio (63-day window)
2.5 │  ╱╲    ╱──╲  ╱╲
    │ ╱  ╲  ╱    ╲╱  ╲
2.0 ├    ╲╱        ╲──╱
    │
1.5 │
    2023    2024    2025

Interpretación:
- Picos: períodos de buena performance
- Valles: períodos débiles o volátiles
- Tendencia: si empeora en el tiempo = problema
```

**Cuándo usarlo**: Entender consistencia en el tiempo

**Cómo acceder**:
```python
viz.plot_rolling_metrics(
    returns=results.returns,
    metrics=['sharpe_ratio', 'volatility'],
    window=63
)
```

---

### 4. 🔥 Monthly Returns Heatmap

**Qué muestra**: Grid de retornos mensuales (meses vs años)

```
       2023    2024    2025
Ene   5.2%    2.1%   -1.3%
Feb   3.8%    1.5%    4.2%
Mar   2.1%   -0.8%    3.7%
Abr   4.5%    6.2%    2.1%
...
```

**Colores**:
- 🟢 Verde: retorno positivo
- 🔴 Rojo: retorno negativo
- ⚪ Blanco: cerca de 0%

**Cuándo usarlo**:
- Identificar meses mejores/peores
- Detectar patrones estacionales
- Ver si el 2024 fue "suerte"

**Cómo acceder**:
```python
viz.plot_monthly_returns_heatmap(results.returns)
```

---

### 5. 🌐 Correlation Network

**Qué muestra**: Red de correlaciones entre activos

```
    AAPL──────MSFT
     │╲       ╱│
     │ ╲     ╱ │
     │  ╲   ╱  │
    AMZN─◆─GOOGL
         ╲│╱
         META

Líneas gruesas = correlación alta
Líneas delgadas = correlación baja
```

**Cuándo usarlo**:
- Diversificación
- Entender dependencias
- Riesgo sistémico

**Cómo acceder**:
```python
viz.plot_correlation_network(
    returns=results.returns,
    correlation_threshold=0.5
)
```

---

### 6. 📊 3D Scatter Plot

**Qué muestra**: 3 métricas simultáneamente (Sharpe vs Drawdown vs Return)

```
Eje Z (Return %)
      │
   60 │    ●●●
      │   ●●●●●●
   40 │  ●●●●●●●●●●
      │ ●●●●●●●●●●●●●
   20 ├────────────────
      └─────────────────
        (Drawdown %)
        (Sharpe →)
```

**Cuándo usarlo**: Análisis multidimensional de performance

**Cómo acceder**:
```python
viz.plot_3d_scatter(
    results,
    x_axis='max_drawdown',
    y_axis='sharpe_ratio',
    z_axis='total_return'
)
```

---

### 7. 📍 Parallel Coordinates Plot

**Qué muestra**: Múltiples dimensiones de forma diferente

```
Return  Sharpe  Drawdown  Win Rate  Profit Factor
│         │        │         │         │
100      2.5      0        80%       3.0
└──50────1.8─────15─────60%────2.0──┘
```

Cada línea = una estrategia o período

**Cuándo usarlo**: Comparar múltiples escenarios

**Cómo acceder**:
```python
viz.plot_parallel_coordinates(
    results=[result1, result2, result3]
)
```

---

### 8. 🏆 Performance Comparison Bar Charts

**Qué muestra**: Barras comparativas de métricas

```
Momentum:      ████████░░ 45.3% Return
Mean Rev:      ██████░░░░ 28.4% Return
Pairs:         █████░░░░░ 22.6% Return
ML Models:     █████████░ 51.2% Return ⭐
```

**Cuándo usarlo**: Comparación rápida entre estrategias

**Cómo acceder**:
```python
viz.plot_strategy_comparison(results_dict)
```

---

## Ejemplos Prácticos

### Ejemplo 1: Backtest Simple de Maximizar Capital

**Objetivo**: Invertidor agresivo con €250,000 queriendo máximo retorno

```python
from decimal import Decimal
from app.core.models.investment_profile import InvestmentProfile, CapitalTier
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner

# 1. Definir perfil
profile = InvestmentProfile(
    capital_initial=Decimal("250000"),
    capital_tier=CapitalTier.LARGE,
    objetivo_inversion="maximizar_capital",  # Objetivo principal
    risk_tolerance="alto",                   # Aceptar volatilidad
    investment_horizon=24                     # 2 años
)

# 2. Ejecutar backtests
runner = ComprehensiveBacktestRunner()
results = runner.run_comprehensive_backtest(
    profile=profile,
    strategy_name="momentum",
    backtest_types=["baseline", "walk_forward", "out_of_sample"]
)

# 3. Analizar resultados
print("\n=== BACKTEST RESULTS ===")
for test_type, result in results.items():
    print(f"\n{test_type.upper()}:")
    print(f"  Total Return: {result.total_return:.2f}%")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {result.max_drawdown:.2f}%")
    print(f"  Win Rate: {result.win_rate:.1f}%")
    print(f"  Total Trades: {len(result.trades)}")

# 4. Visualizar
runner.visualize_results(results)

# 5. Exportar reporte
runner.export_to_html(
    results,
    "reports/momentum_250k_aggressive.html"
)
```

**Salida Esperada**:
```
=== BACKTEST RESULTS ===

BASELINE:
  Total Return: 45.32%
  Sharpe Ratio: 1.82
  Max Drawdown: 12.5%
  Win Rate: 58.2%
  Total Trades: 127

WALK_FORWARD:
  Total Return: 42.18%
  Sharpe Ratio: 1.71
  Max Drawdown: 14.3%
  Win Rate: 56.8%
  Total Trades: 389

OUT_OF_SAMPLE:
  Total Return: 38.66%
  Sharpe Ratio: 1.64
  Max Drawdown: 15.8%
  Win Rate: 55.1%
  Total Trades: 234
```

---

### Ejemplo 2: Backtests Múltiples para Dividend Income

**Objetivo**: Inversor conservador €500,000 queriendo ingresos pasivos

```python
from app.core.models.investment_profile import InvestmentProfile, CapitalTier
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
import pandas as pd

# 1. Perfil para ingresos
profile = InvestmentProfile(
    capital_initial=Decimal("500000"),
    capital_tier=CapitalTier.LARGE,
    objetivo_inversion="maximizar_dividendos",  # Income focus
    risk_tolerance="bajo",                      # Conservative
    investment_horizon=60                        # 5 años
)

# 2. Todos los 10 backtests
runner = ComprehensiveBacktestRunner()
results = runner.run_comprehensive_backtest(
    profile=profile,
    strategy_name="dividend_income",
    backtest_types=[
        "baseline",
        "learning_engines",
        "walk_forward",
        "monte_carlo",
        "ablation",
        "out_of_sample",
        "regime_test"
    ]
)

# 3. Análisis consolidado
summary = pd.DataFrame({
    'Backtest Type': list(results.keys()),
    'Return %': [r.total_return for r in results.values()],
    'Sharpe': [r.sharpe_ratio for r in results.values()],
    'Max Drawdown %': [r.max_drawdown for r in results.values()],
    'Income/Month €': [r.monthly_income * 500000 for r in results.values()],
})

print(summary.to_string())

# 4. Visualizaciones específicas para income
runner.visualize_results(results)

# 5. Generar reporte detallado
from app.services.reporting_generator.reporting_generator import ReportingGenerator

generator = ReportingGenerator()
report = generator.generate_detailed_report(
    results=results,
    profile=profile,
    include_monte_carlo=True,
    include_regime_analysis=True
)

report.export_to_html("reports/dividend_500k_detailed.html")
report.export_to_pdf("reports/dividend_500k_detailed.pdf")
```

---

### Ejemplo 3: Optimización de Parámetros

**Objetivo**: Encontrar mejores parámetros para estrategia momentum

```python
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner

# 1. Grid search
runner = ComprehensiveBacktestRunner()
results = runner.run_comprehensive_backtest(
    profile=profile,
    strategy_name="momentum",
    backtest_types=["grid_search"],
    param_grid={
        "momentum_period": [10, 15, 20, 25, 30],
        "threshold": [1.5, 1.75, 2.0, 2.25, 2.5],
        "position_size_pct": [0.02, 0.03, 0.04, 0.05]
    }
)

# 2. Encontrar best parameters
best_params = results["grid_search"].best_parameters
best_sharpe = results["grid_search"].best_sharpe_ratio

print(f"Best Parameters: {best_params}")
print(f"Best Sharpe Ratio: {best_sharpe:.2f}")

# 3. Validar con out-of-sample
final_results = runner.run_comprehensive_backtest(
    profile=profile,
    strategy_name="momentum",
    backtest_types=["out_of_sample"],
    strategy_params=best_params
)

# 4. Comparar in-sample vs out-of-sample
print(f"\nGrid Search (In-sample): {best_sharpe:.2f}")
print(f"Out-of-Sample Sharpe: {final_results['out_of_sample'].sharpe_ratio:.2f}")

overfitting = (best_sharpe - final_results['out_of_sample'].sharpe_ratio) / best_sharpe
print(f"Overfitting Level: {overfitting:.1%}")

if overfitting > 0.15:
    print("⚠️ WARNING: High overfitting detected!")
```

---

## Interpretar Resultados

### Métricas Clave

#### 1. **Total Return %**
```
Definición: (Valor Final - Valor Inicial) / Valor Inicial × 100
Ejemplo: €250,000 → €362,500 = 45% retorno

Interpretación:
- > 30% anual:    Excelente
- 15-30% anual:   Muy bueno
- 8-15% anual:    Bueno
- 4-8% anual:     Aceptable
- < 4% anual:     Pobre

Nota: Depende del objetivo y horizonte
```

#### 2. **Sharpe Ratio** ⭐ MÁS IMPORTANTE

```
Fórmula: (Return - Risk-Free Rate) / Volatility

Interpretación:
- > 2.0:  Excepcional
- 1.5-2.0: Excelente ✓
- 1.0-1.5: Muy bueno
- 0.5-1.0: Bueno
- < 0.5:  Pobre

Qué mide: Retorno ganado por unidad de riesgo
→ Métrica más importante para comparar estrategias
```

#### 3. **Max Drawdown %** (Riesgo)

```
Definición: Mayor pérdida de pico a valle

Ejemplo:
  Pico:  €350,000
  Valle: €300,000
  Drawdown: (300-350)/350 = -14.3%

Interpretación por objetivo:
- Capital Preservation: Máx 10%
- Income: Máx 12-15%
- Balanced: Máx 15-20%
- Growth: Máx 20-30%
- Aggressive: Máx 30-50%

Pregunta: ¿Puedes dormir si pierde 14.3% en 1 semana?
```

#### 4. **Calmar Ratio**

```
Fórmula: (Annualized Return) / (Max Drawdown)

Ejemplo: 45% annual return / 12.5% drawdown = 3.6

Interpretación:
- > 3.0: Excelente retorno/riesgo
- 1.5-3.0: Bueno
- < 1.5: Pobre (demasiado riesgo)

Vs Sharpe Ratio:
- Sharpe: Usa volatilidad día a día
- Calmar: Usa drawdown máximo (peor escenario)
→ Calmar es más conservador
```

#### 5. **Win Rate %**

```
Definición: % de trades ganadores

Ejemplo: 65 trades ganadores / 127 total = 51.2%

Interpretación:
- > 60%: Excelente
- 50-60%: Bueno ✓
- 40-50%: Aceptable
- < 40%: Pobre (necesita profit factor > 2.0)

NOTA: Win rate BAJO es OK si:
  - Ganancias grandes cuando gana
  - Pérdidas pequeñas cuando pierde
  → Mira Profit Factor, no solo Win Rate
```

#### 6. **Profit Factor**

```
Fórmula: (Sum of Gains) / (Sum of Losses)

Ejemplo:
  Ganancias totales: €45,000
  Pérdidas totales:  €15,000
  Profit Factor: 45,000 / 15,000 = 3.0

Interpretación:
- > 2.0:  Excelente ✓
- 1.5-2.0: Muy bueno
- 1.2-1.5: Bueno
- 1.0-1.2: Marginal
- < 1.0:  Losing (NO HACER)

Trade-off con Win Rate:
- 60% win rate + 1.5 profit factor ✓ (consistente)
- 40% win rate + 3.0 profit factor ✓ (varianza alta)
```

### Señales de Alerta

🚨 **MAX DRAWDOWN > 20%**
```
Problema: Volatilidad muy alta o estrategia riesgosa
Acción: Reducir leverage, agregar hedges, revisar stop loss
```

🚨 **OUT-OF-SAMPLE RETURN < 60% IN-SAMPLE**
```
Problema: Probable overfitting
Acción: Usar menos parámetros, más datos, validation framework
```

🚨 **SHARPE < 1.0**
```
Problema: Retorno insuficiente para el riesgo
Acción: Revisar estrategia, optimizar parámetros o usar mejor estrategia
```

🚨 **PROFIT FACTOR < 1.5**
```
Problema: No hay margen de seguridad
Acción: Ajustar stop loss, mejorar entry signals, agregar filtros
```

🚨 **BEAR MARKET PERFORMANCE MUCHO PEOR**
```
Problema: Estrategia no funciona en mercados bajistas
Acción: Agregar hedge (opciones, inverse ETFs), reduce allocation
```

---

## API REST para Backtests

Si prefieres usar la API HTTP en lugar de Python directo:

### Endpoint 1: Procesar Input de Usuario

```bash
curl -X POST "http://localhost:8000/capa2/process-input" \
  -H "Content-Type: application/json" \
  -d '{
    "capital_initial": 250000,
    "objetivo_inversion": "maximizar_capital",
    "risk_tolerance": "medio",
    "investment_horizon": 24
  }'
```

**Respuesta**:
```json
{
  "capital_initial": 250000,
  "capital_tier": "LARGE",
  "objetivo_inversion": "maximizar_capital",
  "risk_tolerance": "medio",
  "validation_passed": true,
  "warnings": []
}
```

### Endpoint 2: Generar Perfil de Inversión

```bash
curl -X POST "http://localhost:8000/capa2/generate-profile" \
  -H "Content-Type: application/json" \
  -d '{
    "capital_initial": 250000,
    "objetivo_inversion": "maximizar_capital"
  }'
```

### Endpoint 3: Ejecutar Backtest

```bash
curl -X POST "http://localhost:8000/capa2/run-backtest" \
  -H "Content-Type: application/json" \
  -d '{
    "capital_initial": 250000,
    "objetivo_inversion": "maximizar_capital",
    "strategy_name": "momentum",
    "backtest_types": ["baseline", "walk_forward"]
  }'
```

**Respuesta**:
```json
{
  "results": {
    "baseline": {
      "total_return": 45.32,
      "sharpe_ratio": 1.82,
      "max_drawdown": 12.5,
      "win_rate": 58.2,
      "profit_factor": 2.1,
      "trades_total": 127
    },
    "walk_forward": {
      "total_return": 42.18,
      "sharpe_ratio": 1.71,
      "max_drawdown": 14.3,
      ...
    }
  }
}
```

### Endpoint 4: Descargar Visualizaciones

```bash
# Descargar como HTML
curl -X GET "http://localhost:8000/capa2/backtest-visualization?format=html" \
  > backtest_results.html

# Descargar como PDF
curl -X GET "http://localhost:8000/capa2/backtest-visualization?format=pdf" \
  > backtest_results.pdf
```

---

## Mejores Prácticas

### ✅ ANTES de Backtestear

1. **Define tu objetivo claro**
   ```
   ¿Máximo retorno? ¿Ingresos? ¿Capital seguro?
   Eso determina qué objetivo usar
   ```

2. **Ten datos limpios**
   ```python
   # Verificar datos
   assert df['close'] > 0
   assert df['volume'] > 0
   assert no df.isna().any()
   ```

3. **Define horizonte realista**
   ```
   - Corto plazo (< 6 meses): estrategias de trading
   - Medio plazo (6-24 meses): mixed strategies
   - Largo plazo (> 24 meses): buy & hold / dividends
   ```

### ✅ DURANTE Backtesting

4. **Comienza con baseline simple**
   ```python
   # Primero ejecuta basic backtest
   results = runner.run_comprehensive_backtest(
       profile, strategy, ["baseline"]
   )
   # Solo si pasó, continúa con otros tipos
   ```

5. **Valida en múltiples períodos**
   ```python
   # No solo 1 año, prueba 3-5 años mínimo
   backtest_types=["walk_forward", "out_of_sample"]
   ```

6. **Incluye stress testing**
   ```python
   # Siempre ejecuta monte carlo
   backtest_types=["monte_carlo"]  # Entender tail risk
   ```

### ✅ DESPUÉS de Backtesting

7. **Documenta supuestos**
   ```
   - Data source: ¿Cuál?
   - Período: 2020-2025
   - Slippage: 1 pip, 2 bps comisión
   - Leverage: 1.0x
   ```

8. **Compara con benchmark**
   ```python
   # Compare against:
   # - S&P 500 (spy) - returns: 10% anual
   # - Russell 2000 (iqm) - for small caps
   # - Sector benchmarks

   vs_spy = (my_return - benchmark_return) / benchmark_return
   print(f"Alpha vs SPY: {vs_spy:.1%}")
   ```

9. **Verifica sensibilidad de parámetros**
   ```python
   # Pequeños cambios no deben romper la estrategia
   backtest_types=["grid_search"]
   param_grid={"momentum": [18, 20, 22]}  # ±1 day

   # Si sharpe cambia < 10%, robusto ✓
   # Si sharpe cambia > 30%, frágil ❌
   ```

10. **Paper trade antes de live**
    ```
    - Run el backtest final validado
    - Trade con dinero fake (paper trading) 1 mes
    - Verifica que real-world = backtest
    - Solo entonces: live trading con $ pequeño
    ```

---

## Troubleshooting

### Problema: "No data available for symbol"
**Solución**:
```python
# Verificar que datos están descargados
from app.services.data_service import DataService
service = DataService()
service.download_historical_data(['AAPL'], '2020-01-01', '2025-12-27')
```

### Problema: "Strategy underperforms SPY"
**Solución**:
1. Revisar comisiones (¿incluidas en backtest?)
2. Revisar slippage (mercado real tiene más)
3. Revisar lookback bias (información en el futuro?)
4. Aumentar ventana de training

### Problema: "Out-of-sample performance mucho peor"
**Solución**:
1. Más datos de training (2-3 años mínimo)
2. Menos parámetros (overfitting)
3. Validación cruzada (walk-forward)
4. Revisar if market regime changed

### Problema: "Backtest tarda mucho"
**Solución**:
```python
# Usar multiprocessing
backtest_types=["baseline"]  # Solo 1 tipo
# O usar cloud para computation-heavy
```

---

## Conclusión

El sistema de backtesting algoTrading te permite:

✅ **Validar estrategias** antes de arriesgar dinero real
✅ **Comparar objetivos** (¿cuál es mejor para ti?)
✅ **Optimizar parámetros** usando datos históricos
✅ **Entender riesgos** con análisis de stress
✅ **Visualizar resultados** para decisiones informadas
✅ **Integrar con live trading** cuando estés listo

**Siguiente paso**: Elige un objetivo, ejecuta los backtests recomendados, y toma una decisión informada.

¿Preguntas? Ver documentación en el código o contactar support.

---

**Última actualización**: 2025-12-27
**Versión**: 1.0
**Status**: ✅ Ready for Production

