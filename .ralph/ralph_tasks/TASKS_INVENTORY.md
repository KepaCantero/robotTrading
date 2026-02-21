# 📋 Inventario Exhaustivo de Tareas Ralph

**Fecha:** 2026-02-21
**Estado:** Plan completo creado
**Total tareas:** 23 tareas planificadas
**Tareas creadas:** 22 tareas YAML + 1 orquestador

---

## 📁 Archivos en ralph_tasks/

### YAML de Tareas (21 creadas + 1 orquestador)

| Archivo | Estado | Prioridad | Horas | Descripción |
|---------|--------|-----------|-------|-------------|
| `00_master_orchestrator.yml` | ✅ CREADO | P0 | - | Orquestador principal |
| `01_protocol_interfaces.yml` | ✅ CREADO | P0 | 4h | Interfaces Protocol |
| `02_spain_tax_engine.yml` | ✅ CREADO | P0 | 8h | Motor impuestos España |
| `03_trading_decision_logger.yml` | ✅ CREADO | P0 | 6h | Logger append-only |
| `04_risk_validators.yml` | ✅ CREADO | P0 | 8h | Validadores R1,R2,R4 |
| `09_compliance_engine_refactor.yml` | ✅ CREADO | P0 | 16h | Refactor ComplianceEngine |
| `22_code_quality_refactor.yml` | ✅ CREADO | P1 | 15h | Config, Hardcoded Values & Libraries |
| `23_profile_backtest_metrics_fix.yml` | ✅ CREADO | P0 | 16h | Fix Sharpe Ratio & Profile Metrics |

### Tareas Planificadas (Sin YAML aún)

| ID | Prioridad | Horas | Descripción | Archivo a crear |
|----|-----------|-------|-------------|-----------------|
| 05 | P1 | 12h | Position Management (R11,R12,R13) | ✅ YA CREADO |
| 06 | P1 | 6h | Reconciliation Daily (R16) | ✅ YA CREADO |
| 07 | P1 | 6h | Capital Phase Manager (R25-R27) | ✅ YA CREADO |
| 08 | P0 | 16h | Broker Adapters (IBKR Spain) | ✅ YA CREADO |
| 10 | P0 | 4h | Execution Engine Integration | ✅ YA CREADO |
| 11 | P0 | 4h | Order Manager Integration | ✅ YA CREADO |
| 12 | P0 | 4h | Trading Bridge Integration | ✅ YA CREADO |
| 13 | P0 | 8h | Live Trading CLI | ✅ YA CREADO |
| 14 | P1 | 6h | Single User Config | ✅ YA CREADO |
| 15 | P1 | 6h | Telegram Alerting | ✅ YA CREADO |
| 16 | P1 | 12h | Simple Dashboard | ✅ YA CREADO |
| 17 | P0 | 12h | Backtest Fixes | ✅ YA CREADO |
| 19 | P1 | 8h | Security Hardening (R29) | ✅ YA CREADO |
| 20 | P0 | 16h | Integration Tests | ✅ YA CREADO |
| 21 | P1 | 10h | Backtesting Folder Audit | ✅ YA CREADO |
| 22 | P1 | 15h | Code Quality Refactor | ✅ CREADO |
| 99 | P2 | 8h | Final Cleanup | ✅ CREADO |

---

## 📝 Tareas Recientes (2026-02-10)

### ✅ TAREA 22: Code Quality Refactor - Production-Ready (Modular + Dependency-Aware)

**Archivo:** `22_code_quality_refactor.yml`
**Estado:** ✅ CREADO (Versión 4.1 - Dependency-Aware Processing Order)
**Prioridad:** P1 - IMPORTANTE
**Horas:** 30-40h (estimación realista)
**Depends on:** Ninguna (independiente)

