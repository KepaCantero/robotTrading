# 📗 16. "Architecture Patterns with Python" - Harry Percival & Bob Gregory

## REGLAS DE DDD (DOMAIN-DRIVEN DESIGN) PARA TRADING

**Regla 16.1 — Dependency Inversion**

Claude DEBE invertir dependencias:
- Módulos de alto nivel (Estrategia) NO deben depender de bajo nivel (API Brokers)
- Ambos deben depender de abstracciones

```python
# ❌ MAL - Acoplamiento directo
class MomentumStrategy:
    def __init__(self):
        self.binance_api = BinanceAPI()  # Depende de implementación concreta

# ✅ BIEN - Dependency Inversion
class MomentumStrategy:
    def __init__(self, broker_repository: AbstractBrokerRepository):
        self.broker = broker_repository  # Depende de abstracción
```

**Regla 16.2 — Domain Model Purity**

Claude DEBE mantener el dominio puro:
- NO imports de frameworks externos en domain/
- NO imports de bases de datos en domain/
- NO imports de librerías de red en domain/
- Solo Python puro y dataclasses

```python
# ✅ BIEN - Domain model puro
from dataclasses import dataclass
from typing import List

@dataclass
class Order:
    """Orden de trading - modelo de dominio puro."""
    symbol: str
    quantity: int
    price: float
    side: str  # 'BUY' o 'SELL'

    def validate(self) -> bool:
        """Validación de negocio - sin dependencias externas."""
        return self.quantity > 0 and self.price > 0 and self.side in ['BUY', 'SELL']
```

**Regla 16.3 — Repository Pattern**

Claude DEBE usar Repository Pattern:
- NO queries SQL o llamadas HTTP en la estrategia
- Usar AbstractRepository.get_candles() y AbstractRepository.add_order()

```python
from abc import ABC, abstractmethod
from typing import List

# Abstract Repository (Port)
class AbstractCandleRepository(ABC):
    @abstractmethod
    def get_candles(self, symbol: str, start: datetime, end: datetime) -> List[Candle]:
        pass

# Concrete Repository (Adapter)
class PostgresCandleRepository(AbstractCandleRepository):
    def get_candles(self, symbol: str, start: datetime, end: datetime) -> List[Candle]:
        # SQL real oculto en el adaptador
        query = "SELECT * FROM candles WHERE symbol=%s AND timestamp BETWEEN %s AND %s"
        results = self.db.execute(query, (symbol, start, end))
        return [Candle(**r) for r in results]

# Strategy usa solo la abstracción
class Strategy:
    def __init__(self, candle_repo: AbstractCandleRepository):
        self.candle_repo = candle_repo

    def generate_signal(self, symbol: str):
        candles = self.candle_repo.get_candles(symbol, ...)
        # Lógica de estrategia...
```

**Regla 16.4 — Service Layer**

Claude DEBE introducir capa de servicios:
- Controlador web o CLI llaman al Servicio
- Servicio llama al Dominio
- Orquesta acciones complejas

```python
class TradingService:
    """Capa de servicio que orquesta el dominio."""

    def __init__(
        self,
        strategy: Strategy,
        order_repo: AbstractOrderRepository,
        broker: AbstractBroker
    ):
        self.strategy = strategy
        self.order_repo = order_repo
        self.broker = broker

    def execute_trade(self, symbol: str, signal: Signal):
        """Orquesta la ejecución de un trade."""
        # 1. Generar señal usando estrategia (dominio)
        order = self.strategy.create_order(symbol, signal)

        # 2. Validar orden (dominio)
        if not order.validate():
            raise InvalidOrderError("Orden inválida")

        # 3. Guardar orden (repositorio)
        self.order_repo.add(order)

        # 4. Ejecutar orden (broker)
        self.broker.execute_order(order)
```

**Regla 16.5 — Unit of Work (UoW)**

Claude DEBE gestionar transacciones atómicamente:
- Si orden falla al guardarse en DB, NO debe enviarse al broker
- UoW maneja commit o rollback

