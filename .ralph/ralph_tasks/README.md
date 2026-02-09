# 📋 Ralph Tasks - Plan de Implementación Optimizado

**Fecha:** 2026-02-08
**Objetivo:** Implementar toda la funcionalidad descubierta en docs con el MÍNIMO número de refactorings

---

## 🚀 Inicio Rápido

### Ejecutar TODO el sistema:

```bash
# Opción A: Orquestador principal (RECOMENDADO)
ralph run .ralph/ralph_tasks/00_master_orchestrator.yml

# Opción B: Ejecutar fase 1 (Foundation) primero
ralph run .ralph/ralph_tasks/01_protocol_interfaces.yml
ralph run .ralph/ralph_tasks/02_spain_tax_engine.yml
ralph run .ralph/ralph_tasks/03_trading_decision_logger.yml
ralph run .ralph/ralph_tasks/04_risk_validators.yml
```

### Inventario de Tareas:

**Ver inventario completo:** [`TASKS_INVENTORY.md`](./TASKS_INVENTORY.md)

- **Tareas YAML creadas:** 6/18 (33%)
- **Tareas YAML pendientes:** 12/18 (67%)
- **Prompts creados:** 0/6 (0%)

---

## 🎯 Estrategia de Agrupación

### Layer-First Approach
```
1. Foundation Layer (Interfaces)   → Todas las tareas dependen de esta
2. Service Layer (Implementaciones) → Lógica de negocio independiente
3. Infrastructure Layer (Adapters)  → Conectores externos
4. Coordinator Layer (Orquestadores) → Coordina servicios
5. Integration Layer (Conexiones)    → Conecta coordinadores con código existente
6. Interface Layer (CLI, Dashboard) → Usuario final
7. Validation Layer (Tests)          → Garantiza calidad
```

---

## 📊 Resumen de Tareas

| Prioridad | Tareas | Horas | Descripción |
|-----------|--------|-------|-------------|
| **P0 (Críticas)** | 10 | ~90h | Bloquean producción |
| **P1 (Importantes)** | 7 | ~54h | Mejoras significativas |
| **P2 (Opcionales)** | 1 | ~24h | Optimizaciones |
| **TOTAL** | **18** | **~168h** | **~4-5 semanas** |

---

## 🔥 P0 - Tareas Críticas (Producción)

### Foundation Layer

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **01_protocol_interfaces** | 4h | Interfaces Protocol para SOLID | 9 Protocol interfaces |
| **02_spain_tax_engine** | 8h | Motor impuestos España | IRPF 19/21/23%, UE dividends |
| **03_trading_decision_logger** | 6h | Logger append-only (R15, R28) | Correlation ID logging |
| **04_risk_validators** | 8h | Validadores R1, R2, R4 | Kelly, Drawdown, R:R |

### Infrastructure Layer

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **08_broker_adapters** | 16h | IBKR adapter para España | TODO completados, EUR support |

### Service Layer (Position Management)

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **05_position_management** | 12h | R11, R12, R13 | Trailing stop, TP parcial, Pyramiding |

### Coordinator Layer

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **09_compliance_engine_refactor** | 16h | Añadir métodos principales | process_alert, execute_trade, run_strategy_cycle |

### Integration Layer

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **10_execution_engine_integration** | 4h | ExecutionEngine → ComplianceEngine | Usa run_strategy_cycle() |
| **11_order_manager_integration** | 4h | OrderManager → ComplianceEngine | Usa execute_trade() |
| **12_trading_bridge_integration** | 4h | TradingBridge → ComplianceEngine | Usa process_alert() |

### User Interface Layer

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **13_live_trading_cli** | 8h | Script CLI para live trading | start_live_trading.py |

### Validation Layer

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **17_backtest_fixes** | 12h | Corregir bugs críticos | Drawdowns imposibles, P&L |
| **20_testing_integration** | 16h | Tests de integración | Full flow tests |

---

## ⚡ P1 - Tareas Importantes

### Service Layer

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **06_reconciliation_daily** | 6h | R16 - Reconciliación diaria | Broker vs sistema |
| **07_capital_phase_manager** | 6h | R25-R27 - Fases de capital | Survival, Growth, Optimization |

