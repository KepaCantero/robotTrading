# strategy_registry.py

## Purpose
Strategy Registry Pattern - Pluggable algorithms following Percival's Architecture Patterns with Python. Implements the Strategy pattern with a registry for dynamic strategy discovery, dependency inversion, and runtime strategy switching.

Reference: "Architecture Patterns with Python" (Cosmic Python) Chapter 4.

---

## Type Definitions / Data Classes

### StrategyMetadata (dataclass)
```python
@dataclass
class StrategyMetadata:
    name: str                                    # REQUIRED - Unique strategy name
    strategy_class: Type[BaseStrategy]           # REQUIRED - Strategy class
    description: str = ""                        # OPTIONAL - Strategy description
    version: str = "1.0.0"                       # OPTIONAL - Strategy version
    category: str = "general"                    # OPTIONAL - Strategy category
    tags: List[str] = field(default_factory=list) # OPTIONAL - Filtering tags
    required_parameters: List[str] = field(default_factory=list) # REQUIRED - Required params
    enabled: bool = True                         # OPTIONAL - Is strategy enabled
    registered_at: datetime = field(default_factory=datetime.utcnow) # REQUIRED - Registration time
```

---

## Function Signatures (Contracts)

### `BaseStrategy.__init__(config: Dict[str, Any])`
**Pre:** config is valid dictionary
**Post:** Strategy initialized
**Raises:** None
**Retry:** No
**Side Effects:** Sets attributes from config

### `BaseStrategy.execute(*args, **kwargs) -> Any` (abstract)
**Pre:** Implementation-specific
**Post:** Implementation-specific
**Raises:** NotImplementedError
**Retry:** No
**Side Effects:** None

### `BaseStrategy.validate_config() -> bool`
**Pre:** None
**Post:** Returns True if config valid
**Raises:** ValueError if invalid config
**Retry:** No
**Side Effects:** None

### `BaseStrategy.get_required_parameters() -> List[str]`
**Pre:** None
**Post:** Returns list of required parameter names
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BaseStrategy.get_metadata() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns metadata dict
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyContext.__init__(strategy: Optional[BaseStrategy] = None)`
**Pre:** None
**Post:** Context initialized
**Raises:** None
**Retry:** No
**Side Effects:** Initializes execution_history

### `StrategyContext.set_strategy(strategy: BaseStrategy) -> None`
**Pre:** strategy is valid BaseStrategy instance
**Post:** Current strategy set
**Raises:** None
**Retry:** No
**Side Effects:** Updates _strategy reference

### `StrategyContext.get_strategy() -> Optional[BaseStrategy]`
**Pre:** None
**Post:** Returns current strategy or None
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyContext.execute_strategy(*args, **kwargs) -> Any`
**Pre:** Strategy is set
**Post:** Returns execution result
**Raises:** RuntimeError if no strategy set
**Retry:** Yes (can retry execution)
**Side Effects:** Records execution in history

