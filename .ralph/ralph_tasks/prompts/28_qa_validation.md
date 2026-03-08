# QA Validation - Prompt

**Tarea ID:** 28_qa_validation
**Propósito:** Eliminar todos los errores de QA
**Tiempo estimado:** 6 horas
**Prioridad:** P0 (Crítica)

---

## OBJETIVO

Proyecto sin errores de QA (linting, typing, tests).

## HERRAMIENTAS

| Herramienta | Propósito | Comando |
|-------------|----------|---------|
| black | Formato | `black app/ --check` |
| isort | Imports | `isort app/ --check-only` |
| ruff | Linting | `ruff check app/` |
| mypy | Types | `mypy app/ --ignore-missing-imports` |
| pytest | Tests | `pytest tests/ -v` |

## FLUJO

1. Ejecutar todas las validaciones
2. Listar errores
3. Corregir errores
4. Re-validar
5. Repetir hasta 0 errores

## ERRORES COMUNES

### Ruff
- F401: Imported but unused
- E501: Line too long
- F541: f-string without placeholders

### Mypy
- missing type hints
- incompatible types
- missing return statement

### Pytest
- Import errors
- Fixture errors
- Assertion failures

## SUCCESS CRITERIA

```bash
black app/ --check && \
isort app/ --check-only && \
ruff check app/ && \
mypy app/ --ignore-missing-imports && \
pytest tests/ -v
```

All commands exit with 0.
