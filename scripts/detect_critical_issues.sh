#!/bin/bash
# ===========================================
# detect_critical_issues.sh
# ===========================================
# Detección de los 10 problemas críticos
# identificados en CRITICAL_ISSUES_ACTION_PLAN.md
# ===========================================

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Counters
ISSUES_FOUND=0
ISSUES_CRITICAL=0
ISSUES_HIGH=0
ISSUES_MEDIUM=0

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

issue_critical() {
    echo -e "${RED}🔴 CRÍTICA #$1: $2${NC}"
    echo -e "   📍 $(echo "$3" | head -1)"
    ((ISSUES_FOUND++))
    ((ISSUES_CRITICAL++))
}

issue_high() {
    echo -e "${YELLOW}🟠 ALTA #$1: $2${NC}"
    echo -e "   📍 $(echo "$3" | head -1)"
    ((ISSUES_FOUND++))
    ((ISSUES_HIGH++))
}

issue_medium() {
    echo -e "${YELLOW}🟡 MEDIA #$1: $2${NC}"
    echo -e "   📍 $(echo "$3" | head -1)"
    ((ISSUES_FOUND++))
    ((ISSUES_MEDIUM++))
}

cd "$REPO_ROOT"

# ============================================
header "DETECCIÓN DE 10 PROBLEMAS CRÍTICOS"
echo "Escaneando: app/ y tests/"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"

# ============================================
section "PROBLEMA #1: FieldInfo Attribute Access (CRÍTICA)"
echo "Buscando acceso a atributos en FieldInfo..."
RESULTS=$(grep -rn "field\.\(sharpe_ratio\|total_trades\|gross_profit\|max_drawdown_percentage\)" \
    app/backtesting/comprehensive_backtest_runner.py 2>/dev/null || echo "")
if [ -n "$RESULTS" ]; then
    issue_critical 1 "FieldInfo attribute access (crashes en runtime)" "$RESULTS"
    echo "$RESULTS" | sed 's/^/       /'
else
    echo -e "${GREEN}✔ No encontrado${NC}"
fi

# ============================================
section "PROBLEMA #2: Missing reset() Method (CRÍTICA)"
echo "Buscando .reset() en OverfittingDetector..."
RESULTS=$(grep -rn "\.reset()" app/strategies/momentum_modular/learning/learning_updater.py 2>/dev/null || echo "")
if [ -n "$RESULTS" ]; then
    # Verifica si el método existe en drift_detector.py
    if ! grep -q "def reset(" app/strategies/momentum_modular/learning/drift_detector.py; then
        issue_critical 2 "OverfittingDetector.reset() method doesn't exist" "$RESULTS"
        echo "$RESULTS" | sed 's/^/       /'
    fi
else
    echo -e "${GREEN}✔ No encontrado${NC}"
fi

# ============================================
section "PROBLEMA #3: Redundant/Wrong Imports (ALTA)"
echo "Buscando imports dentro de funciones..."
RESULTS=$(grep -rn "^[[:space:]]\+\(from\|import\)" app/ tests/ 2>/dev/null | head -20 || echo "")
if [ -n "$RESULTS" ]; then
    issue_high 3 "Imports dentro de funciones (wrong-import-position)" "$RESULTS"
    echo "$RESULTS" | head -5 | sed 's/^/       /'
else
    echo -e "${GREEN}✔ No encontrado${NC}"
fi

# ============================================
section "PROBLEMA #4: Bare-except & Broad Exception (ALTA)"
echo "Buscando bare-except..."
RESULTS=$(grep -rn "except:$" app/ tests/ 2>/dev/null || echo "")
if [ -n "$RESULTS" ]; then
    issue_high 4 "bare-except (masks all errors)" "$RESULTS"
    echo "$RESULTS" | sed 's/^/       /'
else
    echo -e "${GREEN}✔ No bare-except encontrado${NC}"
fi

echo "Buscando broad Exception catches..."
RESULTS=$(grep -rn "except Exception" app/ tests/ 2>/dev/null | grep -v "except.*as" | head -10 || echo "")
if [ -n "$RESULTS" ]; then
    issue_high 4 "broad Exception catch (hard to debug)" "$RESULTS"
    echo "$RESULTS" | sed 's/^/       /'
else
    echo -e "${GREEN}✔ No broad except encontrado${NC}"
fi

# ============================================
section "PROBLEMA #5: Logger used before assignment (CRÍTICA)"
echo "Buscando logger usado antes de definirse..."
RESULTS=$(grep -rn "logger\." app/strategies/momentum_modular/learning/training_data_preparator.py 2>/dev/null | head -3)
if [ -n "$RESULTS" ]; then
    LOGGER_DEF=$(grep -n "^logger = " app/strategies/momentum_modular/learning/training_data_preparator.py 2>/dev/null || echo "")
    if [ -z "$LOGGER_DEF" ] || [ "$(echo "$RESULTS" | head -1 | cut -d: -f1)" -lt "$(echo "$LOGGER_DEF" | head -1 | cut -d: -f1)" ] 2>/dev/null; then
        issue_critical 5 "logger used before assignment (NameError crash)" "$RESULTS"
        echo "$RESULTS" | sed 's/^/       /'
    fi
