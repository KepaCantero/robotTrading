# 📘 22. Fluent Python - Advanced Python Idioms for Trading

**Libro:** Fluent Python (2nd Edition) - Luciano Ramalho
**Objetivo:** Dominar Python idiomatic para sistemas de trading de alto rendimiento

## 🎯 Resumen Ejecutivo

Este libro es esencial para escribir código Python que sea:
- **Más rápido** (optimizaciones a nivel de lenguaje)
- **Más seguro** (inmutabilidad, type hints)
- **Más mantenible** (código limpio y pythonic)

Claude Code DEBE aplicar estas reglas en todo el código de trading.

---

## 📋 Las 15 Reglas Críticas para Claude Code

### 1. `__slots__` para Ticks (Reduce RAM 40%)

```python
# ❌ MAL: Usa __dict__ dinámico (más memoria)
class Tick:
    def __init__(self, symbol, price, volume, timestamp):
        self.symbol = symbol
        self.price = price
        self.volume = volume
        self.timestamp = timestamp

# ✅ BIEN: Usa __slots__ (más rápido y menos memoria)
class Tick:
    __slots__ = ['symbol', 'price', 'volume', 'timestamp']

    def __init__(self, symbol, price, volume, timestamp):
        self.symbol = symbol
        self.price = price
        self.volume = volume
        self.timestamp = timestamp

# Resultado: 40% menos RAM, acceso a atributos más rápido
```

**Regla para Claude:** TODAS las clases que se instancien millones de veces (Tick, Quote, Order) DEBEN usar `__slots__`.

---

### 2. `dataclass(frozen=True)` para Señales Inmutables

```python
from dataclasses import dataclass

# ✅ BIEN: Señal inmutable (segura para concurrencia)
@dataclass(frozen=True, slots=True)
class TradingSignal:
    symbol: str
    direction: str  # 'BUY' or 'SELL'
    confidence: float
    timestamp: datetime

# Intentar modificar → error (seguro)
signal = TradingSignal('AAPL', 'BUY', 0.85, datetime.now())
signal.confidence = 0.90  # ❌ FrozenInstanceError
```

**Regla para Claude:** Las señales de trading DEBEN ser inmutables para evitar bugs en sistemas concurrentes.

---

### 3. `typing.Protocol` para Interfaces de Brokers

```python
from typing import Protocol

# ✅ BIEN: Protocol (structural typing)
class BrokerProtocol(Protocol):
    def place_order(self, order: Order) -> OrderResult: ...
    def get_positions(self) -> dict[str, Position]: ...
    def get_account(self) -> AccountInfo: ...

# Cualquier clase con estos métodos es un Broker (duck typing estricto)
class BinanceBroker:
    def place_order(self, order: Order) -> OrderResult: ...
    def get_positions(self) -> dict[str, Position]: ...
    def get_account(self) -> AccountInfo: ...

# No necesita herencia explícita
def execute_with_broker(broker: BrokerProtocol, order: Order):
    return broker.place_order(order)
```

**Regla para Claude:** USAR `Protocol` en lugar de ABC para interfaces de brokers/adapters.

---

### 4. Generadores (`yield`) para Streams de Datos

```python
# ❌ MAL: Carga todo en RAM
def process_ticks(file_path):
    with open(file_path) as f:
        return [Tick.from_json(line) for line in f]

# ✅ BIEN: Generador (un tick a la vez)
def tick_stream(file_path) -> Iterator[Tick]:
    with open(file_path) as f:
        for line in f:
            yield Tick.from_json(line)

# Uso: procesa millones de ticks sin saturar RAM
for tick in tick_stream('large_file.csv'):
    process_tick(tick)
```

**Regla para Claude:** USAR generadores para procesamiento de datos históricos y streams de WebSocket.

---

### 5. ABC para Estrategias Abstractas

