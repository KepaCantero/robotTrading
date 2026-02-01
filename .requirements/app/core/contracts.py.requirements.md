# contracts.py

## Purpose
Contract definitions and abstract base classes for system components following Dependency Inversion Principle.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses ABC and Protocol for interface definitions.

### Abstract Contracts
```python
class Repository(ABC):
    # Abstract base for data access
    @abstractmethod
    def get(self, id: str) -> Optional[Any]: ...
    
    @abstractmethod
    def save(self, entity: Any) -> None: ...

class MessageBus(ABC):
    # Abstract base for messaging
    @abstractmethod
    def publish(self, channel: str, message: Any) -> None: ...
    
    @abstractmethod
    def subscribe(self, channel: str, callback: Callable) -> None: ...

class Validator(Protocol):
    # Protocol for validation
    def validate(self, data: Any) -> bool: ...
```

---

## Acceptance Criteria
- [ ] SOL-005: Contracts depend on abstractions
- [ ] All abstract methods marked with @abstractmethod
- [ ] Protocols used for duck typing where appropriate
- [ ] Clear documentation for each contract
- [ ] Type hints on all methods

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-005 | BASE_RULES.md | Dependency Inversion | ✅ OK |
| TYP-001 | BASE_RULES.md | Type coverage | ✅ OK |
| TYP-006 | BASE_RULES.md | Protocol for duck typing | ✅ OK |

---

## Dependencies
- **External:** abc, typing
- **Internal:** None

---

## Required Tests
- **tests/core/test_contracts.py:**
  - Test abstract classes cannot be instantiated
  - Test concrete implementations can be registered
  - Test protocols work with duck typing

---

## Notes
Defines system-wide contracts. Implementations should be in infrastructure layer.
