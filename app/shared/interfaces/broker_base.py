"""
FICHERO 0: Interfaz Abstracta Universal para Brokers

Este archivo define el contrato que TODOS los brokers deben cumplir.
Antes de escribir binance_adapter.py, degiro_adapter.py, o cualquier broker,
DEBES implementar esta interfaz.

Por qué es CRÍTICO:
1. Normalización: Binance usa "BTCUSDT", OANDA usa "BTC_USD", IBKR usa "IBKR:BTC"
2. Testing: Puedes crear MockBroker para testing sin riesgo
3. SRE: WAL y BootReconciler dependen de esta interfaz
4. Tax: FIFO necesita normalización de símbolos

Author: SRE Feedback Integration
Date: 2025-01-25
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class BrokerType(str, Enum):
    """Tipo de broker"""

    CRYPTO = "crypto"  # Binance, Coinbase, Kraken
    FOREX = "forex"  # OANDA, FXCM, Forex.com
    STOCKS_US = "stocks_us"  # Alpaca, IBKR US
    STOCKS_EU = "stocks_eu"  # Degiro, Saxo, Trading 212


class OrderSide(str, Enum):
    """Lado de la orden"""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Tipo de orden"""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT = "take_profit"


class OrderStatus(str, Enum):
    """Estado de la orden"""

    PENDING = "pending"
    SUBMITTED = "submitted"
    ACK_RECEIVED = "ack_received"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


@dataclass
class Balance:
    """Balance de una cuenta"""

    currency: str
    available: Decimal
    locked: Decimal
    total: Decimal

    def __post_init__(self):
        """Validar que available + locked = total"""
        if self.available + self.locked != self.total:
            logger.error(
                "Balance inconsistency detected",
                extra={
                    "currency": self.currency,
                    "available": str(self.available),
                    "locked": str(self.locked),
                    "total": str(self.total),
                    "sum": str(self.available + self.locked),
                },
            )
            raise ValueError(
                f"Balance inconsistency: available ({self.available}) + "
                f"locked ({self.locked}) != total ({self.total})"
            )


@dataclass
class Ticker:
    """Precio de un activo"""

    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    timestamp: datetime
    volume: Optional[Decimal] = None


@dataclass
class Order:
    """Orden de trading"""

    order_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None  # Para LIMIT, STOP_LIMIT
    stop_price: Optional[Decimal] = None  # Para STOP_LOSS, STOP_LIMIT
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    avg_fill_price: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class OrderResult:
    """Resultado de una orden"""

    order_id: str
    status: OrderStatus
    message: Optional[str] = None
    execution_price: Optional[Decimal] = None
    filled_quantity: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class Position:
    """Posición abierta"""

    symbol: str
    quantity: Decimal
    avg_entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    side: OrderSide

    @property
    def market_value(self) -> Decimal:
        """Valor de mercado de la posición"""
        return self.quantity * self.current_price


@dataclass
class BrokerConfig:
    """Configuración de conexión al broker"""

    broker_type: BrokerType
    api_key: str
    api_secret: Optional[str] = None
    sandbox: bool = True  # SIEMPRE empezar en sandbox
    rate_limit_per_second: int = 10  # Límite de Rate Limit Governor
    websocket_enabled: bool = True
    shadow_mode: bool = False  # Shadow Mode: ejecuta sin operar de verdad


class BrokerError(Exception):
    """Error base del broker"""


class RateLimitError(BrokerError):
    """Error por exceder rate limit"""


class BrokerConnectionError(BrokerError):
    """Error de conexión"""


class OrderRejectedError(BrokerError):
    """Orden rechazada por el broker"""


