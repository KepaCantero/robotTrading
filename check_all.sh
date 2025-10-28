#!/bin/bash
# ===========================================
# check_all.sh - Chequeo y corrección completa
# ===========================================
# Ejecuta todos los fixes posibles
# Solo chequea archivos de producción (app/) y tests/ 
# ===========================================

set -euo pipefail

APP_DIRS="app/ tests/"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # Sin color

section() {
    echo -e "\n${CYAN}==========================================="
    echo "  $1"
    echo "===========================================${NC}"
}

run_fix() {
    local name="$1"
    shift
    echo -e "${YELLOW}>>> Ejecutando: $name${NC}"
    if "$@" ; then
        echo -e "${GREEN}✔ $name completado${NC}"
    else
        echo -e "${RED}✖ $name terminó con errores${NC}"
    fi
}

# ============================================
section "FORMATEO Y ORDEN DE IMPORTS - FIX AUTOMÁTICO"
run_fix "Black" black $APP_DIRS
run_fix "Isort" isort $APP_DIRS
run_fix "Autoflake (elimina imports/vars sin usar)" autoflake --in-place --remove-unused-variables --remove-all-unused-imports -r $APP_DIRS
run_fix "Ruff --fix" ruff $APP_DIRS --fix

# ============================================
section "LINTING Y REPORTES"
run_fix "Flake8" flake8 $APP_DIRS --max-line-length=100 --statistics || true
run_fix "Pylint" pylint $APP_DIRS || true

# ============================================
section "TYPE CHECKING"
run_fix "Mypy" mypy $APP_DIRS || true

# ============================================
section "SECURITY CHECK"
run_fix "Bandit" bandit -r $APP_DIRS -ll || true

# ============================================
section "CHEQUEO Y FIX COMPLETO FINALIZADO"
echo -e "${GREEN}Todos los fixes posibles han sido aplicados.${NC}"
