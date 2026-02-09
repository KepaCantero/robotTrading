# 🎯 Master Orchestrator - Prompt

**Tarea ID:** 00_master_orchestrator
**Propósito:** Orquestar la ejecución de TODAS las tareas Ralph en orden correcto
**Tiempo estimado:** ~168 horas (4-5 semanas)

---

## 📋 OBJETIVO

Ejecutar las 18 tareas Ralph en el orden correcto, respetando dependencias, y generar un reporte final del estado del sistema.

---

## 🎯 ESTRATEGIA DE EJECUCIÓN

### Fase 1: Foundation Layer (CRÍTICO - empezar aquí)

**Tiempo:** ~26 horas
**Tareas:** 01, 02, 03, 04
**Dependencias:** Ninguna (01 es base para todo)

1. **01_protocol_interfaces** (4h)
   - Crear 9 Protocol interfaces
   - Validar ISP (< 5 métodos por interfaz)
   - Validar LSP (usar typing.Protocol, no ABC)

2. **02_spain_tax_engine** (8h)
   - Implementar IRPF progresivo 19/21/23%
   - Implementar dividendos UE 0% vs No-UE 19%
   - Implementar Modelo 720 > €50k

3. **03_trading_decision_logger** (6h)
   - Implementar logger append-only
   - Implementar correlation ID
   - Implementar exportación para Hacienda (5 años)

4. **04_risk_validators** (8h)
   - Implementar Kelly Criterion + 2% max
   - Implementar Drawdown 15% stop
   - Implementar R:R 2:1 minimum

**Validación de Fase 1:**
```bash
# Verificar que todos los Protocol existen
ls app/core/protocols/i_*.py | wc -l  # Debe ser >= 9

# Verificar que todos usan typing.Protocol
grep -l "class.*Protocol" app/core/protocols/*.py | wc -l  # Debe ser >= 9

# Verificar que ninguno usa abc.ABC
grep "abc.ABC" app/core/protocols/*.py | wc -l  # Debe ser 0

# Verificar validadores
python -c "from app.core.protocols import IPreTradeValidator; print('OK')"
```

### Fase 2: Infrastructure & Services Layer

**Tiempo:** ~40 horas
**Tareas:** 08, 05, 06, 07

1. **08_broker_adapters** (16h) - IBKR adapter para España
2. **05_position_management** (12h) - R11, R12, R13
3. **06_reconciliation_daily** (6h) - R16
4. **07_capital_phase_manager** (6h) - R25-R27

### Fase 3: Coordinator Layer

**Tiempo:** ~16 horas
**Tareas:** 09

1. **09_compliance_engine_refactor** (16h)
   - Añadir `process_alert()`
   - Añadir `execute_trade()`
   - Añadir `run_strategy_cycle()`

### Fase 4: Integration Layer

**Tiempo:** ~12 horas
**Tareas:** 10, 11, 12

1. **10_execution_engine_integration** (4h)
2. **11_order_manager_integration** (4h)
3. **12_trading_bridge_integration** (4h)

### Fase 5: User Interface Layer

**Tiempo:** ~32 horas
**Tareas:** 13, 14, 15, 16

1. **13_live_trading_cli** (8h)
2. **14_user_config_single_user** (6h)
3. **15_alerting_telegram** (6h)
4. **16_simple_dashboard** (12h)

### Fase 6: Validation Layer

**Tiempo:** ~28 horas
**Tareas:** 17, 20

1. **17_backtest_fixes** (12h)
2. **20_testing_integration** (16h)

### Fase 7: Security Layer

**Tiempo:** ~8 horas
**Tareas:** 19

1. **19_security_hardening** (8h)

### Fase 8: Optional (P2)

**Tiempo:** ~24 horas
**Tareas:** 18

1. **18_additional_rules** (24h) - Puede saltarse

---

## ✅ INSTRUCCIONES DE EJECUCIÓN

### Paso 1: Inicializar checkpoint global

```bash
# Crear checkpoint inicial
cat > .ralph/checkpoints/00_master_orchestrator_checkpoint.json << 'EOF'
{
  "master_orchestrator": {
    "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "current_phase": 1,
    "current_task": "01_protocol_interfaces",
    "total_tasks": 18,
    "completed_tasks": 0,
    "failed_tasks": 0,
    "blocked_tasks": 0
  },
  "tasks": {}
}
EOF
```

### Paso 2: Ejecutar tareas en orden

Para cada tarea:
1. Leer archivo YAML de la tarea
2. Verificar dependencias (que tareas previas estén COMPLETED)
3. Ejecutar según instrucciones del YAML
4. Validar outputs
5. Actualizar checkpoint global
6. Continuar a siguiente tarea

### Paso 3: Validación entre fases

Después de completar cada fase:
- Verificar que todos los archivos de la fase validan
- Verificar que no hay flags @todo sin resolver
- Ejecutar tests de integración de la fase
- Solo entonces continuar a siguiente fase

### Paso 4: Reporte final

Generar reporte final con:
- Tareas completadas
- Tareas fallidas
- Archivos creados
- Archivos modificados
- Tests results
- Recomendaciones

---

## 🚨 MANEJO DE ERRORES

### Si una tarea falla:

1. **Detener ejecución**
2. **Marcar tarea como FAILED**
3. **Revisar logs y errores**
4. **Corregir problema**
5. **Reintentar tarea**

### Si una tarea se bloquea:

1. **Identificar dependencia faltante**
2. **Ejecutar tarea dependiente primero**
3. **Reintentar tarea bloqueada**

---

## 📊 CHECKPOINTS

Checkpoint global se actualiza después de cada tarea:

```json
{
  "current_phase": 2,
  "current_task": "08_broker_adapters",
  "completed_tasks": 4,
  "tasks": {
    "01_protocol_interfaces": {"status": "COMPLETED"},
    "02_spain_tax_engine": {"status": "COMPLETED"},
    "03_trading_decision_logger": {"status": "COMPLETED"},
    "04_risk_validators": {"status": "COMPLETED"},
    "08_broker_adapters": {"status": "IN_PROGRESS"}
  }
}
```

---

## 🎯 SUCCESS CRITERIA

El orquestador se considera COMPLETED cuando:

- [ ] Todas las tareas P0 están COMPLETED
- [ ] Todas las tareas P1 están COMPLETED o SKIPPED (con justificación)
- [ ] Tareas P2 son opcionales
- [ ] Reporte final generado
- [ ] Sistema validado end-to-end

---

## 📝 OUTPUT ESPERADO

Archivo final: `.ralph/outputs/MASTER_ORCHESTRATOR_REPORT.md`

Con:
- Resumen ejecutivo
- Tareas completadas
- Archivos creados (lista completa)
- Tests results
- Issues encontrados y resueltos
- Recomendaciones para producción
