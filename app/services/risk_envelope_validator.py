"""
Risk Envelope Validator

Validates that trades don't exceed maximum exposure limits.
Prevents the system from taking positions that would exceed:
- 20% total exposure per symbol
- Maximum strategy exposure limits
- Portfolio-level risk constraints

Addresses issue: Pairs Trading appears to violate exposure limits,
causing large losses despite small nominal returns.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class RiskEnvelopeValidator:
    """
    Risk Envelope Validator.

    Ensures trades don't exceed maximum exposure constraints.
    """

    def __init__(
        self,
        max_total_exposure_pct: Decimal = Decimal("0.20"),  # 20% max per symbol
        max_strategy_exposure_pct: Decimal = Decimal("0.70"),  # 70% max per strategy
        max_portfolio_exposure_pct: Decimal = Decimal("0.95"),  # 95% max total portfolio
    ):
        """
        Initialize risk envelope validator.

        Args:
            max_total_exposure_pct: Maximum exposure per symbol (default 20%)
            max_strategy_exposure_pct: Maximum exposure per strategy (default 70%)
            max_portfolio_exposure_pct: Maximum total portfolio exposure (default 95%)
        """
        self.max_total_exposure_pct = max_total_exposure_pct
        self.max_strategy_exposure_pct = max_strategy_exposure_pct
        self.max_portfolio_exposure_pct = max_portfolio_exposure_pct

    def validate_trade(
        self,
        symbol: str,
        trade_value: Decimal,
        strategy_name: str,
        current_portfolio: Dict[str, Decimal],  # symbol -> current position value
        strategy_positions: Dict[str, Decimal],  # symbol -> position value for this strategy
        total_capital: Decimal,
        strategy_capital: Decimal,
    ) -> Tuple[bool, str]:
        """
        Validate if a trade would exceed risk envelope constraints.

        Args:
            symbol: Trading symbol
            trade_value: Value of the trade (price * quantity)
            strategy_name: Name of the strategy
            current_portfolio: Current positions across all strategies
            strategy_positions: Current positions for this strategy
            total_capital: Total portfolio capital
            strategy_capital: Capital allocated to this strategy

        Returns:
            Tuple of (is_valid, reason)
        """
        # Check 1: Symbol-level exposure limit
        current_symbol_exposure = current_portfolio.get(symbol, Decimal("0"))
        new_symbol_exposure = current_symbol_exposure + trade_value
        symbol_exposure_pct = (
            new_symbol_exposure / total_capital if total_capital > 0 else Decimal("0")
        )

        if symbol_exposure_pct > self.max_total_exposure_pct:
            reason = (
                f"Symbol exposure limit exceeded: {symbol_exposure_pct:.1%} > "
                f"{self.max_total_exposure_pct:.1%} (current=${current_symbol_exposure:.2f}, "
                f"trade=${trade_value:.2f})"
            )
            logger.warning(f"❌ RISK ENVELOPE: {symbol} {reason}")
            return False, reason

        # Check 2: Strategy-level exposure limit
        current_strategy_exposure = sum(strategy_positions.values())
        new_strategy_exposure = current_strategy_exposure + trade_value
        strategy_exposure_pct = (
            new_strategy_exposure / strategy_capital if strategy_capital > 0 else Decimal("0")
        )

        if strategy_exposure_pct > self.max_strategy_exposure_pct:
            reason = (
                f"Strategy exposure limit exceeded for {strategy_name}: "
                f"{strategy_exposure_pct:.1%} > {self.max_strategy_exposure_pct:.1%} "
                f"(strategy capital=${strategy_capital:.2f})"
            )
            logger.warning(f"❌ RISK ENVELOPE: {reason}")
            return False, reason

        # Check 3: Portfolio-level exposure limit
        total_current_exposure = sum(current_portfolio.values())
        total_new_exposure = total_current_exposure + trade_value
        portfolio_exposure_pct = (
            total_new_exposure / total_capital if total_capital > 0 else Decimal("0")
        )

        if portfolio_exposure_pct > self.max_portfolio_exposure_pct:
            reason = (
                f"Portfolio exposure limit exceeded: {portfolio_exposure_pct:.1%} > "
                f"{self.max_portfolio_exposure_pct:.1%} "
                f"(current total=${total_current_exposure:.2f}, trade=${trade_value:.2f})"
            )
            logger.warning(f"❌ RISK ENVELOPE: {reason}")
            return False, reason

        # All checks passed
        logger.debug(
            f"✅ RISK ENVELOPE: Trade validated for {symbol} "
            f"(symbol_exposure={symbol_exposure_pct:.1%}, "
            f"strategy_exposure={strategy_exposure_pct:.1%}, "
            f"portfolio_exposure={portfolio_exposure_pct:.1%})"
        )
        return True, "OK"

    def get_current_exposures(
        self,
        current_portfolio: Dict[str, Decimal],
        strategy_positions: Dict[str, Decimal],
        total_capital: Decimal,
        strategy_capital: Decimal,
    ) -> Dict[str, float]:
        """
        Get current exposure metrics.

        Returns:
            Dictionary with exposure percentages
        """
        total_portfolio_exposure = sum(current_portfolio.values())
        total_strategy_exposure = sum(strategy_positions.values())

        return {
            "portfolio_exposure_pct": (
                float(total_portfolio_exposure / total_capital) if total_capital > 0 else 0.0
            ),
            "strategy_exposure_pct": (
                float(total_strategy_exposure / strategy_capital) if strategy_capital > 0 else 0.0
            ),
            "largest_symbol_exposure_pct": (
                float(max(current_portfolio.values()) / total_capital)
                if current_portfolio and total_capital > 0
                else 0.0
            ),
        }
