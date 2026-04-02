"""
Country Diversification Validator - TASK-5.6-SECTOR-COUNTRY-DIVERSIFICATION

Validates country/geographic concentration constraints and generates rebalancing recommendations.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.models.portfolio import Portfolio, Position
    from app.shared.config.centralized_config import SectorCountryDiversificationConfig

logger = logging.getLogger(__name__)


class CountryDiversificationValidator:
    """Validator for country concentration constraints."""

    def __init__(self, config: SectorCountryDiversificationConfig):
        """Initialize with configuration."""
        self.config = config
        self.checks_performed = 0
        self.violations_found = 0

    def validate_country_limits(self, portfolio: Portfolio) -> list[dict[str, Any]]:
        """
        Check country exposure against limits.

        Returns:
            List of violation dicts for breaches
        """
        violations = []
        self.checks_performed += 1

        # Calculate country exposures
        country_exposure = self._calculate_country_exposure(portfolio)
        total_value = portfolio.total_equity

        if total_value == 0:
            return violations

        # Check each country against limits
        for country, notional in country_exposure.items():
            exposure_pct = notional / total_value if total_value > 0 else Decimal("0")

            # Check against country-specific limit
            if exposure_pct > Decimal(str(self.config.max_single_country)):
                violation = {
                    "type": "country_exposure",
                    "country": country,
                    "current_exposure": float(exposure_pct),
                    "limit": self.config.max_single_country,
                    "notional_value": float(notional),
                    "severity": self._calculate_severity(
                        exposure_pct, Decimal(str(self.config.max_single_country))
                    ),
                    "message": f"Country {country} exposure {exposure_pct:.2%} exceeds limit of {self.config.max_single_country:.2%}",
                }
                violations.append(violation)
                self.violations_found += 1

        # Check country diversity (minimum number of countries)
        if len(country_exposure) < self.config.minimum_country_count:
            violation = {
                "type": "country_concentration",
                "current_country_count": len(country_exposure),
                "minimum_required": self.config.minimum_country_count,
                "severity": "moderate",
                "message": f"Only {len(country_exposure)} countries, need at least {self.config.minimum_country_count}",
            }
            violations.append(violation)
            self.violations_found += 1

        logger.info(
            f"Country validation: {len(country_exposure)} countries, {len(violations)} violations"
        )
        return violations

    def validate_new_position_country(
        self, portfolio: Portfolio, position: Position
    ) -> tuple[bool, str | None]:
        """
        Check if adding position would violate country limits.

        Returns:
            (allowed, reason_if_blocked)
        """
        if position.country is None:
            return True, None  # No country specified, allow

        # Calculate current country exposure
        country_exposure = self._calculate_country_exposure(portfolio)
        total_value = portfolio.total_equity + position.market_value

        # Calculate new country exposure if we add this position
        current_country_value = country_exposure.get(position.country, Decimal("0"))
        new_country_value = current_country_value + position.market_value
        new_country_pct = new_country_value / total_value if total_value > 0 else Decimal("0")

        # Check if would breach limit
        if new_country_pct > Decimal(str(self.config.max_single_country)):
            reason = (
                f"Adding {position.symbol} would push {position.country} to "
                f"{new_country_pct:.2%}, exceeding limit of {self.config.max_single_country:.2%}"
            )
            return False, reason

        return True, None

    def get_country_rebalancing_suggestions(self, portfolio: Portfolio) -> list[dict[str, Any]]:
        """
        Generate rebalancing suggestions for over-concentrated countries.

        Returns:
            List of suggestion dicts with country, exposure, and action
        """
        suggestions = []
        country_exposure = self._calculate_country_exposure(portfolio)
        total_value = portfolio.total_equity

        if total_value == 0:
            return suggestions

        for country, notional in country_exposure.items():
            exposure_pct = notional / total_value
            limit = Decimal(str(self.config.max_single_country))

            if exposure_pct > limit:
                excess = exposure_pct - limit
                excess_notional = excess * total_value

                suggestion = {
                    "country": country,
                    "current_exposure": float(exposure_pct),
                    "current_notional": float(notional),
                    "limit": self.config.max_single_country,
                    "excess_notional": float(excess_notional),
                    "excess_percentage": float(excess),
                    "action": f"Reduce {country} by {excess:.2%} ({excess_notional:,.0f})",
                    "priority": "high" if excess > Decimal("0.10") else "medium",
                }
                suggestions.append(suggestion)

        logger.info(f"Generated {len(suggestions)} country rebalancing suggestions")
        return suggestions

    def get_country_statistics(self, portfolio: Portfolio) -> dict[str, Any]:
        """Return comprehensive country metrics."""
        country_exposure = self._calculate_country_exposure(portfolio)
        total_value = portfolio.total_equity

        if total_value == 0:
            return {
                "total_countries": 0,
                "country_count": 0,
                "herfindahl_index": None,
                "countries": {},
            }

        # Calculate Herfindahl index for countries
        herfindahl = Decimal("0")
        country_details = {}

        for country, notional in country_exposure.items():
            exposure_pct = notional / total_value
            weight_sq = exposure_pct**2
            herfindahl += weight_sq
            country_details[country] = {
                "exposure": float(exposure_pct),
                "notional": float(notional),
            }

        # Calculate effective number of countries
        effective_countries = Decimal("1") / herfindahl if herfindahl > 0 else Decimal("0")

        return {
            "total_countries": len(country_exposure),
            "country_count": len(country_exposure),
            "herfindahl_index": float(herfindahl),
            "effective_countries": float(effective_countries),
            "diversification_ratio": (
                float(effective_countries / len(country_exposure))
                if len(country_exposure) > 0
                else 0.0
            ),
            "countries": country_details,
            "checks_performed": self.checks_performed,
            "violations_found": self.violations_found,
        }

    def _calculate_country_exposure(self, portfolio: Portfolio) -> dict[str, Decimal]:
        """Calculate aggregate exposure per country."""
        exposure: dict[str, Decimal] = {}

        for position in portfolio.positions:
            if position.country is None or position.hedging.is_hedge:
                continue

            country = position.country
            if country not in exposure:
                exposure[country] = Decimal("0")
            exposure[country] += position.market_value

        return exposure

    def _calculate_severity(self, actual: Decimal, limit: Decimal) -> str:
        """Calculate violation severity."""
        if actual <= limit:
            return "none"

        excess_pct = (actual - limit) / limit
        if excess_pct > Decimal("0.20"):  # > 20% over limit
            return "severe"
        elif excess_pct > Decimal("0.10"):  # > 10% over limit
            return "moderate"
        else:
            return "minor"
