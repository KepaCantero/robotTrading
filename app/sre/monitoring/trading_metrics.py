"""
Trading-Specific Metrics Monitoring for Algorithmic Trading SRE.

This module provides comprehensive monitoring of trading-specific metrics
essential for maintaining high availability and performance in algorithmic
trading systems. It extends Google SRE's golden signals with financial metrics
critical to trading operations.

Financial SRE Metrics:
- Order execution latency (time from signal to fill)
- Fill rate (percentage of orders successfully filled)
- Slippage (execution price vs expected price in basis points)
- Position sync health (broker vs internal position reconciliation)
- Strategy health score (aggregate strategy performance indicator)
- Market data latency (quote freshness and delay)
- Execution quality metrics
- Risk limit compliance

References:
- Financial SRE patterns for trading systems
- Algorithmic trading reliability engineering
- FIX protocol performance metrics
- Tomasini's trading systems monitoring
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import aiosqlite
import numpy as np

logger = logging.getLogger(__name__)


class TradingHealthStatus(str, Enum):
    """Trading system health status levels."""

    OPTIMAL = "optimal"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    SUSPENDED = "suspended"


class OrderExecutionPhase(str, Enum):
    """Phases of order execution for latency tracking."""

    SIGNAL_GENERATED = "signal_generated"
    ORDER_VALIDATED = "order_validated"
    ORDER_SUBMITTED = "order_submitted"
    BROKER_ACKNOWLEDGED = "broker_acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FULLY_FILLED = "fully_filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class OrderExecutionMetrics:
    """Order execution performance metrics."""

    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    mean_latency_ms: float
    total_orders: int
    filled_orders: int
    rejected_orders: int
    cancelled_orders: int
    fill_rate_pct: float
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "mean_latency_ms": self.mean_latency_ms,
            "total_orders": self.total_orders,
            "filled_orders": self.filled_orders,
            "rejected_orders": self.rejected_orders,
            "cancelled_orders": self.cancelled_orders,
            "fill_rate_pct": self.fill_rate_pct,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class SlippageMetrics:
    """Slippage analysis metrics."""

    avg_slippage_bps: float  # Average slippage in basis points
    p95_slippage_bps: float
    max_slippage_bps: float
    total_slippage_usd: float
    positive_slippage_count: int  # Orders with favorable slippage
    negative_slippage_count: int  # Orders with adverse slippage
    slippage_ratio: float  # Positive / (Positive + Negative)
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "avg_slippage_bps": self.avg_slippage_bps,
            "p95_slippage_bps": self.p95_slippage_bps,
            "max_slippage_bps": self.max_slippage_bps,
            "total_slippage_usd": self.total_slippage_usd,
            "positive_slippage_count": self.positive_slippage_count,
            "negative_slippage_count": self.negative_slippage_count,
            "slippage_ratio": self.slippage_ratio,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class PositionSyncMetrics:
    """Position synchronization health metrics."""

    sync_health_pct: float  # Percentage of positions in sync
    total_positions: int
    synced_positions: int
    mismatched_positions: int
    missing_positions: int  # Positions in broker but not internal
    ghost_positions: int  # Positions in internal but not broker
    largest_quantity_delta: float
    avg_quantity_delta: float
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sync_health_pct": self.sync_health_pct,
            "total_positions": self.total_positions,
            "synced_positions": self.synced_positions,
            "mismatched_positions": self.mismatched_positions,
            "missing_positions": self.missing_positions,
            "ghost_positions": self.ghost_positions,
            "largest_quantity_delta": self.largest_quantity_delta,
            "avg_quantity_delta": self.avg_quantity_delta,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class MarketDataMetrics:
    """Market data quality and latency metrics."""

    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    stale_data_count: int  # Quotes older than threshold
    total_quotes: int
    data_freshness_pct: float  # Percentage of fresh quotes
    gap_count: int  # Number of data gaps detected
    last_quote_age_seconds: float
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "stale_data_count": self.stale_data_count,
            "total_quotes": self.total_quotes,
            "data_freshness_pct": self.data_freshness_pct,
            "gap_count": self.gap_count,
            "last_quote_age_seconds": self.last_quote_age_seconds,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class StrategyHealthMetrics:
    """Strategy performance and health metrics."""

    overall_health_score: float  # 0-100
    active_strategies: int
    healthy_strategies: int
    degraded_strategies: int
    critical_strategies: int
    avg_sharpe_ratio: float
    avg_win_rate_pct: float
    avg_profit_factor: float
    total_drawdown_pct: float
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_health_score": self.overall_health_score,
            "active_strategies": self.active_strategies,
            "healthy_strategies": self.healthy_strategies,
            "degraded_strategies": self.degraded_strategies,
            "critical_strategies": self.critical_strategies,
            "avg_sharpe_ratio": self.avg_sharpe_ratio,
            "avg_win_rate_pct": self.avg_win_rate_pct,
            "avg_profit_factor": self.avg_profit_factor,
            "total_drawdown_pct": self.total_drawdown_pct,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class RiskLimitMetrics:
    """Risk limit compliance metrics."""

    compliance_score: float  # 0-100
    total_limits: int
    limits_compliant: int
    limits_violated: int
    limits_warning: int
    critical_violations: int
    max_breach_pct: float
    avg_utilization_pct: float
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "compliance_score": self.compliance_score,
            "total_limits": self.total_limits,
            "limits_compliant": self.limits_compliant,
            "limits_violated": self.limits_violated,
            "limits_warning": self.limits_warning,
            "critical_violations": self.critical_violations,
            "max_breach_pct": self.max_breach_pct,
            "avg_utilization_pct": self.avg_utilization_pct,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TradingMetrics:
    """Container for all trading metrics."""

    order_execution: OrderExecutionMetrics
    slippage: SlippageMetrics
    position_sync: PositionSyncMetrics
    market_data: MarketDataMetrics
    strategy_health: StrategyHealthMetrics
    risk_limits: RiskLimitMetrics
    overall_health: TradingHealthStatus
    collected_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "order_execution": self.order_execution.to_dict(),
            "slippage": self.slippage.to_dict(),
            "position_sync": self.position_sync.to_dict(),
            "market_data": self.market_data.to_dict(),
            "strategy_health": self.strategy_health.to_dict(),
            "risk_limits": self.risk_limits.to_dict(),
            "overall_health": self.overall_health.value,
            "collected_at": self.collected_at.isoformat(),
        }


@dataclass
class OrderRecord:
    """Record of an order for tracking."""

    order_id: str
    symbol: str
    side: str
    quantity: float
    expected_price: float
    submitted_at: datetime
    filled_at: datetime | None = None
    fill_price: float | None = None
    status: str = "pending"
    rejection_reason: str | None = None
    broker_order_id: str | None = None

    def get_latency_ms(self) -> float | None:
        """Get order execution latency in milliseconds."""
        if self.filled_at and self.submitted_at:
            return (self.filled_at - self.submitted_at).total_seconds() * 1000
        return None

    def get_slippage_bps(self) -> float | None:
        """Get slippage in basis points."""
        if self.fill_price and self.expected_price:
            price_diff = self.fill_price - self.expected_price
            return (price_diff / self.expected_price) * 10000
        return None


@dataclass
class TradingMetricsConfig:
    """Configuration for trading metrics monitor."""

    # Thresholds
    fill_rate_warning_pct: float = 95.0
    fill_rate_critical_pct: float = 90.0
    slippage_warning_bps: float = 5.0
    slippage_critical_bps: float = 10.0
    order_latency_warning_ms: float = 500.0
    order_latency_critical_ms: float = 1000.0
    position_sync_warning_pct: float = 95.0
    position_sync_critical_pct: float = 90.0
    market_data_stale_threshold_seconds: float = 5.0
    strategy_health_warning_score: float = 70.0
    strategy_health_critical_score: float = 50.0

    # Collection settings
    collection_interval_seconds: int = 60
    history_size: int = 1440  # 24 hours at 1-minute intervals
    order_sample_size: int = 1000
    slippage_sample_size: int = 1000

    # Database
    db_path: str = "data/trading_metrics.db"

    # Callbacks
    on_health_change: Callable[[TradingHealthStatus, TradingHealthStatus], None] | None = None
    on_critical_event: Callable[[str, dict[str, Any]], None] | None = None


class TradingMetricsMonitor:
    """
    Monitor trading-specific metrics for SRE compliance.

    This class provides comprehensive monitoring of trading system performance
    with focus on financial metrics critical for algorithmic trading reliability.

    Features:
    - Order execution latency tracking (p50, p95, p99)
    - Fill rate monitoring with alerts
    - Slippage analysis in basis points
    - Position synchronization health
    - Market data freshness tracking
    - Strategy health scoring
    - Risk limit compliance monitoring
    - Historical data persistence
    """

    def __init__(
        self,
        config: TradingMetricsConfig | None = None,
    ):
        """
        Initialize trading metrics monitor.

        Args:
            config: Optional configuration
        """
        self.config = config or TradingMetricsConfig()
        self.logger = logging.getLogger(__name__)

        # State
        self._current_health: TradingHealthStatus = TradingHealthStatus.HEALTHY
        self._metrics_history: deque[TradingMetrics] = deque(maxlen=self.config.history_size)
        self._lock = asyncio.Lock()

        # Order tracking
        self._orders: dict[str, OrderRecord] = {}
        self._order_latencies: deque = deque(maxlen=self.config.order_sample_size)
        self._slippages: deque = deque(maxlen=self.config.slippage_sample_size)

        # Position tracking
        self._internal_positions: dict[str, float] = {}
        self._broker_positions: dict[str, float] = {}

        # Market data tracking
        self._market_data_timestamps: dict[str, datetime] = {}
        self._market_data_latencies: deque = deque(maxlen=1000)

        # Strategy tracking
        self._strategy_health: dict[str, float] = {}

        # Risk limit tracking
        self._risk_limits: dict[str, dict[str, Any]] = {}

        # Collection task
        self._collection_task: asyncio.Task | None = None
        self._is_running = False

        self.logger.info("TradingMetricsMonitor initialized")

    async def initialize(self) -> None:
        """Initialize the monitor."""
        async with self._lock:
            try:
                # Initialize database
                await self._init_database()
                self.logger.info("TradingMetricsMonitor initialized successfully")

            except (asyncio.TimeoutError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            db_path = Path(self.config.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.config.db_path) as db:
                # Main metrics table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trading_metrics_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        order_latency_p50 REAL,
                        order_latency_p95 REAL,
                        order_latency_p99 REAL,
                        fill_rate_pct REAL,
                        avg_slippage_bps REAL,
                        position_sync_health_pct REAL,
                        market_data_freshness_pct REAL,
                        strategy_health_score REAL,
                        risk_compliance_score REAL,
                        overall_health TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                # Orders table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS order_records (
                        order_id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        expected_price REAL NOT NULL,
                        submitted_at TEXT NOT NULL,
                        filled_at TEXT,
                        fill_price REAL,
                        status TEXT NOT NULL,
                        rejection_reason TEXT,
                        broker_order_id TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                # Create indexes
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_trading_metrics_timestamp
                    ON trading_metrics_history(timestamp)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_order_records_symbol
                    ON order_records(symbol, submitted_at)
                """
                )

                await db.commit()

            self.logger.debug("Database schema initialized")

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def start_collection(self) -> None:
        """Start automatic metrics collection."""
        if self._is_running:
            self.logger.warning("Collection already running")
            return

        self._is_running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        self.logger.info("Started metrics collection")

    async def stop_collection(self) -> None:
        """Stop automatic metrics collection."""
        self._is_running = False
        if self._collection_task:
            self._collection_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._collection_task
        self.logger.info("Stopped metrics collection")

    async def _collection_loop(self) -> None:
        """Main collection loop."""
        while self._is_running:
            try:
                await self.collect_metrics()
                await asyncio.sleep(self.config.collection_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(self.config.collection_interval_seconds)

    async def collect_metrics(self) -> TradingMetrics:
        """
        Collect all trading metrics.

        Returns:
            TradingMetrics with current measurements
        """
        # Collect individual metric categories
        order_execution = await self._collect_order_execution_metrics()
        slippage = await self._collect_slippage_metrics()
        position_sync = await self._collect_position_sync_metrics()
        market_data = await self._collect_market_data_metrics()
        strategy_health = await self._collect_strategy_health_metrics()
        risk_limits = await self._collect_risk_limit_metrics()

        # Create metrics container
        metrics = TradingMetrics(
            order_execution=order_execution,
            slippage=slippage,
            position_sync=position_sync,
            market_data=market_data,
            strategy_health=strategy_health,
            risk_limits=risk_limits,
            overall_health=TradingHealthStatus.HEALTHY,
            collected_at=datetime.utcnow(),
        )

        # Evaluate overall health
        metrics.overall_health = self._evaluate_overall_health(metrics)

        # Check for health changes
        await self._check_health_change(metrics.overall_health)

        # Store in history
        async with self._lock:
            self._metrics_history.append(metrics)

        # Persist to database
        await self._persist_metrics(metrics)

        return metrics

    async def _collect_order_execution_metrics(self) -> OrderExecutionMetrics:
        """Collect order execution metrics."""
        if not self._order_latencies:
            now = datetime.utcnow()
            return OrderExecutionMetrics(
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                mean_latency_ms=0.0,
                total_orders=0,
                filled_orders=0,
                rejected_orders=0,
                cancelled_orders=0,
                fill_rate_pct=100.0,
                timestamp=now,
            )

        latencies = sorted(self._order_latencies)
        count = len(latencies)

        # Count orders by status
        total_orders = len(self._orders)
        filled_orders = sum(1 for o in self._orders.values() if o.status == "filled")
        rejected_orders = sum(1 for o in self._orders.values() if o.status == "rejected")
        cancelled_orders = sum(1 for o in self._orders.values() if o.status == "cancelled")

        fill_rate = (filled_orders / total_orders * 100) if total_orders > 0 else 100.0

        return OrderExecutionMetrics(
            p50_latency_ms=latencies[int(count * 0.5)],
            p95_latency_ms=latencies[int(count * 0.95)],
            p99_latency_ms=latencies[int(count * 0.99)],
            mean_latency_ms=sum(latencies) / count,
            total_orders=total_orders,
            filled_orders=filled_orders,
            rejected_orders=rejected_orders,
            cancelled_orders=cancelled_orders,
            fill_rate_pct=fill_rate,
            timestamp=datetime.utcnow(),
        )

    async def _collect_slippage_metrics(self) -> SlippageMetrics:
        """Collect slippage metrics."""
        if not self._slippages:
            now = datetime.utcnow()
            return SlippageMetrics(
                avg_slippage_bps=0.0,
                p95_slippage_bps=0.0,
                max_slippage_bps=0.0,
                total_slippage_usd=0.0,
                positive_slippage_count=0,
                negative_slippage_count=0,
                slippage_ratio=1.0,
                timestamp=now,
            )

        slippages = sorted(self._slippages)
        count = len(slippages)

        positive_count = sum(1 for s in slippages if s >= 0)
        negative_count = count - positive_count

        # Calculate total slippage in USD (approximate)
        total_slippage_usd = sum(
            abs(s / 10000) * o.quantity * o.fill_price
            for o, s in zip(
                [o for o in self._orders.values() if o.get_slippage_bps() is not None],
                slippages,
            )
            if o.fill_price
        )

        return SlippageMetrics(
            avg_slippage_bps=sum(slippages) / count,
            p95_slippage_bps=slippages[int(count * 0.95)],
            max_slippage_bps=max(slippages) - min(slippages),
            total_slippage_usd=total_slippage_usd,
            positive_slippage_count=positive_count,
            negative_slippage_count=negative_count,
            slippage_ratio=positive_count / count if count > 0 else 1.0,
            timestamp=datetime.utcnow(),
        )

    async def _collect_position_sync_metrics(self) -> PositionSyncMetrics:
        """Collect position synchronization metrics."""
        all_symbols = set(self._internal_positions.keys()) | set(self._broker_positions.keys())

        if not all_symbols:
            now = datetime.utcnow()
            return PositionSyncMetrics(
                sync_health_pct=100.0,
                total_positions=0,
                synced_positions=0,
                mismatched_positions=0,
                missing_positions=0,
                ghost_positions=0,
                largest_quantity_delta=0.0,
                avg_quantity_delta=0.0,
                timestamp=now,
            )

        synced = 0
        mismatched = 0
        missing = 0
        ghost = 0
        deltas = []

        for symbol in all_symbols:
            internal_qty = self._internal_positions.get(symbol, 0.0)
            broker_qty = self._broker_positions.get(symbol, 0.0)

            if symbol not in self._internal_positions:
                ghost += 1
            elif symbol not in self._broker_positions:
                missing += 1
            elif abs(internal_qty - broker_qty) < 0.01:  # Tolerance
                synced += 1
            else:
                mismatched += 1
                deltas.append(abs(internal_qty - broker_qty))

        total = len(all_symbols)
        sync_health = (synced / total * 100) if total > 0 else 100.0

        return PositionSyncMetrics(
            sync_health_pct=sync_health,
            total_positions=total,
            synced_positions=synced,
            mismatched_positions=mismatched,
            missing_positions=missing,
            ghost_positions=ghost,
            largest_quantity_delta=max(deltas) if deltas else 0.0,
            avg_quantity_delta=float(np.mean(deltas)) if deltas else 0.0,
            timestamp=datetime.utcnow(),
        )

    async def _collect_market_data_metrics(self) -> MarketDataMetrics:
        """Collect market data quality metrics."""
        now = datetime.utcnow()

        if not self._market_data_timestamps:
            return MarketDataMetrics(
                avg_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                stale_data_count=0,
                total_quotes=0,
                data_freshness_pct=100.0,
                gap_count=0,
                last_quote_age_seconds=0.0,
                timestamp=now,
            )

        # Check for stale data
        stale_threshold = timedelta(seconds=self.config.market_data_stale_threshold_seconds)
        stale_count = 0
        ages = []

        for _symbol, timestamp in self._market_data_timestamps.items():
            age = now - timestamp
            ages.append(age.total_seconds())
            if age > stale_threshold:
                stale_count += 1

        total_quotes = len(self._market_data_timestamps)
        freshness_pct = (
            ((total_quotes - stale_count) / total_quotes * 100) if total_quotes > 0 else 100.0
        )

        # Latency metrics
        if self._market_data_latencies:
            latencies = sorted(self._market_data_latencies)
            count = len(latencies)
            avg_latency = sum(latencies) / count
            p95_latency = latencies[int(count * 0.95)]
            p99_latency = latencies[int(count * 0.99)]
        else:
            avg_latency = 0.0
            p95_latency = 0.0
            p99_latency = 0.0

        return MarketDataMetrics(
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            stale_data_count=stale_count,
            total_quotes=total_quotes,
            data_freshness_pct=freshness_pct,
            gap_count=0,  # NOTE: Implement gap detection
            last_quote_age_seconds=max(ages) if ages else 0.0,
            timestamp=now,
        )

    async def _collect_strategy_health_metrics(self) -> StrategyHealthMetrics:
        """Collect strategy health metrics."""
        if not self._strategy_health:
            now = datetime.utcnow()
            return StrategyHealthMetrics(
                overall_health_score=100.0,
                active_strategies=0,
                healthy_strategies=0,
                degraded_strategies=0,
                critical_strategies=0,
                avg_sharpe_ratio=0.0,
                avg_win_rate_pct=0.0,
                avg_profit_factor=0.0,
                total_drawdown_pct=0.0,
                timestamp=now,
            )

        scores = list(self._strategy_health.values())
        overall_score = float(np.mean(scores)) if scores else 100.0

        healthy = sum(1 for s in scores if s >= 80)
        degraded = sum(1 for s in scores if 50 <= s < 80)
        critical = sum(1 for s in scores if s < 50)

        return StrategyHealthMetrics(
            overall_health_score=overall_score,
            active_strategies=len(scores),
            healthy_strategies=healthy,
            degraded_strategies=degraded,
            critical_strategies=critical,
            avg_sharpe_ratio=0.0,  # NOTE: Implement from strategy data
            avg_win_rate_pct=0.0,  # NOTE: Implement from strategy data
            avg_profit_factor=0.0,  # NOTE: Implement from strategy data
            total_drawdown_pct=0.0,  # NOTE: Implement from strategy data
            timestamp=datetime.utcnow(),
        )

    async def _collect_risk_limit_metrics(self) -> RiskLimitMetrics:
        """Collect risk limit compliance metrics."""
        if not self._risk_limits:
            now = datetime.utcnow()
            return RiskLimitMetrics(
                compliance_score=100.0,
                total_limits=0,
                limits_compliant=0,
                limits_violated=0,
                limits_warning=0,
                critical_violations=0,
                max_breach_pct=0.0,
                avg_utilization_pct=0.0,
                timestamp=now,
            )

        compliant = 0
        violated = 0
        warning = 0
        critical = 0
        breaches = []
        utilizations = []

        for _limit_name, limit_data in self._risk_limits.items():
            utilization = limit_data.get("utilization_pct", 0.0)
            utilizations.append(utilization)

            if utilization >= 100:
                violated += 1
                breaches.append(utilization - 100)
                if limit_data.get("critical", False):
                    critical += 1
            elif utilization >= 90:
                warning += 1
            else:
                compliant += 1

        total = len(self._risk_limits)
        compliance_score = (compliant / total * 100) if total > 0 else 100.0

        return RiskLimitMetrics(
            compliance_score=compliance_score,
            total_limits=total,
            limits_compliant=compliant,
            limits_violated=violated,
            limits_warning=warning,
            critical_violations=critical,
            max_breach_pct=max(breaches) if breaches else 0.0,
            avg_utilization_pct=float(np.mean(utilizations)) if utilizations else 0.0,
            timestamp=datetime.utcnow(),
        )

    def _count_health_issues(self, metrics: TradingMetrics) -> tuple[int, int]:
        """
        Count critical and warning health issues.

        Returns:
            Tuple of (critical_count, warning_count)
        """
        critical_count = 0
        warning_count = 0

        # Define threshold checks as (value, critical_threshold, warning_threshold, is_lower_better)
        checks = [
            (
                metrics.order_execution.fill_rate_pct,
                self.config.fill_rate_critical_pct,
                self.config.fill_rate_warning_pct,
                True,
            ),
            (
                metrics.slippage.avg_slippage_bps,
                self.config.slippage_critical_bps,
                self.config.slippage_warning_bps,
                False,
            ),
            (
                metrics.order_execution.p95_latency_ms,
                self.config.order_latency_critical_ms,
                self.config.order_latency_warning_ms,
                False,
            ),
            (
                metrics.position_sync.sync_health_pct,
                self.config.position_sync_critical_pct,
                self.config.position_sync_warning_pct,
                True,
            ),
            (
                metrics.strategy_health.overall_health_score,
                self.config.strategy_health_critical_score,
                self.config.strategy_health_warning_score,
                True,
            ),
            (metrics.market_data.data_freshness_pct, 80, 90, True),
        ]

        for value, critical_thresh, warning_thresh, lower_is_better in checks:
            if lower_is_better:
                if value < critical_thresh:
                    critical_count += 1
                elif value < warning_thresh:
                    warning_count += 1
            else:
                if value > critical_thresh:
                    critical_count += 1
                elif value > warning_thresh:
                    warning_count += 1

        return critical_count, warning_count

    def _evaluate_overall_health(self, metrics: TradingMetrics) -> TradingHealthStatus:
        """
        Evaluate overall trading system health.

        Returns:
            TradingHealthStatus indicating system health
        """
        critical_count, warning_count = self._count_health_issues(metrics)

        # Check for risk limit violations
        if metrics.risk_limits.critical_violations > 0:
            return TradingHealthStatus.CRITICAL

        # Determine overall health based on issue counts
        if critical_count >= 2:
            return TradingHealthStatus.CRITICAL
        elif critical_count >= 1 or warning_count >= 3:
            return TradingHealthStatus.DEGRADED
        elif warning_count >= 1:
            return TradingHealthStatus.HEALTHY
        else:
            return TradingHealthStatus.OPTIMAL

    async def _check_health_change(self, new_health: TradingHealthStatus) -> None:
        """Check if health status has changed."""
        old_health = self._current_health

        if old_health != new_health:
            self.logger.warning(
                f"Trading health status changed: {old_health.value} -> {new_health.value}"
            )

            # Notify callback
            if self.config.on_health_change:
                try:
                    self.config.on_health_change(old_health, new_health)
                except Exception as e:
                    self.logger.error(f"Error in health change callback: {e}")

            self._current_health = new_health

    async def _persist_metrics(self, metrics: TradingMetrics) -> None:
        """Persist metrics to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                created_at = datetime.utcnow().isoformat()

                await db.execute(
                    """
                    INSERT INTO trading_metrics_history
                    (timestamp, order_latency_p50, order_latency_p95, order_latency_p99,
                     fill_rate_pct, avg_slippage_bps, position_sync_health_pct,
                     market_data_freshness_pct, strategy_health_score, risk_compliance_score,
                     overall_health, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        metrics.collected_at.isoformat(),
                        metrics.order_execution.p50_latency_ms,
                        metrics.order_execution.p95_latency_ms,
                        metrics.order_execution.p99_latency_ms,
                        metrics.order_execution.fill_rate_pct,
                        metrics.slippage.avg_slippage_bps,
                        metrics.position_sync.sync_health_pct,
                        metrics.market_data.data_freshness_pct,
                        metrics.strategy_health.overall_health_score,
                        metrics.risk_limits.compliance_score,
                        metrics.overall_health.value,
                        created_at,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error persisting metrics: {e}")

    def record_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        expected_price: float,
        submitted_at: datetime,
        order_id: str | None = None,
    ) -> str:
        """
        Record an order submission.

        Args:
            symbol: Trading symbol
            side: Order side (buy/sell)
            quantity: Order quantity
            expected_price: Expected fill price
            submitted_at: Submission timestamp
            order_id: Optional order ID (generated if not provided)

        Returns:
            Order ID
        """
        if order_id is None:
            order_id = f"order_{datetime.utcnow().timestamp()}_{symbol}"

        order = OrderRecord(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            expected_price=expected_price,
            submitted_at=submitted_at,
        )

        self._orders[order_id] = order
        self.logger.debug(f"Recorded order: {order_id}")

        return order_id

    def update_order_fill(
        self,
        order_id: str,
        fill_price: float,
        filled_at: datetime,
        broker_order_id: str | None = None,
    ) -> None:
        """
        Update order with fill information.

        Args:
            order_id: Order ID
            fill_price: Actual fill price
            filled_at: Fill timestamp
            broker_order_id: Optional broker order ID
        """
        if order_id not in self._orders:
            self.logger.warning(f"Unknown order ID: {order_id}")
            return

        order = self._orders[order_id]
        order.fill_price = fill_price
        order.filled_at = filled_at
        order.status = "filled"
        if broker_order_id:
            order.broker_order_id = broker_order_id

        # Record latency
        latency = order.get_latency_ms()
        if latency:
            self._order_latencies.append(latency)

        # Record slippage
        slippage = order.get_slippage_bps()
        if slippage:
            self._slippages.append(slippage)

        self.logger.debug(f"Updated order fill: {order_id}, latency={latency:.2f}ms")

    def update_order_rejection(self, order_id: str, reason: str) -> None:
        """
        Update order as rejected.

        Args:
            order_id: Order ID
            reason: Rejection reason
        """
        if order_id not in self._orders:
            self.logger.warning(f"Unknown order ID: {order_id}")
            return

        order = self._orders[order_id]
        order.status = "rejected"
        order.rejection_reason = reason

        self.logger.debug(f"Order rejected: {order_id}, reason={reason}")

    def update_order_cancellation(self, order_id: str) -> None:
        """
        Update order as cancelled.

        Args:
            order_id: Order ID
        """
        if order_id not in self._orders:
            self.logger.warning(f"Unknown order ID: {order_id}")
            return

        order = self._orders[order_id]
        order.status = "cancelled"

        self.logger.debug(f"Order cancelled: {order_id}")

    def update_internal_position(self, symbol: str, quantity: float) -> None:
        """
        Update internal position for a symbol.

        Args:
            symbol: Trading symbol
            quantity: Position quantity
        """
        self._internal_positions[symbol] = quantity

    def update_broker_position(self, symbol: str, quantity: float) -> None:
        """
        Update broker position for a symbol.

        Args:
            symbol: Trading symbol
            quantity: Position quantity
        """
        self._broker_positions[symbol] = quantity

    def update_market_data_timestamp(
        self, symbol: str, timestamp: datetime, latency_ms: float
    ) -> None:
        """
        Update market data timestamp for a symbol.

        Args:
            symbol: Trading symbol
            timestamp: Quote timestamp
            latency_ms: Data latency in milliseconds
        """
        self._market_data_timestamps[symbol] = timestamp
        self._market_data_latencies.append(latency_ms)

    def update_strategy_health(self, strategy_name: str, health_score: float) -> None:
        """
        Update strategy health score.

        Args:
            strategy_name: Strategy identifier
            health_score: Health score (0-100)
        """
        self._strategy_health[strategy_name] = max(0.0, min(100.0, health_score))

    def update_risk_limit(
        self,
        limit_name: str,
        utilization_pct: float,
        critical: bool = False,
    ) -> None:
        """
        Update risk limit utilization.

        Args:
            limit_name: Risk limit identifier
            utilization_pct: Utilization percentage
            critical: Whether this is a critical limit
        """
        self._risk_limits[limit_name] = {
            "utilization_pct": utilization_pct,
            "critical": critical,
            "updated_at": datetime.utcnow().isoformat(),
        }

    def calculate_fill_rate(self) -> float:
        """
        Calculate order fill rate.

        Returns:
            Fill rate as percentage (0-100)
        """
        if not self._orders:
            return 100.0

        filled = sum(1 for o in self._orders.values() if o.status == "filled")
        return (filled / len(self._orders)) * 100

    def calculate_slippage(self) -> float:
        """
        Calculate average slippage in basis points.

        Returns:
            Average slippage in basis points
        """
        if not self._slippages:
            return 0.0

        return float(np.mean(self._slippages))

    def check_position_sync(self) -> float:
        """
        Check broker vs internal position sync health.

        Returns:
            Sync health percentage (0-100)
        """
        all_symbols = set(self._internal_positions.keys()) | set(self._broker_positions.keys())

        if not all_symbols:
            return 100.0

        synced = 0
        for symbol in all_symbols:
            internal_qty = self._internal_positions.get(symbol, 0.0)
            broker_qty = self._broker_positions.get(symbol, 0.0)

            if abs(internal_qty - broker_qty) < 0.01:  # Tolerance
                synced += 1

        return (synced / len(all_symbols)) * 100

    def evaluate_trading_health(self) -> str:
        """
        Evaluate overall trading system health.

        Returns:
            Health status string
        """
        return self._current_health.value

    async def get_current_metrics(self) -> TradingMetrics | None:
        """Get most recent metrics."""
        async with self._lock:
            if self._metrics_history:
                return self._metrics_history[-1]
            return None

    async def get_metrics_summary(self) -> dict[str, Any]:
        """Get comprehensive metrics summary."""
        current = await self.get_current_metrics()

        if not current:
            return {
                "status": "no_data",
                "message": "No metrics collected yet",
            }

        return {
            "overall_health": current.overall_health.value,
            "order_execution": {
                "p95_latency_ms": current.order_execution.p95_latency_ms,
                "fill_rate_pct": current.order_execution.fill_rate_pct,
                "total_orders": current.order_execution.total_orders,
                "status": (
                    "ok"
                    if current.order_execution.fill_rate_pct >= self.config.fill_rate_warning_pct
                    else "warning"
                ),
            },
            "slippage": {
                "avg_bps": current.slippage.avg_slippage_bps,
                "ratio": current.slippage.slippage_ratio,
                "status": (
                    "ok"
                    if abs(current.slippage.avg_slippage_bps) <= self.config.slippage_warning_bps
                    else "warning"
                ),
            },
            "position_sync": {
                "health_pct": current.position_sync.sync_health_pct,
                "mismatched": current.position_sync.mismatched_positions,
                "status": (
                    "ok"
                    if current.position_sync.sync_health_pct
                    >= self.config.position_sync_warning_pct
                    else "warning"
                ),
            },
            "market_data": {
                "freshness_pct": current.market_data.data_freshness_pct,
                "p95_latency_ms": current.market_data.p95_latency_ms,
                "status": "ok" if current.market_data.data_freshness_pct >= 90 else "warning",
            },
            "strategy_health": {
                "overall_score": current.strategy_health.overall_health_score,
                "active_strategies": current.strategy_health.active_strategies,
                "status": (
                    "ok"
                    if current.strategy_health.overall_health_score
                    >= self.config.strategy_health_warning_score
                    else "warning"
                ),
            },
            "risk_limits": {
                "compliance_score": current.risk_limits.compliance_score,
                "violations": current.risk_limits.limits_violated,
                "status": "ok" if current.risk_limits.compliance_score >= 80 else "warning",
            },
            "collected_at": current.collected_at.isoformat(),
        }


# Singleton instance
_trading_monitor: TradingMetricsMonitor | None = None


def get_trading_metrics_monitor(
    config: TradingMetricsConfig | None = None,
) -> TradingMetricsMonitor:
    """
    Get or create singleton trading metrics monitor.

    Args:
        config: Optional configuration

    Returns:
        TradingMetricsMonitor instance
    """
    global _trading_monitor

    if _trading_monitor is None:
        _trading_monitor = TradingMetricsMonitor(config=config)
        logger.info("Created TradingMetricsMonitor singleton")

    return _trading_monitor
