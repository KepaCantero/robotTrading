"""
Hedging Engine - Calculate optimal hedge ratios and suggest hedge instruments.

This engine provides sophisticated currency hedging calculations including:
- Optimal hedge ratio based on correlation and volatility
- Hedge instrument selection (forwards, options, ETFs)
- Hedge effectiveness tracking
- Roll optimization for rolling hedges

Key concepts:
- Minimum variance hedge ratio minimizes hedge portfolio variance
- Regression-based hedge ratio uses historical regression
- Basis risk monitoring for hedge effectiveness
- Cost optimization for hedge instrument selection
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Optional

from app.shared.utils.decimal_utils import calculate_percentage

logger = logging.getLogger(__name__)


class HedgeInstrumentType(str, Enum):
    """Types of hedge instruments."""

    FORWARD = "forward"
    FUTURE = "future"
    OPTION = "option"
    ETF = "etf"
    FUND = "fund"


class HedgeDirection(str, Enum):
    """Hedge direction."""

    LONG = "long"  # Hedge against foreign currency depreciation
    SHORT = "short"  # Hedge against foreign currency appreciation


@dataclass
class HedgeInstrument:
    """
    A specific hedge instrument available for hedging.

    Attributes:
        type: Type of instrument (forward, future, option, ETF)
        symbol: Instrument symbol (if applicable)
        currency_pair: Forex pair (e.g., EUR/USD)
        contract_size: Size of one contract in base currency
        tick_size: Minimum price movement
        tick_value: Value of one tick in base currency
        liquidity: Liquidity score (0-100)
        typical_spread_bps: Typical bid-ask spread in bps
        tenor_options: Available tenors in months (for forwards/options)
        is_exchange_traded: Whether traded on exchange
    """

    type: HedgeInstrumentType
    currency_pair: str
    contract_size: Decimal
    liquidity: int  # 0-100
    typical_spread_bps: Decimal
    symbol: Optional[str] = None
    tick_size: Optional[Decimal] = None
    tick_value: Optional[Decimal] = None
    tenor_options: list[int] = field(default_factory=lambda: [1, 3, 6, 12])
    is_exchange_traded: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "symbol": self.symbol,
            "currency_pair": self.currency_pair,
            "contract_size": str(self.contract_size),
            "tick_size": str(self.tick_size) if self.tick_size else None,
            "tick_value": str(self.tick_value) if self.tick_value else None,
            "liquidity": self.liquidity,
            "typical_spread_bps": str(self.typical_spread_bps),
            "tenor_options": self.tenor_options,
            "is_exchange_traded": self.is_exchange_traded,
        }


@dataclass
class HedgeRecommendation:
    """
    A specific hedging recommendation.

    Attributes:
        currency: Currency to hedge
        direction: Hedge direction (long/short)
        amount_eur: Amount to hedge in base currency
        optimal_ratio: Optimal hedge ratio (0-1)
        instrument: Recommended hedge instrument
        contracts: Number of contracts (if applicable)
        tenor_months: Recommended hedge tenor
        expected_cost_eur: Expected hedging cost
        expected_cost_bps: Cost in basis points
        effectiveness: Expected hedge effectiveness (0-1)
        roll_schedule: Recommended roll schedule
        reasoning: Explanation of recommendation
        priority: Priority level
    """

    currency: str
    direction: HedgeDirection
    amount_eur: Decimal
    optimal_ratio: Decimal
    instrument: HedgeInstrument
    contracts: Optional[int]
    tenor_months: int
    expected_cost_eur: Decimal
    expected_cost_bps: Decimal
    effectiveness: Decimal
    roll_schedule: Optional[str]
    reasoning: str
    priority: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "currency": self.currency,
            "direction": self.direction.value,
            "amount_eur": str(self.amount_eur),
            "optimal_ratio": str(self.optimal_ratio),
            "instrument": self.instrument.to_dict(),
            "contracts": self.contracts,
            "tenor_months": self.tenor_months,
            "expected_cost_eur": str(self.expected_cost_eur),
            "expected_cost_bps": str(self.expected_cost_bps),
            "effectiveness": str(self.effectiveness),
            "roll_schedule": self.roll_schedule,
            "reasoning": self.reasoning,
            "priority": self.priority,
        }


@dataclass
class HedgeEffectiveness:
    """
    Measures how effective a hedge has been.

    Attributes:
        currency: Currency being hedged
        hedge_ratio: Hedge ratio used
        period_start: Start of measurement period
        period_end: End of measurement period
        portfolio_return_eur: Portfolio return in EUR (unhedged)
        hedge_return_eur: Hedge return in EUR
        combined_return_eur: Combined (hedged) return in EUR
        variance_reduction: Percentage of variance reduction
        effectiveness: Overall effectiveness score (0-1)
        basis_risk: Observed basis risk
    """

    currency: str
    hedge_ratio: Decimal
    period_start: datetime
    period_end: datetime
    portfolio_return_eur: Decimal
    hedge_return_eur: Decimal
    combined_return_eur: Decimal
    variance_reduction: Decimal
    effectiveness: Decimal
    basis_risk: Decimal

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "currency": self.currency,
            "hedge_ratio": str(self.hedge_ratio),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "portfolio_return_eur": str(self.portfolio_return_eur),
            "hedge_return_eur": str(self.hedge_return_eur),
            "combined_return_eur": str(self.combined_return_eur),
            "variance_reduction": str(self.variance_reduction),
            "effectiveness": str(self.effectiveness),
            "basis_risk": str(self.basis_risk),
        }


class HedgingEngine:
    """
    Calculate optimal hedge ratios and suggest hedge instruments.

    Features:
    - Minimum variance hedge ratio
    - Correlation-based hedge ratio
    - Optimal instrument selection
    - Cost optimization
    - Hedge effectiveness tracking

    Example:
        engine = HedgingEngine(forex_service=forex_fetcher)
        recommendation = await engine.get_recommendation(
            exposure_eur=Decimal("50000"),
            currency="USD",
            risk_tolerance=Decimal("0.8"),
        )
    """

    # Default hedge instruments
    DEFAULT_INSTRUMENTS: ClassVar[dict] = {
        "USD": [
            HedgeInstrument(
                type=HedgeInstrumentType.FORWARD,
                currency_pair="EUR/USD",
                contract_size=Decimal("100000"),
                liquidity=100,
                typical_spread_bps=Decimal("2"),
                tenor_options=[1, 3, 6, 12],
                is_exchange_traded=False,
            ),
            HedgeInstrument(
                type=HedgeInstrumentType.FUTURE,
                symbol="6E",
                currency_pair="EUR/USD",
                contract_size=Decimal("125000"),
                tick_size=Decimal("0.00005"),
                tick_value=Decimal("6.25"),
                liquidity=95,
                typical_spread_bps=Decimal("1"),
                is_exchange_traded=True,
            ),
        ],
        "GBP": [
            HedgeInstrument(
                type=HedgeInstrumentType.FORWARD,
                currency_pair="EUR/GBP",
                contract_size=Decimal("100000"),
                liquidity=95,
                typical_spread_bps=Decimal("3"),
                tenor_options=[1, 3, 6, 12],
                is_exchange_traded=False,
            ),
        ],
        "JPY": [
            HedgeInstrument(
                type=HedgeInstrumentType.FORWARD,
                currency_pair="EUR/JPY",
                contract_size=Decimal("100000"),
                liquidity=90,
                typical_spread_bps=Decimal("3"),
                tenor_options=[1, 3, 6, 12],
                is_exchange_traded=False,
            ),
        ],
    }

    # Default correlations with EUR (for hedge ratio calculation)
    DEFAULT_CORRELATIONS: ClassVar[dict] = {
        "USD": Decimal("0.95"),  # EUR/USD highly correlated with US stocks
        "GBP": Decimal("0.85"),
        "JPY": Decimal("0.70"),
        "CHF": Decimal("0.90"),
        "AUD": Decimal("0.75"),
        "CAD": Decimal("0.88"),
    }

    # Relative volatilities (for minimum variance hedge ratio)
    DEFAULT_VOLATILITIES: ClassVar[dict] = {
        "EUR": Decimal("0.08"),  # EUR volatility
        "USD": Decimal("0.10"),  # USD volatility
        "GBP": Decimal("0.12"),
        "JPY": Decimal("0.11"),
        "CHF": Decimal("0.09"),
        "AUD": Decimal("0.13"),
        "CAD": Decimal("0.11"),
    }

    def __init__(
        self,
        forex_service: Optional[Any] = None,
        base_currency: str = "EUR",
    ):
        """
        Initialize hedging engine.

        Args:
            forex_service: Forex data service
            base_currency: Base currency (EUR for Spain)
        """
        self.forex_service = forex_service
        self.base_currency = base_currency.upper()

        # Historical hedge effectiveness tracking
        self._effectiveness_history: dict[str, list[HedgeEffectiveness]] = {}

        logger.info(f"HedgingEngine initialized with base currency {base_currency}")

    async def calculate_optimal_hedge_ratio(
        self,
        exposure_eur: Decimal,
        currency: str,
        method: str = "minimum_variance",
        correlation: Optional[Decimal] = None,
        volatility_asset: Optional[Decimal] = None,
        volatility_fx: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate optimal hedge ratio for a currency exposure.

        The hedge ratio h* minimizes the variance of the hedged portfolio.
        Different methods:

        1. Minimum Variance: h* = correlation * (sigma_asset / sigma_fx)
        2. Naive: h* = 1.0 (full hedge)
        3. Partial: h* = 0.5 (50% hedge)

        Args:
            exposure_eur: Exposure amount in EUR
            currency: Currency to hedge
            method: Calculation method (minimum_variance, naive, partial)
            correlation: Correlation between asset and FX rate
            volatility_asset: Volatility of asset returns
            volatility_fx: Volatility of FX rate

        Returns:
            Optimal hedge ratio (0-1)
        """
        logger.debug(f"Calculating optimal hedge ratio for {currency} using {method}")

        if method == "naive":
            # Naive hedge: fully hedge
            return Decimal("1.0")

        if method == "partial":
            # Partial hedge: 50%
            return Decimal("0.5")

        if method == "minimum_variance":
            # h* = rho * (sigma_s / sigma_f)
            # where:
            #   rho = correlation between asset and FX
            #   sigma_s = volatility of asset (in foreign currency)
            #   sigma_f = volatility of FX rate

            # Use defaults if not provided
            if correlation is None:
                correlation = self.DEFAULT_CORRELATIONS.get(currency, Decimal("0.85"))

            if volatility_asset is None:
                # Assume equity volatility ~15%
                volatility_asset = Decimal("0.15")

            if volatility_fx is None:
                volatility_fx = self.DEFAULT_VOLATILITIES.get(currency, Decimal("0.10"))

            # Calculate minimum variance hedge ratio
            hedge_ratio = correlation * (volatility_asset / volatility_fx)

            # Bound between 0 and 1
            hedge_ratio = max(Decimal("0"), min(Decimal("1"), hedge_ratio))

            logger.debug(
                f"MV hedge ratio for {currency}: {hedge_ratio:.3f} "
                f"(corr={correlation:.2f}, vol_asset={volatility_asset:.2f}, vol_fx={volatility_fx:.2f})"
            )

            return hedge_ratio

        # Default: 80% hedge
        return Decimal("0.8")

    async def get_recommendation(
        self,
        exposure_eur: Decimal,
        currency: str,
        risk_tolerance: Optional[Decimal] = None,
        preferred_tenor_months: int = 3,
        method: str = "minimum_variance",
    ) -> HedgeRecommendation:
        """
        Get hedging recommendation for a currency exposure.

        Args:
            exposure_eur: Exposure amount in EUR
            currency: Currency to hedge
            risk_tolerance: Risk tolerance (0-1, 1 = fully hedge)
            preferred_tenor_months: Preferred hedge tenor
            method: Hedge ratio calculation method

        Returns:
            Hedge recommendation
        """
        if risk_tolerance is None:
            risk_tolerance = Decimal("0.8")
        logger.info(f"Generating hedge recommendation for {exposure_eur} EUR {currency} exposure")

        # Calculate optimal hedge ratio
        optimal_ratio = await self.calculate_optimal_hedge_ratio(
            exposure_eur=exposure_eur,
            currency=currency,
            method=method,
        )

        # Adjust for risk tolerance
        adjusted_ratio = optimal_ratio * risk_tolerance
        hedge_amount_eur = exposure_eur * adjusted_ratio

        # Select best instrument
        instrument = self._select_instrument(currency, hedge_amount_eur, preferred_tenor_months)

        # Calculate contracts
        contracts = self._calculate_contracts(instrument, hedge_amount_eur)

        # Estimate cost
        cost_eur = await self._estimate_hedge_cost(
            instrument=instrument,
            amount_eur=hedge_amount_eur,
            tenor_months=preferred_tenor_months,
            currency=currency,
        )

        cost_bps = calculate_percentage(cost_eur, hedge_amount_eur) or Decimal("0")

        # Estimate effectiveness
        effectiveness = self._estimate_effectiveness(currency, adjusted_ratio)

        # Determine direction
        direction = HedgeDirection.SHORT  # Typically short FX for long foreign assets

        # Roll schedule
        roll_schedule = self._generate_roll_schedule(preferred_tenor_months)

        # Reasoning
        reasoning = self._generate_reasoning(
            currency=currency,
            exposure_eur=exposure_eur,
            hedge_ratio=adjusted_ratio,
            instrument=instrument,
            cost_bps=cost_bps,
        )

        # Priority
        priority = self._determine_priority(exposure_eur, adjusted_ratio)

        return HedgeRecommendation(
            currency=currency,
            direction=direction,
            amount_eur=hedge_amount_eur,
            optimal_ratio=adjusted_ratio,
            instrument=instrument,
            contracts=contracts,
            tenor_months=preferred_tenor_months,
            expected_cost_eur=cost_eur,
            expected_cost_bps=cost_bps,
            effectiveness=effectiveness,
            roll_schedule=roll_schedule,
            reasoning=reasoning,
            priority=priority,
        )

    def calculate_effectiveness(
        self,
        portfolio_return_local: Decimal,
        fx_return: Decimal,
        hedge_ratio: Decimal,
    ) -> Decimal:
        """
        Calculate hedge effectiveness.

        Effectiveness measures how much the hedge reduced variance.
        A perfect hedge has effectiveness = 1.0.

        Args:
            portfolio_return_local: Portfolio return in local currency
            fx_return: FX rate return (base/foreign)
            hedge_ratio: Hedge ratio used

        Returns:
            Hedge effectiveness (0-1)
        """
        # Unhedged return in base currency
        # R_unhedged ≈ R_local + R_fx (for small returns)
        unhedged_return = portfolio_return_local + fx_return

        # Hedged return
        # R_hedged ≈ R_local + (1 - h) * R_fx
        hedged_return = portfolio_return_local + (Decimal("1") - hedge_ratio) * fx_return

        # Effectiveness = variance reduction
        # Simplified: use squared returns as proxy for variance
        var_unhedged = unhedged_return**2
        var_hedged = hedged_return**2

        if var_unhedged == 0:
            return Decimal("1")  # Perfect hedge (no variance to reduce)

        effectiveness = (var_unhedged - var_hedged) / var_unhedged

        # Bound between 0 and 1
        return max(Decimal("0"), min(Decimal("1"), effectiveness))

    def track_effectiveness(
        self,
        currency: str,
        hedge_ratio: Decimal,
        period_start: datetime,
        period_end: datetime,
        portfolio_return_eur: Decimal,
        hedge_return_eur: Decimal,
        combined_return_eur: Decimal,
    ) -> HedgeEffectiveness:
        """
        Track hedge effectiveness over a period.

        Args:
            currency: Currency being hedged
            hedge_ratio: Hedge ratio used
            period_start: Start of period
            period_end: End of period
            portfolio_return_eur: Portfolio return in EUR (unhedged)
            hedge_return_eur: Hedge return in EUR
            combined_return_eur: Combined (hedged) return in EUR

        Returns:
            Hedge effectiveness metrics
        """
        # Calculate variance reduction
        var_unhedged = portfolio_return_eur**2
        var_hedged = combined_return_eur**2

        if var_unhedged > 0:
            variance_reduction = (var_unhedged - var_hedged) / var_unhedged
        else:
            variance_reduction = Decimal("0")

        # Overall effectiveness
        effectiveness = max(Decimal("0"), min(Decimal("1"), variance_reduction))

        # Basis risk (imperfect hedge effectiveness)
        basis_risk = Decimal("1") - effectiveness

        effectiveness_obj = HedgeEffectiveness(
            currency=currency,
            hedge_ratio=hedge_ratio,
            period_start=period_start,
            period_end=period_end,
            portfolio_return_eur=portfolio_return_eur,
            hedge_return_eur=hedge_return_eur,
            combined_return_eur=combined_return_eur,
            variance_reduction=variance_reduction,
            effectiveness=effectiveness,
            basis_risk=basis_risk,
        )

        # Store in history
        if currency not in self._effectiveness_history:
            self._effectiveness_history[currency] = []
        self._effectiveness_history[currency].append(effectiveness_obj)

        logger.info(
            f"Tracked hedge effectiveness for {currency}: {effectiveness:.1%} variance reduction"
        )

        return effectiveness_obj

    def get_effectiveness_history(
        self,
        currency: str,
        limit: int = 10,
    ) -> list[HedgeEffectiveness]:
        """
        Get historical hedge effectiveness for a currency.

        Args:
            currency: Currency code
            limit: Maximum number of records to return

        Returns:
            List of historical effectiveness measurements
        """
        history = self._effectiveness_history.get(currency, [])
        return history[-limit:]

    def _select_instrument(
        self,
        currency: str,
        amount_eur: Decimal,
        tenor_months: int,
    ) -> HedgeInstrument:
        """
        Select best hedge instrument for given parameters.

        Args:
            currency: Currency to hedge
            amount_eur: Amount to hedge
            tenor_months: Required tenor

        Returns:
            Selected hedge instrument
        """
        # Get available instruments
        instruments = self.DEFAULT_INSTRUMENTS.get(currency, [])

        if not instruments:
            # Create default forward instrument
            return HedgeInstrument(
                type=HedgeInstrumentType.FORWARD,
                currency_pair=f"{self.base_currency}/{currency}",
                contract_size=Decimal("100000"),
                liquidity=80,
                typical_spread_bps=Decimal("5"),
                tenor_options=[1, 3, 6, 12],
                is_exchange_traded=False,
            )

        # Filter by tenor
        valid_instruments = [instr for instr in instruments if tenor_months in instr.tenor_options]

        if not valid_instruments:
            valid_instruments = instruments

        # Score instruments (higher is better)
        def score(instr: HedgeInstrument) -> Decimal:
            # Factors: liquidity (40%), spread (40%), exchange traded (20%)
            liquidity_score = Decimal(str(instr.liquidity / 100)) * Decimal("0.4")
            spread_score = (
                (Decimal("100") - instr.typical_spread_bps) / Decimal("100") * Decimal("0.4")
            )
            exchange_bonus = Decimal("0.2") if instr.is_exchange_traded else Decimal("0")
            return liquidity_score + spread_score + exchange_bonus

        # Select best
        valid_instruments.sort(key=lambda i: score(i), reverse=True)
        return valid_instruments[0]

    def _calculate_contracts(
        self,
        instrument: HedgeInstrument,
        amount_eur: Decimal,
    ) -> Optional[int]:
        """
        Calculate number of contracts needed.

        Args:
            instrument: Hedge instrument
            amount_eur: Amount to hedge

        Returns:
            Number of contracts (None if not applicable)
        """
        if not instrument.is_exchange_traded:
            return None

        if instrument.contract_size == 0:
            return None

        contracts = int(amount_eur / instrument.contract_size)
        return max(1, contracts)

    async def _estimate_hedge_cost(
        self,
        instrument: HedgeInstrument,
        amount_eur: Decimal,
        tenor_months: int,
        currency: str,
    ) -> Decimal:
        """
        Estimate hedging cost.

        Args:
            instrument: Hedge instrument
            amount_eur: Amount to hedge
            tenor_months: Hedge tenor
            currency: Currency being hedged

        Returns:
            Estimated cost in EUR
        """
        # Base cost from spread
        spread_cost = amount_eur * instrument.typical_spread_bps / Decimal("10000")

        # Forward points (interest rate differential)
        # Simplified calculation
        if instrument.type == HedgeInstrumentType.FORWARD:
            # Assume ~2% annual interest rate diff max
            rate_diff = Decimal("0.02")  # ~2% annual interest rate diff
            time_in_years = Decimal(str(tenor_months / 12))
            forward_cost = amount_eur * rate_diff * time_in_years
            return spread_cost + forward_cost

        # For futures/options, mainly spread cost
        return spread_cost

    def _estimate_effectiveness(
        self,
        currency: str,
        hedge_ratio: Decimal,
    ) -> Decimal:
        """
        Estimate hedge effectiveness.

        Args:
            currency: Currency being hedged
            hedge_ratio: Hedge ratio

        Returns:
            Estimated effectiveness (0-1)
        """
        # Base effectiveness from correlation
        correlation = self.DEFAULT_CORRELATIONS.get(currency, Decimal("0.85"))

        # Adjust for hedge ratio
        # Partial hedge has lower effectiveness
        effectiveness = correlation * hedge_ratio

        return effectiveness

    def _generate_roll_schedule(
        self,
        tenor_months: int,
    ) -> str:
        """
        Generate roll schedule recommendation.

        Args:
            tenor_months: Initial hedge tenor

        Returns:
            Roll schedule string
        """
        return {
            1: "Roll monthly, 1 week before expiry",
            3: "Roll quarterly, 2 weeks before expiry",
            6: "Roll semi-annually, 1 month before expiry",
        }.get(tenor_months, "Roll annually, 2 months before expiry")

    def _generate_reasoning(
        self,
        currency: str,
        exposure_eur: Decimal,
        hedge_ratio: Decimal,
        instrument: HedgeInstrument,
        cost_bps: Decimal,
    ) -> str:
        """Generate reasoning for recommendation."""
        return (
            f"Hedge {hedge_ratio:.1%} of {currency} exposure using {instrument.type.value} "
            f"instrument. Estimated cost: {cost_bps:.1f} bps. "
            f"This reduces currency risk while maintaining some upside potential."
        )

    def _determine_priority(
        self,
        exposure_eur: Decimal,
        hedge_ratio: Decimal,
    ) -> str:
        """Determine priority of hedge recommendation."""
        if exposure_eur >= Decimal("50000") and hedge_ratio < Decimal("0.5"):
            return "critical"
        elif exposure_eur >= Decimal("25000"):
            return "high"
        elif exposure_eur >= Decimal("10000"):
            return "medium"
        return "low"

    def clear_effectiveness_history(self, currency: Optional[str] = None) -> None:
        """
        Clear effectiveness history.

        Args:
            currency: Currency to clear (None = clear all)
        """
        if currency:
            self._effectiveness_history.pop(currency, None)
            logger.debug(f"Cleared effectiveness history for {currency}")
        else:
            self._effectiveness_history.clear()
            logger.debug("Cleared all effectiveness history")
