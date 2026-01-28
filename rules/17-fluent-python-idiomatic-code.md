# 📗 17. "Fluent Python" - Luciano Ramalho

## REGLAS DE PYTHON IDIOMÁTICO PARA TRADING

**Regla 17.1 — Data Classes con slots**

Claude DEBE usar `@dataclass(slots=True)`:
- Ahorra memoria
- Escribe menos boilerplate

```python
from dataclasses import dataclass

@dataclass(slots=True)
class Tick:
    """Tick de mercado con slots - más rápido y menos memoria."""
    price: float
    volume: float
    timestamp: datetime

# Sin slots: cada instancia tiene __dict__
# Con slots: atributos fijos, más eficiente
```

**Regla 17.2 — Type Hinting Estricto**

Claude DEBE usar typing en todas las firmas:
- List, Optional, Protocol
- Validar con mypy en CI/CD

```python
from typing import List, Optional, Protocol

class SignalGenerator(Protocol):
    """Protocol para generadores de señales."""

    def generate(self, prices: List[float]) -> Optional[float]:
        """Generar señal o None si no hay señal."""
        ...

def execute_trades(
    signals: List[Signal],
    strategy: SignalGenerator
) -> List[Trade]:
    """Ejecutar trades basado en señales."""
    trades = []
    for signal in signals:
        sig_value = strategy.generate(signal.prices)
        if sig_value is not None:
            trades.append(execute(signal.symbol, sig_value))
    return trades
```

**Regla 17.3 — Context Managers**

Claude DEBE usar `with` para recursos:
- Conexiones a DB, sockets
- Crear propios con @contextmanager

```python
from contextlib import contextmanager

@contextmanager
def database_connection(db_url: str):
    """Context manager para conexión a DB."""
    conn = connect(db_url)
    try:
        yield conn
    finally:
        conn.close()

# Uso
with database_connection(settings.db_url) as conn:
    results = conn.execute("SELECT * FROM trades")
# conexión cerrada automáticamente
```

**Regla 17.4 — Generadores**

Claude DEBE usar `yield` para streams infinitos:
- NO devolver listas gigantes
- Procesar ticks sin llenar RAM

```python
from typing import Iterator

def tick_stream(symbol: str) -> Iterator[Tick]:
    """Generador de ticks infinitos - no llena RAM."""
    while True:
        tick = get_next_tick_websocket(symbol)
        yield tick

# Consumir generador
for tick in tick_stream("AAPL"):
    process_tick(tick)
    if tick.timestamp > market_close:
        break
```

**Regla 17.5 — Dunder Methods**

Claude DEBE implementar __repr__, __eq__, __len__:
- __repr__ para debugging
- __eq__ para comparaciones
- __len__ en colecciones

```python
@dataclass
class Portfolio:
    positions: Dict[str, Position]

    def __repr__(self) -> str:
        """Repr útil para debugging."""
        return f"Portfolio({len(self.positions)} positions, " \
               f"total_value=${self.total_value():.2f})"

    def __eq__(self, other) -> bool:
        """Comparación por contenido, no identidad."""
        if not isinstance(other, Portfolio):
            return False
        return self.positions == other.positions

    def __len__(self) -> int:
        """Número de posiciones."""
        return len(self.positions)
```

**Regla 17.6 — Decoradores**

Claude DEBE usar decoradores para lógica transversal:
- @retry, @log_execution_time, @validate_risk

```python
from functools import wraps
import time

def log_execution_time(func):
    """Decorador para medir tiempo de ejecución."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper

def retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorador para reintentar funciones."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator

# Uso
@log_execution_time
@retry(max_attempts=3)
def execute_order(order: Order) -> Execution:
    """Ejecutar orden con reintentos y logging."""
    return broker.execute(order)
```

**Regla 17.7 — Comprehensions**

Claude DEBE preferir comprehensions sobre map/filter:
- Pero NO anidar más de una vez (legibilidad)

```python
# ✅ BIEN - List comprehension
signals = [calc_signal(prices) for prices in price_lists if len(prices) > 20]

# ✅ BIEN - Dict comprehension
price_dict = {tick.symbol: tick.price for tick in ticks}

# ❌ MAL - Anidado (ilegible)
result = [[x * y for y in range(10)] for x in range(10)]  # Don't do this
```

**Regla 17.8 — First-Class Functions**

Claude DEBE pasar estrategias como funciones:
- El patrón Estrategia = funciones pasadas como argumentos

