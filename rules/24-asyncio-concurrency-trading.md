# 📘 24. Python Concurrency with AsyncIO - Trading Systems

**Libro:** Python Concurrency with asyncio - Matthew Fowler
**Objetivo:** Manejar cientos de WebSockets y APIs simultáneamente sin bloqueos

## 🎯 Resumen Ejecutivo

Claude Code DEBE usar AsyncIO para:
1. **Múltiples WebSockets** (feeds de datos de múltiples exchanges)
2. **No bloquear** el event loop principal
3. **Manejar rate limits** de APIs eficientemente
4. **Graceful shutdown** (cerrar todo limpiamente)

---

## 📋 Las 15 Reglas Críticas para Claude Code

### 1. AsyncIO para WebSockets (No `time.sleep`/`requests`)

```python
import asyncio
import aiohttp

# ❌ MAL: Bloquea el event loop
def fetch_price_sync(symbol):
    time.sleep(1)  # ← BLOQUEA TODO
    response = requests.get(f"https://api.binance.com/ticker/{symbol}")
    return response.json()

# ✅ BIEN: Asíncrono (no bloquea)
async def fetch_price_async(symbol: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.binance.com/ticker/{symbol}") as resp:
            return await resp.json()
```

**Regla para Claude:** ESTÁ PROHIBIDO usar `requests`, `time.sleep()`, u operaciones bloqueantes en código async.

---

### 2. `asyncio.shield` para Órdenes Críticas

```python
async def place_critical_order(order: Order) -> OrderResult:
    """Orden que DEBE ejecutarse incluso si el bot se cancela."""

    # Shield protege la tarea de cancelación externa
    result = await asyncio.shield(_execute_order(order))
    return result

async def _execute_order(order: Order) -> OrderResult:
    # Ejecuta la orden
    async with aiohttp.ClientSession() as session:
        # ... lógica de envío ...
        pass

# Aunque canceles el bot, la orden se intenta completar
```

**Regla para Claude:** USAR `asyncio.shield()` para tareas críticas que no deben interrumpirse.

---

### 3. uvloop (2-4x Más Rápido)

```python
import asyncio
import uvloop

# Instalar uvloop: pip install uvloop
# Reemplazar event loop por defecto (2-4x más rápido)
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Ahora todas las async ops usan uvloop automáticamente
async def main():
    # ... código async ...
    pass

asyncio.run(main())
```

**Regla para Claude:** USAR uvloop SIEMPRE que sea posible (Unix/Linux/macOS).

---

### 4. Task Groups (Python 3.11+)

```python
# Python 3.11+
async def trade_multiple_symbols(symbols: list[str]):
    """Ejecuta estrategias para múltiples símbolos."""

    async with asyncio.TaskGroup() as tg:
        tasks = []
        for symbol in symbols:
            task = tg.create_task(strategy_worker(symbol))
            tasks.append(task)

    # Si una tarea falla, las otras se cancelan limpiamente
    # Task Group maneja excepciones automáticamente

# vs Python 3.10-: asyncio.gather() con manejo manual
```

**Regla para Claude:** USAR `asyncio.TaskGroup` (Python 3.11+) para manejar múltiples tareas concurrentes.

---

### 5. Semáforos para Rate Limits

```python
class BinanceAPI:
    """Cliente con rate limiting."""

    def __init__(self, max_requests_per_second: int = 10):
        self.semaphore = asyncio.Semaphore(max_requests_per_second)

    async def get_ticker(self, symbol: str) -> dict:
        """Respecta rate limits."""
        async with self.semaphore:
            # Máximo N requests simultáneos
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.binance.com/ticker/{symbol}") as resp:
                    return await resp.json()

# Uso:
api = BinanceAPI(max_requests_per_second=10)
tasks = [api.get_ticker(symbol) for symbol in symbols]
results = await asyncio.gather(*tasks)
# Respeta rate limits automáticamente
```

**Regla para Claude:** USAR `asyncio.Semaphore` para respetar rate limits de APIs.

---

