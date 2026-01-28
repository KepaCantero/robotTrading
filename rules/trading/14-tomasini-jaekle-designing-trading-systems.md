# 📘 14. "Designing Trading Systems" - Tomasini & Jaekle

## REGLAS DE ARQUITECTURA DE SISTEMAS DE TRADING

**Regla 14.1 — Arquitectura event-driven**

Claude DEBE usar arquitectura event-driven.

**Backtest ≠ live trading.**

**Interfaces comunes obligatorios.**

```python
# Event-driven architecture
class Event:
    """Base class para todos los eventos."""
    pass

class MarketEvent(Event):
    """Nuevo dato de mercado disponible."""
    def __init__(self, timestamp: datetime, symbol: str, data: dict):
        self.timestamp = timestamp
        self.symbol = symbol
        self.data = data

class SignalEvent(Event):
    """Señal de trading generada."""
    def __init__(self, timestamp: datetime, symbol: str, direction: str, strength: float):
        self.timestamp = timestamp
        self.symbol = symbol
        self.direction = direction  # 'BUY' or 'SELL'
        self.strength = strength

class OrderEvent(Event):
    """Orden a ejecutar."""
    def __init__(self, timestamp: datetime, symbol: str, quantity: int, order_type: str):
        self.timestamp = timestamp
        self.symbol = symbol
        self.quantity = quantity
        self.order_type = order_type

class FillEvent(Event):
    """Orden ejecutada."""
    def __init__(self, timestamp: datetime, symbol: str, quantity: int, price: float, commission: float):
        self.timestamp = timestamp
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.commission = commission
```

**Regla 14.2 — Signal code no debe colocar trades**

```python
def generate_signal(
    self,
    features: pd.Series
) -> float:
    """
    Generar señal SIN ejecutar trades.

    Tomasini & Jaekle: Separación signal → execution.
    """
    # Calcular momentum score
    momentum = features['momentum_126']

    # Calcular mean reversion score
    mean_rev = features['zscore_20']

    # Combinar señales
    signal = momentum * 0.6 + mean_rev * 0.4

    # Normalizar a [-1, 1]
    signal = np.tanh(signal)

    # ✅ BIEN: Solo retornar señal
    return signal

    # ❌ MAL: NO ejecutar trades aquí
    # self.execute_order(symbol, signal)  # PROHIBIDO
```

**Regla 14.3 — Backtests event-driven**

```python
def event_driven_backtest(
    self,
    strategy: Strategy,
    market_data: pd.DataFrame,
    initial_capital: float = 100000
) -> dict:
    """
    Backtest usando eventos (no vectorizado).

    Tomasini & Jaekle: Event-driven backtest = más realista.
    """
    # Event queue
    events = []

    # Generar market events
    for timestamp, row in market_data.iterrows():
        events.append(MarketEvent(timestamp, 'SYMBOL', row.to_dict()))

    # Strategy state
    portfolio = Portfolio(initial_capital)
    signals_generated = 0
    orders_placed = 0
    fills_executed = 0

    # Process events
    for event in events:
        if isinstance(event, MarketEvent):
            # 1. Update strategy con nuevo dato
            strategy.on_market_data(event)

            # 2. Generar señal
            signal = strategy.generate_signal()
            signals_generated += 1

            # 3. Crear order si signal != 0
            if abs(signal) > 0.1:
                order = self.create_order_from_signal(signal, event)
                events.append(OrderEvent(event.timestamp, 'SYMBOL', order.quantity, 'LIMIT'))
                orders_placed += 1

        elif isinstance(event, OrderEvent):
            # 4. Simular execution
            fill = self.simulate_fill(event, market_data)
            if fill:
                events.append(FillEvent(
                    event.timestamp, 'SYMBOL', fill.quantity, fill.price, fill.commission
                ))
                fills_executed += 1

        elif isinstance(event, FillEvent):
            # 5. Update portfolio
            portfolio.on_fill(event)

    return {
        'final_value': portfolio.total_value,
        'signals': signals_generated,
        'orders': orders_placed,
        'fills': fills_executed,
        'returns': (portfolio.total_value - initial_capital) / initial_capital
    }
```

**Regla 14.4 — Interface común entre backtest y live**

```python
class StrategyInterface(ABC):
    """
    Interface común para backtest y live trading.

    Tomasini & Jaekle: Mismo código para backtest y live.
    """

    @abstractmethod
    def on_market_data(self, event: MarketEvent):
        """Called cuando nuevo dato de mercado llega."""
        pass

    @abstractmethod
    def generate_signal(self) -> float:
        """Generar señal basado en estado actual."""
        pass

    @abstractmethod
    def on_order_filled(self, event: FillEvent):
        """Called cuando orden es ejecutada."""
        pass

class MyStrategy(StrategyInterface):
    """Implementación concreta."""

    def __init__(self):
        self.position = 0
        self.cash = 0

    def on_market_data(self, event: MarketEvent):
        """Update indicadores con nuevo dato."""
        # Mismo código en backtest y live
        pass

    def generate_signal(self) -> float:
        """Mismo código en backtest y live."""
        return self.calculate_momentum()

    def on_order_filled(self, event: FillEvent):
        """Mismo código en backtest y live."""
        self.position += event.quantity
```

**Regla 14.5 — Order management system**

