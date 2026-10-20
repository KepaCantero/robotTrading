# Plan: FASE 5 - Backtesting Engine Implementation

## Overview
Implementar el motor de backtesting robusto para 25 años según el PLAN_DE_EJECUCION_TAREAS_PENDIENTES.md

**Objetivo:** Sistema autónomo para backtests de 25 años y optimización multi-estrategia
**Baseline actual:** 43% cumplimiento (~1200 de 2800 reglas)
**Target:** 95% cumplimiento en Backtesting & Validation

## Context
Basado en el análisis de AUDIT_PLAN_COMPLETO.md, implementar las siguientes tareas prioritarias:

### Tareas YA IMPLEMENTADAS (verificar y documentar):
- ✅ Fundamental Law (IR = IC × √BR) - Grinold & Kahn #116
- ✅ Overfitting Detector - Hastie #96
- ✅ Walk-Forward Validation - Pardo #54 — ahora además OBLIGATORIA (ver estado abajo)
- ✅ Regime Detection - Ilmanen #254
- ✅ InputProfile Router - existe
- ✅ Risk Configurator - existe

### Actualización de estado (2026-10)

Lo hecho recientemente sobre este plan, verificado en código:

- ✅ **Gate walk-forward obligatorio** (commit 7274ab71): `execute_backtest` ejecuta walk-forward IS→OOS y valida compliance R5/R6/DATA-001 tras cada backtest real. `ExtendedBacktestResult` lleva `walk_forward_passed`, `walk_forward_degradation` y `compliance_summary`; si no pasa, se lanza `BacktestComplianceError`. Degradación con semántica correcta `max(0, (IS-OOS)/IS)` — la mejora OOS no cuenta como degradación.
- ✅ **Simulador de resultados falsos eliminado** (commit 262b28c9): sin runner real no hay números inventados, hay `RuntimeError`. Además (commit 0528ea62) los gates de compliance se anclaron al tiempo de señal (no al reloj de pared), desbloqueando los replays históricos.
- ✅ **Estrategia de dividendos real** (commit 8279f5ee): `DividendCoreSatelliteStrategy` registrada como `dividend_tracking` en el orquestador (antes caía silenciosamente a mean_reversion). Estrategias cross-sectionales reciben el timeline global; warmup y tamaño de posición conscientes de la estrategia.
- ✅ **Universo de datos ampliado** (commits fce38e01 y 8279f5ee): ~713 CSVs en `data/historical` (catálogo Vanguard de 66 ETFs + 9 clásicos + importaciones masivas de ETFs de dividendo vía `scripts/import_yahoo_csv.py`).

### Tareas A IMPLEMENTAR:

## Validation Commands
- `python -m pytest app/tests/backtesting/ -v --tb=short`
- `python -m pytest app/tests/analysis/ -v --tb=short`
- `mypy --strict app/`
- `ruff check app/`

