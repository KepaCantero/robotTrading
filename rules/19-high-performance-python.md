# 📗 19. "High Performance Python" - Micha Gorelick & Ian Ozsvald

## REGLAS DE ALTO RENDIMIENTO PARA TRADING

**Regla 19.1 — Profiling First**

Claude DEBE profilear antes de optimizar:
- NO optimices sin cProfile o py-spy primero
- La intuición falla

```python
import cProfile
import pstats

def profile_strategy(func):
    """Decorador para profilear funciones."""
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()

        result = func(*args, **kwargs)

        profiler.disable()
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(10)  # Top 10 funciones más lentas

        return result
    return wrapper

# Usar antes de optimizar
@profile_strategy
def backtest_strategy(strategy, data):
    # Backtest completo
    pass

# Ver output para ver qué optimizar
# ncalls  tottime  percall  cumtime  percall filename:lineno(function)
#   1000    0.003    0.000    0.050    0.000 strategy.py:45(calculate_signals)
```

**Regla 19.2 — AsyncIO para I/O**

Claude DEBE usar async/await para red:
- HTTP requests, Websockets
- Obligatorio para múltiples tickers

```python
import asyncio
import aiohttp

async def fetch_quotes(session: aiohttp.ClientSession, symbols: List[str]) -> Dict[str, Quote]:
    """Fetch múltiples símbolos en paralelo con AsyncIO."""
    tasks = [fetch_quote(session, symbol) for symbol in symbols]
    quotes = await asyncio.gather(*tasks)
    return {q.symbol: q for q in quotes}

async def fetch_quote(session: aiohttp.ClientSession, symbol: str) -> Quote:
    """Fetch un símbolo - async."""
    async with session.get(f"/api/quotes/{symbol}") as response:
        data = await response.json()
        return Quote.from_dict(data)

# Usar
async def main():
    async with aiohttp.ClientSession() as session:
        quotes = await fetch_quotes(session, ["AAPL", "MSFT", "GOOGL"])
        print(quotes)

asyncio.run(main())
```

**Regla 19.3 — Multiprocessing para CPU**

Claude DEBE usar ProcessPoolExecutor para cálculos pesados:
- El GIL te frenará
- Cálculos paralelos en núcleos separados

```python
from multiprocessing import Pool
from functools import partial

def calculate_indicators(symbol: str, params: dict) -> dict:
    """Calcular indicadores para un símbolo - CPU intensive."""
    # Cálculo pesado...
    pass

def parallel_backtest(symbols: List[str], params: dict, n_processes: int = 4):
    """Ejecutar backtests en paralelo."""
    with Pool(n_processes) as pool:
        # Partial para fijar params
        func = partial(calculate_indicators, params=params)

        # Mapear a símbolos en paralelo
        results = pool.map(func, symbols)

    return results

# Usar
symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
results = parallel_backtest(symbols, {"lookback": 20}, n_processes=4)
```

**Regla 19.4 — NumPy Broadcasting**

Claude DEBE eliminar bucles con NumPy:
- Operaciones vectoriales

```python
import numpy as np

# ❌ MAL - Loop lento
def calculate_returns_loop(prices):
    returns = np.zeros(len(prices) - 1)
    for i in range(len(prices) - 1):
        returns[i] = (prices[i + 1] - prices[i]) / prices[i]
    return returns

# ✅ BIEN - Vectorizado
def calculate_returns_vectorized(prices: np.ndarray) -> np.ndarray:
    """Returns calculados con broadcasting - 100x más rápido."""
    return np.diff(prices) / prices[:-1]

# También para operaciones complejas
def calculate_volatility_matrix(returns_matrix: np.ndarray) -> np.ndarray:
    """Matriz de covarianza - broadcasting."""
    # returns_matrix shape: (n_observations, n_assets)
    demeaned = returns_matrix - returns_matrix.mean(axis=0)
    cov_matrix = (demeaned.T @ demeaned) / len(returns_matrix)
    return cov_matrix
```

**Regla 19.5 — Pandas Memory Usage**

Claude DEBE usar tipos adecuados en Pandas:
- float32 en vez de float64
- category para strings repetidos

