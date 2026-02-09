#!/bin/bash
# =============================================================================
# Quality Check Script for Modified Files Only
# =============================================================================
# Runs quality checks (black, isort, ruff, flake8, mypy, pytest) only on
# files that have been modified (staged or unstaged).
#
# Usage:
#   ./scripts/check_modified.sh           # Check all modified files
#   ./scripts/check_modified.sh --staged  # Check only staged files
#   ./scripts/check_modified.sh --fix     # Auto-fix issues where possible
#   ./scripts/check_modified.sh --quick   # Skip mypy and pytest (faster)
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FIX_MODE=false
STAGED_ONLY=false
QUICK_MODE=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --staged)
            STAGED_ONLY=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --fix      Auto-fix issues where possible (black, isort, ruff)"
            echo "  --staged   Only check staged files (for pre-commit)"
            echo "  --quick    Skip mypy and pytest (faster checks)"
            echo "  --verbose  Show detailed output"
            echo "  --help     Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Get modified Python files
get_modified_files() {
    if [ "$STAGED_ONLY" = true ]; then
        # Only staged files
        git diff --cached --name-only --diff-filter=ACMR | grep '\.py$' || true
    else
        # Both staged and unstaged (modified + new files)
        {
            git diff --name-only --diff-filter=ACMR
            git diff --cached --name-only --diff-filter=ACMR
            git ls-files --others --exclude-standard
        } | grep '\.py$' | sort -u || true
    fi
}

# Filter out files in .venv, __pycache__, etc.
filter_files() {
    grep -v -E '^(\.venv|venv|__pycache__|\.pytest_cache|\.git|node_modules|\.mypy_cache)/' || true
}

# Print header
print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Print result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}  ✓ $2${NC}"
    else
        echo -e "${RED}  ✗ $2${NC}"
    fi
}

