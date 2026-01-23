#!/bin/bash
# Script para corregir automáticamente problemas de importación

set -euo pipefail

source .venv/bin/activate

echo "=== Corrigiendo importaciones ==="

# Eliminar imports no usados
echo ">>> Eliminando imports no usados..."
autoflake --in-place --remove-unused-variables --remove-all-unused-imports -r app/ tests/

# Ordenar imports
echo ">>> Ordenando imports..."
isort app/ tests/

# Aplicar black después de isort
echo ">>> Aplicando black..."
black app/ tests/

echo "=== Verificando correcciones ==="
flakes_e402=$(flake8 app/ tests/ --max-line-length=100 2>&1 | grep "E402" | wc -l)
echo "Quedan $flakes_e402 errores E402"