**Objetivo:** Revisar TODOS los archivos de `app/` para:
1. Usar config modular centralizada
2. Eliminar valores hardcoded
3. Usar librerías especializadas (numpy, pandas, scipy)
4. **PRODUCTION-READY**: No se aceptan implementaciones incompletas
5. **DEPENDENCY-AWARE**: Procesar en orden de dependencias para no romper nada

**Sistema Modular:**
- Usa templates de `.ralph/ralph_templates/hats/`
- Scripts de validación en `.ralph/scripts/utils.py`
- Event-driven con triggers/publishes
- Checkpoint con formato estandarizado

**Processing Order (10 fases - V4.1 NEW):**
1. **Config** (app/core/config/) → Otros archivos dependen de get_config()
2. **Interfaces/Protocols** → Implementaciones dependen de protocolos
3. **Utils** → Utilidades base sin dependencias
4. **Models** → Modelos de datos
5. **Core Services** → Servicios core (compliance, validators)
6. **Execution Services** → Ejecución y órdenes
7. **Strategies** → Estrategias de trading
8. **Backtesting** → Motor de backtesting
9. **Analysis** → Análisis y métricas
10. **Remaining** → Archivos restantes

**HATS (4 fases):**
1. **auditor** (`base_processor_hat.yml`) → Inventario ORDENADO + Auditoría
2. **fixer** (`implementer_hat.yml`) → Correcciones file-by-file (en orden)
3. **validator** (`validation_hat.yml`) → Validación final
4. **final_reporter** (`final_reviewer_hat.yml`) → Reporte final

**Quality Gates (todos required=true):**
- `no_hardcoded_decimal` - No Decimal('0.XX') hardcoded
- `no_hardcoded_float` - No 0.XX float hardcoded
- `no_todo_fixme` - No TODO/FIXME/XXX/HACK
- `no_stub_implementations` - No pass # stub
- `no_not_implemented` - No raise NotImplementedError
- `config_usage` - Usar getattr(config.trading, ...)
- `numpy_usage` - Usar numpy para cálculos
- `type_hints` - Type hints en funciones
- `docstrings` - Docstrings en funciones públicas
- `error_handling` - Error handling

**Salida esperada:**
- `.ralph/outputs/CODE_QUALITY_AUDIT.json` - Auditoría
- `.ralph/outputs/CODE_QUALITY_FIXES.json` - Correcciones
- `.ralph/outputs/CODE_QUALITY_FINAL_REPORT.json` - Validación final
- `.ralph/outputs/TASK22_EXECUTIVE_SUMMARY.md` - Resumen ejecutivo

**Validación:**
- grep para hardcoded values (debe retornar vacío)
- grep para incomplete implementations (debe retornar vacío)
- pyright para type hints
- black/isort/ruff para code style

---

### Prompts (Ninguno creado aún)

| Archivo | Estado | Descripción |
|---------|--------|-------------|
| `00_master_orchestrator.md` | ❌ NO CREADO | Prompt del orquestador |
| `01_protocol_interfaces.md` | ❌ NO CREADO | Prompt de interfaces |
| `02_spain_tax_engine.md` | ❌ NO CREADO | Prompt de impuestos |
| `03_trading_decision_logger.md` | ❌ NO CREADO | Prompt de logging |
| `04_risk_validators.md` | ❌ NO CREADO | Prompt de validadores |
| `01_compliance_engine_refactor.md` | ❌ NO CREADO | Prompt de refactor |

---

## 🔍 Análisis Detallado por Tarea

### ✅ TAREA 00: Master Orchestrator

**Archivo:** `00_master_orchestrator.yml`
**Estado:** ✅ CREADO
**Propósito:** Orquestar ejecución de todas las tareas
**Key features:**
- Define 8 fases de ejecución
- Establece dependencias entre tareas
- Crea checkpoint global
- Proporciona 3 estrategias de ejecución

**Salida esperada:**
- Sistema completo implementado
- Checkpoint global con estado de todas las tareas
- Reporte final de ejecución

---

### ✅ TAREA 01: Protocol Interfaces

