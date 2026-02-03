# Wrapper: Implementer (Python Expert)

**This template is a CONTEXT WRAPPER for @agent-tech-lead-orchestrator**

When calling @agent-tech-lead-orchestrator, pass this entire context to fix GAP violations deterministically.

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
```

### Task
Fix GAP violations in: `{{PYTHON_FILE}}`

### Required Resources
```
Python File: {{PYTHON_FILE}}
Requirements: {{REQUIREMENTS_FILE}}
BASE_RULES: .requirements/BASE_RULES.md (96+ rules)
Fix Patterns: .tasks/templates/GAP_FIX_PATTERNS.md
Mode: {{MODE}}  # Minimal or Full
```

### Specialist Agent to Call
@agent-python-expert (for fixing GAP violations)

---

## Deterministic Instructions for @agent-python-expert

### Step 1: Read Requirements

```
Read {{REQUIREMENTS_FILE}}
```

Extract GAP violations from "Critical Rules (MUST NOT BREAK)" table.
Only fix rules marked as ❌ GAP.

### Step 2: Read Python File

```
Read {{PYTHON_FILE}}
```

### Step 3: Apply Fixes (Use GAP_FIX_PATTERNS.md)

**Reference:** `.tasks/templates/GAP_FIX_PATTERNS.md`

For each ❌ GAP violation:
1. Locate violating code (line number from requirements)
2. Apply fix from GAP_FIX_PATTERNS.md
3. Use Edit tool (not Write) to make minimal changes

**In Minimal Mode:**
- Only fix the specific GAP violations
- Don't refactor other code
- Preserve all existing functionality

**In Full Mode:**
- Fix GAPs and refactor related code
- Improve overall code quality
- Still preserve functionality

### Step 4: Validate Syntax

```bash
python -m py_compile {{PYTHON_FILE}}
```

Must pass before reporting complete.

---

## Required Output Format

@agent-python-expert must return:

```markdown
## Implementation Complete

**File:** {{PYTHON_FILE}}
**Mode:** {{MODE}}

**GAPs Fixed:**
- RULE-ID:line - Description
- RULE-ID:line - Description

**Changes Summary:**
- [Brief summary of changes]

**Validation:**
- Syntax check: ✅ PASS

**Next:** Ready for testing by @agent-python-testing-expert
```

---

## Quick Fix Reference (From GAP_FIX_PATTERNS.md)

### LOG-001: Structured Logging
```python
# ❌ BAD
logger.info(f"Processing {symbol}")

# ✅ GOOD
logger.info("Processing", symbol=symbol)
```

### LOG-004: Exception Stack Traces
```python
# ❌ BAD
except Exception as e:
    logger.error("Failed", error=str(e))

# ✅ GOOD
except Exception as e:
    logger.error("Failed", error=str(e), exc_info=True)
```

### CC-006: Explicit Error Handling
```python
# ❌ BAD
except Exception as e:

# ✅ GOOD
except ValueError as e:
except ValidationError as e:
```

### FMT-007: DateTime Deprecated
```python
# ❌ BAD
default=datetime.utcnow

# ✅ GOOD
default=lambda: datetime.now(timezone.utc)
```

### TYP-001: Return Types
```python
# ❌ BAD
def process(x):

# ✅ GOOD
def process(x) -> int:
```

---

## Quality Checklist

- [ ] All ❌ GAP violations fixed
- [ ] Syntax check passes
- [ ] No new violations introduced
- [ ] Existing functionality preserved
- [ ] Used Edit tool (not Write) for minimal changes

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
**Orchestrator:** @agent-tech-lead-orchestrator
