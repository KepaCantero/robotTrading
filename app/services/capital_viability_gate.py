"""
PHASE 0 - Capital Viability Gate (T0.1.1)

Validates if a profit goal is mathematically achievable given:
- Capital available
- Tax rate
- Commission per trade
- Expected alpha per signal

This is a MANDATORY gate before any trading begins.
If profit goal is unreachable, system disables trading and recommends action.
"""

import logging
from decimal import Decimal
from typing import Dict

logger = logging.getLogger(__name__)


class CapitalViabilityValidator:
    """
    Validates whether a monthly profit goal is achievable given capital constraints.

    Uses forensic analysis to prevent accounts from chasing impossible returns
    and eroding capital through commission/slippage on unwinnable trades.
    """

    # Thresholds
    ALPHA_THRESHOLD = Decimal("0.10")  # 10% = unreachable for most strategies
    MIN_ACHIEVABLE_ALPHA = Decimal("0.02")  # 2% = conservative realistic floor
    MAX_ACHIEVABLE_ALPHA = Decimal("0.05")  # 5% = optimistic ceiling (rare)

    @staticmethod
    def validate_profit_goal(
        capital: Decimal,
        monthly_goal: Decimal,
        tax_rate: Decimal,
        commission_per_trade: Decimal,
        expected_trades_per_month: int,
        expected_alpha_per_trade: Decimal = None,
    ) -> Dict:
        """
        Calculate if profit goal is viable.

        Args:
            capital: Initial capital available (e.g., Decimal("10000"))
            monthly_goal: Net profit goal per month after taxes (e.g., Decimal("500"))
            tax_rate: Tax rate as decimal (e.g., Decimal("0.40") = 40%)
            commission_per_trade: Fixed cost per trade (e.g., Decimal("15"))
            expected_trades_per_month: Estimated trades per month (e.g., 10)
            expected_alpha_per_trade: Optional expected return per trade (0-1 scale)

        Returns:
            {
                'is_viable': bool,
                'required_alpha_pct': Decimal,
                'required_gross_return': Decimal,
                'expected_alpha_pct': Decimal,
                'achievable_alpha_pct': Decimal,
                'total_commission_monthly': Decimal,
                'reason': str,
                'recommendation': Literal['PROCEED', 'INCREASE_CAPITAL', 'REDUCE_GOAL'],
                'severity': Literal['OK', 'WARNING', 'CRITICAL']
            }
        """

        # Validation
        if capital <= Decimal("0"):
            return {
                "is_viable": False,
                "reason": "Capital must be positive",
                "recommendation": "INCREASE_CAPITAL",
                "severity": "CRITICAL",
            }

        if monthly_goal < Decimal("0"):
            return {
                "is_viable": False,
                "reason": "Profit goal cannot be negative",
                "recommendation": "REDUCE_GOAL",
                "severity": "CRITICAL",
            }

        if tax_rate < Decimal("0") or tax_rate >= Decimal("1"):
            return {
                "is_viable": False,
                "reason": f"Tax rate {tax_rate:.0%} is invalid (must be 0-100%)",
                "recommendation": "FIX_CONFIG",
                "severity": "CRITICAL",
            }

        # === CALCULATE REQUIRED ALPHA ===

        # 1. Gross goal needed to meet net goal after tax
        # net_goal = gross_goal * (1 - tax_rate)
        # gross_goal = net_goal / (1 - tax_rate)
        if tax_rate == Decimal("1"):
            # Edge case: 100% tax rate makes goal impossible
            return {
                "is_viable": False,
                "reason": "100% tax rate makes any profit goal impossible",
                "recommendation": "FIX_CONFIG",
                "severity": "CRITICAL",
                "required_alpha_pct": Decimal("999"),
                "required_gross_return": monthly_goal / Decimal("0.01"),  # Quasi-infinity
            }

        gross_goal = monthly_goal / (Decimal("1") - tax_rate)

        # 2. Total commission cost per month
        total_commission = commission_per_trade * Decimal(expected_trades_per_month)

        # 3. Total alpha needed to cover goal + costs
        required_alpha = gross_goal + total_commission

        # 4. Alpha as percentage of capital (this is the KEY metric)
        required_alpha_pct = required_alpha / capital

        # === CALCULATE ACHIEVABLE ALPHA ===

        # Use provided expected_alpha_per_trade if available
        if expected_alpha_per_trade is not None and expected_alpha_per_trade > Decimal("0"):
            expected_alpha_pct = expected_alpha_per_trade * Decimal(expected_trades_per_month)
        else:
            # Default: use conservative estimate (2-5% monthly)
            # Larger accounts can be more optimistic (closer to 5%)
            # Smaller accounts should be conservative (closer to 2%)
            if capital >= Decimal("50000"):
                expected_alpha_pct = CapitalViabilityValidator.MAX_ACHIEVABLE_ALPHA
            elif capital >= Decimal("25000"):
                expected_alpha_pct = (
                    CapitalViabilityValidator.MIN_ACHIEVABLE_ALPHA
                    + CapitalViabilityValidator.MAX_ACHIEVABLE_ALPHA
                ) / Decimal(
                    "2"
                )  # 3.5%
            else:
                expected_alpha_pct = CapitalViabilityValidator.MIN_ACHIEVABLE_ALPHA

        # === VIABILITY DECISION ===

        is_viable = required_alpha_pct <= CapitalViabilityValidator.ALPHA_THRESHOLD

        # Determine severity
        if required_alpha_pct > Decimal("0.20"):
            severity = "CRITICAL"  # Requires > 20% alpha (impossible)
        elif required_alpha_pct > Decimal("0.10"):
            severity = "WARNING"  # Requires > 10% alpha (very hard)
        else:
            severity = "OK"

        # Generate recommendation
        if not is_viable:
            if required_alpha_pct > Decimal("0.20"):
                # Completely unreachable
                recommended_capital = required_alpha * Decimal(
                    "20"
                )  # Need 20x less alpha requirement
                recommendation = "INCREASE_CAPITAL"
                reason = (
                    f"Goal UNREACHABLE: requires {required_alpha_pct:.1%} monthly alpha. "
                    f"Typical achievable: {expected_alpha_pct:.1%}. "
                    f"Recommended capital: ${recommended_capital:,.0f} to make goal realistic."
                )
            else:
                # Hard but possibly doable with better execution
                reduction = monthly_goal * Decimal("0.5")  # Reduce goal by 50%
                recommendation = "REDUCE_GOAL"
                reason = (
                    f"Goal DIFFICULT: requires {required_alpha_pct:.1%} monthly alpha. "
                    f"Typical achievable: {expected_alpha_pct:.1%}. "
                    f"Reduce monthly goal to ${monthly_goal - reduction:,.0f} to align with realistic returns."
                )
        else:
            recommendation = "PROCEED"
            margin = expected_alpha_pct - required_alpha_pct
            reason = (
                f"Goal VIABLE: requires {required_alpha_pct:.1%} alpha, "
                f"achievable {expected_alpha_pct:.1%}. "
                f"Margin of safety: {margin:.1%}."
            )

        return {
            "is_viable": is_viable,
            "required_alpha_pct": required_alpha_pct,
            "required_gross_return": gross_goal,
            "total_commission_monthly": total_commission,
            "expected_alpha_pct": expected_alpha_pct,
            "achievable_alpha_pct": expected_alpha_pct,
            "reason": reason,
            "recommendation": recommendation,
            "severity": severity,
        }

    @staticmethod
    def get_minimum_viable_capital(
        monthly_goal: Decimal,
        tax_rate: Decimal,
        commission_per_trade: Decimal,
        expected_trades_per_month: int,
        target_alpha_pct: Decimal = None,
    ) -> Decimal:
        """
        Calculate minimum capital needed to achieve a profit goal viably.

        Args:
            monthly_goal: Target net profit per month
            tax_rate: Tax rate
            commission_per_trade: Cost per trade
            expected_trades_per_month: Expected trade frequency
            target_alpha_pct: Target alpha as % of capital (default: 5% = achievable)

        Returns:
            Minimum capital required
        """

        if target_alpha_pct is None:
            target_alpha_pct = Decimal("0.05")  # 5% = realistic achievable

        gross_goal = monthly_goal / (Decimal("1") - tax_rate)
        total_commission = commission_per_trade * Decimal(expected_trades_per_month)
        required_alpha = gross_goal + total_commission

        min_capital = required_alpha / target_alpha_pct

        return min_capital

    @staticmethod
    def log_viability_check(
        capital: Decimal,
        monthly_goal: Decimal,
        result: Dict,
        account_id: str = None,
    ):
        """Log viability check for audit trail"""

        status = "✅ VIABLE" if result["is_viable"] else "❌ UNREACHABLE"
        log_msg = (
            f"{status} | Capital: ${capital:,.0f} | Goal: ${monthly_goal:,.0f}/mo | "
            f"Required: {result['required_alpha_pct']:.1%} alpha | "
            f"Achievable: {result['expected_alpha_pct']:.1%} | "
            f"Action: {result['recommendation']}"
        )

        if account_id:
            log_msg = f"[{account_id}] {log_msg}"

        if result["is_viable"]:
            logger.info(log_msg)
        else:
            logger.warning(log_msg)

        logger.debug(f"Reason: {result['reason']}")

        return log_msg
