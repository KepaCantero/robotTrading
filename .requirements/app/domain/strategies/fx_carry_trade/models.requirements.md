# Requirements: app/domain/strategies/fx_carry_trade/models.py

## Source Analysis
- **File**: app/domain/strategies/fx_carry_trade/models.py
- **Layer**: domain
- **LOC**: ~100
- **Classes**: 4
- **Functions**: 0

## Purpose
Data models for FX Carry Trade strategy. Defines core entities for carry trade calculations.

## Dependencies
### Internal
- None (pure domain models)

### External
- dataclasses
- datetime
- decimal.Decimal
- enum.Enum

## Rules Compliance

### SOLID
- [x] SRP-001: Single Responsibility - Each model has one purpose
- [x] OCP-001: Open/Closed - Models extensible via dataclasses
- [x] LSP-001: Liskov Substitution - N/A (no inheritance)
- [x] ISP-001: Interface Segregation - N/A
- [x] DIP-001: Dependency Inversion - No external dependencies

### Code Quality
- [x] GOD-CLASS: File < 300 lines
- [x] GOD-FUNC: Functions < 50 lines
- [x] COMPLEXITY: CC < 10
- [x] TYPE-HINTS: All functions typed

## Status: ✅ COMPLIANT

### Verification Results (2026-03-19)
- **Validation**: All 11 checks passed
- **CC**: 1.71 (threshold < 10)
- **MI**: 63.80 (threshold >= 20)
- **Anti-patterns**: None found
- **LOC**: 236 lines
