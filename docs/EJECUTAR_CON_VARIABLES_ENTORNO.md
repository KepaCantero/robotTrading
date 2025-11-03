# Ejecutar Scripts con Variables de Entorno para Evitar Bloqueos de Mutex

Este documento explica cómo ejecutar los scripts del sistema AlgoTrading con variables de entorno configuradas para evitar el error `[mutex.cc : 452]` que ocurre cuando PyTorch/MKL/OpenBLAS intentan usar múltiples threads.

## Solución Automática (Recomendada)

Los scripts principales (`app.py`, `run_dashboard.py`, `scripts/run_comprehensive_backtest.py`, etc.) ya están configurados para establecer estas variables automáticamente. Simplemente ejecuta:

```bash
python scripts/run_comprehensive_backtest.py
python run_dashboard.py
python app.py
```

## Solución Manual (Si Persisten Problemas)

Si aún experimentas bloqueos, puedes ejecutar los scripts con variables de entorno explícitas desde la terminal.

### Linux/macOS (bash/zsh)

```bash
MKL_SERVICE_FORCE_INTEL=1 \
KMP_DUPLICATE_LIB_OK=TRUE \
OMP_NUM_THREADS=1 \
OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 \
python scripts/run_comprehensive_backtest.py
```

O usando `export`:

```bash
export MKL_SERVICE_FORCE_INTEL=1
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

python scripts/run_comprehensive_backtest.py
```

### Windows (PowerShell)

```powershell
$env:MKL_SERVICE_FORCE_INTEL="1"
$env:KMP_DUPLICATE_LIB_OK="TRUE"
$env:OMP_NUM_THREADS="1"
$env:OPENBLAS_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"
$env:VECLIB_MAXIMUM_THREADS="1"

python scripts/run_comprehensive_backtest.py
```

### Windows (CMD)

```cmd
set MKL_SERVICE_FORCE_INTEL=1
set KMP_DUPLICATE_LIB_OK=TRUE
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
set VECLIB_MAXIMUM_THREADS=1

python scripts/run_comprehensive_backtest.py
```

## Scripts Principales

### Backtesting de Deep Learning

````bash
# Opción 1: Usar el script wrapper (RECOMENDADO)
./scripts/run_with_env.sh

# Opción 2: Ejecutar directamente con variables
# Linux/macOS
MKL_SERVICE_FORCE_INTEL=1 KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1 MKL_DYNAMIC=FALSE python scripts/run_deep_learning_backtest.py

### Backtesting Comprehensivo

```bash
# Linux/macOS
MKL_SERVICE_FORCE_INTEL=1 KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1 MKL_DYNAMIC=FALSE python scripts/run_comprehensive_backtest.py

# Windows PowerShell
$env:MKL_SERVICE_FORCE_INTEL="1"; $env:KMP_DUPLICATE_LIB_OK="TRUE"; $env:OMP_NUM_THREADS="1"; python scripts/run_comprehensive_backtest.py
````

### Dashboard

```bash
# Linux/macOS
MKL_SERVICE_FORCE_INTEL=1 KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1 python run_dashboard.py

# Windows PowerShell
$env:MKL_SERVICE_FORCE_INTEL="1"; $env:KMP_DUPLICATE_LIB_OK="TRUE"; $env:OMP_NUM_THREADS="1"; python run_dashboard.py
```

### Deep Learning Backtest

```bash
# Linux/macOS
MKL_SERVICE_FORCE_INTEL=1 KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1 python scripts/run_deep_learning_backtest.py

# Windows PowerShell
$env:MKL_SERVICE_FORCE_INTEL="1"; $env:KMP_DUPLICATE_LIB_OK="TRUE"; $env:OMP_NUM_THREADS="1"; python scripts/run_deep_learning_backtest.py
```

## Variables de Entorno Explicadas

| Variable                             | Propósito                                                     |
| ------------------------------------ | ------------------------------------------------------------- |
| `OMP_NUM_THREADS=1`                  | Limita OpenMP a 1 thread                                      |
| `OPENBLAS_NUM_THREADS=1`             | Limita OpenBLAS a 1 thread                                    |
| `MKL_NUM_THREADS=1`                  | Limita Intel MKL a 1 thread                                   |
| `NUMEXPR_NUM_THREADS=1`              | Limita NumExpr a 1 thread                                     |
| `VECLIB_MAXIMUM_THREADS=1`           | Limita Accelerate (macOS) a 1 thread                          |
| `MKL_SERVICE_FORCE_INTEL=1`          | Fuerza MKL a usar backend Intel (crítico en macOS)            |
| `KMP_DUPLICATE_LIB_OK=TRUE`          | Permite múltiples instancias de OpenMP/MKL (evita conflictos) |
| `PYTORCH_ENABLE_MPS_FALLBACK=1`      | Habilita fallback de Metal Performance Shaders en macOS       |
| `FOR_DISABLE_CONSOLE_CTRL_HANDLER=1` | Deshabilita handler de control de consola (Windows)           |
| `CUDA_VISIBLE_DEVICES=""`            | Deshabilita CUDA completamente                                |

## ¿Por qué esto soluciona el problema?

El error `[mutex.cc : 452]` aparece porque:

1. **OpenBLAS o MKL inicializaron threads internos** antes de que PyTorch o multiprocessing clonaran el proceso
2. **Los locks quedaron huérfanos** después de fork/spawn
3. **Cualquier operación de tensor intenta "re-bloquear" el mismo mutex** → bloqueo infinito

Reduciendo todos los threads a 1 y forzando el backend Intel (`MKL_SERVICE_FORCE_INTEL=1`), eliminamos esa condición de carrera.

## Solución Alternativa: Usar Subprocess

Si las variables de entorno no resuelven el problema, el sistema automáticamente detectará bloqueos de mutex y reintentará el entrenamiento en un proceso hijo aislado usando `use_subprocess=True`. Esto está implementado automáticamente en `ComprehensiveBacktestRunner`.

## Referencias

- Documentación de PyTorch sobre threading: https://pytorch.org/docs/stable/notes/cpu_threading_torchscript_inference.html
- Documentación de Intel MKL: https://www.intel.com/content/www/us/en/docs/onemkl/developer-guide-linux/2023-0/threading-control.html
- Documentación de OpenBLAS: https://github.com/xianyi/OpenBLAS/wiki/faq#multi-threaded