```python
def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Reducir huella de RAM."""
    memory_before = df.memory_usage(deep=True).sum() / 1024**2  # MB

    # Downcast integers
    int_cols = df.select_dtypes(include=['int64']).columns
    df[int_cols] = df[int_cols].apply(pd.to_numeric, downcast='integer')

    # Downcast floats
    float_cols = df.select_dtypes(include=['float64']).columns
    df[float_cols] = df[float_cols].apply(pd.to_numeric, downcast='float')

    # Convert strings to category si pocos valores únicos
    str_cols = df.select_dtypes(include=['object']).columns
    for col in str_cols:
        if df[col].nunique() / len(df[col]) < 0.5:
            df[col] = df[col].astype('category')

    memory_after = df.memory_usage(deep=True).sum() / 1024**2  # MB

    print(f"Memory: {memory_before:.1f} MB → {memory_after:.1f} MB")
    return df

# Resultado típico: 100 MB → 30 MB
```

**Regla 19.6 — Queue-Based Communication**

Claude DEBE comunicar procesos/threads con Queue:
- Nunca compartir estado mutable global
- Usar queue.Queue o asyncio.Queue

```python
import asyncio
from asyncio import Queue

async def market_data_producer(queue: Queue, symbols: List[str]):
    """Producer - pone datos en queue."""
    while True:
        for symbol in symbols:
            tick = await get_tick(symbol)
            await queue.put(tick)
        await asyncio.sleep(1)

async def strategy_consumer(queue: Queue):
    """Consumer - procesa datos de queue."""
    while True:
        tick = await queue.get()
        signal = generate_signal(tick)
        if signal:
            await execute_trade(signal)
        queue.task_done()

async def main():
    queue = Queue()

    # Producer y consumer coroutines
    producer = asyncio.create_task(market_data_producer(queue, ["AAPL", "MSFT"]))
    consumer = asyncio.create_task(strategy_consumer(queue))

    # Esperar
    await asyncio.gather(producer, consumer)
```

**Regla 19.7 — Numba JIT**

Claude DEBE compilar funciones críticas con @jit:
- Velocidad cercana a C++

```python
from numba import jit
import numpy as np

@jit(nopython=True)
def calculate_kelly_numba(
    returns: np.ndarray,
    win_rate: float
) -> float:
    """Kelly criterion compilado con Numba."""
    wins = returns[returns > 0]
    losses = returns[returns < 0]

    if len(wins) == 0 or len(losses) == 0:
        return 0.0

    avg_win = wins.mean()
    avg_loss = abs(losses.mean())

    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

    # Half-Kelly, max 25%
    return max(0.0, min(kelly * 0.5, 0.25))

# Primera llamada: lenta (compilación)
# Llamadas subsiguientes: 100x más rápido
kelly = calculate_kelly_numba(returns, 0.55)
```

**Regla 19.8 — Zero-Copy**

Claude DEBE usar memoryview para blobs binarios:
- Evitar copias innecesarias

```python
def parse_market_data(data: bytes) -> List[Tick]:
    """Parse market data sin copias."""
    # Crear memoryview - sin copiar
    mv = memoryview(data)

    ticks = []
    offset = 0

    # Leer sin copiar
    while offset < len(mv):
        symbol_len = mv[offset]
        offset += 1

        symbol = bytes(mv[offset:offset + symbol_len]).decode()
        offset += symbol_len

        price = int.from_bytes(mv[offset:offset + 4], 'big')
        offset += 4

        volume = int.from_bytes(mv[offset:offset + 4], 'big')
        offset += 4

        ticks.append(Tick(symbol, price, volume))

    return ticks

# Sin memoryview: crea bytes nuevos para cada campo
# Con memoryview: zero-copy, solo lectura
```

**Regla 19.9 — Local Variables**

Claude DEBE asignar funciones globales a locales en bucles críticos:

```python
def fast_loop_calculation(values: List[float]) -> List[float]:
    """Bucle optimizado con variables locales."""
    result = []

    # Asignar a locals - más rápido que lookup global
    append = result.append
    sqrt = math.sqrt
    exp = math.exp

    for value in values:
        # Usar locals en lugar de math.sqrt, math.exp cada vez
        calculated = sqrt(value) * exp(value / 10)
        append(calculated)

    return result
```

