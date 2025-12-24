# 🚀 Plan Maestro: AlgoTrading Next Level (v3.1 - Parametrization-Driven Architecture)

**Versión**: 3.1 - Dual Architecture: PHASE 0 (Capital Gates) + PARAMETRIZATION FRAMEWORK + PHASES 1-4 (Execution)
**Fecha**: 2025-12-24
**Estado**: PHASE 0 ✅ COMPLETADO | PARAMETRIZATION FRAMEWORK 🔵 (NEW - Ready for Implementation) | PHASES 1-4 📋 (Ready for Integration)

---

## 📋 RESUMEN EJECUTIVO: LA ARQUITECTURA COHERENTE

Este documento consolida **3 capas arquitectónicas coerentes**:

### **Capa 1: PHASE 0 — Capital Viability Gates** ✅ (COMPLETADO)
- Entrada: `capital` (€)
- Función: Validar viabilidad técnica y económica
- Output: Aprobación o rechazo PRE-parametrización
- Status: ✅ 178 tests pasando
- Serve: Todos los modos (capital pequeño o grande)

### **Capa 2: PARAMETRIZATION FRAMEWORK** 🔵 (NUEVO - T1.1 a T14.1)
- Entrada: `capital_inicial` + `objetivo_inversion` + `risk_tolerance` (optativo)
- Función: Generar automáticamente un perfil de inversión parametrizado
- Proceso:
  1. InputProcessor (T1.1): Capturar y validar inputs
  2. ProfileGenerator (T2.1): Mapear objetivo → InvestmentProfile
  3. ModuleParametrizer (T3.1): Aplicar perfil a 17 módulos → parámetros específicos
  4. [Opcional: RiskScalingApplication (T8.1) si FASE 3 está lista]
- Output: `ModuleParameterSet` — conjunto completo de parámetros para todos los módulos
- Entregables: 14 tareas de infraestructura (T1.1-T14.1)

### **Capa 3: PHASES 1-4 — Execution & Optimization** 📋 (Planeadas)
- Entrada: `ModuleParameterSet` (generado por Capa 2)
- Función:
  - PHASE 1: Aplicar estrategias capital-aware
  - PHASE 2: Optimizar ejecución (orden splitting, impact minimization)
  - PHASE 3: Risk scaling dinámico (si está listo)
  - PHASE 4: Validación de capacity fade y alpha sustainability
- Output: Portfolio ejecutado con retorno objetivo validado
- Integration: Con SmartOrderRouter, PositionSizingEngine, DynamicRiskScaler, etc.

---