### 6. Timeouts con `asyncio.wait_for`

```python
async def safe_api_call(url: str, timeout: float = 5.0) -> dict:
    """Llamada a API con timeout obligatorio."""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                # Timeout obligatorio
                return await asyncio.wait_for(resp.json(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Timeout calling {url}")
        raise
```

**Regla para Claude:** TODAS las llamadas a API DEBEN tener `asyncio.wait_for()` con timeout.

---

### 7. `asyncio.Queue` para Desacoplo

```python
# Producer (data feed)
async def websocket_consumer(queue: asyncio.Queue):
    """Consume WebSocket y pone en queue."""
    async with websockets.connect('wss://stream.binance.com/ws') as ws:
        async for message in ws:
            await queue.put(message)  # No bloquea

# Consumer (strategy)
async def strategy_worker(queue: asyncio.Queue):
    """Procesa mensajes de la queue."""
    while True:
        message = await queue.get()  # Espera si está vacía
        process_message(message)
        queue.task_done()

# Desacopla ingest de datos de procesamiento
```

**Regla para Claude:** USAR `asyncio.Queue` para desacoplar productores y consumidores.

---

### 8. `run_in_executor` para Funciones Pesadas

```python
def heavy_computation(data: np.ndarray) -> float:
    """Función que NO es async (bloqueante)."""
    # ... cálculos pesados ...
    return result

async def async_wrapper(data: np.ndarray) -> float:
    """Wrapper async para función bloqueante."""
    loop = asyncio.get_event_loop()

    # Ejecuta en thread pool (no bloquea event loop)
    result = await loop.run_in_executor(None, heavy_computation, data)
    return result

# Ahora puedes llamarla en código async sin bloquear
```

**Regla para Claude:** USAR `run_in_executor()` para funciones pesadas que no son async.

---

### 9. `task.add_done_callback` para Errores

```python
async def background_task():
    """Tarea en segundo plano."""
    await some_long_operation()

task = asyncio.create_task(background_task())

# Callback para manejar errores silenciosos
def handle_task_error(task: asyncio.Task):
    try:
        task.result()  # Lanza excepción si hubo error
    except Exception as e:
        logger.error(f"Background task failed: {e}")

task.add_done_callback(handle_task_error)

# Ahora errores no se pierden en silencio
```

**Regla para Claude:** AÑADIR `add_done_callback()` a tareas en segundo plano para capturar errores.

---

### 10. Heartbeats Asíncronos

```python
async def websocket_with_heartbeat(ws_url: str):
    """WebSocket con ping automático."""

    async with websockets.connect(ws_url) as ws:
        # Tarea de heartbeat
        async def ping_loop():
            while True:
                await asyncio.sleep(30)  # Ping cada 30s
                await ws.ping()

        ping_task = asyncio.create_task(ping_loop())

        # Recibir mensajes
        async for message in ws:
            process_message(message)

        # Al salir, cancelar heartbeat
        ping_task.cancel()
```

**Regla para Claude:** IMPLEMENTAR heartbeats para mantener conexiones WebSocket vivas.

---

### 11. Cancelación Limpia (Graceful Shutdown)

```python
import signal

class TradingBot:
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.tasks = []

    async def run(self):
        """Loop principal."""

        # Manejar SIGINT (Ctrl+C)
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT, self._signal_handler)

        # Iniciar tareas
        self.tasks = [
            asyncio.create_task(self.websocket_consumer()),
            asyncio.create_task(self.strategy_worker()),
        ]

        # Esperar señal de shutdown
        await self.shutdown_event.wait()

        # Cerrar limpiamente
        await self._graceful_shutdown()

    def _signal_handler(self):
        """Manejador de SIGINT."""
        logger.info("Received shutdown signal")
        self.shutdown_event.set()

    async def _graceful_shutdown(self):
        """Cancela todas las tareas y cierra conexiones."""
        logger.info("Shutting down gracefully...")

        # Cancelar tareas
        for task in self.tasks:
            task.cancel()

        # Esperar que terminen
        await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("Shutdown complete")
```

