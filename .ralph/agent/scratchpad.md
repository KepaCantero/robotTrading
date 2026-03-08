# Ralph Scratchpad - Master Orchestrator v10.0

## 2026-03-08 ITERATION: Component Scan

### Objective
1. Verify rules/ has all required rules
2. Audit files against requirements
3. Add missing rules to rules/
4. Create missing files
5. Fix non-compliant files

### SCAN RESULTS

#### Project Structure Overview
**Total Python files in app/: 1126**

#### Key Components - EXISTENCE CHECK

| Component | Path | Exists | Files |
|-----------|------|--------|-------|
| SpainTaxEngine | `app/services/tax_efficiency/engines/` | YES | spain_tax_engine.py, spain_tax_engine_impl.py |
| DecisionLogger | `app/infrastructure/logging/` | YES | trading_decision_logger.py |
| CentralConfig | `app/shared/config/` | YES | centralized_config.py |
| Protocols | `app/core/protocols/` | YES | __init__.py only |
| RiskValidators | `app/services/risk/validators/` | YES | drawdown_validator.py, kelly_criterion_validator.py |

#### Rules Directory Status

**MISSING: rules/trading/ directory** - Deleted (per git status)

Existing rules directories:
- rules/python/ (28 files)
- rules/sre/ (1 file)

### Rules Required (per Objective)

| Rule ID | Description | Location | Status |
|---------|-------------|----------|--------|
| R1 | Kelly Criterion + 2% max | rules/trading/ | MISSING (dir deleted) |
| R2 | Drawdown 15% stop | rules/trading/ | MISSING |
| R3 | Stop Loss ALWAYS | rules/trading/ | MISSING |
| R4 | R:R 2:1 min | rules/trading/ | MISSING |
| R15 | Logging append-only + correlation ID | rules/python/ | TBD |
| R28 | 5-year retention for tax | rules/trading/ | MISSING |
| IRPF-001 | Progressive rates 19/21/23% | rules/trading/ | MISSING |
| ISP-001 | Max 5 methods per interface | rules/python/ | TBD |
| LSP-001 | Use typing.Protocol | rules/python/ | TBD |
| DIP-001 | DI via Protocol | rules/python/ | TBD |

### Analysis

1. **rules/trading/ directory does not exist** - Need to recreate with all trading-specific rules
2. **rules/python/ exists** - Need to verify ISP-001, LSP-001, DIP-001 are covered
3. **All target components exist** - Proceed to audit phase

### Next Steps (for future iterations)
1. Create rules/trading/ with required rules
2. Audit each component against rules
3. Run QA validation (black, isort, ruff)
4. Generate final report

---
*Task: SCAN complete - Components listed*
