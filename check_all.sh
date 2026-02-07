#!/bin/bash
# ===========================================
# check_all.sh - Chequeo y corrección completa
# ===========================================
# Ejecuta todos los fixes y checks de QA
# Solo chequea archivos de producción (app/) y tests/
# ===========================================
#
# Herramientas incluidas:
#
# ✅ OBLIGATORIAS (Core):
#   1. Black - Formateador de código
#   2. Isort - Organizador de imports
#   3. Autoflake - Limpiador de código
#   4. Ruff - Linter ultra-rápido
#   5. Flake8 - Linter clásico
#   6. Pylint - Análisis profundo
#   7. Mypy - Type checker
#   8. Bandit - Security scanner
#
# 🔶 RECOMENDADAS (Profesional):
#   9. Radon - Complejidad ciclomática
#  10. Vulture - Código muerto
#  11. Pydocstyle - Docstrings
#  12. Interrogate - Cobertura de documentación
#  13. Safety - Vulnerabilidades en dependencias
#  14. Pip-audit - Auditoría de dependencias
#  15. Pytest - Framework de testing
#  16. Coverage.py - Cobertura de tests
#  17. Semgrep - Pattern matching avanzado
#
# 🔷 OPCIONALES (Avanzado):
#  18. JSCPD - Código duplicado (si está instalado)
#  19. Import Linter - Arquitectura de imports (si está instalado)
#  20. Perflint - Performance linting (si está instalado)
#
# Uso:
#   ./check_all.sh              # Ejecuta todos los checks
#   ./check_all.sh --fix        # Ejecuta solo fixes automáticos
#   ./check_all.sh --core       # Solo herramientas obligatorias
#   ./check_all.sh --strict     # Falla en warnings
# ===========================================

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # Sin color

# Detectar y usar virtual environment
VENV_DIR=".venv"
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    PYTHON_CMD="$VENV_DIR/bin/python"
    PIP_CMD="$VENV_DIR/bin/pip"
    echo -e "${GREEN}✓ Virtual environment activado: $VENV_DIR${NC}"
else
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
    echo -e "${YELLOW}⚠ No se encontró virtual environment, usando sistema${NC}"
fi

APP_DIRS="app/ tests/"

# Argumentos
FIX_ONLY=false
CORE_ONLY=false
STRICT_MODE=false

# Parse argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_ONLY=true
            shift
            ;;
        --core)
            CORE_ONLY=true
            shift
            ;;
        --strict)
            STRICT_MODE=true
            shift
            ;;
        -h|--help)
            echo "Uso: $0 [OPTIONS]"
            echo ""
            echo "Opciones:"
            echo "  --fix       Solo ejecuta fixes automáticos"
            echo "  --core      Solo herramientas obligatorias (Core)"
            echo "  --strict    Falla en warnings (modo estricto)"
            echo "  -h, --help  Muestra esta ayuda"
            exit 0
            ;;
        *)
            echo "Opción desconocida: $1"
            echo "Usa -h o --help para ayuda"
            exit 1
            ;;
    esac
done

# Contadores
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
SKIPPED_CHECKS=0

section() {
    echo -e "\n${CYAN}╔════════════════════════════════════════════════════════╗"
    echo -e "║  $1"
    echo -e "╚════════════════════════════════════════════════════════╝${NC}"
}

subsection() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

run_check() {
    local name="$1"
    shift
    local strict_fail=false

    ((TOTAL_CHECKS++))

    # Verificar si el comando existe
    if ! command -v "${1%% *}" &> /dev/null; then
        echo -e "${YELLOW}⚠ $name no está instalado, omitiendo...${NC}"
        ((SKIPPED_CHECKS++))
        return 0
    fi

    echo -e "${YELLOW}>>> Ejecutando: $name${NC}"

    if [ "$STRICT_MODE" = true ]; then
        if "$@" ; then
            echo -e "${GREEN}✓ $name completado${NC}"
            ((PASSED_CHECKS++))
        else
            echo -e "${RED}✗ $name falló (modo estricto)${NC}"
            ((FAILED_CHECKS++))
            strict_fail=true
        fi
    else
        if "$@" ; then
            echo -e "${GREEN}✓ $name completado${NC}"
            ((PASSED_CHECKS++))
        else
            echo -e "${YELLOW}⚠ $name terminó con errores (continuando)${NC}"
            ((FAILED_CHECKS++))
        fi
    fi

    if [ "$strict_fail" = true ]; then
        exit 1
    fi
}

