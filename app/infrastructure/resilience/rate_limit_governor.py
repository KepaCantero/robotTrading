"""
Rate Limit Governor - Token Bucket Algorithm + WebSocket First Strategy

CRÍTICO para evitar baneos de IP en Crypto brokers (Binance, Kraken, etc.)

Problema:
- Binance: 1200 requests/minuto = 20/segundo
- Kraken: Mucho más agresivo
- Si excedes el límite → IP baneada 24 horas

Solución:
1. Token Bucket Algorithm: Garantiza que nunca excedes X requests/segundo
2. WebSocket First Strategy: Usa WebSocket para datos en tiempo real (no consume REST rate limits)
3. Adaptive Rate Limiting: Ajusta dinámicamente según respuestas del broker

Author: SRE Feedback Integration
Date: 2025-01-25
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Excepción cuando se excede el rate limit"""


class RateLimitStrategy(str, Enum):
    """Estrategia de rate limiting"""

    TOKEN_BUCKET = "token_bucket"  # Token Bucket Algorithm
    LEAKY_BUCKET = "leaky_bucket"  # Leaky Bucket
    FIXED_WINDOW = "fixed_window"  # Fixed Window Counter
    SLIDING_WINDOW = "sliding_window"  # Sliding Window Log


@dataclass
class RateLimitConfig:
    """Configuración de Rate Limit Governor"""

    max_requests_per_second: int = 10  # Límite máximo (conservador)
    burst_capacity: int = 20  # Capacidad burst (tokens máximos)
    refill_rate: float = 10.0  # Tokens por segundo (refill rate)
    websocket_enabled: bool = True  # Usar WebSocket First Strategy
    adaptive_mode: bool = True  # Ajustar dinámicamente según respuestas
    ban_recovery_time: int = 86400  # 24 horas en segundos

    # Límites específicos por broker
    broker_limits: Dict[str, int] = field(
        default_factory=lambda: {
            'binance': 20,  # 20 requests/segundo
            'kraken': 10,  # Kraken es más agresivo
            'coinbase': 10,
            'oanda': 15,
            'degiro': 5,  # Degiro es muy lento
        }
    )


@dataclass
class TokenBucketState:
    """Estado del Token Bucket"""

    tokens: float = 20.0  # Tokens actuales
    last_refill: float = 0.0  # Timestamp del último refill
    capacity: int = 20  # Capacidad máxima

    # Estadísticas
    total_requests: int = 0
    blocked_requests: int = 0
    successful_requests: int = 0


