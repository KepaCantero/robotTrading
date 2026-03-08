# Master Orchestrator AAA v10.0

**OBJETIVO:** Llevar el código a nivel AAA (Production Ready)

---

## FLUJO (10 Hats en 6 Fases)

```
FASE 1: ESTRUCTURA
├── 1.1 Structural Fix → eliminar duplicados, corregir imports
├── 1.2 Requirements Generator → requirements.md para cada archivo
└── 1.3 Protocol Interfaces → SOLID interfaces
        │
        v
FASE 2: COMPONENTES CORE
├── 2.1 Compliance Engine → R1-R29 validaciones
├── 2.2 Spain Tax → IRPF 19/21/23%
├── 2.3 Risk Validators → Kelly, DD, R:R
└── 2.4 Decision Logger → append-only, correlation ID
        │
        v
FASE 3: CONFIGURACIÓN
└── 3.1 Central Config → mover hardcoded a config
        │
        v
FASE 4: QA
├── 4.1 QA Validation → black, isort, ruff, mypy
└── 4.2 Tests → unit + integration (NO backtests)
        │
        v
FASE 5: SECURITY
└── 5.1 Security Hardening → sin secrets, .env gitignored
        │
        v
FASE 6: FINAL
└── 6.1 Final Cleanup → TODOs resueltos, reporte AAA
```

---

## FUENTES DE VERDAD

| Fuente | Ubicación | Uso |
|--------|-----------|-----|
| **Rules** | `rules/trading/` | Reglas R1-R29 de trading |
| **Docs** | `.ralph/docs/` | Análisis, arquitectura |
| **Requirements** | `.requirements/` | Requirements por archivo |
| **Código** | `app/` | Archivos Python |

---

## CHECKLIST AAA FINAL

Al terminar, el código debe cumplir:

### Estructura
- [ ] Sin archivos duplicados (MD5 verificado)
- [ ] Imports sin errores (sin circulares)
- [ ] `python -c "import app"` funciona

### Requirements
- [ ] Todos los archivos tienen requirements.md
- [ ] Cada requirements.md tiene reglas aplicables

### Arquitectura SOLID
- [ ] SRP: Una responsabilidad por clase
- [ ] OCP: Abierto a extensión, cerrado a modificación
- [ ] LSP: typing.Protocol (no abc.ABC)
- [ ] ISP: Máximo 5 métodos por interfaz
- [ ] DIP: Dependencias inyectadas vía Protocol

### Reglas Trading (R1-R29)
- [ ] R1: Kelly + 2% max position
- [ ] R2: Drawdown 15% stop
- [ ] R3: Stop loss SIEMPRE
- [ ] R4: R:R 2:1 mínimo
- [ ] R15: Append-only logging
- [ ] R28: 5 años retención Hacienda

### Spain Tax
- [ ] IRPF progresivo: 19%, 21%, 23%
- [ ] Dividendos UE: 0% withholding
- [ ] Modelo 720: >€50k extranjeros

### QA
- [ ] black: 0 errores
- [ ] isort: 0 errores
- [ ] ruff: 0 errores
- [ ] mypy: 0 errores

### Tests
- [ ] pytest tests/unit/: 100% pasando
- [ ] pytest tests/integration/: 100% pasando

### Security
- [ ] Sin API keys en código
- [ ] .env en .gitignore
- [ ] Logs sin datos sensibles

---

## NO EJECUTAR BACKTESTS

**IMPORTANTE:** Este orquestador NO ejecuta backtests.
Solo valida que el código cumple las reglas R1-R29.
La ejecución de backtests llevaría demasiado tiempo.

---

## OUTPUT FINAL

`.ralph/outputs/aaa_audit_report.md`

```markdown
# AAA Production Ready Audit

**Fecha:** (ahora)
**Estado:** AAA_PRODUCTION_READY

## Estructura
- Archivos Python: X
- Duplicados eliminados: Y
- Imports corregidos: Z

## Requirements
- Requirements generados: X/X (100%)

## Arquitectura SOLID
- SRP: ✅
- OCP: ✅
- LSP: ✅
- ISP: ✅
- DIP: ✅

## Reglas Trading (R1-R29)
- R1 Kelly: ✅
- R2 Drawdown: ✅
- R4 R:R: ✅
...

## QA
- Black: ✅
- isort: ✅
- Ruff: ✅
- Mypy: ✅

## Tests
- Unit: X/X pasados
- Integration: X/X pasados

## Estado: AAA_PRODUCTION_READY
```

---

## EJECUTAR

```bash
cd /Users/kepa.cantero/Projects/algoTrading
ralph run .ralph/ralph_tasks/00_master_orchestrator.yml
```
