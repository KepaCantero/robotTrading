"""
FASE 2: PrometheusMetricsCollector - Real-time metrics collection and exposure

Prometheus integration for collecting, tracking, and exposing trading metrics.
Includes counters, gauges, histograms, and summary metrics for comprehensive monitoring.
"""

import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of Prometheus metrics."""

    COUNTER = "counter"  # Cumulative metric, always increases
    GAUGE = "gauge"  # Can go up and down
    HISTOGRAM = "histogram"  # Distribution of observations
    SUMMARY = "summary"  # Similar to histogram with quantiles


class PrometheusMetric:
    """Individual Prometheus metric definition."""

    def __init__(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None,
    ):
        """
        Initialize a Prometheus metric.

        Args:
            name: Metric name (snake_case)
            metric_type: Type of metric
            description: Human-readable description
            labels: Optional label names for dimensionality
            buckets: Optional histogram buckets
        """
        self.name = name
        self.metric_type = metric_type
        self.description = description
        self.labels = labels or []
        self.buckets = buckets or [0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]
        self.values: Dict[str, float] = {}
        self.created_at = datetime.now()


class PrometheusMetricsCollector:
    """
    Collects and manages Prometheus metrics for trading system.

    Metrics Categories:
    1. Portfolio Metrics
       - portfolio_value (gauge)
       - total_return_pct (gauge)
       - cash_available (gauge)

    2. Trading Metrics
       - trades_executed (counter)
       - win_rate_pct (gauge)
       - avg_profit_per_trade (gauge)
       - max_drawdown_pct (gauge)

    3. Risk Metrics
       - position_count (gauge)
       - leverage_ratio (gauge)
       - var_95 (gauge)
       - expected_shortfall (gauge)

    4. Performance Metrics
       - sharpe_ratio (gauge)
       - sortino_ratio (gauge)
       - calmar_ratio (gauge)
       - profit_factor (gauge)

    5. System Metrics
       - backtest_duration_sec (histogram)
       - api_response_time_ms (histogram)
       - strategy_execution_time_sec (histogram)
       - memory_usage_mb (gauge)

    6. Model Metrics
       - model_accuracy (gauge)
       - model_f1_score (gauge)
       - model_precision (gauge)
       - model_recall (gauge)
    """

    def __init__(self):
        """Initialize Prometheus metrics collector."""
        self.metrics: Dict[str, PrometheusMetric] = {}
        self.metric_values: Dict[str, Dict[str, float]] = {}
        self.timestamps: Dict[str, float] = {}
        self._initialize_metrics()
        logger.info("✅ PrometheusMetricsCollector initialized")

    def _initialize_metrics(self) -> None:
        """Initialize all standard trading metrics."""
        # Portfolio metrics
        self._register_metric(
            "portfolio_value_usd",
            MetricType.GAUGE,
            "Current portfolio value in USD",
        )
        self._register_metric(
            "total_return_pct",
            MetricType.GAUGE,
            "Total return percentage",
        )
        self._register_metric(
            "cash_available_usd",
            MetricType.GAUGE,
            "Available cash in USD",
        )
        self._register_metric(
            "equity_usd",
            MetricType.GAUGE,
            "Total equity in USD",
        )

        # Trading metrics
        self._register_metric(
            "trades_executed_total",
            MetricType.COUNTER,
            "Total trades executed",
        )
        self._register_metric(
            "winning_trades_total",
            MetricType.COUNTER,
            "Total winning trades",
        )
        self._register_metric(
            "losing_trades_total",
            MetricType.COUNTER,
            "Total losing trades",
        )
        self._register_metric(
            "win_rate_pct",
            MetricType.GAUGE,
            "Win rate percentage (0-100)",
        )
        self._register_metric(
            "avg_profit_per_trade_usd",
            MetricType.GAUGE,
            "Average profit per trade in USD",
        )
        self._register_metric(
            "max_drawdown_pct",
            MetricType.GAUGE,
            "Maximum drawdown percentage",
        )

        # Risk metrics
        self._register_metric(
            "position_count",
            MetricType.GAUGE,
            "Number of open positions",
        )
        self._register_metric(
            "leverage_ratio",
            MetricType.GAUGE,
            "Current leverage ratio",
        )
        self._register_metric(
            "value_at_risk_95_pct",
            MetricType.GAUGE,
            "Value at Risk at 95% confidence",
        )
        self._register_metric(
            "expected_shortfall",
            MetricType.GAUGE,
            "Expected shortfall (CVaR)",
        )

        # Performance metrics
        self._register_metric(
            "sharpe_ratio",
            MetricType.GAUGE,
            "Sharpe ratio",
        )
        self._register_metric(
            "sortino_ratio",
            MetricType.GAUGE,
            "Sortino ratio",
        )
        self._register_metric(
            "calmar_ratio",
            MetricType.GAUGE,
            "Calmar ratio",
        )
        self._register_metric(
            "profit_factor",
            MetricType.GAUGE,
            "Profit factor",
        )

        # System metrics
        self._register_metric(
            "backtest_duration_seconds",
            MetricType.HISTOGRAM,
            "Backtest execution duration",
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800],
        )
        self._register_metric(
            "api_response_time_milliseconds",
            MetricType.HISTOGRAM,
            "API response time",
            buckets=[10, 50, 100, 500, 1000, 5000],
        )
        self._register_metric(
            "strategy_execution_time_seconds",
            MetricType.HISTOGRAM,
            "Strategy execution time",
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0],
        )
        self._register_metric(
            "memory_usage_mb",
            MetricType.GAUGE,
            "Memory usage in MB",
        )

        # Model metrics
        self._register_metric(
            "model_accuracy",
            MetricType.GAUGE,
            "Model accuracy (0-1)",
        )
        self._register_metric(
            "model_f1_score",
            MetricType.GAUGE,
            "Model F1 score (0-1)",
        )
        self._register_metric(
            "model_precision",
            MetricType.GAUGE,
            "Model precision (0-1)",
        )
        self._register_metric(
            "model_recall",
            MetricType.GAUGE,
            "Model recall (0-1)",
        )

        logger.info(f"✅ Initialized {len(self.metrics)} standard metrics")

    def _register_metric(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        buckets: Optional[List[float]] = None,
    ) -> None:
        """Register a new metric."""
        metric = PrometheusMetric(
            name=name,
            metric_type=metric_type,
            description=description,
            buckets=buckets,
        )
        self.metrics[name] = metric
        self.metric_values[name] = {}
        self.timestamps[name] = time.time()

    def set_gauge(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Set gauge metric value.

        Args:
            metric_name: Name of metric
            value: Value to set
            labels: Optional label values

        Returns:
            True if successful
        """
        if metric_name not in self.metrics:
            logger.warning(f"⚠️ Metric not found: {metric_name}")
            return False

        metric = self.metrics[metric_name]
        if metric.metric_type != MetricType.GAUGE:
            logger.warning(f"⚠️ Metric {metric_name} is not a gauge")
            return False

        key = self._build_key(metric_name, labels)
        self.metric_values[metric_name][key] = float(value)
        self.timestamps[metric_name] = time.time()

        logger.debug(f"✅ Set gauge {metric_name}: {value}")
        return True

    def increment_counter(
        self,
        metric_name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Increment counter metric.

        Args:
            metric_name: Name of metric
            value: Amount to increment
            labels: Optional label values

        Returns:
            True if successful
        """
        if metric_name not in self.metrics:
            logger.warning(f"⚠️ Metric not found: {metric_name}")
            return False

        metric = self.metrics[metric_name]
        if metric.metric_type != MetricType.COUNTER:
            logger.warning(f"⚠️ Metric {metric_name} is not a counter")
            return False

        key = self._build_key(metric_name, labels)
        current = self.metric_values[metric_name].get(key, 0.0)
        self.metric_values[metric_name][key] = current + float(value)
        self.timestamps[metric_name] = time.time()

        logger.debug(f"✅ Incremented counter {metric_name} by {value}")
        return True

    def observe_histogram(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Record histogram observation.

        Args:
            metric_name: Name of metric
            value: Value to record
            labels: Optional label values

        Returns:
            True if successful
        """
        if metric_name not in self.metrics:
            logger.warning(f"⚠️ Metric not found: {metric_name}")
            return False

        metric = self.metrics[metric_name]
        if metric.metric_type != MetricType.HISTOGRAM:
            logger.warning(f"⚠️ Metric {metric_name} is not a histogram")
            return False

        key = self._build_key(metric_name, labels)
        if key not in self.metric_values[metric_name]:
            self.metric_values[metric_name][key] = []

        if not isinstance(self.metric_values[metric_name][key], list):
            self.metric_values[metric_name][key] = []

        self.metric_values[metric_name][key].append(float(value))
        self.timestamps[metric_name] = time.time()

        logger.debug(f"✅ Observed histogram {metric_name}: {value}")
        return True

    def _build_key(
        self, metric_name: str, labels: Optional[Dict[str, str]] = None
    ) -> str:
        """Build metric key with labels."""
        if not labels:
            return metric_name

        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{metric_name}{{{label_str}}}"

    def get_metric_value(
        self,
        metric_name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """Get current metric value."""
        if metric_name not in self.metrics:
            return None

        key = self._build_key(metric_name, labels)
        value = self.metric_values[metric_name].get(key)

        # For histograms, return count of observations
        if isinstance(value, list):
            return float(len(value))

        return value

    def export_prometheus_format(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []

        for metric_name, metric in self.metrics.items():
            # Add HELP line
            lines.append(f"# HELP {metric_name} {metric.description}")

            # Add TYPE line
            lines.append(f"# TYPE {metric_name} {metric.metric_type.value}")

            # Add metric values
            values = self.metric_values.get(metric_name, {})
            if not values:
                continue

            if metric.metric_type == MetricType.HISTOGRAM:
                # Export histogram buckets
                for key, observations in values.items():
                    if not isinstance(observations, list):
                        continue

                    observations_sorted = sorted(observations)
                    for bucket in metric.buckets:
                        count = sum(1 for o in observations_sorted if o <= bucket)
                        lines.append(f'{metric_name}_bucket{{le="{bucket}",{key}}} {count}')

                    # +Inf bucket
                    lines.append(f'{metric_name}_bucket{{le="+Inf",{key}}} {len(observations)}')

                    # Sum and count
                    total = sum(observations)
                    lines.append(f'{metric_name}_sum{{{key}}} {total}')
                    lines.append(f'{metric_name}_count{{{key}}} {len(observations)}')

            else:
                # Gauge or counter
                for key, value in values.items():
                    if key == metric_name:
                        lines.append(f"{metric_name} {value}")
                    else:
                        lines.append(f"{key} {value}")

            lines.append("")  # Blank line between metrics

        return "\n".join(lines)

    def get_metrics_summary(self) -> Dict:
        """Get summary of all metrics."""
        summary = {
            "total_metrics": len(self.metrics),
            "metrics_by_type": {},
            "last_updated": datetime.now().isoformat(),
            "metrics": {},
        }

        for metric_name, metric in self.metrics.items():
            # Count by type
            metric_type = metric.metric_type.value
            if metric_type not in summary["metrics_by_type"]:
                summary["metrics_by_type"][metric_type] = 0
            summary["metrics_by_type"][metric_type] += 1

            # Get current values
            values = self.metric_values.get(metric_name, {})
            summary["metrics"][metric_name] = {
                "type": metric_type,
                "description": metric.description,
                "current_value": list(values.values())[0] if values else None,
                "label_count": len(values),
            }

        return summary

    def reset_metrics(self) -> None:
        """Reset all metrics to initial state."""
        self.metric_values = {name: {} for name in self.metrics}
        self.timestamps = {name: time.time() for name in self.metrics}
        logger.info("✅ All metrics reset")


# Singleton
_collector: Optional[PrometheusMetricsCollector] = None


def get_prometheus_collector() -> PrometheusMetricsCollector:
    """Get or create singleton PrometheusMetricsCollector."""
    global _collector
    if _collector is None:
        _collector = PrometheusMetricsCollector()
        logger.info("✅ PrometheusMetricsCollector singleton initialized")

    return _collector
