"""
WebSocket Streaming - Sistema de streaming real-time para DataEngine.

Proporciona:
- WebSocket server para streaming de datos en tiempo real
- Suscripciones a símbolos
- Broadcasting de updates
- Manejo de reconexiones
"""

import asyncio
import contextlib
import json
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
from requests.exceptions import HTTPError, RequestException

logger = logging.getLogger(__name__)


class WebSocketStreamingManager:
    """
    Manager para streaming de datos en tiempo real vía WebSocket.

    Gestiona conexiones WebSocket y broadcasting de datos.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Inicializar streaming manager.

        Args:
            config: Configuración con:
                - heartbeat_interval: Intervalo de heartbeat en segundos (desde YAML)
                - max_connections: Máximo de conexiones (desde YAML)
                - websocket_path: Ruta del endpoint WebSocket (desde YAML)
                - max_connection_code: Código HTTP para máximo alcanzado (desde YAML)
                - connection_reason_max_reached: Razón para máximo alcanzado (desde YAML)
        """
        config = config or {}
        self.config = config

        # Todos los valores deben venir de config, NO hardcodeados
        if "heartbeat_interval" not in config:
            raise ValueError("heartbeat_interval debe estar en config (cargado desde YAML)")
        if "max_connections" not in config:
            raise ValueError("max_connections debe estar en config (cargado desde YAML)")

        self.heartbeat_interval = config["heartbeat_interval"]
        self.max_connections = config["max_connections"]
        self.websocket_path = config.get("websocket_path", "/ws/data/{client_id}")
        self.max_connection_code = config.get("max_connection_code", 1008)
        self.connection_reason_max_reached = config.get(
            "connection_reason_max_reached", "Maximum connections reached"
        )

        # Conexiones activas: {websocket_id: {websocket, subscriptions: Set[str]}}
        self.active_connections: dict[str, dict[str, Any]] = {}

        # Suscripciones por símbolo: {symbol: Set[websocket_id]}
        self.symbol_subscriptions: dict[str, set[str]] = {}

        # Router para endpoints WebSocket
        self.router = APIRouter()
        self._setup_routes()

        self._heartbeat_task = None
        self._running = False

        logger.info(
            f"WebSocketStreamingManager inicializado (max_connections={self.max_connections})"
        )

    def _setup_routes(self) -> None:
        """Configurar rutas WebSocket."""

        # Usar path desde config (mantener {client_id} como parámetro de ruta)
        @self.router.websocket(self.websocket_path)
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            """Endpoint WebSocket para streaming."""
            await self.handle_connection(websocket, client_id)

    async def start(self) -> None:
        """Iniciar streaming manager."""
        if self._running:
            return

        self._running = True

        # Iniciar heartbeat task
        if self.heartbeat_interval > 0:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info("WebSocketStreamingManager iniciado")

    async def stop(self) -> None:
        """Detener streaming manager."""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task

        # Cerrar todas las conexiones
        for connection_id in list(self.active_connections.keys()):
            await self.disconnect(connection_id)

        logger.info("WebSocketStreamingManager detenido")

    async def handle_connection(self, websocket: WebSocket, client_id: str) -> None:
        """
        Manejar nueva conexión WebSocket.

        Args:
            websocket: WebSocket connection
            client_id: ID del cliente
        """
        if len(self.active_connections) >= self.max_connections:
            await websocket.close(
                code=self.max_connection_code, reason=self.connection_reason_max_reached
            )
            return

        await websocket.accept()

        self.active_connections[client_id] = {
            "websocket": websocket,
            "subscriptions": set(),
            "connected_at": datetime.utcnow(),
        }

        logger.info(f"Cliente {client_id} conectado vía WebSocket")

        try:
            # Enviar mensaje de bienvenida
            await self._send_message(
                client_id,
                {
                    "type": "connected",
                    "client_id": client_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            # Loop de mensajes
            while True:
                message = await websocket.receive_text()
                await self._handle_message(client_id, message)

        except WebSocketDisconnect:
            logger.info(f"Cliente {client_id} desconectado")
            await self.disconnect(client_id)
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.error(f"Error en conexión {client_id}: {e}")
            await self.disconnect(client_id)

    async def _handle_message(self, client_id: str, message: str) -> None:
        """
        Manejar mensaje recibido.

        Args:
            client_id: ID del cliente
            message: Mensaje JSON
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "subscribe":
                symbols = data.get("symbols", [])
                await self.subscribe(client_id, symbols)

            elif msg_type == "unsubscribe":
                symbols = data.get("symbols", [])
                await self.unsubscribe(client_id, symbols)

            elif msg_type == "ping":
                await self._send_message(
                    client_id, {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
                )

            else:
                logger.warning(f"Tipo de mensaje desconocido: {msg_type}")

        except json.JSONDecodeError:
            logger.warning(f"Mensaje JSON inválido de {client_id}")
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error procesando mensaje de {client_id}: {e}")

    async def subscribe(self, client_id: str, symbols: list[str]) -> bool:
        """
        Suscribir cliente a símbolos.

        Args:
            client_id: ID del cliente
            symbols: Lista de símbolos

        Returns:
            True si se suscribió correctamente
        """
        if client_id not in self.active_connections:
            return False

        connection = self.active_connections[client_id]

        for symbol in symbols:
            connection["subscriptions"].add(symbol)

            if symbol not in self.symbol_subscriptions:
                self.symbol_subscriptions[symbol] = set()
            self.symbol_subscriptions[symbol].add(client_id)

        # Confirmar suscripción
        await self._send_message(
            client_id,
            {"type": "subscribed", "symbols": symbols, "timestamp": datetime.utcnow().isoformat()},
        )

        logger.info(f"Cliente {client_id} suscrito a {len(symbols)} símbolos")
        return True

    async def unsubscribe(self, client_id: str, symbols: list[str]) -> bool:
        """
        Desuscribir cliente de símbolos.

        Args:
            client_id: ID del cliente
            symbols: Lista de símbolos

        Returns:
            True si se desuscribió correctamente
        """
        if client_id not in self.active_connections:
            return False

        connection = self.active_connections[client_id]

        for symbol in symbols:
            connection["subscriptions"].discard(symbol)

            if symbol in self.symbol_subscriptions:
                self.symbol_subscriptions[symbol].discard(client_id)
                if not self.symbol_subscriptions[symbol]:
                    del self.symbol_subscriptions[symbol]

        # Confirmar desuscripción
        await self._send_message(
            client_id,
            {
                "type": "unsubscribed",
                "symbols": symbols,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        logger.info(f"Cliente {client_id} desuscrito de {len(symbols)} símbolos")
        return True

    async def disconnect(self, client_id: str) -> None:
        """
        Desconectar cliente.

        Args:
            client_id: ID del cliente
        """
        if client_id not in self.active_connections:
            return

        connection = self.active_connections[client_id]

        # Desuscribir de todos los símbolos
        for symbol in list(connection["subscriptions"]):
            if symbol in self.symbol_subscriptions:
                self.symbol_subscriptions[symbol].discard(client_id)
                if not self.symbol_subscriptions[symbol]:
                    del self.symbol_subscriptions[symbol]

        # Cerrar WebSocket
        try:
            await connection["websocket"].close()
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.warning(f"Error cerrando WebSocket de {client_id}: {e}")

        del self.active_connections[client_id]
        logger.info(f"Cliente {client_id} desconectado")

    async def broadcast_quote(self, symbol: str, quote_data: dict[str, Any]) -> int:
        """
        Broadcast quote a todos los suscriptores.

        Args:
            symbol: Símbolo
            quote_data: Datos del quote

        Returns:
            Número de clientes que recibieron el mensaje
        """
        if symbol not in self.symbol_subscriptions:
            return 0

        message = {
            "type": "quote",
            "symbol": symbol,
            "data": quote_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        count = 0
        disconnected_clients = []

        for client_id in list(self.symbol_subscriptions[symbol]):
            if await self._send_message(client_id, message):
                count += 1
            else:
                disconnected_clients.append(client_id)

        # Limpiar conexiones desconectadas
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

        return count

    async def broadcast_ohlcv(self, symbol: str, ohlcv_data: list[dict[str, Any]]) -> int:
        """
        Broadcast OHLCV data a todos los suscriptores.

        Args:
            symbol: Símbolo
            ohlcv_data: Datos OHLCV

        Returns:
            Número de clientes que recibieron el mensaje
        """
        if symbol not in self.symbol_subscriptions:
            return 0

        message = {
            "type": "ohlcv",
            "symbol": symbol,
            "data": ohlcv_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        count = 0
        disconnected_clients = []

        for client_id in list(self.symbol_subscriptions[symbol]):
            if await self._send_message(client_id, message):
                count += 1
            else:
                disconnected_clients.append(client_id)

        # Limpiar conexiones desconectadas
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

        return count

    async def _send_message(self, client_id: str, message: dict[str, Any]) -> bool:
        """
        Enviar mensaje a cliente.

        Args:
            client_id: ID del cliente
            message: Mensaje a enviar

        Returns:
            True si se envió correctamente
        """
        if client_id not in self.active_connections:
            return False

        try:
            websocket = self.active_connections[client_id]["websocket"]
            await websocket.send_json(message)
            return True
        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Error enviando mensaje a {client_id}: {e}")
            return False

    async def _heartbeat_loop(self) -> None:
        """Loop de heartbeat para mantener conexiones vivas."""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # Enviar heartbeat a todas las conexiones
                for client_id in list(self.active_connections.keys()):
                    await self._send_message(
                        client_id, {"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()}
                    )

            except asyncio.CancelledError:
                break
            except (asyncio.TimeoutError, OSError) as e:
                logger.error(f"Error en heartbeat loop: {e}")

    def get_status(self) -> dict[str, Any]:
        """Obtener estado del streaming manager."""
        return {
            "active_connections": len(self.active_connections),
            "total_subscriptions": sum(len(subs) for subs in self.symbol_subscriptions.values()),
            "symbols_subscribed": len(self.symbol_subscriptions),
            "max_connections": self.max_connections,
            "running": self._running,
        }