**Regla 19.10 — Lazy Evaluation**

Claude DEBE calcular indicadores solo cuando se pidan:
- NO pre-calcular todo si no se usa

```python
class LazyIndicators:
    """Indicadores calculados bajo demanda."""

    def __init__(self, prices: pd.Series):
        self.prices = prices
        self._sma20 = None
        self._volatility = None

    @property
    def sma20(self) -> pd.Series:
        """SMA20 - calculado solo cuando se pide."""
        if self._sma20 is None:
            self._sma20 = self.prices.rolling(20).mean()
        return self._sma20

    @property
    def volatility(self) -> pd.Series:
        """Volatilidad - calculada solo cuando se pide."""
        if self._volatility is None:
            self._volatility = self.prices.pct_change().rolling(20).std()
        return self._volatility

# Usar
indicators = LazyIndicators(prices)
# SMA no se calcula aún
sma = indicators.sma20  # Se calcula ahora
# Volatility no se calcula aún
```

**Regla 19.11 — Slots**

Claude DEBE usar `__slots__` para clases con millones de instancias:

```python
class Tick:
    """Tick con __slots__ - menos RAM, más rápido."""
    __slots__ = ['symbol', 'price', 'volume', 'timestamp']

    def __init__(self, symbol: str, price: float, volume: float, timestamp: datetime):
        self.symbol = symbol
        self.price = price
        self.volume = volume
        self.timestamp = timestamp

# Sin __slots__: cada instancia tiene __dict__ (overhead)
# Con __slots__: atributos fijos, sin overhead
# Ahorro: ~40% RAM, ~10% más rápido acceso
```

**Regla 19.12 — Cython Modules**

Claude DEBE mover código crítico a Cython si Python puro es muy lento:

```python
# indicators.pyx - código Cython
def cython_ema(double[:] prices, double alpha):
    """EMA compilado con Cython."""
    cdef int i
    cdef double ema = prices[0]
    cdef int n = len(prices)

    result = np.zeros(n)
    result[0] = ema

    for i in range(1, n):
        ema = alpha * prices[i] + (1 - alpha) * ema
        result[i] = ema

    return result

# Compilar: python setup.py build_ext --inplace
# Usar como módulo normal
from indicators import cython_ema

# 10-100x más rápido que Python puro
```

**Regla 19.13 — UVLoop**

Claude DEBE usar uvloop para AsyncIO:
- Reemplazo del event loop por defecto
- Mayor velocidad

```python
import asyncio
import uvloop

# Usar uvloop en lugar de asyncio default
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

async def main():
    # Código async normal, pero más rápido
    await fetch_data()

asyncio.run(main())

# Speedup: 2-4x en operaciones I/O intensivas
```

**Regla 19.14 — Cache con LRU**

Claude DEBE usar @functools.lru_cache para funciones puras repetitivas:

```python
from functools import lru_cache

@lru_cache(maxsize=1024)
def calculate_historical_volatility(symbol: str, period: int) -> float:
    """Volatilidad histórica - cacheado."""
    prices = fetch_prices(symbol)
    returns = prices.pct_change()
    return returns.rolling(period).std().iloc[-1]

# Primera llamada: lento
vol = calculate_historical_volatility("AAPL", 20)

# Llamadas subsiguientes: instantáneo (cache)
vol = calculate_historical_volatility("AAPL", 20)
```

**Regla 19.15 — Connection Pooling**

Claude DEBE reutilizar conexiones TCP:
- HTTP Keep-Alive
- El handshake SSL es costoso

```python
import aiohttp

async def main():
    # Session con connection pooling
    async with aiohttp.ClientSession() as session:
        # Reutiliza conexiones
        for i in range(100):
            async with session.get("https://api.example.com/data") as resp:
                data = await resp.json()
                process(data)

# Sin pooling: 100 handshakes SSL = 10-20 segundos
# Con pooling: 1 handshake = 1 segundo
```