class IBroker(ABC):
    """
    Interfaz Abstracta para TODOS los brokers.

    Esta es la DEFINICIÓN del contrato. Cualquier broker (Binance, Degiro, OANDA)
    DEBE implementar estos métodos.

    CRÍTICO: Esta interfaz está diseñada para funcionar con:
    - WAL (Write-Ahead Logging)
    - Boot Reconciler
    - Data Sanity Layer
    - Shadow Mode
    - Rate Limit Governor
    """

    # ========================================================================
    # METADATOS DEL BROKER
    # ========================================================================

    @abstractmethod
    def get_broker_type(self) -> BrokerType:
        """
        Obtener tipo de broker.

        Returns:
            BrokerType: CRYPTO, FOREX, STOCKS_US, STOCKS_EU
        """

    @abstractmethod
    def get_broker_name(self) -> str:
        """
        Obtener nombre del broker.

        Returns:
            str: 'binance', 'degiro', 'oanda', etc.
        """

    # ========================================================================
    # CONEXIÓN Y ESTADO
    # ========================================================================

    @abstractmethod
    async def connect(self, config: BrokerConfig) -> bool:
        """
        Establecer conexión con el broker.

        CRÍTICO: Este método debe:
        1. Validar API keys
        2. Establecer sesión REST API
        3. Establecer conexión WebSocket si está habilitado
        4. Inicializar Rate Limit Governor

        Args:
            config: Configuración de conexión

        Returns:
            bool: True si conexión exitosa
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Cerrar conexión con el broker.

        Debe:
        1. Cerrar sesión REST
        2. Cerrar WebSocket
        3. Cancelar suscripciones
        4. Limpiar recursos
        """

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Verificar si está conectado.

        Returns:
            bool: True si conectado
        """

    @abstractmethod
    async def ping(self) -> bool:
        """
        Ping al broker para verificar conexión.

        Returns:
            bool: True si el broker responde
        """

    # ========================================================================
    # DATOS DE CUENTA
    # ========================================================================

    @abstractmethod
    async def get_normalized_balance(self) -> dict[str, Balance]:
        """
        Obtener balance normalizado de la cuenta.

        CRÍTICO: Debe retornar balances en formato NORMALIZADO.
        Sin importar si el broker llama al BTC como "BTC", "BTCUSDT" o "XBT",
        aquí DEBE usar el Symbol Mapper interno.

        Returns:
            Dict[str, Balance]: key = currency (ej: "BTC", "EUR", "USD")
        """

    @abstractmethod
    async def get_account_id(self) -> str:
        """
        Obtener ID único de la cuenta.

        CRÍTICO para FIFO y Tax.

        Returns:
            str: ID de cuenta del broker
        """

    # ========================================================================
    # DATOS DE MERCADO
    # ========================================================================

    @abstractmethod
    async def get_live_ticker(self, symbol: str) -> Ticker:
        """
        Obtener precio en tiempo real de un activo.

        CRÍTICO:
        1. Si hay WebSocket conectado, usar datos del WebSocket (no polling REST)
        2. Aplicar Rate Limit Governor si no hay WebSocket
        3. Usar Symbol Mapper para convertir symbol interno a broker ticker

        Args:
            symbol: Symbol NORMALIZADO (ej: "BTC", no "BTCUSDT")

        Returns:
            Ticker: Precio bid/ask/last

        Raises:
            RateLimitError: Si excede rate limit
        """

    @abstractmethod
    async def get_historical_ohlcv(
        self, symbol: str, interval: str, start_date: datetime, end_date: datetime
    ) -> list[dict]:
        """
        Obtener datos históricos OHLCV.

        Args:
            symbol: Symbol NORMALIZADO
            interval: "1m", "5m", "1h", "1d", etc.
            start_date: Fecha inicio
            end_date: Fecha fin

        Returns:
            List[dict]: Lista de velas con keys: timestamp, open, high, low, close, volume
        """

    # ========================================================================
    # EJECUCIÓN DE ÓRDENES (CRÍTICO - CON WAL)
    # ========================================================================

    @abstractmethod
    async def execute_order_with_wal(self, order: Order, dry_run: bool = False) -> OrderResult:
        """
        Ejecutar orden CON Write-Ahead Logging.

        CRÍTICO: Este es el MÉTODO MÁS IMPORTANTE de la interfaz.

        La implementación DEBE seguir este orden EXACTO:

        1. PERSISTIR en WAL antes de llamar al broker:
           ```python
           await self.wal.write(OrderLog(
               transaction_id=order.order_id,
               state="SUBMITTING",
               timestamp=datetime.utcnow()
           ))
           ```

        2. Si shadow_mode=True, SIMULAR ejecución:
           ```python
           if self.config.shadow_mode:
               return await self._simulate_execution(order)
           ```

        3. Llamar a la API del broker
        4. PERSISTIR ACK_RECEIVED en WAL
        5. Retornar OrderResult

        Args:
            order: Orden a ejecutar
            dry_run: Si True, no ejecutar (solo validar)

        Returns:
            OrderResult: Resultado de la orden

        Raises:
            BrokerError: Si la orden falla
        """

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancelar orden existente.

        Args:
            order_id: ID de la orden a cancelar

        Returns:
            bool: True si cancelada exitosamente
        """

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """
        Obtener estado actual de una orden.

        CRÍTICO para Boot Reconciler.

        Args:
            order_id: ID de la orden

        Returns:
            OrderStatus: Estado actual
        """

    # ========================================================================
    # POSICIONES
    # ========================================================================

    @abstractmethod
    async def get_all_open_positions(self) -> list[Position]:
        """
        Obtener todas las posiciones abiertas.

        CRÍTICO para Boot Reconciler.
        Debe retornar posiciones con symbols NORMALIZADOS.

        Returns:
            List[Position]: Lista de posiciones abiertas
        """

    @abstractmethod
    async def close_position(self, symbol: str, quantity: Optional[Decimal] = None) -> OrderResult:
        """
        Cerrar posición (total o parcial).

        Args:
            symbol: Symbol NORMALIZADO
            quantity: Cantidad a cerrar (None = cerrar todo)

        Returns:
            OrderResult: Resultado de la orden de cierre
        """

    # ========================================================================
    # STREAMING (WEBSOCKET)
    # ========================================================================

    @abstractmethod
    async def start_ticker_stream(self, symbols: list[str], callback):
        """
        Iniciar stream de precios en tiempo real via WebSocket.

        CRÍTICO:
        1. NO usar polling REST (consume rate limits)
        2. Usar WebSocket del broker
        3. Llamar a callback por cada actualización

        Args:
            symbols: Lista de symbols NORMALIZADOS
            callback: Función a llamar con cada Ticker actualizado

        Example:
            ```python
            async def on_ticker(ticker: Ticker):
                logger.debug(f"{ticker.symbol}: {ticker.last}")

            await broker.start_ticker_stream(["BTC", "ETH"], on_ticker)
            ```
        """

    @abstractmethod
    async def stop_ticker_stream(self) -> None:
        """
        Detener stream de precios.

        Debe cerrar conexión WebSocket y limpiar recursos.
        """

    # ========================================================================
    # SYMBOL MAPPING (CRÍTICO PARA FIFO)
    # ========================================================================

    @abstractmethod
    def map_internal_to_broker(self, internal_symbol: str) -> str:
        """
        Convertir symbol interno a ticker del broker.

        CRÍTICO para FIFO y Tax.

        Example:
            Binance: "BTC" → "BTCUSDT"
            OANDA: "BTC" → "BTC_USD"
            IBKR: "BTC" → "IBKR:BTC"

        Args:
            internal_symbol: Symbol interno (ej: "BTC")

        Returns:
            str: Ticker del broker
        """

    @abstractmethod
    def map_broker_to_internal(self, broker_symbol: str) -> str:
        """
        Convertir ticker del broker a symbol interno.

        Args:
            broker_symbol: Ticker del broker (ej: "BTCUSDT")

        Returns:
            str: Symbol interno (ej: "BTC")
        """

    # ========================================================================
    # RATE LIMITING (CRÍTICO PARA NO SER BANEADO)
    # ========================================================================

    @abstractmethod
    async def acquire_rate_limit_token(self) -> None:
        """
        Adquirir token del Rate Limit Governor.

        CRÍTICO: Debe ser llamado ANTES de cada request REST.

        Usa Token Bucket Algorithm:
        - Si hay tokens disponibles, consumir 1 y continuar
        - Si no hay tokens, esperar hasta que haya

        Example:
            ```python
            async def get_live_ticker(self, symbol: str) -> Ticker:
                await self.acquire_rate_limit_token()  # <-- CRÍTICO
                # ... hacer request REST ...
            ```
        """

    @abstractmethod
    def get_rate_limit_stats(self) -> dict:
        """
        Obtener estadísticas de rate limiting.

        Returns:
            dict: {
                'tokens_remaining': int,
                'tokens_capacity': int,
                'requests_last_second': int,
                'blocked_requests': int
            }
        """

    # ========================================================================
    # SHADOW MODE (CRÍTICO PARA TESTING SEGURO)
    # ========================================================================

    @abstractmethod
    def is_shadow_mode_enabled(self) -> bool:
        """
        Verificar si Shadow Mode está habilitado.

        Shadow Mode = El bot cree que está operando en real con la API real,
        pero place_order intercepta la llamada, registra el WAL, simula el ACK,
        pero NO envía la orden.

        Returns:
            bool: True si shadow mode habilitado
        """

    @abstractmethod
    async def _simulate_execution(self, order: Order) -> OrderResult:
        """
        Simular ejecución de orden (Shadow Mode).

        Debe:
        1. Validar que la orden es válida
        2. Escribir en WAL (como si fuera real)
        3. Simular ACK_RECEIVED
        4. Retornar OrderResult simulado

        Args:
            order: Orden a simular

        Returns:
            OrderResult: Resultado simulado
        """


