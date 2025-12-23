# 🚀 Plan Maestro: AlgoTrading Next Level (Consolidado v2.1)

**Versión**: 2.1 - Consolidado + PHASE 0: Capital Viability & Integration Audit
**Fecha**: 2025-12-23
**Estado**: FASE 0 CRÍTICA + Fases 1-3 completadas

---

## 📋 Resumen Ejecutivo

Este documento consolida CUATRO planes en uno:

1. **Plan Maestro Original**: Arquitectura de 17 módulos inteligentes
2. **Quant Plan (Awesome-Quant Integration)**: 7 librerías validadas para analytics, reporting y optimización
3. **Refactored Plan (Elite Libraries)**: Integración de librerías élite para infraestructura y ejecución
4. **PHASE 0: Capital-Aware Integration Audit** (NUEVO): Hardening crítico contra pérdida de capital en cuentas pequeñas ($10k-$30k)

**Objetivo**:
- Transformar el sistema en una plataforma institucional SEGURA
- Garantizar que el sistema correctamente **rechaza operaciones imposibles** antes de dañar capital
- Validar interacciones de módulos bajo restricción de capital
- Implementar gates fail-fast que previenen ruin de cuentas pequeñas

---

## ⚠️ PHASE 0: System Reliability Hardening & Capital Viability (CRÍTICO - PREREQUISITO)

**Timeline**: 2-3 semanas (ANTES de cualquier deploy live)
**Objetivo**: Garantizar que sistema no mata cuentas por integración faulty o objetivo imposible
**Capital Target**: $10k-$30k (máxima vulnerabilidad)
**Riesgo de No Hacer**: 30-50% pérdida de capital en 3-6 meses

### FASE 0.1: Fail-Fast Gates (Semana 1)

#### T0.1.1: Unreachable Profit Goal Detection Engine
**Módulos Afectados**: Core Config → Risk Engine → Execution Engine

**Qué hace**:
- Calcula si `NET_PROFIT_GOAL_MONTHLY` es alcanzable dado:
  - `CAPITAL_INICIAL`
  - `TAX_RATE`
  - `commission_per_trade`
  - `expected_alpha_per_signal`

**Fórmula de Viabilidad**:
```
required_monthly_alpha = (goal / (1 - tax_rate)) + (commission_per_trade * expected_trades_per_month)
capital_available_for_alpha = capital_inicial * (1 - max_exposure)
alpha_as_pct_of_capital = required_monthly_alpha / capital_available_for_alpha

IF alpha_as_pct_of_capital > threshold (e.g., 10%):
  DISABLE_TRADING
  LOG: "Profit goal unreachable; required {alpha_pct}% alpha vs attainable ~2-3%"
  RETURN recommended_action: INCREASE_CAPITAL or REDUCE_GOAL
```

**Implementación**: `app/services/capital_viability_gate.py`
- Clase `CapitalViabilityValidator`
- Método `validate_profit_goal(capital, goal, tax, commission, expected_alpha)`
- Retorna: `(is_viable: bool, reason: str, recommendation: str)`

**Tests (Mandatory)**:
```python
# test_capital_viability_gates.py
def test_unreachable_goal_10k_capital_500_monthly():
  # Goal es $500/month en $10k = UNREACHABLE
  # Sistema debe rechazar

def test_reachable_goal_100k_capital_500_monthly():
  # Goal es $500/month en $100k = REACHABLE (~0.5% monthly)
  # Sistema debe aceptar

def test_goal_exactly_at_threshold():
  # Test límite
```

**Status**: 🔴 NOT IMPLEMENTED

---

#### T0.1.2: Commission Dominance Detection
**Módulos Afectados**: Execution Engine → Risk Engine → Strategy Engines

**Qué hace**:
- Detecta en TIEMPO REAL cuando `total_cost_per_cycle > estimated_alpha`
- Monitorea régimen de slippage (volatility-dependent)
- Rechaza trade si cost exceeds alpha threshold

**Implementación**: `app/services/execution_cost_analyzer.py`
- Clase `ExecutionCostAnalyzer`
- Método `analyze_trade_cost(signal, market_data, portfolio) → TradeViability`
- Monitorea `slippage_history` (rolling 30-day)
- Detecta cost regime shifts

**Detection Logic**:
```python
base_slippage = 0.1%  # Normal market
current_slippage = f(volatility)  # Increases with VIX

IF volatility > VIX_70:
  slippage = base_slippage * 4  # Can 4x in stress

cost_per_trade = commission + (slippage * position_size)
expected_alpha_per_trade = signal.expected_return * position_size

IF cost > expected_alpha * 0.5:  # Cost > 50% of alpha
  REJECT_TRADE
  LOG: "Cost regime shift: slippage {new_slippage}% > threshold"
```

**Tests (Mandatory)**:
```python
def test_trade_rejected_when_cost_exceeds_alpha():
  # Normal slippage 0.1%, commission $15 = Cost $30
  # Expected alpha = $50
  # ACCEPT

  # High vol: slippage 0.4%, commission $15 = Cost $80
  # Expected alpha = $100
  # REJECT (cost is 80% of alpha, exceeds threshold)

def test_cost_regime_detection_volatility_spike():
  # VIX jumps from 20 to 40
  # System detects slippage doubling
  # Rejects trades until VIX normalizes
```

**Status**: 🔴 NOT IMPLEMENTED

---

#### T0.1.3: "Doing Nothing Is Optimal" Gate
**Módulos Afectados**: Strategy Engines → Execution Engine → Portfolio Engine