class TokenBucketAlgorithm:
    """
    Token Bucket Algorithm para Rate Limiting.

    Ventajas:
    1. Permite bursts (hasta capacity tokens)
    2. Rate limit promedio = refill_rate
    3. Fácil de implementar y entender

    Algoritmo:
    1. Bucket tiene capacidad máxima de tokens
    2. Tokens se agregan a refill_rate por segundo
    3. Cada request consume 1 token
    4. Si no hay tokens, esperar
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.state = TokenBucketState(
            tokens=config.burst_capacity, last_refill=time.time(), capacity=config.burst_capacity
        )
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Adquirir un token.

        Args:
            timeout: Tiempo máximo de espera (None = infinito)

        Returns:
            bool: True si se adquirió el token

        Raises:
            RateLimitError: Si timeout expira
        """
        async with self._lock:
            # Refill tokens basado en tiempo transcurrido
            await self._refill()

            # Si hay tokens disponibles, consumir
            if self.state.tokens >= 1.0:
                self.state.tokens -= 1.0
                self.state.total_requests += 1
                self.state.successful_requests += 1
                logger.debug(
                    f"Token acquired. Remaining: {self.state.tokens:.2f}/{self.state.capacity}"
                )
                return True

            # No hay tokens, esperar refill
            self.state.blocked_requests += 1
            wait_time = self._calculate_wait_time()

            logger.warning(
                f"Rate limit reached. Waiting {wait_time:.2f}s for token refill. "
                f"Tokens: {self.state.tokens:.2f}/{self.state.capacity}"
            )

            if timeout is not None and wait_time > timeout:
                raise RateLimitError(
                    f"Timeout waiting for rate limit token (wait_time={wait_time:.2f}s > timeout={timeout}s)"
                )

            # Esperar y reintentar
            await asyncio.sleep(wait_time)
            await self._refill()

            if self.state.tokens >= 1.0:
                self.state.tokens -= 1.0
                self.state.total_requests += 1
                self.state.successful_requests += 1
                return True

            raise RateLimitError("Unable to acquire token after refill")

    async def _refill(self):
        """
        Refill tokens basado en tiempo transcurrido.

        Fórmula: tokens_added = (current_time - last_refill) * refill_rate
        """
        now = time.time()
        elapsed = now - self.state.last_refill

        if elapsed > 0:
            tokens_added = elapsed * self.config.refill_rate
            self.state.tokens = min(self.state.capacity, self.state.tokens + tokens_added)
            self.state.last_refill = now

            logger.debug(
                f"Refilled {tokens_added:.2f} tokens in {elapsed:.2f}s. "
                f"Current: {self.state.tokens:.2f}/{self.state.capacity}"
            )

    def _calculate_wait_time(self) -> float:
        """Calcular tiempo de espera para próximo token"""
        if self.state.tokens >= 1.0:
            return 0.0

        # Necesitamos al menos 1 token
        tokens_needed = 1.0 - self.state.tokens
        wait_time = tokens_needed / self.config.refill_rate

        return wait_time

    def get_stats(self) -> dict:
        """Obtener estadísticas del token bucket"""
        return {
            'tokens_remaining': self.state.tokens,
            'tokens_capacity': self.state.capacity,
            'total_requests': self.state.total_requests,
            'successful_requests': self.state.successful_requests,
            'blocked_requests': self.state.blocked_requests,
            'block_rate': (
                self.state.blocked_requests / self.state.total_requests
                if self.state.total_requests > 0
                else 0.0
            ),
            'utilization_pct': (
                (1 - self.state.tokens / self.state.capacity) * 100
                if self.state.capacity > 0
                else 0.0
            ),
        }


