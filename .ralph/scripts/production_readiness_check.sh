#!/bin/bash
# ============================================
# Production Readiness Quick Check
# ============================================
# Ejecuta validaciones rapidas sin backtests
# Tiempo: ~5 minutos
# ============================================

set -e

PROJECT_ROOT="/Users/kepa.cantero/Projects/algoTrading"
cd "$PROJECT_ROOT"

echo "========================================"
echo "PRODUCTION READINESS QUICK CHECK"
echo "========================================"
echo ""

# Create results file
RESULTS_FILE=".ralph/outputs/production_readiness_results.txt"
mkdir -p .ralph/outputs

echo "# Production Readiness Results" > "$RESULTS_FILE"
echo "Date: $(date)" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# ============================================
# CHECK 1: Foundation
# ============================================
echo "## 1. FOUNDATION CHECK" >> "$RESULTS_FILE"

echo -n "Protocols exist: "
PROTOCOLS=$(ls app/core/protocols/*.py 2>/dev/null | wc -l | tr -d ' ')
echo "Protocols: $PROTOCOLS files" >> "$RESULTS_FILE"
if [ "$PROTOCOLS" -ge 1 ]; then
    echo "OK"
else
    echo "MISSING"
fi

echo -n "Tax Engine: "
if [ -f "app/services/tax_efficiency/engines/spain_tax_engine.py" ]; then
    echo "OK" >> "$RESULTS_FILE"
    echo "OK"
else
    echo "MISSING" >> "$RESULTS_FILE"
    echo "MISSING"
fi

echo -n "Decision Logger: "
if [ -f "app/infrastructure/logging/trading_decision_logger.py" ]; then
    echo "OK" >> "$RESULTS_FILE"
    echo "OK"
else
    echo "MISSING" >> "$RESULTS_FILE"
    echo "MISSING"
fi

echo -n "Risk Validators: "
RISK=$(ls app/services/risk/*.py 2>/dev/null | wc -l | tr -d ' ')
echo "Risk: $RISK files" >> "$RESULTS_FILE"
if [ "$RISK" -ge 1 ]; then
    echo "OK"
else
    echo "MISSING"
fi

echo ""

# ============================================
# CHECK 2: Central Config
# ============================================
echo "## 2. CENTRAL CONFIG CHECK" >> "$RESULTS_FILE"

echo -n "Central Config: "
if [ -f "app/shared/config/centralized_config.py" ] || [ -f "app/shared/config/trading_thresholds.py" ]; then
    echo "OK" >> "$RESULTS_FILE"
    echo "OK"
else
    echo "MISSING" >> "$RESULTS_FILE"
    echo "MISSING"
fi

echo -n "API Endpoints: "
if [ -f "app/shared/config/api_endpoints.py" ]; then
    echo "OK" >> "$RESULTS_FILE"
    echo "OK"
else
    echo "MISSING" >> "$RESULTS_FILE"
    echo "MISSING"
fi

echo -n "Magic Numbers: "
MAGIC=$(grep -rn "0\.02\|0\.15\|2\.0" app --include="*.py" 2>/dev/null | grep -v "config\|test\|spec\|threshold\|timeout" | wc -l | tr -d ' ')
echo "Magic numbers outside config: $MAGIC" >> "$RESULTS_FILE"
if [ "$MAGIC" -le 10 ]; then
    echo "OK ($MAGIC found)"
else
    echo "WARNING ($MAGIC found)"
fi

echo ""

# ============================================
# CHECK 3: Code Quality
# ============================================
echo "## 3. CODE QUALITY CHECK" >> "$RESULTS_FILE"

echo -n "Black: "
BLACK_ERRORS=$(black app --check 2>&1 | grep -c "would reformat" || echo "0")
echo "Black: $BLACK_ERRORS files need formatting" >> "$RESULTS_FILE"
if [ "$BLACK_ERRORS" -eq 0 ]; then
    echo "OK"
else
    echo "$BLACK_ERRORS files need formatting"
fi

echo -n "Ruff: "
RUFF_ERRORS=$(ruff check app 2>&1 | wc -l | tr -d ' ')
echo "Ruff: $RUFF_ERRORS issues" >> "$RESULTS_FILE"
if [ "$RUFF_ERRORS" -le 20 ]; then
    echo "OK ($RUFF_ERRORS issues)"
else
    echo "$RUFF_ERRORS issues"
fi

echo -n "Mypy: "
MYPY_ERRORS=$(mypy app --ignore-missing-imports 2>&1 | grep -c "error:" || echo "0")
echo "Mypy: $MYPY_ERRORS errors" >> "$RESULTS_FILE"
if [ "$MYPY_ERRORS" -le 10 ]; then
    echo "OK ($MYPY_ERRORS errors)"
else
    echo "$MYPY_ERRORS errors"
fi

echo ""

# ============================================
# CHECK 4: Specialized Libraries
# ============================================
echo "## 4. SPECIALIZED LIBRARIES CHECK" >> "$RESULTS_FILE"

echo -n "Numpy usage: "
NUMPY=$(grep -rn "np\.\(sum\|mean\|std\|dot\|array\)" app --include="*.py" 2>/dev/null | wc -l | tr -d ' ')
echo "Numpy: $NUMPY usages" >> "$RESULTS_FILE"
if [ "$NUMPY" -ge 10 ]; then
    echo "OK ($NUMPY usages)"
else
    echo "LOW ($NUMPY usages)"
fi

echo -n "Pandas usage: "
PANDAS=$(grep -rn "pd\.\(DataFrame\|Series\|rolling\)" app --include="*.py" 2>/dev/null | wc -l | tr -d ' ')
echo "Pandas: $PANDAS usages" >> "$RESULTS_FILE"
if [ "$PANDAS" -ge 10 ]; then
    echo "OK ($PANDAS usages)"
else
    echo "LOW ($PANDAS usages)"
fi

echo -n "Scipy usage: "
SCIPY=$(grep -rn "scipy\.\(stats\|optimize\)" app --include="*.py" 2>/dev/null | wc -l | tr -d ' ')
echo "Scipy: $SCIPY usages" >> "$RESULTS_FILE"
echo "$SCIPY usages"

echo ""

# ============================================
# CHECK 5: Security
# ============================================
echo "## 5. SECURITY CHECK" >> "$RESULTS_FILE"

echo -n "Hardcoded secrets: "
SECRETS=$(grep -rn "api_key\|password\|secret\|token" app --include="*.py" 2>/dev/null | grep -v "config\|env\|os\.getenv\|test\|spec" | wc -l | tr -d ' ')
echo "Potential hardcoded secrets: $SECRETS" >> "$RESULTS_FILE"
if [ "$SECRETS" -eq 0 ]; then
    echo "OK"
else
    echo "WARNING ($SECRETS potential)"
fi

echo -n "Audit logging: "
AUDIT=$(grep -rn "audit\|decision_logger" app/services --include="*.py" 2>/dev/null | wc -l | tr -d ' ')
echo "Audit logging: $AUDIT usages" >> "$RESULTS_FILE"
if [ "$AUDIT" -ge 5 ]; then
    echo "OK ($AUDIT usages)"
else
    echo "LOW ($AUDIT usages)"
fi

echo ""

# ============================================
# CHECK 6: Requirements
# ============================================
echo "## 6. REQUIREMENTS CHECK" >> "$RESULTS_FILE"

PYTHON_FILES=$(find app -name "*.py" -type f | wc -l | tr -d ' ')
REQUIREMENTS_FILES=$(find .requirements -name "*.requirements.txt" | wc -l | tr -d ' ')
echo "Python files: $PYTHON_FILES" >> "$RESULTS_FILE"
echo "Requirements files: $REQUIREMENTS_FILES" >> "$RESULTS_FILE"

echo -n "Requirements coverage: "
if [ "$PYTHON_FILES" -eq "$REQUIREMENTS_FILES" ]; then
    echo "OK (100%)"
else
    echo "MISSING ($((PYTHON_FILES - REQUIREMENTS_FILES)) files)"
fi

echo ""

# ============================================
# SUMMARY
# ============================================
echo "========================================" >> "$RESULTS_FILE"
echo "## SUMMARY" >> "$RESULTS_FILE"
echo "========================================" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "Production Ready: Check results above" >> "$RESULTS_FILE"

echo ""
echo "========================================"
echo "QUICK CHECK COMPLETE"
echo "========================================"
echo ""
echo "Results saved to: $RESULTS_FILE"
echo ""
echo "Run 'cat $RESULTS_FILE' for full details"
