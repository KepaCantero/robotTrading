#!/bin/bash
# QA Baseline Check Script
# Run this script to perform all QA checks on the algoTrading codebase

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="/Users/kepa.cantero/Projects/algoTrading"
cd "$PROJECT_DIR"

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  QA BASELINE CHECK - algoTrading${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Count total Python files
TOTAL_FILES=$(find app -name "*.py" -type f | wc -l | tr -d ' ')
echo -e "Total Python files in app/: ${YELLOW}${TOTAL_FILES}${NC}"
echo ""

# 1. Black Formatting Check
echo -e "${GREEN}[1/5] Running Black formatting check...${NC}"
echo -e "Command: black --check app/"
echo "-------------------------------------------"
BLACK_OUTPUT=$(black --check app/ 2>&1 || true)
BLACK_REFORMAT=$(echo "$BLACK_OUTPUT" | grep "would reformat" | wc -l | tr -d ' ')
BLACK_ERROR=$(echo "$BLACK_OUTPUT" | grep "error: cannot format" | wc -l | tr -d ' ')
BLACK_OK=$(echo "$BLACK_OUTPUT" | grep "would be left unchanged" | wc -l | tr -d ' ')

echo -e "Files needing reformat: ${YELLOW}${BLACK_REFORMAT}${NC}"
echo -e "Files with errors: ${RED}${BLACK_ERROR}${NC}"
echo -e "Files already formatted: ${GREEN}${BLACK_OK}${NC}"

if [ $BLACK_ERROR -gt 0 ]; then
    echo -e "${RED}Files with parse errors:${NC}"
    echo "$BLACK_OUTPUT" | grep "error: cannot format"
fi
echo ""

# 2. isort Import Sorting Check
echo -e "${GREEN}[2/5] Running isort import sorting check...${NC}"
echo -e "Command: isort --check-only app/"
echo "-------------------------------------------"
ISORT_OUTPUT=$(isort --check-only app/ 2>&1 || true)
ISORT_ERRORS=$(echo "$ISORT_OUTPUT" | grep "ERROR:" | wc -l | tr -d ' ')

echo -e "Files with import issues: ${YELLOW}${ISORT_ERRORS}${NC}"
echo ""

# 3. mypy Type Checking
echo -e "${GREEN}[3/5] Running mypy type checking...${NC}"
echo -e "Command: mypy --strict app/"
echo "-------------------------------------------"
MYPY_OUTPUT=$(mypy --strict app/ 2>&1 || true)
MYPY_ERRORS=$(echo "$MYPY_OUTPUT" | grep "error:" | wc -l | tr -d ' ')

echo -e "Type checking errors: ${YELLOW}${MYPY_ERRORS}${NC}"
if [ $MYPY_ERRORS -gt 0 ]; then
    echo -e "${RED}First few errors:${NC}"
    echo "$MYPY_OUTPUT" | head -20
fi
echo ""

# 4. ruff Linting
echo -e "${GREEN}[4/5] Running ruff linter...${NC}"
echo -e "Command: ruff check app/"
echo "-------------------------------------------"
RUFF_OUTPUT=$(ruff check app/ 2>&1 || true)
RUFF_TOTAL=$(echo "$RUFF_OUTPUT" | tail -1 | grep -oE '[0-9]+ errors' | grep -oE '[0-9]+' || echo "0")
RUFF_FIXABLE=$(echo "$RUFF_OUTPUT" | grep "fixable" | grep -oE '[0-9]+ fixable' | grep -oE '[0-9]+' || echo "0")

echo -e "Total errors: ${YELLOW}${RUFF_TOTAL}${NC}"
echo -e "Fixable automatically: ${GREEN}${RUFF_FIXABLE}${NC}"

# Show error breakdown
echo -e "\nError breakdown:"
echo "$RUFF_OUTPUT" | grep -E "^[0-9]+\s+[A-Z][0-9]+" | head -10
echo ""

# 5. radon Complexity Analysis
echo -e "${GREEN}[5/5] Running radon complexity analysis...${NC}"
echo -e "Command: radon cc app/ -a -s"
echo "-------------------------------------------"
RADON_OUTPUT=$(radon cc app/ -a -s 2>&1 || true)
RADON_BLOCKS=$(echo "$RADON_OUTPUT" | grep "blocks analyzed" | grep -oE '[0-9]+' | head -1)
RADON_AVG=$(echo "$RADON_OUTPUT" | grep "Average complexity" | grep -oE 'A \([0-9.]+\)' || echo "")

echo -e "Blocks analyzed: ${GREEN}${RADON_BLOCKS}${NC}"
echo -e "Average complexity: ${YELLOW}${RADON_AVG}${NC}"

# Count complexity grades (saved output analysis)
if [ -f /tmp/radon_output.txt ]; then
    A_COUNT=$(grep -oE ' - A \(' /tmp/radon_output.txt | wc -l | tr -d ' ')
    B_COUNT=$(grep -oE ' - B \(' /tmp/radon_output.txt | wc -l | tr -d ' ')
    C_COUNT=$(grep -oE ' - C \(' /tmp/radon_output.txt | wc -l | tr -d ' ')
    D_COUNT=$(grep -oE ' - D \(' /tmp/radon_output.txt | wc -l | tr -d ' ')
    E_COUNT=$(grep -oE ' - E \(' /tmp/radon_output.txt | wc -l | tr -d ' ')
    F_COUNT=$(grep -oE ' - F \(' /tmp/radon_output.txt | wc -l | tr -d ' ')

    echo -e "\nComplexity distribution:"
    echo -e "  Grade A (Good):        ${GREEN}${A_COUNT}${NC}"
    echo -e "  Grade B (Warning):     ${YELLOW}${B_COUNT}${NC}"
    echo -e "  Grade C (Danger):      ${YELLOW}${C_COUNT}${NC}"
    echo -e "  Grade D (Extreme):     ${RED}${D_COUNT}${NC}"
    echo -e "  Grade E (Critical):    ${RED}${E_COUNT}${NC}"
    echo -e "  Grade F (Critical):    ${RED}${F_COUNT}${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  SUMMARY${NC}"
echo -e "${GREEN}========================================${NC}"

# Calculate health score
FORMATTING_SCORE=$(( (BLACK_OK + BLACK_OK) * 100 / TOTAL_FILES ))
echo -e "Formatting Health:     ${FORMATTING_SCORE}%"

if [ $BLACK_ERROR -gt 0 ]; then
    echo -e "Type Checking:         ${RED}BLOCKED${NC} (fix syntax errors first)"
else
    echo -e "Type Checking:         ${YELLOW}PENDING${NC}"
fi

echo -e ""
echo -e "Full report saved to: ${YELLOW}QA_BASELINE_REPORT.md${NC}"
echo -e ""

# Next steps
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "1. Fix syntax errors blocking type checking"
if [ $BLACK_ERROR -gt 0 ]; then
    echo -e "   - Check files listed above"
fi
echo -e "2. Run auto-fixers:"
echo -e "   ${GREEN}isort app/ --fix-only${NC}"
echo -e "   ${GREEN}black app/${NC}"
echo -e "   ${GREEN}ruff check app/ --fix${NC}"
echo -e "3. Manual fixes for remaining issues"
echo -e "4. Refactor complex functions (Grade D-F)"
echo ""