### `StrategyContext.get_execution_history() -> List[Dict[str, Any]]`
**Pre:** None
**Post:** Returns copy of execution history
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyRegistry.__init__()`
**Pre:** None
**Post:** Registry initialized
**Raises:** None
**Retry:** No
**Side Effects:** Initializes empty dicts

### `StrategyRegistry.register(name: str, strategy_class: Type[BaseStrategy], description: str = "", category: str = "general", tags: Optional[List[str]] = None, enabled: bool = True, replace: bool = False) -> None`
**Pre:** strategy_class inherits from BaseStrategy
**Post:** Strategy registered
**Raises:** ValueError if already exists (unless replace=True), TypeError if invalid class
**Retry:** No
**Side Effects:** Updates _strategies dict

### `StrategyRegistry.unregister(name: str) -> None`
**Pre:** name is registered
**Post:** Strategy unregistered
**Raises:** KeyError if not found
**Retry:** No
**Side Effects:** Removes from _strategies and _instances

### `StrategyRegistry.create(name: str, config: Optional[Dict[str, Any]] = None, cache_instance: bool = False) -> BaseStrategy`
**Pre:** name is registered and enabled
**Post:** Returns strategy instance
**Raises:** KeyError if not found, ValueError if disabled or invalid config
**Retry:** No
**Side Effects:** Creates instance, optionally caches

### `StrategyRegistry.get_metadata(name: str) -> StrategyMetadata`
**Pre:** name is registered
**Post:** Returns metadata
**Raises:** KeyError if not found
**Retry:** No
**Side Effects:** None

### `StrategyRegistry.list_strategies(category: Optional[str] = None, enabled_only: bool = False, tags: Optional[List[str]] = None) -> List[StrategyMetadata]`
**Pre:** None
**Post:** Returns filtered list of strategies
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyRegistry.find_by_category(category: str) -> List[StrategyMetadata]`
**Pre:** category exists
**Post:** Returns strategies in category
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyFactory.__init__(registry: Optional[StrategyRegistry] = None)`
**Pre:** None
**Post:** Factory initialized
**Raises:** None
**Retry:** No
**Side Effects:** Creates registry if none provided

### `StrategyFactory.create(name: str, config: Optional[Dict[str, Any]] = None) -> BaseStrategy`
**Pre:** name is registered
**Post:** Returns strategy instance
**Raises:** KeyError if not found, ValueError on creation failure
**Retry:** No
**Side Effects:** Calls registry.create

### `StrategyFactory.create_context(name: str, config: Optional[Dict[str, Any]] = None) -> StrategyContext`
**Pre:** name is registered
**Post:** Returns context with strategy
**Raises:** KeyError if not found, ValueError on creation failure
**Retry:** No
**Side Effects:** Creates strategy and context

### `StrategyFactory.create_batch(strategy_configs: List[tuple[str, Dict[str, Any]]]) -> List[BaseStrategy]`
**Pre:** All names in configs are registered
**Post:** Returns list of strategy instances
**Raises:** ValueError if any creation fails
**Retry:** No
**Side Effects:** Creates multiple strategies

### `register_strategy(name: str, description: str = "", category: str = "general", tags: Optional[List[str]] = None, registry: Optional[StrategyRegistry] = None)` (decorator)
**Pre:** Used as class decorator
**Post:** Class registered in registry
**Raises:** None
**Retry:** No
**Side Effects:** Registers decorated class

---

## Acceptance Criteria
- [ ] BaseStrategy subclasses implement execute method
- [ ] BaseStrategy.validate_config returns True for valid config
- [ ] StrategyContext.set_strategy updates current strategy
- [ ] StrategyContext.execute_strategy raises RuntimeError if no strategy
- [ ] StrategyContext.execute_strategy records execution history
- [ ] StrategyRegistry.register validates BaseStrategy inheritance
- [ ] StrategyRegistry.register raises ValueError for duplicate (unless replace=True)
- [ ] StrategyRegistry.create returns cached instance if cache_instance=True
- [ ] StrategyRegistry.create raises ValueError for disabled strategy
- [ ] StrategyRegistry.list_strategies filters by category
- [ ] StrategyRegistry.list_strategies filters by enabled_only
- [ ] StrategyRegistry.list_strategies filters by tags (all must match)
- [ ] StrategyFactory.create_context returns StrategyContext with strategy
- [ ] StrategyFactory.create_batch creates all strategies
- [ ] register_strategy decorator registers class

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
| TYP-002 | BASE_RULES | Modern syntax | ✅ OK - Uses modern typing |
| TYP-003 | BASE_RULES | No Any without justification | ⚠️ PARTIAL - Uses Any in execute/config |
| ASYNC-001 | BASE_RULES | Use async def | ✅ OK - execute is async |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - Uses keyword args |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ FIXED - Added exc_info=True (lines 257, 387, 495) |
| CC-006 | BASE_RULES | Explicit error handling | ✅ FIXED - Uses specific exceptions (lines 247, 386, 494) |
| DP-003 | BASE_RULES | Strategy pattern | ✅ OK - Implements Strategy pattern correctly |
| DP-004 | BASE_RULES | Dependency injection | ✅ OK - Uses DI in context |
| ARCH-004 | BASE_RULES | Small functions (<20 lines) | ⚠️ PARTIAL - Some functions >20 lines |

---

## Dependencies
- **External:** inspect, logging, abc, dataclasses, datetime, typing
- **Internal:** None (standalone pattern)

---

## Required Tests
- **tests/strategies/test_strategy_registry.py:**
  - Test BaseStrategy subclass implements execute
  - Test BaseStrategy.validate_config returns True
  - Test StrategyContext.set_strategy updates strategy
  - Test StrategyContext.execute_strategy raises RuntimeError when no strategy
  - Test StrategyContext.execute_strategy records history
  - Test StrategyContext.get_execution_history returns copy
  - Test StrategyRegistry.register with valid class
  - Test StrategyRegistry.register with invalid class (raises TypeError)
  - Test StrategyRegistry.register with duplicate (raises ValueError)
  - Test StrategyRegistry.register with replace=True
  - Test StrategyRegistry.unregister removes strategy
  - Test StrategyRegistry.unregister with unknown (raises KeyError)
  - Test StrategyRegistry.create with valid name
  - Test StrategyRegistry.create with unknown name (raises KeyError)
  - Test StrategyRegistry.create with disabled strategy (raises ValueError)
  - Test StrategyRegistry.create with cache_instance=True
  - Test StrategyRegistry.get_metadata returns metadata
  - Test StrategyRegistry.list_strategies with category filter
  - Test StrategyRegistry.list_strategies with enabled_only filter
  - Test StrategyRegistry.list_strategies with tags filter
  - Test StrategyFactory.create returns strategy
  - Test StrategyFactory.create_context returns context
  - Test StrategyFactory.create_batch creates all
  - Test register_strategy decorator registers class

---

## Notes
- Reference: "Architecture Patterns with Python" by Percival & Gregory
- Implements Strategy pattern for pluggable algorithms
- Supports runtime strategy switching
- Includes registry for dynamic strategy discovery
- Provides decorator for automatic registration
- Supports strategy categories and tags
- Caches strategy instances for performance
- Global default registry for convenience
