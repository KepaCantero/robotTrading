# PLAN DE EJECUCIÓN - TAREAS PENDIENTES

**Fecha:** 31 de Enero de 2026
**Basado en:** AUDIT_PLAN_COMPLETO.md
**Objetivo:** Sistema autónomo para backtests de 25 años y optimización multi-estrategia
**Estado Actual:** 43% de cumplimiento (~1200 de 2800 reglas implementadas)

---

## ÍNDICE

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Matriz de Prioridades](#2-matriz-de-prioridades)
3. [Fase 5: Backtesting Engine](#3-fase-5-backtesting-engine)
4. [Fase 6: Optimización](#4-fase-6-optimización)
5. [Fase 7: Multi-Activo](#5-fase-7-multi-activo)
6. [Brechas Críticas por Categoría](#6-brechas-críticas-por-categoría)
7. [Reglas Específicas Pendientes](#7-reglas-específicas-pendientes)

---

## 1. RESUMEN EJECUTIVO

### 1.1 Estado Actual del Proyecto

| Categoría | Reglas | Implementadas | % Cumplimiento |
|-----------|--------|---------------|----------------|
| **Risk Management** | 300 | 180 | **60%** ⬆️ |
| **Execution Quality** | 250 | 125 | **50%** ⬆️ |
| **Portfolio Optimization** | 200 | 90 | **45%** ⬆️ |
| **Performance** | 150 | 60 | **40%** |
| **Backtesting & Validation** | 100 | 85 | **85%** ⭐ |
| **Clean Architecture** | 200 | 140 | **70%** ⬆️ |
| **Testing** | 200 | 90 | **45%** |
| **Features Especializadas** | 350 | 80 | **23%** |
| **Crypto/FX Específico** | 100 | 0 | **0%** |

**TOTAL: ~850 de 2800 reglas implementadas = 30%**
**CON PARCIALMENTE IMPLEMENTADAS: ~1200 de 2800 = 43% de cumplimiento efectivo**

### 1.2 Fases Completadas ✅

| Fase | Descripción | Estado |
|------|-------------|--------|
| **FASE 0** | Auditoría Completa | ✅ COMPLETADO |
| **FASE 1** | Fundación (Python QA + Arquitectura) | ✅ COMPLETADO |
| **FASE 2** | Dominio Core (Models + Services) | ✅ COMPLETADO |
| **FASE 3** | Portfolio Optimization (MVO, HRP, NCO, BL) | ✅ COMPLETADO |
| **FASE 4** | Estrategias (9 estrategias de dominio) | ✅ COMPLETADO |
| **FASE 4.5** | InputProfile Integration Services | ✅ COMPLETADO |

### 1.3 Fases Pendientes ❌

| Fase | Descripción | Duración Estimada | Prioridad |
|------|-------------|-------------------|-----------|
| **FASE 5** | Backtesting Engine (25 años robusto) | 3 semanas | 🔴 ALTA |
| **FASE 6** | Optimización (Parámetros + Multi-objetivo) | 3 semanas | 🟡 MEDIA |
| **FASE 7** | Multi-Activo (Crypto + FX) | 2 semanas | 🟢 BAJA |

---

## 2. MATRIZ DE PRIORIDADES

### 2.1 Prioridad ALTA 🔴 (Impacto Inmediato en P&L)

| # | Tarea | Categoría | Regla | Impacto |
|---|-------|-----------|-------|---------|
| 1 | **Avellaneda-Stoikov Market Making** | Execution | Stoikov #6 | Crítico MM |
| 2 | **Order Flow Imbalance Enhanced** | Execution | Aldridge #2 | Execution Quality |
| 3 | **NumPy Vectorization Verification** | Performance | High Performance | 10-100x speedup |
| 4 | **Robust 25-year Backtesting** | Backtesting | Carver, Pardo | Core Feature |
| 5 | **Survivorship Bias Correction** | Backtesting | Chan #5 | Data Integrity |
| 6 | **Point-in-Time Database** | Backtesting | Chan #2 | No Look-ahead |
| 7 | **Kill Switches 5% Diario** | Risk | Hull, Chan #15 | Risk Control |

### 2.2 Prioridad MEDIA 🟡 (Mejora de Performance)

| # | Tarea | Categoría | Regla | Impacto |
|---|-------|-----------|-------|---------|
| 8 | **Fundamental Law: IR = IC × √BR** | Metrics | Grinold & Kahn | Alpha Analysis |
| 9 | **Markowitz Mean-Variance Expansión** | Portfolio | Markowitz #66-80 | Optimization |
| 10 | **Walk-Forward Validation** | Validation | Pardo #54 | Robustness |
| 11 | **Overfitting Detection** | Validation | Hastie #96 | Model Quality |
| 12 | **Regime Detection** | Validation | Ilmanen #254 | Adaptability |
| 13 | **Grid Search Optimization** | Optimization | General | Parameter Tuning |
| 14 | **Bayesian Optimization (Optuna)** | Optimization | General | Efficiency |
| 15 | **Pareto Front Optimization** | Optimization | General | Multi-objective |

### 2.3 Prioridad BAJA 🟢 (Features Especializadas)

| # | Tarea | Categoría | Regla | Impacto |
|---|-------|-----------|-------|---------|
| 16 | **AMM/Dex Trading** | Crypto | Steffensen | Crypto Only |
| 17 | **FX Intermarket Signals** | FX | Laidi #1 | FX Only |
| 18 | **Carry Trade para Forex** | FX | Ilmanen #259 | FX Only |
| 19 | **Crypto Momentum Strategy** | Crypto | Gray & Vogel | Crypto Only |

---

## 3. FASE 5: BACKTESTING ENGINE

**Duración:** 3 semanas
**Prioridad:** 🔴 ALTA
**Objetivo:** Robust backtesting for 25 years

### 3.1 Semana 12: Core Engine

| Tarea | Descripción | Archivo | Regla |
|-------|-------------|---------|-------|
| 5.1 | **Robust backtesting for 25 years** | `app/backtesting/robust_backtester.py` | Carver #54 |
| 5.2 | **Survivorship bias correction** | `app/backtesting/survivorship_bias_corrector.py` | Chan #5 |
| 5.3 | **Corporate actions handling** | `app/backtesting/corporate_actions.py` | Pardo #54 |
| 5.4 | **Dividend reinvestment** | `app/backtesting/dividend_handler.py` | Berkin #34 |

#### 5.1 Robust Backtesting for 25 Years

**Requisitos:**
```python
class RobustBacktester:
    """
    Backtester robusto para 25 años de datos históricos.

    Requisitos (Pardo, Carver):
    - Manejar gaps en datos
    - Ajustar por splits y dividendos
    - Point-in-time data (no look-ahead)
    - Survivorship bias correction
    """

    def __init__(self):
        self.min_years = 25
        self.min_data_points = 252 * 25  # 6,300 días
        self.max_gap_pct = 0.05  # Máximo 5% gaps

    def validate_data_quality(self, data: pd.DataFrame) -> bool:
        """Validar calidad de datos para backtesting."""
        # Check for gaps
        # Check for outliers
        # Check for stale data
        pass

    def run_25_year_backtest(
        self,
        strategy: Strategy,
        data: pd.DataFrame,
        initial_capital: float = 1_000_000,
    ) -> BacktestResult:
        """Ejecutar backtesting de 25 años."""
        pass
```

**Archivos a crear/modificar:**
- [ ] `app/backtesting/robust_engine/robust_backtester.py`
- [ ] `app/backtesting/robust_engine/corporate_actions.py`
- [ ] `app/backtesting/robust_engine/dividend_handler.py`
- [ ] `app/backtesting/robust_engine/survivorship_adjuster.py`

#### 5.2 Survivorship Bias Correction

**Requisitos (Chan #5):**
```python
class SurvivorshipBiasCorrector:
    """
    Corrige survivorship bias incluyendo empresas que quebraron.

    Methods:
    - add_delisted_stocks(): Agregar empresas que ya no existen
    - adjust_returns(): Ajustar retornos por delistings
    - calculate_survivorship_adjusted_returns(): Retornos ajustados
    """
```

**Fuentes de datos:**
- [ ] Implementar descarga de delisted stocks
- [ ] Crear base de datos de empresas quebradas
- [ ] Ajustar retornos por delistings

#### 5.3 Corporate Actions Handling

**Requisitos:**
```python
class CorporateActionsHandler:
    """
    Maneja acciones corporativas que afectan precios.

    Methods:
    - adjust_for_splits(): Ajustar precios por splits
    - adjust_for_dividends(): Ajustar por dividendos
    - adjust_for_rights_offers(): Ajustar por ofertas de derechos
    - adjust_for_mergers(): Ajustar por fusiones
    """
```

**Acciones corporativas a manejar:**
- [ ] Stock splits (ej: 10:1, 3:2)
- [ ] Cash dividends
- [ ] Stock dividends
- [ ] Rights offerings
- [ ] Mergers and acquisitions
- [ ] Spin-offs
- [ ] Tender offers

#### 5.4 Dividend Reinvestment

**Requisitos (Berkin & Swedroe, Meb Faber):**
```python
class DividendReinvestor:
    """
    Reinvierte dividendos automáticamente.

    Methods:
    - reinvest_dividends(): Reinvertir dividendos en misma acción
    - calculate_total_return(): Incluir dividendos reinvertidos
    - track_dividend_income(): Seguir ingresos por dividendos
    """
```

### 3.2 Semana 13: Execution

| Tarea | Descripción | Archivo | Regla |
|-------|-------------|---------|-------|
| 5.5 | **Pessimistic execution** | `app/backtesting/execution/execution_model.py` | Carver #53 ✅ |
| 5.6 | **Realistic transaction costs** | `app/backtesting/execution/transaction_cost.py` | Chan #4 ✅ |
| 5.7 | **Slippage modeling** | `app/backtesting/execution/slippage_model.py` | Chan #3, Harris #207 |
| 5.8 | **Market impact** | `app/backtesting/execution/market_impact.py` | Almgren-Chriss |

#### 5.5 Pessimistic Execution (YA EXISTE - Verificar)

**Estado:** ✅ PARCIALMENTE IMPLEMENTADO en `execution_engine.py`

**Mejoras necesarias:**
- [ ] Verificar implementación completa
- [ ] Documentar comportamiento
- [ ] Agregar tests

#### 5.6 Realistic Transaction Costs (YA EXISTE - Verificar)

**Estado:** ✅ PARCIALMENTE IMPLEMENTADO en `cost_calculator.py`

**Componentes de costo (Chan #4):**
```python
class TransactionCostCalculator:
    """
    Calcula costo total de transacción.

    Components (Chan #4, Barry Johnson):
    1. Broker commission
    2. Exchange fee
    3. Regulatory fee (SEC, FINRA)
    4. Data feed fee
    5. Slippage (bid-ask spread)
    6. Market impact
    """
```

**Mejoras necesarias:**
- [ ] Verificar que todos los componentes estén incluidos
- [ ] Calcular commission impact % (Chan #18)
- [ ] Validar que commission impact < 15%

#### 5.7 Slippage Modeling

**Requisitos (Chan #3, #16, Harris #207):**
```python
class SlippageModel:
    """
    Modela slippage realista.

    Requisitos:
    - Usar bid-ask spread COMPLETO (Chan #3)
    - Slippage como función de volatilidad (Chan #16)
    - Bid-ask bounce filter (Harris #208)
    - Timing cost calculation (Harris #209)
    """
```

**Implementación:**
```python
def calculate_slippage(
    self,
    symbol: str,
    order_size: float,
    side: OrderSide,
    volatility: float,
    spread: float,
) -> float:
    """
    Calcula slippage basado en:
    - Volatilidad del activo
    - Tamaño de la orden
    - Bid-ask spread
    - Liquidity del mercado
    """
    # Volatility-adjusted slippage (Chan #16)
    base_slippage = spread / 2
    volatility_adjustment = volatility * order_size / avg_daily_volume
    return base_slippage + volatility_adjustment
```

#### 5.8 Market Impact

**Requisitos (Almgren-Chriss #21, Kissell #106-115):**
```python
class MarketImpactModel:
    """
    Modela impacto de mercado de órdenes grandes.

    Requisitos (Almgren-Chriss):
    - Permanent impact: α · sqrt(7/X) · |ν|
    - Temporary impact: β · |ν|
    - Optimal execution trajectory
    """
```

**Implementación:**
```python
def calculate_market_impact(
    self,
    order_size: float,
    avg_daily_volume: float,
    volatility: float,
    price: float,
) -> float:
    """
    Almgren-Chriss market impact model.

    Permanent impact: α · sqrt(7/X) · |ν|
    Temporary impact: β · |ν|
    """
    # Permanent market impact
    permanent = self.alpha * np.sqrt(self.T / self.shares) * abs(order_size)

    # Temporary market impact
    temporary = self.beta * abs(order_size) / avg_daily_volume

    return permanent + temporary
```

### 3.3 Semana 14: Validation

| Tarea | Descripción | Archivo | Regla |
|-------|-------------|---------|-------|
| 5.9 | **Walk-forward validation** | `app/backtesting/validation/walk_forward.py` | Pardo #54 ✅ |
| 5.10 | **Overfitting detection** | `app/backtesting/validation/overfitting_detector.py` | Hastie #96 |
| 5.11 | **Regime detection** | `app/backtesting/validation/regime_detector.py` | Ilmanen #254 |

#### 5.9 Walk-Forward Validation (YA EXISTE - Verificar)

**Estado:** ✅ PARCIALMENTE IMPLEMENTADO en `walk_forward_validator.py`

**Requisitos (Pardo #54):**
```python
class WalkForwardValidator:
    """
    Validación walk-forward para evitar overfitting.

    Requisitos:
    - 70% train / 30% test split
    - Mínimo 5 ciclos de validación
    - IS/OOS metrics separation
    - Consistency ratio calculation
    - Degradation thresholds (max 30%)
    """
```

**Mejoras necesarias:**
- [ ] Verificar que se cumple 70/30 split
- [ ] Validar mínimo 5 ciclos
- [ ] Documentar métricas IS vs OOS

#### 5.10 Overfitting Detection

**Requisitos (Hastie #96, Pardo #41):**
```python
class OverfittingDetector:
    """
    Detecta overfitting en backtests.

    Métricas:
    - Gap IS/OOS > 20% (Hastie #96)
    - Degradation ratio > 30% (Pardo)
    - Parameter stability tests
    - Monte Carlo validation
    """
```

**Implementación:**
```python
def detect_overfitting(
    self,
    is_metrics: dict,
    oos_metrics: dict,
) -> OverfittingResult:
    """
    Detecta overfitting comparando IS vs OOS.

    Red flags:
    - Sharpe ratio gap > 20%
    - Return degradation > 30%
    - Max drawdown much worse in OOS
    - Parameter instability
    """
    sharpe_gap = (is_metrics['sharpe'] - oos_metrics['sharpe']) / is_metrics['sharpe']
    return_gap = (is_metrics['return'] - oos_metrics['return']) / is_metrics['return']

    is_overfitted = sharpe_gap > 0.20 or return_gap > 0.30
    return OverfittingResult(is_overfitted, sharpe_gap, return_gap)
```

#### 5.11 Regime Detection

**Requisitos (Ilmanen #254):**
```python
class RegimeDetector:
    """
    Detecta cambios de régimen en el mercado.

    Regímenes:
    - Bull market (tendencia alcista)
    - Bear market (tendencia bajista)
    - Sideways/ranging
    - High volatility
    - Low volatility
    """
```

**Implementación:**
```python
def detect_regime(
    self,
    returns: pd.Series,
    window: int = 252,
) -> MarketRegime:
    """
    Detecta régimen actual usando:
    - Trend (moving average slope)
    - Volatility (rolling std)
    - Drawdown (from peak)
    """
    # Calculate trend
    trend = returns.rolling(window).mean()

    # Calculate volatility
    volatility = returns.rolling(window).std()

    # Classify regime
    if trend > 0 and volatility < 0.15:
        return MarketRegime.BULL_LOW_VOL
    elif trend > 0 and volatility >= 0.15:
        return MarketRegime.BULL_HIGH_VOL
    elif trend < 0 and volatility < 0.15:
        return MarketRegime.BEAR_LOW_VOL
    elif trend < 0 and volatility >= 0.15:
        return MarketRegime.BEAR_HIGH_VOL
    else:
        return MarketRegime.SIDEWAYS
```

---

## 4. FASE 6: OPTIMIZACIÓN

**Duración:** 3 semanas
**Prioridad:** 🟡 MEDIA
**Objetivo:** Encontrar mejores parámetros para InputProfile

### 4.1 Semana 15: Parameter Optimization

| Tarea | Descripción | Archivo | Regla |
|-------|-------------|---------|-------|
| 6.1 | **Grid search** | `app/optimization/parameter/grid_search.py` | General |
| 6.2 | **Random search** | `app/optimization/parameter/random_search.py` | General |
| 6.3 | **Bayesian optimization (Optuna)** | `app/optimization/parameter/bayesian_optimizer.py` | General |

#### 6.1 Grid Search

**Requisitos:**
```python
class GridSearchOptimizer:
    """
    Optimización por grid search.

    Requisitos:
    - Definir grid de parámetros
    - Evaluar todas las combinaciones
    - Retornar mejores parámetros
    """
```

**Implementación:**
```python
def optimize(
    self,
    strategy: Strategy,
    param_grid: dict,
    data: pd.DataFrame,
    metric: str = 'sharpe',
) -> OptimizationResult:
    """
    Ejecuta grid search sobre parámetros.

    Example param_grid:
    {
        'lookback': [20, 50, 100, 200],
        'entry_threshold': [1.0, 1.5, 2.0],
        'exit_threshold': [0.5, 1.0],
    }
    """
    from itertools import product

    # Generate all combinations
    keys = param_grid.keys()
    values = param_grid.values()
    combinations = [dict(zip(keys, v)) for v in product(*values)]

    # Evaluate each combination
    results = []
    for params in combinations:
        result = self._evaluate_params(strategy, params, data, metric)
        results.append((params, result))

    # Return best
    return max(results, key=lambda x: x[1][metric])
```

#### 6.2 Random Search

**Requisitos:**
```python
class RandomSearchOptimizer:
    """
    Optimización por random search.

    Ventaja sobre grid search:
    - Más eficiente para espacios grandes
    - Mejor cobertura del espacio
    """
```

#### 6.3 Bayesian Optimization (Optuna)

**Requisitos:**
```python
class BayesianOptimizer:
    """
    Optimización bayesiana usando Optuna.

    Ventajas:
    - Más eficiente que grid/random search
    - Aprende de evaluaciones previas
    - Soporta parámetros continuos y discretos
    """
```

**Implementación:**
```python
import optuna

def optimize(
    self,
    strategy: Strategy,
    search_space: dict,
    data: pd.DataFrame,
    n_trials: int = 100,
) -> OptimizationResult:
    """
    Ejecuta optimización bayesiana con Optuna.

    Example search_space:
    {
        'lookback': (20, 200),  # continuous
        'entry_threshold': (1.0, 3.0),
        'exit_threshold': (0.1, 1.0),
    }
    """
    def objective(trial):
        # Suggest parameters
        params = {}
        for key, (low, high) in search_space.items():
            params[key] = trial.suggest_float(key, low, high)

        # Evaluate
        result = self._evaluate_params(strategy, params, data)
        return result['sharpe']

    # Run optimization
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials)

    return OptimizationResult(
        best_params=study.best_params,
        best_value=study.best_value,
        n_trials=len(study.trials),
    )
```

### 4.2 Semana 16: Multi-Objective

| Tarea | Descripción | Archivo | Regla |
|-------|-------------|---------|-------|
| 6.4 | **Pareto front optimization** | `app/optimization/parameter/multi_objective.py` | General |
| 6.5 | **Balance return vs drawdown vs Sharpe** | `app/optimization/parameter/multi_objective.py` | General |

#### 6.4 Pareto Front Optimization

**Requisitos:**
```python
class MultiObjectiveOptimizer:
    """
    Optimización multi-objetivo con Pareto front.

    Objetivos:
    - Maximizar retorno
    - Minimizar drawdown
    - Maximizar Sharpe ratio
    """
```

**Implementación:**
```python
def optimize_pareto(
    self,
    strategy: Strategy,
    search_space: dict,
    data: pd.DataFrame,
    objectives: list[str] = ['return', 'sharpe', '-max_drawdown'],
) -> ParetoFront:
    """
    Encuentra Pareto front de soluciones no-dominadas.

    Una solución domina a otra si es mejor en todos los objetivos.
    El Pareto front contiene todas las soluciones no-dominadas.
    """
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.optimize import minimize

    # Define problem
    problem = StrategyOptimizationProblem(
        strategy=strategy,
        search_space=search_space,
        data=data,
        objectives=objectives,
    )

    # Run NSGA-II
    algorithm = NSGA2(pop_size=100)
    result = minimize(problem, algorithm, termination=('n_gen', 100))

    return ParetoFront(result.F, result.X)
```

#### 6.5 Balance Return vs Drawdown vs Sharpe

**Requisitos:**
```python
def select_balanced_solution(
    self,
    pareto_front: ParetoFront,
    preferences: dict = {
        'return_weight': 0.4,
        'sharpe_weight': 0.4,
        'drawdown_weight': 0.2,
    },
) -> Solution:
    """
    Selecciona solución balanceada del Pareto front.

    Usa weighted sum o utopia point distance.
    """
    # Normalize objectives
    normalized = self._normalize_objectives(pareto_front)

    # Calculate weighted score
    scores = (
        preferences['return_weight'] * normalized['return'] +
        preferences['sharpe_weight'] * normalized['sharpe'] +
        preferences['drawdown_weight'] * (1 - normalized['drawdown'])
    )

    # Return best
    best_idx = np.argmax(scores)
    return pareto_front.solutions[best_idx]
```

### 4.3 Semana 17: Auto-Selection

| Tarea | Descripción | Archivo | Regla |
|-------|-------------|---------|-------|
| 6.6 | **Best strategy for InputProfile** | `app/application/use_cases/select_strategy.py` | User |
| 6.7 | **Ensemble methods** | `app/ensemble/ensemble.py` | General |
| 6.8 | **Strategy combination** | `app/ensemble/strategy_combiner.py` | General |

#### 6.6 Best Strategy for InputProfile

**Requisitos:**
```python
class StrategySelector:
    """
    Selecciona mejor estrategia para InputProfile.

    InputProfile → [Momentum, Dividend, LowVol, MultiFactor, CoveredCall]
    ↓
    Evalúa cada estrategia con optimización de parámetros
    ↓
    Retorna mejor estrategia + parámetros óptimos
    """
```

**Implementación:**
```python
def select_best_strategy(
    self,
    profile: InputProfile,
    data: pd.DataFrame,
) -> StrategyConfiguration:
    """
    Selecciona mejor estrategia basado en InputProfile.

    Proceso:
    1. Mapear objetivo_inversion a estrategia candidata
    2. Para cada estrategia, optimizar parámetros
    3. Evaluar con validación walk-forward
    4. Seleccionar mejor resultado ajustado por riesgo
    """
    # Map objective to candidate strategies
    candidates = self._get_candidate_strategies(profile.objetivo_inversion)

    # Optimize each candidate
    results = []
    for strategy in candidates:
        optimized = self._optimize_strategy(strategy, profile, data)
        validated = self._validate_walk_forward(optimized, data)
        results.append((strategy, validated))

    # Select best
    best = max(results, key=lambda x: self._score(x[1], profile.risk_tolerance))

    return StrategyConfiguration(
        strategy=best[0],
        params=best[1].params,
        expected_metrics=best[1].metrics,
    )
```

#### 6.7 Ensemble Methods

**Requisitos:**
```python
class EnsembleStrategy:
    """
    Combina múltiples estrategias para mejorar robustez.

    Métodos:
    - Bagging: Promedio de predicciones
    - Boosting: Secuencial con pesos
    - Stacking: Meta-model sobre predicciones
    """
```

#### 6.8 Strategy Combination

**Requisitos:**
```python
class StrategyCombiner:
    """
    Combina señales de múltiples estrategias.

    Métodos:
    - Voting: Mayoría de votos
    - Weighted: Peso por desempeño pasado
    - Correlation-adjusted: Ajustar por correlación
    """
```

---

## 5. FASE 7: MULTI-ACTIVO

**Duración:** 2 semanas
**Prioridad:** 🟢 BAJA
**Objetivo:** Soporte para Crypto y Forex

### 5.1 Semana 18: Data Infrastructure

| Tarea | Descripción | Archivo | Regla |
|-------|-------------|---------|-------|
| 7.1 | **Stocks data (25 años)** | `app/engines/data_engine/sources/ohlcv_sources.py` | - |
| 7.2 | **ETFs data** | `app/engines/data_engine/sources/etf_sources.py` | - |
| 7.3 | **Crypto data** | `app/engines/data_engine/sources/crypto_sources.py` | - |
| 7.4 | **Forex data** | `app/engines/data_engine/sources/forex_sources.py` | - |

### 5.2 Semana 19: Asset-Specific Strategies

| Tarea | Descripción | Archivo | Regla |
|-------|-------------|---------|-------|
| 7.5 | **Dividendos para stocks/ETFs** | `app/strategies/dividend/` | Berkin #30 |
| 7.6 | **Momentum para crypto** | `app/strategies/crypto_momentum/` | Gray & Vogel |
| 7.7 | **Carry trade para forex** | `app/strategies/fx_carry_trade/` | Ilmanen #259 |

---

## 6. BRECHAS CRÍTICAS POR CATEGORÍA

### 6.1 Trading Rules - Reglas Específicas Pendientes

#### Ernest Chan - Algorithmic Trading (26 reglas)

| # | Regla | Estado | Tarea |
|---|-------|--------|-------|
| 1 | No look-ahead bias | ❓ | [6.1] Point-in-time database |
| 2 | Point-in-time database | ❌ NO | **FASE 5.1** |
| 3 | Slippage realista | ✅ | Verificar en FASE 5.7 |
| 4 | Comisiones completas | ✅ | Verificar en FASE 5.6 |
| 5 | Survivorship bias correction | ❌ NO | **FASE 5.2** |
| 6 | No optimizar en todo dataset | ❓ | [5.9] Walk-forward validation |
| 7 | Sharpe ratio correcto | ✅ | Verificado |
| 8 | Sharpe > 1.0 threshold | ❌ NO | Agregar validador |
| 9 | Max drawdown correcto | ✅ | Verificado |
| 10 | Max DD < 25% rechazo | ❌ NO | Agregar validador |
| 11 | Max 2% riesgo por trade | ✅ | Verificado |
| 12 | Kelly Criterion | ✅ | Verificado |
| 13 | SIEMPRE usar stop-loss | ✅ | Verificado |
| 14 | Limitar correlación | ❌ NO | Agregar validador |
| 15 | Circuit breaker 5% diario | ❌ NO | **FASE 5: Kill switches** |
| 16 | Slippage como función de volatilidad | ❓ | **FASE 5.7** |
| 17 | Bid-ask spread obligatorio | ❌ NO | **FASE 5.7** |
| 18 | Commission impact < 15% | ❌ NO | **FASE 5.6** |
| 19 | Bollinger Bands señales | ✅ | Verificado |
| 20 | Momentum 12 meses lookback | ❓ | Verificar implementación |
| 21 | Pairs trading cointegración | ✅ | Verificado |
| 22 | No HFT sin co-location | ❌ NO | Agregar validador de latencia |
| 23 | Half-life < 1 año | ❌ NO | Agregar validador |
| 24 | Hurst exponent | ❌ NO | Agregar a mean reversion |
| 25 | Stationarity test ADF | ❌ NO | Agregar a mean reversion |
| 26 | Calmar ratio > 1.0 | ✅ | Verificado |

**Tareas pendientes - Ernest Chan:**
- [ ] **Tarea EC-01:** Implementar Point-in-time database (FASE 5.1)
- [ ] **Tarea EC-02:** Implementar Survivorship bias correction (FASE 5.2)
- [ ] **Tarea EC-03:** Validar 70/30 train/test split
- [ ] **Tarea EC-04:** Agregar validador Sharpe > 1.0
- [ ] **Tarea EC-05:** Agregar validador Max DD < 25%
- [ ] **Tarea EC-06:** Agregar limitador de correlación
- [ ] **Tarea EC-07:** Implementar Circuit breaker 5% diario (FASE 5)
- [ ] **Tarea EC-08:** Verificar slippage como función de volatilidad (FASE 5.7)
- [ ] **Tarea EC-09:** Verificar bid-ask spread incluido (FASE 5.7)
- [ ] **Tarea EC-10:** Validar commission impact < 15% (FASE 5.6)
- [ ] **Tarea EC-11:** Agregar validador de latencia HFT
- [ ] **Tarea EC-12:** Agregar validador half-life < 1 año
- [ ] **Tarea EC-13:** Agregar Hurst exponent a mean reversion
- [ ] **Tarea EC-14:** Agregar stationarity test ADF a mean reversion

#### Robert Carver - Systematic Trading (10 reglas)

| # | Regla | Estado | Tarea |
|---|-------|--------|-------|
| 45 | Volatility Targeting | ✅ | Verificado |
| 46 | Instrument Diversification | ❌ NO | Agregar validador |
| 47 | Simple momentum signal | ✅ | Verificado |
| 48 | Fixed timestamp trading | ❌ NO | Agregar a execution |
| 49 | Handcrafted signals | ❓ | Verificar implementación |
| 50 | Decay factor 0.94 | ❌ NO | Agregar a EWMA calculations |
| 51 | Handcrafted portfolio weights | ✅ | **IMPLEMENTADO** |
| 52 | Risk Parity weights | ✅ | Verificado |
| 53 | Trading costs completos | ✅ | **FASE 5.6** |
| 54 | Walk-forward validation | ✅ | **FASE 5.9** |
| 55 | Robustez > Performance | ❌ NO | **FASE 5.10, 5.11** |

**Tareas pendientes - Robert Carver:**
- [ ] **Tarea RC-01:** Agregar validador Instrument Diversification max 25%
- [ ] **Tarea RC-02:** Implementar Fixed timestamp trading
- [ ] **Tarea RC-03:** Verificar handcrafted signals
- [ ] **Tarea RC-04:** Agregar decay factor 0.94 a EWMA
- [ ] **Tarea RC-05:** Verificar Walk-forward validation (FASE 5.9)
- [ ] **Tarea RC-06:** Implementar Overfitting detection (FASE 5.10)
- [ ] **Tarea RC-07:** Implementar Regime detection (FASE 5.11)

#### John Hull - Risk Management (10 reglas)

| # | Regla | Estado | Tarea |
|---|-------|--------|-------|
| 56 | Kill switch obligatorio | ✅ | **IMPLEMENTADO** |
| 57 | Risk overrides alpha | ❌ NO | Agregar a risk engine |
| 58 | Value at Risk (VaR) | ✅ | **IMPLEMENTADO** |
| 59 | Expected Shortfall | ✅ | **IMPLEMENTADO** |
| 60 | Position limits | ✅ | **IMPLEMENTADO** |
| 61 | Greeks monitoring | ❌ NO | Agregar a options |
| 62 | Stress testing | ✅ | **IMPLEMENTADO** |
| 63 | Volatility targeting | ✅ | Verificado |
| 64 | Correlation stress test | ❌ NO | Agregar a risk engine |
| 65 | Circuit breaker | ✅ | **IMPLEMENTADO** |

**Tareas pendientes - John Hull:**
- [ ] **Tarea JH-01:** Implementar Risk overrides alpha
- [ ] **Tarea JH-02:** Implementar Greeks monitoring para options
- [ ] **Tarea JH-03:** Implementar Correlation stress test

#### Markowitz - Portfolio Selection (15 reglas)

| # | Regla | Estado | Tarea |
|---|-------|--------|-------|
| 66 | Matriz covarianza 252 días | ✅ | **IMPLEMENTADO** |
| 67 | Mean-Variance Optimization | ✅ | **IMPLEMENTADO** |
| 68 | Long-only constraints | ✅ | Verificado |
| 69 | Suma unitaria hard constraint | ✅ | Verificado |
| 70 | Diversificación forzada | ✅ | Verificado |
| 71 | Frontera eficiente | ❌ NO | **FASE 6.5** |
| 72 | Max Sharpe Portfolio | ✅ | Verificado |
| 73 | Regularización L2 | ⚠️ | Expandir implementación |
| 74 | Rebalanceo por desviación | ❌ NO | **FASE 6** |
| 75 | Shrinkage Ledoit-Wolf | ❌ NO | Agregar |
| 76 | Beta constraints | ❌ NO | Agregar |
| 77 | Transaction cost penalty | ❌ NO | Agregar |
| 78 | Risk Parity fallback | ✅ | **IMPLEMENTADO** |
| 79 | Correlation alert | ✅ | **IMPLEMENTADO** |
| 80 | Input sanitation | ✅ | **IMPLEMENTADO** |

**Tareas pendientes - Markowitz:**
- [ ] **Tarea MK-01:** Implementar Efficient frontier completa (FASE 6.5)
- [ ] **Tarea MK-02:** Expandir Regularización L2
- [ ] **Tarea MK-03:** Implementar Rebalanceo por desviación (FASE 6)
- [ ] **Tarea MK-04:** Implementar Shrinkage Ledoit-Wolf
- [ ] **Tarea MK-05:** Implementar Beta constraints
- [ ] **Tarea MK-06:** Implementar Transaction cost penalty

### 6.2 High Performance Python - Reglas Pendientes

#### High Performance Python (20 reglas)

| # | Regla | Estado | Tarea |
|---|-------|--------|-------|
| 151 | Vectorización NumPy/Pandas | ⚠️ | **FASE 5: Verificar** |
| 152 | No iterrows() | ⚠️ | **FASE 5: Verificar** |
| 153 | Groupby agregaciones | ✅ | Verificado |
| 154 | Missing data eficiente | ✅ | Verificado |
| 155 | Numba hot paths | ✅ | **IMPLEMENTADO** |
| 156 | Memory efficiency | ❌ NO | **FASE 5: Verificar** |
| 157 | Multiprocessing backtest | ❌ NO | Agregar |
| 158 | Caching LRU | ❌ NO | Agregar |
| 159 | Resampling eficiente | ✅ | Verificado |
| 160 | Time shifts eficientes | ✅ | Verificado |

**Tareas pendientes - High Performance:**
- [ ] **Tarea HP-01:** **Verificar vectorización en todo el codebase** (FASE 5)
- [ ] **Tarea HP-02:** Eliminar todos los iterrows() prohibidos
- [ ] **Tarea HP-03:** Verificar memory efficiency (tipos correctos)
- [ ] **Tarea HP-04:** Implementar multiprocessing backtest
- [ ] **Tarea HP-05:** Agregar caching LRU para cálculos costosos

---

## 7. REGLAS ESPECÍFICAS PENDIENTES

### 7.1 Por Prioridad de Implementación

#### 🔴 PRIORIDAD ALTA (15 tareas)

| # | Tarea | Categoría | Archivo | Regla |
|---|-------|-----------|---------|-------|
| 1 | **Point-in-time database** | Backtesting | `point_in_time_database.py` | Chan #2 |
| 2 | **Survivorship bias correction** | Backtesting | `survivorship_bias_corrector.py` | Chan #5 |
| 3 | **Robust 25-year backtesting** | Backtesting | `robust_backtester.py` | Carver #54 |
| 4 | **Circuit breaker 5% diario** | Risk | `circuit_breaker.py` | Hull, Chan #15 |
| 5 | **Slippage modeling** | Execution | `slippage_model.py` | Chan #16 |
| 6 | **Commission impact < 15%** | Execution | `transaction_cost.py` | Chan #18 |
| 7 | **Avellaneda-Stoikov MM** | Execution | `avellaneda_stoikov.py` | Stoikov #6 |
| 8 | **Order Flow Imbalance Enhanced** | Execution | `ofi_predictor.py` | Aldridge #2 |
| 9 | **Vectorization verification** | Performance | - | High Performance |
| 10 | **Walk-forward validation** | Validation | `walk_forward.py` | Pardo #54 |
| 11 | **Overfitting detection** | Validation | `overfitting_detector.py` | Hastie #96 |
| 12 | **Regime detection** | Validation | `regime_detector.py` | Ilmanen #254 |
| 13 | **Grid search optimization** | Optimization | `grid_search.py` | General |
| 14 | **Bayesian optimization** | Optimization | `bayesian_optimizer.py` | General |
| 15 | **Pareto front optimization** | Optimization | `multi_objective.py` | General |

#### 🟡 PRIORIDAD MEDIA (20 tareas)

| # | Tarea | Categoría | Archivo | Regla |
|---|-------|-----------|---------|-------|
| 16 | **Sharpe > 1.0 threshold** | Validation | `strategy_validator.py` | Chan #8 |
| 17 | **Max DD < 25% rechazo** | Validation | `strategy_validator.py` | Chan #10 |
| 18 | **Limitar correlación** | Risk | `correlation_limiter.py` | Chan #14 |
| 19 | **Fixed timestamp trading** | Execution | `execution_scheduler.py` | Carver #48 |
| 20 | **Decay factor 0.94** | Indicators | `ewma_calculator.py` | Carver #50 |
| 21 | **Instrument Diversification** | Risk | `diversification_checker.py` | Carver #46 |
| 22 | **Risk overrides alpha** | Risk | `risk_overrider.py` | Hull #57 |
| 23 | **Greeks monitoring** | Risk | `greeks_monitor.py` | Hull #61 |
| 24 | **Correlation stress test** | Risk | `correlation_stress.py` | Hull #64 |
| 25 | **Efficient frontier** | Portfolio | `efficient_frontier.py` | Markowitz #71 |
| 26 | **Rebalanceo por desviación** | Portfolio | `rebalancer.py` | Markowitz #74 |
| 27 | **Shrinkage Ledoit-Wolf** | Portfolio | `covariance_shrinkage.py` | Markowitz #75 |
| 28 | **Beta constraints** | Portfolio | `beta_constraint.py` | Markowitz #76 |
| 29 | **Fundamental Law IR=IC×√BR** | Metrics | `fundamental_law.py` | Grinold #116 |
| 30 | **Ensemble methods** | Ensemble | `ensemble.py` | General |
| 31 | **Strategy combination** | Ensemble | `strategy_combiner.py` | General |
| 32 | **Half-life < 1 año** | Validation | `half_life_checker.py` | Chan #23 |
| 33 | **Hurst exponent** | Indicators | `hurst_calculator.py` | Chan #24 |
| 34 | **Stationarity test ADF** | Indicators | `stationarity_test.py` | Chan #25 |
| 35 | **Multiprocessing backtest** | Performance | `parallel_backtester.py` | High Performance |

#### 🟢 PRIORIDAD BAJA (10 tareas)

| # | Tarea | Categoría | Archivo | Regla |
|---|-------|-----------|---------|-------|
| 36 | **AMM/Dex Trading** | Crypto | `amm_trader.py` | Steffensen |
| 37 | **FX Intermarket Signals** | FX | `intermarket_signals.py` | Laidi #1 |
| 38 | **Carry Trade para Forex** | FX | `carry_trade.py` | Ilmanen #259 |
| 39 | **Crypto Momentum** | Crypto | `crypto_momentum.py` | Gray & Vogel |
| 40 | **No HFT sin co-location** | Validation | `latency_validator.py` | Chan #22 |
| 41 | **Bid-ask bounce filter** | Execution | `bid_ask_bounce.py` | Harris #208 |
| 42 | **Timing cost calculation** | Execution | `timing_cost.py` | Harris #209 |
| 43 | **Almgren-Chriss impact** | Execution | `almgren_chriss.py` | #21 |
| 44 | **Caching LRU** | Performance | `cache.py` | High Performance |
| 45 | **Memory efficiency** | Performance | `memory_optimizer.py` | High Performance |

---

## 8. PLAN DE TRABAJO SEMANAL

### 8.1 Semana 1: Backtesting Core

**Lunes - Martes:**
- [ ] Implementar `RobustBacktester` base class
- [ ] Agregar validación de calidad de datos
- [ ] Implementar detección de gaps

**Miércoles - Jueves:**
- [ ] Implementar `SurvivorshipBiasCorrector`
- [ ] Agregar descarga de delisted stocks
- [ ] Implementar ajuste de retornos

**Viernes:**
- [ ] Implementar `CorporateActionsHandler`
- [ ] Agregar manejo de splits
- [ ] Tests para backtesting core

### 8.2 Semana 2: Execution + Validation

**Lunes - Martes:**
- [ ] Implementar `SlippageModel`
- [ ] Agregar vol-adjusted slippage
- [ ] Verificar `TransactionCostCalculator`

**Miércoles - Jueves:**
- [ ] Implementar `MarketImpactModel` (Almgren-Chriss)
- [ ] Verificar `WalkForwardValidator`
- [ ] Implementar `OverfittingDetector`

**Viernes:**
- [ ] Implementar `RegimeDetector`
- [ ] Tests para validation

### 8.3 Semana 3: Dividendos + Data Quality

**Lunes - Martes:**
- [ ] Implementar `DividendReinvestor`
- [ ] Agregar reinversión automática
- [ ] Implementar `PointInTimeDatabase`

**Miércoles - Jueves:**
- [ ] Verificar vectorización en todo el codebase
- [ ] Eliminar for loops prohibidos
- [ ] Agregar multiprocessing backtest

**Viernes:**
- [ ] Tests completos para FASE 5
- [ ] Documentación de backtesting engine

### 8.4 Semana 4: Optimization

**Lunes - Martes:**
- [ ] Implementar `GridSearchOptimizer`
- [ ] Implementar `RandomSearchOptimizer`
- [ ] Tests para grid/random search

**Miércoles - Jueves:**
- [ ] Implementar `BayesianOptimizer` (Optuna)
- [ ] Agregar visualización de resultados
- [ ] Tests para Bayesian optimization

**Viernes:**
- [ ] Implementar `MultiObjectiveOptimizer`
- [ ] Implementar Pareto front
- [ ] Tests para multi-objective

### 8.5 Semana 5: Auto-Selection + Ensemble

**Lunes - Martes:**
- [ ] Implementar `StrategySelector` para InputProfile
- [ ] Agregar evaluación de candidatos
- [ ] Tests para strategy selection

**Miércoles - Jueves:**
- [ ] Implementar `EnsembleStrategy`
- [ ] Implementar `StrategyCombiner`
- [ ] Tests para ensemble

**Viernes:**
- [ ] Tests completos para FASE 6
- [ ] Documentación de optimization

### 8.6 Semana 6: Multi-Activo (Opcional)

**Lunes - Martes:**
- [ ] Implementar `CryptoDataSource`
- [ ] Implementar `ForexDataSource`
- [ ] Tests para data sources

**Miércoles - Jueves:**
- [ ] Implementar `CryptoMomentumStrategy`
- [ ] Implementar `FXCarryTradeStrategy`
- [ ] Tests para estrategias multi-activo

**Viernes:**
- [ ] Tests completos para FASE 7
- [ ] Documentación de multi-activo

---

## 9. MÉTRICAS DE ÉXITO

### 9.1 Métricas de Implementación

| Métrica | Valor Actual | Valor Objetivo | Fase |
|---------|-------------|----------------|------|
| **Cumplimiento total** | 43% | 70% | Todas |
| **Backtesting & Validation** | 85% | 95% | FASE 5 |
| **Execution Quality** | 50% | 80% | FASE 5 |
| **Optimization** | 20% | 70% | FASE 6 |
| **Performance** | 40% | 70% | FASE 5 |
| **Crypto/FX** | 0% | 50% | FASE 7 |

### 9.2 Tests y Cobertura

| Métrica | Valor Actual | Valor Objetivo |
|---------|-------------|----------------|
| **Tests passing** | 1013 | 1500+ |
| **Cobertura** | ~80% | 90%+ |
| **Tests de integración** | ? | 100+ |
| **Tests de regresión** | ? | 50+ |

---

## 10. CONCLUSIÓN

### 10.1 Resumen de Tareas

| Fase | Tareas | Duración | Prioridad |
|------|--------|----------|-----------|
| **FASE 5** | 15 tareas | 3 semanas | 🔴 ALTA |
| **FASE 6** | 8 tareas | 3 semanas | 🟡 MEDIA |
| **FASE 7** | 7 tareas | 2 semanas | 🟢 BAJA |
| **TOTAL** | **30 tareas** | **8 semanas** | - |

### 10.2 Orden de Implementación Recomendado

1. **FASE 5 (Semana 1-3):** Backtesting Engine
   - Crítico para validar todas las estrategias
   - Base para optimización de parámetros

2. **FASE 6 (Semana 4-6):** Optimización
   - Encuentra mejores parámetros para InputProfile
   - Habilita auto-selección de estrategias

3. **FASE 7 (Semana 7-8):** Multi-Activo
   - Features especializadas para Crypto y FX
   - No crítico para equities

### 10.3 Próximos Pasos Inmediatos

**Esta semana:**
1. Implementar `RobustBacktester` base class
2. Implementar `SurvivorshipBiasCorrector`
3. Verificar `TransactionCostCalculator` completeness
4. Implementar `SlippageModel` con vol-adjustment

**Próxima semana:**
1. Implementar `MarketImpactModel` (Almgren-Chriss)
2. Implementar `OverfittingDetector`
3. Implementar `RegimeDetector`
4. Verificar vectorización en codebase

**En 3 semanas:**
1. FASE 5 completa
2. Backtesting robusto para 25 años
3. Execution quality mejorada
4. Validation completa (walk-forward, overfitting, regime)

---

**Fin del Plan de Ejecución**

**Fecha de creación:** 31 de Enero de 2026
**Próxima revisión:** 14 de Febrero de 2026 (post FASE 5)