class WebSocketFirstStrategy:
    """
    WebSocket First Strategy para datos en tiempo real.

    Problema: Polling REST API cada segundo consume rate limits.
    Solución: Usar WebSocket para datos streaming (no consume rate limits REST).

    Arquitectura:
    1. Suscribir a WebSocket para symbols deseados
    2. Callback recibe datos en tiempo real
    3. Cache local de precios (para fallback)
    4. Si WebSocket falla, fallback a REST con rate limiting
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._websocket = None
        self._subscriptions: Dict[str, List[Callable]] = {}
        self._price_cache: Dict[str, tuple] = {}  # symbol -> (price, timestamp)
        self._is_connected = False
        self._use_websocket = config.websocket_enabled

    async def get_ticker(self, symbol: str, rest_fallback: Callable) -> Decimal:
        """
        Obtener ticker usando WebSocket First Strategy.

        Args:
            symbol: Symbol a consultar
            rest_fallback: Función para fallback REST (si WebSocket no disponible)

        Returns:
            Decimal: Precio actual

        Flow:
        1. Si WebSocket activo y dato fresco (< 1s), usar cache
        2. Si dato stale (> 1s), usar REST con rate limiting
        3. Si WebSocket no conectado, solo REST
        """
        if self._use_websocket and self._is_connected:
            cached_price, timestamp = self._price_cache.get(symbol, (None, 0))

            # Dato fresco (< 1 segundo)
            if cached_price is not None and (time.time() - timestamp) < 1.0:
                logger.debug(f"Using fresh WebSocket data for {symbol}")
                return Decimal(str(cached_price))

            # Dato stale, usar REST
            logger.debug(f"WebSocket data stale for {symbol}, using REST fallback")
            return await rest_fallback(symbol)

        # WebSocket no disponible, solo REST
        logger.debug(f"WebSocket not connected, using REST for {symbol}")
        return await rest_fallback(symbol)

    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """
        Suscribirse a actualizaciones de ticker via WebSocket.

        Args:
            symbol: Symbol a suscribir
            callback: Función a llamar con cada actualización
        """
        if symbol not in self._subscriptions:
            self._subscriptions[symbol] = []

        self._subscriptions[symbol].append(callback)
        logger.info(f"Subscribed to {symbol} ticker via WebSocket")

    async def start_websocket(self, websocket_url: str):
        """
        Iniciar conexión WebSocket.

        Args:
            websocket_url: URL del WebSocket del broker
        """
        if not self._use_websocket:
            logger.info("WebSocket disabled, using REST only")
            return

        try:
            import aiohttp

            self._websocket = await aiohttp.ClientSession().ws_connect(websocket_url)
            self._is_connected = True

            logger.info(f"WebSocket connected to {websocket_url}")

            # Task para procesar mensajes
            asyncio.create_task(self._process_messages())

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"WebSocket connection failed: {e}")
            self._is_connected = False

    async def _process_messages(self):
        """Procesar mensajes del WebSocket"""
        if not self._websocket:
            return

        try:
            async for msg in self._websocket:
                # aiohttp.WSMsgType.TEXT == 1, aiohttp.WSMsgType.ERROR == 4
                # Using literal values to avoid TYPE_CHECKING import issues
                if msg.type == 1:  # WSMsgType.TEXT
                    data = msg.json()
                    await self._handle_message(data)
                elif msg.type == 4:  # WSMsgType.ERROR
                    logger.error(f"WebSocket error: {self._websocket.exception()}")
                    break

        except OSError as e:
            logger.error(f"Error processing WebSocket messages: {e}")
        finally:
            self._is_connected = False

    async def _handle_message(self, data: dict):
        """Manejar mensaje del WebSocket"""
        # Extraer symbol y precio
        # Esto es broker-specific, cada broker tiene formato diferente
        if 'symbol' in data and 'price' in data:
            symbol = data['symbol']
            price = Decimal(str(data['price']))

            # Actualizar cache
            self._price_cache[symbol] = (float(price), time.time())

            # Llamar callbacks
            if symbol in self._subscriptions:
                for callback in self._subscriptions[symbol]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(symbol, price)
                        else:
                            callback(symbol, price)
                    except (asyncio.TimeoutError, OSError) as e:
                        logger.error(f"Error in ticker callback: {e}")

    async def stop_websocket(self):
        """Detener conexión WebSocket"""
        if self._websocket:
            await self._websocket.close()
            self._is_connected = False
            logger.info("WebSocket connection closed")


class AdaptiveRateLimiter:
    """
    Adaptive Rate Limiting basado en respuestas del broker.

    Si el broker empieza a responder con 429 (Too Many Requests),
    reducir automáticamente el rate limit.

    Estrategia:
    1. Monitorizar HTTP status codes
    2. Si detecta 429, reducir rate limit un 50%
    3. Si todo OK por 5 minutos, aumentar un 10%
    """

    def __init__(self, initial_rate: int = 10):
        self.current_rate = initial_rate
        self.initial_rate = initial_rate
        self._429_count = 0
        self._success_count = 0
        self._last_adjustment = time.time()

    async def record_response(self, status_code: int):
        """
        Registrar respuesta HTTP del broker.

        Args:
            status_code: HTTP status code
        """
        if status_code == 429:
            self._429_count += 1
            await self._adjust_for_429()
        elif 200 <= status_code < 300:
            self._success_count += 1
            await self._consider_increase()

    async def _adjust_for_429(self):
        """Reducir rate limit al detectar 429"""
        if self._429_count >= 3:
            old_rate = self.current_rate
            self.current_rate = max(1, int(self.current_rate * 0.5))

            logger.warning(
                f"Detected rate limit (429). Reducing rate: {old_rate} → {self.current_rate} req/s"
            )

            self._429_count = 0
            self._last_adjustment = time.time()

    async def _consider_increase(self):
        """Considerar aumentar rate limit después de período exitoso"""
        if time.time() - self._last_adjustment > 300 and self._success_count > 100:  # 5 minutos
            old_rate = self.current_rate
            self.current_rate = min(self.initial_rate, int(self.current_rate * 1.1))

            logger.info(f"Stable period. Increasing rate: {old_rate} → {self.current_rate} req/s")

            self._success_count = 0
            self._last_adjustment = time.time()


class RateLimitGovernor:
    """
    Rate Limit Governor - Componente principal.

    Combina:
    1. Token Bucket Algorithm
    2. WebSocket First Strategy
    3. Adaptive Rate Limiting

    Uso:
        ```python
        governor = RateLimitGovernor(
            broker_name='binance',
            config=RateLimitConfig(max_requests_per_second=20)
        )

        # Antes de cada request REST
        await governor.acquire_token()

        # Para streaming de datos
        await governor.subscribe_ticker('BTC', callback)

        # Si hay respuesta 429
        await governor.record_response(429)
        ```
    """

    def __init__(self, broker_name: str, config: Optional[RateLimitConfig] = None):
        self.broker_name = broker_name
        self.config = config or RateLimitConfig()

        # Ajustar límite según broker
        if broker_name in self.config.broker_limits:
            self.config.max_requests_per_second = self.config.broker_limits[broker_name]
            self.config.refill_rate = float(self.config.broker_limits[broker_name])

        # Componentes
        self.token_bucket = TokenBucketAlgorithm(self.config)
        self.websocket_strategy = WebSocketFirstStrategy(self.config)
        self.adaptive_limiter = AdaptiveRateLimiter(self.config.max_requests_per_second)

        logger.info(
            f"RateLimitGovernor initialized for {broker_name}: "
            f"{self.config.max_requests_per_second} req/s, "
            f"WebSocket={'enabled' if self.config.websocket_enabled else 'disabled'}"
        )

    async def acquire_token(self, timeout: Optional[float] = None) -> bool:
        """
        Adquirir token antes de hacer request REST.

        CRÍTICO: Llamar este método ANTES de cada request REST.

        Args:
            timeout: Tiempo máximo de espera

        Returns:
            bool: True si token adquirido

        Raises:
            RateLimitError: Si timeout expira
        """
        return await self.token_bucket.acquire(timeout=timeout)

    async def get_ticker(self, symbol: str, rest_fallback: Callable) -> Decimal:
        """
        Obtener ticker usando WebSocket First Strategy.

        Args:
            symbol: Symbol a consultar
            rest_fallback: Función REST fallback (con rate limiting)

        Returns:
            Decimal: Precio actual
        """
        return await self.websocket_strategy.get_ticker(symbol, rest_fallback)

    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """
        Suscribirse a actualizaciones de ticker.

        Args:
            symbol: Symbol
            callback: Función callback
        """
        await self.websocket_strategy.subscribe_ticker(symbol, callback)

    async def record_response(self, status_code: int):
        """
        Registrar respuesta HTTP para adaptive rate limiting.

        Args:
            status_code: HTTP status code
        """
        await self.adaptive_limiter.record_response(status_code)

    async def start_websocket(self, websocket_url: str):
        """
        Iniciar conexión WebSocket.

        Args:
            websocket_url: URL del WebSocket
        """
        await self.websocket_strategy.start_websocket(websocket_url)

    async def stop_websocket(self):
        """Detener WebSocket."""
        await self.websocket_strategy.stop_websocket()

    def get_stats(self) -> dict:
        """Obtener estadísticas completas."""
        return {
            'broker': self.broker_name,
            'configured_rate': self.config.max_requests_per_second,
            'current_rate': self.adaptive_limiter.current_rate,
            'websocket_connected': self.websocket_strategy._is_connected,
            'token_bucket': self.token_bucket.get_stats(),
            'adaptive': {
                'initial_rate': self.adaptive_limiter.initial_rate,
                'current_rate': self.adaptive_limiter.current_rate,
                '429_count': self.adaptive_limiter._429_count,
                'success_count': self.adaptive_limiter._success_count,
            },
        }

    def is_websocket_connected(self) -> bool:
        """Verificar si WebSocket está conectado."""
        return self.websocket_strategy._is_connected


# ============================================================================
# DECORADOR PARA RATE LIMITING (Fácil de usar)
# ============================================================================


def rate_limit(governor: RateLimitGovernor):
    """
    Decorador para aplicar rate limiting a una función async.

    Usage:
        ```python
        @rate_limit(governor)
        async def fetch_binance_price(symbol: str) -> Decimal:
            # ... implementation ...
        ```

    El decorador automáticamente llama governor.acquire_token() antes
    de ejecutar la función.
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            await governor.acquire_token()
            return await func(*args, **kwargs)

        return wrapper

    return decorator
