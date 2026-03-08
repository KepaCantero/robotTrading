# Master Orchestrator - Production Ready v6.0

**Version:** 6.0
**Accion:** EJECUTA validaciones y formateo
**Tiempo:** ~10-15 minutos

---

## OBJETIVO

Ejecutar validaciones reales de production readiness. El agente DEBE ejecutar los comandos bash indicados en cada hat.

---

## FLUJO (5 Hats)

```
1. VERIFY COMPONENTS
   - EJECUTA: ls commands para verificar archivos
   - REPORTA: estado de cada componente
   - EMITE: master.components_verified
        |
        v
2. RUN BLACK
   - EJECUTA: black app --line-length 100
   - REPORTA: archivos formateados
   - EMITE: master.black_done
        |
        v
3. RUN ISORT
   - EJECUTA: isort app --profile black
   - REPORTA: resultado
   - EMITE: master.isort_done
        |
        v
4. RUN RUFF
   - EJECUTA: ruff check app --fix
   - REPORTA: errores antes/después
   - EMITE: master.ruff_done
        |
        v
5. GENERATE REPORT
   - CREA: .ralph/outputs/production_readiness_audit.md
   - EMITE: master.complete
```

---

## REGLAS CRITICAS

1. **EJECUTA los comandos** - No solo los leas
2. **REPORTA resultados** - Muestra la salida de cada comando
3. **NO CREES DUPLICADOS** - Solo verifica y formatea
4. **USA LAS RUTAS CORRECTAS:**
   - SpainTaxEngine: `app/services/tax_efficiency/engines/spain_tax_engine.py`
   - DecisionLogger: `app/infrastructure/logging/trading_decision_logger.py`
   - CentralConfig: `app/shared/config/centralized_config.py`

---

## OUTPUT ESPERADO

Al finalizar, debe existir:
- `.ralph/outputs/production_readiness_audit.md` con el reporte completo
- Codigo formateado (black, isort)
- Linting reducido (ruff)

---

## COMANDO PARA EJECUTAR

```bash
cd /Users/kepa.cantero/Projects/algoTrading
ralph run -P .ralph/ralph_tasks/prompts/00_master_orchestrator.md
```