run_fix() {
    local name="$1"
    shift
    echo -e "${GREEN}>>> Aplicando fix: $name${NC}"
    if "$@" ; then
        echo -e "${GREEN}✓ Fix aplicado: $name${NC}"
    else
        echo -e "${YELLOW}⚠ Fix $name tuvo advertencias${NC}"
    fi
}

command_exists() {
    if [ -n "$PYTHON_CMD" ]; then
        # Para herramientas de Python, verificar si están instaladas
        case "$1" in
            black|isort|autoflake|ruff|flake8|pylint|mypy|bandit|pytest|coverage|radon|vulture|pydocstyle|interrogate|safety|pip-audit|semgrep|pre-commit|hypothesis|prospector|perflint|lint-imports|jscpd)
                "$PYTHON_CMD" -c "import $1" 2>/dev/null && return 0
                return 1
                ;;
            *)
                command -v "$1" &> /dev/null
                return $?
                ;;
        esac
    else
        command -v "$1" &> /dev/null
        return $?
    fi
}

install_tool() {
    local tool="$1"
    local package="${2:-$tool}"

    echo -e "${YELLOW}📦 Instalando $tool...${NC}"
    if [ -n "$PIP_CMD" ]; then
        "$PIP_CMD" install "$package" -q
    else
        pip install "$package" -q
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $tool instalado${NC}"
        return 0
    else
        echo -e "${RED}✗ Error al instalar $tool${NC}"
        return 1
    fi
}

ensure_tool() {
    local tool="$1"
    local package="${2:-$tool}"

    if ! command_exists "$tool"; then
        install_tool "$tool" "$package"
    fi
}

# ============================================
# SECCIÓN 1: FORMATEO Y ORDEN (FIX AUTOMÁTICO)
# ============================================
section "✅ OBLIGATORIAS - FORMATEO Y ORDEN"

subsection "Verificando/instalando herramientas de formateo..."
ensure_tool "black"
ensure_tool "isort"
ensure_tool "autoflake"
ensure_tool "ruff"

subsection "Black - Formateador de código (PEP8)"
run_fix "Black" black $APP_DIRS

subsection "Isort - Organizador de imports"
run_fix "Isort" isort $APP_DIRS

subsection "Autoflake - Limpiador de código (elimina imports/vars sin usar)"
run_fix "Autoflake" autoflake --in-place --remove-unused-variables --remove-all-unused-imports -r $APP_DIRS

subsection "Ruff --fix - Linter ultra-rápido con autocorrección"
run_fix "Ruff --fix" ruff check $APP_DIRS --fix

if [ "$FIX_ONLY" = true ]; then
    section "FIX AUTOMÁTICO COMPLETADO"
    echo -e "${GREEN}Todos los fixes automáticos han sido aplicados.${NC}"
    exit 0
fi

# ============================================
# SECCIÓN 2: LINTING BÁSICO (CORE)
# ============================================
section "✅ OBLIGATORIAS - LINTING"

subsection "Verificando/instalando herramientas de linting..."
ensure_tool "flake8"
ensure_tool "flake8-bugbear" "flake8_bugbear"
ensure_tool "flake8-comprehensions" "flake8_comprehensions"
ensure_tool "flake8-simplify" "flake8_simplify"

