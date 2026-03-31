# Master Orchestrator AAA v14.0 - PRODUCTION CODE ONLY

**OBJETIVO:** Llevar el codigo de `app/` a nivel AAA (Production Ready).
**METODO:** Cada accion se VERIFICA con un comando real. Sin conjeturas. Sin atajos.

---

## ALCANCE: SOLO `app/`

- ANALIZA: `app/`, `config/`, `scripts/`
- IGNORA: `tests/`, `.venv/`, `__pycache__/`, `htmlcov/`, `logs/`

---

## ANTI-ALUCINACION (inyectado por guardrails)

Antes de CADA accion:
1. Si vas a decir "pasa" - ejecuta el comando primero
2. Si vas a decir "existe" - haz find o ls primero
3. Si vas a modificar un archivo - leelo entero primero
4. Si vas a crear un import - verifica que el modulo existe con python -c
5. Despues de CADA cambio - ejecuta black + isort + ruff sobre el archivo

---

## FLUJO DE HATS

```
aaa.start
  -> clean_start (reset estado)
  -> structural_fix (duplicados, imports)
  -> requirements_generator (generar/verificar .requirements/)
  -> production_audit (cada archivo vs su .requirements/)
  -> architecture_audit (SOLID, layers, hardcoded)
  -> qa_enforcement (black/isort/ruff hasta 0)
  -> security (secrets, injection, gitignore)
  -> final_report (reporte AAA)
  -> AAA_PRODUCTION_READY
```

---

## FUENTES DE VERDAD

| Fuente | Ubicacion |
|--------|-----------|
| Codigo produccion | `app/` |
| Requirements por archivo | `.requirements/app/` |
| Reglas de trading | `config/rules/trading/` |
| Documentacion | `.ralph/docs/` |

---

## VERIFICACION FINAL

Antes de emitir AAA_PRODUCTION_READY:

```bash
black app/ --check && echo "BLACK: PASS" || echo "BLACK: FAIL"
isort app/ --check-only && echo "ISORT: PASS" || echo "ISORT: FAIL"
ruff check app/ && echo "RUFF: PASS" || echo "RUFF: FAIL"
python -c "import app; print('IMPORTS: PASS')" 2>&1
grep -r "TODO\|FIXME\|XXX\|HACK" app/ --include="*.py" -c 2>/dev/null || echo "NO PLACEHOLDERS"
grep -rn "api_key\s*=\s*['\"]\|password\s*=\s*['\"]" app/ --include="*.py" || echo "NO SECRETS"
```

TODOS deben pasar. Si uno falla: FIX, no emitir.

---

## NO EJECUTAR BACKTESTS

Este orquestador NO ejecuta backtests. Solo valida codigo de produccion.

---

## EJECUTAR

```bash
cd /Users/kepa.cantero/Projects/algoTrading
ralph run -c .ralph/ralph_tasks/00_master_orchestrator.yml
```
