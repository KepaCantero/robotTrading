# Active Context - AlgoTrading

## Current Focus (2025-12-23): Plan Maestro v3.0 "Capital-Aware Dual-Mode Architecture"

**Estado de alto nivel**: MVP operativo + PHASE 0 ✅ COMPLETADO. Nuevo foco: **Escalamiento a Capital Grande (€250k+)**.

**Estrategia**: Arquitectura dual-mode:
- **Small Capital Mode** (<€50k): PHASE 0 ✅ (fail-safe, supervivencia)
- **Large Capital Mode** (€250k+): PHASES 1-4 🟡 (optimización para €800/mes = 3.9% anual)

**Referencia**: Ver `docs/PLAN_MAESTRO_NEXT_LEVEL.md` (v3.0) para arquitectura completa de 17 módulos + PHASES 1-4 para capital grande.

## 🚀 Cambio Estratégico (23-12-2025)

**Insight crítico**: El Plan Maestro original estaba sobre-optimizado para **supervivencia con capital pequeño**, pero no tiene mecanismos para **escalamiento a capital grande con objetivo de retorno absoluto**.

**Nueva arquitectura**: Integra PHASES 1-4 que implementan:
1. Capital-Tier Aware Strategy Selector (T1.1)
2. Absolute Return Optimizer (T1.2) → €800/mes específico
3. Smart Order Routing para órdenes grandes (T2.1)
4. Dynamic Risk Scaling por capital (T3)
5. Capacity Fade Validation (T4)

## 📋 Estado del Plan Maestro por Fase

### **FASE 1: Fundamentos de Datos y Contexto** (Meses 1-3) ✅ **COMPLETADA**

**Módulo 1: Data Engine** ✅

- Normalización unificada de múltiples fuentes (IBKR, Binance, Alpaca, Polygon)
- Limpieza y validación de datos
- Sistema de versionado y caché distribuido
- Tests de integración completos

**Módulo 2: Context Engine** ✅

- Detección de régimen de mercado (HMM, Markov)
- Análisis de volatilidad y correlaciones
- Identificación de contexto macro
- Tests de integración completos

### **FASE 2: Strategy & Learning** (Meses 4-7) ✅ **COMPLETADA (100%)**

**Módulo 3: Strategy Engines** ✅ **100% completado**

- [x] **3.1 Refactorizar estrategias existentes** ✅

  - `BaseStrategyEngine` abstracta creada
  - `MomentumStrategyEngine`, `MeanReversionStrategyEngine`, `PairsTradingStrategyEngine`, `ModularMomentumStrategyEngine` refactorizados

- [x] **3.2 Nuevas estrategias base** ✅ **4/4 completadas**

  - `BreakoutStrategyEngine` ✅ (2025-12-15)
  - `TrendFollowingStrategyEngine` ✅ (2025-12-15)
  - `ArbitrageStrategyEngine` ✅ (2025-12-16)
  - `MeanReversionStrategyEngine` mejorado ✅

- [x] **3.3 Sistema de composición de estrategias** ✅ (2025-12-17)

  - `BaseStrategyEnsemble`, `WeightedEnsemble`, `RegimeBasedSelector`, `VotingEnsemble`
  - Configuración YAML centralizada
  - Integrado en StrategyFactory

- [x] **3.4 Integración con Learning Engine** ✅ **PARCIALMENTE COMPLETADO**

  - Callbacks implementados
  - Feature extraction estandarizado
  - Pendiente: drift detection avanzada, feature importance, transfer learning

- [x] **3.5 Testing y validación** ✅ (2025-12-19)
  - Walk-forward validation, cross-validation temporal
  - Stress testing con datos sintéticos
  - Monte Carlo simulation
  - 44 unit tests (100% passing)

**Módulo 4: Learning Engine** 🟡 **75% completado**

- Sistema de learning para `momentum_modular` completo
- ✅ **Drift Detection** [TASK-4.2-DRIFT] ✅ (2025-12-19)

  - PSI, ADWIN, KS Test, MMD
  - Feature-level drift monitoring
  - Auto-retraining triggers
  - 60 unit tests (100% passing)

- ✅ **Feature Importance** [TASK-4.2-FEATURE-IMPORTANCE] ✅ (2025-12-19)

  - 6-method ensemble (SHAP, Permutation, Built-in, Correlation, Stability, Selection)
  - Feature categorization y engineering recommendations

- ✅ **Transfer Learning** [TASK-4.2-TRANSFER-LEARNING] ✅ (2025-12-19)
  - Market regime detection
  - Pre-trained model lookup y fine-tuning automático

