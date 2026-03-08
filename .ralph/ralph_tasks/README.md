# Ralph Tasks - Master Orchestrator v10.0

**Actualizado:** 2026-03-08

## Master Orchestrator v10.0

**Flujo:**
1. **VERIFY RULES** → Verifica `rules/` tiene todas las reglas (R1-R4, R15, R28, IRPF, SOLID)
2. **AUDIT COMPONENTS** → Lee source + requirements + rules → Verifica cumplimiento → Arregla si falta
3. **QA VALIDATION** → black, isort, ruff
4. **FINAL REPORT** → Genera audit.md

## Ejecutar

```bash
ralph run -P .ralph/ralph_tasks/prompts/00_master_orchestrator.md
```

## Output

`.ralph/outputs/production_readiness_audit.md`
