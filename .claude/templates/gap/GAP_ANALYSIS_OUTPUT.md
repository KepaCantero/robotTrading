# Template: GAP Analysis Output Format

Use this template when reporting GAP violations found in a Python file.

---

## GAP Analysis Report for: `[FileName].py`

**File Path:** `app/[PATH]/[FileName].py`
**Requirements File:** `.requirements/[PATH]/[FileName].requirements.md`
**Analysis Date:** `YYYY-MM-DD`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Violations | X |
| From BASE_RULES.md | Y |
| From File-Specific Requirements | Z |
| P0 (Critical) | A |
| P1 (High) | B |
| P2 (Medium) | C |
| P3 (Low) | D |

---

## Violations from BASE_RULES.md (Universal Rules)

### P0 (Critical) - A violations

**[LOG-001]**:line_number - [Description]
```python
# Code snippet showing violation
```
**Fix Required:** [What needs to be done]

### P1 (High) - B violations

**[CC-006]**:line_number - [Description]
```python
# Code snippet showing violation
```
**Fix Required:** [What needs to be done]

### P2 (Medium) - C violations

**[TYP-001]**:line_number - [Description]
```python
# Code snippet showing violation
```
**Fix Required:** [What needs to be done]

---

## Violations from File-Specific Requirements

### ❌ Still Violated - W violations

**[RULE-ID]**:line_number - [Description from requirements.md]
```python
# Code snippet showing violation
```
**Status in requirements:** ❌ GAP
**Fix Required:** [What needs to be done]

### ⚠️ PARTIAL - V violations

**[RULE-ID]**:line_range - [Description]
```python
# Code snippet showing partial implementation
```
**Status in requirements:** ⚠️ PARTIAL
**Missing:** [What's missing to complete]

### ✅ Already OK

**[RULE-ID]** - [Description]
**Status:** ✅ OK - Rule is correctly implemented

### ⚠️ NOT APPLIED (with justification)

**[RULE-ID]** - [Description]
**Status:** ⚠️ NOT APPLIED
**Reason:** [Why this rule doesn't apply to this file]

---

## Status Meanings

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| ❌ VIOLATED | Rule is broken | YES - Fix required |
| ✅ OK | Rule is followed correctly | NO |
| ⚠️ NOT APPLIED | Rule doesn't apply | NO (with justification) |
| ⚠️ PARTIAL | Rule partially followed | YES - Complete implementation |
| ✅ FIXED | Previously violated, now fixed | NO |

---

## Priority Definitions

| Priority | Description | Examples |
|----------|-------------|----------|
| P0 | Critical - Security, Crashes, Data Loss | SEC-001, SEC-002, SEC-003, CC-006, TRD-001, TRD-005 |
| P1 | High - Production Standards | LOG-001, LOG-004, TRD-004, TRD-007, SEC-007 |
| P2 | Medium - Code Quality | TYP-001, TYP-003, ARCH-004, ARCH-006 |
| P3 | Low - Nice to Have | FMT-001, PERF-001 |

---

## Next Steps

1. **For ❌ VIOLATED violations:**
   - Call @agent-python-expert to fix
   - Create/update tests
   - Run code review
   - Verify fix

2. **For ⚠️ PARTIAL violations:**
   - Complete implementation
   - Add missing parts
   - Update requirements to ✅ OK

3. **For ⚠️ NOT APPLIED violations:**
   - Ensure justification is valid
   - Document why rule doesn't apply

---

**Analyzed by:** @agent-python-expert
**Template Version:** 1.0
**BASE_RULES.md Reference:** `.requirements/BASE_RULES.md`