# ========================================================================
# HELPERS Y VALIDADORES
# ========================================================================


def validate_order(order: Order) -> tuple[bool, Optional[str]]:
    """
    Validar orden antes de enviar al broker.

    Args:
        order: Orden a validar

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    logger.debug(
        "Validating order",
        extra={
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "type": order.type.value,
            "quantity": str(order.quantity),
        },
    )
    if order.quantity <= 0:
        logger.warning(
            "Order validation failed: quantity must be positive",
            extra={"order_id": order.order_id, "quantity": str(order.quantity)},
        )
        return False, "Quantity must be positive"

    if order.type == OrderType.LIMIT and order.price is None:
        logger.warning(
            "Order validation failed: limit order requires price",
            extra={"order_id": order.order_id, "order_type": order.type.value},
        )
        return False, "Limit orders require a price"

    if order.type in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT] and order.stop_price is None:
        logger.warning(
            "Order validation failed: stop order requires stop_price",
            extra={"order_id": order.order_id, "order_type": order.type.value},
        )
        return False, "Stop orders require a stop_price"

    logger.debug(
        "Order validation passed", extra={"order_id": order.order_id, "symbol": order.symbol}
    )
    return True, None


def normalize_symbol(symbol: str) -> str:
    """
    Normalizar symbol a formato estándar.

    Elimina sufijos de broker (USDT, _USD, etc.)

    Args:
        symbol: Symbol del broker

    Returns:
        str: Symbol normalizado (ej: "BTC")
    """
    original_symbol = symbol
    # Eliminar sufijos comunes
    suffixes = ["USDT", "USD", "EUR", "GBP", "_USD", "_EUR", "_GBP"]
    for suffix in suffixes:
        if symbol.endswith(suffix):
            symbol = symbol[: -len(suffix)]
            break

    # Eliminar prefijos (ej: "IBKR:")
    if ":" in symbol:
        symbol = symbol.split(":")[1]

    normalized = symbol.upper()
    if original_symbol != normalized:
        logger.debug(
            "Symbol normalized", extra={"original": original_symbol, "normalized": normalized}
        )
    return normalized