### **FASE 3: Portfolio y Risk** (Meses 8-10) ✅ **NÚCLEO IMPLEMENTADO**

**Módulo 5: Portfolio Engine** ✅ **95% completado**

- Optimizadores: Markowitz, Risk Parity, Black-Litterman, Kelly Criterion ✅
- Rebalancers dinámicos ✅
- Meta-learners para asignación ✅
- ✅ **Currency Hedging Automático** [TASK-5.5-CURRENCY-HEDGING] ✅ (2025-12-19)
- Pendiente: diversificación sector/país

**Módulo 6: Risk Engine** ✅

- VaR/CVaR calculados
- Stress testing implementado
- Exposición, drawdowns, correlaciones
- Risk attribution y alert system
- Tests de integración completos

## 🔒 PHASE 0: Capital Viability & Integration Audit ✅ **COMPLETADO (23-12-2025)**

**Status**: Production-ready para accounts <€50k
**Tests**: 178 tests passing
**Componentes**:
- ✅ T0.1: Capital Viability Gates (49 tests)
- ✅ T0.2: Learning & Module Gates (60 tests)
- ✅ T0.3: Integration Tests (10 tests)
- ✅ T0.4: Deployment Validator & Account Config (59 tests)

**Garantía**: Sistema rechaza operaciones imposibles antes de dañar capital en cuentas pequeñas.

## 🟡 PHASES 1-4: Large Capital Optimization (**PRÓXIMO - 9-11 días**)

**Objetivo**: Escalar sistema a €250k con target €800/mes neto (3.9% anual)

### Timeline:
```
PHASE 1: Capital-Tier Strategy (2-3 días)
  ├─ T1.1: Capital Tier Strategy Selector
  └─ T1.2: Absolute Return Optimizer

PHASE 2: Execution Optimization (2-3 días)
  ├─ T2.1: Smart Order Routing
  └─ T2.2: Large Position Builder

PHASE 3: Dynamic Risk Scaling (1-2 días)
  └─ Riesgo dinámico por capital + target

PHASE 4: Capacity Fade Validation (2-3 días)
  └─ Valida 3.9% es realista a €250k
```

### **Fases 5–7** (Original Plan): ⏳ **PENDIENTES después de PHASES 1-4**

- Diseño detallado en `PLAN_MAESTRO_NEXT_LEVEL.md`
- Piezas iniciales en código
- Módulos dedicados bajo `app/engines/` aún no implementados

## 📊 Progreso General del Plan Maestro

| Fase                        | Estado | Progreso | Módulos Completados                                             |
| --------------------------- | ------ | -------- | --------------------------------------------------------------- |
| Fase 1: Data & Context      | ✅     | 100%     | 2/2 (Data Engine, Context Engine)                               |
| Fase 2: Strategy & Learning | ✅     | 100%     | 3.1 ✅, 3.2 ✅ (4/4), 3.3 ✅, 3.4 ✅, 3.5 ✅                    |
| Fase 3: Portfolio & Risk    | ✅     | 90%      | Portfolio Engine ✅, Risk Engine ✅                             |
| Fases 4-7                   | 🟡     | 40%      | Drift Detection ✅, Feature Importance ✅, Transfer Learning ✅ |

## 🎯 Próximas Tareas Prioritarias

1. ⏳ Diversificación sector/país (Portfolio Engine)
2. ⏳ Mejoras avanzadas Learning Engine (drift detection avanzada, feature importance tracking)
3. ⏳ Fase 4: Meta-Analyzer (Mejora)
4. ⏳ Fase 5: Execution Engine (Mejora)
5. ⏳ Fase 6: Monitoring & Dashboard (Next Level)

## 📊 Estado Actual del Sistema

**Métricas Clave:**

- Tests: 686 pasando / 0 fallando (100% éxito ✅)
- Cobertura: 53% (5,503/11,680 líneas)
- Linting: ✅ Errores críticos corregidos
- Arquitectura: Microservicios con FastAPI + PostgreSQL + Redis
- Estrategias: Momentum, Liquidity, Mean Reversion, Pairs Trading, Breakout, Trend Following operativas
- Backtesting: ✅ Funcional con datos históricos reales

**Integración Completa:**

- ✅ Engines registrados en `StrategyFactory`
- ✅ Configuración YAML centralizada (`config/strategies/*.yaml`)
- ✅ Integración en `comprehensive_backtest_runner.py`
- ✅ Todos los parámetros centralizados (sin magic numbers)
