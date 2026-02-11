# registry.py

## Purpose
Strategy Registry - Registro centralizado de estrategias disponibles. Gestiona el ciclo de vida de las estrategias, incluyendo carga, descarga, activación y hot-swapping de estrategias.

---

## Type Definitions / Data Classes

No custom dataclasses defined

---

## Function Signatures (Contracts)

### `StrategyRegistry.__init__()`
**Pre:** None
**Post:** Registry initialized with factory and empty state
**Raises:** None
**Retry:** No
**Side Effects:** Creates StrategyFactory instance

### `StrategyRegistry.load_strategy(name: str, config: Dict[str, Any]) -> BaseStrategy`
**Pre:** name is registered in factory
**Post:** Returns loaded strategy instance
**Raises:** ValueError if strategy creation fails
**Retry:** No
**Side Effects:** Stores strategy in strategies dict, unloads existing if name conflicts

### `StrategyRegistry.unload_strategy(name: str) -> None`
**Pre:** name is loaded in registry
**Post:** Strategy removed from registry
**Raises:** ValueError if strategy not loaded
**Retry:** No
**Side Effects:** Deactivates strategy, clears active_strategy if needed, deletes from dict

### `StrategyRegistry.get_strategy(name: str) -> Optional[BaseStrategy]`
**Pre:** None
**Post:** Returns strategy instance or None
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyRegistry.set_active_strategy(name: str) -> None`
**Pre:** name is loaded in registry
**Post:** Strategy marked as active
**Raises:** ValueError if strategy not loaded
**Retry:** No
**Side Effects:** Deactivates previous active strategy, activates new one

### `StrategyRegistry.get_active_strategy() -> Optional[BaseStrategy]`
**Pre:** None
**Post:** Returns active strategy instance or None
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyRegistry.list_loaded_strategies() -> List[str]`
**Pre:** None
**Post:** Returns list of loaded strategy names
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyRegistry.list_available_strategies() -> List[str]`
**Pre:** None
**Post:** Returns list of available strategy names from factory
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyRegistry.get_strategy_status(name: str) -> Dict[str, Any]`
**Pre:** name is loaded in registry
**Post:** Returns strategy status dict
**Raises:** ValueError if strategy not loaded
**Retry:** No
**Side Effects:** None

### `StrategyRegistry.get_all_strategies_status() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns status of all loaded strategies
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyRegistry.reload_strategy(name: str, config: Dict[str, Any]) -> BaseStrategy`
**Pre:** name is loaded in registry
**Post:** Returns reloaded strategy instance
**Raises:** ValueError if reload fails
**Retry:** Yes (can retry reload)
**Side Effects:** Unloads and reloads strategy, preserves active status

### `StrategyRegistry.clear_all_strategies() -> None`
**Pre:** None
**Post:** All strategies removed
**Raises:** None
**Retry:** No
**Side Effects:** Unloads all strategies

---

## Acceptance Criteria
- [ ] load_strategy creates strategy via factory
- [ ] load_strategy replaces existing strategy with same name
- [ ] load_strategy raises ValueError for unknown strategy
- [ ] unload_strategy removes strategy from registry
- [ ] unload_strategy deactivates strategy if active
- [ ] unload_strategy raises ValueError for unknown strategy
- [ ] set_active_strategy deactivates previous strategy
- [ ] set_active_strategy activates new strategy
- [ ] set_active_strategy raises ValueError for unloaded strategy
- [ ] get_active_strategy returns active strategy or None
- [ ] list_loaded_strategies returns loaded names
- [ ] list_available_strategies returns factory's available names
- [ ] get_strategy_status returns strategy metadata
- [ ] reload_strategy preserves active status
- [ ] clear_all_strategies removes all strategies

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-05T12:00:00Z |
| **Audit Status** | PASSED |
| **BASE_RULES Version** | 2026-02-01 |
| **Audited By** | @agent-python-expert (via Tech Lead Orchestrator) |
| **GAPs Fixed** | 0 / ? total |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| TYP-003 | BASE_RULES | No Any without justification | ⚠️ PARTIAL - Uses Any in config dict |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - Uses keyword args in logging |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ FIXED - Added exc_info=True (lines 53, 222) |
| CC-006 | BASE_RULES | Explicit error handling | ❌ GAP - Broad exception catching (lines 52, 222) |
| DP-003 | BASE_RULES | Strategy pattern | ✅ OK - Implements Strategy/Registry pattern |
| ARCH-004 | BASE_RULES | Small functions (<20 lines) | ✅ OK - Most functions <20 lines |

---

## Dependencies
- **External:** logging, datetime, typing
- **Internal:** 
  - .base.BaseStrategy
  - .factory.StrategyFactory

---

## Required Tests
- **tests/strategies/test_registry.py:**
  - Test load_strategy creates strategy instance
  - Test load_strategy replaces existing strategy
  - Test load_strategy with unknown strategy (raises ValueError)
  - Test unload_strategy removes loaded strategy
  - Test unload_strategy deactivates active strategy
  - Test unload_strategy with unknown strategy (raises ValueError)
  - Test get_strategy returns loaded strategy
  - Test get_strategy with unknown strategy returns None
  - Test set_active_strategy marks strategy as active
  - Test set_active_strategy deactivates previous
  - Test set_active_strategy with unknown strategy (raises ValueError)
  - Test get_active_strategy returns active strategy
  - Test get_active_strategy returns None when none active
  - Test list_loaded_strategies returns loaded names
  - Test list_available_strategies returns factory names
  - Test get_strategy_status returns status dict
  - Test get_strategy_status with unknown strategy (raises ValueError)
  - Test get_all_strategies_status returns all statuses
  - Test reload_strategy preserves active status
  - Test reload_strategy with unknown strategy (raises ValueError)
  - Test clear_all_strategies removes all strategies

---

## Notes
- Spanish language comments and docstrings
- Manages strategy lifecycle (load, unload, activate, deactivate)
- Supports hot-swapping of strategies
- Tracks created_at timestamp
- Delegates strategy creation to StrategyFactory