```python
from abc import ABC, abstractmethod

# ✅ BIEN: Estrategia base abstracta
class Strategy(ABC):
    @abstractmethod
    def generate_signal(self, market_data: MarketData) -> TradingSignal:
        """Genera señal de trading."""
        pass

    @abstractmethod
    def validate_signal(self, signal: TradingSignal) -> bool:
        """Valida señal antes de enviar."""
        pass

# Obliga a implementar métodos
class MomentumStrategy(Strategy):
    def generate_signal(self, market_data: MarketData) -> TradingSignal:
        # Implementación...
        pass

    def validate_signal(self, signal: TradingSignal) -> bool:
        return signal.confidence > 0.7
```

**Regla para Claude:** DEFINIR clases base abstractas para todas las estrategias.

---

### 6. Pattern Matching (`match/case`) para Estados de Órdenes

```python
# Python 3.10+
def handle_order_event(event: OrderEvent):
    match event.status:
        case 'FILLED':
            log_trade_fill(event)
            update_position(event)
        case 'PARTIALLY_FILLED':
            log_partial_fill(event)
        case 'CANCELLED':
            handle_cancellation(event)
        case 'REJECTED':
            alert_rejection(event)
        case _:
            logger.warning(f"Unknown status: {event.status}")

# Más limpio que múltiples if/elif
```

**Regla para Claude:** USAR `match/case` para manejar estados de órdenes y eventos de trading.

---

### 7. Dict Comprehensions para Mapear IDs

```python
# ✅ BIEN: Dict comprehension (pythonic)
order_map = {
    order.order_id: order
    for order in orders
    if order.status == 'OPEN'
}

# Más limpio que:
# order_map = {}
# for order in orders:
#     if order.status == 'OPEN':
#         order_map[order.order_id] = order
```

**Regla para Claude:** USAR dict comprehensions para transformaciones de datos.

---

### 8. Context Managers para Locks de Trading

```python
from contextlib import contextmanager

@contextmanager
def trading_lock(symbol: str):
    """Lock para evitar operaciones concurrentes en mismo símbolo."""
    lock = locks[symbol]
    lock.acquire()
    try:
        yield
    finally:
        lock.release()

# Uso:
with trading_lock('AAPL'):
    # Operaciones atómicas en AAPL
    position = get_position('AAPL')
    position += new_order
    save_position(position)
# Lock liberado automáticamente
```

**Regla para Claude:** USAR context managers para gestión de recursos (locks, conexiones, transacciones).

---

### 9. Operator Overloading para Position (+, -)

```python
@dataclass
class Position:
    symbol: str
    quantity: Decimal
    avg_price: Decimal

    def __add__(self, other: Position) -> Position:
        """Suma posiciones (promedio ponderado)."""
        if self.symbol != other.symbol:
            raise ValueError("Cannot add different symbols")

        total_cost = (self.quantity * self.avg_price +
                     other.quantity * other.avg_price)
        total_qty = self.quantity + other.quantity

        return Position(
            symbol=self.symbol,
            quantity=total_qty,
            avg_price=total_cost / total_qty if total_qty != 0 else Decimal('0')
        )

# Uso natural:
pos1 = Position('AAPL', Decimal('100'), Decimal('150'))
pos2 = Position('AAPL', Decimal('50'), Decimal('155'))
combined = pos1 + pos2  # Position('AAPL', 150, 151.67)
```

**Regla para Claude:** SOBRECARGAR operadores para clases matemáticas (Position, Money, Price).

---

### 10. `__repr__` para Debugging

```python
@dataclass
class Order:
    order_id: str
    symbol: str
    quantity: Decimal
    price: Decimal

    def __repr__(self) -> str:
        return (f"Order(id={self.order_id[:8]}, "
                f"{self.symbol}, qty={self.quantity}, "
                f"price={self.price})")

# Logs claros:
# Order(id=abc12345, AAPL, qty=100, price=150.25)
# vs <__main__.Order object at 0x7f8d4c2b3d10>
```

**Regla para Claude:** IMPLEMENTAR `__repr__` en todas las clases principales para logging.

---

### 11. Type Hinting Estricto (`Final`, `Literal`)

