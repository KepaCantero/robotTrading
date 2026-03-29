"""
Messaging system for inter-module communication.
Uses Redis for pub/sub and ZeroMQ as fallback for high-throughput scenarios.
Optimized for single-instance deployment with memory constraints.
"""

import logging
import time
from threading import Thread
from typing import TYPE_CHECKING, Any, Callable, Optional

from app.security.secure_serialization import sign_and_dump, verify_and_load

# Fallback pattern: Try to import redis and zmq
# These are optional dependencies - the system works without them using in-memory fallback
try:
    import redis as _redis_module

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    _redis_module = None
    logging.warning("redis package not installed. Messaging system will use in-memory fallback.")

try:
    import zmq as _zmq_module

    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False
    _zmq_module = None
    logging.warning("zmq package not installed. ZeroMQ messaging disabled.")

if TYPE_CHECKING:
    from redis import Redis
    from zmq import Context, Socket

logger = logging.getLogger(__name__)


# Re-export functions for backward compatibility
__all__ = ["MessageBus", "get_message_bus", "sign_and_dump", "verify_and_load"]


class MessageBus:
    """
    Unified message bus for inter-module communication.
    Uses Redis pub/sub for most cases, ZeroMQ for high-frequency data.
    Falls back to in-memory message passing if dependencies are unavailable.
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        use_zmq: bool = False,
        zmq_port: int = 5555,
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.use_zmq = use_zmq
        self.redis_client: Optional[Redis[bytes]] = None
        self.redis_pubsub: Optional[Any] = None
        self.zmq_context: Optional[Context] = None
        self.zmq_socket: Optional[Socket] = None
        self._memory_subscribers: dict[str, list] = {}

        # Redis connection with fallback
        if REDIS_AVAILABLE and _redis_module is not None:
            try:
                self.redis_client = _redis_module.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=False,  # Binary mode for pickle
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    max_connections=10,
                )
                self.redis_client.ping()
                logger.info("Redis connected for messaging")
            except (ConnectionError, TimeoutError) as err:
                logger.warning(f"Redis connection failed: {err}. Using in-memory fallback.")
                self.redis_client = None
        else:
            logger.warning("Redis not installed. Using in-memory fallback.")

        # ZeroMQ setup if requested
        if self.use_zmq:
            if ZMQ_AVAILABLE and _zmq_module is not None:
                try:
                    self.zmq_context = _zmq_module.Context()
                    self.zmq_socket = self.zmq_context.socket(_zmq_module.PUB)
                    self.zmq_socket.bind(f"tcp://*:{zmq_port}")
                    logger.info(f"ZeroMQ PUB socket bound on port {zmq_port}")
                except (ConnectionError, TimeoutError) as err:
                    logger.warning(f"ZeroMQ setup failed: {err}. Using Redis fallback.")
                    self.zmq_context = None
                    self.zmq_socket = None
                    self.use_zmq = False
            else:
                logger.warning("ZeroMQ not installed. Using Redis fallback.")
                self.use_zmq = False

    def publish(self, channel: str, message: dict[str, Any]) -> bool:
        """
        Publish message to channel.

        Args:
            channel: Channel name (e.g., 'market-ticks', 'signals', 'orders')
            message: Message dictionary

        Returns:
            True if published successfully
        """
        logger.debug(
            "Publishing message to channel",
            extra={"channel": channel, "message_keys": list(message.keys())},
        )
        try:
            if (
                self.use_zmq
                and channel in ["market-ticks", "signals"]
                and self.zmq_socket is not None
                and _zmq_module is not None
            ):
                # Use ZeroMQ for high-frequency channels
                # SECURE: Use JSON+HMAC instead of pickle
                data = sign_and_dump({"channel": channel, "data": message})
                self.zmq_socket.send(data, _zmq_module.NOBLOCK)
                return True
            elif self.redis_client is not None:
                # Use Redis for most channels
                # SECURE: Use JSON+HMAC instead of pickle
                data = sign_and_dump(message)
                self.redis_client.publish(channel, data)
                return True
            else:
                # In-memory fallback
                if channel in self._memory_subscribers:
                    for callback in self._memory_subscribers[channel]:
                        try:
                            callback(message)
                        except Exception as err:
                            logger.error(
                                "Error in memory subscriber callback",
                                extra={"channel": channel, "error": str(err)},
                                exc_info=True,
                            )
                return True
        except (ConnectionError, TimeoutError) as err:
            logger.error(
                "Failed to publish to channel",
                extra={"channel": channel, "error_type": type(err).__name__},
            )
            return False

    def subscribe(
        self, channel: str, callback: Callable[[dict[str, Any]], None]
    ) -> Optional[Thread]:
        """
        Subscribe to channel and call callback for each message.

        Args:
            channel: Channel name
            callback: Function to call with message data

        Returns:
            Thread running the subscription, or None if using in-memory fallback
        """
        if (
            self.use_zmq
            and channel in ["market-ticks", "signals"]
            and self.zmq_context is not None
            and _zmq_module is not None
        ):
            return self._subscribe_zmq(channel, callback)
        elif self.redis_client is not None:
            return self._subscribe_redis(channel, callback)
        else:
            # In-memory fallback
            if channel not in self._memory_subscribers:
                self._memory_subscribers[channel] = []
            self._memory_subscribers[channel].append(callback)
            logger.info(f"Registered in-memory subscriber for channel: {channel}")
            return None

    def _subscribe_redis(self, channel: str, callback: Callable[[dict[str, Any]], None]) -> Thread:
        """Subscribe using Redis pub/sub."""
        logger.info("Starting Redis subscription", extra={"channel": channel})

        def _run() -> None:
            if self.redis_client is None:
                return
            try:
                pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(channel)

                for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            # SECURE: Use JSON+HMAC verification instead of pickle
                            data = verify_and_load(message["data"])
                            callback(data)
                        except ValueError as err:
                            logger.error(
                                "Security error processing Redis message",
                                extra={"channel": channel, "error": str(err)},
                                exc_info=True,
                            )
                        except (ConnectionError, TimeoutError) as err:
                            logger.error(
                                "Error processing Redis message",
                                extra={"channel": channel, "error_type": type(err).__name__},
                            )
            except (ConnectionError, TimeoutError) as err:
                logger.error(
                    "Redis subscription error",
                    extra={"channel": channel, "error_type": type(err).__name__},
                )

        thread = Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def _subscribe_zmq(self, channel: str, callback: Callable[[dict[str, Any]], None]) -> Thread:
        """
        Subscribe using ZeroMQ.

        Note: This runs in a separate thread (not async context), so time.sleep()
        is appropriate here. The thread-based design avoids blocking the main event loop.
        """
        if _zmq_module is None or self.zmq_context is None:
            raise RuntimeError("ZeroMQ not available")

        def _run() -> None:
            try:
                socket = self.zmq_context.socket(_zmq_module.SUB)
                socket.connect("tcp://localhost:5555")
                socket.setsockopt_string(_zmq_module.SUBSCRIBE, channel)

                while True:
                    try:
                        data = socket.recv(_zmq_module.NOBLOCK)
                        # SECURE: Use JSON+HMAC verification instead of pickle
                        msg = verify_and_load(data)
                        if msg.get("channel") == channel:
                            callback(msg.get("data", {}))
                    except _zmq_module.Again:
                        time.sleep(0.001)  # 1ms sleep to avoid CPU spinning
                        # Note: time.sleep() is acceptable here because this runs
                        # in a dedicated thread, not in an async event loop
                    except ValueError as err:
                        logger.error(
                            "Security error processing ZMQ message",
                            extra={"channel": channel, "error": str(err)},
                            exc_info=True,
                        )
                    except OSError as err:
                        # Covers FileNotFoundError, PermissionError, IOError, IsADirectoryError
                        logger.error(
                            "Error processing ZMQ message",
                            extra={"channel": channel, "error_type": type(err).__name__},
                        )
            except OSError as err:
                # Covers FileNotFoundError, PermissionError, IOError, IsADirectoryError
                logger.error(
                    "ZMQ subscription error",
                    extra={"channel": channel, "error_type": type(err).__name__},
                )

        thread = Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def close(self) -> None:
        """Close connections."""
        logger.info(
            "Closing MessageBus connections",
            extra={
                "has_redis": self.redis_client is not None,
                "has_zmq": self.zmq_socket is not None,
            },
        )
        if self.redis_pubsub is not None:
            self.redis_pubsub.close()
        if self.redis_client is not None:
            self.redis_client.close()
        if self.zmq_socket is not None:
            self.zmq_socket.close()
        if self.zmq_context is not None:
            self.zmq_context.term()


# Global message bus instance
_message_bus: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """Get or create global message bus instance."""
    global _message_bus
    logger.debug("Getting message bus instance", extra={"exists": _message_bus is not None})
    if _message_bus is None:
        import os

        _message_bus = MessageBus(
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            use_zmq=os.getenv("USE_ZMQ", "false").lower() == "true",
        )
    return _message_bus