**Archivo:** `01_protocol_interfaces.yml`
**Estado:** ✅ CREADO
**Prioridad:** P0 - FUNDAMENTAL
**Horas:** 4h
**Depends on:** Nada (es la primera)

**Archivos a crear:**
1. `app/core/protocols/i_pre_trade_validator.py` - Validaciones pre-trade (R1,R2,R4)
2. `app/core/protocols/i_trade_executor.py` - Ejecución de trades
3. `app/core/protocols/i_post_trade_analyzer.py` - Análisis post-trade (R11,R12,R13)
4. `app/core/protocols/i_broker_adapter.py` - Adapter para broker
5. `app/core/protocols/i_spain_tax_engine.py` - Motor impuestos España
6. `app/core/protocols/i_trading_decision_logger.py` - Logger (R15,R28)
7. `app/core/protocols/i_kill_switch_monitor.py` - Monitor drawdown (R2)
8. `app/core/protocols/i_alert_processor.py` - Procesa alertas
9. `app/core/protocols/i_strategy_cycle_runner.py` - Ejecuta ciclos
10. `app/core/protocols/__init__.py` - Exporta todos

**Validación:**
- Todos los Protocol tienen <= 5 métodos (ISP-001)
- Todos usan typing.Protocol (LSP-001)
- Ninguno usa abc.ABC

**Checkpoint:**
```json
{
  "task": "01_protocol_interfaces",
  "status": "completed",
  "files_created": 10,
  "protocols_created": 9,
  "validated": true
}
```

---

### ✅ TAREA 02: Spain Tax Engine

**Archivo:** `02_spain_tax_engine.yml`
**Estado:** ✅ CREADO
**Prioridad:** P0 - CRÍTICA para usuario España
**Horas:** 8h
**Depends on:** 01_protocol_interfaces

**Archivos a crear:**
1. `app/services/tax_efficiency/engines/spain_tax_engine_impl.py` - Implementación principal
2. `app/services/tax_efficiency/engines/modelo_720_generator.py` - Modelo 720
3. `app/services/tax_efficiency/engines/spain_dividend_tax.py` - Dividendos UE/No-UE

**Archivos a modificar:**
1. `app/services/tax_efficiency/engines/spain_tax_engine.py` - Actualizar fachada

**Reglas implementadas:**
- IRPF-001: Progresivo 19/21/23%
- DIV-001: UE 0% vs No-UE 19%
- MOD720-001: Modelo 720 > €50k
- LOSS-CF-001: Carryforward 4 años

**Checkpoint:**
```json
{
  "task": "02_spain_tax_engine",
  "status": "completed",
  "spain_tax_rules_implemented": 4,
  "validated": true
}
```

---

### ✅ TAREA 03: Trading Decision Logger

**Archivo:** `03_trading_decision_logger.yml`
**Estado:** ✅ CREADO
**Prioridad:** P0 - CRÍTICA para Hacienda
**Horas:** 6h
**Depends on:** 01_protocol_interfaces

**Archivos a crear:**
1. `app/services/logging/log_entry.py` - Entrada de log inmutable
2. `app/services/logging/append_only_log.py` - Log append-only
3. `app/services/logging/trading_decision_logger.py` - Logger principal

**Reglas implementadas:**
- R15: Logging append-only + correlation ID
- R28: Registro para Hacienda (5 años)
- LOG-001: Structured logging
- AUD-001: Audit trail completo

**Checkpoint:**
```json
{
  "task": "03_trading_decision_logger",
  "status": "completed",
  "r15_implemented": true,
  "r28_implemented": true,
  "validated": true
}
```

---

### ✅ TAREA 04: Risk Validators

**Archivo:** `04_risk_validators.yml`
**Estado:** ✅ CREADO
**Prioridad:** P0 - CRÍTICAS para riesgo
**Horas:** 8h
**Depends on:** 01_protocol_interfaces

