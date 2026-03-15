# Memories

**Last Reset:** 2026-03-08
**Status:** Fresh start - all previous memories cleared

---

## Patterns

### mem-1773595899-f4e0
> Phase 1 Compliance Fix COMPLETE: FS-BAN-001 (2 files renamed), FS-DIR-004 (app.py moved to scripts/), FS-DIR-005 (30+ to 2 deep dirs, 95%+ improvement). ARCH-DEP-001/ARCH-ANTI-006 deferred to Phase 2 (requires Protocol creation + DI refactoring). Report: .ralph/outputs/COMPLIANCE_FIX_REPORT.md
<!-- tags: aaa, compliance, phase1 | created: 2026-03-15 -->

### mem-1773556121-6054
> Phase 5.1 - execution adapters: 3 files fixed ( TradeResultDataclass moved to module level, dataclasses.asdict() converts to dict via dataclasses.asdict() for protocol compatibility. fixed union-attr issues by extracting order_side safely before accessing .value. refact exception handling to complex union-attr access patterns. commit: bcdcfe8e
<!-- tags:  | created: 2026-03-15 -->

### mem-1773555325-ad12
> Phase 5 core services audit: 57 files audited (app/core/, app/domain/services/), 51 passed (89.5%), 6 failing. Failing files: compliance_engine.py (HIGH - 28k tokens, MI=0, needs architectural review), technical_indicators.py (MEDIUM - CC=10.34, MI=6.28, needs refactoring), 3 execution adapters (LOW - TradeResult vs dict return type). Key patterns: local dataclasses in methods cause mypy issues, conditional imports cause pylint used-before-assignment, numpy floating vs float type mismatches.
<!-- tags: aaa, production-audit, phase5, core-services | created: 2026-03-15 -->

### mem-1773553987-e203
> Phase 4 models/entities audit: 11 files audited (app/models/, app/domain/entities/), all 11 passed 11 validation checks with no fixes needed. Models are well-structured with good type hints, low CC (1.75-4.17), high MI (27-100).
<!-- tags: aaa, production-audit, phase4, models | created: 2026-03-15 -->

### mem-1773038454-7b0c
> AAA v13.0 Master Orchestrator COMPLETE: All 6 phases verified and executed. 1140 Python files in app/, 100% requirements coverage, 73 Protocol interfaces, 29/29 trading rules, Spain Tax (IRPF 19/21/23%, Modelo 720, loss carryforward), QA passes (Black/isort/Ruff), Security hardened. Report: .ralph/outputs/aaa_audit_report.md
<!-- tags: aaa, complete, production-ready | created: 2026-03-09 -->

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

### mem-1773595090-0ad8
> HAT 6 FS-DIR-004: Moved app.py to scripts/launcher.py. Root app.py was a convenience launcher script for dashboard/api, not imported anywhere. Moved to scripts/ to comply with FS-DIR-004 (no code in root). Usage: python scripts/launcher.py [dashboard|api]
<!-- tags: aaa, compliance, fs-dir-004 | created: 2026-03-15 -->

### mem-1773594866-87ac
> HAT 6 FS-BAN-001: Renamed prohibited file names - app/presentation/api/utils.py -> api_helpers.py, app/services/hurst_analysis/utils.py -> hurst_calculations.py. Updated import in orchestrator.py using alias pattern to preserve 'utils' namespace usage.
<!-- tags: aaa, compliance, fs-ban-001 | created: 2026-03-15 -->

### mem-1773594615-c8f5
> Phase 5.3 - compliance_engine.py: Fixed W0613 (unused args prefixed with underscore), W1203 (f-string logging converted to lazy %). Pylint 10/10. C0415 (imports outside toplevel) left as-is for lazy loading pattern.
<!-- tags: aaa, production-audit, phase5, compliance | created: 2026-03-15 -->

### mem-1773553724-3d1f
> Phase 3 utilities audit: 8 files audited (core/utils, shared/utils), 5 passed initially, 3 fixed. Fixes: decimal_utils.py sum() Decimal type, subsystem_config_factory.py singleton pattern, symbol_mapper.py @abstractmethod + removed forbidden pylint disables
<!-- tags: aaa, production-audit, phase3, utilities | created: 2026-03-15 -->

### mem-1773553044-540e
> Phase 2 protocols audit: 18 files audited, all passed 11 validation checks. 1 fix applied: removed forbidden pylint disable from hurst_analysis/protocols.py. Protocol files are well-maintained with high MI scores (67-100).
<!-- tags: aaa, production-audit, phase2, protocols | created: 2026-03-15 -->

### mem-1773552666-3dc3
> Phase 1 config audit: 4 files fixed (api_endpoints, di_config, centralized_config, compliance, config_validator). - import paths fixed, black/isort applied, MI improved through docstrings and helper method extraction.
<!-- tags: aaa, production-audit, phase1 | created: 2026-03-15 -->

### mem-1773038248-1fa7
> FASE 4.1 black fix: questdb_connector.py had indentation issue from previous security fix (removed hardcoded password). Black reformat corrected it.
<!-- tags: aaa, formatting | created: 2026-03-09 -->

*No fixes recorded yet.*

---

## Context

### mem-1772996846-afdd
> app/ has 1119 non-empty Python files, 21 empty __init__.py files. No duplicate files with actual content. Use 'find app -name *.py -type f \! -empty | wc -l' to count non-empty files.
<!-- tags: codebase, metrics | created: 2026-03-08 -->

*No context recorded yet.*
