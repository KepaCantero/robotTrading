# Wrapper: Tester (Python Testing Expert)

**This template is a CONTEXT WRAPPER for @agent-tech-lead-orchestrator**

When calling @agent-tech-lead-orchestrator, pass this entire context to create/update tests deterministically.

---

## Agent to Delegate

**@agent-tech-lead-orchestrator** - Will coordinate the workflow and delegate to appropriate specialist agents.

---

## Context for Tech Lead Orchestrator

### Repository Information
```
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
Tests Directory: tests/
```

### Task
Create/update tests for: `{{PYTHON_FILE}}`

### Required Resources
```
Python File: {{PYTHON_FILE}}
Requirements: {{REQUIREMENTS_FILE}}
Test File: {{TEST_FILE}}
Changes: {{CHANGES_SUMMARY}}
BASE_RULES: .requirements/BASE_RULES.md
Test Template Patterns: .tasks/templates/TEST_PATTERNS.md (create this reference)
```

### Specialist Agent to Call
@agent-python-testing-expert (for creating/updating tests)

---

## Deterministic Instructions for @agent-python-testing-expert

### Step 1: Gather Context

```bash
# Read requirements to understand what tests are needed
Read {{REQUIREMENTS_FILE}}

# Read the source file to understand what needs testing
Read {{PYTHON_FILE}}

# Check if test file exists
ls {{TEST_FILE}}

# Get current date for test docstrings
date -u +%Y-%m-%d
```

### Step 2: Extract Required Tests

From requirements document, find "Required Tests" section and extract:
- Test cases that MUST be implemented
- Edge cases to cover
- Error scenarios to test

### Step 3: Check Existing Test File

If test file exists:
```bash
Read {{TEST_FILE}}
```

Identify:
- Existing tests that can be reused
- Tests that need to be added
- Tests that need to be updated

### Step 4: Create/Update Tests

**Test Structure Pattern:**
```python
"""
Tests for {{MODULE_PATH}}

Created: {{DATE}}
Coverage: Target >80%
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch

from {{MODULE_PATH}} import {{CLASSES_FUNCTIONS}}


class Test{{ClassName}}:
    """Test suite for {{ClassName}}."""

    @pytest.fixture
    def sample_{{entity}}(self):
        """Create sample {{entity}} for testing."""
        return {{Entity}}(
            # fields...
        )

    # Happy Path Tests
    def test_{{specific_behavior}}(self, sample_{{entity}}):
        """
        Test {{specific_behavior}}.

        Given {{preconditions}}
        When {{action}}
        Then {{expected_result}}
        """
        # Arrange
        # Act
        # Assert
        pass

    # Edge Case Tests
    def test_{{edge_case}}(self):
        """Test {{edge_case}} behavior."""
        pass

    # Error Handling Tests
    def test_{{error_scenario}}_raises_error(self):
        """Test that {{error_scenario}} raises appropriate exception."""
        with pytest.raises(ValueError, match="expected message"):
            # code that should raise
            pass
```

**Test Categories:**
1. Happy Path - Normal operation with valid inputs
2. Edge Cases - Boundary values, empty collections, None handling
3. Error Handling - Invalid inputs, exception validation
4. Integration - Dependencies, database, API mocks

### Step 5: Run Tests

```bash
# Run the tests
pytest {{TEST_FILE}} -v

# Run with coverage if available
pytest {{TEST_FILE}} --cov={{MODULE_PATH}} --cov-report=term-missing
```

Must pass before reporting complete.

---

## Required Output Format

@agent-python-testing-expert must return:

```markdown
## Tests Created/Updated

**File:** {{PYTHON_FILE}}
**Test File:** {{TEST_FILE}}
**Date:** {{DATE}}

**Tests Created:** {{N}}
**Tests Updated:** {{N}}

**Test Coverage:**
- Happy path: {{N}} tests
- Edge cases: {{N}} tests
- Error handling: {{N}} tests

**Test Summary:**
- test_{{name}}: {{description}}
- test_{{name}}: {{description}}
- ...

**Validation:**
- All tests pass: ✅
- Coverage: {{X}}%

**Test Commands:**
```bash
pytest {{TEST_FILE}} -v
```

**Next:** Ready for code review by @agent-code-reviewer
```

---

## Common Test Patterns Reference

### Testing Functions with Return Values
```python
def test_calculate_mid_price(self):
    """Test mid price calculation."""
    # Arrange
    bid = Decimal("100.00")
    ask = Decimal("101.00")

    # Act
    result = calculate_mid_price(bid, ask)

    # Assert
    assert result == Decimal("100.50")
```

### Testing Exceptions
```python
def test_calculate_mid_price_invalid_bid_raises_error(self):
    """Test that invalid bid raises ValueError."""
    with pytest.raises(ValueError, match="Invalid bid price"):
        calculate_mid_price(Decimal("-10"), Decimal("101"))
```

### Testing with Mocks
```python
@patch('app.services.trade_service.repository')
def test_process_trade_with_mock(self, mock_repo):
    """Test trade processing with mocked repository."""
    mock_repo.add.return_value = None
    result = process_trade(sample_trade)
    mock_repo.add.assert_called_once()
```

---

## Quality Checklist

- [ ] All required tests from requirements document created
- [ ] Happy path tests implemented
- [ ] Edge case tests implemented
- [ ] Error handling tests implemented
- [ ] All tests pass
- [ ] Test coverage >80% (if measurable)
- [ ] Descriptive test names
- [ ] Arrange-Act-Assert pattern followed
- [ ] External dependencies mocked

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
**Orchestrator:** @agent-tech-lead-orchestrator
**Specialist:** @agent-python-testing-expert
