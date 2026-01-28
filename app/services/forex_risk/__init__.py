"""
Forex Risk Management Module - Phase 3.2

This module provides FX exposure tracking and hedging recommendations for
multi-currency portfolios, with special focus on Spain residents (EUR-based)
trading US stocks and other international assets.

Critical for Spain residents:
- EUR/USD movement can erase profits from US stock positions
- Multi-currency exposure tracking (USD, GBP, JPY, CHF, etc.)
- Currency hedging recommendations (forward contracts, options)
- Forward contract cost calculation
- Hedge effectiveness tracking

Components:
- ForexRiskTracker: Track FX exposure by currency and calculate unhedged risk
- HedgingEngine: Calculate optimal hedge ratios and suggest hedge instruments

Example usage:
    from app.services.forex_risk import ForexRiskTracker, HedgingEngine
    from app.services.forex_data_service import get_forex_fetcher

    tracker = ForexRiskTracker(base_currency="EUR", forex_service=get_forex_fetcher())
    exposures = await tracker.calculate_fx_exposure(portfolio)
    unhedged = tracker.calculate_unhedged_exposure(exposures)
    recommendations = await tracker.get_hedging_recommendation(exposures)

    hedging_engine = HedgingEngine(forex_service=get_forex_fetcher())
    hedge_ratio = await hedging_engine.calculate_optimal_hedge_ratio(
        exposure_eur=Decimal("50000"),
        currency="USD",
        risk_tolerance=Decimal("0.8"),
    )
"""

from app.services.forex_risk.hedging_engine import (
    HedgeEffectiveness,
    HedgeInstrument,
    HedgeRecommendation,
    HedgingEngine,
)
from app.services.forex_risk.tracker import (
    CurrencyExposure,
    ForexExposureReport,
    ForexRiskTracker,
)

__all__ = [
    # Tracker
    "CurrencyExposure",
    "ForexRiskTracker",
    "ForexExposureReport",
    # Hedging
    "HedgeRecommendation",
    "HedgeInstrument",
    "HedgingEngine",
    "HedgeEffectiveness",
]