### Task 1: Crear Strategy Validators (Sharpe > 1.0, DD < 25%)
- [x] Crear `app/backtesting/validation/strategy_validator.py`  # ya existía
- [x] Implementar `StrategyValidator` class con validadores:
  - Sharpe ratio >= 1.0 (Chan #8)
  - Max drawdown <= 25% (Chan #10)
- [x] Crear modelos Pydantic en `validation_models.py`
- [x] Agregar tests (tests/backtesting/validation/test_strategy_validator.py, verde)
- [x] Integrar con pipeline de backtesting  # HOY: wired al T5 del producto — Sharpe<1 warning; DD>25% warning + APPROVE degradado a CONDITIONAL (tests en tests/unit/dashboard/test_goal_presets.py)
- [x] Documentar con Google style docstrings

**Referencias:**
- PLAN_EJECUCION_TAREAS_PENDIENTES.md - Task 5
- AUDIT_PLAN_COMPLETO.md - Reglas Chan #8, #10

### Task 2: Verificar y Completar Circuit Breaker 5% Daily
- [x] Verificar `app/services/circuit_breaker_manager_v2.py`  # no existe NUNCA existió; el breaker REAL vive en el motor: ComplianceEngine kill_switch_threshold default -0.05 (Hull Rule 13.1)
- [x] Implementar circuit breaker de 5% diario si no existe:  # HOY corregida su semántica: track_daily_pnl hace ROLLOVER por fecha de simulación (antes acumulaba el P&L de todo el proceso y un día malo bloqueaba el backtest entero para siempre; tests tests/unit/core/test_kill_switch_daily.py 4/4)
  - Track daily P&L en real-time
  - Trading halted cuando -5% threshold hit
  - Breaker resets al inicio del siguiente día
- [ ] Crear `app/services/circuit_breaker/daily_circuit_breaker.py`
- [ ] Integrar con `RobustBacktester`
- [ ] Agregar tests
- [ ] Documentar

**Referencias:**
- PLAN_EJECUCION_TAREAS_PENDIENTES.md - Task 2
- Chan #15, Hull #65

### Task 3: Verificar Slippage Model Completeness
- [ ] Verificar `app/backtesting/execution/slippage_model.py`
- [ ] Confirmar que incluye todos los componentes de Chan #3, #16:
  - Bid-ask spread COMPLETO
  - Slippage como función de volatilidad
  - Bid-ask bounce filter
  - Timing cost calculation
- [ ] Agregar componentes faltantes si es necesario
- [ ] Tests para todos los componentes
- [ ] Documentar

**Referencias:**
- PLAN_EJECUCION_TAREAS_PENDIENTES.md - Task 5.7
- Chan #3, #16, Harris #207-209

### Task 4: Verificar Transaction Costs Completeness
- [ ] Verificar `app/backtesting/execution/transaction_cost.py`
- [ ] Confirmar 6 componentes de Chan #4:
  1. Broker commission
  2. Exchange fee
  3. Regulatory fee (SEC, FINRA)
  4. Data feed fee
  5. Slippage (bid-ask spread)
  6. Market impact
- [ ] Verificar commission impact < 15% (Chan #18)
- [ ] Agregar componentes faltantes
- [ ] Tests
- [ ] Documentar

**Referencias:**
- PLAN_EJECUCION_TAREAS_PENDIENTES.md - Task 5.6
- Chan #4, #18

### Task 5: Verificar Market Impact Model
- [ ] Verificar `app/backtesting/execution/market_impact.py`
- [ ] Confirmar modelo Almgren-Chriss implementado:
  - Permanent impact: α · sqrt(7/X) · |ν|
  - Temporary impact: β · |ν|
  - Optimal execution trajectory
- [ ] Tests
- [ ] Documentar

**Referencias:**
- PLAN_EJECUCION_TAREAS_PENDIENTES.md - Task 5.8
- Almgren-Chriss #21

### Task 6: Arreglar Tests de Validation
- [ ] Investigar por qué 71 tests están being skipped
- [ ] Verificar imports y dependencias
- [ ] Verificar conftest.py configuration
- [ ] Arreglar issues para que los tests pasen
- [ ] Confirmar 71/71 tests passing

**Referencias:**
- app/tests/backtesting/test_validation.py

### Task 7: Verificar Vectorización en Todo el Codebase
- [ ] Escanear `app/backtesting/` en busca de:
  - `df.iterrows()` prohibido
  - `for` loops sobre DataFrames
  - Operaciones no vectorizadas
- [ ] Reemplazar con operaciones vectorizadas NumPy/Pandas
- [ ] Verificar `app/optimization/`
- [ ] Verificar `app/strategies/`
- [ ] Profile antes/después para verificar mejora 10x+
- [ ] Documentar mejoras de performance

**Referencias:**
- PLAN_EJECUCION_TAREAS_PENDIENTES.md - Task HP-01
- High Performance Python rules

### Task 8: Documentar Estado Final de FASE 5
- [ ] Actualizar ESTADO_IMPLEMENTACION.md con estado final
- [ ] Documentar todas las verificaciones realizadas
- [ ] Actualizar métricas de cumplimiento
- [ ] Crear reporte final de FASE 5

**Referencias:**
- ESTADO_IMPLEMENTACION.md

## Notas de Implementación

1. **Usar /rules** para verificar cumplimiento de reglas específicas
2. **Type hints** obligatorios (mypy --strict)
3. **Docstrings** Google style en todos los módulos públicos
4. **Tests** con >80% coverage mínimo
5. **No iterrows()** en código de producción
6. **Seguir SOLID principles** en toda nueva implementación

## Criterios de Éxito

- [ ] Todos los tasks marcados como completados
- [ ] Tests passing > 1100/1013
- [ ] Coverage > 85%
- [ ] Mypy strict sin errores
- [ ] Ruff check sin warnings
- [ ] Backtesting & Validation >= 95% cumplimiento
- [ ] Documentación completa y actualizada