```python
class OrderManager:
    """
    Gestiona ciclo de vida de órdenes.

    Tomasini & Jaekle: State machine para orders.
    """

    def __init__(self):
        self.orders = {}  # order_id -> Order
        self.open_orders = {}  # symbol -> [Order]

    def submit_order(self, order: Order) -> str:
        """Submit nueva orden."""
        order.status = 'SUBMITTED'
        order.submitted_at = datetime.now()

        self.orders[order.id] = order
        self.open_orders.setdefault(order.symbol, []).append(order)

        logger.info(f"Order submitted: {order.id}")

        return order.id

    def on_fill(self, fill: Fill):
        """Procesar fill."""
        order = self.orders.get(fill.order_id)

        if not order:
            logger.error(f"Fill for unknown order: {fill.order_id}")
            return

        order.filled_quantity += fill.quantity
        order.avg_fill_price = (
            (order.avg_fill_price * (order.filled_quantity - fill.quantity) +
             fill.price * fill.quantity) / order.filled_quantity
        )

        # Check si orden completamente fill
        if order.filled_quantity >= order.quantity:
            order.status = 'FILLED'
            order.filled_at = datetime.now()

            # Remove de open orders
            if order.id in [o.id for o in self.open_orders.get(order.symbol, [])]:
                self.open_orders[order.symbol] = [
                    o for o in self.open_orders[order.symbol]
                    if o.id != order.id
                ]

        logger.info(
            f"Order {order.id} fill: {fill.quantity}/{order.quantity} @ {fill.price}"
        )
```

**Regla 14.6 — Position tracking**

```python
class PositionTracker:
    """
    Tracking de posiciones con FIFO.

    Tomasini & Jaekle: FIFO para tax y P&L calculation.
    """

    def __init__(self):
        self.positions = {}  # symbol -> Position
        self.fifo_queues = {}  # symbol -> [(entry_date, quantity, price)]

    def on_fill(self, fill: FillEvent):
        """Update position en fill."""
        symbol = fill.symbol

        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
            self.fifo_queues[symbol] = []

        if fill.quantity > 0:  # BUY
            self.positions[symbol].quantity += fill.quantity
            self.fifo_queues[symbol].append((
                fill.timestamp,
                fill.quantity,
                fill.price
            ))

        else:  # SELL
            # FIFO: cerrar posiciones más antiguas primero
            remaining = abs(fill.quantity)

            while remaining > 0 and self.fifo_queues[symbol]:
                entry_date, entry_qty, entry_price = self.fifo_queues[symbol][0]

                if entry_qty <= remaining:
                    # Cerrar completamente esta entrada
                    realized_pnl = (fill.price - entry_price) * entry_qty
                    self.positions[symbol].realized_pnl += realized_pnl

                    remaining -= entry_qty
                    self.fifo_queues[symbol].pop(0)

                else:
                    # Cerrar parcialmente
                    realized_pnl = (fill.price - entry_price) * remaining
                    self.positions[symbol].realized_pnl += realized_pnl

                    # Update entrada remaining
                    self.fifo_queues[symbol][0] = (
                        entry_date,
                        entry_qty - remaining,
                        entry_price
                    )

                    remaining = 0
```

**Regla 14.7 — Performance metrics**

```python
def calculate_performance_metrics(
    self,
    equity_curve: pd.Series,
    returns: pd.Series
) -> dict:
    """
    Métricas de performance completas.

    Tomasini & Jaekle: Más que Sharpe ratio.
    """
    # Basic metrics
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1

    # Sharpe ratio
    sharpe = np.sqrt(252) * returns.mean() / returns.std()

    # Maximum drawdown
    peak = equity_curve.expanding().max()
    drawdown = (equity_curve - peak) / peak
    max_dd = drawdown.min()

    # Calmar ratio
    calmar = total_return / abs(max_dd) if max_dd != 0 else float('inf')

    # Sortino ratio
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std()
    sortino = np.sqrt(252) * returns.mean() / downside_std if downside_std > 0 else 0

    # Win rate
    winning_days = (returns > 0).sum()
    total_days = len(returns)
    win_rate = winning_days / total_days

    # Profit factor
    gross_profit = returns[returns > 0].sum()
    gross_loss = abs(returns[returns < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')

    return {
        'total_return': total_return,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'max_drawdown': max_dd,
        'calmar_ratio': calmar,
        'win_rate': win_rate,
        'profit_factor': profit_factor
    }
```

**Regla 14.8 — Logging estructurado**

```python
def log_trade_event(
    self,
    event: Union[OrderEvent, FillEvent, SignalEvent],
    context: dict
):
    """
    Logging estructurado para debugging.

    Tomasini & Jaekle: Logs deben ser replayables.
    """
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event.__class__.__name__,
        'event_data': vars(event),
        'context': context
    }

    logger.info(json.dumps(log_entry))
```

**Regla 14.9 — Configuración externalizada**

```python
def load_strategy_config(
    self,
    config_path: str = "strategy_config.yaml"
) -> dict:
    """
    Configuración externalizada en YAML.

    Tomasini & Jaekle: No hardcodear parámetros.
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Validar config
    required_keys = ['parameters', 'risk_limits', 'execution']

    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")

    logger.info(f"Loaded config from {config_path}")

    return config
```

**Regla 14.10 — Estado persistente**

```python
def persist_state(
    self,
    state: dict,
    state_path: str = "strategy_state.json"
):
    """
    Persistir estado de estrategia.

    Tomasini & Jaekle: Recuperar de crashes es obligatorio.
    """
    state_snapshot = {
        'timestamp': datetime.now().isoformat(),
        'positions': state['positions'],
        'cash': state['cash'],
        'last_signal': state.get('last_signal'),
        'last_rebalance': state.get('last_rebalance')
    }

    with open(state_path, 'w') as f:
        json.dump(state_snapshot, f, indent=2)

    logger.info(f"State persisted to {state_path}")

def load_state(
    self,
    state_path: str = "strategy_state.json"
) -> dict:
    """Cargar estado persistido."""
    if not os.path.exists(state_path):
        return {}

    with open(state_path, 'r') as f:
        state = json.load(f)

    logger.info(f"State loaded from {state_path}")

    return state
```