**Qué hace**:
- Compara: `expected_alpha_per_trade` vs. `risk_free_rate + execution_cost`
- Si risk-free > expected active return, sistema rechaza trades

**Implementación**: `app/services/opportunity_cost_validator.py`
- Clase `OpportunityCostValidator`
- Método `is_active_trading_worth_it(capital, expected_alpha, risk_free_rate) → bool`
- Retorna `False` si passive > active

**Logic**:
```python
risk_free_monthly = capital * (risk_free_rate / 12)  # ~0.33% on $10k
expected_active_monthly = expected_alpha * expected_trades_per_month - commissions

IF expected_active_monthly < risk_free_monthly:
  HOLD_CASH
  LOG: "Passive return {rf_monthly} > active return {active_monthly}"
```

**Tests (Mandatory)**:
```python
def test_hold_cash_when_rfr_exceeds_strategy_alpha():
  capital = 12000
  risk_free = 0.04  # 4% annually = $40/month
  strategy_alpha = $25/month

  # System should HOLD_CASH

def test_trade_when_alpha_exceeds_rfr():
  # Strategy alpha $60/month > $40 risk-free
  # System should TRADE
```

**Status**: 🔴 NOT IMPLEMENTED

---

### FASE 0.2: Capital-Constrained Module Gating (Semana 1-2)

#### T0.2.1: Learning Engine Capital Gate
**Módulos Afectados**: Strategy Engines → Learning Engine → Drift Detector

**Qué hace**:
- **No inicializa** Learning Engine si `capital < threshold`
- Learning tiene costo implícito (compute, feature extraction, retraining)
- En $15k-$20k, costo learning > alpha generado

**Implementación**: `app/strategies/momentum_modular/learning/learning_capital_gate.py`
```python
class LearningCapitalGate:
  MIN_CAPITAL_FOR_LEARNING = Decimal("25000")  # $25k minimum
  LEARNING_COST_PER_MONTH = Decimal("50")  # Estimated cost

  def should_enable_learning(self, capital: Decimal, expected_alpha: Decimal) -> bool:
    if capital < self.MIN_CAPITAL_FOR_LEARNING:
      return False  # Don't load learning engine

    monthly_alpha = expected_alpha / 12
    if self.LEARNING_COST_PER_MONTH > monthly_alpha * 0.3:
      return False  # Cost is >30% of alpha, not worth it

    return True
```

**Where to Apply**:
- `ModularMomentumStrategy.__init__()`: Check before lazy-loading learning engine
- `DriftDetector.check()`: Return "disable" recommendation if capital too low
- `LearningUpdater.update_learning_systems()`: Skip update if below threshold

**Tests (Mandatory)**:
```python
def test_learning_not_initialized_capital_15k():
  capital = Decimal("15000")
  strategy = ModularMomentumStrategy(config)

  # System should NOT initialize learning engine
  assert strategy.learning_engine is None

def test_learning_initialized_capital_30k():
  capital = Decimal("30000")
  # Learning should initialize if enabled in config

def test_drift_detector_disables_learning_small_capital():
  # If drift detected on $20k account, recommend "disable"
  # instead of "retrain"
```

**Status**: 🔴 NOT IMPLEMENTED

---

#### T0.2.2: Synthetic Data & LLM Disabling
**Módulos Afectados**: Learning Engine → Data Augmentation

**Qué hace**:
- Disables synthetic data generation if capital < $30k (expensive)
- Disables LLM-based signal augmentation if capital < $50k

**Implementación**: `app/services/expensive_module_gate.py`
```python
class ExpensiveModuleGate:
  MIN_CAPITAL_FOR_SYNTHETIC = Decimal("30000")
  MIN_CAPITAL_FOR_LLM = Decimal("50000")

  def should_enable_synthetic_data(self, capital: Decimal) -> bool:
    return capital >= self.MIN_CAPITAL_FOR_SYNTHETIC

  def should_enable_llm_signals(self, capital: Decimal) -> bool:
    return capital >= self.MIN_CAPITAL_FOR_LLM
```

**Status**: 🔴 NOT IMPLEMENTED

---

### FASE 0.3: Integration Testing Under Capital Stress (Semana 2-3)

#### T0.3.1: Joint Strategy Lethality Test
**Módulos Afectados**: Portfolio Engine → Execution Engine → Risk Engine

**Test Name**: `test_integration_joint_strategy_execution_small_capital`

**Scenario**:
- Capital: $20k
- Momentum: 60% ($12k), MeanReversion: 25% ($5k), Pairs: 15% ($3k)
- Both Momentum AND MeanReversion generate signals simultaneously
- Execution engine must handle **sequential execution** with realistic cost escalation

**What to Verify**:
```python
# Step 1: Momentum signal for AAPL (pending)
# Step 2: MeanReversion signal for MSFT (pending)
# Step 3: Execute in sequence, measuring cumulative slippage

# Expected:
# Trade 1 slippage: 0.15% ($30)
# Trade 2 slippage: 0.20% ($40) - increased due to market impact
# Total: $70 cost

# NOT: Both trades slipped at 0.15% independently ($60)

# Verify: Portfolio state matches risk engine expectations
# Verify: Joint exposure = sum of allocations, not exceeding 85%
```

**Status**: 🔴 NOT IMPLEMENTED

**File Location**: `tests/integration/validation/test_capital_stress_joint_strategy.py`

---

#### T0.3.2: Data Staleness + Learning Damage Test
**Modules Affected**: Data Engine → Strategy Engine → Learning Engine

**Test Name**: `test_integration_stale_data_learning_damage`

