# AlgoTrading Scripts

Operational, QA, and maintenance scripts for the project.

---

## Structure

```
scripts/
├── check_all.sh               # EL script de calidad (solo lectura; --fix aplica)
├── generate_requirements.py   # Sincroniza los specs .requirements/app/ con app/
├── production_audit.py        # Audita código vs spec (GAP/STALE), exit 1 si drift
├── start_paper_trading.sh     # Start API + dashboard for paper trading
├── stop_paper_trading.sh      # Stop paper-trading processes
├── sonarqube.sh               # SonarQube analysis helper
│
├── db/                        # Database init and management
└── deployment/                # AWS / Docker / ELK / production deploys, rollback
```

## Main Scripts

| Script | Purpose | Usage |
|--------|--------|-------|
| `check_all.sh` | QA completo: ruff, black, isort, flake8, pylint, mypy, bandit (+ radon/vulture/semgrep/pip-audit si están) | `./scripts/check_all.sh [--core\|--fix\|--strict]` |
| `generate_requirements.py` | Regenera los 1.170 specs de `.requirements/app/` y borra huérfanos; idempotente | `python scripts/generate_requirements.py [--dry-run]` |
| `production_audit.py` | Verifica cada archivo de `app/` contra su spec: GAP (falta en código) y STALE (spec desactualizada) | `python scripts/production_audit.py` |
| `start_paper_trading.sh` | Start API server + dashboard (NiceGUI) | `./scripts/start_paper_trading.sh` |
| `stop_paper_trading.sh` | Stop paper-trading processes | `./scripts/stop_paper_trading.sh` |

## QA workflow

1. `./scripts/check_all.sh` — reporte de calidad (no toca nada).
2. `./scripts/check_all.sh --fix` — aplica lo mismo que pre-commit (ruff --fix + ruff format).
3. `python scripts/generate_requirements.py` — tras añadir/quitar clases o funciones.
4. `python scripts/production_audit.py` — confirma que código y specs coinciden (lo usa el flujo GAP).

Scripts resolve the repository root relative to their own location, so they can be
run from anywhere inside the repo.
