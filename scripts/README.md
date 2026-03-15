# AlgoTrading Scripts - Clean Architecture

**Last Updated:** 2026-03-15
**Status:** Cleaned and Organized

---

## Structure

```
scripts/
├── validate_file_complete.sh    # Main validation script (used by Ralph)
├── generate_requirements_v2.py  # Generate requirements.md files
├── utils.py                  # Unified CLI
│
├── backtesting/               # Backtesting scripts
│   ├── simple/                # Simple backtests
│   └── optimization/           # Backtests with optimization
│
├── data/                     # Data download scripts
├── db/                      # Database scripts
├── deployment/              # Deployment scripts
├── optimization/            # Hyperparameter optimization
└── validation/              # Validation scripts (if needed)
```

---

## Main Scripts

| Script | Purpose | Usage |
|--------|--------|------|
| `validate_file_complete.sh` | Full QA validation (black, isort, ruff, flake8, pylint, mypy, bandit, radon) | `./scripts/validate_file_complete.sh app/file.py` |
| `generate_requirements_v2.py` | Generate requirements.md for Python files | `python scripts/generate_requirements_v2.py` |
| `utils.py` | Unified CLI for various operations | `python scripts/utils.py validate app/file.py` |

---

## Validation Script Details

### validate_file_complete.sh

**Tools executed:**
1. **black** - Code formatting
2. **isort** - Import sorting
3. **ruff** - Linting
4. **flake8** - Style enforcement
5. **pylint** - Code quality
6. **mypy** - Type checking
7. **bandit** - Security scanning
8. **radon cc** - Cyclomatic complexity (CC < 10)
9. **radon mi** - Maintainability index (MI > 20)
10. **syntax** - Python syntax validation
11. **imports** - AST import validation

**Output:** JSON with pass/fail status for each check

---

## Backtesting Scripts

### Simple Backtests (no optimization)
```bash
python scripts/backtesting/simple/run_simple_backtest.py
python scripts/backtesting/simple/run_baseline_backtest.py
python scripts/backtesting/simple/run_deep_learning_backtest.py
```

### Optimization Backtests
```bash
python scripts/backtesting/optimization/run_comprehensive_backtest.py
python scripts/backtesting/optimization/run_all_backtests.py
python scripts/backtesting/optimization/run_profile_batch_backtester.py
```

---

## Data Scripts

```bash
python scripts/data/download_market_data.py
python scripts/data/download_portfolio_data.py
```

---

## Deployment Scripts

```bash
bash scripts/deployment/deploy_production.sh
bash scripts/deployment/setup_environment.sh
```

---

## Cleanup History

### 2026-03-15: Removed scripts/util/

Deleted 27 one-time utility scripts:
- Phase 4/5 cleanup scripts (completed phases)
- Batch creation scripts (one-time use)
- AWS destruction scripts (one-time use)
- Checkpoint trackers (moved to Ralph)
- Progress checkers (consolidated)
- Import fixers (one-time use)

**Reason:** These were all one-time scripts for completed phases of the project. Their functionality is now handled by Ralph tasks.

---

## Integration with Ralph

The validation script is used by Ralph task 31_production_audit.yml:

```bash
# Ralph task uses this script
ralph run -c .ralph/ralph_tasks/31_production_audit.yml
```

---

## Adding New Scripts

When adding new scripts:

1. Add shebang: `#!/usr/bin/env python3`
2. Add docstring with purpose and usage
3. Add type hints
4. Handle errors gracefully
5. Update this README.md
