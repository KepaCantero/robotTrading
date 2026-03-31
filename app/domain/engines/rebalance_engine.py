"""
Rebalance Engine

Engine for portfolio rebalancing operations.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RebalanceTrigger(str, Enum):
    """Rebalance trigger enumeration."""

    SCHEDULED = "scheduled"
    THRESHOLD = "threshold"
    DRIFT = "drift"
    MANUAL = "manual"
    SIGNAL = "signal"


class RebalanceEngine:
    """
    Rebalance Engine.

    Responsible for detecting rebalancing needs and generating
    rebalancing orders to maintain target allocations.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize the Rebalance Engine.

        Args:
            config: Configuration dictionary for the engine.
        """
        self.config = config or {}
        self.drift_threshold = self.config.get("drift_threshold", 0.05)
        logger.info(
            "RebalanceEngine initialized",
            extra={
                "config_keys": list(self.config.keys()),
                "drift_threshold": self.drift_threshold,
            },
        )

    def check_rebalance_needed(
        self,
        current_weights: dict[str, float],
        target_weights: dict[str, float],
        trigger: RebalanceTrigger = RebalanceTrigger.DRIFT,
    ) -> dict[str, Any]:
        """
        Check if portfolio rebalancing is needed.

        Args:
            current_weights: Current portfolio weights by symbol.
            target_weights: Target portfolio weights by symbol.
            trigger: Rebalance trigger type.

        Returns:
            Rebalance assessment with drift analysis.
        """
        logger.debug(
            "Checking rebalance need",
            extra={"symbols_count": len(current_weights), "trigger": trigger.value},
        )

        drifts = {}
        max_drift = 0.0
        rebalance_needed = False

        for symbol in target_weights:
            current = current_weights.get(symbol, 0.0)
            target = target_weights.get(symbol, 0.0)
            drift = abs(current - target)
            drifts[symbol] = drift
            if drift > max_drift:
                max_drift = drift

        if max_drift > self.drift_threshold:
            rebalance_needed = True

        result = {
            "rebalance_needed": rebalance_needed,
            "max_drift": max_drift,
            "drifts": drifts,
            "trigger": trigger.value,
        }

        logger.info(
            "Rebalance check completed",
            extra={
                "rebalance_needed": rebalance_needed,
                "max_drift": max_drift,
                "trigger": trigger.value,
            },
        )

        return result

    def generate_rebalance_orders(
        self, current_portfolio: dict[str, Any], target_weights: dict[str, float], **kwargs
    ) -> list[dict[str, Any]]:
        """
        Generate rebalancing orders to reach target weights.

        Args:
            current_portfolio: Current portfolio state.
            target_weights: Target portfolio weights.
            **kwargs: Additional parameters.

        Returns:
            List of rebalancing orders.
        """
        logger.info(
            "Generating rebalance orders",
            extra={
                "current_holdings": len(current_portfolio.get("holdings", [])),
                "target_symbols": len(target_weights),
            },
        )

        orders: list[dict[str, Any]] = []
        total_value = current_portfolio.get("total_value", 0)

        if total_value <= 0:
            logger.warning(
                "Cannot generate rebalance orders: invalid portfolio value",
                extra={"total_value": total_value},
            )
            return orders

        for symbol, target_weight in target_weights.items():
            target_value = total_value * target_weight
            current_value = current_portfolio.get("holdings", {}).get(symbol, {}).get("value", 0)
            diff = target_value - current_value

            if abs(diff) > 0:
                order = {
                    "symbol": symbol,
                    "side": "buy" if diff > 0 else "sell",
                    "value": abs(diff),
                    "reason": "rebalance",
                }
                orders.append(order)

        logger.debug(
            "Rebalance orders generated",
            extra={
                "orders_count": len(orders),
                "total_rebalance_value": sum(abs(o.get("value", 0)) for o in orders),
            },
        )

        return orders

    def execute_rebalance(
        self,
        current_portfolio: dict[str, Any],
        target_weights: dict[str, float],
        trigger: RebalanceTrigger = RebalanceTrigger.MANUAL,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Execute a full portfolio rebalance.

        Args:
            current_portfolio: Current portfolio state.
            target_weights: Target portfolio weights.
            trigger: Rebalance trigger type.
            **kwargs: Additional parameters.

        Returns:
            Rebalance execution result.
        """
        logger.info(
            "Starting portfolio rebalance",
            extra={
                "trigger": trigger.value,
                "portfolio_value": current_portfolio.get("total_value", 0),
            },
        )

        # Check if rebalance is needed
        check_result = self.check_rebalance_needed(
            current_weights=current_portfolio.get("weights", {}),
            target_weights=target_weights,
            trigger=trigger,
        )

        result: dict[str, Any] = {
            "trigger": trigger.value,
            "check_result": check_result,
            "orders": [],
            "status": "skipped",
        }

        if check_result["rebalance_needed"]:
            orders = self.generate_rebalance_orders(
                current_portfolio=current_portfolio, target_weights=target_weights, **kwargs
            )
            result["orders"] = orders
            result["status"] = "orders_generated"

            logger.info(
                "Rebalance orders generated",
                extra={
                    "trigger": trigger.value,
                    "orders_count": len(orders),
                    "status": result["status"],
                },
            )
        else:
            logger.info(
                "Rebalance not needed",
                extra={"trigger": trigger.value, "max_drift": check_result["max_drift"]},
            )

        return result