**Scenario**:
- Data feed 5 minutes behind real market
- Strategy generates signal based on lagged RSI
- Learning engine trains on stale features
- Drift detector should **immediately flag & disable** learning

**Verification**:
```python
def test_stale_data_disables_learning():
  # Data timestamp older than current_time - 300s
  # Learning engine should NOT initialize
  # OR already-loaded engine should disable itself

  # Expected log: "Stale data detected; disabling learning engine"
```

**Status**: 🔴 NOT IMPLEMENTED

---

#### T0.3.3: Risk Escalation Atomicity Test
**Modules Affected**: Risk Engine → Execution Engine → Signal Queue

**Test Name**: `test_integration_risk_escalation_signal_atomicity`

**Scenario**:
```
T=0ms: Risk Level = LOW
       Momentum generates 5 BUY signals (queued)

T=100ms: First 2 signals execute
         Portfolio equity drops 2% (unlucky slippage)

T=150ms: Risk Level = CRITICAL (drawdown limit breach)
         Remaining 3 signals should be REJECTED ATOMICALLY
         NOT partially executed
```

**Verification**:
- All pending signals rejected when risk escalates
- No unhedged positions created
- Log entry for each rejected signal

**Status**: 🔴 NOT IMPLEMENTED

---

#### T0.3.4: Rebalancing + Pending Trades Test
**Modules Affected**: Portfolio Engine → Execution Engine

**Test Name**: `test_integration_rebalancing_pending_trades`

**Scenario**:
- Momentum allocation at 65% (over 60% target)
- Rebalancing triggered: reduce momentum to 60%
- Momentum has 3 pending buy signals
- System must decide: execute-then-rebalance OR rebalance-then-reject

**Verification**:
- Pending queue processed atomically vs. rebalancing decision
- Portfolio state consistent with risk engine expectations

**Status**: 🔴 NOT IMPLEMENTED

---

#### T0.3.5: Currency Hedging Cost > Alpha Test
**Modules Affected**: Portfolio Engine → Risk Engine

**Test Name**: `test_integration_currency_hedging_cost_dominance`

**Scenario**:
- Capital: $15k
- 30% in European stocks (EUR exposure)
- Currency hedging cost: 0.3% annually = $13.50/month
- Expected alpha on EUR holdings: $12/month
- **Hedging costs MORE than alpha**

**Verification**:
```python
def test_disable_hedging_when_cost_exceeds_alpha():
  # System detects: hedging_cost > alpha * 0.8
  # Automatically unhedges
  # Logs: "Hedging cost $13.50 > alpha $12; unhedging"
```

**Status**: 🔴 NOT IMPLEMENTED

---

### FASE 0.4: Deployment Safety Checklist (Antes de live)

#### Checkpoints de Validación

- [ ] T0.1.1: Unreachable goal detection implemented & tested
- [ ] T0.1.2: Commission dominance detection implemented & tested
- [ ] T0.1.3: Opportunity cost validator implemented & tested
- [ ] T0.2.1: Learning capital gate implemented & tested
- [ ] T0.2.2: Expensive module gating implemented & tested
- [ ] T0.3.1: Joint strategy test passing
- [ ] T0.3.2: Data staleness test passing
- [ ] T0.3.3: Risk atomicity test passing
- [ ] T0.3.4: Rebalancing test passing
- [ ] T0.3.5: Hedging cost test passing
- [ ] Documentation: All fail-fast conditions documented
- [ ] Production config: All capital gates configured per account size
- [ ] Alerts: System logs all gating decisions to audit trail

**Deployment Gate**:
- For accounts $10k-$25k: ALL PHASE 0 tests must pass
- For accounts $25k-$50k: T0.1, T0.2, T0.3 must pass
- For accounts >$50k: All tests strongly recommended

---

## 🎯 Arquitectura de los 17 Módulos (Con PHASE 0 Integration)

---

## 🎯 Arquitectura de los 17 Módulos

### Mapeo Librería-Módulo (17 Módulos + PHASE 0 Gates)

| Módulo | Nombre                          | Librerías Elite Asignadas                                       | Estado        | PHASE 0 Requirements |
| ------ | ------------------------------- | --------------------------------------------------------------- | ------------- | -------------------- |
| 1      | Data Engine                     | QuestDB (time-series), Pydantic (contracts)                     | ✅ Completado | T0.3.2: Staleness detection |
| 2      | Context Engine                  | statsmodels, arch (GARCH)                                       | ✅ Completado | (No changes needed)  |
| 3      | Strategy Engines                | TA-Lib (indicadores), Alphalens (factor analysis)               | ✅ Completado | T0.1.3: Opportunity cost gate |
| 4      | Learning Engine                 | Microsoft Qlib (DoubleEnsemble), FinRL (RL)                     | 🟡 75%        | **T0.2.1: Capital gate** (CRITICAL) |
| 5      | Portfolio Engine                | PyPortfolioOpt, Riskfolio-Lib (HRP/CVaR)                        | ✅ 95%        | T0.3.4: Rebalancing atomicity, T0.3.5: Hedging cost |
| 6      | Risk Engine                     | Riskfolio-Lib (CVaR), QuantStats (reporting)                    | ✅ Completado | T0.1.1: Profit goal validation, T0.3.3: Atomicity |
| 7      | Meta-Analyzer                   | QuantStats (HTML reports), empyrical-reloaded, pyfolio-reloaded | ⏳ Pendiente  | (Phase 4 work)       |
| 8      | Audit & Persistence             | Pydantic (contracts), QuestDB (storage)                         | ⏳ Pendiente  | Log all PHASE 0 gates |
| 9      | Execution Engine                | Zipline-Reloaded (backtesting core)                             | ⏳ Pendiente  | **T0.1.2: Cost analysis** (CRITICAL) |
| 10     | Monitoring & Dashboard          | QuantStats (visualizations)                                     | ⏳ Pendiente  | Display capital gates status |
| 11     | Explainability Engine (XAI)     | SHAP, LIME (ya integrado)                                       | ⏳ Pendiente  | (Phase 6 work)       |
| 12     | Synthetic Data Engine           | ydata-synthetic, sdv                                            | ⏳ Pendiente  | T0.2.2: Capital gate |
| 13     | Prediction Fusion Engine        | PyTorch, scikit-learn                                           | ⏳ Pendiente  | (Phase 6 work)       |
| 14     | Compliance & Governance         | Pydantic (validation)                                           | ⏳ Pendiente  | Validate capital gates per account |
| 15     | Knowledge Graph Engine          | networkx, neo4j                                                 | ⏳ Pendiente  | (Phase 6 work)       |
| 16     | Experimentation & Orchestration | Dagster (orchestration), MLflow                                 | ⏳ Pendiente  | Orchestrate PHASE 0 tests |
| 17     | Infrastructure Optimizer        | QuestDB (performance)                                           | ⏳ Pendiente  | (Phase 6 work)       |

