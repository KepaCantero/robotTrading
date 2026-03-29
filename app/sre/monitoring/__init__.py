"""
SRE Monitoring Module - Golden Signals, System Health, and Trading Metrics.

This module provides comprehensive monitoring capabilities following Google SRE practices:

System Monitoring:
- Golden Signals Monitoring (Latency, Traffic, Errors, Saturation)
- SLO Compliance Tracking
- Health Status Evaluation
- Intelligent Alerting
- Historical Metrics Analysis

Trading-Specific Monitoring:
- Order Execution Latency (p50, p95, p99)
- Fill Rate Monitoring
- Slippage Analysis (basis points)
- Position Synchronization Health
- Market Data Freshness
- Strategy Health Scoring
- Risk Limit Compliance

Key Components:
    - GoldenSignalsMonitor: Main monitoring class for golden signals
    - TradingMetricsMonitor: Trading-specific metrics monitoring
    - HealthStatus: System health status enumeration
    - TradingHealthStatus: Trading system health status enumeration
    - GoldenSignalMetrics: Container for all golden signal measurements
    - TradingMetrics: Container for all trading metrics
    - SLOTarget: SLO target definition and compliance checking

Usage:
    from app.sre.monitoring import (
        get_golden_signals_monitor,
        get_trading_metrics_monitor,
        HealthStatus,
        TradingHealthStatus
    )

    # System monitoring
    system_monitor = get_golden_signals_monitor(service_name="trading-engine")
    await system_monitor.initialize()
    await system_monitor.start_collection()

    # Trading monitoring
    trading_monitor = get_trading_metrics_monitor()
    await trading_monitor.initialize()
    await trading_monitor.start_collection()

    # Record trading metrics
    order_id = trading_monitor.record_order(
        symbol="AAPL",
        side="buy",
        quantity=100,
        expected_price=150.0,
        submitted_at=datetime.utcnow()
    )

    trading_monitor.update_order_fill(
        order_id=order_id,
        fill_price=150.05,
        filled_at=datetime.utcnow()
    )

    # Get current status
    trading_metrics = await trading_monitor.get_current_metrics()
    trading_summary = await trading_monitor.get_metrics_summary()

References:
    - Google SRE Book: https://sre.google/sre-book/monitoring-distributed-systems/
    - Site Reliability Engineering: How Google Runs Production Systems
    - Financial SRE patterns for algorithmic trading
"""

from .golden_signals import (
    ErrorMetrics,
    GoldenSignalMetrics,
    GoldenSignalsConfig,
    GoldenSignalsMonitor,
    HealthStatus,
    LatencyCollector,
    LatencyMetrics,
    RequestTracker,
    SaturationMetrics,
    SignalType,
    SLOTarget,
    TrafficMetrics,
    get_golden_signals_monitor,
)
from .trading_metrics import (
    MarketDataMetrics,
    OrderExecutionMetrics,
    OrderRecord,
    PositionSyncMetrics,
    RiskLimitMetrics,
    SlippageMetrics,
    StrategyHealthMetrics,
    TradingHealthStatus,
    TradingMetrics,
    TradingMetricsConfig,
    TradingMetricsMonitor,
    get_trading_metrics_monitor,
)

__all__ = [
    "ErrorMetrics",
    # System metrics
    "GoldenSignalMetrics",
    # Configuration
    "GoldenSignalsConfig",
    # Main monitors
    "GoldenSignalsMonitor",
    # Enums
    "HealthStatus",
    # Internal components
    "LatencyCollector",
    "LatencyMetrics",
    "MarketDataMetrics",
    "OrderExecutionMetrics",
    "OrderRecord",
    "PositionSyncMetrics",
    "RequestTracker",
    "RiskLimitMetrics",
    "SLOTarget",
    "SaturationMetrics",
    "SignalType",
    "SlippageMetrics",
    "StrategyHealthMetrics",
    "TradingHealthStatus",
    # Trading metrics
    "TradingMetrics",
    "TradingMetricsConfig",
    "TradingMetricsMonitor",
    "TrafficMetrics",
    "get_golden_signals_monitor",
    "get_trading_metrics_monitor",
]

# Version information
__version__ = "1.1.0"
__author__ = "SRE Team"