```python
from typing import Final, Literal

# Constantes (no se pueden reasignar)
MAX_POSITION_SIZE: Final = Decimal('0.20')  # 20% max
DEFAULT_STOP_LOSS: Final = Decimal('0.05')  # 5%

# Literales (solo estos valores permitidos)
OrderSide = Literal['BUY', 'SELL', 'SHORT']
OrderType = Literal['MARKET', 'LIMIT', 'STOP_LIMIT']

def place_order(
    symbol: str,
    side: OrderSide,  # Solo 'BUY', 'SELL', 'SHORT'
    order_type: OrderType,  # Solo 'MARKET', 'LIMIT', 'STOP_LIMIT'
    quantity: Decimal
) -> str:
    ...
```

**Regla para Claude:** USAR type hints estrictos en todo el código. Validar con `mypy`.

---

### 12. `defaultdict` para Portafolios

```python
from collections import defaultdict

# ✅ BIEN: defaultdict (inicialización automática)
portfolio = defaultdict(Position)

# No necesitas check if exists
portfolio['AAPL'].quantity += Decimal('100')  # Crea Position si no existe
portfolio['TSLA'].quantity += Decimal('50')
```

**Regla para Claude:** USAR `defaultdict` para colecciones que necesitan inicialización automática.

---

### 13. `namedtuple` para Registros Históricos

```python
from collections import namedtuple

# Estructura ligera para registros inmutables
TradeRecord = namedtuple('TradeRecord', [
    'timestamp',
    'symbol',
    'side',
    'quantity',
    'price',
    'commission'
])

# Más eficiente que dataclass para datos simples
record = TradeRecord(
    timestamp=datetime.now(),
    symbol='AAPL',
    side='BUY',
    quantity=Decimal('100'),
    price=Decimal('150'),
    commission=Decimal('1.5')
)
```

**Regla para Claude:** USAR `namedtuple` para registros históricos inmutables ligeros.

---

### 14. Módulo `bisect` para Listas Ordenadas O(log n)

```python
import bisect

# Mantener lista de niveles de precio ordenada
price_levels = [100.0, 105.0, 110.0, 115.0]

# Inserción eficiente (O(log n))
new_level = 107.5
bisect.insort(price_levels, new_level)
# [100.0, 105.0, 107.5, 110.0, 115.0]

# Búsqueda eficiente
idx = bisect.bisect_left(price_levels, 108.0)
# idx = 3 (price_levels[3] = 110.0 es el primer >= 108.0)
```

**Regla para Claude:** USAR `bisect` para mantener listas ordenadas (order book, price levels).

---

### 15. Módulo `heapq` para Colas de Prioridad

```python
import heapq

# Cola de prioridad para órdenes (por precio)
buy_orders = []
heapq.heappush(buy_orders, (150.0, 'order_1'))
heapq.heappush(buy_orders, (155.0, 'order_2'))
heapq.heappush(buy_orders, (148.0, 'order_3'))

# Obtener orden con precio más alto (max-heap: usar precios negativos)
best_price = -heapq.heappop(buy_orders)[0]
# 155.0
```

**Regla para Claude:** USAR `heapq` para colas de prioridad (mejor precio, órdenes urgentes).

---

## 🚀 Bonus: Walrus Operator `:=` (Python 3.8+)

```python
# Asignación en expresión
while (tick := get_next_tick()) is not None:
    process_tick(tick)

# Más limpio que:
# while True:
#     tick = get_next_tick()
#     if tick is None:
#         break
#     process_tick(tick)
```

---

## 📊 Checklist para Claude Code

Antes de entregar código, verificar:

- [ ] Clases高频usadas usan `__slots__`
- [ ] Señales inmutables usan `@dataclass(frozen=True)`
- [ ] Interfaces usan `Protocol` en lugar de ABC
- [ ] Streams de datos usan generadores (`yield`)
- [ ] Estrategias heredan de ABC con métodos abstractos
- [ ] Estados de órdenes usan `match/case`
- [ ] Transformaciones de datos usan comprehensions
- [ ] Locks usan context managers (`with`)
- [ ] Clases matemáticas tienen operator overloading
- [ ] Clases principales tienen `__repr__` descriptivo
- [ ] Todo tiene type hints estrictos
- [ ] Colecciones con inicialización automática usan `defaultdict`
- [ ] Registros inmutables usan `namedtuple`
- [ ] Listas ordenadas usan `bisect`
- [ ] Colas de prioridad usan `heapq`