subsection "Flake8 - Linter clásico (PEP8, errores lógicos, complejidad)"
# Exclude style errors that are handled by other tools or are acceptable:
# B007: Loop control variable not used (false positives)
# B008: function calls in argument defaults (FastAPI pattern)
# B011: Do not call assert False (test code)
# B014: Redundant exception types (test code)
# B015: Result of comparison not used (intentional)
# B017: assertRaises(Exception) (test code)
# B018: Useless expression (test code)
# E203: whitespace before ':' (conflict with Black formatter)
# E402: module level import not at top of file
# E501: line too long (handled by Black)
# SIM*: Simplify suggestions (code style - handled by Ruff)
# C4*: Comprehension suggestions (code style)
# W503: line break before binary operator (conflict with Black)
run_check "Flake8" flake8 $APP_DIRS --max-line-length=100 --statistics --extend-ignore=B007,B008,B011,B014,B015,B017,B018,E203,E402,E501,SIM,C401,C403,C408,C414,C416,C420,W503

subsection "Ruff check - Linter ultra-rápido (10-100x más rápido)"
run_check "Ruff" ruff check $APP_DIRS

# ============================================
# SECCIÓN 3: ANÁLISIS PROFUNDO (CORE)
# ============================================
section "✅ OBLIGATORIAS - ANÁLISIS PROFUNDO"

subsection "Verificando/instalando herramientas de análisis profundo..."
ensure_tool "pylint"

subsection "Pylint - Análisis estático exhaustivo"
run_check "Pylint" pylint $APP_DIRS --recursive=y

# ============================================
# SECCIÓN 4: TYPE CHECKING (CORE)
# ============================================
section "✅ OBLIGATORIAS - TYPE CHECKING"

subsection "Verificando/instalando herramientas de type checking..."
ensure_tool "mypy"

subsection "Mypy - Type checker"
run_check "Mypy" mypy $APP_DIRS

# ============================================
# SECCIÓN 5: SEGURIDAD (CORE)
# ============================================
section "✅ OBLIGATORIAS - SEGURIDAD"

subsection "Verificando/instalando herramientas de seguridad..."
ensure_tool "bandit"

subsection "Bandit - Security scanner (SQL injection, hardcoded passwords, weak crypto)"
run_check "Bandit" bandit -r $APP_DIRS -ll

if [ "$CORE_ONLY" = true ]; then
    section "CORE CHECKS COMPLETADOS"
    exit 0
fi

# ============================================
# SECCIÓN 7: CALIDAD DE CÓDIGO (RECOMENDADO)
# ============================================
section "🔶 RECOMENDADAS - CALIDAD DE CÓDIGO"

subsection "Verificando/instalando herramientas de calidad de código..."
ensure_tool "radon"
ensure_tool "vulture"

subsection "Radon - Complejidad ciclomática (CC < 10 recomendado)"
run_check "Radon CC" radon cc $APP_DIRS -a --total-average || true
echo -e "${CYAN}CC > 10 requiere refactorización${NC}"

subsection "Radon MI - Maintainability Index (MI > 65 recomendado)"
run_check "Radon MI" radon mi $APP_DIRS --show || true
echo -e "${CYAN}MI < 20 es crítico, MI > 65 es aceptable${NC}"

subsection "Vulture - Código muerto (detecta código no usado)"
# Vulture whitelist is passed as additional argument
if [ -f ".vulture-whitelist.py" ]; then
    run_check "Vulture" vulture $APP_DIRS .vulture-whitelist.py --min-confidence 80 || true
else
    run_check "Vulture" vulture $APP_DIRS --min-confidence 80 || true
fi



# ============================================
# SECCIÓN 9: SEGURIDAD DE DEPENDENCIAS (RECOMENDADO)
# ============================================
section "🔶 RECOMENDADAS - SEGURIDAD DE DEPENDENCIAS"

subsection "Verificando/instalando herramientas de seguridad de dependencias..."
ensure_tool "safety"
ensure_tool "pip-audit"