## FLUJO COHERENTE: INPUT → PROFIL → PARÁMETROS → EJECUCIÓN → VALIDACIÓN → DEPLOY DECISION

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     USER INPUT                                           │
│  • capital_inicial: €250,000                                            │
│  • objetivo_inversion: "maximizar_sharpe" | "bajo_riesgo" | etc.      │
│  • risk_tolerance (optional): conservador|moderado|agresivo            │
└────────────┬────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ✅ PHASE 0: CAPITAL VIABILITY GATES (178 tests)                         │
│  ├─ T0.1: Capital Viability (€10k-€10M range valid?)                  │
│  ├─ T0.2: Module Gates (capital enough for advanced modules?)         │
│  ├─ T0.3: Integration Tests                                           │
│  └─ T0.4: Deployment System                                           │
│  OUTPUT: ✅ APPROVED or ❌ REJECTED                                    │
│  IF REJECTED: STOP HERE. Return error & recommendations.              │
└────────────┬────────────────────────────────────────────────────────────┘
             │ IF APPROVED: Continue
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 🔵 PARAMETRIZATION FRAMEWORK (T1.1-T14.1) — NEW!                       │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ T1.1: InputProcessor                                            │  │
│  │  └─ Validate & parse capital, objetivo_inversion, etc.        │  │
│  │  OUTPUT: InputProfile (Pydantic)                               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                   ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ T2.1: ProfileGenerator                                          │  │
│  │  └─ Map objetivo_inversion → InvestmentProfile                │  │
│  │     (config/investment_profiles.yaml lookup + adjustments)     │  │
│  │  OUTPUT: InvestmentProfile (strategy, risk_level, sectors, etc)│  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                   ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ T3.1: ModuleParametrizer                                        │  │
│  │  └─ Apply InvestmentProfile → parameters for 17 modules       │  │
│  │     (config/module_parameter_mappings.yaml rules evaluation)   │  │
│  │  OUTPUT: ModuleParameterSet (all params for all modules)       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                   ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ T8.1: RiskScalingApplication [CONDITIONAL - feature flag]      │  │
│  │  └─ IF risk_scaling_enabled: Apply FASE 3 scaling factors     │  │
│  │     ELSE: Skip (direct parameter usage)                         │  │
│  │  OUTPUT: OptionallyScaledModuleParameterSet                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  AGGREGATED OUTPUT: Complete ModuleParameterSet ready for backtest    │
└────────────┬────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ T4.1: BacktestOrchestrator                                             │
│  └─ Execute backtest with ModuleParameterSet parameters               │
│     (Zipline-Reloaded integration)                                    │
│  OUTPUT: BacktestResult (sharpe, returns, max_dd, feasibility_ratio) │
└────────────┬────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ T5.1: ValidationEngine (FASE 0 Integration)                            │
│  └─ Run FASE 0 tests against configuration                            │
│  └─ Criteria: capital viability, module readiness, feasibility        │
│  OUTPUT: ValidationResult (passed/failed, critical_failures)          │
│  IF FAILED: STOP. Return detailed errors.                             │
└────────────┬────────────────────────────────────────────────────────────┘
             │ IF VALIDATED
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ T6.1: StrategyRecommender                                              │
│  └─ Analyze backtest_result + validation_result                       │
│  └─ Generate human-readable recommendations                           │
│  OUTPUT: StrategyRecommendation (suggested adjustments, warnings)     │
└────────────┬────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ T7.1: PortfolioConstructor                                             │
│  └─ Build portfolio with weights (PyPortfolioOpt + Riskfolio)         │
│  OUTPUT: PortfolioAllocation (assets, weights, expected metrics)      │
└────────────┬────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ T9.1: ReportingGenerator                                               │
│  └─ Generate HTML report (QuantStats + pyfolio)                       │
│  OUTPUT: ReportPackage (HTML + JSON)                                  │
└────────────┬────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ T10.1: DeployDecisionOrchestrator [MASTER ORCHESTRATOR]                │
│  └─ Orchestrate T1.1-T9.1, aggregate results                          │
│  └─ Decision Logic:                                                    │
│      ✅ APPROVED:    Backtest feasible, validation passed             │
│      ⚠️  CONDITIONAL: Backtest weak but viable, manual review needed  │
│      ❌ REJECTED:    Capital insufficient OR validation failed        │
│  OUTPUT: DeployDecision (APPROVED|CONDITIONAL|REJECTED, reasoning)    │
└────────────┬────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 📋 PHASES 1-4: EXECUTION (Only if DeployDecision == APPROVED)          │
│                                                                          │
│  PHASE 1: Capital-Tier Aware Strategy (T1 from v3.0)                  │
│   └─ Use InvestmentProfile + ModuleParameterSet                       │
│   └─ CapitalTierStrategySelector activates features dynamically      │
│   └─ AbsoluteReturnOptimizer optimizes for €800/mes target           │
│                                                                          │
│  PHASE 2: Execution Optimization (T2 from v3.0)                       │
│   └─ SmartOrderRouter uses splitting strategy from ModuleParameterSet │
│   └─ LargePositionBuilder applies parameters                         │
│                                                                          │
│  PHASE 3: Dynamic Risk Scaling (T3 from v3.0)                         │
│   └─ RiskScalingOrchestrator applies runtime scaling (if PHASE 3 done)│
│   └─ VolatilityMonitor, SharpeMonitor, LossMonitor, DrawdownMonitor │
│                                                                          │
│  PHASE 4: Capacity Fade Validation (T4 from v3.0)                     │
│   └─ Validate that alpha is sustainable as capital grows             │
│   └─ Recommend position sizing adjustments                           │
│                                                                          │
│  OUTPUT: Executed portfolio with validated returns                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ✅ PHASE 0: System Reliability Hardening & Capital Viability (COMPLETADO)

**Timeline**: ✅ 2025-12-23 Completado
**Estado**: 178 tests ✅ pasando
**Capital Target**: €10k-€50k (fail-safe, supervivencia)

| Subtask | Tests | Status |
|---------|-------|--------|
| **T0.1: Capital Viability Gates** | 49 | ✅ |
| **T0.2: Learning & Module Gates** | 60 | ✅ |
| **T0.3: Integration Tests** | 10 | ✅ |
| **T0.4: Deployment System** | 59 | ✅ |
| **TOTAL** | **178** | **✅** |

### Componentes T0:
- ✅ CapitalViabilityValidator
- ✅ ExecutionCostAnalyzer
- ✅ OpportunityCostValidator
- ✅ LearningCapitalGate
- ✅ ExpensiveModuleGate
- ✅ DeploymentValidator
- ✅ AccountConfiguration (Micro/Small/Medium/Large tiers)

**Función**: Rechaza automáticamente operaciones imposibles antes de ejecutarse. Garantiza que si el sistema pasa PHASE 0, el capital está seguro bajo ese modo.

---

## 🔵 PARAMETRIZATION FRAMEWORK: NEW (T1.1 - T14.1) — INFRASTRUCTURE PARA PARAMETRIZACIÓN DINÁMICA

**Timeline**: Estimado 3-4 semanas (implementación paralela con PHASES 1-4)
**Objetivo**: Recibir capital + objetivo de inversión → generar automáticamente perfil y parámetros operacionales
**Salida**: ModuleParameterSet listo para pasar a PHASES 1-4

### **TAREAS DEFINITIVAS: T1.1 - T14.1**

