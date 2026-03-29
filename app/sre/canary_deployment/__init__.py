"""
Canary Deployment Module - Gradual Rollout with Auto-Rollback (SRE Rule 20.8)

Implements Google SRE canary deployment best practices:
- Gradual rollout (1% → 10% → 50% → 100%)
- Automated rollback on degradation
- Metrics comparison (canary vs production)
- Blast radius limiting
- Progressive exposure

Usage:
    analyzer = CanaryAnalyzer()
    deployment = await CanaryDeployment.start(
        strategy="momentum_v2",
        canary_percentage=1,
        metrics_comparison=["latency", "error_rate", "throughput"]
    )
"""

from .canary_analyzer import CanaryAnalysisResult, CanaryAnalyzer, MetricComparison, RollbackTrigger
from .canary_deployment import (
    CanaryConfig,
    CanaryDeployment,
    CanaryMetrics,
    CanaryRollbackDecision,
    CanaryStatus,
)
from .traffic_splitter import SplitStrategy, TrafficConfig, TrafficSplitter

__all__ = [
    "CanaryAnalysisResult",
    "CanaryAnalyzer",
    "CanaryConfig",
    "CanaryDeployment",
    "CanaryMetrics",
    "CanaryRollbackDecision",
    "CanaryStatus",
    "MetricComparison",
    "RollbackTrigger",
    "SplitStrategy",
    "TrafficConfig",
    "TrafficSplitter",
]
