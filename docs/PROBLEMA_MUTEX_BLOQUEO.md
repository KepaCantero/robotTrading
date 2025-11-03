# 🔒 Problema de Bloqueo mutex.cc con PyTorch

## Problema

El error `[mutex.cc : 452] RAW: Lock blocking` ocurre cuando PyTorch intenta inicializar threading múltiple y hay conflictos con las bibliotecas C++ subyacentes (MKL, OpenBLAS).

## Soluciones Implementadas

### 1. Variables de Entorno (Nivel de Sistema)

Configuradas en:

- `scripts/run_deep_learning_backtest.py`
- `app/strategies/momentum_modular/learning/deep_learning_engine.py`
- `app/strategies/momentum_modular/learning/transformer_engine.py`

```python
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_MAX_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['MKL_DYNAMIC'] = 'FALSE'
```

### 2. Configuración de PyTorch

- `torch.set_num_threads(1)`
- `torch.set_num_interop_threads(1)`
- Device forzado a CPU

### 3. DataLoader Single-Threaded

- `num_workers=0`
- `pin_memory=False`
- `persistent_workers=False`

### 4. Creación Segura de Tensores

- Uso de `torch.from_numpy().clone()` en lugar de `torch.FloatTensor()`
- `torch.inference_mode()` para crear tensores

## Si el Problema Persiste

El bloqueo de `mutex.cc` puede ser causado por:

1. **Versión de PyTorch incompatible** con el sistema
2. **Conflicto entre MKL y OpenBLAS** en el sistema
3. **Problema en la instalación** de PyTorch o sus dependencias

### Soluciones Alternativas

1. **Reinstalar PyTorch sin MKL:**

   ```bash
   pip uninstall torch
   pip install torch --no-deps
   pip install torchvision torchaudio --no-deps
   ```

2. **Usar versión CPU-only de PyTorch:**

   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   ```

3. **Deshabilitar MKL completamente:**

   ```bash
   export MKL_SERVICE_FORCE_INTEL=1
   export KMP_DUPLICATE_LIB_OK=TRUE
   ```

4. **Usar conda en lugar de pip:**
   ```bash
   conda install pytorch cpuonly -c pytorch
   ```

## Nota

Este es un problema conocido con PyTorch en macOS, especialmente cuando hay conflictos entre diferentes bibliotecas matemáticas (MKL vs OpenBLAS). Las configuraciones aplicadas deberían resolver el problema en la mayoría de los casos, pero si persiste, puede requerir reinstalación de PyTorch o uso de un entorno virtual diferente.
