# 📘 25. Clean Code in Python - Maintainable Trading Systems

**Libro:** Clean Code in Python - Mariano Anaya
**Objetivo:** Escribir código mantenible, testable y robusto para sistemas de trading

## 🎯 Resumen Ejecutivo

Claude Code DEBE seguir estos principios:
1. **Código auto-explicativo** (sin comentarios obvios)
2. **Separación de responsabilidades** (una cosa a la vez)
3. **Nombres basados en dominio** (lenguaje de trading)
4. **Manejo de errores específico** (no `except Exception`)

---

## 📋 Las 15 Reglas Críticas para Claude Code

### 1. Pydantic para Validación

```python
from pydantic import BaseModel, Field, validator

class TradingSignal(BaseModel):
    """Señal de trading validada."""

    symbol: str = Field(..., min_length=1, description="Símbolo de ticker")
    direction: str = Field(..., regex="^(BUY|SELL|SHORT)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime

    @validator('confidence')
    def validate_confidence(cls, v):
        """Confidence debe ser >= 0.5 para ser válida."""
        if v < 0.5:
            raise ValueError("Confidence too low (min 0.5)")
        return v

# Uso:
try:
    signal = TradingSignal(
        symbol="AAPL",
        direction="BUY",
        confidence=0.85,
        timestamp=datetime.now()
    )
except ValidationError as e:
    logger.error(f"Invalid signal: {e}")
```

**Regla para Claude:** USAR Pydantic para validar TODOS los datos externos (API, WebSocket, DB).

---

### 2. Configuración via `.env` (python-dotenv)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configuración desde variables de entorno."""

    # API Keys
    binance_api_key: str
    binance_api_secret: str

    # Parámetros de trading
    max_position_size: float = 0.20
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

# Uso:
settings = Settings()
# Valida y carga desde .env automáticamente
```

**Regla para Claude:** NUNCA hardcodear API keys o configuración. Usar variables de entorno.

---

### 3. Separación de Lógica (Order No Sabe Enviarse)

```python
# ❌ MAL: Order sabe cómo enviarse
class Order:
    def send_to_broker(self):
        """Order no debe saber de brokers."""
        # ... lógica de API de Binance ...

# ✅ BIEN: Responsabilidades separadas
@dataclass
class Order:
    symbol: str
    quantity: Decimal
    price: Decimal
    side: str

class BrokerAdapter:
    """Adaptador sabe cómo enviar órdenes."""

    def send_order(self, order: Order) -> OrderResult:
        """Envía orden al broker."""
        # ... lógica de API ...

# Separación de responsabilidades
```

**Regla para Claude:** SEPARAR lógica de dominio (Order) de infraestructura (BrokerAdapter).

---

### 4. Enumeraciones para Direcciones

```python
from enum import Enum

class Side(Enum):
    """Dirección de orden."""
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"

