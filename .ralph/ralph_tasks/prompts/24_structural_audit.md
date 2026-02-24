# Ralph Task 24: Auditoría Estructural Completa - app/
## Prompt para Agente Especializado

You are a specialized structural audit agent. Your task is to perform a COMPLETE STRUCTURAL AUDIT of all Python files in the `app/` directory.

**IMPORTANT:**
- DO NOT describe code superficially
- DO NOT summarize
- DO NOT reformat
- ANALYZE architecture, duplications, consistency, and structural quality

---

## OBJECTIVE

Evaluate the following strictly:

### 1. DUPLICATED LOGIC
- Detect functions, blocks, or algorithms that implement the same logic with slight variations
- Identify implicit duplications (same intent, different name)
- Indicate where common functions or shared modules should be extracted
- Classify duplication: exact, partial, conceptual

### 2. DUPLICATED OR OVERLAPPING FILES
- Detect files that essentially do the same thing
- Identify poorly separated responsibilities
- Identify violations of the Single Responsibility Principle
- Indicate if "shadow" modules exist (same purpose in different path)

### 3. CENTRALIZED CONFIGURATION
- Verify that constants, parameters, thresholds, magic numbers, and settings are centralized
- Detect hardcoded values

### 4. LIBRARY REUSE
- Detect manual logic that should use:
  - STL / Python standard library
  - Standard algorithms
  - Mathematical libraries (numpy, scipy, pandas)
  - Parsing libraries
  - Concurrency libraries
- Indicate wheel reinvention
- Indicate unnecessary maintenance cost

### 5. ARCHITECTURAL COHERENCE
- Are layers mixed?
- Are there clear separation violations?
- Circular dependencies?
- Heavy logic in headers/modules?
- Unnecessary imports?
- Suboptimal compilation/structure?

---

## VERSION 1.0 - WORKFLOW

**ARCHITECTURE - PHASE BY PHASE:**

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: DISCOVERY                                             │
│  - Catalog all files and directories                            │
│  - Generate import map                                          │
│  - Generate base statistics                                     │
│  ✓ Output: STRUCTURE_STATS.json                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: DUPLICATION DETECTION                                 │
│  - Detect similar functions                                     │
│  - Detect duplicate code blocks                                 │
│  - Detect shadow files                                          │
│  - Classify duplications                                        │
│  ✓ Output: DUPLICATION_REPORT.json                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: CONFIG AUDIT                                          │
│  - Verify centralized config system                             │
│  - Detect hardcoded percentages                                 │
│  - Detect hardcoded decimals                                    │
│  - Detect hardcoded thresholds                                  │
│  ✓ Output: CONFIG_AUDIT_REPORT.json                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: LIBRARY USAGE ANALYSIS                                │
│  - Detect manual std calculations                               │
│  - Detect manual correlation                                    │
│  - Detect manual moving averages                                │
│  - Detect manual percentiles                                    │
│  - Identify wheel reinvention                                   │
│  ✓ Output: LIBRARY_AUDIT_REPORT.json                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: ARCHITECTURE ANALYSIS                                 │
│  - Verify layer separation                                      │
│  - Detect circular dependencies                                 │
│  - Detect SRP violations                                        │
│  - Detect unnecessary imports                                   │
│  ✓ Output: ARCHITECTURE_AUDIT_REPORT.json                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 6: FINAL REPORT                                          │
│  - Consolidate all findings                                     │
│  - Calculate overall score                                      │
│  - Generate prioritized action plan                             │
│  ✓ Output: STRUCTURAL_AUDIT_FINAL_REPORT.json                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## SEVERITY CLASSIFICATION

### CRITICAL
- Circular dependencies between layers
- Hardcoded values in trading logic
- Complete duplication of critical functions
- Violations of basic architectural principles

### HIGH
- Partial duplication that should be consolidated
- Hardcoded configuration values
- Manual implementations that could use libraries
- SRP violations in critical files

### MEDIUM
- Conceptual duplication (same intent, different implementation)
- Minor hardcoded values
- Unnecessary imports
- Files that could be consolidated

### LOW
- Code style inconsistencies
- Minor optimization opportunities
- Documentation gaps

---

## DETECTION PATTERNS

### 1. Duplicated Logic Patterns

```bash
# Similar function signatures
grep -rh "def " app/ --include="*.py" | grep -v "__" | sort

# Common calculation patterns
grep -rh "sqrt\|sum.*\*\*\|mean\|std\|variance" app/ --include="*.py"

# Similar class structures
grep -rh "class " app/ --include="*.py" | sort
```

### 2. Shadow File Patterns

```bash
# Files with same name in different directories
find app/ -type f -name "*.py" | xargs -I {} basename {} | sort | uniq -d
```

### 3. Hardcoded Value Patterns

```bash
# Magic percentages
grep -rn "0\.[0-9][0-9]" app/ --include="*.py" | grep -v "test\|0.0\|1.0"

# Hardcoded decimals
grep -rn 'Decimal("0\.' app/ --include="*.py"

# Hardcoded thresholds
grep -rn "threshold\|limit\|max\|min" app/ --include="*.py" | grep "= 0\."
```

### 4. Wheel Reinvention Patterns

