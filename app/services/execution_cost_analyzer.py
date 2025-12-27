"""
PHASE 0 - Execution Cost Analyzer (T0.1.2)

Monitors execution costs (commission + slippage) and detects:
1. Commission/slippage dominance: When cost > expected alpha
2. Cost regime shifts: When volatility changes slippage expectations
3. Real-time trade rejection: Prevents uneconomical trades

This gate prevents systematic capital erosion from execution costs
that exceed strategy alpha, especially on small accounts.
"""

import logging
from collections import deque
from decimal import Decimal
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ExecutionCostAnalyzer:
    """
    Monitors execution costs and detects uneconomical trading conditions.

    Prevents capital loss from:
    - Commission costs exceeding alpha in high-volatility regimes
    - Systematic underestimation of slippage
    - Amplified costs from joint strategy execution
    """

    def __init__(
        self,
        lookback_days: int = 30,
        max_cost_ratio: Decimal = Decimal("0.50"),
        base_slippage: Decimal = Decimal("0.001"),  # 0.1%
        commission_per_trade: Decimal = Decimal("15"),
    ):
        """
        Args:
            lookback_days: How many trades to track for slippage history
            max_cost_ratio: Max ratio of cost to alpha (e.g., 0.50 = 50%)
            base_slippage: Base slippage in normal market conditions (0.1%)
            commission_per_trade: Fixed commission cost per trade
        """
        self.slippage_history = deque(maxlen=lookback_days)
        self.max_cost_ratio = max_cost_ratio
        self.base_slippage = base_slippage
        self.commission_per_trade = commission_per_trade

        # Cost regime detection
        self.cost_regime_history = deque(maxlen=lookback_days)
        self.current_cost_regime = "normal"  # normal | elevated | extreme

    def add_trade_slippage(self, slippage_pct: Decimal, timestamp: str = None):
        """
        Record actual slippage from a completed trade.

        Args:
            slippage_pct: Slippage as decimal (e.g., Decimal("0.002") = 0.2%)
            timestamp: Optional timestamp for tracking
        """
        if slippage_pct < Decimal("0"):
            logger.warning(f"Negative slippage recorded: {slippage_pct}")
            return

        self.slippage_history.append(slippage_pct)
        logger.debug(
            f"Trade slippage recorded: {slippage_pct:.3%} (history size: {len(self.slippage_history)})"
        )

    def get_current_slippage_estimate(self, volatility_percentile: int) -> Decimal:
        """
        Calculate current slippage estimate based on volatility and recent trade history.

        Args:
            volatility_percentile: 0-100 (0=lowest vol, 100=highest vol)

        Returns:
            Estimated slippage as decimal
        """

        if len(self.slippage_history) == 0:
            # No history: use base estimate adjusted for volatility
            return self._volatility_adjusted_slippage(volatility_percentile)

        # Use average of recent trades, adjusted for current volatility
        avg_slippage = sum(self.slippage_history) / len(self.slippage_history)
        vol_adjustment = self._get_volatility_multiplier(volatility_percentile)

        current_estimate = avg_slippage * vol_adjustment
        return current_estimate

    def _volatility_adjusted_slippage(self, volatility_percentile: int) -> Decimal:
        """
        Map volatility percentile to slippage multiplier (for no-history case).

        Volatility Regime Mapping:
        - 0-25%: Low vol (0.5x base = 0.05%)
        - 25-75%: Normal vol (1.0x base = 0.1%)
        - 75-95%: High vol (2.0x base = 0.2%)
        - 95-100%: Extreme vol (4.0x base = 0.4%)
        """
        percentile = min(100, max(0, volatility_percentile))  # Clamp to 0-100

        if percentile < 25:
            return self.base_slippage * Decimal("0.5")
        elif percentile < 75:
            return self.base_slippage * Decimal("1.0")
        elif percentile < 95:
            return self.base_slippage * Decimal("2.0")
        else:
            return self.base_slippage * Decimal("4.0")

    def _get_volatility_multiplier(self, volatility_percentile: int) -> Decimal:
        """Get volatility multiplier for slippage adjustment"""
        return self._volatility_adjusted_slippage(volatility_percentile) / self.base_slippage

    def detect_cost_regime(self, volatility_percentile: int) -> str:
        """
        Detect current cost regime based on volatility and slippage history.

        Returns: 'normal' | 'elevated' | 'extreme'
        """

        current_slippage = self.get_current_slippage_estimate(volatility_percentile)

        if volatility_percentile > 95 or current_slippage > self.base_slippage * Decimal("3"):
            regime = "extreme"
        elif volatility_percentile > 75 or current_slippage > self.base_slippage * Decimal("1.5"):
            regime = "elevated"
        else:
            regime = "normal"

        self.cost_regime_history.append(regime)
        self.current_cost_regime = regime

        return regime

    def should_execute_trade(
        self,
        position_size: Decimal,
        expected_alpha: Decimal,
        volatility_percentile: int,
        num_concurrent_trades: int = 1,
    ) -> Tuple[bool, Dict]:
        """
        Determine if a trade is economical to execute.

        Factors:
        - Commission cost (fixed per trade)
        - Slippage cost (volatility-dependent)
        - Number of concurrent trades (amplifies cost via market impact)
        - Expected alpha

        Args:
            position_size: Size of position in dollars
            expected_alpha: Expected profit from trade in dollars
            volatility_percentile: Current volatility percentile (0-100)
            num_concurrent_trades: How many trades executing simultaneously

        Returns:
            (should_execute: bool, analysis: Dict)

        Dict contains:
            - slippage_cost: Estimated slippage cost
            - total_cost: Commission + slippage
            - cost_ratio: Cost as % of alpha
            - reason: Human-readable explanation
            - regime: Current cost regime (normal/elevated/extreme)
        """

        # Detect cost regime
        regime = self.detect_cost_regime(volatility_percentile)

        # Estimate slippage (can be amplified by concurrent trades)
        base_slippage_estimate = self.get_current_slippage_estimate(volatility_percentile)

        # Market impact multiplier for concurrent trades
        # Each additional trade amplifies slippage
        market_impact_multiplier = Decimal("1") + (
            Decimal(num_concurrent_trades - 1) * Decimal("0.1")
        )  # +10% per extra trade
        slippage_estimate = base_slippage_estimate * market_impact_multiplier

        # Calculate costs
        slippage_cost = position_size * slippage_estimate
        total_cost = slippage_cost + self.commission_per_trade

        # Calculate cost ratio
        if expected_alpha <= Decimal("0"):
            # No positive alpha expected
            cost_ratio = Decimal("999")  # Effectively infinite
            should_execute = False
            reason = f"Expected alpha ${expected_alpha:.2f} is not positive; cost ${total_cost:.2f} would result in loss"
        else:
            cost_ratio = total_cost / expected_alpha

            # Decision logic
            should_execute = cost_ratio <= self.max_cost_ratio

            if not should_execute:
                reason = (
                    f"Trade REJECTED: Cost ${total_cost:.2f} ({cost_ratio:.0%} of alpha ${expected_alpha:.2f}) "
                    f"exceeds threshold {self.max_cost_ratio:.0%} (regime: {regime})"
                )
            else:
                margin = expected_alpha - total_cost
                reason = (
                    f"Trade ACCEPTED: Cost ${total_cost:.2f} ({cost_ratio:.0%} of alpha) within threshold; "
                    f"net profit ${margin:.2f} (regime: {regime})"
                )

        return should_execute, {
            "should_execute": should_execute,
            "slippage_estimate": slippage_estimate,
            "slippage_cost": slippage_cost,
            "commission_cost": self.commission_per_trade,
            "total_cost": total_cost,
            "cost_ratio": cost_ratio,
            "expected_alpha": expected_alpha,
            "net_profit": (
                expected_alpha - total_cost if expected_alpha > Decimal("0") else Decimal("0")
            ),
            "reason": reason,
            "regime": regime,
            "volatility_percentile": volatility_percentile,
        }

    def get_slippage_stats(self) -> Dict:
        """
        Get statistics on recent slippage history.

        Returns: Dict with min, max, avg, median slippage
        """
        if len(self.slippage_history) == 0:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "avg": None,
                "median": None,
                "has_history": False,
            }

        slippages = list(self.slippage_history)
        slippages_sorted = sorted(slippages)

        avg = sum(slippages) / len(slippages)
        median = (
            slippages_sorted[len(slippages) // 2]
            if len(slippages) % 2 == 1
            else (slippages_sorted[len(slippages) // 2 - 1] + slippages_sorted[len(slippages) // 2])
            / 2
        )

        return {
            "count": len(slippages),
            "min": min(slippages),
            "max": max(slippages),
            "avg": avg,
            "median": median,
            "has_history": True,
        }

    def detect_cost_regime_shift(self, window_size: int = 10) -> Optional[Dict]:
        """
        Detect if cost regime has shifted significantly.

        Compares recent trades to older trades to identify
        sudden increases in costs (e.g., market volatility spike).

        Args:
            window_size: How many recent trades to use for comparison

        Returns:
            Dict with shift details if detected, None otherwise
        """

        if len(self.slippage_history) < window_size * 2:
            return None  # Not enough history

        recent = list(self.slippage_history)[-window_size:]
        older = list(self.slippage_history)[-window_size * 2: -window_size]

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        # Detect 50% increase in slippage
        if recent_avg > older_avg * Decimal("1.50"):
            shift_pct = (recent_avg - older_avg) / older_avg

            return {
                "shift_detected": True,
                "old_avg_slippage": older_avg,
                "new_avg_slippage": recent_avg,
                "shift_percentage": shift_pct,
                "recommendation": "REDUCE_TRADE_SIZE or WAIT_FOR_VOLATILITY_DROP",
            }

        return None

    def log_trade_decision(
        self,
        symbol: str,
        position_size: Decimal,
        expected_alpha: Decimal,
        analysis: Dict,
        account_id: str = None,
    ):
        """Log trade cost analysis for audit trail"""

        status = "✅ ACCEPTED" if analysis["should_execute"] else "❌ REJECTED"
        log_msg = (
            f"{status} | Symbol: {symbol} | Position: ${position_size:,.0f} | "
            f"Cost: ${analysis['total_cost']:.2f} ({analysis['cost_ratio']:.0%}) | "
            f"Alpha: ${expected_alpha:.2f} | Regime: {analysis['regime']}"
        )

        if account_id:
            log_msg = f"[{account_id}] {log_msg}"

        if analysis["should_execute"]:
            logger.info(log_msg)
        else:
            logger.warning(log_msg)

        logger.debug(f"Reason: {analysis['reason']}")
        logger.debug(f"Volatility percentile: {analysis['volatility_percentile']}")

        return log_msg
