"""
Sector Diversification Validator - TASK-5.6-SECTOR-COUNTRY-DIVERSIFICATION

Validates sector concentration constraints and generates rebalancing recommendations.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.shared.config.centralized_config import SectorCountryDiversificationConfig
from app.domain.models.portfolio import Portfolio, Position

logger = logging.getLogger(__name__)


class SectorDiversificationValidator:
    """Validator for sector concentration constraints."""

    def __init__(self, config: SectorCountryDiversificationConfig):
        """Initialize with configuration."""
        self.config = config
        self.checks_performed = 0
        self.violations_found = 0

    def validate_sector_limits(self, portfolio: Portfolio) -> List[Dict[str, Any]]:
        """
        Check sector exposure against limits.

        Returns:
            List of violation dicts for breaches
        """
        violations = []
        self.checks_performed += 1

        # Calculate sector exposures
        sector_exposure = self._calculate_sector_exposure(portfolio)
        total_value = portfolio.total_equity

        if total_value == 0:
            return violations

        # Check each sector against limits
        for sector, notional in sector_exposure.items():
            exposure_pct = notional / total_value if total_value > 0 else Decimal("0")

            # Check against sector-specific limit
            if exposure_pct > Decimal(str(self.config.max_single_sector)):
                violation = {
                    "type": "sector_exposure",
                    "sector": sector,
                    "current_exposure": float(exposure_pct),
                    "limit": self.config.max_single_sector,
                    "notional_value": float(notional),
                    "severity": self._calculate_severity(
                        exposure_pct, Decimal(str(self.config.max_single_sector))
                    ),
                    "message": f"Sector {sector} exposure {exposure_pct:.2%} exceeds limit of {self.config.max_single_sector:.2%}",
                }
                violations.append(violation)
                self.violations_found += 1

        # Check sector diversity (minimum number of sectors)
        if len(sector_exposure) < self.config.minimum_sector_count:
            violation = {
                "type": "sector_concentration",
                "current_sector_count": len(sector_exposure),
                "minimum_required": self.config.minimum_sector_count,
                "severity": "moderate",
                "message": f"Only {len(sector_exposure)} sectors, need at least {self.config.minimum_sector_count}",
            }
            violations.append(violation)
            self.violations_found += 1

        logger.info(
            f"Sector validation: {len(sector_exposure)} sectors, {len(violations)} violations"
        )
        return violations

    def validate_new_position_sector(
        self, portfolio: Portfolio, position: Position
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if adding position would violate sector limits.

        Returns:
            (allowed, reason_if_blocked)
        """
        if position.sector is None:
            return True, None  # No sector specified, allow

        # Calculate current sector exposure
        sector_exposure = self._calculate_sector_exposure(portfolio)
        total_value = portfolio.total_equity + position.market_value

        # Calculate new sector exposure if we add this position
        current_sector_value = sector_exposure.get(position.sector, Decimal("0"))
        new_sector_value = current_sector_value + position.market_value
        new_sector_pct = new_sector_value / total_value if total_value > 0 else Decimal("0")

        # Check if would breach limit
        if new_sector_pct > Decimal(str(self.config.max_single_sector)):
            reason = (
                f"Adding {position.symbol} would push {position.sector} to "
                f"{new_sector_pct:.2%}, exceeding limit of {self.config.max_single_sector:.2%}"
            )
            return False, reason

        return True, None

    def get_sector_rebalancing_suggestions(self, portfolio: Portfolio) -> List[Dict[str, Any]]:
        """
        Generate rebalancing suggestions for over-concentrated sectors.

        Returns:
            List of suggestion dicts with sector, exposure, and action
        """
        suggestions = []
        sector_exposure = self._calculate_sector_exposure(portfolio)
        total_value = portfolio.total_equity

        if total_value == 0:
            return suggestions

        for sector, notional in sector_exposure.items():
            exposure_pct = notional / total_value
            limit = Decimal(str(self.config.max_single_sector))

            if exposure_pct > limit:
                excess = exposure_pct - limit
                excess_notional = excess * total_value

                suggestion = {
                    "sector": sector,
                    "current_exposure": float(exposure_pct),
                    "current_notional": float(notional),
                    "limit": self.config.max_single_sector,
                    "excess_notional": float(excess_notional),
                    "excess_percentage": float(excess),
                    "action": f"Reduce {sector} by {excess:.2%} ({excess_notional:,.0f})",
                    "priority": "high" if excess > Decimal("0.10") else "medium",
                }
                suggestions.append(suggestion)

        logger.info(f"Generated {len(suggestions)} sector rebalancing suggestions")
        return suggestions

    def get_sector_statistics(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Return comprehensive sector metrics."""
        sector_exposure = self._calculate_sector_exposure(portfolio)
        total_value = portfolio.total_equity

        if total_value == 0:
            return {
                "total_sectors": 0,
                "sector_count": 0,
                "herfindahl_index": None,
                "sectors": {},
            }

        # Calculate Herfindahl index for sectors
        herfindahl = Decimal("0")
        sector_details = {}

        for sector, notional in sector_exposure.items():
            exposure_pct = notional / total_value
            weight_sq = exposure_pct**2
            herfindahl += weight_sq
            sector_details[sector] = {"exposure": float(exposure_pct), "notional": float(notional)}

        # Calculate effective number of sectors
        effective_sectors = Decimal("1") / herfindahl if herfindahl > 0 else Decimal("0")

        return {
            "total_sectors": len(sector_exposure),
            "sector_count": len(sector_exposure),
            "herfindahl_index": float(herfindahl),
            "effective_sectors": float(effective_sectors),
            "diversification_ratio": (
                float(effective_sectors / len(sector_exposure)) if len(sector_exposure) > 0 else 0.0
            ),
            "sectors": sector_details,
            "checks_performed": self.checks_performed,
            "violations_found": self.violations_found,
        }

    def _calculate_sector_exposure(self, portfolio: Portfolio) -> Dict[str, Decimal]:
        """Calculate aggregate exposure per sector."""
        exposure: Dict[str, Decimal] = {}

        for position in portfolio.positions:
            if position.sector is None or position.hedging.is_hedge:
                continue

            sector = position.sector
            if sector not in exposure:
                exposure[sector] = Decimal("0")
            exposure[sector] += position.market_value

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
