"""
Forex Risk Tracker - Track FX exposure for EUR-based investors.

Spain residents trading US stocks have EUR/USD currency risk.
This tracker calculates exposure and suggests hedges.

Key features:
- Calculate FX exposure by currency
- Calculate unhedged exposure
- Currency hedging recommendations
- Forward contract cost calculation
- Multi-currency P&L tracking
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.core.decimal_utils import to_decimal, safe_decimal_divide, calculate_percentage
from app.core.timezone_utils import utc_now
from app.models.portfolio import Portfolio, Position


logger = logging.getLogger(__name__)


@dataclass
class CurrencyExposure:
    """
    Exposure for a single currency.

    Attributes:
        currency: ISO currency code (e.g., USD, GBP, JPY)
        exposure_eur: Total exposure in EUR (positive = long, negative = short)
        hedge_eur: Amount hedged in EUR
        net_exposure_eur: Unhedged exposure (exposure - hedge)
        hedge_ratio: Hedge coverage ratio (0 = no hedge, 1 = fully hedged)
        unrealized_pnl_eur: Unrealized P&L from FX movements
        unrealized_pnl_pct: P&L as percentage of exposure
        position_count: Number of positions in this currency
    """

    currency: str
    exposure_eur: Decimal
    hedge_eur: Decimal
    net_exposure_eur: Decimal
    hedge_ratio: Decimal
    unrealized_pnl_eur: Decimal
    unrealized_pnl_pct: Decimal
    position_count: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "currency": self.currency,
            "exposure_eur": str(self.exposure_eur),
            "hedge_eur": str(self.hedge_eur),
            "net_exposure_eur": str(self.net_exposure_eur),
            "hedge_ratio": str(self.hedge_ratio),
            "unrealized_pnl_eur": str(self.unrealized_pnl_eur),
            "unrealized_pnl_pct": str(self.unrealized_pnl_pct),
            "position_count": self.position_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CurrencyExposure":
        """Create from dictionary."""
        return cls(
            currency=data["currency"],
            exposure_eur=to_decimal(data["exposure_eur"]),
            hedge_eur=to_decimal(data["hedge_eur"]),
            net_exposure_eur=to_decimal(data["net_exposure_eur"]),
            hedge_ratio=to_decimal(data["hedge_ratio"]),
            unrealized_pnl_eur=to_decimal(data["unrealized_pnl_eur"]),
            unrealized_pnl_pct=to_decimal(data["unrealized_pnl_pct"]),
            position_count=data["position_count"],
        )


@dataclass
class ForexExposureReport:
    """
    Complete FX exposure report for a portfolio.

    Attributes:
        timestamp: When report was generated
        base_currency: Portfolio base currency
        total_portfolio_eur: Total portfolio value in base currency
        total_exposure_eur: Total FX exposure in EUR
        total_unhedged_eur: Total unhedged exposure
        overall_hedge_ratio: Overall hedge coverage
        fx_pnl_eur: Total unrealized FX P&L
        by_currency: Exposure by currency
        hedging_recommendations: List of hedging recommendations
        risk_level: Overall FX risk level (low, medium, high, critical)
    """

    timestamp: datetime
    base_currency: str
    total_portfolio_eur: Decimal
    total_exposure_eur: Decimal
    total_unhedged_eur: Decimal
    overall_hedge_ratio: Decimal
    fx_pnl_eur: Decimal
    by_currency: Dict[str, CurrencyExposure]
    hedging_recommendations: List[dict]
    risk_level: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "base_currency": self.base_currency,
            "total_portfolio_eur": str(self.total_portfolio_eur),
            "total_exposure_eur": str(self.total_exposure_eur),
            "total_unhedged_eur": str(self.total_unhedged_eur),
            "overall_hedge_ratio": str(self.overall_hedge_ratio),
            "fx_pnl_eur": str(self.fx_pnl_eur),
            "by_currency": {
                currency: exposure.to_dict()
                for currency, exposure in self.by_currency.items()
            },
            "hedging_recommendations": self.hedging_recommendations,
            "risk_level": self.risk_level,
        }


class ForexRiskTracker:
    """
    Track FX exposure for EUR-based investors.

    Key metrics:
    - FX exposure by currency
    - Unhedged exposure
    - Currency hedging recommendations
    - Forward contract cost calculation
    - Multi-currency P&L

    Example:
        tracker = ForexRiskTracker(base_currency="EUR", forex_service=forex_fetcher)
        report = await tracker.generate_report(portfolio)
        print(f"Unhedged USD exposure: {report.total_unhedged_eur}")
    """

    # Currency symbol suffixes for auto-detection
    CURRENCY_SUFFIXES = {
        "EUR": [".MC", ".PA", ".AS", ".DE", ".MI"],  # European exchanges
        "GBP": [".L"],  # London
        "CAD": [".TO"],
        "CHF": [".SW"],
        "JPY": [".T"],
        "AUD": [".AX"],
        "NZD": [".NZ"],
        "HKD": [".HK"],
        "INR": [".NS", ".BO"],
        "CNY": [".SS", ".SZ"],
    }

    # Risk level thresholds for unhedged exposure
    RISK_THRESHOLDS = {
        "low": Decimal("0.05"),      # < 5% of portfolio
        "medium": Decimal("0.10"),   # 5-10% of portfolio
        "high": Decimal("0.20"),     # 10-20% of portfolio
        "critical": Decimal("0.20"), # > 20% of portfolio
    }

    def __init__(
        self,
        base_currency: str = "EUR",
        forex_service: Optional[Any] = None,
        min_hedge_threshold: Decimal = Decimal("10000"),
    ):
        """
        Initialize forex risk tracker.

        Args:
            base_currency: Base currency (EUR for Spain residents)
            forex_service: Forex data service for rates (from forex_data_service)
            min_hedge_threshold: Minimum unhedged exposure to recommend hedge
        """
        self.base_currency = base_currency.upper()
        self.forex_service = forex_service
        self.min_hedge_threshold = min_hedge_threshold

        # State
        self._fx_rates: Dict[str, Tuple[Decimal, datetime]] = {}
        self._rate_cache_duration_seconds = 3600  # 1 hour

        logger.info(
            f"ForexRiskTracker initialized with base currency {base_currency}, "
            f"min hedge threshold {min_hedge_threshold}"
        )

    async def generate_report(self, portfolio: Portfolio) -> ForexExposureReport:
        """
        Generate complete FX exposure report.

        Args:
            portfolio: Current portfolio with positions

        Returns:
            Complete FX exposure report
        """
        logger.info("Generating FX exposure report")

        # Calculate exposures by currency
        exposures = await self.calculate_fx_exposure(portfolio)

        # Calculate totals
        total_portfolio_eur = portfolio.total_equity
        total_exposure_eur = sum(e.exposure_eur for e in exposures.values())
        total_unhedged_eur = self.calculate_unhedged_exposure(exposures)
        overall_hedge_ratio = self._calculate_overall_hedge_ratio(exposures, total_exposure_eur)
        fx_pnl_eur = sum(e.unrealized_pnl_eur for e in exposures.values())

        # Get hedging recommendations
        recommendations = await self.get_hedging_recommendation(exposures)

        # Determine risk level
        risk_level = self._determine_risk_level(total_unhedged_eur, total_portfolio_eur)

        return ForexExposureReport(
            timestamp=utc_now(),
            base_currency=self.base_currency,
            total_portfolio_eur=total_portfolio_eur,
            total_exposure_eur=total_exposure_eur,
            total_unhedged_eur=total_unhedged_eur,
            overall_hedge_ratio=overall_hedge_ratio,
            fx_pnl_eur=fx_pnl_eur,
            by_currency=exposures,
            hedging_recommendations=recommendations,
            risk_level=risk_level,
        )

    async def calculate_fx_exposure(
        self,
        portfolio: Portfolio,
    ) -> Dict[str, CurrencyExposure]:
        """
        Calculate exposure by currency.

        Args:
            portfolio: Current portfolio with positions

        Returns:
            Dict mapping currency to exposure info
        """
        logger.debug(f"Calculating FX exposure for portfolio with {len(portfolio.positions)} positions")

        # Get current FX rates
        await self._update_fx_rates()

        # Group positions by currency
        exposure_data: Dict[str, Dict[str, Any]] = {}

        for position in portfolio.positions:
            # Skip hedge positions
            if position.hedging.is_hedge:
                continue

            currency = self._get_position_currency(position)
            value_local = position.quantity * position.market_price

            # Convert to base currency
            value_eur = await self._convert_to_eur(value_local, currency)

            # Calculate FX P&L (change in value since entry due to FX)
            # This assumes avg_price was in local currency
            cost_local = position.quantity * position.avg_price
            cost_eur = await self._convert_to_eur(cost_local, currency)
            fx_pnl_eur = value_eur - cost_eur

            # Accumulate
            if currency not in exposure_data:
                exposure_data[currency] = {
                    "exposure_eur": Decimal("0"),
                    "hedge_eur": Decimal("0"),
                    "unrealized_pnl_eur": Decimal("0"),
                    "position_count": 0,
                }

            exposure_data[currency]["exposure_eur"] += value_eur
            exposure_data[currency]["unrealized_pnl_eur"] += fx_pnl_eur
            exposure_data[currency]["position_count"] += 1

            # Add hedge if position has hedging metadata
            if position.hedging.hedge_ratio > 0:
                hedge_eur = value_eur * position.hedging.hedge_ratio
                exposure_data[currency]["hedge_eur"] += hedge_eur

        # Create CurrencyExposure objects
        result: Dict[str, CurrencyExposure] = {}
        for currency, data in exposure_data.items():
            exposure_eur = data["exposure_eur"]
            hedge_eur = data["hedge_eur"]
            net_exposure_eur = exposure_eur - hedge_eur
            hedge_ratio = safe_decimal_divide(hedge_eur, exposure_eur, Decimal("0"))
            unrealized_pnl_eur = data["unrealized_pnl_eur"]
            unrealized_pnl_pct = calculate_percentage(unrealized_pnl_eur, exposure_eur) or Decimal("0")

            result[currency] = CurrencyExposure(
                currency=currency,
                exposure_eur=exposure_eur,
                hedge_eur=hedge_eur,
                net_exposure_eur=net_exposure_eur,
                hedge_ratio=hedge_ratio,
                unrealized_pnl_eur=unrealized_pnl_eur,
                unrealized_pnl_pct=unrealized_pnl_pct,
                position_count=data["position_count"],
            )

        logger.debug(f"Calculated FX exposure for {len(result)} currencies")
        return result

    def calculate_unhedged_exposure(
        self,
        exposures: Dict[str, CurrencyExposure],
    ) -> Decimal:
        """
        Calculate unhedged FX risk.

        Args:
            exposures: Currency exposures

        Returns:
            Total unhedged exposure in base currency
        """
        # Sum of net exposure (excluding base currency)
        total_unhedged = Decimal("0")
        for currency, exposure in exposures.items():
            if currency != self.base_currency:
                total_unhedged += abs(exposure.net_exposure_eur)

        return total_unhedged

    async def get_hedging_recommendation(
        self,
        exposures: Dict[str, CurrencyExposure],
    ) -> List[dict]:
        """
        Get currency hedging recommendations.

        Args:
            exposures: Current currency exposures

        Returns:
            List of hedging recommendations
        """
        recommendations = []

        for currency, exposure in exposures.items():
            if currency == self.base_currency:
                continue

            net_exposure = abs(exposure.net_exposure_eur)

            # Only recommend if above threshold
            if net_exposure >= self.min_hedge_threshold:
                direction = "short" if exposure.net_exposure_eur > 0 else "long"

                # Calculate forward cost
                try:
                    forward_rate, cost_eur = await self.calculate_forward_cost(
                        currency=currency,
                        amount_eur=net_exposure,
                        months=3,
                    )
                except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                    logger.warning(f"Could not calculate forward cost for {currency}: {e}")
                    forward_rate = None
                    cost_eur = None

                recommendation = {
                    "currency": currency,
                    "action": "hedge",
                    "direction": direction,
                    "amount_eur": str(net_exposure),
                    "current_hedge_ratio": str(exposure.hedge_ratio),
                    "recommended_instrument": f"{self.base_currency}/{currency} forward",
                    "recommended_tenor_months": 3,
                    "forward_rate": str(forward_rate) if forward_rate else None,
                    "estimated_cost_eur": str(cost_eur) if cost_eur else None,
                    "cost_bps": str(calculate_percentage(cost_eur, net_exposure)) if cost_eur else None,
                    "reason": (
                        f"Unhedged {direction} exposure of {net_exposure:,.2f} {self.base_currency} "
                        f"to {currency}. Current hedge ratio: {exposure.hedge_ratio:.1%}"
                    ),
                    "priority": self._get_hedge_priority(net_exposure, exposure.hedge_ratio),
                }
                recommendations.append(recommendation)

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda r: priority_order.get(r["priority"], 99))

        return recommendations

    async def calculate_forward_cost(
        self,
        currency: str,
        amount_eur: Decimal,
        months: int = 3,
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate forward contract cost for hedging.

        Args:
            currency: Currency to hedge
            amount_eur: Amount in base currency (EUR)
            months: Forward contract months (1, 3, 6, 12 typical)

        Returns:
            Tuple of (forward_rate, cost_eur)

        Note: This is a simplified calculation. In production, you would:
        - Get actual forward rates from your broker
        - Use interest rate differentials
        - Account for bid-ask spreads
        - Consider counterparty risk
        """
        # Get current spot rate
        spot_rate = await self._get_fx_rate(currency)

        if not spot_rate:
            raise ValueError(f"No FX rate available for {self.base_currency}/{currency}")

        # Calculate forward points using interest rate differential
        # Forward = Spot * (1 + r_quote * t) / (1 + r_base * t)
        # Simplified: Forward = Spot * (1 + rate_diff * t)

        # Assumed interest rates (in production, get from market data)
        interest_rates = {
            "EUR": Decimal("0.0375"),  # ~3.75% ECB
            "USD": Decimal("0.0425"),  # ~4.25% Fed
            "GBP": Decimal("0.0450"),  # ~4.5% BoE
            "CHF": Decimal("0.0100"),  # ~1% SNB
            "JPY": Decimal("0.0000"),  # ~0% BoJ
            "CAD": Decimal("0.0375"),  # ~3.75% BoC
            "AUD": Decimal("0.0350"),  # ~3.5% RBA
        }

        base_rate = interest_rates.get(self.base_currency, Decimal("0.03"))
        quote_rate = interest_rates.get(currency, Decimal("0.03"))
        rate_diff = quote_rate - base_rate

        # Time in years
        t = Decimal(str(months / 12))

        # Forward rate calculation
        forward_rate = spot_rate * (Decimal("1") + rate_diff * t)

        # Calculate cost (positive = cost to hedge, negative = gain)
        # For long foreign exposure: sell foreign forward
        cost_eur = amount_eur * (forward_rate / spot_rate - 1)

        logger.debug(
            f"Forward cost for {currency}: spot={spot_rate}, forward={forward_rate}, "
            f"cost={cost_eur} for {amount_eur} EUR over {months} months"
        )

        return forward_rate, cost_eur

    def _get_position_currency(self, position: Position) -> str:
        """
        Get currency of a position.

        Uses symbol suffix patterns for auto-detection.

        Args:
            position: Portfolio position

        Returns:
            ISO currency code
        """
        # First check explicit currency field
        if hasattr(position, 'currency') and position.currency:
            return position.currency.upper()

        # Detect from symbol suffix
        symbol = position.symbol.upper()

        # Check known suffixes
        for currency, suffixes in self.CURRENCY_SUFFIXES.items():
            for suffix in suffixes:
                if symbol.endswith(suffix):
                    return currency

        # Special handling for .L (could be GBP or EUR)
        if symbol.endswith(".L"):
            # Assume GBP for London
            return "GBP"

        # Default: US stocks = USD
        return "USD"

    async def _convert_to_eur(
        self,
        amount: Decimal,
        from_currency: str,
    ) -> Decimal:
        """
        Convert amount to base currency (EUR).

        Args:
            amount: Amount in source currency
            from_currency: Source currency code

        Returns:
            Amount in base currency (EUR)
        """
        if from_currency == self.base_currency:
            return amount

        # Get FX rate
        rate = await self._get_fx_rate(from_currency)

        if rate is None or rate == 0:
            logger.warning(f"No FX rate for {from_currency}, using 1.0")
            return amount

        return amount / rate

    async def _get_fx_rate(self, currency: str) -> Optional[Decimal]:
        """
        Get FX rate for a currency.

        Returns rate as base/currency (e.g., EUR/USD = 1.08).

        Args:
            currency: Currency code to get rate for

        Returns:
            FX rate or None if unavailable
        """
        pair = f"{self.base_currency}{currency}"

        # Check cache
        if pair in self._fx_rates:
            rate, timestamp = self._fx_rates[pair]
            age = (utc_now() - timestamp).total_seconds()
            if age < self._rate_cache_duration_seconds:
                return rate

        # Try to get from forex service
        if self.forex_service:
            try:
                # Format pair for service (EUR/USD format)
                pair_str = f"{self.base_currency}/{currency}"
                rates = self.forex_service.get_current_rates([pair_str])

                if pair_str in rates:
                    rate = rates[pair_str]
                    self._fx_rates[pair] = (rate, utc_now())
                    return rate
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.warning(f"Failed to get FX rate from service: {e}")

        # Use fallback rates
        fallback_rates = {
            "EURUSD": Decimal("1.08"),
            "EURGBP": Decimal("0.86"),
            "EURJPY": Decimal("162.0"),
            "EURCHF": Decimal("0.94"),
            "EURAUD": Decimal("1.65"),
            "EURCAD": Decimal("1.47"),
            "EURNZD": Decimal("1.78"),
            "EURHKD": Decimal("8.45"),
            "EURINR": Decimal("90.0"),
        }

        return fallback_rates.get(pair)

    async def _update_fx_rates(self) -> None:
        """Update FX rates from data service."""
        if not self.forex_service:
            return

        # Major pairs for base currency
        currencies = ["USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "HKD", "INR"]
        pairs = [f"{self.base_currency}/{ccy}" for ccy in currencies]

        try:
            rates = self.forex_service.get_current_rates(pairs)

            for pair, rate in rates.items():
                # Convert pair format EUR/USD to EURUSD
                pair_key = pair.replace("/", "")
                self._fx_rates[pair_key] = (rate, utc_now())

            logger.debug(f"Updated {len(rates)} FX rates")
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.warning(f"Could not update FX rates: {e}")

    def _calculate_overall_hedge_ratio(
        self,
        exposures: Dict[str, CurrencyExposure],
        total_exposure_eur: Decimal,
    ) -> Decimal:
        """
        Calculate overall hedge ratio across all currencies.

        Args:
            exposures: Currency exposures
            total_exposure_eur: Total exposure

        Returns:
            Overall hedge ratio (0-1)
        """
        if total_exposure_eur == 0:
            return Decimal("0")

        total_hedged = sum(e.hedge_eur for e in exposures.values())
        return safe_decimal_divide(total_hedged, total_exposure_eur, Decimal("0"))

    def _determine_risk_level(
        self,
        unhedged_eur: Decimal,
        total_portfolio_eur: Decimal,
    ) -> str:
        """
        Determine overall FX risk level.

        Args:
            unhedged_eur: Total unhedged exposure
            total_portfolio_eur: Total portfolio value

        Returns:
            Risk level: low, medium, high, or critical
        """
        if total_portfolio_eur == 0:
            return "low"

        ratio = safe_decimal_divide(unhedged_eur, total_portfolio_eur, Decimal("0"))

        if ratio < self.RISK_THRESHOLDS["low"]:
            return "low"
        elif ratio < self.RISK_THRESHOLDS["medium"]:
            return "medium"
        elif ratio < self.RISK_THRESHOLDS["high"]:
            return "high"
        else:
            return "critical"

    def _get_hedge_priority(
        self,
        unhedged_eur: Decimal,
        current_hedge_ratio: Decimal,
    ) -> str:
        """
        Determine priority for hedging recommendation.

        Args:
            unhedged_eur: Unhedged amount
            current_hedge_ratio: Current hedge ratio (0-1)

        Returns:
            Priority: critical, high, medium, low
        """
        # Critical: large exposure with no hedge
        if unhedged_eur >= Decimal("50000") and current_hedge_ratio < Decimal("0.25"):
            return "critical"

        # High: significant exposure or low hedge
        if unhedged_eur >= Decimal("25000") or current_hedge_ratio < Decimal("0.5"):
            return "high"

        # Medium: moderate exposure
        if unhedged_eur >= Decimal("10000") or current_hedge_ratio < Decimal("0.75"):
            return "medium"

        # Low: small exposure or well hedged
        return "low"

    def clear_rate_cache(self) -> None:
        """Clear cached FX rates."""
        self._fx_rates.clear()
        logger.debug("Cleared FX rate cache")
