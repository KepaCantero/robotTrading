"""
T18.1: Metrics Collector - Centralized metrics collection from all monitors

Collects metrics from:
- Risk Scaling Monitor
- Portfolio Analytics Service
- Performance Tracker
- Execution Cost Monitor
- Fill Ratio Tracker
- Any custom metric sources
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Callable, Dict, List, Optional

from .models import MetricPoint, MetricsCollectionResult, MetricType
from .questdb_connector import QuestDBConnector

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Centralized metrics collection and persistence.

    Collects metrics from all system monitors and stores them in QuestDB.
    Handles batching, error handling, and automatic flushing.
    """

    def __init__(
        self,
        questdb_connector: QuestDBConnector,
        collection_interval_seconds: int = 60,
        auto_flush: bool = True,
    ):
        """
        Initialize MetricsCollector.

        Args:
            questdb_connector: QuestDB connector instance
            collection_interval_seconds: Interval between collections
            auto_flush: Automatically flush to database
        """
        self.questdb = questdb_connector
        self.collection_interval_seconds = collection_interval_seconds
        self.auto_flush = auto_flush

        self._metric_sources: Dict[str, Callable] = {}
        self._pending_metrics: List[MetricPoint] = []
        self._collection_running = False
        self._collection_task: Optional[asyncio.Task] = None

        # Statistics
        self._total_collected = 0
        self._total_stored = 0
        self._total_errors = 0

    def register_metric_source(self, source_name: str, collector_func: Callable) -> None:
        """
        Register a metric source (collector function).

        Args:
            source_name: Name of the metric source
            collector_func: Async function that returns List[MetricPoint]
        """
        self._metric_sources[source_name] = collector_func
        logger.info(f"Registered metric source: {source_name}")

    async def collect_once(self) -> MetricsCollectionResult:
        """
        Perform a single collection cycle from all sources.

        Returns:
            MetricsCollectionResult with collection statistics
        """
        start_time = datetime.utcnow()
        metrics_collected = 0
        metrics_failed = 0
        errors: List[str] = []

        try:
            logger.debug("Starting metrics collection cycle")

            # Collect from all registered sources
            for source_name, collector_func in self._metric_sources.items():
                try:
                    logger.debug(f"Collecting from {source_name}")

                    # Call collector function (should be async)
                    if asyncio.iscoroutinefunction(collector_func):
                        metrics = await collector_func()
                    else:
                        # Handle sync functions by running in executor
                        metrics = await asyncio.get_event_loop().run_in_executor(
                            None, collector_func
                        )

                    if metrics:
                        self._pending_metrics.extend(metrics)
                        metrics_collected += len(metrics)
                        logger.debug(f"Collected {len(metrics)} metrics from {source_name}")

                except Exception as e:
                    error_msg = f"Error collecting from {source_name}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    metrics_failed += 1

            # Store metrics to database if auto_flush enabled
            if self.auto_flush and self._pending_metrics:
                try:
                    stored_count = await self.questdb.insert_metrics_batch(self._pending_metrics)
                    self._total_stored += stored_count
                    self._pending_metrics.clear()
                    logger.debug(f"Stored {stored_count} metrics to QuestDB")

                except Exception as e:
                    error_msg = f"Error storing metrics: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Update statistics
            self._total_collected += metrics_collected
            self._total_errors += len(errors)

            # Calculate duration
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            result = MetricsCollectionResult(
                success=len(errors) == 0,
                metrics_collected=metrics_collected,
                metrics_failed=metrics_failed,
                total_duration_ms=duration_ms,
                errors=errors,
            )

            logger.info(
                f"Collection cycle complete: "
                f"{metrics_collected} collected, "
                f"{metrics_failed} failed, "
                f"{duration_ms:.2f}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Collection cycle failed: {e}")
            return MetricsCollectionResult(
                success=False,
                metrics_collected=metrics_collected,
                metrics_failed=metrics_failed,
                total_duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                errors=[str(e)],
            )

    async def start_continuous_collection(self) -> None:
        """Start continuous metrics collection."""
        if self._collection_running:
            logger.warning("Collection already running")
            return

        self._collection_running = True
        logger.info(
            f"Starting continuous metrics collection "
            f"(interval: {self.collection_interval_seconds}s)"
        )

        # Create continuous collection task
        self._collection_task = asyncio.create_task(self._continuous_collection_loop())

    async def stop_continuous_collection(self) -> None:
        """Stop continuous metrics collection."""
        if not self._collection_running:
            logger.warning("Collection not running")
            return

        self._collection_running = False
        logger.info("Stopping continuous metrics collection")

        # Flush remaining metrics
        if self._pending_metrics:
            await self.questdb.insert_metrics_batch(self._pending_metrics)
            self._pending_metrics.clear()

        # Cancel collection task
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

    async def _continuous_collection_loop(self) -> None:
        """Run continuous collection loop."""
        while self._collection_running:
            try:
                result = await self.collect_once()

                if not result.success:
                    logger.warning(f"Collection cycle had errors: {result.errors}")

                # Wait before next collection
                await asyncio.sleep(self.collection_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in collection loop: {e}")
                await asyncio.sleep(self.collection_interval_seconds)

    async def flush_metrics(self) -> int:
        """
        Flush pending metrics to database.

        Returns:
            Number of metrics flushed
        """
        if not self._pending_metrics:
            return 0

        try:
            count = await self.questdb.insert_metrics_batch(self._pending_metrics)
            self._total_stored += count
            self._pending_metrics.clear()
            logger.info(f"Flushed {count} metrics to QuestDB")
            return count

        except Exception as e:
            logger.error(f"Error flushing metrics: {e}")
            return 0

    def add_metric(
        self,
        metric_type: MetricType,
        value: Decimal,
        symbol: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Add a single metric to the collection.

        Args:
            metric_type: Type of metric
            value: Metric value
            symbol: Optional symbol
            portfolio_id: Optional portfolio ID
            tags: Optional tags dictionary
        """
        metric = MetricPoint(
            timestamp=datetime.utcnow(),
            metric_type=metric_type,
            value=value,
            symbol=symbol,
            portfolio_id=portfolio_id,
            tags=tags or {},
        )

        self._pending_metrics.append(metric)

    async def get_statistics(self) -> Dict:
        """
        Get collector statistics.

        Returns:
            Dictionary with collection statistics
        """
        return {
            "total_collected": self._total_collected,
            "total_stored": self._total_stored,
            "total_errors": self._total_errors,
            "pending_metrics": len(self._pending_metrics),
            "collection_running": self._collection_running,
            "registered_sources": len(self._metric_sources),
        }

    async def health_check(self) -> bool:
        """
        Check collector and database health.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Check database connectivity
            db_healthy = await self.questdb.health_check()

            if db_healthy:
                logger.debug("✅ Metrics collector health check passed")
            else:
                logger.warning("❌ Database health check failed")

            return db_healthy

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
