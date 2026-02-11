# __init__.py - Core Protocols Package

## Purpose
Package initialization file that exports all Protocol interfaces for SOLID architecture (dependency inversion and interface segregation). Enables importing protocol interfaces (IPreTradeValidator, ITradeExecutor, etc.) independently.

---

## Type Definitions / Data Classes

This is a package init file with no custom classes.

---

## Function Signatures (Contracts)

### Module Exports
```python
from app.core.protocols.i_pre_trade_validator import IPreTradeValidator
from app.core.protocols.i_trade_executor import ITradeExecutor
from app.core.protocols.i_post_trade_analyzer import IPostTradeAnalyzer
from app.core.protocols.i_broker_adapter import IBrokerAdapter
from app.core.protocols.i_spain_tax_engine import ISpainTaxEngine
from app.core.protocols.i_trading_decision_logger import ITradingDecisionLogger
from app.core.protocols.i_kill_switch_monitor import IKillSwitchMonitor
from app.core.protocols.i_alert_processor import IAlertProcessor
from app.core.protocols.i_strategy_cycle_runner import IStrategyCycleRunner

__all__ = [
    "IPreTradeValidator",
    "ITradeExecutor",
    "IPostTradeAnalyzer",
    "IBrokerAdapter",
    "ISpainTaxEngine",
    "ITradingDecisionLogger",
    "IKillSwitchMonitor",
    "IAlertProcessor",
    "IStrategyCycleRunner",
]
```

**Pre:** All imported protocol modules must exist and define their respective Protocol classes
**Post:** Module exposes 10 protocol interfaces via __all__
**Raises:** ImportError if any dependency module is missing
**Retry:** No
**Side Effects:** None (module-level imports only)

---

## Acceptance Criteria
- [ ] Module successfully imports all 10 protocol classes
- [ ] __all__ exactly matches exported protocol names
- [ ] No circular imports exist
- [ ] Module can be imported without side effects

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | Clean package init file with proper Protocol exports for SOLID architecture. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-001 | BASE_RULES | Layered architecture dependencies inward | ✅ OK - Only imports from sibling modules |
| SOL-004 | BASE_RULES | Interface Segregation | ✅ OK - Each Protocol is small and focused |
| SOL-005 | BASE_RULES | Dependency Inversion | ✅ OK - Uses Protocol for abstractions |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ImportError propagated if modules missing |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All protocols are typed |
| FMT-001 | BASE_RULES | Black formatting | ✅ OK - Properly formatted |

---

## Dependencies
- **Internal:**
  - `.i_pre_trade_validator.IPreTradeValidator`
  - `.i_trade_executor.ITradeExecutor`
  - `.i_post_trade_analyzer.IPostTradeAnalyzer`
  - `.i_broker_adapter.IBrokerAdapter`
  - `.i_spain_tax_engine.ISpainTaxEngine`
  - `.i_trading_decision_logger.ITradingDecisionLogger`
  - `.i_kill_switch_monitor.IKillSwitchMonitor`
  - `.i_alert_processor.IAlertProcessor`
  - `.i_strategy_cycle_runner.IStrategyCycleRunner`

---

## Required Tests
- **tests/core/protocols/test_init.py:**
  - Test all 10 protocol classes are importable
  - Test __all__ contains expected exports
  - Test module has no side effects on import
  - Test all exported items are Protocol types

---

## Notes
This is a pure package init file that aggregates Protocol interface exports for SOLID architecture. The actual Protocol definitions are in individual protocol modules. Using Protocol (Python 3.8+) instead of ABC enables structural subtyping and better IDE support.
