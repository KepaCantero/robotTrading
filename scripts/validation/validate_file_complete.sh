#!/bin/bash
# Validación COMPLETA de un solo archivo - Compatible con bash 3.x
# Uso: scripts/validate_file_complete.sh <archivo>

FILE="$1"

if [ ! -f "$FILE" ]; then
    echo '{"success": false, "error": "File not found"}'
    exit 1
fi

# Usar .venv/bin/ herramientas
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo '{"success": false, "error": ".venv not found"}'
    exit 1
fi

BLACK="$VENV_DIR/bin/black"
ISORT="$VENV_DIR/bin/isort"
RUFF="$VENV_DIR/bin/ruff"
FLAKE8="$VENV_DIR/bin/flake8"
PYLINT="$VENV_DIR/bin/pylint"
MYPY="$VENV_DIR/bin/mypy"
BANDIT="$VENV_DIR/bin/bandit"
RADON="$VENV_DIR/bin/radon"

# Verificar que todas las herramientas existan
MISSING=""
for tool in "$BLACK" "$ISORT" "$RUFF" "$FLAKE8" "$PYLINT" "$MYPY" "$BANDIT" "$RADON"; do
    [ ! -f "$tool" ] && MISSING="$MISSING $tool"
done
if [ -n "$MISSING" ]; then
    echo "{\"success\": false, \"error\": \"Tools not found:$MISSING\"}"
    exit 1
fi

# Ejecutar checks y capturar resultados
TOTAL=0
PASSED=0
FAILED=0

# Black
if "$BLACK" --check "$FILE" >/dev/null 2>&1; then
    BLACK_STATUS="\"status\": \"passed\""
    PASSED=$((PASSED + 1))
else
    BLACK_STATUS="\"status\": \"failed\""
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))

# Isort
if "$ISORT" --check-only "$FILE" >/dev/null 2>&1; then
    ISORT_STATUS="\"status\": \"passed\""
    PASSED=$((PASSED + 1))
else
    ISORT_STATUS="\"status\": \"failed\""
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))

# Ruff
if "$RUFF" check "$FILE" >/dev/null 2>&1; then
    RUFF_STATUS="\"status\": \"passed\""
    PASSED=$((PASSED + 1))
else
    RUFF_STATUS="\"status\": \"failed\""
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))

# Flake8
if "$FLAKE8" "$FILE" --max-line-length=100 --extend-ignore=E203,E402,E501,W503,B007,B008,B011,B014,B015,B017,B018,B024,SIM,C401,C403,C408,C414,C416,C420 >/dev/null 2>&1; then
    FLAKE8_STATUS="\"status\": \"passed\""
    PASSED=$((PASSED + 1))
else
    FLAKE8_STATUS="\"status\": \"failed\""
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))

# Pylint
if "$PYLINT" "$FILE" --output-format=json >/dev/null 2>&1; then
    PYLINT_STATUS="\"status\": \"passed\""
    PASSED=$((PASSED + 1))
else
    PYLINT_STATUS="\"status\": \"failed\""
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))

# Mypy - SOLO validar el archivo actual, no imports
if "$MYPY" --no-incremental --follow-imports=skip "$FILE" >/dev/null 2>&1; then
    MYPY_STATUS="\"status\": \"passed\""
    PASSED=$((PASSED + 1))
else
    MYPY_STATUS="\"status\": \"failed\""
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))

# Bandit
if "$BANDIT" "$FILE" -ll -f json >/dev/null 2>&1; then
    BANDIT_STATUS="\"status\": \"passed\""
    PASSED=$((PASSED + 1))
else
    BANDIT_STATUS="\"status\": \"failed\""
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))

# Radon - Extract numeric CC from "Average complexity: A (1.0)" format
RADON_OUTPUT=$("$RADON" cc "$FILE" -a -s 2>/dev/null)
# Get average complexity line and extract number from parentheses
CC=$(echo "$RADON_OUTPUT" | grep "Average complexity" | sed 's/.*(\([0-9.]*\)).*/\1/' 2>/dev/null || echo "0")
# Fallback: if no average line, get the last numeric value from output
if [ "$CC" == "0" ] || [ -z "$CC" ]; then
    CC=$(echo "$RADON_OUTPUT" | grep -oE '\([0-9.]+\)' | tail -1 | tr -d '()' 2>/dev/null || echo "0")
fi
# Ensure CC is a number
if ! echo "$CC" | grep -qE '^[0-9.]+$'; then
    CC="0"
fi
TOTAL=$((TOTAL + 1))
# Use bc for floating point comparison, or integer if no decimal
CC_INT=$(echo "$CC" | cut -d. -f1)
if [ "$CC_INT" -lt 10 ] 2>/dev/null || [ "$CC" == "0" ]; then
    RADON_STATUS="\"status\": \"passed\", \"cc\": $CC"
    PASSED=$((PASSED + 1))
else
    RADON_STATUS="\"status\": \"failed\", \"cc\": $CC"
    FAILED=$((FAILED + 1))
fi

# Success flag
if [ $FAILED -eq 0 ]; then
    SUCCESS="true"
else
    SUCCESS="false"
fi

# Escribir JSON completo (siempre)
cat <<EOF
{
  "file": "$FILE",
  "checks": {
    "black": {$BLACK_STATUS},
    "isort": {$ISORT_STATUS},
    "ruff": {$RUFF_STATUS},
    "flake8": {$FLAKE8_STATUS},
    "pylint": {$PYLINT_STATUS},
    "mypy": {$MYPY_STATUS},
    "bandit": {$BANDIT_STATUS},
    "radon": {$RADON_STATUS}
  },
  "summary": {
    "total_checks": $TOTAL,
    "passed": $PASSED,
    "failed": $FAILED,
    "success": $SUCCESS
  }
}
EOF

# Exit code DESPUÉS de escribir JSON
[ $FAILED -eq 0 ]