#### **T1.1: InputProcessor & Validation** (Puerta de Entrada)
**Objetivo**: Capturar y validar inputs del usuario
**Subtareas**:
- T1.1.1: API de entrada (InputProfile Pydantic)
  - `capital_inicial: Decimal (€10k - €10M)`
  - `objetivo_inversion: Enum[10 valores]`
  - `risk_tolerance: Enum (conservador|moderado|agresivo)` [optional]
  - `asset_classes: List[str]` [optional]

- T1.1.2: Validación contra constraints FASE 0
  - ✅ Rechaza capital < €10k
  - ✅ Rechaza capital > €10M
  - ✅ Rechaza objetivo no válido

- T1.1.3: InputProfile Pydantic model
  - Location: `app/core/models/input_profile.py`

**Dependencias**: Pydantic, FASE 0 constraints
**Entregables**: `app/core/models/input_profile.py`, `app/core/validators/input_validator.py`
**Pruebas**: 8-10 tests (validación de inputs, boundary cases)

---

#### **T2.1: InvestmentProfileGenerator** (Mapeo Objetivo → Perfil)
**Objetivo**: Mapear objetivo_inversion + capital_inicial + risk_tolerance → InvestmentProfile completo
**Subtareas**:
- T2.1.1: Matriz de mapeo en YAML
  - Location: `config/investment_profiles.yaml`
  - Ejemplo: `maximizar_dividendos` → `{target_return: 4.5%, sharpe_target: 0.8, sectors: [utilities, staples], dividend_yield_min: 2.0}`

- T2.1.2: InvestmentProfile Pydantic model
  - Fields: target_return, sharpe_target, sector_prefs, leverage, rebalance_freq, risk_scaling_enabled

- T2.1.3: ProfileGenerator service
  - Método: `generate_profile(input: InputProfile) → InvestmentProfile`
  - Logic: lookup + capital-based adjustments + risk_tolerance overrides

- T2.1.4: Perfil "recommended" logic-driven
  - Basado en capital/objetivo ratios de viabilidad

**Dependencias**: T1.1, Pydantic, config/investment_profiles.yaml
**Entregables**: `config/investment_profiles.yaml`, `app/services/profile_generator.py`
**Pruebas**: 10-12 tests (mapeos correctos, adjustments válidos)

---

#### **T3.1: DynamicModuleParametrizer** (Aplicación a 17 Módulos)
**Objetivo**: Convertir InvestmentProfile → parámetros específicos para cada uno de 17 módulos
**Subtareas**:
- T3.1.1: Matriz de mapeo módulo → parámetros
  - Location: `config/module_parameter_mappings.yaml`
  - Template evaluation (Jinja2): `rule: "capital * 0.02 if profile.position_sizing_conservative else capital * 0.05"`

- T3.1.2: ModuleParametrizer service
  - Método: `parametrize_modules(profile: InvestmentProfile) → Dict[str, ModuleConfig]`

- T3.1.3: Validación de coherencia (detecta conflictos)

- T3.1.4: ModuleParameterSet Pydantic model
  - Serializable a YAML para persistencia

**Módulos Parametrizados** (≥ 10 críticos):
- PositionSizingEngine (base_position_size, kelly_fraction)
- DynamicCapitalReallocationEngine (rebalance_freq, allocation_weights)
- VolatilityAdjustmentEngine (volatility_scale_factor)
- SmartOrderRouter (splitting_strategy: VWAP|TWAP|POI)
- StrategySelector (feature_set, ensemble_mode)
- TrailingStopManager (stop_distance_pct)
- RiskScalingOrchestrator (feature_flag enabled)
- LearningEngine (learning_rate, sample_size)
- Y más...

**Dependencias**: T2.1, Pydantic, Jinja2
**Entregables**: `config/module_parameter_mappings.yaml`, `app/services/module_parametrizer.py`
**Pruebas**: 12-15 tests (mapeos correctos, template evaluation, coherencia)

---

#### **T4.1: BacktestOrchestrator** (Ejecución de Backtest con Parámetros)
**Objetivo**: Ejecutar backtest con ModuleParameterSet, validar factibilidad de retorno objetivo
**Subtareas**:
- T4.1.1: BacktestConfig Pydantic model

- T4.1.2: BacktestExecutor service
  - Integración con Zipline-Reloaded
  - Método: `run_backtest(module_params: ModuleParameterSet) → BacktestResult`
  - Aplicación dinámica de parámetros en cada ciclo de backtest

- T4.1.3: QuantStats reporting
  - Generación de métricas avanzadas: sharpe, information_ratio, calmar, etc.

- T4.1.4: Validación de factibilidad
  - Comparar backtest_sharpe vs profile.sharpe_target
  - Flag: `feasibility_ratio = actual_return / target_return`
  - ✅ Viable si ratio >= 0.9 (90% del objetivo)

**Dependencias**: T3.1, Zipline-Reloaded, QuantStats, empyrical-reloaded
**Entregables**: `app/services/backtest_executor.py`, `app/core/models/backtest_result.py`
**Pruebas**: 10-12 tests (ejecución correcta, métricas validas, factibilidad logic)