---

## 🎓 Aplicación en Trading

### Ejemplo Completo: Sistema de Órdenes

```python
from dataclasses import dataclass
from collections import defaultdict
from typing import Protocol, Iterator
from enum import Enum
import bisect
import heapq

class Side(Enum):
    BUY = 'BUY'
    SELL = 'SELL'

@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    symbol: str
    side: Side
    quantity: Decimal
    price: Decimal

    def __repr__(self) -> str:
        return f"Order({self.order_id[:8]}, {self.symbol}, {self.side.value}, {self.quantity})"

class BrokerProtocol(Protocol):
    def place_order(self, order: Order) -> bool: ...

class OrderBook:
    def __init__(self):
        self.bids: list[tuple[Decimal, str]] = []  # Max-heap
        self.asks: list[tuple[Decimal, str]] = []  # Min-heap

    def add_bid(self, price: Decimal, order_id: str):
        heapq.heappush(self.bids, (-float(price), order_id))

    def add_ask(self, price: Decimal, order_id: str):
        heapq.heappush(self.asks, (float(price), order_id))

class Portfolio:
    def __init__(self):
        self.positions = defaultdict(Position)

    def __iadd__(self, trade: Trade):
        self.positions[trade.symbol] += trade.position
        return self
```

---

## 📚 Referencias

- **Libro:** Fluent Python (2nd Edition) - Luciano Ramalho
- **Capítulos clave:**
  - Cap 1: Python Data Model
  - Cap 5: Dataclass Builders
  - Cap 7: Function Decorators
  - Cap 9: Pythonic Objects
  - Cap 11: Interfaces (Protocol)
  - Cap 14: Iterators, Generators
  - Cap 16: Coroutines

---

**Última actualización:** 2026-01-28
**Version:** 2.1 (Completado con ejemplos prácticos)


---

## 💼 Ejemplos Prácticos de Trading

### Ejemplo 1: Orden con slots + frozen

```python
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class Side(Enum):
    BUY = 'BUY'
    SELL = 'SELL'

@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    symbol: str
    side: Side
    quantity: Decimal
    price: Decimal
```

### Ejemplo 2: Protocol para Brokers

```python
from typing import Protocol

class BrokerProtocol(Protocol):
    def place_order(self, order): pass
    def cancel_order(self, order_id): pass

class BinanceBroker:
    def place_order(self, order): pass
    def cancel_order(self, order_id): pass
```

### Ejemplo 3: Match/Case para Estados

```python
from enum import Enum

class Status(Enum):
    FILLED = 'FILLED'
    CANCELLED = 'CANCELLED'

def handle(status):
    match status:
        case Status.FILLED:
            return 'Update position'
        case Status.CANCELLED:
            return 'Log cancellation'
```


---

## 💼 Ejemplos Prácticos de Trading

### Ejemplo 1: Orden con slots + frozen

```python
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class Side(Enum):
    BUY = 'BUY'
    SELL = 'SELL'

@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    symbol: str
    side: Side
    quantity: Decimal
    price: Decimal
```

### Ejemplo 2: Protocol para Brokers

```python
from typing import Protocol

class BrokerProtocol(Protocol):
    def place_order(self, order): pass
    def cancel_order(self, order_id): pass

class BinanceBroker:
    def place_order(self, order): pass
    def cancel_order(self, order_id): pass
```

### Ejemplo 3: Match/Case para Estados

```python
from enum import Enum

class Status(Enum):
    FILLED = 'FILLED'
    CANCELLED = 'CANCELLED'

def handle(status):
    match status:
        case Status.FILLED:
            return 'Update position'
        case Status.CANCELLED:
            return 'Log cancellation'
```
