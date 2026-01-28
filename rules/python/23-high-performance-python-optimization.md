# 📘 23. High Performance Python - Optimization Strategies

**Libro:** High Performance Python (2nd Edition) - Micha Gorelick & Ian Ozsvald
**Objetivo:** Optimizar código Python para trading de alta frecuencia y gran volumen

## 🎯 Resumen Ejecutivo

Claude Code DEBE optimizar el código siguiendo estos principios:
1. **Medir antes de optimizar** (profiling obligatorio)
2. **Vectorizar** todo lo posible
3. **Eliminar cuellos de botella** del GIL
4. **Minimizar copias de memoria**

---

## 📋 Las 15 Reglas Críticas para Claude Code

### 1. Vectorización NumPy (Prohibido `for` loops)

```python
import numpy as np

# ❌ MAL: Loop for en Python (MUY LENTO)
def calculate_returns_slow(prices):
    returns = []
    for i in range(1, len(prices)):
        ret = (prices[i] - prices[i-1]) / prices[i-1]
        returns.append(ret)
    return np.array(returns)

# ✅ BIEN: Vectorizado con NumPy (100x más rápido)
def calculate_returns_fast(prices: np.ndarray) -> np.ndarray:
    return np.diff(prices) / prices[:-1]

# O más simple:
def calculate_returns_fastest(prices: np.ndarray) -> np.ndarray:
    return prices.pct_change().dropna()
```

**Regla para Claude:** ESTÁ PROHIBIDO usar `for` loops para cálculos numéricos. TODO debe vectorizarse.

---

### 2. Numba `@jit(nopython=True)` para Indicadores Recursivos

```python
from numba import jit
import numpy as np

# ✅ BIEN: Compilado a máquina (velocidad C++)
@jit(nopython=True, cache=True)
def ema_numba(prices: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average - compilado."""
    n = len(prices)
    result = np.empty(n)
    alpha = 2.0 / (period + 1)

    result[0] = prices[0]
    for i in range(1, n):
        result[i] = alpha * prices[i] + (1 - alpha) * result[i-1]

    return result

# Primer llamada: compila (lento)
# Segunda llamada: ejecuta compilado (muy rápido)
```

**Regla para Claude:** USAR `@jit(nopython=True)` para cálculos recursivos (EMA, ATR, Hurst).

---

### 3. Multiprocessing para Backtesting

```python
from multiprocessing import Pool, cpu_count
import numpy as np

def backtest_single(params):
    """Backtest con un set de parámetros."""
    # ... lógica de backtest ...
    return sharpe_ratio

def parallel_backtest(param_grid):
    """Ejecuta múltiples backtests en paralelo."""
    n_cores = cpu_count()

    with Pool(n_cores) as pool:
        results = pool.map(backtest_single, param_grid)

    return results

# Usar TODOS los núcleos del CPU
```

**Regla para Claude:** USAR `multiprocessing` para backtests de parámetros múltiples (el GIL bloquea threads).

---

### 4. Cython para Risk Gates

```python
# risk_gates.pyx (compila a C)
#cython: language_level=3

def check_position_limit_risk(
    double current_position,
    double position_limit,
    double order_quantity
) -> bool:
    """Validación de riesgo crítica - compilada a C."""
    if current_position + order_quantity > position_limit:
        return False
    return True

# Compilar: python setup.py build_ext --inplace
# Resultado: Velocidad C++
```

**Regla para Claude:** COMPILAR a Cython las funciones de riesgo críticas (validaciones en hot path).

---

### 5. `memoryview` para Socket Data sin Copias

```python
# ❌ MAL: Copia datos
def process_socket_data(data):
    array = np.frombuffer(data, dtype=np.float64)  # Copia

# ✅ BIEN: Zero-copy
def process_socket_data_fast(data):
    mv = memoryview(data)
    # Trabaja directamente sobre el buffer del socket
    return mv.cast('B')  # Vista como bytes, sin copiar
```

**Regla para Claude:** USAR `memoryview` para datos de WebSocket (evitar copias innecesarias).

---

### 6. Evitar Global Scope

```python
# ❌ MAL: Variables globales (acceso lento)
MAX_POSITION = 1000
def check_limit(position):
    return position < MAX_POSITION

# ✅ BIEN: Funciones puras con argumentos
def check_limit_fast(position: int, max_position: int) -> bool:
    return position < max_position

# Local variables >> Global variables en speed
```

**Regla para Claude:** METER lógica en funciones (local scope es más rápido que global scope).

---

### 7. `''.join()` sobre `+` para Strings

```python
# ❌ MAL: Concatenación con + (crea objetos intermedios)
message = "Order " + order_id + " for " + symbol + " filled."

# ✅ BIEN: join (una sola creación)
message = ''.join(["Order ", order_id, " for ", symbol, " filled."])

# ✅ MEJOR: f-string (más rápido y legible)
message = f"Order {order_id} for {symbol} filled."
```