else
    echo -e "${GREEN}✔ No encontrado${NC}"
fi

# ============================================
section "PROBLEMA #6: f-string in Logger (ALTA)"
echo "Buscando logger.*(f\"...{...}...) patterns..."
RESULTS=$(grep -rn 'logger\.\(info\|debug\|warning\|error\)(f"' app/ tests/ 2>/dev/null | head -10 || echo "")
if [ -n "$RESULTS" ]; then
    issue_high 6 "f-string in logger (performance loss, silent logs)" "$RESULTS"
    echo "$RESULTS" | head -5 | sed 's/^/       /'
else
    echo -e "${GREEN}✔ No encontrado${NC}"
fi

echo "Buscando f-string sin interpolación..."
RESULTS=$(grep -rn 'f"[^{]*"' app/ tests/ 2>/dev/null | grep -v "{" | head -5 || echo "")
if [ -n "$RESULTS" ]; then
    issue_high 6 "f-string without interpolation (unnecessary)" "$RESULTS"
    echo "$RESULTS" | sed 's/^/       /'
else
    echo -e "${GREEN}✔ No encontrado${NC}"
fi

# ============================================
section "PROBLEMA #7: Wrong Import Position (MEDIA)"
echo "Buscando imports después de código ejecutable..."
RESULTS=$(grep -rn "^import\|^from" app/ tests/ 2>/dev/null | tail -20 | head -5 || echo "")
echo -e "${GREEN}✔ Validación manual recomendada (revisar primeras líneas de cada archivo)${NC}"

# ============================================
section "PROBLEMA #8: Too Many Arguments (MEDIA)"
echo "Buscando funciones con >5 argumentos..."
RESULTS=$(grep -rn "def [a-zA-Z_][a-zA-Z0-9_]*([^)]\{100,\})" app/ tests/ 2>/dev/null | head -5 || echo "")
if [ -n "$RESULTS" ]; then
    issue_medium 8 "Function with >5 arguments (hard to use)" "$RESULTS"
    echo "$RESULTS" | sed 's/^/       /'
else
    echo -e "${GREEN}✔ No encontrado (o detectado)${NC}"
fi

# ============================================
section "PROBLEMA #9: Duplicate Test Code (MEDIA)"
echo "Buscando patrones duplicados en tests..."
# Simple heuristic: busca "def test_" que se repite mucho
TEST_COUNT=$(find tests -name "*.py" -exec grep -c "def test_" {} + 2>/dev/null | awk '{s+=$1} END {print s}')
FIXTURE_COUNT=$(find tests -name "conftest.py" -exec grep -c "@pytest.fixture" {} + 2>/dev/null | awk '{s+=$1} END {print s}')
RATIO=$(echo "scale=2; $FIXTURE_COUNT / $TEST_COUNT" | bc 2>/dev/null || echo "0")

if (( $(echo "$RATIO < 0.1" | bc -l) )); then
    echo -e "${YELLOW}🟡 MEDIA #9: Bajo ratio de fixtures vs tests (ratio: $RATIO)${NC}"
    echo "   Posible código duplicado en tests"
    ((ISSUES_FOUND++))
    ((ISSUES_MEDIUM++))
else
    echo -e "${GREEN}✔ Buen ratio de fixtures ($RATIO)${NC}"
fi

# ============================================
section "PROBLEMA #10: Missing encoding in open() (MEDIA)"
echo "Buscando open() sin encoding=..."
RESULTS=$(grep -rn "open(" app/ tests/ 2>/dev/null | grep -v "encoding=" | head -10 || echo "")
if [ -n "$RESULTS" ]; then
    issue_medium 10 "open() without encoding= (UnicodeDecodeError risk)" "$RESULTS"
    echo "$RESULTS" | head -5 | sed 's/^/       /'
else
    echo -e "${GREEN}✔ No encontrado${NC}"
fi

# ============================================
header "RESUMEN DE DETECCIÓN"

echo -e "\n${CYAN}Total de problemas encontrados:${NC} $ISSUES_FOUND"
echo -e "  ${RED}🔴 Críticos: $ISSUES_CRITICAL${NC}"
echo -e "  ${YELLOW}🟠 Alta severidad: $ISSUES_HIGH${NC}"
echo -e "  ${YELLOW}🟡 Media severidad: $ISSUES_MEDIUM${NC}"

if [ "$ISSUES_CRITICAL" -gt 0 ]; then
    echo -e "\n${RED}❌ PROBLEMAS CRÍTICOS DETECTADOS${NC}"
    echo -e "Acción: Revisa CRITICAL_ISSUES_ACTION_PLAN.md para soluciones"
    echo -e "\nProblemas críticos deben arreglarse ANTES de hacer commit."
    exit 1
elif [ "$ISSUES_FOUND" -gt 0 ]; then
    echo -e "\n${YELLOW}⚠️ PROBLEMAS ENCONTRADOS${NC}"
    echo -e "Acción: Revisa CRITICAL_ISSUES_ACTION_PLAN.md para soluciones"
    exit 0
else
    echo -e "\n${GREEN}✅ NINGÚN PROBLEMA CRÍTICO DETECTADO${NC}"
    exit 0
fi