---

#### **T5.1: ValidationEngine** (Integración FASE 0 - Guarda/Rechaza Deploy)
**Objetivo**: Ejecutar suite FASE 0 contra configuración. Criterios de aceptación/rechazo.
**Subtareas**:
- T5.1.1: Mapping FASE 0 Tests → Validaciones
  - Capital Viability (49 tests): ✅ capital >= €10k, <= €10M
  - Learning & Module Gates (60 tests): ✅ módulos válidos con parámetros
  - Integration Tests (10 tests): ✅ flujo completo funciona
  - Deployment System (59 tests): ✅ config deployable

- T5.1.2: ValidationResult Pydantic model
  - Fields: passed (int), failed (int), warnings (List), critical_failures (List), is_deployable (bool)

- T5.1.3: ValidationEngine service
  - Método: `validate(config, backtest_result) → ValidationResult`

- T5.1.4: Criterios de rechazo HARD (BLOCKS):
  - ❌ capital < €10k → REJECT
  - ❌ feasibility_ratio < 0.5 → REJECT
  - ❌ critical_failures > 0 → REJECT

**Dependencias**: T4.1, FASE 0 tests
**Entregables**: `app/services/validation_engine.py`, `app/core/models/validation_result.py`
**Pruebas**: 8-10 tests (criterios hard blocks, warnings valid)

---

#### **T6.1: StrategyRecommender** (Recomendaciones a Usuario)
**Objetivo**: Basado en backtest + validación, recomendar ajustes y estrategias
**Subtareas**:
- T6.1.1: Recommendation logic
  - sharpe > 1.0 → "Strategy STRONG"
  - 0.5 < sharpe < 1.0 → "Strategy VIABLE"
  - sharpe < 0.5 → "Strategy WEAK"
  - max_dd > 20% → "Risk ALTO"

- T6.1.2: StrategyRecommendation Pydantic model

- T6.1.3: StrategyRecommender service

- T6.1.4: Sugerencias de ajuste
  - "Aumentar capital si strategy es fuerte"
  - "Revisar parámetros si performance es débil"

**Dependencias**: T4.1, T5.1
**Entregables**: `app/services/strategy_recommender.py`
**Pruebas**: 8-10 tests (recomendaciones coherentes, confidence levels)

---

#### **T7.1: PortfolioConstructor** (Construcción de Cartera)
**Objetivo**: Generar cartera específica con pesos, usando PyPortfolioOpt + Riskfolio
**Subtareas**:
- T7.1.1: PortfolioConstruction service
  - Método: `construct_portfolio(profile, backtest_result) → Portfolio`

- T7.1.2: Integración PyPortfolioOpt
  - Efficient Frontier, risk_parity, max_sharpe optimization

- T7.1.3: Integración Riskfolio-Lib
  - CVaR/CDaR optimization, constraint application

- T7.1.4: Integración alphalens
  - Factor alpha analysis, asset selection

- T7.1.5: PortfolioAllocation Pydantic model

**Dependencias**: T6.1, PyPortfolioOpt, Riskfolio-Lib, alphalens
**Entregables**: `app/services/portfolio_constructor.py`
**Pruebas**: 8-10 tests (pesos válidos, diversificación, métricas esperadas)

---

#### **T8.1: RiskScalingApplication** ⚠️ CONDICIONAL (Integración FASE 3)
**Objetivo**: Aplicar FASE 3 scaling si está disponible (feature flag)
**Subtareas**:
- T8.1.1: Feature flag `risk_scaling_enabled` en config/feature_flags.yaml
  - Default: `false` (hasta que FASE 3 esté 100%)

- T8.1.2: Conditional logic
  - SI enabled: Aplicar RiskScalingOrchestrator → recalcular backtest con scaling
  - SI disabled: Skip, usar parámetros directamente

- T8.1.3: RiskScalingApplicationEngine (cuando FASE 3 esté lista)

**Dependencias**: T3.1, FASE 3 (en desarrollo 30%)
**Entregables**: `config/feature_flags.yaml`, `app/services/risk_scaling_application.py` (cuando FASE 3 lista)
**Pruebas**: 5-7 tests (flag behavior, scaling application logic)
**Status**: ⏳ NO BLOQUEA MVP si FASE 3 no está lista

---

#### **T9.1: ReportingGenerator** (Reportes HTML + JSON)
**Objetivo**: Generar reportes interactivos post-backtest
**Subtareas**:
- T9.1.1: ReportingService
  - Integraciones: QuantStats (HTML), pyfolio-reloaded (tearsheets), empyrical (metrics)

- T9.1.2: ReportPackage Pydantic model
  - Fields: input, investment_profile, backtest_result, validation_result, recommendation, portfolio, report_path

- T9.1.3: Report content
  - Summary, performance charts, risk analysis, allocations, recommendations

- T9.1.4: Persistencia
  - Location: `reports/{timestamp}_{capital}_{objective}.html` + `.json`