```python
class TradingUnitOfWork:
    """Gestiona transacción atómica."""

    def __init__(self, session_factory, broker_factory):
        self.session_factory = session_factory
        self.broker_factory = broker_factory

    def __enter__(self):
        self.session = self.session_factory()
        self.broker = self.broker_factory()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Commit DB y enviar orden al broker
            self.session.commit()
        else:
            # Rollback DB y NO enviar orden
            self.session.rollback()

    def execute_trade(self, order: Order):
        # Guardar en DB (pendiente de commit)
        self.session.add(order)

        # Enviar al broker (solo si commit exitoso)
        self.broker.execute(order)

# Uso
try:
    with TradingUnitOfWork(session_factory, broker_factory) as uow:
        uow.execute_trade(order)
except Exception as e:
    # Todo se revertirá automáticamente
    logger.error(f"Trade fallido: {e}")
```

**Regla 16.6 — Aggregates**

Claude DEBE agrupar objetos relacionados:
- Portfolio, Position, Order son un Aggregate
- Solo modificar Portfolio raíz para asegurar consistencia

```python
@dataclass
class Position:
    """Parte del aggregate Portfolio."""
    symbol: str
    quantity: int
    avg_price: float

@dataclass
class Order:
    """Parta del aggregate Portfolio."""
    symbol: str
    quantity: int
    price: float

class Portfolio:
    """Aggregate root - único punto de modificación."""

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []

    def add_position(self, symbol: str, quantity: int, price: float):
        """Modificar portfolio SOLO a través de este método."""
        if symbol in self.positions:
            # Actualizar posición existente
            existing = self.positions[symbol]
            total_cost = existing.quantity * existing.avg_price + quantity * price
            total_qty = existing.quantity + quantity
            existing.avg_price = total_cost / total_qty
            existing.quantity = total_qty
        else:
            # Crear nueva posición
            self.positions[symbol] = Position(symbol, quantity, price)

    def add_order(self, order: Order):
        """Modificar portfolio SOLO a través de este método."""
        self.orders.append(order)
        # Actualizar posición basado en orden
        self.add_position(order.symbol, order.quantity, order.price)
```

**Regla 16.7 — Value Objects**

Claude DEBE usar objetos inmutables:
- Money(amount, currency) es mejor que float + str por separado
- Son inmutables y no tienen identidad

```python
from dataclasses import dataclass

@dataclass(frozen=True)  # Inmutable
class Money:
    """Value Object para cantidades de dinero."""
    amount: Decimal
    currency: str

    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

@dataclass(frozen=True)  # Inmutable
class Quantity:
    """Value Object para cantidades de activos."""
    value: int
    unit: str  # 'shares', 'contracts', etc.

    def __add__(self, other: 'Quantity') -> 'Quantity':
        if self.unit != other.unit:
            raise ValueError("Cannot add different units")
        return Quantity(self.value + other.value, self.unit)
```

**Regla 16.8 — Message Bus**

Claude DEBE desacoplar eventos secundarios:
- Si OrderFilled ocurre, publica un evento
- Sistema de notificación y logger escuchan, sin bloquear flujo principal

```python
from dataclasses import dataclass
from typing import List, Callable

@dataclass
class Event:
    """Evento de dominio."""
    type: str
    data: dict

class MessageBus:
    """Bus de mensajes para desacoplar eventos."""

    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        """Suscribir handler a evento."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def publish(self, event: Event):
        """Publicar evento a todos los handlers."""
        handlers = self.handlers.get(event.type, [])
        for handler in handlers:
            handler(event)  # No bloquear el flujo principal

# Uso
bus = MessageBus()

# Suscribir handlers
bus.subscribe("ORDER_FILLED", lambda e: logger.info(f"Order filled: {e.data}"))
bus.subscribe("ORDER_FILLED", lambda e: send_telegram_alert(f"Order filled: {e.data}"))

# Publicar evento
order = Order("AAPL", 100, 150.0)
bus.publish(Event("ORDER_FILLED", {"symbol": order.symbol, "qty": order.quantity}))
```

**Regla 16.9 — Command vs Event**

Claude DEBE distinguir entre:
- Comandos (Imperativos: "Compra X") - pueden fallar
- Eventos (Hechos: "X Comprado") - ya sucedieron

```python
@dataclass
class BuyCommand:
    """Comando - puede fallar."""
    symbol: str
    quantity: int
    price: float

    def execute(self) -> bool:
        """Ejecutar comando - puede retornar False."""
        # Lógica de compra...
        return True  # o False si falla

@dataclass
class OrderExecutedEvent:
    """Evento - ya sucedió, inmutable."""
    order_id: str
    symbol: str
    quantity: int
    price: float
    timestamp: datetime
```