```python
def apply_strategy(
    prices: List[float],
    strategy: Callable[[List[float]], float]
) -> float:
    """Aplicar estrategia (función) a precios."""
    return strategy(prices)

# Diferentes estrategias como funciones
def momentum_strategy(prices: List[float]) -> float:
    return prices[-1] / prices[-252] - 1

def mean_reversion_strategy(prices: List[float]) -> float:
    return (prices[-1] - np.mean(prices[-20:])) / np.std(prices[-20:])

# Usar funciones como estrategias
signal = apply_strategy(prices, momentum_strategy)
```

**Regla 17.9 — Operator Overloading**

Claude DEBE sobrecargar operadores para clases financieras:
- __add__, __mul__ para Money o Position

```python
@dataclass
class Money:
    amount: Decimal
    currency: str

    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, factor: float) -> 'Money':
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __rmul__(self, factor: float) -> 'Money':
        return self.__mul__(factor)

# Uso natural
total = Money(100, "USD") + Money(50, "USD")
doubled = Money(100, "USD") * 2
```

**Regla 17.10 — Abstract Base Classes (ABC)**

Claude DEBE usar abc.ABC para interfaces:
- NO lanzar NotImplementedError manualmente

```python
from abc import ABC, abstractmethod

class Broker(ABC):
    """Interfaz abstracta para brokers."""

    @abstractmethod
    def execute_order(self, order: Order) -> Execution:
        """Ejecutar orden - debe implementar subclasses."""
        pass

    @abstractmethod
    def get_account_balance(self) -> Money:
        """Obtener balance - debe implementar subclasses."""
        pass

# Implementación concreta
class AlpacaBroker(Broker):
    def execute_order(self, order: Order) -> Execution:
        # Implementación real
        pass

    def get_account_balance(self) -> Money:
        # Implementación real
        pass
```

**Regla 17.11 — Properties**

Claude DEBE usar @property para valores calculados:
- NO getters estilo Java get_unrealized_pnl()

```python
@dataclass
class Position:
    symbol: str
    quantity: int
    entry_price: float
    current_price: float = None

    @property
    def unrealized_pnl(self) -> float:
        """PnL no realizado - valor calculado."""
        if self.current_price is None:
            return 0.0
        return (self.current_price - self.entry_price) * self.quantity

    @property
    def market_value(self) -> float:
        """Valor de mercado de la posición."""
        if self.current_price is None:
            return 0.0
        return self.current_price * self.quantity

# Uso natural
position = Position("AAPL", 100, 150.0, current_price=160.0)
print(position.unrealized_pnl)  # 1000.0 (NO position.get_unrealized_pnl())
```

**Regla 17.12 — F-Strings**

Claude DEBE usar f-strings para todo:
- Más rápidas y legibles

```python
# ✅ BIEN - f-string
symbol = "AAPL"
price = 150.0
message = f"Order executed: {symbol} @ ${price:.2f}"

# ❌ MAL - viejo estilo
message = "Order executed: {} @ ${:.2f}".format(symbol, price)
message = "Order executed: %s @ $%.2f" % (symbol, price)
```

**Regla 17.13 — Walrus Operator**

Claude DEBE usar := para asignar y chequear:
- Útil en bucles while que leen sockets

```python
# Walrus operator en while loop
while (tick := get_next_tick()) is not None:
    process_tick(tick)
    if should_stop:
        break

# Sin walrus (más verbose)
tick = get_next_tick()
while tick is not None:
    process_tick(tick)
    tick = get_next_tick()
```

**Regla 17.14 — Enum**

Claude DEBE usar enum.Enum para estados:
- Estados de órdenes (FILLED, OPEN) en lugar de strings mágicos

```python
from enum import Enum

class OrderStatus(Enum):
    """Estados de orden - no strings mágicos."""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

# Uso
order = Order(..., status=OrderStatus.OPEN)
if order.status == OrderStatus.FILLED:
    # Orden completada
    pass
```

**Regla 17.15 — Collections Avanzadas**

Claude DEBE dominar defaultdict, Counter, deque:
- defaultdict para valores por defecto
- Counter para contar frecuencias
- deque para buffers circulares

```python
from collections import defaultdict, Counter, deque

# defaultdict - aggregates por estrategia
strategy_returns = defaultdict(list)
strategy_returns["momentum"].append(0.05)
strategy_returns["momentum"].append(0.03)
# No need to check if key exists

# Counter - contar tipos de órdenes
order_types = Counter(["BUY", "SELL", "BUY", "BUY"])
print(order_types["BUY"])  # 3
print(order_types.most_common(1))  # [("BUY", 3)]

# deque - buffer circular de precios (máximo tamaño)
price_buffer = deque(maxlen=100)
for tick in tick_stream:
    price_buffer.append(tick.price)
    # Solo últimos 100 precios se mantienen
```
