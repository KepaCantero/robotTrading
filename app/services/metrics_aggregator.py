"""
Centralized Metrics Aggregator Service.

Aggregates all trading metrics from various sources into a unified interface:
- Signal Scoring metrics
- Performance Tracking metrics
- Fill Ratio metrics
- Multi-Timeframe metrics
- Multi-Strategy Allocation metrics
- Risk Management metrics
- Rebalancing metrics
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class MetricsAggregator:
    """
    Centralized metrics aggregator.
    
    Collects metrics from all trading system components.
    """

    def __init__(self):
        """Initialize metrics aggregator."""
        self.metrics: Dict[str, Any] = {}
        self.timestamp = datetime.utcnow()

    def aggregate_all_metrics(
        self,
        signal_scoring_metrics: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        fill_ratio_metrics: Dict[str, Any],
        multi_timeframe_metrics: Dict[str, Any],
        allocation_metrics: Dict[str, Any],
        risk_metrics: Dict[str, Any],
        rebalancing_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Aggregate all metrics into single report.
        
        Args:
            signal_scoring_metrics: From Signal Scoring Engine
            performance_metrics: From Performance Tracker
            fill_ratio_metrics: From Fill Ratio Tracker
            multi_timeframe_metrics: From Multi-Timeframe Service
            allocation_metrics: From Multi-Strategy Allocation
            risk_metrics: From Advanced Risk Manager
            rebalancing_metrics: From Portfolio Rebalancer
            
        Returns:
            Complete metrics report
        """
        aggregated = {
            "timestamp": datetime.utcnow().isoformat(),
            
            # Signal Scoring
            "signal_scoring": {
                "active_cooldowns": signal_scoring_metrics.get("active_cooldowns", 0),
                "active_positions": signal_scoring_metrics.get("active_positions", 0),
            },
            
            # Performance Tracking
            "performance": {
                "total_cycles": performance_metrics.get("total_cycles", 0),
                "avg_cycle_duration_ms": performance_metrics.get("avg_duration_ms", 0),
                "total_signals_generated": performance_metrics.get("total_signals", 0),
                "total_trades_executed": performance_metrics.get("total_trades", 0),
                "error_rate": performance_metrics.get("error_rate", 0.0),
            },
            
            # Fill Ratio
            "fill_ratio": {
                "total_orders": fill_ratio_metrics.get("total_orders", 0),
                "avg_fill_ratio": fill_ratio_metrics.get("avg_fill_ratio", 0.0),
                "total_filled": fill_ratio_metrics.get("total_filled", 0),
                "total_partial": fill_ratio_metrics.get("total_partial", 0),
                "avg_slippage": fill_ratio_metrics.get("avg_slippage", 0.0),
            },
            
            # Multi-Timeframe
            "multi_timeframe": {
                "confirmed_signals": multi_timeframe_metrics.get("confirmed_count", 0),
                "pending_signals": multi_timeframe_metrics.get("pending_count", 0),
                "avg_confirmations": multi_timeframe_metrics.get("avg_confirmations", 0.0),
            },
            
            # Strategy Allocation
            "allocation": {
                "strategy_allocations": allocation_metrics.get("allocations", {}),
                "total_capital": float(allocation_metrics.get("total_capital", 0)),
            },
            
            # Risk Management
            "risk": {
                "drawdown_exceeded": risk_metrics.get("drawdown_exceeded", False),
                "peak_equity": float(risk_metrics.get("peak_equity", 0)),
                "strategy_stops": risk_metrics.get("strategy_stops", {}),
                "paused_strategies": risk_metrics.get("paused_strategies", []),
            },
            
            # Rebalancing
            "rebalancing": {
                "rebalance_status": rebalancing_metrics.get("status", {}),
                "next_rebalance_days": rebalancing_metrics.get("next_rebalance_days", 30),
            },
        }
        
        logger.info("Metrics aggregated successfully")
        return aggregated

    def get_health_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate overall system health score.
        
        Args:
            metrics: Aggregated metrics
            
        Returns:
            Health score (0-100)
        """
        score = 100.0
        
        # Check risk metrics
        if metrics.get("risk", {}).get("drawdown_exceeded"):
            score -= 30
        
        paused_strategies = len(metrics.get("risk", {}).get("paused_strategies", []))
        score -= paused_strategies * 10
        
        # Check error rate
        error_rate = metrics.get("performance", {}).get("error_rate", 0.0)
        if error_rate > 0.05:  # More than 5%
            score -= (error_rate * 100) * 2
        
        # Check fill ratio
        avg_fill_ratio = metrics.get("fill_ratio", {}).get("avg_fill_ratio", 1.0)
        if avg_fill_ratio < 0.8:  # Less than 80%
            score -= (1 - avg_fill_ratio) * 20
        
        return max(0, min(100, score))

    def get_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get executive summary of metrics.
        
        Args:
            metrics: Aggregated metrics
            
        Returns:
            Executive summary
        """
        return {
            "timestamp": metrics.get("timestamp"),
            "health_score": self.get_health_score(metrics),
            "total_signals": metrics.get("performance", {}).get("total_signals_generated", 0),
            "total_trades": metrics.get("performance", {}).get("total_trades_executed", 0),
            "total_orders": metrics.get("fill_ratio", {}).get("total_orders", 0),
            "paused_strategies": len(metrics.get("risk", {}).get("paused_strategies", [])),
            "drawdown_exceeded": metrics.get("risk", {}).get("drawdown_exceeded", False),
            "total_capital": metrics.get("allocation", {}).get("total_capital", 0),
        }


# Global aggregator instance
_metrics_aggregator = None


def get_metrics_aggregator() -> MetricsAggregator:
    """Get global metrics aggregator instance."""
    global _metrics_aggregator
    if _metrics_aggregator is None:
        _metrics_aggregator = MetricsAggregator()
    return _metrics_aggregator