# Main script
main() {
    print_header "Quality Check - Modified Files Only"

    # Get files
    FILES=$(get_modified_files | filter_files)

    if [ -z "$FILES" ]; then
        echo -e "${YELLOW}No modified Python files to check.${NC}"
        exit 0
    fi

    # Count files
    FILE_COUNT=$(echo "$FILES" | wc -l | tr -d ' ')
    echo -e "${YELLOW}Found ${FILE_COUNT} modified Python file(s):${NC}"

    if [ "$VERBOSE" = true ]; then
        echo "$FILES" | while read -r f; do echo "  - $f"; done
    else
        echo "$FILES" | head -5 | while read -r f; do echo "  - $f"; done
        if [ "$FILE_COUNT" -gt 5 ]; then
            echo "  ... and $((FILE_COUNT - 5)) more"
        fi
    fi

    # Convert to space-separated list for tools
    FILES_LIST=$(echo "$FILES" | tr '\n' ' ')

    # Track failures
    FAILURES=0

    # -------------------------------------------------------------------------
    # 1. Black - Code Formatting
    # -------------------------------------------------------------------------
    print_header "1. Black (Code Formatting)"

    if [ "$FIX_MODE" = true ]; then
        if black --line-length 100 $FILES_LIST 2>/dev/null; then
            print_result 0 "Black formatting applied"
        else
            print_result 1 "Black formatting failed"
            ((FAILURES++))
        fi
    else
        if black --check --line-length 100 $FILES_LIST 2>/dev/null; then
            print_result 0 "Black check passed"
        else
            print_result 1 "Black check failed (run with --fix to auto-format)"
            ((FAILURES++))
        fi
    fi

    # -------------------------------------------------------------------------
    # 2. isort - Import Sorting
    # -------------------------------------------------------------------------
    print_header "2. isort (Import Sorting)"

    if [ "$FIX_MODE" = true ]; then
        if isort --profile black --line-length 100 $FILES_LIST 2>/dev/null; then
            print_result 0 "isort applied"
        else
            print_result 1 "isort failed"
            ((FAILURES++))
        fi
    else
        if isort --check-only --profile black --line-length 100 $FILES_LIST 2>/dev/null; then
            print_result 0 "isort check passed"
        else
            print_result 1 "isort check failed (run with --fix to auto-sort)"
            ((FAILURES++))
        fi
    fi

    # -------------------------------------------------------------------------
    # 3. Ruff - Fast Linter
    # -------------------------------------------------------------------------
    print_header "3. Ruff (Fast Linter)"

    if command -v ruff &> /dev/null; then
        if [ "$FIX_MODE" = true ]; then
            if ruff check --fix --line-length 100 $FILES_LIST 2>/dev/null; then
                print_result 0 "Ruff check passed (fixes applied)"
            else
                print_result 1 "Ruff found issues"
                ((FAILURES++))
            fi
        else
            if ruff check --line-length 100 $FILES_LIST 2>/dev/null; then
                print_result 0 "Ruff check passed"
            else
                print_result 1 "Ruff found issues (run with --fix to auto-fix)"
                ((FAILURES++))
            fi
        fi
    else
        echo -e "${YELLOW}  ⚠ Ruff not installed, skipping...${NC}"
    fi

    # -------------------------------------------------------------------------
    # 4. Flake8 - Style Guide
    # -------------------------------------------------------------------------
    print_header "4. Flake8 (Style Guide)"

    if flake8 --max-line-length=100 --extend-ignore=E203,W503 $FILES_LIST 2>/dev/null; then
        print_result 0 "Flake8 check passed"
    else
        print_result 1 "Flake8 found issues"
        ((FAILURES++))
    fi

    # -------------------------------------------------------------------------
    # 5. MyPy - Type Checking (skip in quick mode)
    # -------------------------------------------------------------------------
    if [ "$QUICK_MODE" = false ]; then
        print_header "5. MyPy (Type Checking)"

        if command -v mypy &> /dev/null; then
            if mypy --ignore-missing-imports --no-error-summary $FILES_LIST 2>/dev/null; then
                print_result 0 "MyPy check passed"
            else
                print_result 1 "MyPy found type issues"
                ((FAILURES++))
            fi
        else
            echo -e "${YELLOW}  ⚠ MyPy not installed, skipping...${NC}"
        fi
    fi

    # -------------------------------------------------------------------------
    # 6. Pytest - Related Tests (skip in quick mode)
    # -------------------------------------------------------------------------
    if [ "$QUICK_MODE" = false ]; then
        print_header "6. Pytest (Related Tests)"

        # Find test files for modified source files
        TEST_FILES=""
        for f in $FILES; do
            # If it's already a test file, include it
            if [[ "$f" == tests/* ]]; then
                TEST_FILES="$TEST_FILES $f"
            else
                # Try to find corresponding test file
                BASE=$(basename "$f" .py)
                POSSIBLE_TEST="tests/test_${BASE}.py"
                if [ -f "$POSSIBLE_TEST" ]; then
                    TEST_FILES="$TEST_FILES $POSSIBLE_TEST"
                fi
                # Also check in subdirectories
                POSSIBLE_TEST=$(find tests -name "test_${BASE}.py" 2>/dev/null | head -1)
                if [ -n "$POSSIBLE_TEST" ] && [ -f "$POSSIBLE_TEST" ]; then
                    TEST_FILES="$TEST_FILES $POSSIBLE_TEST"
                fi
            fi
        done

        TEST_FILES=$(echo "$TEST_FILES" | tr ' ' '\n' | sort -u | tr '\n' ' ')

        if [ -n "$TEST_FILES" ]; then
            echo -e "${YELLOW}  Running tests for: $(echo $TEST_FILES | wc -w | tr -d ' ') file(s)${NC}"
            if pytest $TEST_FILES --maxfail=3 -q 2>/dev/null; then
                print_result 0 "Related tests passed"
            else
                print_result 1 "Some tests failed"
                ((FAILURES++))
            fi
        else
            echo -e "${YELLOW}  ⚠ No related test files found${NC}"
        fi
    fi

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print_header "Summary"

    if [ $FAILURES -eq 0 ]; then
        echo -e "${GREEN}  ✓ All checks passed!${NC}"
        echo -e "${GREEN}  Ready to commit.${NC}"
        exit 0
    else
        echo -e "${RED}  ✗ ${FAILURES} check(s) failed.${NC}"
        echo -e "${YELLOW}  Fix issues before committing.${NC}"
        if [ "$FIX_MODE" = false ]; then
            echo -e "${YELLOW}  Tip: Run with --fix to auto-fix some issues.${NC}"
        fi
        exit 1
    fi
}

# Run main
main