**Regla para Claude:** USAR f-strings para formateo de strings (más rápido y legible).

---

### 8. PyPy para Bots sin NumPy Extensivo

```python
# Si tu bot NO usa NumPy/Pandas extensivamente:
# Ejecutar con PyPy (JIT automático)

# pypy trading_bot.py
# Resultado: 2-5x más rápido que CPython en código puro Python
```

**Regla para Claude:** CONSIDERAR PyPy para bots sin cálculos numéricos pesados (solo lógica de órdenes).

---

### 9. py-spy para Profiling en Producción

```bash
# Profiling de bot en vivo SIN detenerlo
py-spy top --pid $(pgrep -f trading_bot.py)

# Sampling profiler: baja overhead (<5%)
# Muestra dónde está el cuello de botella en tiempo real
```

**Regla para Claude:** USAR `py-spy` para profiling de producción (no detiene el bot).

---

### 10. Prohibido `pandas.apply()` (Usar Vectorizado)

```python
# ❌ MAL: apply (lento, es un loop disfrazado)
df['signal'] = df.apply(lambda row: 1 if row['price'] > row['ma'] else 0, axis=1)

# ✅ BIEN: Vectorizado (donde sea posible)
df['signal'] = np.where(df['price'] > df['ma'], 1, 0)

# ✅ MEJOR: Operación directa
df['signal'] = (df['price'] > df['ma']).astype(int)
```

**Regla para Claude:** PROHIBIDO usar `apply()` en código de producción. Usar vectorizado.

---

### 11. Local Imports en Loops Críticos

```python
# ❌ MAL: Import en loop (se ejecuta cada iteración)
for tick in ticks:
    import numpy as np  # ← LENTO
    process_tick(tick)

# ✅ BIEN: Import al inicio del módulo
import numpy as np
for tick in ticks:
    process_tick(tick)
```

**Regla para Claude:** IMPORTAR módulos al inicio del archivo, nunca dentro de loops.

---

### 12. `@functools.cached_property`

```python
from functools import cached_property

@dataclass
class MarketData:
    prices: np.ndarray
    volumes: np.ndarray

    @cached_property
    def vwap(self) -> float:
        """VWAP - calcula solo una vez."""
        return np.sum(self.prices * self.volumes) / np.sum(self.volumes)

    @cached_property
    def volatility(self) -> float:
        """Volatilidad - calcula solo una vez."""
        return np.std(self.prices) / np.mean(self.prices)

# Primer acceso: calcula
# Accesos subsiguientes: cache
```

**Regla para Claude:** USAR `cached_property` para propiedades costosas que no cambian.

---

### 13. Buffers de Red Ajustados

```python
import socket

# Socket con buffer optimizado para trading de alta frecuencia
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)  # 64KB send buffer
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)  # 64KB recv buffer
sock.connect((broker_host, broker_port))
```

**Regla para Claude:** AJUSTAR buffers de socket para evitar pérdida de paquetes en alta volatilidad.

---

### 14. f-strings para Formateo Rápido

```python
# ✅ BIEN: f-strings (más rápido y legible)
def log_order(order: Order) -> None:
    logger.info(f"Order {order.order_id}: {order.side} {order.quantity} {order.symbol} @ {order.price}")

# vs logger.info("Order {}: {} {} {} @ {}".format(...))
```

**Regla para Claude:** USAR f-strings para TODO el formateo de strings (logging, mensajes).

---

### 15. `math.sqrt` sobre `np.sqrt` para Escalares

```python
import math
import numpy as np

# ❌ Para un solo número: np.sqrt es overkill
value = np.sqrt(25.0)  # Crea array numpy

# ✅ Para un solo número: math es más rápido
value = math.sqrt(25.0)

# ✅ Para arrays: np.sqrt es el correcto
values = np.sqrt(array_10k)
```

**Regla para Claude:** USAR `math.sqrt` para escalares, `np.sqrt` para arrays.

---

## 🚀 Bonus: Pre-allocation de Arrays

```python
# ❌ MAL: Append en loop (reallocations)
results = []
for i in range(1000000):
    results.append(calculate_something(i))

# ✅ BIEN: Pre-allocate
n = 1000000
results = np.empty(n)
for i in range(n):
    results[i] = calculate_something(i)
```

---

## 📊 Checklist de Optimización para Claude Code

### Antes de Optimizar
1. **Medir primero**: `cProfile` o `py-spy`
2. **Encontrar hot path**: ¿Dónde está el 80% del tiempo?
3. **Optimizar solo hot path**: Premature optimization es root of all evil