**Regla para Claude:** IMPLEMENTAR graceful shutdown que cierre posiciones y conexiones limpiamente.

---

### 12. Priorización de Tareas

```python
import heapq

class PriorityQueue:
    """Cola con prioridad para eventos."""

    def __init__(self):
        self.queue = []
        self.counter = 0

    async def put(self, priority: int, item):
        """Pone item con prioridad (menor = más urgente)."""
        heapq.heappush(self.queue, (priority, self.counter, item))
        self.counter += 1

    async def get(self):
        """Obtiene item más urgente."""
        return heapq.heappop(self.queue)[2]

# Uso:
queue = PriorityQueue()

# Stop loss tiene prioridad 0 (máxima urgencia)
await queue.put(0, stop_loss_order)

# Análisis tiene prioridad 10 (menos urgente)
await queue.put(10, analysis_task)

# Procesa en orden de prioridad
```

**Regla para Claude:** USAR colas prioritarias para eventos críticos (stop loss, market close).

---

### 13. orjson para JSON Streaming

```python
import orjson  # pip install orjson

# Más rápido que json estándar (para WebSocket streams)

async def websocket_parser(ws_url: str):
    """Parsea mensajes JSON de WebSocket."""
    async with websockets.connect(ws_url) as ws:
        async for message in ws:
            # orjson es más rápido que json.loads
            data = orjson.loads(message)
            process_data(data)
```

**Regla para Claude:** USAR `orjson` para parsing de JSON en streams de alta velocidad.

---

### 14. Backpressure Handling

```python
class BackpressureQueue(asyncio.Queue):
    """Queue con límite para evitar saturación."""

    def __init__(self, maxsize: int = 1000):
        super().__init__(maxsize=maxsize)

    async def put(self, item):
        """Si está llena, descarta mensajes viejos."""
        if self.full():
            # Descartar mensaje más viejo
            self.get_nowait()
            logger.warning("Queue full, dropping oldest message")

        await super().put(item)

# Evita que el bot se quede atrás procesando datos viejos
```

**Regla para Claude:** IMPLEMENTAR backpressure para descartar datos viejos si el procesamiento es lento.

---

### 15. Async Safety: Diccionarios Atómicos

```python
import asyncio

class ThreadSafePortfolio:
    """Portfolio seguro para concurrencia."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._positions = {}

    async def update_position(self, symbol: str, quantity: float):
        """Actualiza posición de forma atómica."""
        async with self._lock:  # Solo una tarea a la vez
            if symbol in self._positions:
                self._positions[symbol] += quantity
            else:
                self._positions[symbol] = quantity

    async def get_position(self, symbol: str) -> float:
        """Lee posición."""
        async with self._lock:
            return self._positions.get(symbol, 0.0)
```

**Regla para Claude:** USAR `asyncio.Lock()` para proteger estado compartido en código async.

---

## 🎓 Ejemplo Completo: Sistema AsyncIO

