#!/bin/bash
# Script para ejecutar run_deep_learning_backtest.py con variables de entorno configuradas
# Uso: ./scripts/run_with_env.sh

# Variables de entorno para prevenir bloqueos de mutex.cc
export MKL_SERVICE_FORCE_INTEL=1
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export NUMEXPR_MAX_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export MKL_DYNAMIC=FALSE
export MKL_INTERFACE_LAYER=LP64,GNU
export CUDA_VISIBLE_DEVICES=
export TORCH_USE_CUDA_DSA=0
export PYTORCH_ENABLE_MPS_FALLBACK=1
export TF_CPP_MIN_LOG_LEVEL=2

# Cambiar al directorio del proyecto
cd "$(dirname "$0")/.." || exit 1

# Ejecutar el script
echo "🚀 Ejecutando backtest con variables de entorno configuradas..."
python scripts/run_deep_learning_backtest.py

