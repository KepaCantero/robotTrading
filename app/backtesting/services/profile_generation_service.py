"""
Profile Generation Service

Handles generation of investor profile combinations for batch testing.

Responsibilities:
- Generate all profile combinations (objectives × risk × tier × horizon)
- Map capital tiers to configuration keys
- Handle profile creation logic
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, List

from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.core.tier_mapper import map_profile_tier_to_config

logger = logging.getLogger(__name__)

ConfigDict = Dict


class ProfileGenerationService:
    """
    Service for generating investor profile combinations.

    Creates all possible combinations of investment objectives,
    risk tolerances, capital tiers, and investment horizons for
    batch backtesting.
    """

    def __init__(self, capital_tiers: ConfigDict):
        """
        Initialize profile generation service.

        Args:
            capital_tiers: Dictionary mapping tier keys to capital amounts
        """
        self.capital_tiers = capital_tiers

    def generate_all_profiles(self, investment_horizons: List[int]) -> List[InputProfile]:
        """
        Generate all profile combinations.

        Combinations:
        - 5 objectives
        - 3 risk tolerances (bajo, medio, alto)
        - 3 capital tiers (bajo, medio, alto)
        - N investment horizons (loaded from config)

        Args:
            investment_horizons: List of investment horizon values in months

        Returns:
            List of InputProfile objects
        """
        profiles = []

        # Generate combinations
        objectives = list(ObjectivoInversion)
        risk_tolerances = list(RiskTolerance)
        capital_tiers = ["bajo", "medio", "alto"]

        for objective in objectives:
            for risk in risk_tolerances:
                for tier in capital_tiers:
                    for horizon in investment_horizons:
                        # Get capital for tier
                        capital = Decimal(str(self.capital_tiers.get(tier, 100000)))

                        # Create profile
                        profile = InputProfile(
                            capital_initial=capital,
                            objetivo_inversion=objective,
                            risk_tolerance=risk,
                            investment_horizon=horizon,
                        )
                        profiles.append(profile)

        expected_count = (
            len(objectives) * len(risk_tolerances) * len(capital_tiers) * len(investment_horizons)
        )
        logger.info(
            f"Generated {len(profiles)} profile combinations "
            f"({len(objectives)} objectives × {len(risk_tolerances)} risk levels × "
            f"{len(capital_tiers)} tiers × {len(investment_horizons)} horizons = {expected_count})"
        )
        return profiles

    @staticmethod
    def get_capital_tier_key(profile: InputProfile) -> str:
        """
        Map capital_flag to config tier key using unified tier mapping.

        The InputProfile.capital_flag returns 'small', 'medium', 'large'
        but config expects 'bajo', 'medio', 'alto'.
        This method uses the centralized TierMapper to ensure consistency
        across all tier conversions in the system.

        Tier Systems:
        - InputProfile.capital_flag: small (<€50k), medium (€50k-€250k), large (>=€250k)
        - investment_profiles.yaml: micro (<€15k), small (€15k-€50k), medium (€50k-€250k), large (>=€250k)
        - Config (Spanish): bajo (<€50k), medio (€50k-€250k), alto (>=€250k)

        Args:
            profile: InputProfile

        Returns:
            Mapped tier key for config lookups (bajo, medio, or alto)

        Examples:
            >>> profile = InputProfile(capital_initial=30000, ...)
            >>> ProfileGenerationService.get_capital_tier_key(profile)
            'bajo'
            >>> profile = InputProfile(capital_initial=100000, ...)
            >>> ProfileGenerationService.get_capital_tier_key(profile)
            'medio'
            >>> profile = InputProfile(capital_initial=500000, ...)
            >>> ProfileGenerationService.get_capital_tier_key(profile)
            'alto'
        """
        try:
            # Use the centralized tier mapper for consistency
            return map_profile_tier_to_config(profile.capital_flag, target_format="spanish")
        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # Fallback to manual mapping if tier mapper fails
            logger.warning(f"Tier mapper failed for {profile.capital_flag}, using fallback: {e}")
            tier_map = {"small": "bajo", "medium": "medio", "large": "alto"}
            return tier_map.get(profile.capital_flag, "medio")
