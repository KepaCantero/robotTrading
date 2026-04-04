# Memories

## Patterns

### mem-1773735508-7c30
> strategy_stock_allocator.py is a 2100+ line monolithic file with CC=17.19 and MI=0.00. Requires architectural splitting into: _filter.py, _scoring.py (momentum/mean_reversion/pairs), _erc_allocation.py, _models.py. Subdirectory already started at app/services/strategy_stock_allocator/ with domain_models.py and algorithms.py
<!-- tags: radon, mi, refactoring, strategy-allocator | created: 2026-03-17 -->

### mem-1773651638-e43f
> technical_indicators.py has 1313 lines. MI=4.32 due to LOC penalty in MI formula. To achieve MI>=20, file needs to be split into ~4-5 smaller modules (trend_indicators.py, momentum_indicators.py, volatility_indicators.py, volume_indicators.py). This requires architectural decision and import refactoring across codebase.
<!-- tags: radon, mi, technical-indicators, refactoring | created: 2026-03-16 -->

### mem-1773649950-b720
> compliance_engine.py has 3860 lines. MI formula penalizes large files
<!-- tags:  | created: 2026-03-16 -->

## Decisions

## Fixes

### mem-1775221037-ea79
> bonferroni_correction.py is_strategy_significant returns numpy.bool_ on Python 3.9 - must wrap with bool() for isinstance checks
<!-- tags: backtesting, validation, numpy | created: 2026-04-03 -->

### mem-1775208376-3b39
> calculate_bet_sizes_with_meta_model uses user-friendly method names (kelly, probability, expected_value, confidence) but passes to calculate_bet_sizes_ml which expects meta_* prefixed names (meta_kelly, meta_probability, etc.). A mapping layer was added at line ~1092 of bet_sizing.py to handle the conversion.
<!-- tags: backtesting, bet-sizing, method-mapping | created: 2026-04-03 -->

### mem-1774897554-2d91
> app/domain/tax/ was an orphan directory with unreferenced SQLAlchemy and aiohttp/aiosqlite files. Deleted in iteration 6. The canonical fifo_schema.py is at app/infrastructure/persistence/tax/fifo_schema.py. modelo_721_exporter.py had zero references anywhere.
<!-- tags: architecture, dead-code, domain-purity | created: 2026-03-30 -->

### mem-1774707451-06d7
> Fixed corrupted Depends/Query names (epends->Depends, uery->Query) in app/presentation/ files. Added extend-immutable-calls to .flake8 for FastAPI patterns (Depends, Query, Path, Security, Body, Field, Form, Header, Cookie, File) to properly handle B008 without noqa. auth.py Security() calls moved to module-level vars.
<!-- tags: flake8, fastapi, B008 | created: 2026-03-28 -->

### mem-1773647476-ee7e
> MI score 0.00 for large files (3000+ LOC): Root cause is Lines of Code factor in MI calculation. Only fix is to split file into smaller modules. Adding docstrings, reducing CC, or comments won't help. Architectural refactoring required.
<!-- tags: radon, mi, maintainability, code-quality | created: 2026-03-16 -->

## Context
