"""
Trade Utility Functions

Centralized trade-related utilities for backtesting.
This eliminates duplicated trade logic across multiple files.

Usage:
    from app.backtesting.shared.trade_utils import build_trade_reason
"""

from decimal import Decimal
from typing import Any, Optional

from app.shared.config.centralized_config import get_config


def build_trade_reason(signal: Any, market_data: Any = None) -> str:
    """
    Build a human-readable trade reason string from a signal.

    This is the SINGLE SOURCE OF TRUTH for trade reason building.
    Replaces duplicated _build_trade_reason() in engine.py and trade_executor.py.

    Args:
        signal: Signal object with signal_type, source, confidence, metadata
        market_data: Optional market data (for additional context)

    Returns:
        Formatted trade reason string

    Example:
        >>> reason = build_trade_reason(signal)
        "BUY via momentum_filter (rsi=35.2, ema_trend=up) conf=85.0%"
    """
    reason_parts = []

    # Signal type (BUY/SELL)
    signal_type_str = (
        signal.signal_type.value
        if hasattr(signal.signal_type, "value")
        else str(signal.signal_type)
    )
    reason_parts.append(signal_type_str.upper())

    # Source
    source_str = signal.source.value if hasattr(signal.source, "value") else str(signal.source)
    if source_str:
        reason_parts.append(f"via {source_str}")

    # Key metadata
    if signal.metadata:
        metadata_strs = []
        # Important keys to include in reason
        important_keys = [
            "rsi",
            "ema_trend",
            "volume_ratio",
            "z_score",
            "spread",
            "momentum_score",
            "atr_pct",
        ]
        for key in important_keys:
            if key in signal.metadata:
                value = signal.metadata[key]
                if isinstance(value, float):
                    metadata_strs.append(f"{key}={value:.2f}")
                else:
                    metadata_strs.append(f"{key}={value}")

        if metadata_strs:
            reason_parts.append("(" + ", ".join(metadata_strs) + ")")

    # Confidence
    if hasattr(signal, "confidence") and signal.confidence is not None:
        reason_parts.append(f"conf={signal.confidence:.1f}%")

    return " ".join(reason_parts)


def calculate_position_size(
    capital: Decimal,
    price: Decimal,
    risk_pct: Optional[Decimal] = None,
    max_position_pct: Optional[Decimal] = None,
) -> Decimal:
    """
    Calculate position size based on capital and risk parameters.

    This is a centralized position sizing calculation.
    Uses config defaults if parameters not provided.

    Args:
        capital: Available capital
        price: Current price
        risk_pct: Risk percentage per trade (default from config)
        max_position_pct: Maximum position size percentage (default from config)

    Returns:
        Number of shares/units to trade
    """
    config = get_config().backtesting

    if risk_pct is None:
        risk_pct = config.default_max_position_size
    if max_position_pct is None:
        max_position_pct = config.default_max_position_size

    # Calculate position based on capital allocation
    position_value = capital * min(risk_pct, max_position_pct)

    # Convert to shares
    if price > 0:
        shares = position_value / price
        return shares.quantize(Decimal("1"))  # Round to whole shares

    return Decimal("0")


def get_commission(
    trade_value: Decimal,
    shares: Decimal,
    capital: Decimal,
    commission_type: str = "rate",
) -> Decimal:
    """
    Calculate commission for a trade.

    This is the SINGLE SOURCE OF TRUTH for commission calculations.

    Args:
        trade_value: Total trade value in currency
        shares: Number of shares traded
        capital: Account capital (for tier determination)
        commission_type: "rate" (percentage), "per_share", or "fixed"

    Returns:
        Commission amount in currency
    """
    config = get_config().backtesting

    if commission_type == "rate":
        # Percentage of trade value
        commission = trade_value * config.default_commission_rate
        return max(commission, config.min_commission)

    elif commission_type == "per_share":
        # Per-share commission (e.g., IBKR)
        commission = shares * config.default_commission_per_share
        return max(commission, config.min_commission)

    elif commission_type == "fixed":
        # Fixed fee per trade
        return config.default_commission_fixed

    else:
        # Default to rate-based
        commission = trade_value * config.default_commission_rate
        return max(commission, config.min_commission)


def validate_trade(
    shares: Decimal,
    price: Decimal,
    capital: Decimal,
    symbol: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate a trade against position limits.

    Args:
        shares: Number of shares to trade
        price: Trade price
        capital: Available capital
        symbol: Optional symbol for specific rules

    Returns:
        Tuple of (is_valid, error_message)
    """
    config = get_config().backtesting

    trade_value = shares * price
    position_pct = trade_value / capital if capital > 0 else Decimal("1")

    max_position = config.get_position_limit_for_capital(capital)

    if position_pct > max_position:
        return False, f"Position {position_pct:.2%} exceeds max {max_position:.2%}"

    if position_pct < config.default_min_position_size:
        return (
            False,
            f"Position {position_pct:.2%} below min {config.default_min_position_size:.2%}",
        )

    return True, None


def format_pnl(pnl: Decimal, capital: Decimal) -> str:
    """
    Format P&L as a readable string with percentage.

    Args:
        pnl: Profit/loss amount
        capital: Initial capital

    Returns:
        Formatted string like "+$1,234.56 (+1.23%)" or "-$500.00 (-0.50%)"
    """
    pct = (pnl / capital * 100) if capital > 0 else Decimal("0")

    if pnl >= 0:
        return f"+${pnl:,.2f} (+{pct:.2f}%)"
    else:
        return f"-${abs(pnl):,.2f} ({pct:.2f}%)"