---

## 📅 Cronograma Consolidado (20 Semanas - 7 Fases: 0 + 1-6)

### **FASE 0: System Reliability Hardening** (Semanas 1-3) 🔴 **CRÍTICO - PENDIENTE**

**Prerequisito obligatorio ANTES de cualquier deployment live**

| Subtarea | Timeline | Status | Priority |
|----------|----------|--------|----------|
| T0.1.1: Profit goal validator | Semana 1 | 🔴 | P0-CRITICAL |
| T0.1.2: Commission cost analyzer | Semana 1 | 🔴 | P0-CRITICAL |
| T0.1.3: Opportunity cost gate | Semana 1 | 🔴 | P0-CRITICAL |
| T0.2.1: Learning capital gate | Semana 1-2 | 🔴 | P0-CRITICAL |
| T0.2.2: Expensive module gates | Semana 2 | 🔴 | P0-MEDIUM |
| T0.3.1-T0.3.5: Integration tests | Semana 2-3 | 🔴 | P0-CRITICAL |
| T0.4: Safety checklist | Semana 3 | 🔴 | P0-CRITICAL |

**Outputs de PHASE 0**:
- ✅ `app/services/capital_viability_gate.py` (fail-fast validation)
- ✅ `app/services/execution_cost_analyzer.py` (cost regime detection)
- ✅ `app/services/opportunity_cost_validator.py` (passive vs active decision)
- ✅ `app/strategies/momentum_modular/learning/learning_capital_gate.py`
- ✅ 5x integration tests (joint strategy, staleness, risk atomicity, rebalancing, hedging)
- ✅ Updated Audit Trail logging for all gates
- ✅ Config file templates for capital size tiers

**Deployment Requirement**:
- ✅ All P0 tests passing
- ✅ No account < $10k can be deployed
- ✅ All gates logged and auditable
- ✅ Operator can see "WHY" trading was rejected

---

### **FASE 1: Fundamentos de Datos y Contexto** (Meses 1-3) ✅ **COMPLETADA**

**Objetivo**: Establecer la base de datos limpia y detección de régimen

#### Módulo 1: Data Engine ✅

**Librerías Elite Integradas**:

- ✅ **Pydantic 2.x**: Data contracts para validación (`app/core/contracts.py`)
- ✅ **QuestDB** (planificado): Time-series storage para ticks en vivo
- ✅ **Parquet**: Persistencia histórica

**Tareas Completadas**:

- [x] Normalización unificada de múltiples fuentes
- [x] Sistema de limpieza y validación
- [x] Sistema de versionado y caché distribuido
- [x] API unificada de acceso

**Stack Tecnológico**:

- `pandas`, `pandas_ta`, `yfinance`, `ccxt`, `alpha_vantage`
- `polars`, `pyarrow`, `duckdb` (ETL de alto rendimiento)
- `parquet`, `sqlite` (almacenamiento)
- **QuestDB** (pendiente migración)

#### Módulo 2: Context Engine ✅

**Librerías Elite Integradas**:

- ✅ **statsmodels**: Análisis estadístico, correlaciones
- ✅ **arch**: Modelos GARCH para volatilidad

**Tareas Completadas**:

- [x] Detección de régimen con HMM
- [x] Sistema de volatilidad adaptativa
- [x] Detección de correlaciones
- [x] Contexto macroeconómico

---

### **FASE 2: Strategy & Learning** (Meses 4-7) ✅ **COMPLETADA (100%)**

#### Módulo 3: Strategy Engines ✅ **100% completado**

**Librerías Elite Integradas**:

- ✅ **TA-Lib** (opcional): C-Wrapper para indicadores de baja latencia
- ✅ **Alphalens-reloaded**: Factor analysis e Information Coefficient (IC)
- ✅ **pandas-ta-classic**: Indicadores técnicos (ya integrado)

**Tareas Completadas**:

- [x] **3.1** Refactorizar estrategias existentes ✅
- [x] **3.2** Nuevas estrategias base ✅ (4/4: Breakout, TrendFollowing, Arbitrage, MeanReversion mejorado)
- [x] **3.3** Sistema de composición de estrategias ✅ (Ensembles)
- [x] **3.4** Integración con Learning Engine ✅ (parcialmente)
- [x] **3.5** Testing y validación ✅ (Walk-forward, stress testing, Monte Carlo)

