# 📗 18. "Clean Architecture" - Robert C. Martin

## REGLAS DE ARQUITECTURA LIMPIA PARA TRADING

**Regla 18.1 — Screaming Architecture**

Claude DEBE estructurar carpetas por dominio:
- /strategies, /execution, /risk (NO /models, /views)
- La estructura debe gritar qué hace el sistema

```python
# ❌ MAL - Framework-oriented
trading_bot/
├── models/
├── views/
├── controllers/
└── services/

# ✅ BIEN - Domain-oriented
trading_bot/
├── strategies/      # Lógica de trading
├── execution/       # Ejecución de órdenes
├── risk/            # Gestión de riesgo
├── data/            # Acceso a datos
└── infrastructure/  # APIs, DBs, etc.
```

**Regla 18.2 — Stable Dependencies**

Claude DEBE apuntar dependencias hacia estabilidad:
- Código volátil (UI, API adapters) depende del código estable (reglas de negocio)
- NO al revés

```python
# Capa estable (reglas de negocio) - NO depende de nadie
class RiskManager:
    def check_position_size(self, position: Position) -> bool:
        """Regla de negocio estable."""
        return position.quantity * position.price < self.max_position_value

# Capa volátil (API) - depende de regla de negocio
class OrderAPI:
    def __init__(self, risk_manager: RiskManager):
        self.risk = risk_manager  # Depende de capa estable

    def create_order(self, request: OrderRequest):
        order = Order.from_request(request)
        if not self.risk.check_position_size(order):
            raise RiskLimitExceeded()
        # Ejecutar orden...
```

**Regla 18.3 — Boundary Crossing**

Claude DEBE usar DTOs simples al cruzar límites:
- De Estrategia a Base de Datos
- NO pasar objetos complejos del ORM

```python
@dataclass
class OrderDTO:
    """Data Transfer Object simple para cruzar límites."""
    symbol: str
    quantity: int
    price: float
    side: str

# Strategy returns DTO
def generate_signal(self) -> OrderDTO:
    return OrderDTO("AAPL", 100, 150.0, "BUY")

# Repository receives DTO
def save_order(self, dto: OrderDTO):
    # Convertir DTO a entidad de DB
    db_order = OrderEntity(
        symbol=dto.symbol,
        quantity=dto.quantity,
        price=dto.price,
        side=dto.side
    )
    self.session.add(db_order)
```

**Regla 18.4 — Main Component**

Claude DEBE tener un único main.py:
- Único lugar "sucio" donde se instancia todo
- Inyección de dependencias

```python
# main.py - único lugar donde se ensambla todo
def main():
    # Infrastructure
    db = PostgresDatabase(settings.db_url)
    broker = AlpacaBroker(settings.api_key, settings.api_secret)

    # Repositories
    candle_repo = PostgresCandleRepository(db)
    order_repo = PostgresOrderRepository(db)

    # Services
    risk_manager = RiskManager(max_position_size=0.20)
    execution_service = ExecutionService(broker, order_repo)

    # Strategies
    momentum = MomentumStrategy(candle_repo, risk_manager)

    # Application
    trading_bot = TradingBot(
        strategy=momentum,
        execution=execution_service
    )

    trading_bot.run()

if __name__ == "__main__":
    main()
```

**Regla 18.5 — Interface Segregation**

Claude DEBE preferir interfaces pequeñas:
- ReadableRepository, WritableRepository separados
- NO Repository gigante

```python
from abc import ABC, abstractmethod

class ReadableCandleRepository(ABC):
    """Solo lectura - pequeño y cohesivo."""

    @abstractmethod
    def get_candles(self, symbol: str, start: datetime, end: datetime) -> List[Candle]:
        pass

class WritableCandleRepository(ABC):
    """Solo escritura - pequeño y cohesivo."""

    @abstractmethod
    def save_candles(self, candles: List[Candle]) -> None:
        pass

# Implementar solo lo que necesitas
class InMemoryCandleRepository(ReadableCandleRepository):
    """Solo lectura - no necesita implementar save."""
    def __init__(self):
        self.candles = {}

    def get_candles(self, symbol: str, start: datetime, end: datetime) -> List[Candle]:
        # Implementación solo lectura
        pass
```

