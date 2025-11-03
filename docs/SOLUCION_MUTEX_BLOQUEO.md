# 🔒 Solución Definitiva para Error mutex.cc Blocking

## Problema

El error `[mutex.cc : 452] RAW: Lock blocking` ocurre cuando PyTorch/MKL intentan usar múltiples threads y hay conflictos de sincronización. Esto puede bloquear el proceso completamente.

## Solución Implementada

### 1. Variables de Entorno Configuradas Automáticamente

Los scripts principales ya configuran estas variables **ANTES** de importar cualquier librería:

- ✅ `scripts/run_deep_learning_backtest.py`
- ✅ `scripts/run_comprehensive_backtest.py`
- ✅ `app/backtesting/comprehensive_backtest_runner.py`
- ✅ `app/strategies/momentum_modular/learning/deep_learning_engine.py`
- ✅ `app/strategies/momentum_modular/learning/transformer_engine.py`

### 2. Fallback Automático a Subprocess

Si el bloqueo persiste, el sistema **automáticamente** detecta el error y reintenta el entrenamiento en un proceso hijo aislado (`use_subprocess=True`).

### 3. Script Wrapper (Recomendado)

Ejecuta el backtest usando el script wrapper que asegura todas las variables:

```bash
./scripts/run_with_env.sh
```

## Si el Problema Persiste

### Opción A: Ejecutar con Variables Explícitas

```bash
export MKL_SERVICE_FORCE_INTEL=1
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export MKL_DYNAMIC=FALSE
export MKL_INTERFACE_LAYER=LP64,GNU

python scripts/run_deep_learning_backtest.py
```

### Opción B: Reinstalar PyTorch sin MKL

```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### Opción C: Usar Conda

```bash
conda install pytorch cpuonly -c pytorch
conda install numpy pandas scikit-learn
```

## Verificación

Para verificar que las variables están configuradas:

```bash
python -c "import os; print('OMP_NUM_THREADS:', os.environ.get('OMP_NUM_THREADS')); print('MKL_NUM_THREADS:', os.environ.get('MKL_NUM_THREADS'))"
```

Debería mostrar `1` para ambas variables.

## Logs de Diagnóstico

Si el problema persiste, los logs mostrarán:

```
⚠️ Bloqueo de mutex detectado. Reintentando entrenamiento en proceso hijo aislado...
```

Esto indica que el sistema detectó el bloqueo y está usando el fallback automático.
