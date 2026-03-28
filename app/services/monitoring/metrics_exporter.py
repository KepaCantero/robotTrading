"""
FASE 2: MetricsExporter - Export metrics to Prometheus and external systems

Handles metrics export in multiple formats (Prometheus, JSON, CSV) and
supports real-time streaming to monitoring backends.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from requests.exceptions import HTTPError, RequestException
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)

logger = logging.getLogger(__name__)


class MetricsExporter:
    """
    Exports metrics to Prometheus and other monitoring systems.

    Supports:
    - Prometheus text format (OpenMetrics)
    - JSON export for APIs
    - CSV export for analytics
    - Real-time webhook streaming
    - Remote write to Prometheus/Thanos
    """

    def __init__(
        self,
        prometheus_url: Optional[str] = None,
        pushgateway_url: Optional[str] = None,
    ):
        """
        Initialize metrics exporter.

        Args:
            prometheus_url: URL to Prometheus server
            pushgateway_url: URL to Prometheus PushGateway
        """
        self.prometheus_url = prometheus_url or "http://localhost:9090"
        self.pushgateway_url = pushgateway_url or "http://localhost:9091"
        self.session: Optional[aiohttp.ClientSession] = None
        self.export_history: List[Dict] = []
        logger.info(
            f"✅ MetricsExporter initialized "
            f"(Prometheus: {self.prometheus_url}, "
            f"PushGateway: {self.pushgateway_url})"
        )

    async def connect(self) -> bool:
        """Connect to metric export services."""
        try:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self.session = aiohttp.ClientSession(
                connector=connector, timeout=aiohttp.ClientTimeout(total=30)
            )

            # Verify Prometheus connectivity
            async with self.session.get(f"{self.prometheus_url}/-/healthy") as resp:
                if resp.status == 200:
                    logger.info("✅ Connected to Prometheus")
                    return True

        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(f"⚠️ Failed to connect to Prometheus: {str(e)}")

        return False

    async def disconnect(self) -> bool:
        """Disconnect from export services."""
        try:
            if self.session:
                await self.session.close()
            logger.info("✅ Disconnected from export services")
            return True
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"❌ Disconnect failed: {str(e)}")
            return False

    async def push_metrics(
        self,
        metrics_data: Dict,
        job_name: str = "trading_system",
        instance: str = "main",
    ) -> bool:
        """
        Push metrics to Prometheus PushGateway.

        Args:
            metrics_data: Dictionary of metric_name -> value
            job_name: Prometheus job name
            instance: Instance name

        Returns:
            True if successful
        """
        if not self.session:
            logger.warning("⚠️ No session available, skipping push")
            return False

        try:
            # Convert to Prometheus text format
            prometheus_text = self._format_prometheus_text(metrics_data)

            # Push to PushGateway
            url = f"{self.pushgateway_url}/metrics/job/{job_name}/instance/{instance}"
            async with self.session.post(
                url, data=prometheus_text, content_type="text/plain"
            ) as resp:
                if resp.status in (200, 201, 204):
                    logger.info(
                        f"✅ Pushed metrics to PushGateway " f"(job={job_name}, instance={instance})"
                    )
                    self.export_history.append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "job": job_name,
                            "instance": instance,
                            "metrics_count": len(metrics_data),
                            "success": True,
                        }
                    )
                    return True
                else:
                    logger.error(f"❌ PushGateway push failed: HTTP {resp.status}")
                    return False

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"❌ Failed to push metrics: {str(e)}")
            return False

    async def query_prometheus(self, query: str, time: Optional[str] = None) -> Optional[Dict]:
        """
        Query Prometheus for metric data.

        Args:
            query: PromQL query string
            time: Optional Unix timestamp

        Returns:
            Query results or None
        """
        if not self.session:
            logger.warning("⚠️ No session available, skipping query")
            return None

        try:
            params = {"query": query}
            if time:
                params["time"] = time

            async with self.session.get(
                f"{self.prometheus_url}/api/v1/query",
                params=params,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.debug(f"✅ Prometheus query successful: {query}")
                    return data
                else:
                    logger.error(f"❌ Prometheus query failed: HTTP {resp.status}")
                    return None

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"❌ Query failed: {str(e)}")
            return None

    async def query_range(
        self,
        query: str,
        start: str,
        end: str,
        step: str = "1m",
    ) -> Optional[Dict]:
        """
        Query Prometheus for time series data.

        Args:
            query: PromQL query
            start: Start timestamp
            end: End timestamp
            step: Query step

        Returns:
            Query results or None
        """
        if not self.session:
            return None

        try:
            params = {
                "query": query,
                "start": start,
                "end": end,
                "step": step,
            }

            async with self.session.get(
                f"{self.prometheus_url}/api/v1/query_range",
                params=params,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.debug("✅ Prometheus range query successful")
                    return data
                else:
                    logger.error(f"❌ Prometheus range query failed: HTTP {resp.status}")
                    return None

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"❌ Range query failed: {str(e)}")
            return None

    def export_json(self, metrics_data: Dict) -> str:
        """
        Export metrics as JSON.

        Args:
            metrics_data: Dictionary of metrics

        Returns:
            JSON string
        """
        export = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics_data,
            "metadata": {
                "count": len(metrics_data),
                "version": "1.0",
            },
        }

        return json.dumps(export, indent=2)

    def export_csv(self, metrics_data: Dict) -> str:
        """
        Export metrics as CSV.

        Args:
            metrics_data: Dictionary of metrics

        Returns:
            CSV string
        """
        lines = [
            "timestamp,metric_name,metric_value",
        ]

        timestamp = datetime.now().isoformat()
        for metric_name, value in metrics_data.items():
            lines.append(f"{timestamp},{metric_name},{value}")

        return "\n".join(lines)

    def export_prometheus_text(self, metrics_data: Dict) -> str:
        """Export metrics in Prometheus text format."""
        return self._format_prometheus_text(metrics_data)

    def _format_prometheus_text(self, metrics_data: Dict) -> str:
        """Format metrics in Prometheus text format."""
        lines = []

        for metric_name, value in metrics_data.items():
            # Add HELP and TYPE lines
            lines.append(f"# HELP {metric_name} Trading system metric")
            lines.append(f"# TYPE {metric_name} gauge")

            # Add metric value
            timestamp_ms = int(datetime.now().timestamp() * 1000)
            lines.append(f"{metric_name} {value} {timestamp_ms}")

        return "\n".join(lines)

    def get_export_history(self, limit: int = 100) -> List[Dict]:
        """Get export history."""
        return self.export_history[-limit:]

    async def health_check(self) -> Dict:
        """Check health of export services."""
        health = {
            "prometheus": False,
            "pushgateway": False,
            "timestamp": datetime.now().isoformat(),
        }

        if not self.session:
            return health

        # Check Prometheus
        try:
            async with self.session.get(
                f"{self.prometheus_url}/-/healthy",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                health["prometheus"] = resp.status == 200
        except (ConnectionError, TimeoutError, HTTPError, RequestException):
            health["prometheus"] = False

        # Check PushGateway
        try:
            async with self.session.get(
                f"{self.pushgateway_url}/-/healthy",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                health["pushgateway"] = resp.status == 200
        except (ConnectionError, TimeoutError, HTTPError, RequestException):
            health["pushgateway"] = False

        logger.info(
            f"✅ Health check: Prometheus={health['prometheus']}, "
            f"PushGateway={health['pushgateway']}"
        )
        return health


# Singleton
_exporter: Optional[MetricsExporter] = None


def get_metrics_exporter(
    prometheus_url: Optional[str] = None,
    pushgateway_url: Optional[str] = None,
) -> MetricsExporter:
    """
    Get or create singleton MetricsExporter.

    If the exporter doesn't exist, creates one with the specified URLs.
    If it exists but different URLs are provided, recreates it with new URLs.
    """
    global _exporter
    if _exporter is None:
        _exporter = MetricsExporter(
            prometheus_url=prometheus_url,
            pushgateway_url=pushgateway_url,
        )
        logger.info("✅ MetricsExporter singleton initialized")
    elif prometheus_url is not None or pushgateway_url is not None:
        # If URLs are explicitly provided and differ from current, recreate
        current_prom = _exporter.prometheus_url
        current_push = _exporter.pushgateway_url
        new_prom = prometheus_url or "http://localhost:9090"
        new_push = pushgateway_url or "http://localhost:9091"
        if current_prom != new_prom or current_push != new_push:
            _exporter = MetricsExporter(
                prometheus_url=prometheus_url,
                pushgateway_url=pushgateway_url,
            )
            logger.info("✅ MetricsExporter singleton recreated with new URLs")

    return _exporter
