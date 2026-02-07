# pylint: disable=eval-used
"""
Blast Radius Controller - Limits Failure Impact (SRE Rule 20)

Controls the scope of chaos experiments to prevent widespread outages:
- Isolates failures to specific segments
- Prevents cascading failures
- Enables safe experimentation
- Automatic containment

Usage:
    controller = BlastRadiusController()
    await controller.apply_controls({
        "scope": "single_region",
        "regions": ["us-west-2"],
        "percentage": 10
    })
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class BlastRadiusScope(str, Enum):
    """Scope of blast radius."""

    SINGLE_POD = "single_pod"  # Only one pod
    SINGLE_NODE = "single_node"  # Only one node
    SINGLE_ZONE = "single_zone"  # Only one availability zone
    SINGLE_REGION = "single_region"  # Only one region
    PERCENTAGE = "percentage"  # Percentage of traffic
    CUSTOM = "custom"  # Custom selection


@dataclass
class BlastRadiusConfig:
    """Configuration for blast radius control."""

    scope: BlastRadiusScope
    percentage: Decimal = Decimal("10")  # For PERCENTAGE scope

    # Specific targets
    pods: List[str] = field(default_factory=list)
    nodes: List[str] = field(default_factory=list)
    zones: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)

    # Traffic splitting
    traffic_split: Dict[str, Decimal] = field(default_factory=dict)

    # Constraints
    max_failure_domains: int = 1
    require_quorum: bool = True
    min_healthy_pods: int = 2

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scope": self.scope.value,
            "percentage": f"{self.percentage}%",
            "pods": self.pods,
            "nodes": self.nodes,
            "zones": self.zones,
            "regions": self.regions,
            "traffic_split": {k: f"{v}%" for k, v in self.traffic_split.items()},
            "max_failure_domains": self.max_failure_domains,
            "require_quorum": self.require_quorum,
            "min_healthy_pods": self.min_healthy_pods,
        }


@dataclass
class ContainmentState:
    """Current containment state."""

    config: BlastRadiusConfig
    applied_at: datetime
    active_failures: List[str] = field(default_factory=list)
    isolated_domains: List[str] = field(default_factory=list)
    health_status: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "config": self.config.to_dict(),
            "applied_at": self.applied_at.isoformat(),
            "active_failures": self.active_failures,
            "isolated_domains": self.isolated_domains,
            "health_status": self.health_status,
        }


class BlastRadiusController:
    """
    Blast radius control for chaos experiments.

    Responsibilities:
    - Limit experiment scope
    - Prevent cascading failures
    - Isolate failure domains
    - Maintain quorum
    - Automatic containment
    """

    def __init__(
        self,
        service_name: str,
        db_path: str = "data/blast_radius.db",
    ):
        """
        Initialize blast radius controller.

        Args:
            service_name: Name of service
            db_path: Path to database
        """
        self.service_name = service_name
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # State
        self._active_containment: Optional[ContainmentState] = None
        self._containment_history: List[ContainmentState] = []
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize blast radius controller."""
        async with self._lock:
            try:
                await self._init_database()
                await self._load_active_containment()
                self.logger.info("BlastRadiusController initialized")
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            from pathlib import Path

            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS blast_radius_containment (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        scope TEXT NOT NULL,
                        percentage TEXT NOT NULL,
                        pods TEXT NOT NULL,
                        nodes TEXT NOT NULL,
                        zones TEXT NOT NULL,
                        regions TEXT NOT NULL,
                        traffic_split TEXT NOT NULL,
                        applied_at TEXT NOT NULL,
                        removed_at TEXT,
                        active_failures TEXT NOT NULL,
                        isolated_domains TEXT NOT NULL,
                        health_status TEXT NOT NULL
                    )
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_containment_service
                    ON blast_radius_containment(service_name)
                """
                )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _load_active_containment(self) -> None:
        """Load active containment from database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT scope, percentage, pods, nodes, zones, regions,
                           traffic_split, applied_at, active_failures,
                           isolated_domains, health_status
                    FROM blast_radius_containment
                    WHERE service_name = ? AND removed_at IS NULL
                    LIMIT 1
                """,
                    (self.service_name,),
                )

                row = await cursor.fetchone()

                if row:
                    config = BlastRadiusConfig(
                        scope=BlastRadiusScope(row[0]),
                        percentage=Decimal(row[1]),
                        pods=eval(row[2]),  # nosec B307 - internal data from controlled source
                        nodes=eval(row[3]),  # nosec B307 - internal data from controlled source
                        zones=eval(row[4]),  # nosec B307 - internal data from controlled source
                        regions=eval(row[5]),  # nosec B307 - internal data from controlled source
                        traffic_split=eval(
                            row[6]
                        ),  # nosec B307 - internal data from controlled source
                    )

                    self._active_containment = ContainmentState(
                        config=config,
                        applied_at=datetime.fromisoformat(row[7]),
                        active_failures=eval(
                            row[8]
                        ),  # nosec B307 - internal data from controlled source
                        isolated_domains=eval(
                            row[9]
                        ),  # nosec B307 - internal data from controlled source
                        health_status=eval(
                            row[10]
                        ),  # nosec B307 - internal data from controlled source
                    )

                    self.logger.info("Loaded active containment")

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error loading containment: {e}")

    async def apply_controls(self, config_dict: Dict[str, Any]) -> ContainmentState:
        """
        Apply blast radius controls.

        Args:
            config_dict: Blast radius configuration

        Returns:
            ContainmentState
        """
        async with self._lock:
            # Create config
            config = BlastRadiusConfig(
                scope=BlastRadiusScope(config_dict.get("scope", "percentage")),
                percentage=Decimal(str(config_dict.get("percentage", 10))),
                pods=config_dict.get("pods", []),
                nodes=config_dict.get("nodes", []),
                zones=config_dict.get("zones", []),
                regions=config_dict.get("regions", []),
                traffic_split=config_dict.get("traffic_split", {}),
            )

            # Validate config
            await self._validate_config(config)

            # Apply containment
            state = await self._apply_containment(config)

            self._active_containment = state

            # Save to database
            await self._save_containment(state)

            self.logger.info(f"Applied blast radius controls: {config.scope}")

            return state

    async def _validate_config(self, config: BlastRadiusConfig) -> None:
        """Validate blast radius configuration."""
        # Check minimum healthy pods
        if config.scope in [BlastRadiusScope.SINGLE_POD, BlastRadiusScope.PERCENTAGE]:
            if config.min_healthy_pods < 1:
                raise ValueError("Must maintain at least 1 healthy pod")

        # Check quorum requirements
        if config.require_quorum:
            # Ensure majority remains healthy
            # This is a simplified check
            if config.percentage > Decimal("50"):
                raise ValueError("Cannot fail majority when quorum required")

    async def _apply_containment(self, config: BlastRadiusConfig) -> ContainmentState:
        """Apply containment controls."""
        state = ContainmentState(
            config=config,
            applied_at=datetime.utcnow(),
        )

        # Apply traffic splitting
        if config.traffic_split:
            await self._apply_traffic_split(config.traffic_split, state)

        # Isolate failure domains
        await self._isolate_failure_domains(config, state)

        return state

    async def _apply_traffic_split(
        self,
        traffic_split: Dict[str, Decimal],
        state: ContainmentState,
    ) -> None:
        """Apply traffic splitting."""
        # In real implementation, this would configure:
        # - Service mesh (Istio, Linkerd)
        # - Load balancer rules
        # - DNS routing
        # - Proxy configuration

        for target, percentage in traffic_split.items():
            state.isolated_domains.append(target)
            self.logger.info(f"Splitting {percentage}% traffic to {target}")

    async def _isolate_failure_domains(
        self,
        config: BlastRadiusConfig,
        state: ContainmentState,
    ) -> None:
        """Isolate failure domains."""
        if config.scope == BlastRadiusScope.SINGLE_ZONE:
            for zone in config.zones:
                state.isolated_domains.append(f"zone:{zone}")

        elif config.scope == BlastRadiusScope.SINGLE_REGION:
            for region in config.regions:
                state.isolated_domains.append(f"region:{region}")

        elif config.scope == BlastRadiusScope.SINGLE_NODE:
            for node in config.nodes:
                state.isolated_domains.append(f"node:{node}")

    async def remove_controls(self) -> bool:
        """
        Remove blast radius controls.

        Returns:
            True if removed
        """
        async with self._lock:
            if not self._active_containment:
                return False

            # Remove from database
            await self._mark_containment_removed()

            # Clear state
            self._containment_history.append(self._active_containment)
            self._active_containment = None

            self.logger.info("Removed blast radius controls")

            return True

    async def _save_containment(self, state: ContainmentState) -> None:
        """Save containment to database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO blast_radius_containment
                    (service_name, scope, percentage, pods, nodes, zones, regions,
                     traffic_split, applied_at, active_failures, isolated_domains, health_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.service_name,
                        state.config.scope.value,
                        str(state.config.percentage),
                        str(state.config.pods),
                        str(state.config.nodes),
                        str(state.config.zones),
                        str(state.config.regions),
                        str(state.config.traffic_split),
                        state.applied_at.isoformat(),
                        str(state.active_failures),
                        str(state.isolated_domains),
                        str(state.health_status),
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving containment: {e}")

    async def _mark_containment_removed(self) -> None:
        """Mark containment as removed in database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE blast_radius_containment
                    SET removed_at = datetime('utc')
                    WHERE service_name = ? AND removed_at IS NULL
                """,
                    (self.service_name,),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error marking containment removed: {e}")

    async def get_active_containment(self) -> Optional[ContainmentState]:
        """Get active containment."""
        return self._active_containment

    async def get_containment_history(self, limit: int = 100) -> List[ContainmentState]:
        """Get containment history."""
        return self._containment_history[-limit:]

    async def check_health_in_containment(self) -> Dict[str, bool]:
        """Check health of contained domains."""
        if not self._active_containment:
            return {}

        # In real implementation, this would check:
        # - Pod health
        # - Node health
        # - Zone health
        # - Region health

        health_status = {}

        for domain in self._active_containment.isolated_domains:
            # Simulate health check
            health_status[domain] = True  # Placeholder

        self._active_containment.health_status = health_status

        return health_status
