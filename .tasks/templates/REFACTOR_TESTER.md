# Wrapper: Refactor Tester (Python Testing Expert)

**This template is a CONTEXT WRAPPER for @agent-tech-lead-orchestrator**

When calling @agent-tech-lead-orchestrator for refactoring testing, pass this entire context.

---

## Agent to Delegate

**@agent-tech-lead-orchestrator** - Will coordinate the workflow and delegate to @agent-python-testing-expert.

---

## Context for Tech Lead Orchestrator

### Repository Information
```
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
```

### Task
Test refactored code for: `{{PYTHON_FILE}}`
Refactoring changes: `{{CHANGES_SUMMARY}}`

### Required Resources
```
Python File: {{PYTHON_FILE}}
Test File: {{TEST_FILE}}
Changes Summary: {{CHANGES_SUMMARY}}
```

### Specialist Agent to Call
@agent-python-testing-expert (for testing refactored code)

---

## Deterministic Instructions for @agent-python-testing-expert

### Step 1: Gather Context

```bash
# Read the refactored source file
Read {{PYTHON_FILE}}

# Read existing test file
Read {{TEST_FILE}}

# Read changes summary
# Understand what was refactored
```

### Step 2: Analyze Refactoring Changes

**Identify what changed:**

**For DI Container refactoring:**
- Direct instantiation replaced with DI
- New dependency injection patterns
- Singleton behavior to test

**For Service Layer extraction:**
- Logic moved to new service class
- API now calls service layer
- New service needs testing

**For other patterns:**
- Analyze the specific refactoring pattern
- Identify test coverage gaps

### Step 3: Determine Test Strategy

**Create tests for:**

1. **New functionality** (if any):
   - New DI container methods
   - New service classes
   - New factory methods

2. **Refactored functionality**:
   - Ensure behavior is preserved
   - Test new patterns (DI, service calls)
   - Verify backward compatibility

3. **Edge cases**:
   - Missing dependencies
   - Configuration errors
   - Null/None handling

### Step 4: Create/Update Tests

**Test Structure:**

```python
"""Tests for {{FILE_NAME}}."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import refactored code
from {{MODULE_PATH}} import {{CLASS_OR_FUNCTION}}

# Test fixtures
@pytest.fixture
def {{SERVICE_NAME}}():
    """Fixture for {{SERVICE_NAME}}."""
    # Create instance with test config
    return {{SERVICE_NAME}}(config=test_config)

@pytest.fixture
def mock_container():
    """Mock DI container for testing."""
    container = Mock()
    # Setup mock behavior
    return container


# Test classes
class Test{{FEATURE_NAME}}:
    """Test {{FEATURE_NAME}} functionality."""

    def test_{{BEHAVIOR}}_{{SCENARIO}}(self, {{SERVICE_NAME}}):
        """Test {{BEHAVIOR}} when {{SCENARIO}}."""
        # Arrange
        input_data = ...

        # Act
        result = {{SERVICE_NAME}}.{{METHOD}}(input_data)

        # Assert
        assert result is not None
        assert result.{{PROPERTY}} == expected_value

    def test_{{BEHAVIOR}}_with_error(self, {{SERVICE_NAME}}):
        """Test {{BEHAVIOR}} handles errors correctly."""
        # Arrange
        invalid_input = ...

        # Act & Assert
        with pytest.raises({{EXCEPTION_TYPE}}):
            {{SERVICE_NAME}}.{{METHOD}}(invalid_input)
```

**Common Test Patterns:**

```python
# DI Container Tests
class TestDIContainer:
    """Test DI container functionality."""

    def test_service_returns_singleton(self):
        """Test that container returns singleton instance."""
        service1 = container.get_service()
        service2 = container.get_service()
        assert service1 is service2

    def test_service_can_be_registered(self):
        """Test that services can be registered manually."""
        mock_service = Mock()
        container.register_service(mock_service)
        assert container.get_service() is mock_service

    def test_lazy_initialization(self):
        """Test that services are created on first use."""
        assert 'service' not in container._services
        container.get_service()
        assert 'service' in container._services

# Service Layer Tests
class Test{{SERVICE_NAME}}:
    """Test {{SERVICE_NAME}} service."""

    def test_{{METHOD}}_success(self):
        """Test {{METHOD}} with valid input."""
        result = service.{{METHOD}}(valid_input)
        assert result.status == "healthy"

    def test_{{METHOD}}_handles_errors(self):
        """Test {{METHOD}} handles exceptions correctly."""
        with patch('path.to.dependency', side_effect=Exception("Test error")):
            result = service.{{METHOD}}()
            assert result.status == "unhealthy"
            assert "error" in result.details
```

