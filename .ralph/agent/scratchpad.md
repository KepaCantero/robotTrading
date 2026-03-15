# Ralph Task 31: Production Code Audit & Fix

## Objective
Audit ALL Python files in app/ (excluding tests) and fix them to pass 11 validation checks:
1. black - Formatting
2. isort - Import Order
3. ruff - Linting
4. flake8 - Style Guide
5. pylint - Code Quality
6. mypy - Type Checking
7. bandit - Security
8. radon cc - Complexity (CC < 10)
9. radon mi - Maintainability (MI >= 20)
10. py_compile - Syntax
11. AST parse - Imports Valid

## Scope
- 1152 production Python files to process
- Files listed in .ralph/outputs/PRODUCTION_FILE_LIST.json
- NO shortcuts: no # type: ignore, # pylint: disable, # noqa, # nosec, or Any types

## Processing Order
Phase 1: Configuration (app/core/config/)
Phase 2: Protocols & Interfaces (app/core/protocols/, app/interfaces/)
Phase 3: Utilities (app/utils/, app/core/utils/)
Phase 4: Models (app/models/, app/domain/entities/)
Phase 5: Core Services (app/core/, app/domain/services/)
Phase 6: Execution Services (app/services/execution/)
Phase 7: Strategies (app/strategies/, app/domain/strategies/)
Phase 8: Backtesting (app/backtesting/)
Phase 9: Analysis (app/analysis/, app/market_microstructure/)
Phase 10: Remaining Files

## Current Status
- [ ] Starting Phase 1: Configuration files
- Progress tracking in .ralph/outputs/PRODUCTION_FIX_PROGRESS.json

## Session 2026-03-15
Starting fresh iteration. Creating tasks for systematic processing.