### Configuration Layer

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **14_user_config_single_user** | 6h | Config usuario único | Simplifica multi-tenant |

### Notification Layer

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **15_alerting_telegram** | 6h | Alertas via Telegram | Usuario único |

### User Interface Layer

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **16_simple_dashboard** | 12h | Dashboard simple | P&L, posiciones, métricas |

### Security Layer

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **19_security_hardening** | 8h | R29 - Security hardening | Secrets manager, encriptación |

---

## 🔧 P2 - Tareas Opcionales

| Tarea | Horas | Descripción | Output |
|-------|-------|-------------|--------|
| **18_additional_rules** | 24h | R6, R7, R9, R14, R17-R24 | Overfitting, Monte Carlo, emocional |

---

## 📅 Orden de Implementación Recomendado

### Sprint 1: Foundation (Semana 1)
```
Day 1-2:  01_protocol_interfaces    (4h)
Day 3-4:  02_spain_tax_engine       (8h)
Day 5-6:  03_trading_decision_logger (6h)
Day 7-8:  04_risk_validators        (8h)
```

### Sprint 2: Infrastructure (Semana 2)
```
Day 9-12: 08_broker_adapters        (16h)
Day 13:   17_backtest_fixes         (12h - empieza)
```

### Sprint 3: Services (Semana 2-3)
```
Day 14:   17_backtest_fixes         (termina)
Day 15-17: 05_position_management   (12h)
Day 18:   06_reconciliation_daily   (6h)
Day 19:   07_capital_phase_manager  (6h)
```

### Sprint 4: Coordinator (Semana 3-4)
```
Day 20-23: 09_compliance_engine_refactor (16h)
Day 24:   10_execution_engine_integration  (4h)
Day 25:   11_order_manager_integration     (4h)
Day 26:   12_trading_bridge_integration   (4h)
```

### Sprint 5: Interface & Testing (Semana 4-5)
```
Day 27-28: 13_live_trading_cli       (8h)
Day 29:   20_testing_integration     (16h - empieza)
```

### Sprint 6: Polish (Semana 5)
```
Day 30-31: 20_testing_integration     (termina)
Day 32-33: 14_user_config_single_user (6h)
Day 34:   15_alerting_telegram       (6h)
Day 35-37: 16_simple_dashboard       (12h)
Day 38-39: 19_security_hardening     (8h)
```

### Sprint 7: Optional (Semana 6+)
```
Day 40+:  18_additional_rules        (24h)
```

---

## 🔗 Dependencias Críticas

```
01_protocol_interfaces (Foundation)
    ↓
├─→ 02_spain_tax_engine
├─→ 03_trading_decision_logger
├─→ 04_risk_validators
├─→ 08_broker_adapters
└─→ 05_position_management
        ↓
09_compliance_engine_refactor (Coordinator - depende de 01, 02, 03, 04)
    ↓
├─→ 10_execution_engine_integration
├─→ 11_order_manager_integration
└─→ 12_trading_bridge_integration
        ↓
13_live_trading_cli + 20_testing_integration
```

---

## ✅ Checklist por Tarea

Antes de marcar una tarea como COMPLETADA:

- [ ] Todos los archivos creados validan con `python scripts/utils.py validate`
- [ ] No hay flags `@todo`, `@skip-import`, `@clarify` sin resolver
- [ ] Tests manuales pasan
- [ ] Documentación actualizada
- [ ] Checkpoint JSON creado con `success: true`

---

## 📈 Métricas de Progreso

### Foundation Layer
- [ ] 01_protocol_interfaces
- [ ] 02_spain_tax_engine
- [ ] 03_trading_decision_logger
- [ ] 04_risk_validators

**Progreso:** 0/4 (0%)

### Critical Integration
- [ ] 08_broker_adapters
- [ ] 09_compliance_engine_refactor
- [ ] 10_execution_engine_integration
- [ ] 11_order_manager_integration
- [ ] 12_trading_bridge_integration

**Progreso:** 0/5 (0%)

### Production Ready
- [ ] 13_live_trading_cli
- [ ] 17_backtest_fixes
- [ ] 20_testing_integration

**Progreso:** 0/3 (0%)

---

**Última actualización:** 2026-02-08
**Estado:** ✅ Plan optimizado creado - 18 tareas, ~168 horas