**Archivos a crear:**
1. `app/services/risk/validators/kelly_criterion_validator.py` - R1
2. `app/services/risk/validators/drawdown_validator.py` - R2
3. `app/services/risk/validators/risk_reward_validator.py` - R4

**Archivos a modificar:**
1. `app/services/position_sizing_engine.py` - Integrar Kelly validator

**Reglas implementadas:**
- R1: Kelly Criterion + 2% max
- R2: Drawdown 15% stop
- R3: Stop Loss SIEMPRE
- R4: R:R 2:1 mínimo

**Checkpoint:**
```json
{
  "task": "04_risk_validators",
  "status": "completed",
  "risk_validators_implemented": 3,
  "validated": true
}
```

---

### ⚠️ TAREA 05: Position Management (NO CREADA AÚN)

**Prioridad:** P1
**Horas:** 12h
**Depends on:** 01_protocol_interfaces

**Archivos a crear:**
1. `app/services/position_management/trailing_stop_manager.py` - R11
2. `app/services/position_management/partial_take_profit.py` - R12
3. `app/services/position_management/pyramiding_manager.py` - R13

**Reglas implementadas:**
- R11: Trailing Stop Dinámico
- R12: Take Profit Parcial
- R13: Pyramiding (solo ganadores)

---

### ⚠️ TAREA 06: Reconciliation Daily (NO CREADA AÚN)

**Prioridad:** P1
**Horas:** 6h
**Depends on:** 01_protocol_interfaces

**Archivos a crear:**
1. `app/services/reconciliation/daily_reconciler.py`
2. `app/services/reconciliation/discrepancy_detector.py`

**Reglas implementadas:**
- R16: Reconciliación diaria

---

### ⚠️ TAREA 07: Capital Phase Manager (NO CREADA AÚN)

**Prioridad:** P1
**Horas:** 6h
**Depends on:** Nada

**Archivos a crear:**
1. `app/services/capital/capital_phase_manager.py`
2. `app/services/capital/phase_config.py`

**Reglas implementadas:**
- R25: Survival phase (1k-10k)
- R26: Growth phase (10k-50k)
- R27: Optimization phase (50k-500k)

---

### ⚠️ TAREA 08: Broker Adapters (NO CREADA AÚN)

**Prioridad:** P0
**Horas:** 16h
**Depends on:** 01_protocol_interfaces

**Archivos a crear:**
1. `app/services/live_trading/broker_adapters/ibkr_adapter_spain.py`
2. `app/services/live_trading/broker_adapters/currency_converter.py`

**Archivos a modificar:**
1. `app/services/live_trading/broker_adapters/ib_adapter.py` - Completar TODOs

**Objetivo:** IBKR adapter funcional para España (EUR, IBEX35)

---

### ✅ TAREA 09: Compliance Engine Refactor

**Archivo:** `01_compliance_engine_refactor.yml` (renombrar a 09)
**Estado:** ✅ ACTUALIZADO
**Prioridad:** P0 - COORDINADOR PRINCIPAL
**Horas:** 16h
**Depends on:** 01, 02, 03, 04

**Archivos a crear:**
1. `app/core/compliance_engine_refactored.py`
2. `app/core/trade_result.py`
3. `app/core/cycle_result.py`

**Archivos a modificar:**
1. `app/core/compliance_engine.py` - Añadir métodos principales

**Métodos a implementar:**
- `process_alert()` - Procesa alertas de mercado
- `execute_trade()` - Ejecuta trade con compliance
- `run_strategy_cycle()` - Ejecuta ciclo completo

---

### ⚠️ TAREAS 10-12: Integration Layer (NO CREADAS AÚN)

**Prioridad:** P0
**Horas:** 12h (4h cada una)
**Depends on:** 09

**Tarea 10:** `10_execution_engine_integration.yml`
- Modificar: `app/strategies/execution_engine.py`
- Usar: `ComplianceEngine.run_strategy_cycle()`

