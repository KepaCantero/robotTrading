"""
Slippage Utility Functions

Centralized slippage calculations for backtesting.
This eliminates duplicated slippage logic across multiple files.

Usage:
    from app.backtesting.shared.slippage_utils import apply_slippage

    adjusted_price = apply_slippage(price, is_buy=True)
"""

from __future__ import annotations

from decimal import Decimal

from app.shared.config.centralized_config import get_config


def apply_slippage(
    price: Decimal,
    is_buy: bool,
    slippage_pct: Decimal | None = None,
    is_stop: bool = False,
    is_volatile: bool = False,
) -> Decimal:
    """
    Apply slippage to a price.

    This is the SINGLE SOURCE OF TRUTH for slippage calculations.
    Replaces duplicated _apply_slippage() in engine.py and trade_executor.py.

    Args:
        price: Original price
        is_buy: True if buying (slippage increases price), False if selling
        slippage_pct: Optional custom slippage percentage. If None, uses config.
        is_stop: True if this is a stop order (worse execution)
        is_volatile: True if market is volatile (worse execution)

    Returns:
        Price with slippage applied

    Example:
        >>> apply_slippage(Decimal("100"), is_buy=True)
        Decimal("100.10")  # 0.1% slippage added

        >>> apply_slippage(Decimal("100"), is_buy=False)
        Decimal("99.90")   # 0.1% slippage subtracted
    """
    config = get_config().backtesting

    if slippage_pct is not None:
        # Custom slippage provided - use directly
        slippage_factor = slippage_pct / Decimal("100")
    else:
        # Use centralized config with conditionals
        slippage_factor = config.get_slippage_pct(is_stop=is_stop, is_volatile=is_volatile)

    if is_buy:
        return price * (Decimal("1") + slippage_factor)
    else:
        return price * (Decimal("1") - slippage_factor)


def calculate_slippage_pct(
    is_stop: bool = False,
    is_volatile: bool = False,
    optimistic: bool = False,
) -> Decimal:
    """
    Calculate slippage percentage based on conditions.

    Args:
        is_stop: True if this is a stop order
        is_volatile: True if market is volatile
        optimistic: True to use optimistic slippage (lower)

    Returns:
        Slippage as decimal percentage (e.g., 0.001 = 0.1%)
    """
    config = get_config().backtesting

    if optimistic:
        base = config.optimistic_slippage_bps / Decimal("10000")
    else:
        base = config.base_slippage_bps / Decimal("10000")

    result = base

    if is_stop:
        result *= config.stop_slippage_multiplier
    if is_volatile:
        result *= config.volatility_multiplier

    return result


def get_base_slippage_bps() -> Decimal:
    """Get base slippage in basis points from config."""
    return get_config().backtesting.base_slippage_bps


def get_slippage_for_capital(capital: Decimal) -> Decimal:
    """
    Get appropriate slippage based on capital level.

    Larger accounts may have worse execution due to market impact.

    Args:
        capital: Account capital

    Returns:
        Slippage multiplier (1.0 = normal, >1.0 = worse execution)
    """
    if capital > Decimal("500000"):
        return Decimal("1.5")  # Large accounts have more market impact
    elif capital > Decimal("100000"):
        return Decimal("1.2")
    else:
        return Decimal("1.0")  # Normal slippage for smaller accounts
