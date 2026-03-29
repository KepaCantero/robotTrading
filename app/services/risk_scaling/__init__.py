"""
PHASE 3: Dynamic Risk Scaling Service

Coordinates intelligent risk scaling across multiple dimensions:
- Volatility-based sizing (ATR)
- Performance-based allocation (Sharpe ratio)
- Loss-based reduction (consecutive losses)
- Drawdown protection (circuit breakers)

Components:
- DynamicRiskScaler: Main orchestrator
- VolatilityMonitor: ATR-based scaling (0.5x-1.5x)
- SharpeRatioMonitor: Performance-based scaling (0.2x-1.0x)
- LossMonitor: Consecutive loss detection (0.5x-1.0x)
- DrawdownMonitor: Circuit breaker protection (0.0x-1.0x)
- RiskScalingOrchestrator: Integration coordinator
- RiskScalingMonitor: Dashboard/API
"""

from .models import (
    AdjustedPositionSizes,
    AdjustedSignal,
    AlertSubscription,
    RiskAlert,
    RiskAlertType,
    RiskLevel,
    RiskScalingFactors,
    RiskScalingReport,
    RiskScalingSnapshot,
    RiskScalingState,
    RiskScalingStatus,
)

__all__ = [
    "AdjustedPositionSizes",
    "AdjustedSignal",
    "AlertSubscription",
    "RiskAlert",
    "RiskAlertType",
    "RiskLevel",
    "RiskScalingFactors",
    "RiskScalingReport",
    "RiskScalingSnapshot",
    "RiskScalingState",
    "RiskScalingStatus",
]
