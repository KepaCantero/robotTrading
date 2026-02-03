# Task: Refactor app/api/portfolio.py - Implement Dependency Injection

## Extends
- **Base:** `.claude/base/REFACTOR_BASE.md`
- **Orchestrator:** @agent-tech-lead-orchestrator

## Context Variables (Pre-filled)
- `{{PYTHON_FILE}}` = `app/api/portfolio.py`
- `{{VIOLATION_TYPE}}` = `DP-004`
- `{{PATTERN}}` = `DI Container`
- `{{REQUIREMENTS_FILE}}` = `.requirements/app/api/portfolio.py.requirements.md`
- `{{INSTRUCTIONS_FILE}}` = `.claude/tasks/refactor_portfolio_di.md`
- `{{TEST_FILE}}` = `tests/api/test_portfolio.py`

---

## Refactoring Details

**File:** `app/api/portfolio.py`
**Line:** 43
**Violation:** DP-004 (Direct Instantiation)
**Pattern:** DI Container with FastAPI Depends

### Current Code
```python
provider = PaperTradingPortfolioProvider()
_portfolio_service = PortfolioService(provider)
```

### Target Code
```python
from app.core.di_container import DIContainer

_di_container = DIContainer()

def get_portfolio_service() -> PortfolioService:
    """FastAPI dependency for portfolio service."""
    return _di_container.get_portfolio_service()

# All endpoints use:
# portfolio_service: PortfolioService = Depends(get_portfolio_service)
```

---

## Filled Templates (Pre-filled with Context Variables)

### Step 1: Implementer (@agent-backend-developer)

**Template:** `.tasks/templates/REFACTOR_IMPLEMENTER.md`

**All variables pre-filled:**

```markdown
## Agent to Delegate
@agent-tech-lead-orchestrator (delegates to @agent-backend-developer)

## Repository Information
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
BASE_RULES: .requirements/BASE_RULES.md

## Task
Refactor: `app/api/portfolio.py`
Violation Type: `DP-004`
Refactoring Pattern: `DI Container`

## Required Resources
Python File: app/api/portfolio.py
Requirements: .requirements/app/api/portfolio.py.requirements.md
BASE_RULES: .requirements/BASE_RULES.md
Refactoring Instructions: .claude/tasks/refactor_portfolio_di.md

## Implementation Steps
1. Read app/api/portfolio.py
2. Read .requirements/BASE_RULES.md
3. Create app/core/di_container.py with DI container class
4. Add get_portfolio_service() dependency function
5. Update all endpoints to use Depends(get_portfolio_service)
6. Remove direct instantiation at line 43
7. Verify: python -m py_compile app/api/portfolio.py
```

---

### Step 2: Tester (@agent-python-testing-expert)

**Template:** `.tasks/templates/REFACTOR_TESTER.md`

**All variables pre-filled:**

```markdown
## Agent to Delegate
@agent-tech-lead-orchestrator (delegates to @agent-python-testing-expert)

## Repository Information
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main

## Task
Test refactored code for: `app/api/portfolio.py`
Refactoring changes: [TO BE FILLED FROM STEP 1 OUTPUT]

## Required Resources
Python File: app/api/portfolio.py
Test File: tests/api/test_portfolio.py
Changes Summary: [FROM STEP 1]

## Tests to Create
```python
def test_get_portfolio_service_returns_singleton():
    """Test DI container returns singleton."""
    service1 = get_portfolio_service()
    service2 = get_portfolio_service()
    assert service1 is service2

def test_get_portfolio_service_with_mock():
    """Test DI container can be mocked."""
    mock_service = Mock()
    container = DIContainer()
    container.register_portfolio_service(mock_service)
    assert container.get_portfolio_service() is mock_service
```
```

---

### Step 3: Code Reviewer (@agent-code-reviewer)

**Template:** `.tasks/templates/REFACTOR_CODE_REVIEWER.md`

**All variables pre-filled:**

```markdown
## Agent to Delegate
@agent-tech-lead-orchestrator (delegates to @agent-code-reviewer)

## Repository Information
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
BASE_RULES: .requirements/BASE_RULES.md

## Task
Review refactored code for: `app/api/portfolio.py`
Refactoring Type: `DP-004`
Changes: [TO BE FILLED FROM STEP 1 OUTPUT]

## Required Resources
Python File: app/api/portfolio.py
Requirements: .requirements/app/api/portfolio.py.requirements.md
Test File: tests/api/test_portfolio.py
Changes Summary: [FROM STEP 1]
BASE_RULES: .requirements/BASE_RULES.md

## QA Commands
cd /Users/kepa.cantero/Projects/algoTrading
python -m py_compile app/api/portfolio.py
mypy --strict app/api/portfolio.py
ruff check app/api/portfolio.py
pytest tests/api/test_portfolio.py -v
```

---

### Step 4: Auditor (@agent-code-auditor)

**Template:** `.tasks/templates/REFACTOR_AUDITOR.md`

**All variables pre-filled:**

```markdown
## Agent to Delegate
@agent-tech-lead-orchestrator (delegates to @agent-code-auditor)

## Repository Information
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
Requirements Location: .requirements/
BASE_RULES: .requirements/BASE_RULES.md

## Task
Audit refactoring compliance for: `app/api/portfolio.py`
Refactoring Type: `DP-004`
Code Review Status: [TO BE FILLED FROM STEP 3]

## Required Resources
Python File: app/api/portfolio.py
Requirements: .requirements/app/api/portfolio.py.requirements.md
BASE_RULES: .requirements/BASE_RULES.md
Verification Checklist: .tasks/templates/GAP_FIX_PATTERNS.md

## Verification Checklist
- DI Container exists
- No direct instantiation
- Depends() used correctly
- Singleton pattern implemented
```

---

## Acceptance Criteria

- [ ] `app/core/di_container.py` created
- [ ] `app/api/portfolio.py` uses DI container
- [ ] All endpoints use `Depends(get_portfolio_service)`
- [ ] Tests pass
- [ ] QA checks pass
- [ ] Requirements updated: DP-004 → ✅ FIXED

---

## Files

| File | Action |
|------|--------|
| `app/core/di_container.py` | CREATE |
| `app/api/portfolio.py` | MODIFY |
| `tests/api/test_portfolio.py` | UPDATE |
| `.requirements/app/api/portfolio.py.requirements.md` | UPDATE |

---

**Priority:** P1
**Estimated:** 2-3 hours
**Dependencies:** None (foundation for other DI tasks)