### Step 5: Run Tests

```bash
cd /Users/kepa.cantero/Projects/algoTrading

# Run specific test file
pytest {{TEST_FILE}} -v

# Run with coverage
pytest {{TEST_FILE}} -v --cov={{MODULE_PATH}} --cov-report=html

# Run specific test
pytest {{TEST_FILE}}::Test{{CLASS}}::test_{{method}} -v
```

### Step 6: Report Results

**Output Format:**

```markdown
## Testing Complete

**File:** {{PYTHON_FILE}}
**Test File:** {{TEST_FILE}}
**Status:** ✅ PASS / ❌ FAIL

**Tests Created/Updated:**
| Test | Description | Status |
|------|-------------|--------|
| test_service_singleton | Verify singleton behavior | ✅ PASS |
| test_service_registration | Verify manual registration | ✅ PASS |
| test_lazy_initialization | Verify lazy loading | ✅ PASS |

**Test Results Summary:**
- Total tests: N
- Passed: N
- Failed: N
- Skipped: N

**Coverage Report:**
- Line coverage: X%
- Branch coverage: Y%

**Failing Tests (if any):**
```
test_{{name}} - AssertionError: ...
Expected: ...
Actual: ...
```

**Issues Found:**
[List any issues or concerns]

**Recommendations:**
[Suggestions for improvement]

**Next:** [Ready for code review OR Fix needed]
```

---

## Quality Checklist

- [ ] All new functionality has tests
- [ ] All refactored functionality has tests
- [ ] Tests follow pytest conventions
- [ ] Fixtures used appropriately
- [ ] Mocks used for external dependencies
- [ ] Edge cases covered
- [ ] Error scenarios tested
- [ ] All tests pass

---

## Common Test Scenarios

### DI Container Testing

```python
def test_container_is_singleton():
    """Test DI container itself is singleton."""
    container1 = DIContainer()
    container2 = DIContainer()
    assert container1 is container2

def test_service_lifecycle():
    """Test service is created once and reused."""
    container = DIContainer()
    service1 = container.get_service()
    service2 = container.get_service()
    assert service1 is service2
    assert id(service1) == id(service2)

def test_container_thread_safety():
    """Test container is thread-safe (if applicable)."""
    import threading
    container = DIContainer()
    services = []

    def get_service():
        services.append(container.get_service())

    threads = [threading.Thread(target=get_service) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All should be the same instance
    assert len(set(id(s) for s in services)) == 1
```

### Service Layer Testing

```python
def test_service_handles_none_input():
    """Test service handles None gracefully."""
    service = Service(config)
    result = service.process(None)
    assert result.status == "error"
    assert "None" in result.message

def test_service_with_mock_dependency():
    """Test service with mocked dependency."""
    mock_dep = Mock()
    mock_dep.calculate.return_value = 42
    service = Service(dependency=mock_dep)
    result = service.calculate()
    assert result == 42
    mock_dep.calculate.assert_called_once()
```

---

## Troubleshooting

### Tests Fail After Refactoring

**Common causes:**
1. Import paths changed → Update test imports
2. Class/method signatures changed → Update test calls
3. Dependencies moved → Update mocks/patches
4. Configuration needed → Add test fixtures

### Coverage Is Low

**Add tests for:**
- Edge cases (empty, None, invalid inputs)
- Error paths (exceptions, error handling)
- New patterns (DI, service calls)
- Integration points (between modules)

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
**Orchestrator:** @agent-tech-lead-orchestrator
**Specialist:** @agent-python-testing-expert