**Integración Alphalens**:

- Factor analysis para validar poder predictivo de features
- Information Coefficient (IC) para medir calidad de factores
- Quantile analysis para performance por quintil

#### Módulo 4: Learning Engine 🟡 **75% completado**

**Librerías Elite Integradas**:

- ✅ **Microsoft Qlib**: DoubleEnsemble, pipeline completo ML
- ✅ **FinRL**: Reinforcement Learning framework profesional
- ✅ **stable-baselines3**: RL algorithms (ya integrado)

**Tareas Completadas**:

- [x] Sistema de learning para `momentum_modular` completo
- [x] **Drift Detection** ✅ (PSI, ADWIN, KS Test, MMD)
- [x] **Feature Importance** ✅ (SHAP, Permutation, Built-in, Correlation, Stability, Selection)
- [x] **Transfer Learning** ✅ (Market regime detection, pre-trained models)

**Integración Qlib** (pendiente):

- Pipeline completo: datos → features → modelos → backtesting
- DoubleEnsemble para robustez
- Validación temporal integrada

**Integración FinRL** (pendiente):

- Environments profesionales de trading
- State space más completo
- Risk-aware learning

---

### **FASE 3: Portfolio y Risk** (Meses 8-10) ✅ **NÚCLEO IMPLEMENTADO**

#### Módulo 5: Portfolio Engine ✅ **95% completado**

**Librerías Elite Integradas**:

- ✅ **PyPortfolioOpt**: Efficient Frontier, Risk Parity, Black-Litterman, HRP
- ✅ **Riskfolio-Lib**: CVaR, CDaR, EVaR optimization, HRP avanzado
- ✅ **optuna**: Optimización global (ya integrado)

**Tareas Completadas**:

- [x] Optimizadores: Markowitz, Risk Parity, Black-Litterman, Kelly Criterion ✅
- [x] Rebalancers dinámicos ✅
- [x] Meta-learners para asignación ✅
- [x] Currency Hedging Automático ✅
- [ ] Diversificación sector/país (pendiente)

**Integración PyPortfolioOpt**:

- Efficient Frontier (Markowitz)
- Minimum Volatility
- Maximum Sharpe Ratio
- Risk Parity
- Black-Litterman
- Hierarchical Risk Parity (HRP)

**Integración Riskfolio-Lib**:

- CVaR Optimization (Conditional Value at Risk)
- CDaR Optimization (Conditional Drawdown at Risk)
- EVaR Optimization (Entropic Value at Risk)
- Maximum Diversification
- Robust Portfolio (resistent to outliers)

#### Módulo 6: Risk Engine ✅

**Librerías Elite Integradas**:

- ✅ **Riskfolio-Lib**: VaR/CVaR avanzado
- ✅ **QuantStats**: Portfolio analytics y reporting
- ✅ **empyrical-reloaded**: Métricas estándar industria

**Tareas Completadas**:

- [x] VaR/CVaR calculados
- [x] Stress testing implementado
- [x] Exposición, drawdowns, correlaciones
- [x] Risk attribution y alert system

---

### **FASE 4: Análisis y Persistencia** (Meses 11-12) 🟡 **EN PROGRESO**

#### Módulo 7: Meta-Analyzer (Mejora) ⏳

**Librerías Elite Integradas**:

- ⏳ **QuantStats**: Portfolio analytics con HTML reports profesionales
- ⏳ **empyrical-reloaded**: Métricas estándar industria (Calmar, Stability, Tail Ratio)
- ⏳ **pyfolio-reloaded**: Portfolio y risk analytics, tearsheets

**Tareas Pendientes**:

- [ ] Expandir `BacktestMetaAnalyzer` con quantstats
- [ ] Agregar reportes HTML profesionales
- [ ] Análisis de estacionalidad
- [ ] Clustering avanzado
- [ ] Análisis de factores

**Integración QuantStats**:

- Reportes HTML profesionales automáticos
- 30+ métricas adicionales (Omega, Tail Ratio, Common Sense Ratio)
- Visualizaciones integradas (equity curves, drawdowns, monthly returns heatmaps)

**Integración empyrical-reloaded**:

- Métricas estándar: Calmar, Stability, Tail Ratio, Max Drawdown Duration
- Serenity Index, Excess Return, Recovery Factor Duration

**Integración pyfolio-reloaded**:

- Exposición por sector, estilo, factor
- Concentración de riesgo
- Drawdown analysis
- Rolling Sharpe
- Tearsheets completos

#### Módulo 8: Audit & Persistence Engine ⏳

**Librerías Elite Integradas**:

- ✅ **Pydantic 2.x**: Data contracts (ya integrado)
- ⏳ **QuestDB**: Time-series storage para audit trails
- ⏳ **MLflow**: Model registry y experiment tracking

**Tareas Pendientes**:

- [ ] Expandir `AuditTrail` con QuestDB
- [ ] Sistema de versionado de modelos (MLflow)
- [ ] Trazabilidad completa
- [ ] Reproducibilidad mejorada
- [ ] Data governance

---

### **FASE 5: Ejecución y Monitoreo** (Meses 13-14) ⏳

#### Módulo 9: Execution Engine ⏳

**Librerías Elite Integradas**:

- ⏳ **Zipline-Reloaded**: Reemplazar motor core de backtesting
- ⏳ **backtrader**: Framework completo (opcional, para trading real-time)

**Tareas Pendientes**:

- [ ] Refactorizar `SignalExecutionEngine` → `ExecutionEngine`
- [ ] Integrar Zipline-Reloaded como motor de backtesting core
- [ ] Optimización de ejecución (TWAP, VWAP)
- [ ] Gestión de slippage
- [ ] Latency optimization
- [ ] Simulación de ejecución

**Integración Zipline-Reloaded**:

- Pipeline system para feature engineering
- Backtesting optimizado específicamente para histórico
- Análisis de estrategias cuantitativas
- Reemplazo gradual de `SimpleBacktester` core

#### Módulo 10: Monitoring & Dashboard ⏳

**Librerías Elite Integradas**:

- ⏳ **QuantStats**: Visualizaciones profesionales
- ⏳ **Streamlit**: Dashboard (ya integrado)
- ⏳ **Plotly**: Interactive charts

**Tareas Pendientes**:

- [ ] Expandir dashboard con QuantStats visualizations
- [ ] Real-time P&L tracking
- [ ] Alertas automáticas
- [ ] Visualizaciones avanzadas
- [ ] Reporting automático
- [ ] Performance attribution

---

### **FASE 6: Inteligencia Avanzada e Infraestructura** (Meses 15-18) ⏳

#### Módulo 11: Explainability Engine (XAI) ⏳

**Librerías Elite Integradas**:

- ✅ **SHAP**: Feature importance (ya integrado)
- ⏳ **LIME**: Local interpretability
- ⏳ **interpret**: Model interpretability

#### Módulo 12: Synthetic Data Engine ⏳

**Librerías Elite Integradas**:

- ⏳ **ydata-synthetic**: GANs para datos sintéticos
- ⏳ **sdv**: Synthetic Data Vault
- ⏳ **PyTorch**: VAEs, Diffusion Models

#### Módulo 13: Prediction Fusion Engine ⏳

**Librerías Elite Integradas**:

- ✅ **PyTorch**: Deep learning (ya integrado)
- ✅ **scikit-learn**: ML models (ya integrado)
- ⏳ **Microsoft Qlib**: DoubleEnsemble para fusion

#### Módulo 14: Compliance & Governance ⏳

**Librerías Elite Integradas**:

- ✅ **Pydantic 2.x**: Data validation (ya integrado)
- ⏳ **Audit trails**: Sistema completo

#### Módulo 15: Knowledge Graph Engine ⏳

**Librerías Elite Integradas**:

- ⏳ **networkx**: Graph analysis
- ⏳ **neo4j**: Graph database
- ⏳ **graph-tool**: Advanced graph algorithms

#### Módulo 16: Experimentation & Orchestration ⏳

**Librerías Elite Integradas**:

- ⏳ **Dagster**: Data orchestration y pipelines
- ⏳ **MLflow**: Experiment tracking
- ⏳ **Prefect**: Workflow orchestration (alternativa)

**Integración Dagster**:

- Data pipelines para ETL
- Orchestration de backtests
- Dependency management
- Monitoring de pipelines

#### Módulo 17: Infrastructure Optimizer ⏳

**Librerías Elite Integradas**:

- ⏳ **QuestDB**: Optimización de time-series storage
- ⏳ **Performance monitoring**: Optimización continua

---

## 🔧 Data Contracts con Pydantic

### Estructura de Contratos

**Ubicación**: `app/contracts/` (nuevo)

**Contratos Principales**:

- `SignalContract`: Validación de señales entre StrategyEngine → RiskEngine → ExecutionEngine
- `MarketDataContract`: Validación de datos de mercado
- `OrderContract`: Validación de órdenes
- `PositionContract`: Validación de posiciones
- `PortfolioContract`: Validación de portfolio

**Flujo de Datos**:

```
StrategyEngine.generate_signals()
  → SignalContract.validate()
  → RiskEngine.validate_risk()
  → ExecutionEngine.execute()
  → OrderContract.validate()
```

---

## 📊 Migración de Persistencia (Data Engine)

### Modelo Híbrido

**Histórico**: Parquet files

- Datos históricos OHLCV
- Backtesting data
- Optimización de lectura

**Live Ticks**: QuestDB

- Time-series database optimizada
- Queries SQL rápidas
- Streaming data

**Migración**:

1. Mantener Parquet para histórico
2. Implementar QuestDB para live data
3. Sincronización automática
4. Fallback a Parquet si QuestDB no disponible

---

## 🎯 Compatibilidad Strategy Engines con Zipline/Qlib

### Modificaciones Base Strategy

**BaseStrategyEngine** debe ser compatible con:

- **Zipline**: Pipeline system para features
- **Qlib**: DoubleEnsemble y validación temporal

**Cambios Requeridos**:

- Método `get_zipline_pipeline()` para generar pipelines
- Método `get_qlib_features()` para feature extraction compatible
- Wrapper para compatibilidad dual

---

## 📦 Dependencias Consolidadas

### requirements.txt (Sección Elite Libraries)