```python
# BAD - Manual standard deviation
mean = sum(values) / len(values)
variance = sum((x - mean)**2 for x in values) / len(values)
std = math.sqrt(variance)

# GOOD - Use numpy
import numpy as np
std = np.std(values)

# BAD - Manual correlation
# ... complex manual calculation

# GOOD - Use numpy
correlation = np.corrcoef(x, y)[0, 1]

# BAD - Manual moving average
ma_values = []
for i in range(len(prices) - window + 1):
    ma_values.append(sum(prices[i:i+window]) / window)

# GOOD - Use pandas
ma_values = pd.Series(prices).rolling(window).mean()
```

### 5. Architecture Violation Patterns

```python
# BAD - Domain importing Infrastructure
# app/domain/services/some_service.py
from app.infrastructure.database import Database  # VIOLATION!

# GOOD - Use dependency injection
class SomeService:
    def __init__(self, db: DatabaseInterface):
        self._db = db

# BAD - Circular dependency
# module_a.py
from module_b import func_b

# module_b.py
from module_a import func_a  # CIRCULAR!
```

---

## OUTPUT FORMAT

### STRUCTURAL_AUDIT_FINAL_REPORT.json

```json
{
  "task": "24_structural_audit",
  "timestamp": "2026-02-22T00:00:00Z",
  "summary": {
    "total_files": 400,
    "total_lines": 50000,
    "overall_score": 72
  },
  "categories": {
    "duplication": {
      "score": 65,
      "issues": [
        {
          "type": "exact",
          "severity": "HIGH",
          "location": "app/services/calc_a.py:50",
          "duplicate_of": "app/services/calc_b.py:45",
          "description": "Identical calculate_std function"
        }
      ],
      "severity_counts": {"CRITICAL": 0, "HIGH": 5, "MEDIUM": 12, "LOW": 8}
    },
    "config": {
      "score": 45,
      "hardcoded_values": 234,
      "issues": [
        {
          "type": "hardcoded_percentage",
          "severity": "CRITICAL",
          "location": "app/services/risk.py:100",
          "code": "if exposure > 0.35:",
          "recommendation": "Use getattr(config.trading, 'max_exposure_pct', 0.35)"
        }
      ],
      "severity_counts": {"CRITICAL": 15, "HIGH": 45, "MEDIUM": 120, "LOW": 54}
    },
    "libraries": {
      "score": 70,
      "reinventions": 34,
      "issues": [
        {
          "type": "manual_calculation",
          "severity": "HIGH",
          "location": "app/analysis/metrics.py:200",
          "code": "std = math.sqrt(sum((x-mean)**2 for x in values)/len(values))",
          "recommendation": "Use np.std(values)"
        }
      ],
      "severity_counts": {"CRITICAL": 0, "HIGH": 8, "MEDIUM": 15, "LOW": 11}
    },
    "architecture": {
      "score": 80,
      "violations": 12,
      "issues": [
        {
          "type": "circular_dependency",
          "severity": "CRITICAL",
          "modules": ["app.services.a", "app.services.b", "app.services.c"],
          "description": "Circular import chain detected"
        },
        {
          "type": "layer_violation",
          "severity": "HIGH",
          "location": "app/domain/services/x.py",
          "violation": "Domain imports Infrastructure",
          "recommendation": "Use dependency injection"
        }
      ],
      "severity_counts": {"CRITICAL": 2, "HIGH": 5, "MEDIUM": 3, "LOW": 2}
    }
  },
  "recommendations": [
    "CRITICAL: Resolve 2 circular dependency chains",
    "CRITICAL: Centralize 15 critical hardcoded values",
    "HIGH: Consolidate 5 exact duplications into shared modules",
    "HIGH: Replace 8 manual calculations with library functions",
    "MEDIUM: Fix 5 layer separation violations"
  ],
  "action_plan": {
    "immediate": [
      "Resolve circular dependencies in services layer",
      "Extract hardcoded trading thresholds to config",
      "Consolidate duplicated calculation functions"
    ],
    "short_term": [
      "Replace manual statistical implementations with numpy",
      "Fix layer separation violations",
      "Remove shadow files and consolidate"
    ],
    "long_term": [
      "Implement comprehensive shared utilities module",
      "Create centralized validation framework",
      "Refactor large files following SRP"
    ]
  }
}
```

---

## COMPLETION CRITERIA

Task is COMPLETE when:
- [ ] All `.py` files in `app/` have been cataloged
- [ ] All duplications detected and classified
- [ ] All hardcoded values identified
- [ ] All wheel reinventions detected
- [ ] All architectural violations found
- [ ] Severity assigned to each issue
- [ ] Overall score calculated
- [ ] Prioritized action plan generated
- [ ] Final report in JSON format
- [ ] Executive summary in Markdown format

---

## IMPORTANT NOTES

1. **Do not fix anything** - This is an AUDIT task, not a fix task
2. **Be thorough** - Every file must be analyzed
3. **Be precise** - Include exact file:line locations
4. **Be actionable** - Recommendations must be specific
5. **Prioritize** - Use severity levels correctly

---

## CHECKPOINT HANDLING

If execution is interrupted:
1. Load last checkpoint to see progress
2. Resume from first incomplete phase
3. Update tracking report as phases complete
4. Save checkpoint after each phase

Checkpoint structure:
```json
{
  "phase": "duplication_detection",
  "files_analyzed": ["app/services/file1.py", ...],
  "current_file": "app/services/file2.py",
  "issues_found": 45,
  "timestamp": "2026-02-22T10:00:00Z"
}
```

---

Start with discovery, then analyze each category systematically, and generate comprehensive final report with prioritized action plan.

REMEMBER: **Audit means IDENTIFY and DOCUMENT, not FIX.**
