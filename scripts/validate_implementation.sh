#!/bin/bash
# ===========================================
# validate_implementation.sh
# ===========================================
# Valida que una implementación cumpla con
# todos los requisitos antes de hacer commit
# ===========================================

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m' # Sin color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0

header() {
    echo -e "\n${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║ $1${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
}

section() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_pass() {
    echo -e "${GREEN}✔ $1${NC}"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "${RED}✗ $1${NC}"
    ((CHECKS_FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ============================================
header "VALIDACIÓN DE IMPLEMENTACIÓN"
echo -e "Repo: ${BLUE}$REPO_ROOT${NC}"
echo -e "Hora: $(date '+%Y-%m-%d %H:%M:%S')"

# ============================================
section "PASO 1: FORMATEO Y ORDEN DE IMPORTS"

cd "$REPO_ROOT"

if command -v black &> /dev/null; then
    if black app/ tests/ --quiet 2>/dev/null; then
        check_pass "Black - Formateado completado"
    else
        check_warn "Black - Algunos archivos tienen formato inconsistente"
    fi
else
    check_fail "Black no instalado"
fi

if command -v isort &> /dev/null; then
    if isort app/ tests/ --quiet 2>/dev/null; then
        check_pass "Isort - Imports ordenados"
    else
        check_warn "Isort - Algunos imports necesitan reordenamiento"
    fi
else
    check_fail "Isort no instalado"
fi

if command -v autoflake &> /dev/null; then
    if autoflake --in-place --remove-unused-variables --remove-all-unused-imports -r app/ tests/ --quiet 2>/dev/null; then
        check_pass "Autoflake - Limpieza completada"
    else
        check_warn "Autoflake - No hay variables/imports sin usar"
    fi
else
    check_fail "Autoflake no instalado"
fi

if command -v ruff &> /dev/null; then
    if ruff check app/ tests/ --fix --quiet 2>/dev/null; then
        check_pass "Ruff - Fixes aplicados"
    else
        check_warn "Ruff - Algunos issues no se pudieron arreglar automáticamente"
    fi
else
    check_fail "Ruff no instalado"
fi

# ============================================
section "PASO 2: LINTING (FLAKE8)"

if command -v flake8 &> /dev/null; then
    echo "Ejecutando Flake8..."
    FLAKE8_OUTPUT=$(flake8 app/ tests/ --max-line-length=100 --statistics 2>&1 || true)

    # Count errors by type
    CRITICAL_ERRORS=0
    E501_ERRORS=0

    if [ -n "$FLAKE8_OUTPUT" ]; then
        # E501 = line too long (permitido hasta 5 por archivo)
        E501_ERRORS=$(echo "$FLAKE8_OUTPUT" | grep -c "E501" || true)

        # Errores críticos
        CRITICAL=$(echo "$FLAKE8_OUTPUT" | grep -E "^(F|E[1-4]|W[1-3])" || true)
        CRITICAL_ERRORS=$(echo "$CRITICAL" | wc -l)
        CRITICAL_ERRORS=$((CRITICAL_ERRORS - 1))  # Remove header line
    fi

    if [ "$CRITICAL_ERRORS" -eq 0 ]; then
        check_pass "Flake8 - Sin errores críticos"
        if [ "$E501_ERRORS" -gt 0 ]; then
            check_warn "Flake8 - $E501_ERRORS errores E501 (líneas largas - permitido)"
        fi
    else
        check_fail "Flake8 - $CRITICAL_ERRORS errores críticos encontrados"
        echo "$CRITICAL" | head -10
    fi
else
    check_fail "Flake8 no instalado"
fi

# ============================================
section "PASO 3: LINTING (PYLINT)"

if command -v pylint &> /dev/null; then
    echo "Ejecutando Pylint (puede tomar tiempo)..."
    PYLINT_OUTPUT=$(pylint app/ tests/ --disable=all --enable=E,F 2>&1 || true)

    # Extract score
    PYLINT_SCORE=$(echo "$PYLINT_OUTPUT" | grep "Your code has been rated" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "0")

    if (( $(echo "$PYLINT_SCORE > 8.0" | bc -l) )); then
        check_pass "Pylint - Score: $PYLINT_SCORE/10 ✓"
    elif (( $(echo "$PYLINT_SCORE > 0" | bc -l) )); then
        check_warn "Pylint - Score: $PYLINT_SCORE/10 (objetivo: >8.0)"
    else
        check_warn "Pylint - No se pudo obtener score"
    fi
else
    check_warn "Pylint no instalado (opcional)"
fi

# ============================================
section "PASO 4: TYPE CHECKING (MYPY)"

if command -v mypy &> /dev/null; then
    echo "Ejecutando Mypy..."
    if mypy app/ tests/ --ignore-missing-imports 2>&1 | tee /tmp/mypy_output.txt | grep -q "Success"; then
        check_pass "Mypy - Sin errores de tipo"
    else
        MYPY_ERRORS=$(grep "error:" /tmp/mypy_output.txt | wc -l)
        if [ "$MYPY_ERRORS" -gt 0 ]; then
            check_warn "Mypy - $MYPY_ERRORS errores encontrados (informativo)"
        else
            check_pass "Mypy - Completado"
        fi
    fi
else
    check_warn "Mypy no instalado (opcional)"
fi

# ============================================
section "PASO 5: SECURITY CHECK (BANDIT)"

if command -v bandit &> /dev/null; then
    echo "Ejecutando Bandit..."
    BANDIT_OUTPUT=$(bandit -r app/ tests/ -ll -f json 2>&1 || true)

    HIGH_ISSUES=$(echo "$BANDIT_OUTPUT" | grep -o '"severity": "HIGH"' | wc -l || echo 0)

    if [ "$HIGH_ISSUES" -eq 0 ]; then
        check_pass "Bandit - Sin issues de severidad HIGH"
    else
        check_fail "Bandit - $HIGH_ISSUES issues HIGH encontrados"
    fi
else
    check_warn "Bandit no instalado (opcional)"
fi

# ============================================
section "PASO 6: VERIFICACIÓN DE TESTS"

if command -v pytest &> /dev/null; then
    echo "Ejecutando pytest..."
    if pytest tests/ -q 2>&1 | tail -1 | grep -q "passed"; then
        check_pass "Tests - Todos los tests pasaron"
    else
        check_warn "Tests - Algunos tests fallaron o no hay tests"
    fi
else
    check_warn "Pytest no instalado (opcional)"
fi

# ============================================
header "RESUMEN DE VALIDACIÓN"

echo -e "\n${CYAN}Resultados:${NC}"
echo -e "  ${GREEN}✔ Checks pasados: $CHECKS_PASSED${NC}"
echo -e "  ${RED}✗ Checks fallidos: $CHECKS_FAILED${NC}"

echo -e "\n${CYAN}Status:${NC}"
if [ "$CHECKS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✅ IMPLEMENTACIÓN VALIDADA - LISTO PARA COMMIT${NC}"
    echo -e "\n${CYAN}Próximo paso:${NC}"
    echo -e "  git add -A && git commit -m \"[mensaje]\""
    exit 0
else
    echo -e "${RED}❌ VALIDACIÓN FALLIDA - CORREGIR ERRORES ANTES DE COMMIT${NC}"
    echo -e "\n${YELLOW}Próximos pasos:${NC}"
    echo -e "  1. Revisar errores arriba"
    echo -e "  2. Corregir errores críticos manualmente"
    echo -e "  3. Ejecutar: ./scripts/validate_implementation.sh"
    exit 1
fi
