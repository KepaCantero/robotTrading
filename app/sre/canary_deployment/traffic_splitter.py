"""
Traffic Splitter - Canary Traffic Routing

Implements traffic splitting for canary deployments using various strategies.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class SplitStrategy(str, Enum):
    """Traffic split strategies."""

    PERCENTAGE = "percentage"  # Random by percentage
    USER_ID = "user_id"  # Hash-based on user ID
    HEADER = "header"  # Based on request header
    COOKIE = "cookie"  # Based on cookie
    IP_HASH = "ip_hash"  # Hash-based on IP


@dataclass
class TrafficConfig:
    """Configuration for traffic splitting."""

    strategy: SplitStrategy
    canary_percentage: Decimal  # 0.0 to 1.0
    baseline_percentage: Decimal  # 0.0 to 1.0

    # Strategy-specific config
    header_name: str | None = None  # For HEADER strategy
    cookie_name: str | None = None  # For COOKIE strategy
    user_id_field: str | None = None  # For USER_ID strategy

    # Sticky sessions
    enable_sticky_sessions: bool = True
    sticky_duration_minutes: int = 60

    # Whitelist for canary access
    whitelisted_users: list[str] = field(default_factory=list)
    whitelisted_ips: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy": self.strategy.value,
            "canary_percentage": f"{self.canary_percentage * 100:.1f}%",
            "baseline_percentage": f"{self.baseline_percentage * 100:.1f}%",
            "header_name": self.header_name,
            "cookie_name": self.cookie_name,
            "user_id_field": self.user_id_field,
            "sticky_sessions": self.enable_sticky_sessions,
            "sticky_duration_minutes": self.sticky_duration_minutes,
            "whitelisted_users": len(self.whitelisted_users),
            "whitelisted_ips": len(self.whitelisted_ips),
        }


@dataclass
class RoutingDecision:
    """Decision for routing a request."""

    route_to_canary: bool
    strategy_used: SplitStrategy
    reason: str
    session_sticky: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "canary": self.route_to_canary,
            "strategy": self.strategy_used.value,
            "reason": self.reason,
            "sticky": self.session_sticky,
        }


class TrafficSplitter:
    """
    Traffic splitter for canary deployments.

    Responsibilities:
    - Route requests to canary or baseline based on strategy
    - Support multiple splitting strategies
    - Sticky session management
    - Whitelist support

    Usage:
        splitter = TrafficSplitter(config)
        decision = await splitter.route_request(request_context)
    """

    def __init__(
        self,
        config: TrafficConfig,
        db_path: str = "data/traffic_splitter.db",
    ):
        """
        Initialize traffic splitter.

        Args:
            config: Traffic configuration
            db_path: Path to database for sticky sessions
        """
        self.config = config
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}")

        # Validate percentages
        if config.canary_percentage + config.baseline_percentage != Decimal("1"):
            raise ValueError("Canary and baseline percentages must sum to 1.0")

    async def initialize(self) -> None:
        """Initialize traffic splitter."""
        try:
            await self._init_database()
            self.logger.info("TrafficSplitter initialized")
        except (asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error initializing: {e}")
            raise

    async def _init_database(self) -> None:
        """Initialize database for sticky sessions."""
        try:
            from pathlib import Path

            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sticky_sessions (
                        session_id TEXT PRIMARY KEY,
                        route_to_canary INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL
                    )
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sticky_sessions_expires
                    ON sticky_sessions(expires_at)
                """
                )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def route_request(
        self,
        request_context: dict[str, Any],
    ) -> RoutingDecision:
        """
        Decide where to route a request.

        Args:
            request_context: Request context containing:
                - user_id: Optional user ID
                - headers: Dict of headers
                - cookies: Dict of cookies
                - ip: Client IP address
                - session_id: Session ID for sticky sessions

        Returns:
            RoutingDecision
        """
        # Check whitelist first
        if self._is_whitelisted(request_context):
            return RoutingDecision(
                route_to_canary=True,
                strategy_used=SplitStrategy.USER_ID,
                reason="Whitelisted user/IP",
            )

        # Check sticky session
        if self.config.enable_sticky_sessions:
            session_id = request_context.get("session_id")
            if session_id:
                sticky_decision = await self._get_sticky_decision(session_id)
                if sticky_decision is not None:
                    return RoutingDecision(
                        route_to_canary=sticky_decision,
                        strategy_used=self.config.strategy,
                        reason=f"Sticky session: {session_id}",
                        session_sticky=True,
                    )

        # Apply strategy
        route_to_canary = await self._apply_strategy(request_context)

        # Store sticky decision
        if self.config.enable_sticky_sessions and session_id:
            await self._set_sticky_decision(session_id, route_to_canary)

        return RoutingDecision(
            route_to_canary=route_to_canary,
            strategy_used=self.config.strategy,
            reason=f"{self.config.strategy.value} strategy",
        )

    def _is_whitelisted(self, request_context: dict[str, Any]) -> bool:
        """Check if request is whitelisted for canary."""
        user_id = request_context.get("user_id")
        if user_id and user_id in self.config.whitelisted_users:
            return True

        ip = request_context.get("ip")
        return bool(ip and ip in self.config.whitelisted_ips)

    async def _apply_strategy(self, request_context: dict[str, Any]) -> bool:
        """Apply routing strategy."""
        if self.config.strategy == SplitStrategy.PERCENTAGE:
            return await self._percentage_strategy()

        elif self.config.strategy == SplitStrategy.USER_ID:
            return await self._user_id_strategy(request_context)

        elif self.config.strategy == SplitStrategy.HEADER:
            return await self._header_strategy(request_context)

        elif self.config.strategy == SplitStrategy.COOKIE:
            return await self._cookie_strategy(request_context)

        elif self.config.strategy == SplitStrategy.IP_HASH:
            return await self._ip_hash_strategy(request_context)

        else:
            # Default to percentage
            return await self._percentage_strategy()

    async def _percentage_strategy(self) -> bool:
        """Random percentage-based routing."""
        return random.random() < float(self.config.canary_percentage)

    async def _user_id_strategy(self, request_context: dict[str, Any]) -> bool:
        """Hash-based routing on user ID."""
        user_id = request_context.get("user_id")
        if not user_id:
            # Fall back to percentage if no user ID
            return await self._percentage_strategy()

        # Hash user ID and check if falls in canary range
        hash_value = int(hashlib.sha256(str(user_id).encode()).hexdigest(), 16)
        canary_threshold = int(float(self.config.canary_percentage) * (2**256))

        return hash_value < canary_threshold

    async def _header_strategy(self, request_context: dict[str, Any]) -> bool:
        """Header-based routing."""
        if not self.config.header_name:
            return await self._percentage_strategy()

        headers = request_context.get("headers", {})
        header_value = headers.get(self.config.header_name)

        if not header_value:
            return await self._percentage_strategy()

        # Hash header value
        hash_value = int(hashlib.sha256(str(header_value).encode()).hexdigest(), 16)
        canary_threshold = int(float(self.config.canary_percentage) * (2**256))

        return hash_value < canary_threshold

    async def _cookie_strategy(self, request_context: dict[str, Any]) -> bool:
        """Cookie-based routing."""
        if not self.config.cookie_name:
            return await self._percentage_strategy()

        cookies = request_context.get("cookies", {})
        cookie_value = cookies.get(self.config.cookie_name)

        if not cookie_value:
            return await self._percentage_strategy()

        # Hash cookie value
        hash_value = int(hashlib.sha256(str(cookie_value).encode()).hexdigest(), 16)
        canary_threshold = int(float(self.config.canary_percentage) * (2**256))

        return hash_value < canary_threshold

    async def _ip_hash_strategy(self, request_context: dict[str, Any]) -> bool:
        """IP hash-based routing."""
        ip = request_context.get("ip")
        if not ip:
            return await self._percentage_strategy()

        # Hash IP
        hash_value = int(hashlib.sha256(ip.encode()).hexdigest(), 16)
        canary_threshold = int(float(self.config.canary_percentage) * (2**256))

        return hash_value < canary_threshold

    async def _get_sticky_decision(self, session_id: str) -> bool | None:
        """Get sticky session decision."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT route_to_canary, expires_at
                    FROM sticky_sessions
                    WHERE session_id = ? AND expires_at > datetime('utc')
                """,
                    (session_id,),
                )

                row = await cursor.fetchone()

                if row:
                    return bool(row[0])

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error getting sticky decision: {e}")

        return None

    async def _set_sticky_decision(self, session_id: str, route_to_canary: bool) -> None:
        """Store sticky session decision."""
        try:
            from datetime import timedelta

            expires_at = datetime.utcnow() + timedelta(minutes=self.config.sticky_duration_minutes)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO sticky_sessions
                    (session_id, route_to_canary, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        session_id,
                        1 if route_to_canary else 0,
                        datetime.utcnow().isoformat(),
                        expires_at.isoformat(),
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error setting sticky decision: {e}")

    async def clear_expired_sessions(self) -> int:
        """Clear expired sticky sessions."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    DELETE FROM sticky_sessions
                    WHERE expires_at <= datetime('utc')
                """
                )

                await db.commit()

                return int(cursor.rowcount)

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error clearing sessions: {e}")
            return 0

    async def update_canary_percentage(self, new_percentage: Decimal) -> None:
        """
        Update canary traffic percentage.

        Args:
            new_percentage: New canary percentage (0.0 to 1.0)
        """
        if new_percentage < 0 or new_percentage > 1:
            raise ValueError("Percentage must be between 0 and 1")

        self.config.canary_percentage = new_percentage
        self.config.baseline_percentage = Decimal("1") - new_percentage

        self.logger.info(f"Updated canary percentage to {new_percentage * 100:.1f}%")
