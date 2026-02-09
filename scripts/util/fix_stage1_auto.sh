#!/bin/bash
# FASE 1: CORRECCIONES AUTOMÁTICAS
# Ejecutar este script primero

set -euo pipefail

source .venv/bin/activate

echo "=========================================="
echo "FASE 1: CORRECCIONES AUTOMÁTICAS"
echo "=========================================="
echo ""

echo ">>> 1.1 Autoflake - Eliminar imports/vars no usados"
autoflake --in-place --remove-unused-variables --remove-all-unused-imports -r app/ tests/

echo ">>> 1.2 Ruff --fix - Correcciones automáticas"
ruff check app/ tests/ --fix

echo ">>> 1.3 Black - Formatear código"
black app/ tests/

echo ">>> 1.4 Isort - Ordenar imports"
isort app/ tests/

echo ">>> 1.5 Corregir E712 (comparaciones con True/False)"
ruff check app/ tests/ --select E712 --fix

echo ""
echo "=========================================="
echo "FASE 1 COMPLETADA"
echo "=========================================="
echo ""
echo "Verificando progreso..."
flake8 app/ tests/ --max-line-length=100 2>&1 | wc -l | xargs echo "Flake8 errores:"
pylint app/ tests/ --output-format=text 2>&1 | grep -c "^" | xargs echo "Pylint líneas:"
mypy app/ tests/ 2>&1 | grep 'error:' | wc -l | xargs echo "Mypy errores:"
bandit -r app/ tests/ -ll 2>&1 | grep '>> Issue:' | wc -l | xargs echo "Bandit issues:"
echo ""
echo "Continuar con FASE 2 (seguridad)"