**Regla 18.6 — Open/Closed Principle**

Claude DEBE poder añadir sin modificar:
- Nueva estrategia o broker = agregar código
- NO modificar código existente

```python
# Abierto para extensión, cerrado para modificación
class StrategyEvaluator:
    """Evalúa estrategias - no cambia cuando añades nuevas."""

    def __init__(self):
        self.strategies = []

    def add_strategy(self, strategy: Strategy):
        """Añadir estrategia sin modificar código existente."""
        self.strategies.append(strategy)

    def evaluate_all(self, data: MarketData) -> Dict[str, float]:
        """Evaluar todas las estrategias registradas."""
        return {
            strategy.name: strategy.evaluate(data)
            for strategy in self.strategies
        }

# Añadir nueva estrategia sin modificar StrategyEvaluator
evaluator = StrategyEvaluator()
evaluator.add_strategy(MomentumStrategy())
evaluator.add_strategy(MeanReversionStrategy())
evaluator.add_strategy(YourNewStrategy())  # ¡Nueva estrategia!
```

**Regla 18.7 — Liskov Substitution**

Claude DEBE asegurar comportamiento consistente:
- BinanceBroker y KrakenBroker deben comportarse idénticamente
- Si heredan de Broker, deben ser intercambiables

```python
class Broker(ABC):
    """Contrato que todos los brokers deben cumplir."""

    @abstractmethod
    def execute_order(self, order: Order) -> Execution:
        """Ejecutar orden - mismo comportamiento para todos."""
        pass

    @abstractmethod
    def get_balance(self) -> Money:
        """Obtener balance - mismo comportamiento para todos."""
        pass

class BinanceBroker(Broker):
    def execute_order(self, order: Order) -> Execution:
        # Implementación específica de Binance
        pass

class KrakenBroker(Broker):
    def execute_order(self, order: Order) -> Execution:
        # Implementación específica de Kraken
        # Pero MISMO comportamiento (misma interfaz)
        pass

# Intercambiables
def execute_trade(broker: Broker, order: Order):
    """Funciona con cualquier broker."""
    execution = broker.execute_order(order)
    return execution

# Usar indistintamente
execute_trade(BinanceBroker(), order)
execute_trade(KrakenBroker(), order)  # Mismo comportamiento
```

**Regla 18.8 — Single Responsibility (Clases)**

Claude DEBE separar responsabilidades:
- Una clase Strategy NO debe enviar emails
- Delega eso a un Notifier

```python
# ❌ MAL - Strategy hace muchas cosas
class Strategy:
    def generate_signal(self, data):
        pass

    def execute_order(self, order):
        pass

    def send_email_alert(self, message):
        pass  # ¡NO es responsabilidad de Strategy!

# ✅ BIEN - Responsabilidades separadas
class Strategy:
    def generate_signal(self, data):
        pass

class ExecutionService:
    def execute_order(self, order):
        pass

class EmailNotifier:
    def send_alert(self, message):
        pass
```

**Regla 18.9 — Single Responsibility (Módulos)**

Claude DEBE limitar tamaño de archivos:
- Un archivo NO debe tener 2000 líneas
- Agrupar por cohesión funcional

```python
# ❌ MAL - strategy.py con 2000 líneas
# strategy.py
class Strategy:
    # 500 lines de signal generation
    ...

    # 500 lines de position sizing
    ...

    # 500 lines de risk management
    ...

    # 500 lines de execution logic
    ...

# ✅ BIEN - Separado por responsabilidad
# signal_generator.py
class SignalGenerator:
    ...

# position_sizer.py
class PositionSizer:
    ...

# risk_manager.py
class RiskManager:
    ...

# execution_service.py
class ExecutionService:
    ...
```

**Regla 18.10 — Humble Object**

Claude DEBE extraer lógica difícil de testear:
- Websockets, GUI → objeto "humilde"
- Lógica en clase pura fácil de testear

