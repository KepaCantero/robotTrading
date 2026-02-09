#!/bin/bash
# Script para verificar el progreso de correcciones

set -euo pipefail

source .venv/bin/activate

echo "=== PROGRESO DE CORRECCIONES ==="
echo ""

echo "Total archivos Python:"
find app/ tests/ -name "*.py" | wc -l
echo ""

echo "=== ERRORES POR HERRAMIENTA ==="
echo ""

echo "Flake8:"
flakes=$(flake8 app/ tests/ --max-line-length=100 2>&1 | wc -l | xargs)
echo "  Total: $flakes errores"
echo "  E402 (imports): $(flake8 app/ tests/ --max-line-length=100 2>&1 | grep 'E402' | wc -l | xargs)"
echo "  E712 (True/False): $(flake8 app/ tests/ --max-line-length=100 2>&1 | grep 'E712' | wc -l | xargs)"
echo "  E722 (bare except): $(flake8 app/ tests/ --max-line-length=100 2>&1 | grep 'E722' | wc -l | xargs)"
echo "  F841 (unused vars): $(flake8 app/ tests/ --max-line-length=100 2>&1 | grep 'F841' | wc -l | xargs)"
echo "  F821 (undefined): $(flake8 app/ tests/ --max-line-length=100 2>&1 | grep 'F821' | wc -l | xargs)"
echo ""

echo "Pylint:"
pylint_messages=$(pylint app/ tests/ --output-format=text 2>&1 | grep -oE "[A-Z][0-9]{4}:" | wc -l | xargs)
echo "  Total: $pylint_messages mensajes"
echo "  W1203 (logging f-strings): $(pylint app/ tests/ --output-format=text 2>&1 | grep 'W1203:' | wc -l | xargs)"
echo "  C0301 (line too long): $(pylint app/ tests/ --output-format=text 2>&1 | grep 'C0301:' | wc -l | xargs)"
echo "  W0613 (unused args): $(pylint app/ tests/ --output-format=text 2>&1 | grep 'W0613:' | wc -l | xargs)"
echo "  W0603 (global stmt): $(pylint app/ tests/ --output-format=text 2>&1 | grep 'W0603:' | wc -l | xargs)"
echo ""

echo "Mypy:"
mypy_errors=$(mypy app/ tests/ 2>&1 | grep 'error:' | wc -l | xargs)
echo "  Total: $mypy_errors errores"
echo ""

echo "Bandit:"
bandit_issues=$(bandit -r app/ tests/ -ll 2>&1 | grep '>> Issue:' | wc -l | xargs)
echo "  Total: $bandit_issues issues"
echo "  B301 (pickle): $(bandit -r app/ tests/ -ll 2>&1 | grep 'B301:blacklist' | wc -l | xargs)"
echo "  B104 (bind all): $(bandit -r app/ tests/ -ll 2>&1 | grep 'B104:hardcoded_bind_all_interfaces' | wc -l | xargs)"
echo "  B608 (SQL): $(bandit -r app/ tests/ -ll 2>&1 | grep 'B608:hardcoded_sql_expressions' | wc -l | xargs)"
echo ""

echo "=== ARCHIVOS MÁS AFECTADOS ==="
echo ""
echo "Top 10 archivos con más errores de Flake8:"
flake8 app/ tests/ --max-line-length=100 2>&1 | cut -d: -f1 | sort | uniq -c | sort -rn | head -10
echo ""

echo "=== RESUMEN ==="
echo "Objetivo: CERO errores en todas las herramientas"
echo "Progreso: Ver manual detallado en PLAN_CORRECCION_CHECK_ALL.md"