**Dependencias**: T4.1, T5.1, T6.1, QuantStats, pyfolio
**Entregables**: `app/services/reporting_service.py`
**Pruebas**: 6-8 tests (report generation, content validity)

---

#### **T10.1: DeployDecisionOrchestrator** ⭐ (MAESTRO — El Corazón del Framework)
**Objetivo**: Orquestar T1.1-T9.1, tomar decisión final de deploy
**Subtareas**:
- T10.1.1: DeployDecisionOrchestrator service
  - Método master: `process_investment_request(input_profile: InputProfile) → DeployDecision`

- T10.1.2: State machine
  - INPUT_RECEIVED → PROFILE_GENERATED → PARAMETERS_SET → BACKTEST_RUNNING → BACKTEST_COMPLETE → VALIDATION_RUNNING → VALIDATION_COMPLETE → RECOMMENDATION_GENERATED → **DEPLOY_DECISION_MADE**

- T10.1.3: Flujo ejecutivo (orquestación secuencial)
  1. T1.1 InputProcessor
  2. T2.1 ProfileGenerator
  3. T3.1 ModuleParametrizer
  4. T4.1 BacktestExecutor
  5. T5.1 ValidationEngine
  6. T6.1 StrategyRecommender
  7. T7.1 PortfolioConstructor
  8. T8.1 RiskScalingApplication [if enabled]
  9. T9.1 ReportingGenerator
  10. **DECISION LOGIC**

- T10.1.4: DeployDecision Pydantic model
  ```
  decision: Enum[APPROVED | CONDITIONAL | REJECTED]
  approval_reason: str
  conditional_requirements: List[str] (if CONDITIONAL)
  report_path: str
  estimated_monthly_return: Decimal (if APPROVED)
  validation_result: ValidationResult
  recommendation: StrategyRecommendation
  portfolio: PortfolioAllocation
  ```

- T10.1.5: Decision Logic
  - ✅ **APPROVED**: Backtest feasible (ratio >= 0.9), validation passed, capital sufficient
  - ⚠️ **CONDITIONAL**: Backtest weak (ratio 0.7-0.9) but viable, manual review recommended
  - ❌ **REJECTED**: Capital < €10k OR validation failed (critical) OR feasibility ratio < 0.7

- T10.1.6: Audit trail logging
  - Registrar cada step con timestamp
  - Guardar intermedios (profile, params, backtest, validation)

**Dependencias**: T1.1-T9.1
**Entregables**: `app/services/deploy_decision_orchestrator.py`, `app/core/models/deploy_decision.py`
**Pruebas**: 12-15 tests (flujo completo, decisiones correctas, audit trail)

---

#### **T11.1: ConfigurationPersistence** (Reproducibilidad & Auditoría)
**Objetivo**: Persistir artefactos para reproducibilidad, auditoría y replay
**Subtareas**:
- T11.1.1: PersistenceService
  - Location: `app/services/persistence_service.py`

- T11.1.2: Serialización YAML
  - Location: `data/profiles/{capital}_{objective}_{timestamp}.yaml`

- T11.1.3: Database schema (SQLite/PostgreSQL)
  - Table: `deployment_configs`
  - Table: `profile_metrics`

- T11.1.4: Métodos
  - `save_config(decision) → config_id`
  - `load_config(config_id) → decision`
  - `replay_config(config_id) → void` (re-ejecutar con parámetros guardados)

**Dependencias**: Pydantic, SQLAlchemy, YAML
**Entregables**: `app/services/persistence_service.py`
**Pruebas**: 8-10 tests (persistence, replay accuracy)

---

#### **T12.1: ErrorHandling & Robustness** (Confiabilidad)
**Objetivo**: Manejo graceful de errores, logging comprehensive
**Subtareas**:
- T12.1.1: Custom exception hierarchy (`app/core/exceptions.py`)
  - InputValidationError, ProfileGenerationError, BacktestError, ValidationError, DeployDecisionError

- T12.1.2: Comprehensive logging (`app/core/logger.py`)
  - File + console output, structured logging

- T12.1.3: Precondition checks (validar dependencias)

- T12.1.4: Graceful degradation
  - Si T8.1 (RiskScaling) falla → continuar sin scaling
  - Si T9.1 (Reporting) falla → continuar con decisión, sin reporte

**Dependencias**: Python logging, Pydantic
**Entregables**: `app/core/exceptions.py`, `app/core/logger.py`
**Pruebas**: 10-12 tests (error cases, degradation scenarios)

---

#### **T13.1: APIEndpoints** (Interfaz REST)
**Objetivo**: Exponer framework via REST API
**Subtareas**:
- T13.1.1: API schema
  - POST `/api/v1/deploy/analyze` → InputProfile → DeployDecision (async)
  - GET `/api/v1/deploy/{config_id}` → Retrieve saved decision
  - GET `/api/v1/deploy/list` → List all configs
  - POST `/api/v1/deploy/{config_id}/approve` → Mark approved

- T13.1.2: Framework (FastAPI recomendado)
  - Async handling para backtests largos

- T13.1.3: Authentication (simple API key para MVP)

