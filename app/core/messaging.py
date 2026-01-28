"""
Messaging system for inter-module communication.
Uses Redis for pub/sub and ZeroMQ as fallback for high-throughput scenarios.
Optimized for single-instance deployment with memory constraints.
"""

import logging
import time
from threading import Thread
from typing import Any, Callable, Dict, Optional

from .secure_serialization import sign_and_dump, verify_and_load

# Fallback pattern: Try to import redis and zmq
try:
    import redis  # noqa: F401

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore
    logging.warning("redis package not installed. Messaging system will use in-memory fallback.")

try:
    import zmq  # noqa: F401

    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False
    zmq = None  # type: ignore
    logging.warning("zmq package not installed. ZeroMQ messaging disabled.")

logger = logging.getLogger(__name__)


# Re-export functions for backward compatibility
__all__ = ['sign_and_dump', 'verify_and_load', 'MessageBus', 'get_message_bus']


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
        self.redis_client = None
        self.redis_pubsub = None
        self.zmq_context = None
        self.zmq_socket = None
        self._memory_subscribers: Dict[str, list] = {}

        # Redis connection with fallback
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(  # type: ignore
                    host=redis_host,
                    port=redis_port,
                    decode_responses=False,  # Binary mode for pickle
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    max_connections=10,
                )
                self.redis_client.ping()
                logger.info("✅ Redis connected for messaging")
            except (ConnectionError, TimeoutError) as e:
                logger.warning(f"⚠️ Redis connection failed: {e}. Using in-memory fallback.")
                self.redis_client = None
        else:
            logger.warning("⚠️ Redis not installed. Using in-memory fallback.")

        # ZeroMQ setup if requested
        if self.use_zmq:
            if ZMQ_AVAILABLE:
                try:
                    self.zmq_context = zmq.Context()  # type: ignore
                    self.zmq_socket = self.zmq_context.socket(zmq.PUB)  # type: ignore
                    self.zmq_socket.bind(f"tcp://*:{zmq_port}")
                    logger.info(f"✅ ZeroMQ PUB socket bound on port {zmq_port}")
                except (ConnectionError, TimeoutError) as e:
                    logger.warning(f"⚠️ ZeroMQ setup failed: {e}. Using Redis fallback.")
                    self.zmq_context = None
                    self.zmq_socket = None
                    self.use_zmq = False
            else:
                logger.warning("⚠️ ZeroMQ not installed. Using Redis fallback.")
                self.use_zmq = False

    def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """
        Publish message to channel.

        Args:
            channel: Channel name (e.g., 'market-ticks', 'signals', 'orders')
            message: Message dictionary

        Returns:
            True if published successfully
        """
        try:
            if self.use_zmq and channel in ['market-ticks', 'signals'] and self.zmq_socket:
                # Use ZeroMQ for high-frequency channels
                # SECURE: Use JSON+HMAC instead of pickle
                data = sign_and_dump({'channel': channel, 'data': message})
                self.zmq_socket.send(data, zmq.NOBLOCK)  # type: ignore
                return True
            elif self.redis_client:
                # Use Redis for most channels
                # SECURE: Use JSON+HMAC instead of pickle
                data = sign_and_dump(message)
                self.redis_client.publish(channel, data)  # type: ignore
                return True
            else:
                # In-memory fallback
                if channel in self._memory_subscribers:
                    for callback in self._memory_subscribers[channel]:
                        try:
                            callback(message)
                        except Exception as e:
                            logger.error(f"Error in memory subscriber callback: {e}")
                return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            return False

    def subscribe(
        self, channel: str, callback: Callable[[Dict[str, Any]], None]
    ) -> Optional[Thread]:
        """
        Subscribe to channel and call callback for each message.

        Args:
            channel: Channel name
            callback: Function to call with message data

        Returns:
            Thread running the subscription, or None if using in-memory fallback
        """
        if self.use_zmq and channel in ['market-ticks', 'signals'] and self.zmq_context:
            return self._subscribe_zmq(channel, callback)
        elif self.redis_client:
            return self._subscribe_redis(channel, callback)
        else:
            # In-memory fallback
            if channel not in self._memory_subscribers:
                self._memory_subscribers[channel] = []
            self._memory_subscribers[channel].append(callback)
            logger.info(f"Registered in-memory subscriber for channel: {channel}")
            return None

    def _subscribe_redis(self, channel: str, callback: Callable) -> Thread:
        """Subscribe using Redis pub/sub."""

        def _run():
            try:
                pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(channel)

                for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            # SECURE: Use JSON+HMAC verification instead of pickle
                            data = verify_and_load(message['data'])
                            callback(data)
                        except ValueError as e:
                            logger.error(f"Security error processing Redis message: {e}")
                        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
                            logger.error(f"Error processing Redis message: {e}")
            except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
                logger.error(f"Redis subscription error: {e}")

        thread = Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def _subscribe_zmq(self, channel: str, callback: Callable) -> Thread:
        """
        Subscribe using ZeroMQ.

        Note: This runs in a separate thread (not async context), so time.sleep()
        is appropriate here. The thread-based design avoids blocking the main event loop.
        """

        def _run():
            try:
                socket = self.zmq_context.socket(zmq.SUB)
                socket.connect("tcp://localhost:5555")
                socket.setsockopt_string(zmq.SUBSCRIBE, channel)

                while True:
                    try:
                        data = socket.recv(zmq.NOBLOCK)
                        # SECURE: Use JSON+HMAC verification instead of pickle
                        msg = verify_and_load(data)
                        if msg.get('channel') == channel:
                            callback(msg.get('data', {}))
                    except zmq.Again:
                        time.sleep(0.001)  # 1ms sleep to avoid CPU spinning
                        # Note: time.sleep() is acceptable here because this runs
                        # in a dedicated thread, not in an async event loop
                    except ValueError as e:
                        logger.error(f"Security error processing ZMQ message: {e}")
                    except (
                        FileNotFoundError,
                        PermissionError,
                        IOError,
                        OSError,
                        IsADirectoryError,
                    ) as e:
                        logger.error(f"Error processing ZMQ message: {e}")
            except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
                logger.error(f"ZMQ subscription error: {e}")

        thread = Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def close(self):
        """Close connections."""
        if self.redis_pubsub:
            self.redis_pubsub.close()
        if self.redis_client:
            self.redis_client.close()
        if self.zmq_socket:
            self.zmq_socket.close()
        if self.zmq_context:
            self.zmq_context.term()


# Global message bus instance
_message_bus: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """Get or create global message bus instance."""
    global _message_bus
    if _message_bus is None:
        import os

        _message_bus = MessageBus(
            redis_host=os.getenv('REDIS_HOST', 'localhost'),
            redis_port=int(os.getenv('REDIS_PORT', '6379')),
            use_zmq=os.getenv('USE_ZMQ', 'false').lower() == 'true',
        )
    return _message_bus
