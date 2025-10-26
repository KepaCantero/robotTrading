#!/bin/bash
# ===========================================
# check_all.sh - Chequeo completo de proyecto
# ===========================================
# Solo chequea archivos de producción (app/) y tests (tests/)
# ===========================================

set -e

echo "==========================================="
echo "       FORMATEO Y ORDEN DE IMPORTS"
echo "==========================================="
black app/ tests/ check_all.sh 2>&1 || true
isort app/ tests/ 2>&1 || true

echo "==========================================="
echo "                 LINTING"
echo "==========================================="
flake8 app/ tests/ --max-line-length=100 --statistics 2>&1 || true

echo "==========================================="
echo "                  TESTS"
echo "==========================================="
pytest --tb=no -q 2>&1

echo "==========================================="
echo "          CHEQUEO COMPLETO FINALIZADO"
echo "==========================================="
