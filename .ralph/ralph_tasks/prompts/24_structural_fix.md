# Ralph Task 24: Auditoria y Reparacion Estructural - app/
## Prompt para Agente Especializado

You are a specialized structural audit AND FIX agent. Your task is to DETECT AND AUTOMATICALLY FIX structural issues in all Python files in the `app/` directory.

**CRITICAL - YOU MUST FIX, NOT JUST AUDIT:**
- DO NOT just report issues - YOU MUST ACTUALLY FIX THEM
- DO NOT describe code superficially
- DO NOT summarize without acting
- DETECT problems AND APPLY fixes automatically
- Modify files, remove duplicates, update imports, extract hardcoded values

---

## OBJECTIVE - DETECT AND FIX

### 1. DUPLICATED FILES - DETECT AND DELETE
- Find files with same name and same size in different locations
- DELETE the duplicate, KEEP the canonical version
- Rules: shared/ > domain/ > infrastructure/ > core/ > services/
- UPDATE all imports after deletion

### 2. LAYER VIOLATIONS - DETECT AND FIX
- Domain should NOT import infrastructure
- Infrastructure should NOT import presentation
- FIX by: moving modules to shared/, or using late imports

### 3. CIRCULAR DEPENDENCIES - DETECT AND FIX
- Find cycles in import graph
- FIX by: converting to late imports inside functions

### 4. HARDCODED VALUES - DETECT AND EXTRACT
- Find Decimal("0.xx") that appear 3+ times
- EXTRACT to centralized config
- REPLACE with getattr(get_config(), "param_name", default)

### 5. SRP VIOLATIONS - DETECT AND PLAN
- Find files > 1000 lines
- GENERATE refactor plan to split

---

## VERSION 2.0 - WORKFLOW CON FIXES

**ARQUITECTURA - FASE POR FASE CON ACCIONES:**

```
PHASE 1: DISCOVERY
  - Catalog all files
  - Generate import map
  - Calculate stats
  ACTION: None (just data collection)

PHASE 2: DUPLICATION DETECTION + FIX
  - Detect: Find duplicate files (same name, same size)
  - FIX: DELETE duplicates, UPDATE imports
  ACTION: rm duplicate_file.py && sed -i 's/old_import/new_import/g'

PHASE 3: LAYER VIOLATION DETECTION + FIX
  - Detect: domain imports infrastructure
  - FIX: MOVE module to shared/ OR use late import
  ACTION: mv or modify import lines

PHASE 4: CIRCULAR DEPENDENCY DETECTION + FIX
  - Detect: cycles in import graph
  - FIX: Convert to late import
  ACTION: Move import inside function

PHASE 5: HARDCODED VALUES DETECTION + FIX
  - Detect: Decimal("0.xx") appearing 3+ times
  - FIX: Add import get_config, replace with getattr()
  ACTION: Modify files to use config

PHASE 6: SRP VIOLATIONS DETECTION + PLAN
  - Detect: Files > 1000 lines
  - FIX: Generate refactor plan
  ACTION: Create plan for manual review

PHASE 7: FINAL REPORT
  - Generate before/after comparison
  - Show fixes applied
  - Calculate improvement score
```

---

## COMPLETION PROMISE

**YOU MUST ACHIEVE:** STRUCTURAL_FIX_COMPLETE

This means you have:
1. Deleted at least N duplicate files
2. Fixed at least M layer violations
3. Resolved at least K circular dependencies
4. Extracted at least P hardcoded values
5. Generated refactor plans for large files

---

## OUTPUT FILES

Generate these files:
- `{{OUTPUT_DIR}}/DUPLICATES_FIXED.json` - List of deleted files
- `{{OUTPUT_DIR}}/LAYER_VIOLATIONS_FIXED.json` - Fixed violations
- `{{OUTPUT_DIR}}/CIRCULAR_DEPS_FIXED.json` - Resolved cycles
- `{{OUTPUT_DIR}}/HARDCODED_FIXED.json` - Extracted constants
- `{{OUTPUT_DIR}}/SRP_REFACTOR_PLAN.json` - Refactor plans
- `{{OUTPUT_DIR}}/TASK24_EXECUTIVE_SUMMARY.md` - Final report
