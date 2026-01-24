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

APP_DIRS="app/ tests/"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # Sin color

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
    command -v "$1" &> /dev/null
}

# ============================================
# SECCIÓN 1: FORMATEO Y ORDEN (FIX AUTOMÁTICO)
# ============================================
section "✅ OBLIGATORIAS - FORMATEO Y ORDEN"

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

subsection "Flake8 - Linter clásico (PEP8, errores lógicos, complejidad)"
run_check "Flake8" flake8 $APP_DIRS --max-line-length=100 --statistics

subsection "Ruff check - Linter ultra-rápido (10-100x más rápido)"
run_check "Ruff" ruff check $APP_DIRS

# ============================================
# SECCIÓN 3: ANÁLISIS PROFUNDO (CORE)
# ============================================
section "✅ OBLIGATORIAS - ANÁLISIS PROFUNDO"

subsection "Pylint - Análisis estático exhaustivo"
run_check "Pylint" pylint $APP_DIRS --recursive=y

# ============================================
# SECCIÓN 4: TYPE CHECKING (CORE)
# ============================================
section "✅ OBLIGATORIAS - TYPE CHECKING"

subsection "Mypy - Type checker"
run_check "Mypy" mypy $APP_DIRS

# ============================================
# SECCIÓN 5: SEGURIDAD (CORE)
# ============================================
section "✅ OBLIGATORIAS - SEGURIDAD"

subsection "Bandit - Security scanner (SQL injection, hardcoded passwords, weak crypto)"
run_check "Bandit" bandit -r $APP_DIRS -ll

if [ "$CORE_ONLY" = true ]; then
    section "CORE CHECKS COMPLETADOS"
    exit 0
fi

# ============================================
# SECCIÓN 6: TESTING (RECOMENDADO)
# ============================================
section "🔶 RECOMENDADAS - TESTING"

subsection "Pytest - Framework de testing"
run_check "Pytest" pytest tests/ -v --tb=short -x

subsection "Coverage.py - Cobertura de tests"
if command_exists coverage; then
    run_check "Coverage Report" coverage report --fail-under=70 || true
    echo -e "${CYAN}Generando reporte HTML de cobertura...${NC}"
    coverage html --fail-under=70 || true
    echo -e "${GREEN}Reporte HTML generado en: htmlcov/index.html${NC}"
else
    run_check "Pytest Coverage" pytest tests/ --cov=app --cov-report=html --cov-report=term || true
fi

# ============================================
# SECCIÓN 7: CALIDAD DE CÓDIGO (RECOMENDADO)
# ============================================
section "🔶 RECOMENDADAS - CALIDAD DE CÓDIGO"

subsection "Radon - Complejidad ciclomática (CC < 10 recomendado)"
if command_exists radon; then
    run_check "Radon CC" radon cc $APP_DIRS -a --total-average || true
    echo -e "${CYAN}CC > 10 requiere refactorización${NC}"
fi

subsection "Radon MI - Maintainability Index (MI > 65 recomendado)"
if command_exists radon; then
    run_check "Radon MI" radon mi $APP_DIRS --show || true
    echo -e "${CYAN}MI < 20 es crítico, MI > 65 es aceptable${NC}"
fi

subsection "Vulture - Código muerto (detecta código no usado)"
if command_exists vulture; then
    run_check "Vulture" vulture $APP_DIRS --min-confidence 80 || true
fi

# ============================================
# SECCIÓN 8: DOCUMENTACIÓN (RECOMENDADO)
# ============================================
section "🔶 RECOMENDADAS - DOCUMENTACIÓN"

subsection "Pydocstyle - Valida formato de docstrings (convención Google)"
if command_exists pydocstyle; then
    run_check "Pydocstyle" pydocstyle $APP_DIRS --convention=google || true
fi

subsection "Interrogate - Cobertura de documentación (>70% recomendado)"
if command_exists interrogate; then
    run_check "Interrogate" interrogate $APP_DIRS -v --fail-under=70 || true
fi

# ============================================
# SECCIÓN 9: SEGURIDAD DE DEPENDENCIAS (RECOMENDADO)
# ============================================
section "🔶 RECOMENDADAS - SEGURIDAD DE DEPENDENCIAS"

subsection "Safety - Escanea dependencias por CVEs conocidos"
if command_exists safety; then
    run_check "Safety" safety check || true
fi

subsection "Pip-audit - Auditoría de dependencias (PyPI Advisory Database)"
if command_exists pip-audit; then
    run_check "Pip-audit" pip-audit || true
fi

# ============================================
# SECCIÓN 10: PATTERN MATCHING AVANZADO (RECOMENDADO)
# ============================================
section "🔶 RECOMENDADAS - PATTERN MATCHING"

subsection "Semgrep - Detecta anti-patterns, bugs, security issues"
if command_exists semgrep; then
    run_check "Semgrep" semgrep --config=auto $APP_DIRS || true
fi

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