```python
# Humble object - difícil de testear
class WebSocketClient:
    """Objeto humilde - solo conecta y recibe."""

    def connect(self, url: str):
        self.ws = websocket.create_connection(url)

    def get_messages(self) -> List[str]:
        messages = []
        while True:
            message = self.ws.recv()
            messages.append(message)
        return messages

# Lógica pura - fácil de testear
class TickParser:
    """Clase pura - lógica de negocio."""

    def parse_ticks(self, messages: List[str]) -> List[Tick]:
        """Lógica de parseo - testable sin websocket."""
        ticks = []
        for msg in messages:
            data = json.loads(msg)
            ticks.append(Tick(
                symbol=data['s'],
                price=float(data['p']),
                volume=float(data['v'])
            ))
        return ticks
```

**Regla 18.11 — Config Separation**

Claude DEBE separar configuración del código:
- Cargar vía variables de entorno
- Usar pydantic-settings

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Configuración separada del código."""
    database_url: str
    api_key: str
    api_secret: str
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

# Código usa settings
settings = Settings()
db = connect(settings.database_url)
api = Broker(api_key=settings.api_key, api_secret=settings.api_secret)

# NO valores hard-coded
# db = connect("postgresql://localhost:5432/trading")  # ❌ MAL
```

**Regla 18.12 — Factories**

Claude DEBE usar patrón Factory para instanciación dinámica:
- Instanciar estrategias basadas en configuración

```python
from abc import ABC, abstractmethod

class StrategyFactory(ABC):
    """Factory para crear estrategias."""

    @abstractmethod
    def create(self, config: dict) -> Strategy:
        pass

class MomentumStrategyFactory(StrategyFactory):
    def create(self, config: dict) -> Strategy:
        return MomentumStrategy(
            lookback=config['lookback'],
            threshold=config['threshold']
        )

# Uso con configuración
config = {
    "type": "momentum",
    "params": {"lookback": 252, "threshold": 0.10}
}

factory = STRATEGY_FACTORIES[config["type"]]  # MomentumStrategyFactory
strategy = factory.create(config["params"])
```

**Regla 18.13 — Testing Strategy**

Claude DEBE tener dos tipos de tests:
- Unit tests para reglas de negocio (sin mocks)
- Integration tests para DB/Broker (con mocks)

```python
# Unit test - dominio puro, sin mocks
def test_kelly_criterion():
    """Test de fórmula de Kelly - sin dependencias externas."""
    win_rate = 0.55
    avg_win = 100
    avg_loss = 80

    kelly = calculate_kelly(win_rate, avg_win, avg_loss)

    assert kelly == pytest.approx(0.2375)

# Integration test - con mocks
def test_order_execution():
    """Test de ejecución con broker mock."""
    mock_broker = MockBroker()
    executor = ExecutionService(mock_broker)

    order = Order("AAPL", 100, 150.0, "BUY")
    execution = executor.execute(order)

    assert execution.status == ExecutionStatus.FILLED
    mock_broker.execute.assert_called_once()
```

**Regla 18.14 — Dead Code Elimination**

Claude DEBE eliminar código no usado:
- Si no se usa, se borra
- NO código comentado

```python
# ❌ MAL - Código muerto
def calculate_old_indicator(prices):
    # This function is deprecated but kept just in case
    pass

# ✅ BIEN - Eliminar código muerto
# Si no se usa, borrar. Git tiene el historial.
```

**Regla 18.15 — Cyclic Dependencies**

Claude DEBE PROHIBIR importaciones cíclicas:
- NO importar A en B y B en A
- Usar inyección o refactorizar a módulo C común

```python
# ❌ MAL - Importación cíclica
# strategies.py
from execution import ExecutionService

class Strategy:
    def __init__(self):
        self.execution = ExecutionService()  # Importa execution

# execution.py
from strategies import Strategy  # ¡Importa strategies!

class ExecutionService:
    def __init__(self):
        self.strategy = Strategy()  # Importación cíclica

# ✅ BIEN - Resolver con inyección o módulo común
# models.py - módulo compartido
@dataclass
class Order:
    symbol: str
    quantity: int
    price: float

# strategies.py - no importa execution
class Strategy:
    def __init__(self, execution: ExecutionService):
        self.execution = execution  # Inyectado, no importado

# execution.py - no importa strategies
class ExecutionService:
    def execute(self, order: Order):  # Usa modelo compartido
        pass
```