```txt
# === ELITE LIBRARIES - QUANT PLAN ===
# Fase 1: Analytics & Reporting
quantstats>=0.0.62,<1.0.0              # Portfolio analytics with HTML reports
empyrical-reloaded>=0.5.0,<1.0.0       # Financial metrics (Calmar, Stability, etc)
pyfolio-reloaded>=0.9.5,<1.0.0         # Portfolio and risk analytics

# Fase 2: Optimization & Analysis
PyPortfolioOpt>=1.5.0,<2.0.0            # Efficient Frontier, Risk Parity, HRP
Riskfolio-Lib>=5.0.0,<6.0.0             # CVaR, CDaR, EVaR optimization
alphalens-reloaded>=0.4.0,<1.0.0        # Factor analysis and IC metrics
FinRL>=0.3.6,<1.0.0                     # Professional RL trading framework

# === ELITE LIBRARIES - REFACTORED PLAN ===
# Execution & Backtest
zipline-reloaded>=3.0.0,<4.0.0          # Backtesting core engine (replaces SimpleBacktester)

# Learning & Features
qlib>=0.9.0,<1.0.0                      # Microsoft Qlib (DoubleEnsemble, pipeline)
TA-Lib>=0.4.28,<1.0.0                   # C-Wrapper for low latency indicators (optional)

# Infrastructure
questdb>=7.0.0,<8.0.0                   # Time-series database for live ticks
dagster>=1.5.0,<2.0.0                   # Data orchestration and pipelines

# Data Contracts (ya integrado)
pydantic>=2.0.0,<3.0.0                  # Data contracts and validation
```

---

## 📈 Estimación de Impacto Consolidado

| Librería               | Módulo                | Impacto  | Esfuerzo | Timeline    | ROI        |
| ---------------------- | --------------------- | -------- | -------- | ----------- | ---------- |
| **QuantStats**         | Meta-Analyzer         | ALTO     | Bajo     | 2-3 días    | ⭐⭐⭐⭐⭐ |
| **empyrical-reloaded** | Meta-Analyzer         | ALTO     | Bajo     | 3-4 días    | ⭐⭐⭐⭐⭐ |
| **pyfolio-reloaded**   | Meta-Analyzer         | ALTO     | Medio    | 4-5 días    | ⭐⭐⭐⭐⭐ |
| **PyPortfolioOpt**     | Portfolio Engine      | MUY ALTO | Medio    | 1-2 semanas | ⭐⭐⭐⭐⭐ |
| **Riskfolio-Lib**      | Portfolio/Risk Engine | ALTO     | Medio    | 1 semana    | ⭐⭐⭐⭐   |
| **alphalens-reloaded** | Strategy Engines      | ALTO     | Medio    | 1-2 semanas | ⭐⭐⭐⭐   |
| **FinRL**              | Learning Engine       | MUY ALTO | Alto     | 2-3 semanas | ⭐⭐⭐⭐⭐ |
| **Zipline-Reloaded**   | Execution Engine      | MUY ALTO | Alto     | 2-3 semanas | ⭐⭐⭐⭐⭐ |
| **Qlib**               | Learning Engine       | ALTO     | Alto     | 2-3 semanas | ⭐⭐⭐⭐   |
| **QuestDB**            | Data Engine           | ALTO     | Medio    | 1-2 semanas | ⭐⭐⭐⭐   |
| **Dagster**            | Orchestration         | ALTO     | Medio    | 1-2 semanas | ⭐⭐⭐⭐   |
| **TA-Lib**             | Strategy Engines      | MEDIO    | Bajo     | 3-4 días    | ⭐⭐⭐     |

**Tiempo Total Estimado**: 12-16 semanas adicionales  
**Mejora Total Estimada**: 100-200% en profesionalismo y capacidades

---

## ✅ Estado Actual Consolidado

### Fases Completadas

- ✅ **Fase 1**: Data Engine + Context Engine (100%)
- ✅ **Fase 2**: Strategy Engines + Learning Engine (100%)
- ✅ **Fase 3**: Portfolio Engine + Risk Engine (90%)
- 🔴 **FASE 0** (NUEVO): Capital Viability & Integration Hardening (0%) - **CRÍTICO ANTES DE DEPLOY LIVE**

### Integraciones Completadas

- ✅ Pydantic 2.x (Data Contracts)
- ✅ PyPortfolioOpt (Portfolio Engine)
- ✅ Riskfolio-Lib (Risk Engine)
- ✅ Alphalens (Factor Analysis - pendiente integración completa)
- ✅ QuantStats (ya en requirements, pendiente integración Meta-Analyzer)
- ✅ Drift Detection, Feature Importance, Transfer Learning (Learning Engine)

### Integraciones Pendientes

- 🔴 **PHASE 0 GATES** (Blocker for any live trading on small accounts) - 2-3 weeks
  - Capital viability validator
  - Commission cost analyzer
  - Opportunity cost validator
  - Learning capital gate
  - 5x integration tests
- ⏳ Zipline-Reloaded (Execution Engine)
- ⏳ Qlib (Learning Engine - DoubleEnsemble)
- ⏳ QuestDB (Data Engine - time-series storage)
- ⏳ Dagster (Orchestration)
- ⏳ QuantStats/empyrical/pyfolio (Meta-Analyzer)
- ⏳ TA-Lib (opcional - Strategy Engines)

---

## 🎯 Roadmap: Próximas Acciones Prioritarias (REORDENADAS CON PHASE 0)

### BLOQUERS CRÍTICOS (Antes de anything else)

**⚠️ PHASE 0 - System Reliability Hardening** (2-3 semanas OBLIGATORIO)
1. **T0.1.1**: Profit goal validator `app/services/capital_viability_gate.py` (3 days)
2. **T0.1.2**: Commission cost analyzer `app/services/execution_cost_analyzer.py` (3 days)
3. **T0.1.3**: Opportunity cost validator `app/services/opportunity_cost_validator.py` (2 days)
4. **T0.2.1**: Learning capital gate (3 days)
5. **T0.2.2**: Expensive module gates (2 days)
6. **T0.3.1-T0.3.5**: 5x Integration tests (4 days)
7. **T0.4**: Deployment safety checklist & logging (2 days)

**No live account < $30k can trade until PHASE 0 complete**

### Post-PHASE-0 Roadmap

