"""
PHASE 0 - Opportunity Cost Validator (T0.1.3)

Determines if active trading is economically superior to passive holding
(holding cash at risk-free rate).

This gate prevents small accounts from systematically eroding capital through
commission/slippage costs that exceed what they could earn passively.

Economics principle: If passive return (RF rate) > active strategy return,
then the optimal action is to HOLD CASH, not trade.
"""

import logging
from decimal import Decimal
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class OpportunityCostValidator:
    """
    Validates that active trading is more profitable than passive holding.

    Prevents accounts from trading when the risk-free rate (bonds, money market,
    treasury bills) exceeds expected strategy returns after commissions.

    This is especially critical for small accounts where fixed commission costs
    are a larger percentage of capital.
    """

    # Default risk-free rate assumptions (annual)
    DEFAULT_RISK_FREE_RATE = Decimal("0.04")  # 4% annually (conservative)
    MINIMUM_RETURN_THRESHOLD = Decimal("0.03")  # Must beat 3% passively minimum

    @staticmethod
    def is_active_trading_worthwhile(
        capital: Decimal,
        monthly_risk_free_rate: Decimal = None,
        expected_monthly_alpha: Decimal = Decimal("0"),
        expected_trades_per_month: int = 10,
        commission_per_trade: Decimal = Decimal("15"),
        cost_of_capital_pct: Decimal = None,
    ) -> Tuple[bool, Dict]:
        """
        Compare passive (risk-free) return vs active trading return.

        Args:
            capital: Available capital in dollars
            monthly_risk_free_rate: Monthly risk-free rate as decimal
                                   (e.g., 0.04/12 for annual 4%)
                                   If None, uses DEFAULT_RISK_FREE_RATE
            expected_monthly_alpha: Expected alpha per month from strategy
            expected_trades_per_month: Expected trade frequency
            commission_per_trade: Fixed cost per trade
            cost_of_capital_pct: Optional cost of borrowing (for leverage scenarios)

        Returns:
            (should_trade: bool, analysis: Dict)

        Dict contains:
            - passive_monthly_return: Risk-free return in dollars
            - active_monthly_return: Strategy alpha minus costs
            - passive_annual_return: Extrapolated annual
            - active_annual_return: Extrapolated annual
            - reason: Human-readable comparison
            - recommendation: TRADE | HOLD_CASH | CONSIDER_ALTERNATIVES
        """

        # Use default if not provided
        if monthly_risk_free_rate is None:
            monthly_risk_free_rate = OpportunityCostValidator.DEFAULT_RISK_FREE_RATE / 12

        # Validate inputs
        if capital <= Decimal("0"):
            return False, {
                "should_trade": False,
                "reason": "Capital must be positive",
                "recommendation": "INCREASE_CAPITAL",
            }

        # === CALCULATE PASSIVE RETURN ===

        # Passive: Hold cash earning risk-free rate (treasury, money market)
        passive_monthly = capital * monthly_risk_free_rate
        passive_annual = passive_monthly * 12

        # === CALCULATE ACTIVE RETURN ===

        # Total commission cost per month
        total_commission = commission_per_trade * Decimal(expected_trades_per_month)

        # Cost of capital (if using leverage/margin)
        capital_cost = Decimal("0")
        if cost_of_capital_pct is not None and cost_of_capital_pct > Decimal("0"):
            capital_cost = capital * (cost_of_capital_pct / 12)

        # Active return: alpha minus all costs
        active_monthly = expected_monthly_alpha - total_commission - capital_cost
        active_annual = active_monthly * 12

        # === DECISION LOGIC ===

        should_trade = active_monthly > passive_monthly

        # Calculate advantage/disadvantage
        margin = active_monthly - passive_monthly
        margin_annual = margin * 12

        if should_trade:
            if margin > passive_monthly:
                # Active is significantly better
                confidence = "HIGH"
                recommendation = "TRADE"
                reason = (
                    f"Active strategy is {(margin / passive_monthly):.0%} better than passive. "
                    f"Active: ${active_monthly:.2f}/mo (${active_annual:.2f}/yr) vs "
                    f"Passive: ${passive_monthly:.2f}/mo (${passive_annual:.2f}/yr). "
                    "Trade with confidence."
                )
            else:
                # Active is better but margin is small
                confidence = "MEDIUM"
                recommendation = "TRADE_WITH_CAUTION"
                reason = (
                    f"Active strategy slightly better than passive (+${margin:.2f}/mo). "
                    f"Active: ${active_monthly:.2f}/mo vs Passive: ${passive_monthly:.2f}/mo. "
                    "Small margin of safety."
                )
        else:
            # Passive is better - recommend holding cash
            confidence = "HIGH"
            recommendation = "HOLD_CASH"
            disadvantage = abs(margin)
            reason = (
                f"Passive return (${passive_monthly:.2f}/mo) exceeds active strategy "
                f"(${active_monthly:.2f}/mo) by ${disadvantage:.2f}/mo. "
                "Recommend holding cash/treasury bills instead of trading. "
                f"Cost of trading (${total_commission:.2f}/mo commission) exceeds alpha."
            )

        return should_trade, {
            "should_trade": should_trade,
            "passive_monthly_return": passive_monthly,
            "passive_annual_return": passive_annual,
            "active_monthly_return": active_monthly,
            "active_annual_return": active_annual,
            "total_commission_monthly": total_commission,
            "capital_cost_monthly": capital_cost,
            "margin_monthly": margin,
            "margin_annual": margin_annual,
            "confidence": confidence,
            "reason": reason,
            "recommendation": recommendation,
            "risk_free_rate_annual": monthly_risk_free_rate * 12,
        }

    @staticmethod
    def get_minimum_alpha_for_trading(
        capital: Decimal,
        monthly_risk_free_rate: Decimal = None,
        expected_trades_per_month: int = 10,
        commission_per_trade: Decimal = Decimal("15"),
    ) -> Decimal:
        """
        Calculate minimum alpha needed to justify trading vs passive holding.

        Args:
            capital: Available capital
            monthly_risk_free_rate: Risk-free monthly rate
            expected_trades_per_month: Trade frequency
            commission_per_trade: Cost per trade

        Returns:
            Minimum monthly alpha required to beat passive return
        """

        if monthly_risk_free_rate is None:
            monthly_risk_free_rate = OpportunityCostValidator.DEFAULT_RISK_FREE_RATE / 12

        # Passive return
        passive_return = capital * monthly_risk_free_rate

        # Commission cost
        total_commission = commission_per_trade * Decimal(expected_trades_per_month)

        # Minimum alpha to beat passive
        min_alpha = passive_return + total_commission

        return min_alpha

    @staticmethod
    def capital_inflection_point(
        monthly_risk_free_rate: Decimal = None,
        expected_trades_per_month: int = 10,
        commission_per_trade: Decimal = Decimal("15"),
        target_alpha_pct_monthly: Decimal = getattr(config.trading, 'max_risk_per_trade', 0.02)"),  # 2% monthly
    ) -> Decimal:
        """
        Calculate the capital amount where trading becomes viable.

        Below this capital, holding cash is optimal.
        Above this capital, trading becomes worthwhile.

        Args:
            monthly_risk_free_rate: Risk-free rate
            expected_trades_per_month: Expected trades
            commission_per_trade: Cost per trade
            target_alpha_pct_monthly: Target alpha % per month (e.g., 2%)

        Returns:
            Minimum capital threshold for trading viability
        """

        if monthly_risk_free_rate is None:
            monthly_risk_free_rate = OpportunityCostValidator.DEFAULT_RISK_FREE_RATE / 12

        # At inflection point: active return = passive return
        # Strategy alpha = capital * RF_rate + total_commission
        # Assuming alpha is X% of capital:
        # capital * X% = capital * RF_rate + total_commission
        # capital * (X% - RF_rate) = total_commission
        # capital = total_commission / (X% - RF_rate)

        total_commission = commission_per_trade * Decimal(expected_trades_per_month)
        alpha_advantage = target_alpha_pct_monthly - monthly_risk_free_rate

        if alpha_advantage <= Decimal("0"):
            # Strategy can never beat passive (alpha too low)
            return Decimal("999999999")  # Essentially infinite

        inflection_capital = total_commission / alpha_advantage

        return inflection_capital

    @staticmethod
    def analyze_capital_tier_viability(
        capital: Decimal,
        expected_trades_per_month: int = 10,
        commission_per_trade: Decimal = Decimal("15"),
    ) -> Dict:
        """
        Analyze viability of trading for a given capital tier.

        Args:
            capital: Account capital
            expected_trades_per_month: Trade frequency
            commission_per_trade: Cost per trade

        Returns:
            Dict with viability analysis for this capital tier
        """

        monthly_rf_rate = OpportunityCostValidator.DEFAULT_RISK_FREE_RATE / 12

        # Passive return
        passive_monthly = capital * monthly_rf_rate

        # Minimum alpha needed
        min_alpha = OpportunityCostValidator.get_minimum_alpha_for_trading(
            capital=capital,
            monthly_risk_free_rate=monthly_rf_rate,
            expected_trades_per_month=expected_trades_per_month,
            commission_per_trade=commission_per_trade,
        )

        # Minimum alpha as percentage of capital
        min_alpha_pct = min_alpha / capital

        # Assess viability
        if min_alpha_pct > Decimal("0.10"):
            viability = "POOR"  # Requires >10% monthly alpha (unrealistic)
        elif min_alpha_pct > Decimal("0.05"):
            viability = "DIFFICULT"  # Requires 5-10% (hard)
        elif min_alpha_pct > Decimal("0.03"):
            viability = "MODERATE"  # Requires 3-5% (achievable)
        else:
            viability = "GOOD"  # Requires <3% (realistic)

        # Only recommend trading if viability is GOOD
        trading_recommended = viability == "GOOD"

        return {
            "capital": capital,
            "passive_monthly_return": passive_monthly,
            "minimum_alpha_required": min_alpha,
            "minimum_alpha_pct_of_capital": min_alpha_pct,
            "viability": viability,
            "trading_recommended": trading_recommended,
        }

    @staticmethod
    def log_opportunity_cost_decision(
        capital: Decimal,
        analysis: Dict,
        account_id: str = None,
    ):
        """Log opportunity cost analysis for audit trail"""

        status = "✅ TRADE" if analysis["should_trade"] else "❌ HOLD_CASH"
        log_msg = (
            f"{status} | Capital: ${capital:,.0f} | "
            f"Passive: ${analysis['passive_monthly_return']:.2f}/mo | "
            f"Active: ${analysis['active_monthly_return']:.2f}/mo | "
            f"Margin: ${analysis['margin_monthly']:.2f}/mo | "
            f"Recommendation: {analysis['recommendation']}"
        )

        if account_id:
            log_msg = f"[{account_id}] {log_msg}"

        if analysis["should_trade"]:
            logger.info(log_msg)
        else:
            logger.warning(log_msg)

        logger.debug(f"Reason: {analysis['reason']}")

        return log_msg
