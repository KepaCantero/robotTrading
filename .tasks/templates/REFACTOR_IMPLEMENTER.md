# Wrapper: Refactor Implementer (Backend Developer)

**This template is a CONTEXT WRAPPER for @agent-tech-lead-orchestrator**

When calling @agent-tech-lead-orchestrator for refactoring implementation, pass this entire context.

---

## Agent to Delegate

**@agent-tech-lead-orchestrator** - Will coordinate the workflow and delegate to @agent-backend-developer.

---

## Context for Tech Lead Orchestrator

### Repository Information
```
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
BASE_RULES: .requirements/BASE_RULES.md
```

### Task
Refactor: `{{PYTHON_FILE}}`
Violation Type: `{{VIOLATION_TYPE}}`
Refactoring Pattern: `{{PATTERN}}`

### Required Resources
```
Python File: {{PYTHON_FILE}}
Requirements: {{REQUIREMENTS_FILE}}
BASE_RULES: .requirements/BASE_RULES.md
Refactoring Instructions: {{INSTRUCTIONS_FILE}}
```

### Specialist Agent to Call
@agent-backend-developer (for architectural refactoring)

---

## Deterministic Instructions for @agent-backend-developer

### Step 1: Gather Context

```bash
# Read the source file
Read {{PYTHON_FILE}}

# Read BASE_RULES for context
Read .requirements/BASE_RULES.md

# Read refactoring instructions (if provided)
Read {{INSTRUCTIONS_FILE}}
```

### Step 2: Understand the Violation

Identify what needs to be refactored:

**Common Violation Patterns:**

**DP-004: Direct Instantiation**
```python
# ❌ BEFORE - Direct instantiation
provider = PaperTradingPortfolioProvider()
service = PortfolioService(provider)

# ✅ AFTER - Dependency Injection
from app.core.di_container import DIContainer
_di_container = DIContainer()
service = _di_container.get_portfolio_service()
```

**ARCH-001: Layering Violation**
```python
# ❌ BEFORE - Database logic in API layer
def check_database():
    conn = sqlite3.connect(path)
    # ... database operations ...

# ✅ AFTER - Service layer
from app.infrastructure.health.database_health_checker import DatabaseHealthChecker
checker = DatabaseHealthChecker(config)
return checker.check_health()
```

### Step 3: Apply Refactoring

**Use Edit tool for all changes:**

1. **Identify the exact lines** to modify
2. **Prepare the replacement code** following the pattern
3. **Use Edit tool** with exact old_string/new_string
4. **Verify syntax** after each change

```bash
# After each edit, verify syntax
python -m py_compile {{PYTHON_FILE}}
```

### Step 4: Preserve Functionality

**Critical checks:**

- [ ] All existing functions still work
- [ ] No breaking changes to public APIs
- [ ] Imports are correct and organized
- [ ] Type hints are preserved or improved
- [ ] Error handling is maintained

### Step 5: Implementation Summary

Report changes in this format:

```markdown
## Implementation Complete

**File:** {{PYTHON_FILE}}
**Violation:** {{VIOLATION_TYPE}}
**Status:** ✅ IMPLEMENTED

**Changes Applied:**
| Line(s) | Change | Pattern |
|---------|--------|---------|
| 43 | Replaced direct instantiation with DI container | DP-004 |
| 87 | Moved database logic to infrastructure service | ARCH-001 |

**Files Created/Modified:**
- {{PYTHON_FILE}}: [description of changes]
- [NEW_FILE]: [if any new files created]

**Syntax Verification:**
✅ python -m py_compile {{PYTHON_FILE}}

**Functionality Preserved:**
✅ All existing functionality maintained
✅ No breaking changes to public APIs

**Imports Modified:**
- Added: [new imports]
- Removed: [removed imports]

**Next:** Ready for testing phase
```

---

## Common Refactoring Patterns

### Pattern 1: DI Container Integration

```python
# Create DI Container entry
class DIContainer:
    def get_{{SERVICE_NAME}}(self) -> {{SERVICE_TYPE}}:
        if '{{SERVICE_KEY}}' not in self._services:
            # Lazy initialization
            service = {{SERVICE_FACTORY}}()
            self._services['{{SERVICE_KEY}}'] = service
        return self._services['{{SERVICE_KEY}}']

# Update API file
from app.core.di_container import DIContainer

_di_container = DIContainer()

def get_{{SERVICE_NAME}}() -> {{SERVICE_TYPE}}:
    """FastAPI dependency for {{SERVICE_NAME}}."""
    return _di_container.get_{{SERVICE_NAME}}()

# Update endpoints
@router.get("/endpoint")
async def endpoint(
    service: {{SERVICE_TYPE}} = Depends(get_{{SERVICE_NAME}})
):
    # ... use service instead of direct instantiation
```

### Pattern 2: Service Layer Extraction

```python
# Create service in infrastructure layer
# app/infrastructure/health/{{NAME}}.py

class {{SERVICE_NAME}}:
    """Service for {{PURPOSE}}."""

    def __init__(self, config: {{CONFIG_TYPE}}) -> None:
        self.config = config

    def {{METHOD_NAME}}(self) -> {{RETURN_TYPE}}:
        """Implement business logic here."""
        # ... implementation ...

# Update API to use service
from app.infrastructure.health.{{NAME}} import {{SERVICE_NAME}}

def get_{{SERVICE_NAME}}() -> {{SERVICE_NAME}}:
    """FastAPI dependency."""
    return {{SERVICE_NAME}}(config=settings)
```

### Pattern 3: Factory Pattern

```python
# Create factory
class {{SERVICE_NAME}}Factory:
    """Factory for creating {{SERVICE_NAME}} instances."""

    @staticmethod
    def create_{{VARIANT}}(config: {{CONFIG_TYPE}}) -> {{SERVICE_TYPE}}:
        """Create {{VARIANT}} instance."""
        return {{SERVICE_TYPE}}(config)

    @staticmethod
    def create_from_config(config: dict) -> {{SERVICE_TYPE}}:
        """Create from configuration dict."""
        variant = config.get("variant", "default")
        if variant == "default":
            return {{SERVICE_NAME}}Factory.create_{{VARIANT}}(config)
        raise ValueError(f"Unsupported variant: {variant}")
```

---

## Quality Checklist

- [ ] All edits used with exact string matching
- [ ] Syntax verification passed for all changes
- [ ] Existing functionality preserved
- [ ] Type hints maintained or improved
- [ ] Error handling preserved
- [ ] No new violations introduced
- [ ] Imports are clean and organized
- [ ] Code follows BASE_RULES patterns

---

## Output Format

@agent-backend-developer must return:

```markdown
## Refactoring Implementation Report

**File:** {{PYTHON_FILE}}
**Violation Type:** {{VIOLATION_TYPE}}
**Pattern:** {{PATTERN}}

**Implementation Summary:**
[What was changed]

**Changes by Line:**
| Line | Before | After |
|------|--------|-------|
| 43 | `provider = ...` | `service = container.get...` |

**Syntax Check:** ✅ PASS / ❌ FAIL

**New Files Created:** [if any]

**Next:** Ready for testing
```

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
**Orchestrator:** @agent-tech-lead-orchestrator
**Specialist:** @agent-backend-developer