1. **Fase 4 - Meta-Analyzer**: Integrar QuantStats, empyrical, pyfolio (2-3 semanas)
2. **Fase 5 - Execution Engine**: Integrar Zipline-Reloaded (2-3 semanas)
3. **Data Engine**: Migrar a QuestDB para live ticks (1-2 semanas)
4. **Learning Engine**: Integrar Qlib DoubleEnsemble (2-3 semanas)
5. **Orchestration**: Integrar Dagster (1-2 semanas)

---

## 📊 Risk Assessment Summary (Post-Audit)

### Top 3 Risks Eliminated by PHASE 0

| Risk | Probability | Impact | Severity | PHASE 0 Fix |
|------|-------------|--------|----------|------------|
| Chasing unreachable profit goals | 100% on <$25k | -30-50% capital/3mo | **CRITICAL** | T0.1.1 |
| Commission dominance undetected | 90% in high-vol | -20-40% capital/2wk | **CRITICAL** | T0.1.2 |
| Learning amplifies losses on small accounts | 75% if enabled | -30% capital/4-8wk | **CRITICAL** | T0.2.1 |
| Joint strategy execution costs not modeled | 70% multi-strat | -15-25% capital/4wk | **HIGH** | T0.3.1 |
| Silent bankruptcy on margin accounts | 40% + leverage | -100% capital/1-2da | **CRITICAL** | T0.1.3 |

### Deployment Readiness Gate

**❌ BLOCKED**: Cannot deploy accounts < $30k without PHASE 0
**⚠️ CAUTION**: Accounts $30k-$50k need all P0 tests passing
**✅ CLEARED**: Accounts > $50k can proceed with recommended tests

---

## 📝 Implementation Checklist (PHASE 0 → PHASES 1-6)

### Week 1-3: PHASE 0 (CRITICAL PATH)

- [ ] Create `app/services/` directory if not exists
- [ ] **Day 1-3**: Implement `capital_viability_gate.py`
  - [ ] `CapitalViabilityValidator` class
  - [ ] Formula for alpha requirement
  - [ ] Unit tests (3 scenarios)
- [ ] **Day 4-6**: Implement `execution_cost_analyzer.py`
  - [ ] Slippage history tracking
  - [ ] Volatility-dependent cost modeling
  - [ ] Real-time rejection logic
  - [ ] Unit tests (5 scenarios)
- [ ] **Day 7-8**: Implement `opportunity_cost_validator.py`
  - [ ] Risk-free rate comparison
  - [ ] Active vs passive decision logic
  - [ ] Unit tests (3 scenarios)
- [ ] **Day 9-11**: Implement `learning_capital_gate.py`
  - [ ] Capital threshold check (T0.2.1)
  - [ ] Cost-benefit analysis
  - [ ] Integration with drift detector
  - [ ] Unit tests (4 scenarios)
- [ ] **Day 12-13**: Implement `expensive_module_gate.py`
  - [ ] Synthetic data gating (T0.2.2)
  - [ ] LLM gating
  - [ ] Unit tests
- [ ] **Day 14-17**: Integration tests
  - [ ] `test_capital_stress_joint_strategy.py` (T0.3.1)
  - [ ] `test_integration_stale_data_learning_damage.py` (T0.3.2)
  - [ ] `test_integration_risk_escalation_signal_atomicity.py` (T0.3.3)
  - [ ] `test_integration_rebalancing_pending_trades.py` (T0.3.4)
  - [ ] `test_integration_currency_hedging_cost_dominance.py` (T0.3.5)
- [ ] **Day 18-21**: Audit trail & config
  - [ ] Update `AuditTrail` logging
  - [ ] Create config templates per capital tier
  - [ ] Safety checklist document
- [ ] **Day 22**: Full PHASE 0 test run
  - [ ] All 7 gates working
  - [ ] All 5 integration tests passing
  - [ ] 100% log coverage

### Week 4+: Proceed to PHASES 1-6

Once PHASE 0 passing:
- Continue with Phase 4 (Meta-Analyzer)
- Ensure each subsequent phase includes capital-aware validation
- Audit any new module for capital sensitivity

---

## 🚨 Deployment Guards (Enforcement)

### Pre-Live Checklist

```python
# app/core/deployment_gates.py (NEW FILE)

class DeploymentGate:
    @staticmethod
    def can_trade(capital: Decimal, strategy_config: dict, features_enabled: dict) -> (bool, str):
        """
        Final gate before any live trading.
        Returns (can_trade, reason_if_blocked)
        """

        # PHASE 0 mandatory checks
        viability = CapitalViabilityValidator.validate_profit_goal(
            capital,
            strategy_config.get('profit_goal'),
            strategy_config.get('tax_rate')
        )
        if not viability['is_viable']:
            return False, viability['reason']

        # Check learning gate
        if features_enabled.get('learning'):
            learning_gate = LearningCapitalGate()
            if not learning_gate.should_enable_learning(capital, ...):
                return False, "Learning disabled: insufficient capital"

        # Check capital thresholds
        if capital < Decimal("10000"):
            return False, "Minimum capital $10,000 required for live trading"

        # Check all gates
        if capital < Decimal("30000") and not all_phase0_tests_passing():
            return False, "PHASE 0 tests not passing; cannot trade < $30k"

        return True, "APPROVED for trading"
```

---

**Documento consolidado v2.1 (con PHASE 0 Critical Integration Audit)**
**Estado**: PHASE 0 es BLOCKER para live deployment
**Próxima revisión**: Después de completar PHASE 0 (en ~3 semanas)