**Regla 16.10 — Adapters**

Claude DEBE mantener adaptadores en los bordes:
- Todo lo que toque el mundo exterior es un Adaptador
- API Broker, CSVs, Websockets van en adapters/

```python
# adapters/broker_alpaca.py
class AlpacaBrokerAdapter(AbstractBroker):
    """Adaptador para Alpaca API - tocando mundo exterior."""

    def __init__(self, api_key: str, api_secret: str):
        self.client = AlpacaClient(api_key, api_secret)  # HTTP client

    def execute_order(self, order: Order) -> Execution:
        """Llamar API externa - kept in adapter."""
        response = self.client.post("/orders", {
            "symbol": order.symbol,
            "qty": order.quantity,
            "side": order.side,
            "type": "market"
        })
        return Execution.from_response(response)
```

**Regla 16.11 — Thin Views**

Claude DEBE mantener lógica en el modelo:
- Si hay dashboard, lógica en modelo, no en vista/API
- Views solo presentan datos

```python
# ❌ MAL - Lógica en view
def portfolio_value_view():
    portfolio = get_portfolio()
    total = 0
    for pos in portfolio.positions:
        total += pos.quantity * pos.avg_price  # Lógica en view
    return render_template("portfolio.html", total=total)

# ✅ BIEN - Lógica en modelo
class Portfolio:
    def total_value(self) -> Money:
        """Lógica en el modelo."""
        return sum(
            pos.quantity * pos.avg_price
            for pos in self.positions
        )

def portfolio_value_view():
    portfolio = get_portfolio()
    total = portfolio.total_value()  # View solo llama modelo
    return render_template("portfolio.html", total=total)
```

**Regla 16.12 — Dependency Injection**

Claude DEBE inyectar dependencias:
- Pasar repositorios, clientes API al constructor
- NO instanciar dentro de la clase

```python
# ❌ MAL - Instanciación interna
class Strategy:
    def __init__(self):
        self.db = PostgreSQLDatabase("localhost", 5432)  # Hard-coded
        self.broker = BinanceAPI("api_key", "api_secret")

# ✅ BIEN - Inyección de dependencias
class Strategy:
    def __init__(
        self,
        db: AbstractDatabase,
        broker: AbstractBroker
    ):
        self.db = db  # Inyectado
        self.broker = broker  # Inyectado
```

**Regla 16.13 — Test Pyramid**

Claude DEBE tener muchos tests unitarios rápidos:
- Tests unitarios para dominio (sin mocks)
- Tests end-to-end lentos para adaptadores (con mocks)

```python
# Unit test - dominio puro, sin mocks
def test_portfolio_add_position():
    portfolio = Portfolio()
    portfolio.add_position("AAPL", 100, 150.0)
    assert portfolio.positions["AAPL"].quantity == 100

# Integration test - adaptador con mock
def test_postgres_repository():
    mock_db = MockDatabase()
    repo = PostgresCandleRepository(mock_db)
    candles = repo.get_candles("AAPL", ...)
    assert len(candles) > 0
```

**Regla 16.14 — Domain Exceptions**

Claude DEBE lanzar excepciones de dominio:
- NO KeyError o ConnectionError
- Capturar y lanzar InsufficientFundsError o MarketClosedError

```python
class DomainError(Exception):
    """Base exception para dominio."""
    pass

class InsufficientFundsError(DomainError):
    """No hay suficiente capital."""
    pass

class MarketClosedError(DomainError):
    """Mercado cerrado."""
    pass

class Order:
    def validate(self, account_balance: Money):
        if self.quantity * self.price > account_balance:
            raise InsufficientFundsError(
                f"Insufficient funds: need {self.quantity * self.price}, "
                f"have {account_balance}"
            )
```

**Regla 16.15 — Configuration Externalization**

Claude DEBE externalizar configuración:
- Claves API, params en variables de entorno
- Usar pydantic-settings

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Configuración externalizada."""
    database_url: str
    binance_api_key: str
    binance_api_secret: str
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

# Uso
settings = Settings()
db = connect(settings.database_url)
broker = BinanceAPI(settings.binance_api_key, settings.binance_api_secret)
```
