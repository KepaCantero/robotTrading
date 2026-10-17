# AlgoTrading Scripts

Operational, QA, and maintenance scripts for the project.

---

## Structure

```
scripts/
├── check_all.sh               # Full QA pass (formatting, linting, types)
├── run_qa_checks.sh           # Lighter QA runner
├── start_paper_trading.sh     # Start API + dashboard for paper trading
├── stop_paper_trading.sh      # Stop paper-trading processes
├── generate_requirements.py   # Generate .requirements audit files
├── production_audit.py        # Production readiness audit
├── sonarqube.sh               # SonarQube analysis helper
│
├── db/                        # Database init and management
├── deployment/                # AWS / Docker / ELK / production deploys, rollback
├── maintenance/               # validate_file_complete.sh (per-file QA gate)
└── validation/                # Validation scripts
```

## Main Scripts

| Script | Purpose | Usage |
|--------|--------|------|
| `check_all.sh` | Full QA pass over `app/` and `tests/` | `./scripts/check_all.sh` |
| `run_qa_checks.sh` | Run the QA check suite | `./scripts/run_qa_checks.sh` |
| `start_paper_trading.sh` | Start API server + Streamlit dashboard | `./scripts/start_paper_trading.sh` |
| `stop_paper_trading.sh` | Stop paper-trading processes | `./scripts/stop_paper_trading.sh` |
| `maintenance/validate_file_complete.sh` | Per-file QA gate (black, isort, ruff, flake8, pylint, mypy, bandit, radon) | `./scripts/maintenance/validate_file_complete.sh app/file.py` |
| `generate_requirements.py` | Regenerate `.requirements/` audit files | `python scripts/generate_requirements.py` |

Scripts resolve the repository root relative to their own location, so they can be
run from anywhere inside the repo.