**Dependencias**: FastAPI, SQLAlchemy, Pydantic
**Entregables**: `app/api/v1/endpoints/deploy.py`
**Pruebas**: 6-8 tests (endpoint functionality, async handling)
**Status**: 🔵 OPCIONAL PARA MVP (implementar en FASE posterior)

---

#### **T14.1: Testing & Validation Suite** (Confianza)
**Objetivo**: Cobertura integral Unit + Integration tests
**Subtareas**:
- T14.1.1: Unit tests para T1.1-T13.1
  - Validaciones, mapeos, orchestration logic
  - Mínimo 8-10 tests por tarea

- T14.1.2: Integration tests
  - Full flow scenarios (€10k bajo_riesgo, €500k maximizar_sharpe, etc.)
  - Esperados: APPROVED, CONDITIONAL, REJECTED en casos correctos

- T14.1.3: Coverage target: ≥ 80% cobertura de código

**Dependencias**: pytest, unittest, mock
**Entregables**: `tests/unit/parametrization/`, `tests/integration/deploy_decision/`
**Pruebas**: 50-70 tests (unit + integration)
**Status**: 🔵 EJECUTAR EN PARALELO con desarrollo T1.1-T13.1

---

## RESUMEN DE ENTREGABLES: PARAMETRIZATION FRAMEWORK (T1.1-T14.1)

| Tarea | Archivos/Componentes | Tests | Esfuerzo (días) |
|-------|----------------------|-------|-----------------|
| T1.1 InputProcessor | input_profile.py, input_validator.py | 8-10 | 0.5 |
| T2.1 ProfileGenerator | profile_generator.py, investment_profiles.yaml | 10-12 | 1 |
| T3.1 ModuleParametrizer | module_parametrizer.py, module_parameter_mappings.yaml | 12-15 | 1.5 |
| T4.1 BacktestOrchestrator | backtest_executor.py, backtest_result.py | 10-12 | 2 |
| T5.1 ValidationEngine | validation_engine.py, validation_result.py | 8-10 | 1 |
| T6.1 StrategyRecommender | strategy_recommender.py | 8-10 | 1 |
| T7.1 PortfolioConstructor | portfolio_constructor.py | 8-10 | 1.5 |
| T8.1 RiskScalingApplication | risk_scaling_application.py [conditional] | 5-7 | 0.5 |
| T9.1 ReportingGenerator | reporting_service.py | 6-8 | 1 |
| T10.1 DeployDecisionOrchestrator ⭐ | deploy_decision_orchestrator.py, deploy_decision.py | 12-15 | 2 |
| T11.1 ConfigurationPersistence | persistence_service.py | 8-10 | 1 |
| T12.1 ErrorHandling & Robustness | exceptions.py, logger.py | 10-12 | 1 |
| T13.1 APIEndpoints | endpoints/deploy.py [optional] | 6-8 | 1 |
| T14.1 Testing & Validation | tests/unit/, tests/integration/ | 50-70 | 2 |
| **TOTAL** | **~30 archivos** | **~130-160 tests** | **~17 días** |

---

## 🚀 PHASES 1-4: Execution & Optimization (Enabled by T1.1-T14.1 Framework)

### **PHASE 1: Capital-Tier Aware Strategy Orchestration**

**Prerequisito**: DeployDecision == APPROVED (from T10.1)

**Entrada**: `ModuleParameterSet` (from T3.1)

**Objetivo**: Aplicar estrategias adaptadas al capital, usando parámetros generados

**Componentes** (ya existentes en v3.0):
- T1.1 (PHASE 1): CapitalTierStrategySelector
- T1.2 (PHASE 1): AbsoluteReturnOptimizer

**Integración**:
- CapitalTierStrategySelector toma InvestmentProfile.target_return y aplica estrategias dinámicamente
- AbsoluteReturnOptimizer recibe parámetros de ModuleParameterSet (position_size, leverage, etc.)

**Timeline**: 2-3 días

---

### **PHASE 2: Execution Optimization for Large Capital**

**Entrada**: `ModuleParameterSet` + estrategia de PHASE 1

**Objetivo**: Minimizar costes de ejecución, mantener 3.9% neto

**Componentes**:
- T2.1 (PHASE 2): SmartOrderRouter
- T2.2 (PHASE 2): LargePositionBuilder

**Integración**:
- SmartOrderRouter toma `splitting_strategy` de ModuleParameterSet (VWAP|TWAP|POI)
- LargePositionBuilder usa parámetros de ejecución (execution_windows, size_allocation)

**Timeline**: 2-3 días

---

### **PHASE 3: Dynamic Risk Scaling**

**Entrada**: Running positions + market data

**Objetivo**: Ajustar dinámicamente tamaños de posición basado en volatilidad, Sharpe, drawdown

**Componentes** (ya implementados al 30%):
- VolatilityMonitor, SharpeRatioMonitor, LossMonitor, DrawdownMonitor
- RiskScalingOrchestrator

**Integración**:
- Si `risk_scaling_enabled == true` (from T8.1 feature flag), aplicar scaling factors
- Si `risk_scaling_enabled == false`, usar parámetros fijos de ModuleParameterSet

