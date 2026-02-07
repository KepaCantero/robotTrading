# TAREA: Auditoría GAP Real con Ralph Orchestrator

## OBJETIVO

Ejecutar auditoría REAL de **812 archivos Python** en `app/` usando **TODAS** las herramientas de validación de `check_all.sh`, procesar en 147 batches, y marcar como `PASSED` SOLO cuando **TODAS** las validaciones pasan.

## REGLAS DE ORO

1. ❌ **NO** marcar PASSED si hay cualquier error en CUALQUIER herramienta
2. ❌ **NO** confiar en tu "juicio" - solo confía en las herramientas
3. ❌ **NO** inventar resultados de validación
4. ✅ **SOLO** marcar PASSED si `validate_file_complete.sh` devuelve `success: true`
5. ✅ **EJECUTAR** las herramientas, no solo verificar sus resultados

---

## POR CADA ARCHIVO:

### Paso 1: Clasificar reglas aplicables
```bash
python scripts/smart_rule_classifier.py <archivo>
```

### Paso 2: Ejecutar validación COMPLETA (OBLIGATORIO)
```bash
scripts/validate_file_complete.sh <archivo>
```

**Esto EJECUTA las siguientes herramientas:**
- ✅ **Black** - Formateador PEP8
- ✅ **Isort** - Organizador de imports
- ✅ **Ruff** - Linter ultra-rápido
- ✅ **Flake8** - Linter clásico
- ✅ **Pylint** - Análisis profundo
- ✅ **Mypy** - Type checker (SOLO el archivo, no imports)
- ✅ **Bandit** - Security scanner
- ✅ **Radon** - Complejidad ciclomática (CC < 10)

**Devuelve JSON:**
```json
{
  "file": "app/path/file.py",
  "checks": {
    "black": {"status": "passed"},
    "isort": {"status": "passed"},
    "ruff": {"status": "passed"},
    "flake8": {"status": "passed"},
    "pylint": {"status": "passed"},
    "mypy": {"status": "passed"},
    "bandit": {"status": "passed"},
    "radon": {"status": "passed", "cc": 3}
  },
  "summary": {
    "total_checks": 8,
    "passed": 8,
    "failed": 0,
    "success": true
  }
}
```

### Paso 3: Si hay errores
```bash
# a. Intentar auto-fix (formateo)
.venv/bin/black <archivo>
.venv/bin/isort <archivo>
.venv/bin/ruff check <archivo> --fix

# b. Re-validar
scripts/validate_file_complete.sh <archivo>

# c. Si aún hay errores → ARREGLAR MANUALMENTE el código
# d. Re-validar hasta success: true
```

### Paso 4: SOLO cuando success: true
- Marcar en checkpoint como PASSED
- Actualizar `.requirements/<archivo>.requirements.md`

---

## FINAL REVIEWER - INCLUYE TESTS

Al completar todos los batches, ejecutar:

```bash
# 1. Verificar muestra de 50 archivos
cat .ralph/batches.json | jq -r '.batches[].files[]' | \
  shuf -n 50 | while read f; do
    scripts/validate_file_complete.sh "$f" | jq -r '.summary.success'
  done | grep -c false
# Debe retornar 0

# 2. EJECUTAR TESTS OBLIGATORIAMENTE
.venv/bin/pytest tests/ -v --tb=short
# TODOS los tests deben PASAR
```

Si TODO está limpio:
```
ralph emit "audit.final_summary" "all_validated"
Output: **GAP_AUDIT_COMPLETE**
```

Si hay errores:
```
ralph emit "audit.failed" "found_errors=<cantidad>"
```

---

## MÉTRICAS DE ÉXITO

### Por archivo (8 checks obligatorios):
- [ ] **Black**: passed
- [ ] **Isort**: passed (0 cambios pendientes)
- [ ] **Ruff**: passed (0 errores)
- [ ] **Flake8**: passed (0 errores)
- [ ] **Pylint**: passed (0 errores)
- [ ] **Mypy**: passed (0 errores)
- [ ] **Bandit**: passed (0 issues HIGH/MEDIUM)
- [ ] **Radon**: passed (CC < 10)

### Tests:
- [ ] **Pytest**: TODOS los tests pasan

---

## Output final: **GAP_AUDIT_COMPLETE**
