"""
Default Configuration Values

Provides default values for various configuration parameters.
Single responsibility: manage default configuration values.

TASK-24: SRP Compliance - Separate default values
"""


def get_default_atr_multiplier() -> float:
    """
    Get default ATR multiplier value.

    Returns:
        Default ATR multiplier (2.0)

    Examples:
        >>> get_default_atr_multiplier()
        2.0
    """
    return 2.0


def get_default_risk_per_trade() -> float:
    """
    Get default risk per trade percentage.

    Returns:
        Default risk per trade (0.02 = 2%)

    Examples:
        >>> get_default_risk_per_trade()
        0.02
    """
    return 0.02


def get_default_max_position_size() -> float:
    """
    Get default maximum position size.

    Returns:
        Default max position size (0.25 = 25%)

    Examples:
        >>> get_default_max_position_size()
        0.25
    """
    return 0.25


def get_default_stop_distance_pct() -> float:
    """
    Get default stop loss distance percentage.

    Returns:
        Default stop distance (0.05 = 5%)

    Examples:
        >>> get_default_stop_distance_pct()
        0.05
    """
    return 0.05


def get_default_magic_values() -> dict[str, list[str]]:
    """
    Get default magic values that should be moved to configuration.

    Returns:
        Dictionary of magic value categories

    Examples:
        >>> magic_values = get_default_magic_values()
        >>> 'numeric_thresholds' in magic_values
        True
    """
    return {
        "numeric_thresholds": [
            "Signal cooldown: 10 minutes",
            "Compound score weights: 30/25/20/15/10",
            "Priority thresholds: 80/50",
            "Risk per trade: 2%",
            "Risk/reward ratio: 3:1",
            "Max consecutive stops: 5",
            "Rebalance frequency: 30 days",
            "Allocation weights: 50/25/25",
        ],
        "string_constants": [],
        "timeout_values": [],
        "retry_counts": [],
    }
