#!/bin/bash
# Script para instalar TODAS las dependencias requeridas

set -e

echo "🚀 Instalando todas las dependencias del proyecto..."

# Actualizar pip
python -m pip install --upgrade pip

# Instalar dependencias base
echo "📦 Instalando dependencias base..."
python -m pip install "numpy>=2.0.0" "pandas>=2.0.0" --upgrade --force-reinstall

# Instalar pandas-ta-classic (requiere numpy 2.x)
echo "📦 Instalando pandas-ta-classic..."
python -m pip install "pandas-ta-classic>=0.3.36"

# Instalar scikit-learn y xgboost
echo "📦 Instalando scikit-learn y xgboost..."
python -m pip install "scikit-learn>=1.3.0" "xgboost>=2.0.0"

# Instalar PyTorch
echo "📦 Instalando PyTorch..."
python -m pip install "torch>=2.0.0" "torchvision>=0.15.0"

# Instalar TensorFlow (opcional, pero recomendado)
echo "📦 Instalando TensorFlow..."
python -m pip install "tensorflow>=2.13.0"

# Instalar Reinforcement Learning
echo "📦 Instalando stable-baselines3 y gym..."
python -m pip install "stable-baselines3>=2.0.0" "gym>=0.26.0" "gymnasium>=0.29.0"

# Instalar resto de dependencias
echo "📦 Instalando resto de dependencias..."
python -m pip install -r requirements.txt --ignore-installed pandas --ignore-installed numpy

echo "✅ Todas las dependencias instaladas correctamente!"
echo ""
echo "🔍 Verificando instalación..."
python -c "
import pandas_ta_classic as ta
import numpy as np
import pandas as pd
from sklearn import ensemble
import xgboost
import torch
import stable_baselines3
print('✅ pandas-ta-classic:', ta.__version__)
print('✅ numpy:', np.__version__)
print('✅ pandas:', pd.__version__)
print('✅ scikit-learn: OK')
print('✅ xgboost:', xgboost.__version__)
print('✅ torch:', torch.__version__)
print('✅ stable-baselines3: OK')
print('')
print('🎉 TODAS LAS DEPENDENCIAS ESTÁN INSTALADAS!')
"

