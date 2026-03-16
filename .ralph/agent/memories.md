# Memories

## Patterns

### mem-1773651638-e43f
> technical_indicators.py has 1313 lines. MI=4.32 due to LOC penalty in MI formula. To achieve MI>=20, file needs to be split into ~4-5 smaller modules (trend_indicators.py, momentum_indicators.py, volatility_indicators.py, volume_indicators.py). This requires architectural decision and import refactoring across codebase.
<!-- tags: radon, mi, technical-indicators, refactoring | created: 2026-03-16 -->

### mem-1773649950-b720
> compliance_engine.py has 3860 lines. MI formula penalizes large files
<!-- tags:  | created: 2026-03-16 -->

## Decisions

## Fixes

### mem-1773647476-ee7e
> MI score 0.00 for large files (3000+ LOC): Root cause is Lines of Code factor in MI calculation. Only fix is to split file into smaller modules. Adding docstrings, reducing CC, or comments won't help. Architectural refactoring required.
<!-- tags: radon, mi, maintainability, code-quality | created: 2026-03-16 -->

## Context