**Timeline**: 1-2 días (integration, cuando FASE 3 completada)

---

### **PHASE 4: Capacity Fade & Alpha Validation**

**Entrada**: Backtest results + live performance

**Objetivo**: Validar que alpha es sustainable a medida que capital crece

**Componentes** (a especificar):
- CapacityFadeAnalyzer
- AlphaSustainabilityValidator

**Integration**: Recibir métrica de capacity_fade desde PHASE 4, ajustar parámetros de PHASES 1-3

**Timeline**: 2-3 días

---

## 🔄 FLUJO COHERENTE COMPLETO: DE USUARIO A DEPLOY

```
1. USER INPUT (capital_inicial, objetivo_inversion)
   ↓
2. ✅ PHASE 0 (Capital Viability) → ✅ APPROVED or ❌ REJECTED
   ↓ (if approved)
3. 🔵 PARAMETRIZATION FRAMEWORK (T1.1-T14.1)
   ├─ T1.1: InputProcessor
   ├─ T2.1: ProfileGenerator
   ├─ T3.1: ModuleParametrizer
   ├─ T4.1: BacktestExecutor → metrics (sharpe, return, dd)
   ├─ T5.1: ValidationEngine → ✅ VALID or ❌ INVALID
   ├─ T6.1: StrategyRecommender
   ├─ T7.1: PortfolioConstructor
   ├─ T8.1: [Conditional] RiskScalingApplication
   ├─ T9.1: ReportingGenerator
   ├─ T10.1: DeployDecisionOrchestrator → ✅ APPROVED / ⚠️ CONDITIONAL / ❌ REJECTED
   ├─ T11.1: ConfigurationPersistence (save decision)
   ├─ T12.1-T13.1: (error handling, logging, API)
   └─ T14.1: (tests & validation)
   ↓ (if T10.1 decision == APPROVED)
4. 📋 PHASES 1-4 (Execution)
   ├─ PHASE 1: Activate strategies (CapitalTierStrategySelector + AbsoluteReturnOptimizer)
   ├─ PHASE 2: Optimize execution (SmartOrderRouter + LargePositionBuilder)
   ├─ PHASE 3: Risk scaling (RiskScalingOrchestrator)
   └─ PHASE 4: Capacity fade validation
   ↓
5. ✅ LIVE PORTFOLIO EXECUTING WITH VALIDATED PARAMETERS
```

---

## 📊 DEPENDENCIAS DE TAREAS (DAG): Parametrization Framework

```
T1.1 (InputProcessor)
  ↓
T2.1 (ProfileGenerator)
  ↓
T3.1 (ModuleParametrizer)
  ├→ T4.1 (BacktestExecutor)
  │    ↓
  │    T5.1 (ValidationEngine) — FASE 0 integration
  │    ↓
  │    T6.1 (StrategyRecommender)
  │    ↓
  │    T7.1 (PortfolioConstructor)
  │    ↓
  │    T8.1 [CONDITIONAL] (RiskScalingApplication)
  │    ↓
  │    T9.1 (ReportingGenerator)
  │
  └────────────────────────────────────────↓
                                    T10.1 ⭐ (DeployDecisionOrchestrator)
                                           ↓
T11.1 (ConfigurationPersistence) ←─────────┘
T12.1 (ErrorHandling & Robustness) — ACROSS ALL
T13.1 (APIEndpoints) [OPTIONAL]
T14.1 (Testing & Validation) — PARALLEL with all
```

---

## ✅ VALIDACIÓN DE COHERENCIA: ¿TODO TIENE SENTIDO?

### **Coherencia Arquitectónica: 9/10 ✅**

#### **✅ LO QUE FUNCIONA BIEN**

1. **Separación clara de concerns**:
   - PHASE 0 = Guardias de entrada (capital viability)
   - T1.1-T14.1 = Parametrización automática (infraestructura)
   - PHASES 1-4 = Ejecución con parámetros (operacional)
   - **Resultado**: Cada capa es independiente, testeable y reutilizable

2. **Flujo lógico impecable Input → Profile → Parameters → Backtest → Validation → Deploy**:
   - Cada paso valida salida del anterior
   - Errores se detectan temprano
   - **Garantía**: Si pasa T10.1, configuración es viable

3. **Integración con FASE 0**:
   - T5.1 (ValidationEngine) ejecuta 178 tests contra config
   - Criterios hard (capital < €10k = REJECT) son claros
   - **Resultado**: No hay surprise failures en deploy

4. **Parametrización de 17 módulos**:
   - T3.1 mapea InvestmentProfile → parámetros específicos
   - Cada módulo (PositionSizer, RiskScaler, SmartOrderRouter, etc.) recibe parámetros del framework
   - **Resultado**: Sistema es dinámico, adaptive, no hard-coded

5. **Integración flexible de FASE 3**:
   - T8.1 usa feature flag para risk_scaling_enabled
   - Si FASE 3 no está lista, skip sin bloqueo
   - **Resultado**: MVP viable sin FASE 3 completa (hoy está 30%)

