# Master Orchestrator - Verify & Fix

**Version:** 5.0
**Accion:** VERIFICA PRIMERO, luego formatea
**Tiempo:** ~5-10 minutos

---

## OBJETIVO

Verificar que existe ANTES de hacer nada. NO crear duplicados.

---

## FLUJO (4 Hats)

```
1. VERIFY EXISTING COMPONENTS
   - Verifica: SpainTaxEngine EXISTE
   - Verifica: TradingDecisionLogger EXISTE
   - Verifica: CentralConfig EXISTE
   - Verifica: Protocol interfaces
   - NO CREAR NADA - Solo verificar
        |
        v
2. FORMAT CODE
   - Ejecuta: black app --line-length 100
   - Ejecuta: isort app --profile black
        |
        v
3. FIX LINTING
   - Ejecuta: ruff check app --fix
        |
        v
4. FINAL REPORT
   - Genera: production_readiness_audit.md
   - Marca: master.complete
```

---

## RUTAS CORRECTAS (Ya existen)

| Componente | Ubicacion Real |
|------------|----------------|
| SpainTaxEngine | `app/services/tax_efficiency/engines/spain_tax_engine.py` |
| DecisionLogger | `app/infrastructure/logging/trading_decision_logger.py` |
| CentralConfig | `app/shared/config/centralized_config.py` |
| Protocols | `app/core/protocols/` |
| RiskValidators | `app/services/risk/validators/` |

---

## REGLA CRITICA

**NO CREAR DUPLICADOS**

Si un archivo ya existe:
- NO crear otro
- NO modificarlo
- Solo reportar que existe

---

## OUTPUT

- Codigo formateado (black, isort)
- Linting arreglado (ruff)
- `.ralph/outputs/production_readiness_audit.md`
- Event: `master.complete`
