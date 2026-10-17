#!/bin/bash
# ===========================================
# check_all.sh - QA completo del código (solo lectura)
# ===========================================
# Es EL script de calidad del repo. Checks por defecto; no modifica nada.
#
# Uso:
#   ./scripts/check_all.sh              # todos los checks (reporte)
#   ./scripts/check_all.sh --core       # solo checks core (rápido)
#   ./scripts/check_all.sh --fix        # aplica fixes (ruff --fix + ruff format,
#                                       # lo mismo que pre-commit) y luego chequea
#   ./scripts/check_all.sh --strict     # corta en el primer fallo (para CI)
#
# Checks CORE (siempre, si la herramienta existe):
#   ruff check, ruff format, black --check, isort --check,
#   flake8, pylint (E,F), mypy, bandit
# Checks EXTRA (se omiten si la herramienta no está instalada):
#   radon cc/mi, vulture, semgrep, pip-audit, safety
#
# NO corre tests (usa `make test`) ni instala nada.
# ===========================================

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Virtual environment del proyecto (las herramientas viven ahí)
if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

APP_DIRS=(app/ tests/)

FIX_MODE=false
CORE_ONLY=false
STRICT_MODE=false
for arg in "$@"; do
    case $arg in
        --fix)   FIX_MODE=true ;;
        --core)  CORE_ONLY=true ;;
        --strict) STRICT_MODE=true ;;
        -h|--help) grep '^# ' "$0" | cut -c3-; exit 0 ;;
        *) echo "Opción desconocida: $arg (usa -h)"; exit 1 ;;
    esac
done

TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
SKIPPED_CHECKS=0

section() {
    echo -e "\n${CYAN}╔════════════════════════════════════════════════════════╗"
    echo -e "║  $1"
    echo -e "╚════════════════════════════════════════════════════════╝${NC}"
}

# run_check <nombre> <comando...>
run_check() {
    local name="$1"
    shift
    local cmd="${1%% *}"

    ((TOTAL_CHECKS++))

    if ! command -v "$cmd" &> /dev/null; then
        echo -e "${YELLOW}⚠ $name: $cmd no está instalado, omitiendo${NC}"
        ((SKIPPED_CHECKS++))
        return 0
    fi

    echo -e "${YELLOW}>>> $name${NC}"
    if "$@"; then
        echo -e "${GREEN}✓ $name${NC}"
        ((PASSED_CHECKS++))
    elif [ "$STRICT_MODE" = true ]; then
        echo -e "${RED}✗ $name falló (modo estricto)${NC}"
        ((FAILED_CHECKS++))
        exit 1
    else
        echo -e "${RED}✗ $name${NC}"
        ((FAILED_CHECKS++))
    fi
}

# ============================================
if [ "$FIX_MODE" = true ]; then
    section "FIXES (equivalente a pre-commit)"
    run_check "ruff check --fix" ruff check "${APP_DIRS[@]}" --fix
    run_check "ruff format" ruff format "${APP_DIRS[@]}"
fi

# ============================================
section "CORE - LINT Y FORMATO (solo lectura)"

run_check "ruff check" ruff check "${APP_DIRS[@]}"
run_check "ruff format --check" ruff format --check "${APP_DIRS[@]}"
# black e isort se retiraron: pelean circularmente con ruff format/I001
# (el formateo canónico del repo, impuesto por pre-commit y CI). Un formateador, una verdad.

# Excluye reglas cubiertas por ruff/black o aceptadas por el proyecto
run_check "flake8" flake8 "${APP_DIRS[@]}" --max-line-length=100 \
    --extend-ignore=B007,B008,B011,B014,B015,B017,B018,E203,E402,E501,SIM,C401,C403,C408,C414,C416,C420,W503

run_check "pylint (E,F)" pylint "${APP_DIRS[@]}" --recursive=y --disable=all --enable=E,F

# ============================================
section "CORE - TIPOS Y SEGURIDAD (solo lectura)"

run_check "mypy" mypy app/
run_check "bandit" bandit -r app/ -ll

if [ "$CORE_ONLY" = true ]; then
    section "CORE COMPLETADO"
    echo -e "Usa ./scripts/check_all.sh sin --core para los checks extra."
else
    # ============================================
    section "EXTRA - CALIDAD (se omiten si no están instaladas)"

    run_check "radon cc (complejidad)" radon cc "${APP_DIRS[@]}" --total-average
    run_check "radon mi (mantenibilidad)" radon mi "${APP_DIRS[@]}" -s

    if [ -f .vulture-whitelist.py ]; then
        run_check "vulture" vulture "${APP_DIRS[@]}" .vulture-whitelist.py --min-confidence 80
    else
        run_check "vulture" vulture "${APP_DIRS[@]}" --min-confidence 80
    fi

    run_check "semgrep" semgrep --config=auto "${APP_DIRS[@]}"
    run_check "pip-audit" pip-audit
    run_check "safety" safety check
fi

# ============================================
section "RESUMEN"

echo -e "Checks ejecutados: ${TOTAL_CHECKS}"
echo -e "${GREEN}Pasaron: ${PASSED_CHECKS}${NC}"
echo -e "${RED}Fallaron: ${FAILED_CHECKS}${NC}"
echo -e "${YELLOW}Omitidos (no instalados): ${SKIPPED_CHECKS}${NC}"

if [ "$FAILED_CHECKS" -eq 0 ]; then
    echo -e "\n${GREEN}✅ TODOS LOS CHECKS PASARON${NC}"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  ALGUNOS CHECKS FALLARON${NC}"
    exit 1
fi