6. **Orquestación centralizada (T10.1)**:
   - Maestro que coordina T1.1-T9.1
   - State machine clara
   - Decision logic explícita (APPROVED | CONDITIONAL | REJECTED)
   - **Resultado**: Control total del flujo

7. **Persistencia & Auditoria (T11.1)**:
   - Toda decisión guardada con parámetros
   - Reproducibilidad garantizada (replay_config)
   - **Resultado**: Cumple compliance, debugging, análisis post-mortem

8. **Opcionalidad estratégica**:
   - T13.1 (API) es optional para MVP
   - T8.1 (RiskScaling) es conditional
   - **Resultado**: MVP ejecutable sin bloqueadores

9. **Testing distribuido (T14.1)**:
   - Unit tests para cada tarea (T1.1-T13.1)
   - Integration tests para flujo completo
   - Target: 80% coverage
   - **Resultado**: Confianza en código

---

#### **⚠️ PUNTOS A VIGILAR**

1. **Complejidad de mapeos (T2.1, T3.1)**:
   - Los archivos YAML (`investment_profiles.yaml`, `module_parameter_mappings.yaml`) pueden crecer complejos
   - **Mitigación**: Documentar bien, crear tests de mapeos, versionar YAML

2. **Performance del backtest (T4.1)**:
   - Zipline-Reloaded puede ser lento con backtests largos
   - **Mitigación**: Implementar caché de backtests, parallelizar si es posible

3. **Integración FASE 3 timing**:
   - T8.1 depende de FASE 3 completada (actualmente 30%)
   - **Mitigación**: Feature flag mantiene MVP viable, integración fluida cuando FASE 3 lista

4. **Validación FASE 0 scope**:
   - T5.1 ejecuta 178 tests, pueden ser lentos
   - **Mitigación**: Subset de tests críticos para path feliz, full suite para validación exhaustiva

5. **Error handling en cascada**:
   - Si T4.1 falla (backtest error), T5.1-T10.1 no se ejecutan
   - **Mitigación**: Logging claro, mensajes de error descriptivos, graceful degradation donde aplique

---

#### **✅ VALIDACIÓN FINAL: ¿El Framework Habilita PHASES 1-4?**

| PHASE | Requiere de Framework | Cómo |
|-------|---|---|
| **PHASE 1** (Capital-Tier Strategy) | ✅ SÍ | InvestmentProfile + ModuleParameterSet guían CapitalTierStrategySelector |
| **PHASE 2** (Execution Optimization) | ✅ SÍ | splitting_strategy (VWAP/TWAP/POI) + execution_params vienen de T3.1 |
| **PHASE 3** (Risk Scaling) | ✅ SÍ (opcional) | risk_scaling_enabled feature flag, parámetros de RiskScaler en ModuleParameterSet |
| **PHASE 4** (Capacity Fade) | ✅ SÍ | capacity_fade_multiplier en ModuleParameterSet, ajusta parámetros dinámicamente |

**Conclusión**: Framework T1.1-T14.1 es PREREQUISITO y HABILITADOR de PHASES 1-4. Sin parámetros generados dinámicamente, las fases son hard-coded y no adaptables.

---

#### **CRITERIOS DE ÉXITO: Todo el Sistema**

| Criterio | Status |
|----------|--------|
| ✅ PHASE 0 completado (178 tests) | DONE |
| ✅ T1.1-T14.1 framework diseñado | DONE (this doc) |
| ⏳ T1.1-T14.1 implementación | READY TO START |
| ⏳ PHASES 1-4 integración | READY (awaits T1.1-T14.1) |
| ⏳ Full E2E testing | READY (T14.1) |
| ✅ Deploy decision logic | DEFINED (T10.1) |
| ✅ Feature flags & graceful degradation | DESIGNED |
| ✅ Audit trail & reproducibility | DESIGNED (T11.1) |

---

## 🎯 PRÓXIMOS PASOS

### **Inmediatos (Esta semana)**:
1. ✅ Review & approval de Plan Maestro v3.1 (este doc) — **DONE**
2. 🔵 Iniciar implementación de T1.1 (InputProcessor)
3. 🔵 Iniciar T2.1 (ProfileGenerator) en paralelo
4. 🔵 Iniciar T14.1 (tests) en paralelo

### **Próxima semana**:
5. Completar T1.1-T3.1 (infraestructura de parámetros)
6. Completar T4.1-T5.1 (backtest + validación)
7. Completar T6.1-T10.1 (recomendaciones, decisión)

### **Semana 3-4**:
8. Completar T11.1-T14.1 (persistencia, API, testing)
9. Validación E2E (MVP debe pasar T14.1 tests)
10. Integración PHASES 1-4

---

## 📌 RESUMEN UNA LÍNEA

**Plan Maestro v3.1**: PHASE 0 (guardia) → T1.1-T14.1 (parametrización) → PHASES 1-4 (ejecución) = Sistema completo, adaptable, auditable, deployable.
