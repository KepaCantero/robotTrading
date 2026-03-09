# Memories

**Last Reset:** 2026-03-08
**Status:** Fresh start - all previous memories cleared

---

## Patterns

### mem-1773036279-6d30
> FASE 5.1 Security Hardening completed: Removed hardcoded password fallback in questdb_connector.py (line 87). All security checkpoints pass: No API keys, no secret tokens, .env in gitignore, no hardcoded passwords.
<!-- tags: aaa, security | created: 2026-03-09 -->

### mem-1773036094-2290
> FASE 4.1 QA Validation completed: Fixed 1 black formatting issue (trading_thresholds.py), 1 isort issue (error_handler.py), 1 ruff unused import (modelo_720_generator.py). All checks now pass. Mypy shows ~80 type errors (acceptable per orchestrator spec).
<!-- tags: aaa, linting, qa | created: 2026-03-09 -->

### mem-1772997627-f66d
> FASE 1.2 completed: 1140 Python files in app/ now have requirements.txt coverage. Requirements files stored in .requirements/app/ with same directory structure. Use find app -name '*.py' | wc -l and find .requirements/app -name '*.requirements.txt' | wc -l to verify coverage.
<!-- tags: aaa, requirements, coverage | created: 2026-03-08 -->

*No patterns recorded yet.*

---

## Decisions

*No decisions recorded yet.*

---

## Fixes

*No fixes recorded yet.*

---

## Context

### mem-1772996846-afdd
> app/ has 1119 non-empty Python files, 21 empty __init__.py files. No duplicate files with actual content. Use 'find app -name *.py -type f \! -empty | wc -l' to count non-empty files.
<!-- tags: codebase, metrics | created: 2026-03-08 -->

*No context recorded yet.*