**Tarea 11:** `11_order_manager_integration.yml`
- Modificar: `app/services/live_trading/order_manager.py`
- Usar: `ComplianceEngine.execute_trade()`

**Tarea 12:** `12_trading_bridge_integration.yml`
- Modificar: `app/services/live_trading/trading_bridge_orchestrator.py`
- Usar: `ComplianceEngine.process_alert()`

---

### ⚠️ TAREA 13: Live Trading CLI (NO CREADA AÚN)

**Prioridad:** P0
**Horas:** 8h
**Depends on:** 09, 12

**Archivos a crear:**
1. `scripts/start_live_trading.py`
2. `scripts/validate_config.py`
3. `scripts/validate_broker_connection.py`

---

### ⚠️ TAREAS 14-16: User Interface Layer (NO CREADAS AÚN)

**Prioridad:** P1
**Horas:** 24h total

**Tarea 14:** `14_user_config_single_user.yml` (6h)
- Config simplificada usuario único

**Tarea 15:** `15_alerting_telegram.yml` (6h)
- Alertas via Telegram

**Tarea 16:** `16_simple_dashboard.yml` (12h)
- Dashboard simple para P&L, posiciones

---

### ⚠️ TAREA 17: Backtest Fixes (NO CREADA AÚN)

**Prioridad:** P0
**Horas:** 12h
**Depends on:** Nada

**Archivos a crear:**
1. `app/backtesting/validation/pnl_validator.py`
2. `app/backtesting/validation/drawdown_validator.py`

**Archivos a modificar:**
1. `app/backtesting/execution_engine.py` - Fix bugs
2. `app/backtesting/report_generator.py` - Añadir métricas

---

### ⚠️ TAREA 18: Additional Rules (NO CREADA AÚN)

**Prioridad:** P2 (Opcional)
**Horas:** 24h
**Depends on:** 01

**Archivos a crear:**
1. `app/backtesting/validation/overfitting_guard.py` - R6
2. `app/services/risk/monte_carlo_analyzer.py` - R7
3. `app/services/execution_timing.py` - R9
4. `app/services/psychology/emotion_control_guard.py` - R17
5. `app/services/journal/trading_journal.py` - R18
6. `app/services/testing/ab_tester.py` - R23

---

### ⚠️ TAREA 19: Security Hardening (NO CREADA AÚN)

**Prioridad:** P1
**Horas:** 8h
**Depends on:** Nada

**Archivos a crear:**
1. `app/services/security/api_key_manager.py`
2. `app/services/security/secrets_manager_impl.py`
3. `app/services/security/key_rotation.py`

**Reglas implementadas:**
- R29: Security hardening

---

### ⚠️ TAREA 20: Testing Integration (NO CREADA AÚN)

**Prioridad:** P0
**Horas:** 16h
**Depends on:** 09, 10, 11, 12, 02

**Archivos a crear:**
1. `tests/integration/test_compliance_engine_full_flow.py`
2. `tests/integration/test_execution_engine_integration.py`
3. `tests/integration/test_order_manager_integration.py`
4. `tests/integration/test_trading_bridge_integration.py`
5. `tests/integration/test_spain_tax_integration.py`

---

## 📊 Resumen de Estado

### Tareas YAML Creadas: 6/18 (33%)

- ✅ 00_master_orchestrator.yml
- ✅ 01_protocol_interfaces.yml
- ✅ 02_spain_tax_engine.yml
- ✅ 03_trading_decision_logger.yml
- ✅ 04_risk_validators.yml
- ✅ 01_compliance_engine_refactor.yml (actualizado)

### Tareas YAML Pendientes: 12/18 (67%)

