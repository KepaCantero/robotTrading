"""
Historical data fixtures for backtesting tests.

This module provides sample historical market data and trading signals
for testing backtesting functionality with known outcomes.
"""

import math
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from app.models.momentum import MarketData
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType


def create_spy_2020_trending_market_data() -> List[MarketData]:
    """Create SPY market data for trending market (recent dates)."""
    data = []
    base_date = datetime(2025, 1, 1)  # Changed to 2024
    base_price = Decimal("320.0")

    # Simulate trending market with some volatility
    for i in range(252):  # Trading days in a year
        date = base_date + timedelta(days=i)

        # Add trend and some noise
        trend_factor = 1 + (i * 0.001)  # 0.1% daily trend
        noise_factor = 1 + ((i % 10 - 5) * 0.002)  # ±1% noise

        price = base_price * Decimal(str(trend_factor * noise_factor))

        # Create OHLC data
        open_price = price * Decimal("0.999")
        high_price = price * Decimal("1.005")
        low_price = price * Decimal("0.995")
        close_price = price

        volume = Decimal("50000000")  # 50M shares

        # Bid-ask spread
        spread = price * Decimal("0.001")  # 0.1% spread
        bid = price - spread / Decimal("2")
        ask = price + spread / Decimal("2")

        data.append(
            MarketData(
                symbol="SPY",
                timestamp=date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                bid=bid,
                ask=ask,
                spread=spread,
            )
        )

    return data


def create_spy_2020_trending_signals() -> List[Signal]:
    """Create trading signals for SPY trending market."""
    signals = []
    base_date = datetime(2025, 1, 1)  # Changed to 2024

    # Buy signals at the beginning of uptrends
    buy_dates = [0, 30, 60, 90, 120, 150, 180, 210]

    for day_offset in buy_dates:
        signal_date = base_date + timedelta(days=day_offset)
        price = Decimal("320.0") * Decimal(str(1 + day_offset * 0.001))

        signals.append(
            Signal(
                symbol="SPY",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=80.0,
                liquidity_score=95.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("1000000"),
                timestamp=signal_date,
            )
        )

    # Sell signals at the end of trends
    sell_dates = [25, 55, 85, 115, 145, 175, 205, 235]

    for day_offset in sell_dates:
        signal_date = base_date + timedelta(days=day_offset)
        price = Decimal("320.0") * Decimal(str(1 + day_offset * 0.001))

        signals.append(
            Signal(
                symbol="SPY",
                signal_type=SignalType.SELL,
                strength=SignalStrength.MODERATE,
                confidence=70.0,
                liquidity_score=95.0,
                priority_score=75.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("1000000"),
                timestamp=signal_date,
            )
        )

    return signals


def create_spy_2020_ranging_market_data() -> List[MarketData]:
    """Create SPY market data for ranging market (sideways)."""
    data = []
    base_date = datetime(2025, 1, 1)
    base_price = Decimal("320.0")

    # Simulate ranging market
    for i in range(252):
        date = base_date + timedelta(days=i)

        # Add cyclical movement (ranging)
        cycle_factor = 1 + Decimal(
            str(0.02 * math.sin(i * math.pi / 30))
        )  # 30-day cycle

        price = base_price * cycle_factor

        # Create OHLC data
        open_price = price * Decimal("0.999")
        high_price = price * Decimal("1.003")
        low_price = price * Decimal("0.997")
        close_price = price

        volume = Decimal("40000000")  # 40M shares

        # Bid-ask spread
        spread = (price * Decimal("0.001")).quantize(Decimal("0.000001"))
        bid = (price - spread / Decimal("2")).quantize(Decimal("0.000001"))
        ask = (price + spread / Decimal("2")).quantize(Decimal("0.000001"))

        data.append(
            MarketData(
                symbol="SPY",
                timestamp=date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                bid=bid,
                ask=ask,
                spread=spread,
            )
        )

    return data


def create_spy_2020_ranging_signals() -> List[Signal]:
    """Create trading signals for SPY 2020 ranging market."""
    signals = []
    base_date = datetime(2025, 1, 1)

    # Buy signals at cycle lows
    buy_dates = [15, 45, 75, 105, 135, 165, 195, 225]

    for day_offset in buy_dates:
        signal_date = base_date + timedelta(days=day_offset)
        price = Decimal("320.0") * Decimal(
            str(1 + 0.02 * math.sin(day_offset * math.pi / 30))
        )

        signals.append(
            Signal(
                symbol="SPY",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=65.0,
                liquidity_score=95.0,
                priority_score=70.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("1000000"),
                timestamp=signal_date,
            )
        )

    # Sell signals at cycle highs
    sell_dates = [0, 30, 60, 90, 120, 150, 180, 210]

    for day_offset in sell_dates:
        signal_date = base_date + timedelta(days=day_offset)
        price = Decimal("320.0") * Decimal(
            str(1 + 0.02 * math.sin(day_offset * math.pi / 30))
        )

        signals.append(
            Signal(
                symbol="SPY",
                signal_type=SignalType.SELL,
                strength=SignalStrength.MODERATE,
                confidence=65.0,
                liquidity_score=95.0,
                priority_score=70.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("1000000"),
                timestamp=signal_date,
            )
        )

    return signals


def create_contradictory_signals() -> List[Signal]:
    """Create contradictory signals for testing signal handling."""
    base_date = datetime(2025, 1, 1)

    return [
        # Buy signal
        Signal(
            symbol="TEST",  # Changed to match market data
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=90.0,
            liquidity_score=85.0,
            priority_score=90.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.0"),
            volume=Decimal("2000000"),
            timestamp=base_date,
        ),
        # Contradictory sell signal immediately after
        Signal(
            symbol="TEST",  # Changed to match market data
            signal_type=SignalType.SELL,
            strength=SignalStrength.STRONG,
            confidence=85.0,
            liquidity_score=85.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("151.0"),
            volume=Decimal("2000000"),
            timestamp=base_date + timedelta(minutes=1),
        ),
        # Another buy signal
        Signal(
            symbol="TEST",  # Changed to match market data
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=75.0,
            liquidity_score=85.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("152.0"),
            volume=Decimal("1500000"),
            timestamp=base_date + timedelta(minutes=2),
        ),
    ]


def create_single_day_market_data() -> List[MarketData]:
    """Create single day market data for simple tests."""
    base_date = datetime(2025, 1, 1)

    return [
        MarketData(
            symbol="TEST",
            timestamp=base_date,
            open_price=Decimal("100.0"),
            high_price=Decimal("105.0"),
            low_price=Decimal("98.0"),
            close_price=Decimal("102.0"),
            volume=Decimal("1000000"),
            bid=Decimal("101.9"),
            ask=Decimal("102.1"),
            spread=Decimal("0.2"),
        )
    ]


def create_single_day_signals() -> List[Signal]:
    """Create single day trading signals for simple tests."""
    base_date = datetime(2025, 1, 1)

    return [
        Signal(
            symbol="TEST",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=90.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("102.0"),
            volume=Decimal("1000"),
            timestamp=base_date,
        )
    ]