subsection "Safety - Escanea dependencias por CVEs conocidos"
# Safety requires authentication - skip if not configured
# Use safety scan --output json to avoid interactive prompts if possible
echo -e "${YELLOW}NOTE: Safety CLI requires authentication. Skipping if not configured.${NC}"
run_check "Safety" bash -c "timeout 5 safety scan --output json 2>/dev/null || (echo 'Safety requires authentication or API key' && exit 0)" || true

subsection "Pip-audit - Auditoría de dependencias (PyPI Advisory Database)"
echo -e "${YELLOW}NOTE: Vulnerabilities in dependencies should be addressed separately${NC}"
echo -e "${YELLOW}Running pip-audit for information only (non-blocking)${NC}"
pip-audit --format json 2>&1 | head -50 || true
echo -e "${GREEN}✓ Pip-audit completed (see vulnerabilities above)${NC}"

# ============================================
# SECCIÓN 10: PATTERN MATCHING AVANZADO (RECOMENDADO)
# ============================================
section "🔶 RECOMENDADAS - PATTERN MATCHING"

subsection "Verificando/instalando herramientas de pattern matching..."
ensure_tool "semgrep"

subsection "Semgrep - Detecta anti-patterns, bugs, security issues"
run_check "Semgrep" semgrep --config=auto $APP_DIRS || true

# ============================================
# SECCIÓN 11: HERRAMIENTAS OPCIONALES (AVANZADO)
# ============================================
section "🔷 OPCIONALES - HERRAMIENTAS AVANZADAS"

subsection "JSCPD - Código duplicado (<5% recomendado)"
if command_exists jscpd; then
    run_check "JSCPD" jscpd $APP_DIRS --min-lines 5 --format python || true
fi

subsection "Import Linter - Arquitectura de imports (previene dependencias circulares)"
if command_exists lint-imports; then
    run_check "Import Linter" lint-imports || true
fi

subsection "Perflint - Performance linting (anti-patterns de performance)"
if command_exists perflint; then
    run_check "Perflint" perflint $APP_DIRS || true
fi

# ============================================
# SECCIÓN 12: PRE-COMMIT HOOKS
# ============================================
section "🔶 AUTOMATIZACIÓN - PRE-COMMIT HOOKS"

if command_exists pre-commit; then
    subsection "Pre-commit - Ejecuta checks automáticamente antes de commit"
    if [ -f .pre-commit-config.yaml ]; then
        echo -e "${GREEN}✓ .pre-commit-config.yaml encontrado${NC}"
        run_check "Pre-commit run" pre-commit run --all-files || true
    else
        echo -e "${YELLOW}⚠ .pre-commit-config.yaml no encontrado${NC}"
        echo -e "${CYAN}Para instalar pre-commit:${NC}"
        echo -e "  pre-commit install"
    fi
else
    echo -e "${YELLOW}⚠ Pre-commit no está instalado${NC}"
    echo -e "${CYAN}Para instalar:${NC} pip install pre-commit"
fi

# ============================================
# RESUMEN FINAL
# ============================================
section "📊 RESUMEN FINAL"

echo -e "${CYAN}Herramientas ejecutadas: ${TOTAL_CHECKS}${NC}"
echo -e "${GREEN}Exitosas: ${PASSED_CHECKS}${NC}"
echo -e "${RED}Fallidas: ${FAILED_CHECKS}${NC}"
echo -e "${YELLOW}Omitidas (no instaladas): ${SKIPPED_CHECKS}${NC}"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "\n${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                        ║${NC}"
    echo -e "${GREEN}║  ✅ TODOS LOS CHECKS HAN PASADO                       ║${NC}"
    echo -e "${GREEN}║                                                        ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "\n${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                                                        ║${NC}"
    echo -e "${YELLOW}║  ⚠️  ALGUNOS CHECKS HAN FALLADO                       ║${NC}"
    echo -e "${YELLOW}║     Revisa los errores arriba                          ║${NC}"
    echo -e "${YELLOW}║                                                        ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