- ❌ 05_position_management.yml
- ❌ 06_reconciliation_daily.yml
- ❌ 07_capital_phase_manager.yml
- ❌ 08_broker_adapters.yml
- ❌ 09_compliance_engine_refactor.yml (renombrar de 01)
- ❌ 10_execution_engine_integration.yml
- ❌ 11_order_manager_integration.yml
- ❌ 12_trading_bridge_integration.yml
- ❌ 13_live_trading_cli.yml
- ❌ 14_user_config_single_user.yml
- ❌ 15_alerting_telegram.yml
- ❌ 16_simple_dashboard.yml
- ❌ 17_backtest_fixes.yml
- ❌ 18_additional_rules.yml
- ❌ 19_security_hardening.yml
- ❌ 20_testing_integration.yml

### Prompts Creados: 0/6 (0%)

- ❌ 00_master_orchestrator.md
- ❌ 01_protocol_interfaces.md
- ❌ 02_spain_tax_engine.md
- ❌ 03_trading_decision_logger.md
- ❌ 04_risk_validators.md
- ❌ 01_compliance_engine_refactor.md

---

## 🚀 Próximos Pasos

### Opción A: Comenzar con Foundation Layer (RECOMENDADO)

```bash
# 1. Crear prompts para tareas 01-04
mkdir -p .ralph/ralph_tasks/prompts

# 2. Ejecutar primera tarea
ralph run .ralph/ralph_tasks/01_protocol_interfaces.yml

# 3. Validar y continuar
ralph run .ralph/ralph_tasks/02_spain_tax_engine.yml
ralph run .ralph/ralph_tasks/03_trading_decision_logger.yml
ralph run .ralph/ralph_tasks/04_risk_validators.yml
```

### Opción B: Ejecutar Orquestador Principal

```bash
# Ejecutar todas las tareas en orden
ralph run .ralph/ralph_tasks/00_master_orchestrator.yml
```

### Opción C: Crear tareas restantes primero

```bash
# Crear YAML para tareas 05-20
# (ver documentación en ralph_tasks/README.md)
```

---

**Última actualización:** 2026-02-21
**Estado:** ✅ Inventario completo - 22 tareas YAML creadas

---

## 🔧 TAREA 23: Profile Backtest Metrics Fix (NUEVA - 2026-02-21)

**Archivo:** `23_profile_backtest_metrics_fix.yml`
**Estado:** ✅ CREADO
**Prioridad:** P0 - CRITICO
**Horas:** 16h
**Depends on:** 17_backtest_fixes (validadores P&L y drawdown)

### Problema Actual
```
Baseline Sharpe: -1099.01 (extremadamente pobre)
Optimized Sharpe: -166.53 (84.8% mejora pero todavia pobre)
Return: N/A
Max Drawdown: -18.29%
Status: REJECTED
```

### Objetivo
Lograr metricas aceptables para que el profile investor sea APPROVED:
- Sharpe Ratio > 0.5
- Return > 0%
- Win Rate > 45%
- Ready for Paper Trading = True

### HATS (5 fases)
1. **metrics_diagnostician** - Diagnostica problemas con Sharpe ratio
2. **params_fixer** - Arregla parametros de optimizacion
3. **strategy_fixer** - Arregla configuracion de estrategia
4. **validator** - Valida que los fixes mejoren las metricas
5. **final_reviewer** - Revision final y documentacion

### Archivos a Modificar
1. `app/backtesting/performance_calculator.py` - Sharpe calculation
2. `app/backtesting/profile_batch_backtester.py` - Parameter ranges
3. `config/profile_optimization.yaml` - Optimization config
4. `config/strategies/momentum_modular.yaml` - Strategy config
5. `config/profile_batch_backtest.yaml` - Backtest config

### Salida Esperada
- `.ralph/outputs/23_metrics_diagnosis.md` - Diagnostico
- `.ralph/outputs/23_metrics_fix_summary.md` - Resumen de fixes
- Profile backtest con Sharpe > 0.5 y APPROVED

### Ejecucion
```bash
ralph run .ralph/ralph_tasks/23_profile_backtest_metrics_fix.yml
```

---