class OrderStatus(Enum):
    """Estado de orden."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

# Uso:
order = Order(side=Side.BUY, status=OrderStatus.PENDING)

# Más seguro que strings ("BUY", "SELL")
```

**Regla para Claude:** USAR `Enum` para conjuntos finitos de valores (Side, Status, Type).

---

### 5. Pequeñas Funciones (Divide y Vencerás)

```python
# ❌ MAL: Función gigante
def process_trade(trade_data):
    # 200 líneas de código...
    # Validar
    # Calcular posición
    # Actualizar portfolio
    # Enviar orden
    # Loggear
    # Notificar
    pass

# ✅ BIEN: Funciones pequeñas y enfocadas
def process_trade(trade_data: TradeData) -> None:
    """Procesa trade (orquesta pasos)."""
    validated_trade = validate_trade(trade_data)
    position = calculate_position(validated_trade)
    update_portfolio(position)
    send_order(validated_trade.order)
    log_trade(validated_trade)
    notify_user(validated_trade)

def validate_trade(trade_data: TradeData) -> TradeData:
    """Valida datos de trade."""
    # ... validación ...
    pass

def calculate_position(trade: TradeData) -> Position:
    """Calcula tamaño de posición."""
    # ... cálculo ...
    pass
```

**Regla para Claude:** UNA FUNCIÓN = UNA RESPONSABILIDAD. Máximo 20-30 líneas.

---

### 6. Nombres Basados en Dominio

```python
# ❌ MAL: Nombres genéricos
def process(data):
    for item in data:
        if item['x'] > item['y']:
            do_something(item)

# ✅ BIEN: Lenguaje de dominio
def execute_trades(market_data: list[MarketSnapshot]) -> None:
    """Ejecuta trades cuando precio > media móvil."""
    for snapshot in market_data:
        if snapshot.price > snapshot.moving_average:
            place_order(snapshot)

# Código se lee como prosa
```

**Regla para Claude:** USAR nombres del dominio de trading (price, volume, position, order).

---

### 7. Docstrings con Tipos

```python
def calculate_position_size(
    capital: Decimal,
    risk_per_trade: Decimal,
    stop_loss_pct: Decimal
) -> Decimal:
    """
    Calcula tamaño de posición usando Kelly Criterion simplificado.

    Args:
        capital: Capital total disponible
        risk_per_trade: Riesgo por trade (ej. 0.02 = 2%)
        stop_loss_pct: Stop loss como % (ej. 0.05 = 5%)

    Returns:
        Tamaño de posición en unidades de moneda/base

    Raises:
        ValueError: Si risk_per_trade > 0.10 (muy arriesgado)

    Example:
        >>> calculate_position_size(Decimal('10000'), Decimal('0.02'), Decimal('0.05'))
        Decimal('4000.0')
    """
    if risk_per_trade > Decimal('0.10'):
        raise ValueError("Risk per trade too high (max 10%)")

    position_size = (capital * risk_per_trade) / stop_loss_pct
    return min(position_size, capital * Decimal('0.20'))
```

**Regla para Claude:** TODAS las funciones públicas DEBEN tener docstring completo.

---

### 8. Logging Estructurado (structlog, JSON)

```python
import structlog

# Configurar logging en JSON
logger = structlog.get_logger()

# Uso:
logger.info(
    "order_filled",
    order_id=order.order_id,
    symbol=order.symbol,
    side=order.side,
    quantity=float(order.quantity),
    price=float(order.price),
    commission=float(commission)
)

# Salida JSON:
# {
#   "event": "order_filled",
#   "order_id": "abc123",
#   "symbol": "AAPL",
#   "side": "BUY",
#   "quantity": 100.0,
#   "price": 150.25,
#   "commission": 1.5
# }
```

**Regla para Claude:** USAR structlog para logging en JSON (fácil de analizar).

---

### 9. Unit Tests por Estrategia

```python
import pytest

def test_momentum_strategy_signal_generation():
    """Test de generación de señales de momentum."""

    # Setup
    strategy = MomentumStrategy(lookback=20)
    prices = pd.Series([
        100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
        110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120
    ])

    # Execute
    signal = strategy.generate_signal(prices)

    # Assert
    assert signal.direction == 'BUY'
    assert signal.confidence > 0.7
    assert signal.symbol is not None
```

**Regla para Claude:** ESCRIBIR tests ANTES de código (TDD) para toda lógica de estrategia.

---

### 10. Sin Comentarios Obvios (Código Auto-Explicativo)

```python
# ❌ MAL: Comentario obvio
# Incrementar contador
counter += 1

# ✅ BIEN: Código auto-explicativo
filled_orders_count += 1

# ❌ MAL: Comentario que repite código
# Si precio > media, comprar
if price > moving_average:
    buy()

# ✅ BIEN: Código se explica solo
if price > moving_average:
    execute_buy_order()
```

**Regla para Claude:** ELIMINAR comentarios que repiten el código. El código debe hablar por sí solo.

---

### 11. Manejo de Errores Específicos

```python
# ❌ MAL: Captura todo
try:
    order = send_order_to_broker(order_data)
except Exception as e:
    logger.error(f"Error: {e}")

# ✅ BIEN: Errores específicos
try:
    order = send_order_to_broker(order_data)
except InsufficientFundsError:
    logger.error("Insufficient funds for order")
    raise
except RateLimitError:
    logger.warning("Rate limit hit, backing off")
    await asyncio.sleep(60)
except NetworkError:
    logger.error("Network error, retrying")
    retry_order(order_data)
```

**Regla para Claude:** NUNCA usar `except Exception`. Capturar excepciones específicas.

---

### 12. Inyección de Dependencias

```python
# ❌ MAL: Instancia dependencia dentro
class TradingStrategy:
    def __init__(self):
        self.broker = BinanceAPI()  # Hard-coded

# ✅ BIEN: Inyección de dependencias
class TradingStrategy:
    def __init__(self, broker: BrokerProtocol, notifier: NotifierProtocol):
        self.broker = broker
        self.notifier = notifier

# Facilita testing con mocks
def test_strategy():
    mock_broker = MockBroker()
    mock_notifier = MockNotifier()
    strategy = TradingStrategy(mock_broker, mock_notifier)
    # ... test ...
```

**Regla para Claude:** INYECTAR dependencias (broker, DB, notifier) en el constructor.

---

### 13. Poetry/Pipenv para Dependencias

```toml
# pyproject.toml (Poetry)
[tool.poetry.dependencies]
python = "^3.11"
pandas = "^2.0.0"
numpy = "^1.24.0"
aiohttp = "^3.8.0"
pydantic = "^2.0.0"

[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
mypy = "^1.5.0"
ruff = "^0.1.0"
```

**Regla para Claude:** USAR Poetry o Pipenv para gestionar dependencias (reproducibilidad).

---

### 14. Linters (Ruff/Flake8)

```bash
# .github/workflows/lint.yml
- name: Lint with Ruff
  run: |
    pip install ruff
    ruff check .

- name: Type check with mypy
  run: |
    pip install mypy
    mypy .

# CI rechaza código que no pasa linter
```

**Regla para Claude:** CONFIGURAR CI para rechazar código que no pase Ruff y mypy.

---

### 15. Modularidad (Instancia de Strategy por Par)

```python
# ❌ MAL: Una estrategia maneja todo
class MegaStrategy:
    def __init__(self, symbols: list[str]):
        self.symbols = symbols

    def run(self):
        for symbol in self.symbols:
            # ... lógica para todos los símbolos ...
            pass

# ✅ BIEN: Una instancia por símbolo
class MomentumStrategy:
    def __init__(self, symbol: str, params: StrategyParams):
        self.symbol = symbol
        self.params = params

    def run(self):
        # ... lógica para este símbolo ...
        pass

# Inicializar múltiples instancias
strategies = [
    MomentumStrategy('AAPL', params),
    MomentumStrategy('TSLA', params),
]
```

**Regla para Claude:** UNA INSTANCIA de estrategia por símbolo (no una estrategia para todo).

---

## 🎓 Ejemplo Completo: Código Limpio

```python
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from pydantic import BaseModel, Field, validator
import structlog

logger = structlog.get_logger()

class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass(frozen=True)
class Position:
    """Posición inmutable."""
    symbol: str
    quantity: Decimal
    avg_price: Decimal

class TradingSignal(BaseModel):
    """Señal de trading validada."""
    symbol: str = Field(..., min_length=1)
    side: Side
    confidence: float = Field(..., ge=0.0, le=1.0)

    @validator('confidence')
    def confidence_must_be_sufficient(cls, v):
        if v < 0.6:
            raise ValueError("Confidence too low (min 0.6)")
        return v

class PositionManager:
    """Gestiona posiciones (SRP)."""

    def __init__(self, broker: BrokerProtocol):
        self.broker = broker
        self._positions: dict[str, Position] = {}

    def add_position(self, signal: TradingSignal) -> None:
        """Añade posición basada en señal."""
        if signal.confidence < 0.6:
            logger.warning("Signal confidence too low", symbol=signal.symbol)
            return

        logger.info(
            "adding_position",
            symbol=signal.symbol,
            side=signal.side,
            confidence=signal.confidence
        )

        # ... lógica de añadir posición ...

    def get_position(self, symbol: str) -> Position | None:
        """Obtiene posición actual."""
        return self._positions.get(symbol)
```

---

## 📚 Referencias

- **Libro:** Clean Code in Python - Mariano Anaya
- **Herramientas:**
  - `pylint`: Linter completo
  - `ruff`: Linter rápido (Rust)
  - `mypy`: Type checker
  - `black`: Formateador de código
  - `pytest`: Framework de tests
  - `structlog`: Logging estructurado

---

**Última actualización:** 2026-01-28
**Version:** 2.1 (Completado con ejemplos de refactoring real)


---

## 🛠️ Ejemplos de Refactoring Real

### Before/After 1: Extracción de Método

**❌ ANTES (Código procedural):**

```python
def execute_trade(signal, portfolio, broker, config):
    if signal['confidence'] < 0.6:
        return False
    # ... 50 lines of code ...
```

**✅ DESPUÉS (Clean Code):**

```python
class SignalValidator:
    def validate(self, signal, portfolio):
        return signal.confidence >= 0.6

class PositionSizer:
    def calculate_size(self, signal, portfolio, risk_per_trade):
        risk_amount = portfolio.cash * risk_per_trade
        return min(signal.quantity, risk_amount / signal.price)
```

**Mejoras:** SRP, testing individual, inyección de dependencias


---

## 🛠️ Ejemplos de Refactoring Real

### Before/After 1: Extracción de Método

**❌ ANTES (Código procedural):**

```python
def execute_trade(signal, portfolio, broker, config):
    if signal['confidence'] < 0.6:
        return False
    # ... 50 lines of code ...
```

**✅ DESPUÉS (Clean Code):**

```python
class SignalValidator:
    def validate(self, signal, portfolio):
        return signal.confidence >= 0.6

class PositionSizer:
    def calculate_size(self, signal, portfolio, risk_per_trade):
        risk_amount = portfolio.cash * risk_per_trade
        return min(signal.quantity, risk_amount / signal.price)
```

**Mejoras:** SRP, testing individual, inyección de dependencias