### Durante Optimización
1. ✅ Vectorizar con NumPy
2. ✅ Compilar con Numba (recursivos)
3. ✅ Paralelizar con multiprocessing (backtests)
4. ✅ Eliminar copias de memoria (memoryview)
5. ✅ Local scope (funciones > globales)
6. ✅ Evitar apply(), iterrows()
7. ✅ Usar tipos correctos (float32 vs float64)

### Después de Optimizar
1. **Medir de nuevo**: ¿Mejoró realmente?
2. **Verificar corrección**: Tests unitarios
3. **Documentar**: Comentario con benchmark

---

## 🎓 Ejemplo Completo: Sistema Optimizado

```python
import numpy as np
from numba import jit
from functools import cached_property
from dataclasses import dataclass

@dataclass
class OptimizedIndicator:
    """Indicadores técnicos optimizados."""
    prices: np.ndarray
    volumes: np.ndarray

    @cached_property
    def returns(self) -> np.ndarray:
        """Retornos vectorizados."""
        return np.diff(self.prices) / self.prices[:-1]

    @cached_property
    def volatility(self) -> float:
        """Volatilidad anualizada."""
        return np.std(self.returns) * np.sqrt(252)

@jit(nopython=True, cache=True)
def calculate_ema_numba(prices: np.ndarray, period: int) -> np.ndarray:
    """EMA compilado."""
    n = len(prices)
    result = np.empty(n)
    alpha = 2.0 / (period + 1)
    result[0] = prices[0]

    for i in range(1, n):
        result[i] = alpha * prices[i] + (1 - alpha) * result[i-1]

    return result

def backtest_vectorized(prices: np.ndarray, signals: np.ndarray) -> float:
    """Backtest vectorizado (sin loops)."""
    returns = np.diff(prices) / prices[:-1]
    strategy_returns = returns[1:] * signals[:-1]

    sharpe = np.mean(strategy_returns) / np.std(strategy_returns) * np.sqrt(252)
    return sharpe
```

---

## 📚 Referencias

- **Libro:** High Performance Python (2nd Edition) - Micha Gorelick & Ian Ozsvald
- **Herramientas:**
  - `cProfile`: Profiling estándar
  - `py-spy`: Profiling de producción
  - `line_profiler`: Profiling línea por línea
  - `memory_profiler`: Profiling de memoria
  - `Numba`: JIT compilation
  - `Cython`: Compilación a C

---

**Última actualización:** 2026-01-28
**Version:** 2.1 (Completado con ejemplos de GPU)


---

## 🚀 GPU Acceleration con CuPy

### Introducción

CuPy implementa NumPy para GPU (10-100x más rápido).

```bash
pip install cupy-cuda11x
```

### Ejemplo 1: Cálculo en GPU

```python
import cupy as cp
import numpy as np

# GPU
prices_gpu = cp.array(np.random.randn(10_000_000).cumsum())
returns = cp.diff(prices_gpu) / prices_gpu[:-1]

# Sincronizar
cp.cuda.Stream.null.synchronize()
```

### Ejemplo 2: Backtesting Paralelo

```python
def parallel_backtest_gpu(prices, signals):
    price_returns = cp.diff(prices, axis=0) / prices[:-1]
    return price_returns[1:] * signals[:-1]

def calculate_sharpe_gpu(returns):
    mean = cp.mean(returns, axis=0)
    std = cp.std(returns, axis=0)
    return mean / std * cp.sqrt(252)
```

### Ejemplo 3: VaR en GPU

```python
def calculate_var_gpu(returns, confidence=0.95):
    alpha = 1 - confidence
    return float(cp.percentile(returns, alpha * 100))
```


---

## 🚀 GPU Acceleration con CuPy

### Introducción

CuPy implementa NumPy para GPU (10-100x más rápido).

```bash
pip install cupy-cuda11x
```

### Ejemplo 1: Cálculo en GPU

```python
import cupy as cp
import numpy as np

# GPU
prices_gpu = cp.array(np.random.randn(10_000_000).cumsum())
returns = cp.diff(prices_gpu) / prices_gpu[:-1]

# Sincronizar
cp.cuda.Stream.null.synchronize()
```

### Ejemplo 2: Backtesting Paralelo

```python
def parallel_backtest_gpu(prices, signals):
    price_returns = cp.diff(prices, axis=0) / prices[:-1]
    return price_returns[1:] * signals[:-1]

def calculate_sharpe_gpu(returns):
    mean = cp.mean(returns, axis=0)
    std = cp.std(returns, axis=0)
    return mean / std * cp.sqrt(252)
```

### Ejemplo 3: VaR en GPU

```python
def calculate_var_gpu(returns, confidence=0.95):
    alpha = 1 - confidence
    return float(cp.percentile(returns, alpha * 100))
```
