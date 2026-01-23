#!/bin/bash
# Script para corregir automáticamente E712 (comparaciones con True/False)

set -euo pipefail

source .venv/bin/activate

echo "=== Corrigiendo E712 - Comparaciones con True/False ==="
ruff check app/ tests/ --select E712 --fix

echo "=== Verificando correcciones ==="
flakes_e712=$(flake8 app/ tests/ --max-line-length=100 2>&1 | grep "E712" | wc -l)
echo "Quedan $flakes_e712 errores E712"
