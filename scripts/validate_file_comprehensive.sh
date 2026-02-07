#!/bin/bash
# Comprehensive validation script for GAP audit
# Runs all validation tools and generates a report

set -e

FILE_PATH="$1"
REPORT_DIR="${2:-$(pwd)/.gap_reports}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create report directory
mkdir -p "$REPORT_DIR"

REPORT_FILE="$REPORT_DIR/validation_$(basename "$FILE_PATH" .py)_${TIMESTAMP}.md"

echo "# Validation Report: $FILE_PATH" > "$REPORT_FILE"
echo "**Generated:** $TIMESTAMP" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo -e "${YELLOW}Running comprehensive validation for:${NC} $FILE_PATH"
echo ""

# 1. Type checking with mypy
echo "## 1. Type Checking (mypy)" >> "$REPORT_FILE"
echo -n "Running mypy... "
if mypy --ignore-missing-imports --no-error-summary "$FILE_PATH" 2>&1 | tee -a "$REPORT_FILE" | grep -q "Success"; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "**Status:** ✅ PASSED" >> "$REPORT_FILE"
else
    echo -e "${RED}✗ FAILED${NC}"
    echo "**Status:** ❌ FAILED" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 2. Linting with ruff
echo "## 2. Linting (ruff)" >> "$REPORT_FILE"
echo -n "Running ruff... "
if ruff check "$FILE_PATH" --output-format=json > /tmp/ruff_output.json 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "**Status:** ✅ PASSED" >> "$REPORT_FILE"
else
    echo -e "${YELLOW}⚠ ISSUES FOUND${NC}"
    echo "**Status:** ⚠️ ISSUES FOUND" >> "$REPORT_FILE"
    echo '```json' >> "$REPORT_FILE"
    cat /tmp/ruff_output.json >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 3. Security with bandit
echo "## 3. Security (bandit)" >> "$REPORT_FILE"
echo -n "Running bandit... "
if bandit "$FILE_PATH" -f json -o /tmp/bandit_output.json 2>/dev/null; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "**Status:** ✅ PASSED" >> "$REPORT_FILE"
else
    echo -e "${YELLOW}⚠ ISSUES FOUND${NC}"
    echo "**Status:** ⚠️ ISSUES FOUND" >> "$REPORT_FILE"
    echo '```json' >> "$REPORT_FILE"
    cat /tmp/bandit_output.json >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 4. Complexity with radon
echo "## 4. Complexity (radon)" >> "$REPORT_FILE"
echo -n "Running radon... "
radon cc "$FILE_PATH" -a -s >> "$REPORT_FILE" 2>&1 || true
# Extract complexity using Python instead of grep -P (not compatible with macOS)
COMPLEXITY=$(radon cc "$FILE_PATH" -a -s 2>/dev/null | python3 -c "import sys, re; matches = re.findall(r'\([\d.]+\)', sys.stdin.read()); values = [float(m.strip('()')) for m in matches]; print(max(values)) if values else print('')" | head -1)
if [ -n "$COMPLEXITY" ] && [ $(echo "$COMPLEXITY < 10" | bc -l 2>/dev/null || echo "0") -eq 1 ]; then
    echo -e "${GREEN}✓ GOOD (avg: $COMPLEXITY)${NC}"
else
    echo -e "${YELLOW}⚠ HIGH COMPLEXITY${NC}"
fi
echo "" >> "$REPORT_FILE"

# 5. Maintainability index
echo "## 5. Maintainability Index" >> "$REPORT_FILE"
radon mi "$FILE_PATH" -s >> "$REPORT_FILE" 2>&1 || true
echo "" >> "$REPORT_FILE"

# 6. Syntax check
echo "## 6. Syntax Check" >> "$REPORT_FILE"
echo -n "Running python -m py_compile... "
if python -m py_compile "$FILE_PATH" 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "**Status:** ✅ PASSED" >> "$REPORT_FILE"
else
    echo -e "${RED}✗ FAILED${NC}"
    echo "**Status:** ❌ FAILED" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 7. Import validation
echo "## 7. Import Validation" >> "$REPORT_FILE"
echo -n "Checking imports... "
if python -c "
import sys
import ast
with open('$FILE_PATH', 'r') as f:
    ast.parse(f.read())
" 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "**Status:** ✅ PASSED" >> "$REPORT_FILE"
else
    echo -e "${RED}✗ FAILED${NC}"
    echo "**Status:** ❌ FAILED" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# Summary
echo "---" >> "$REPORT_FILE"
echo "## Summary" >> "$REPORT_FILE"
echo "**Validation completed at:** $TIMESTAMP" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo ""
echo -e "${GREEN}Validation complete!${NC}"
echo "Report saved to: $REPORT_FILE"

# Exit with appropriate code
if [ -f "$REPORT_FILE" ] && grep -q "❌ FAILED" "$REPORT_FILE"; then
    exit 1
fi
exit 0
