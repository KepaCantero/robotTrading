"""
Pre-Trade Compliance Checker
=============================

Coordinates all pre-trade compliance checks across multiple services.

Responsibilities:
- Collect pre-trade checks from all available services
- Aggregate results
- Provide unified decision on whether to execute
- Generate execution recommendations

Author: Compliance Integration System
Date: 2026-02-03
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from app.domain.services.compliance.results import PreTradeCheckResult
from app.domain.services.compliance.service_registry import get_service_registry

if TYPE_CHECKING:
    from typing import Protocol

    import pandas as pd

    from app.domain.market_analysis.microstructure.liquidity import DepthProfile
    from app.domain.strategies.alpha_models import AlphaSignal
    from app.engines.execution_engine.microstructure.harris_integration import (
        PreTradeCheckResult as HarrisPreTradeCheckResult,
    )

    class HarrisService(Protocol):
        """Superficie de harris_integrator usada por este checker."""

        def pre_trade_check(
            self,
            symbol: str,
            side: str,
            quantity: Decimal,
            current_price: Decimal,
            order_book: object = None,
            price_history: "pd.DataFrame | None" = None,
            adv: Decimal | None = None,
            urgency: float = 0.5,
            signal_time: datetime | None = None,
        ) -> HarrisPreTradeCheckResult: ...

    class LiquidityService(Protocol):
        """Superficie de liquidity_analyzer usada por este checker."""

        def measure_market_depth(
            self, order_book: object, target_size: Decimal | None = None
        ) -> DepthProfile: ...

        def calculate_liquidity_score(
            self,
            spread_bps: float,
            depth: Decimal,
            volatility: float,
            volume: float,
        ) -> float: ...

        def classify_liquidity_regime(self, liquidity_score: float) -> str: ...

    class RegimeDetectorService(Protocol):
        """Superficie de regime_detector usada por este checker."""

        def detect_regimes(
            self,
            returns: object,
            prices: object = None,
            volume: object = None,
        ) -> "pd.Series": ...

    class AlphaModelService(Protocol):
        """Superficie de alpha_model usada por este checker."""

        def generate_alpha(
            self, symbol: str, market_data: "pd.DataFrame", timestamp: datetime
        ) -> AlphaSignal | None: ...

    class VarCalculatorService(Protocol):
        """Superficie de var_calculator usada por este checker."""

        def calculate_var(
            self, returns: object, portfolio_value: float | None = None
        ) -> dict[str, object]: ...


logger = logging.getLogger(__name__)


# =============================================================================
# PRE-TRADE COMPLIANCE CHECKER
# =============================================================================


class PreTradeComplianceChecker:
    """
    Coordinates pre-trade compliance checks from all services.

    This class has a Single Responsibility:
        - Aggregate pre-trade checks from multiple services
        - Provide unified execution decision

    It delegates to:
        - HarrisIntegrator: Microstructure analysis
        - O'Hara analyzers: Liquidity and order flow
        - Chan regime detector: Market regime
        - Narang alpha model: Alpha signals
        - Hull risk calculator: VaR and risk metrics
    """

    def __init__(self) -> None:
        """Initialize the pre-trade checker with service registry."""
        self._registry = get_service_registry()
        self._cache: dict[str, Any] = {}

    # =========================================================================
    # MAIN CHECK METHOD
    # =========================================================================

    def check_signal(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        current_price: Decimal,
        price_history: pd.DataFrame | None = None,
        order_book: object | None = None,
        urgency: float = 0.5,
        signal_time: datetime | None = None,
        **kwargs: str | int | float | bool | dict | list,  # Extension point for additional params
    ) -> PreTradeCheckResult:
        """
        Perform comprehensive pre-trade check using all available services.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            current_price: Current market price
            price_history: Historical price data
            order_book: Order book snapshot
            urgency: Urgency score (0-1)
            signal_time: Signal timestamp
            **kwargs: Additional parameters

        Returns:
            PreTradeCheckResult with aggregated decision and recommendations
        """
        reasons: list[str] = []
        can_execute = True
        confidence = 1.0

        result = PreTradeCheckResult(
            passed=True,
            confidence=1.0,
            can_execute=True,
        )

        # -------------------------------------------------------------------------
        # 1. Harris & O'Hara: Microstructure Analysis
        # -------------------------------------------------------------------------
        self._check_harris_microstructure(
            symbol=symbol,
            side=side,
            quantity=quantity,
            current_price=current_price,
            order_book=order_book,
            price_history=price_history,
            urgency=urgency,
            signal_time=signal_time,
            result=result,
            reasons=reasons,
        )

        # Update decision based on Harris
        if not result.order_book_depth_ok:
            can_execute = False
            confidence = 0.0

        # -------------------------------------------------------------------------
        # 2. O'Hara: Liquidity Analysis
        # -------------------------------------------------------------------------
        if not result.order_book_depth_ok:  # Only if Harris didn't already check
            self._check_ohara_liquidity(
                symbol=symbol,
                quantity=quantity,
                order_book=order_book,
                price_history=price_history,
                result=result,
                reasons=reasons,
            )

        # -------------------------------------------------------------------------
        # 3. Ernest Chan: Regime Detection
        # -------------------------------------------------------------------------
        self._check_chan_regime(
            price_history=price_history,
            result=result,
            reasons=reasons,
        )

        # -------------------------------------------------------------------------
        # 4. Narang: Alpha Analysis
        # -------------------------------------------------------------------------
        self._check_narang_alpha(
            symbol=symbol,
            price_history=price_history,
            result=result,
            reasons=reasons,
        )

        # -------------------------------------------------------------------------
        # 5. Hull: Risk Metrics
        # -------------------------------------------------------------------------
        self._check_hull_risk(
            price_history=price_history,
            result=result,
            reasons=reasons,
        )

        # -------------------------------------------------------------------------
        # FINAL DECISION
        # -------------------------------------------------------------------------
        result.can_execute = can_execute
        result.passed = can_execute
        result.confidence = max(0.0, min(1.0, confidence))
        result.reasons = reasons

        return result

    # =========================================================================
    # INDIVIDUAL CHECK METHODS
    # =========================================================================

    def _check_harris_microstructure(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        current_price: Decimal,
        order_book: object | None,
        price_history: pd.DataFrame | None,
        urgency: float,
        signal_time: datetime | None,
        result: PreTradeCheckResult,
        reasons: list[str],
    ) -> None:
        """Check Harris microstructure analysis."""
        harris = cast("HarrisService", self._registry.get_service("harris_integrator"))
        if harris is None:
            return

        try:
            harris_check = harris.pre_trade_check(
                symbol=symbol,
                side=side,
                quantity=quantity,
                current_price=current_price,
                order_book=order_book,
                price_history=price_history,
                adv=self._estimate_adv(price_history),
                urgency=urgency,
                signal_time=signal_time,
            )

            # Copy results
            result.order_book_depth_ok = harris_check.order_book_depth_ok
            result.liquidity_score = harris_check.risk_factors.get("liquidity_score", 50.0)
            result.estimated_market_impact_bps = harris_check.estimated_cost_bps
            result.recommended_venue = harris_check.recommended_venue
            result.recommended_algorithm = harris_check.recommended_order_type
            result.recommended_limit_price = harris_check.recommended_limit_price

            if not harris_check.can_execute:
                reasons.extend(harris_check.reasons)

            if not harris_check.liquidity_sufficient:
                reasons.append("Insufficient liquidity")

        except Exception as e:
            logger.warning("Harris pre-trade check error: %s", e)

    def _check_ohara_liquidity(
        self,
        symbol: str,
        quantity: Decimal,
        order_book: object | None,
        price_history: pd.DataFrame | None,
        result: PreTradeCheckResult,
        reasons: list[str],
    ) -> None:
        """Check O'Hara liquidity analysis."""
        if price_history is None:
            return

        liquidity_analyzer = cast(
            "LiquidityService", self._registry.get_service("liquidity_analyzer")
        )
        if liquidity_analyzer is None:
            return

        try:
            if order_book:
                # Measure market depth
                depth_profile = liquidity_analyzer.measure_market_depth(
                    order_book=order_book,
                    target_size=quantity,
                )
                # DepthProfile expone total_bid_depth/total_ask_depth (sin total_depth)
                total_depth = depth_profile.total_bid_depth + depth_profile.total_ask_depth
                result.liquidity_score = liquidity_analyzer.calculate_liquidity_score(
                    spread_bps=5.0,
                    depth=total_depth,
                    volatility=0.02,
                    volume=1_000_000,
                )

                # classify_liquidity_regime devuelve directamente el string
                regime_str = liquidity_analyzer.classify_liquidity_regime(result.liquidity_score)
                result.liquidity_regime = regime_str

                if regime_str in ["LOW", "POOR"]:
                    result.confidence -= 0.2
                    reasons.append(f"Low liquidity regime: {regime_str}")

        except Exception as e:
            logger.warning("O'Hara liquidity analysis error: %s", e)

    def _check_chan_regime(
        self,
        price_history: pd.DataFrame | None,
        result: PreTradeCheckResult,
        reasons: list[str],
    ) -> None:
        """Check Chan regime detection."""
        if price_history is None:
            return

        regime_detector = cast(
            "RegimeDetectorService", self._registry.get_service("regime_detector")
        )
        if regime_detector is None:
            return

        try:
            regime_result = regime_detector.detect_regimes(price_history)
            if regime_result and len(regime_result) > 0:
                current_regime = regime_result[-1]
                result.market_regime = current_regime
                result.regime_confidence = 0.7

                # Adjust confidence based on regime
                if current_regime == "BEAR":
                    result.confidence -= 0.1
                    reasons.append("Bear market regime detected")
                elif current_regime == "BULL":
                    result.confidence += 0.05

        except Exception as e:
            logger.warning("Chan regime detection error: %s", e)

    def _check_narang_alpha(
        self,
        symbol: str,
        price_history: pd.DataFrame | None,
        result: PreTradeCheckResult,
        reasons: list[str],
    ) -> None:
        """Check Narang alpha generation."""
        if price_history is None:
            return

        alpha_model = cast("AlphaModelService", self._registry.get_service("alpha_model"))
        if alpha_model is None:
            return

        try:
            alpha_signal = alpha_model.generate_alpha(
                symbol=symbol,
                market_data=price_history,
                timestamp=datetime.now(),
            )
            if alpha_signal is None:
                return

            result.alpha_signal = float(alpha_signal.confidence)
            result.alpha_decay_rate = 0.01  # Default decay
            result.recommended_holding_period = 5  # Default days

            # Alpha quality check
            if alpha_signal.confidence < 0.3:
                result.confidence -= 0.2
                reasons.append(f"Low alpha confidence: {alpha_signal.confidence:.2f}")

        except Exception as e:
            logger.warning("Narang alpha generation error: %s", e)

    def _check_hull_risk(
        self,
        price_history: pd.DataFrame | None,
        result: PreTradeCheckResult,
        reasons: list[str],
    ) -> None:
        """Check Hull risk calculations."""
        if price_history is None:
            return

        var_calculator = cast("VarCalculatorService", self._registry.get_service("var_calculator"))
        if var_calculator is None:
            return

        try:
            # Calculate VaR
            returns = price_history["close"].pct_change().dropna()
            var_result = var_calculator.calculate_var(returns)
            var_95 = var_result.get("var")
            if not isinstance(var_95, (int, float)):
                return

            result.var_1d_95 = float(var_95)

            # Risk limits
            if abs(float(var_95)) > 0.05:  # 5% daily VaR threshold
                result.confidence -= 0.1
                reasons.append(f"High VaR: {float(var_95):.2%}")

        except Exception as e:
            logger.warning("Hull risk calculation error: %s", e)

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _estimate_adv(self, price_history: pd.DataFrame | None) -> Decimal:
        """Estimate average daily volume from price history."""
        if price_history is not None and "volume" in price_history.columns:
            return Decimal(str(price_history["volume"].mean()))
        return Decimal("1000000")  # Default

    def get_available_checks(self) -> list[str]:
        """Get list of available pre-trade checks."""
        checks = []

        if self._registry.is_available("harris_integrator"):
            checks.append("harris_microstructure")

        if self._registry.is_available("liquidity_analyzer"):
            checks.append("ohara_liquidity")

        if self._registry.is_available("regime_detector"):
            checks.append("chan_regime")

        if self._registry.is_available("alpha_model"):
            checks.append("narang_alpha")

        if self._registry.is_available("var_calculator"):
            checks.append("hull_risk")

        return checks