```python
import asyncio
import signal
import aiohttp
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TradingConfig:
    symbols: list[str]
    max_concurrent_requests: int = 10
    api_timeout: float = 5.0

class AsyncTradingBot:
    """Bot de trading asíncrono."""

    def __init__(self, config: TradingConfig):
        self.config = config
        self.shutdown_event = asyncio.Event()
        self.semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        self.tasks = []

    async def run(self):
        """Loop principal."""
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT, self._signal_handler)

        logger.info("Starting bot...")

        # Iniciar tareas
        self.tasks = [
            asyncio.create_task(self._market_data_feed()),
            asyncio.create_task(self._strategy_worker()),
        ]

        # Esperar shutdown
        await self.shutdown_event.wait()

        # Graceful shutdown
        await self._shutdown()

    def _signal_handler(self):
        """Handle SIGINT."""
        logger.info("Received shutdown signal")
        self.shutdown_event.set()

    async def _market_data_feed(self):
        """Feed de datos de mercado."""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._fetch_ticker(session, symbol)
                for symbol in self.config.symbols
            ]
            await asyncio.gather(*tasks)

    async def _fetch_ticker(self, session: aiohttp.ClientSession, symbol: str):
        """Obtiene ticker con rate limiting."""
        async with self.semaphore:  # Rate limiting
            try:
                async with session.get(
                    f"https://api.binance.com/ticker/{symbol}"
                ) as resp:
                    data = await asyncio.wait_for(
                        resp.json(),
                        timeout=self.config.api_timeout
                    )
                    logger.debug(f"{symbol}: {data['price']}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching {symbol}")
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")

    async def _strategy_worker(self):
        """Worker de estrategia."""
        while not self.shutdown_event.is_set():
            # ... lógica de estrategia ...
            await asyncio.sleep(1)

    async def _shutdown(self):
        """Cierra limpiamente."""
        logger.info("Shutting down...")

        # Cancelar tareas
        for task in self.tasks:
            task.cancel()

        # Esperar que terminen
        await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("Shutdown complete")

async def main():
    config = TradingConfig(symbols=['BTCUSDT', 'ETHUSDT'])
    bot = AsyncTradingBot(config)
    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())
```

---

## 📚 Referencias

- **Libro:** Python Concurrency with asyncio - Matthew Fowler
- **Librerías:**
  - `asyncio`: Librería estándar
  - `aiohttp`: Cliente HTTP async
  - `websockets`: WebSocket client
  - `uvloop`: Event loop ultrarrápido
  - `orjson`: JSON parser rápido

---

**Última actualización:** 2026-01-28
**Version:** 2.1 (Completado con ejemplos de websockets reales)


---

## 🔌 Ejemplos Reales de WebSockets de Exchanges

### Ejemplo 1: Binance WebSocket Manager

```python
import asyncio
import websockets
import json

class BinanceWebSocketManager:
    BASE_WS_URL = 'wss://stream.binance.com:9443/ws'
    
    async def connect(self, symbols):
        streams = [f'{s.lower()}@ticker' for s in symbols]
        url = f'{self.BASE_WS_URL}/{"/".join(streams)}'
        
        retry_count = 0
        while retry_count < 5:
            try:
                async with websockets.connect(url) as ws:
                    async for message in ws:
                        data = json.loads(message)
                        await self.process_message(data)
            except Exception:
                retry_count += 1
                await asyncio.sleep(2 ** retry_count)
```

### Ejemplo 2: Coinbase Order Book

```python
class CoinbaseOrderBook:
    async def connect(self, product_id):
        url = 'wss://ws-feed.exchange.coinbase.com'
        msg = {'type': 'subscribe', 'product_ids': [product_id]}
        
        async with websockets.connect(url) as ws:
            await ws.send(json.dumps(msg))
            async for message in ws:
                self.update_orderbook(json.loads(message))
```


---

## 🔌 Ejemplos Reales de WebSockets de Exchanges

### Ejemplo 1: Binance WebSocket Manager

```python
import asyncio
import websockets
import json

class BinanceWebSocketManager:
    BASE_WS_URL = 'wss://stream.binance.com:9443/ws'
    
    async def connect(self, symbols):
        streams = [f'{s.lower()}@ticker' for s in symbols]
        url = f'{self.BASE_WS_URL}/{"/".join(streams)}'
        
        retry_count = 0
        while retry_count < 5:
            try:
                async with websockets.connect(url) as ws:
                    async for message in ws:
                        data = json.loads(message)
                        await self.process_message(data)
            except Exception:
                retry_count += 1
                await asyncio.sleep(2 ** retry_count)
```

### Ejemplo 2: Coinbase Order Book

```python
class CoinbaseOrderBook:
    async def connect(self, product_id):
        url = 'wss://ws-feed.exchange.coinbase.com'
        msg = {'type': 'subscribe', 'product_ids': [product_id]}
        
        async with websockets.connect(url) as ws:
            await ws.send(json.dumps(msg))
            async for message in ws:
                self.update_orderbook(json.loads(message))
```
