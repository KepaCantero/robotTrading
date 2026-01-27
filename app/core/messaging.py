"""
Messaging system for inter-module communication.
Uses Redis for pub/sub and ZeroMQ as fallback for high-throughput scenarios.
Optimized for single-instance deployment with memory constraints.
"""

import logging
import os
import time
from threading import Thread
from typing import Any, Callable, Dict, Optional

from .secure_serialization import sign_and_dump, verify_and_load

try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    import zmq

    HAS_ZMQ = True
except ImportError:
    HAS_ZMQ = False

logger = logging.getLogger(__name__)


# Re-export functions for backward compatibility
__all__ = ['sign_and_dump', 'verify_and_load', 'MessageBus', 'get_message_bus']


class MessageBus:
    """
    Unified message bus for inter-module communication.
    Uses Redis pub/sub for most cases, ZeroMQ for high-frequency data.
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
        self.use_zmq = use_zmq and HAS_ZMQ
        self.redis_client = None
        self.redis_pubsub = None
        self.zmq_context = None
        self.zmq_socket = None

        if HAS_REDIS:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=False,  # Binary mode for pickle
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    max_connections=10,
                )
                self.redis_client.ping()
                logger.info("✅ Redis connected for messaging")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}, falling back to in-memory")
                self.redis_client = None

        if self.use_zmq:
            try:
                self.zmq_context = zmq.Context()
                self.zmq_socket = self.zmq_context.socket(zmq.PUB)
                self.zmq_socket.bind(f"tcp://*:{zmq_port}")
                logger.info(f"✅ ZeroMQ PUB socket bound on port {zmq_port}")
            except Exception as e:
                logger.warning(f"⚠️ ZeroMQ setup failed: {e}")
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
            if self.use_zmq and channel in ['market-ticks', 'signals']:
                # Use ZeroMQ for high-frequency channels
                # SECURE: Use JSON+HMAC instead of pickle
                data = sign_and_dump({'channel': channel, 'data': message})
                self.zmq_socket.send(data, zmq.NOBLOCK)
                return True
            elif self.redis_client:
                # Use Redis for most channels
                # SECURE: Use JSON+HMAC instead of pickle
                data = sign_and_dump(message)
                self.redis_client.publish(channel, data)
                return True
            else:
                logger.warning(f"No messaging backend available for channel: {channel}")
                return False
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            return False

    def subscribe(self, channel: str, callback: Callable[[Dict[str, Any]], None]) -> Thread:
        """
        Subscribe to channel and call callback for each message.

        Args:
            channel: Channel name
            callback: Function to call with message data

        Returns:
            Thread running the subscription
        """
        if self.use_zmq and channel in ['market-ticks', 'signals']:
            return self._subscribe_zmq(channel, callback)
        elif self.redis_client:
            return self._subscribe_redis(channel, callback)
        else:
            logger.warning(f"No messaging backend available for subscription: {channel}")
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
                        except Exception as e:
                            logger.error(f"Error processing Redis message: {e}")
            except Exception as e:
                logger.error(f"Redis subscription error: {e}")

        thread = Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def _subscribe_zmq(self, channel: str, callback: Callable) -> Thread:
        """Subscribe using ZeroMQ."""

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
                    except ValueError as e:
                        logger.error(f"Security error processing ZMQ message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing ZMQ message: {e}")
            except Exception as e:
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
