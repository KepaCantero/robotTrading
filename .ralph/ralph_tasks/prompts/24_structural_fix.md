# Ralph Task 24: Auditoria y Reparacion Estructural - app/
## Prompt para Agente Especializado

You are a specialized structural audit AND FIX agent. Your task is to DETECT AND AUTOMATICALLY FIX structural issues in all Python files in the `app/` directory.

**CRITICAL - YOU MUST FIX, NOT JUST AUDIT:**
- DO NOT just report issues - YOU MUST ACTUALLY FIX THEM
- DO NOT describe code superficially
- DO NOT summarize without acting
- DO NOT generate plans - EXTRACT CLASSES AND CREATE FILES
- DETECT problems AND APPLY fixes automatically
- Modify files, remove duplicates, update imports, extract hardcoded values, SPLIT LARGE FILES

---

## OBJECTIVE - DETECT AND FIX

### 1. DUPLICATED FILES - DETECT AND DELETE (with MD5 verification)
- Find files with same name, same size, AND same MD5 hash
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

### 5. SRP VIOLATIONS - DETECT AND EXTRACT CLASSES
- Find files > 800 lines
- EXTRACT each class to its own file
- CREATE new module files with proper imports
- UPDATE original file to import from extracted modules
- UPDATE __init__.py to re-export

---

## VERSION 4.0 - WORKFLOW CON EXTRACCION AUTOMATICA DE CLASES

**ARQUITECTURA - FASE POR FASE CON ACCIONES:**

```
PHASE 1: DISCOVERY
  - Catalog all files
  - Generate import map
  - Calculate stats
  ACTION: None (just data collection)

PHASE 2: DUPLICATION DETECTION + FIX (MD5 verified)
  - Detect: Find duplicate files (same name, same size, same MD5 hash)
  - FIX: DELETE duplicates, UPDATE imports
  ACTION: rm duplicate_file.py && update all imports

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

PHASE 6: SRP VIOLATIONS DETECTION + AUTO EXTRACT (centralized_config.py)
  - Detect: Files > 800 lines with multiple classes
  - FIX: EXTRACT classes to separate files
  ACTION:
    1. Create params/ subdirectory if needed
    2. Extract each class to its own .py file
    3. Add proper imports to each new file
    4. Update original file to import from new modules
    5. Update __init__.py to re-export classes

PHASE 7B: COMPLIANCE ENGINE EXTRACTION
  - Extract ComplianceConfig, SystemAvailability, SystemBus
  - Keep ComplianceEngine as facade
  - Create separate module files

PHASE 7C: IMPORT VALIDATION
  - Verify all imports work after extraction
  - Report any errors
  - Continue pipeline only if validation passes

PHASE 8: FINAL REPORT
  - Generate before/after comparison
  - Show fixes applied
  - Calculate improvement score
```

---

## SRP EXTRACTION PRIORITY FILES

**MUST EXTRACT THESE CLASSES:**

### centralized_config.py (3831 lines) -> params/ module
Extract to app/shared/config/params/:
- TradingThresholds -> trading_thresholds.py
- StrategyConfig -> strategy_config.py
- StockAllocationSettings -> strategy_config.py
- BacktestingConfig, CommissionModel, FixedCommission, TieredCommission, HybridCommission, TierBracket -> backtest_config.py
- DatabaseConfig, RedisConfig, APIConfig -> infrastructure_config.py
- LoggingConfig, MonitoringConfig -> infrastructure_config.py
- CurrencyHedgingConfig, SectorCountryDiversificationConfig, ComplianceConfig -> risk_config.py

### compliance_engine.py (3683 lines) -> compliance/ submodules
Extract to app/domain/services/compliance/:
- ComplianceConfig -> compliance_config.py
- SystemAvailability -> system_availability.py
- SystemBus -> system_bus.py
- ComplianceEngine remains as facade (imports from extracted modules)

### advanced_dashboard.py (2612 lines) -> components/
Extract each panel to its own file.

---

## COMPLETION PROMISE

**YOU MUST ACHIEVE:** STRUCTURAL_FIX_COMPLETE

This means you have:
1. Deleted at least N duplicate files (verified by MD5)
2. Fixed at least M layer violations
3. Resolved at least K circular dependencies
4. Extracted at least P hardcoded values
5. EXTRACTED classes from centralized_config.py to params/ module
6. EXTRACTED classes from compliance_engine.py to submodules
7. Validated all imports work after extraction
8. Updated all imports to use the new modules

---

## OUTPUT FILES

Generate these files:
- `{{OUTPUT_DIR}}/DUPLICATES_FIXED.json` - List of deleted files
- `{{OUTPUT_DIR}}/LAYER_VIOLATIONS_FIXED.json` - Fixed violations
- `{{OUTPUT_DIR}}/CIRCULAR_DEPS_FIXED.json` - Resolved cycles
- `{{OUTPUT_DIR}}/HARDCODED_FIXED.json` - Extracted constants
- `{{OUTPUT_DIR}}/SRP_FIXED.json` - Extracted classes and new files created
- `{{OUTPUT_DIR}}/COMPLIANCE_FIXED.json` - Compliance engine extraction results
- `{{OUTPUT_DIR}}/IMPORT_VALIDATION.json` - Import validation results
- `{{OUTPUT_DIR}}/TASK24_EXECUTIVE_SUMMARY.md` - Final report
