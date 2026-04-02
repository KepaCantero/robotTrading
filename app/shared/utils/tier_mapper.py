"""
Unified Tier Mapping System

This module provides a centralized, consistent mapping between different tier
naming conventions used across the algorithmic trading system.

PROBLEM:
The system uses THREE different tier systems:
1. InputProfile.capital_flag: "small", "medium", "large" (English, 3 tiers)
2. investment_profiles.yaml: "micro", "small", "medium", "large" (English, 4 tiers)
3. Config expectations: "bajo", "medio", "alto" (Spanish, 3 tiers)

SOLUTION:
This module provides:
- Unified tier mapping between all systems
- Capital-based tier determination
- Validation and consistency checking
- Comprehensive documentation
- Integration with centralized capital_tiers.yaml configuration

Configuration:
Capital thresholds are now loaded from config/capital_tiers.yaml.

Usage:
    from app.shared.utils.tier_mapper import TierMapper, get_tier, normalize_tier

    # Get tier from capital amount
    tier = get_tier(Decimal("100000"))  # Returns "medium"

    # Normalize tier name to standard format
    normalized = normalize_tier("small")  # Returns "small"

    # Map between different systems
    spanish_tier = TierMapper.to_spanish("medium")  # Returns "medio"
    yaml_tier = TierMapper.to_yaml_tier("medium")  # Returns "medium"
"""

from __future__ import annotations

import logging
from decimal import Decimal
from enum import Enum
from typing import ClassVar

# Import centralized configuration (REQUIRED - no fallbacks)
from app.shared.config.strategy_config_loader import get_strategy_config

logger = logging.getLogger(__name__)


class TierSystem(str, Enum):
    """
    Different tier naming systems used in the codebase.
    """

    CAPITAL_FLAG = "capital_flag"  # InputProfile.capital_flag: small, medium, large
    YAML = "yaml"  # investment_profiles.yaml: micro, small, medium, large
    SPANISH = "spanish"  # Config expectations: bajo, medio, alto
    STANDARD = "standard"  # Internal standard: micro, small, medium, large


class TierMapper:
    """
    Centralized tier mapping between different naming conventions.

    This class handles conversion between the three tier systems used in the
    algorithmic trading system, ensuring consistency and preventing errors.

    Capital thresholds are loaded from config/capital_tiers.yaml if available.
    """

    # Capital thresholds (EUR) - loaded from config or using defaults
    # These will be updated on first access if config is available
    THRESHOLDS: ClassVar[dict[str, Decimal]] = {
        "micro": Decimal("0"),  # Not used for micro, but defined for completeness
        "small": Decimal("15000"),  # €15k - €50k
        "medium": Decimal("50000"),  # €50k - €250k
        "large": Decimal("250000"),  # >= €250k
    }

    @classmethod
    def _load_thresholds_from_config(cls) -> None:
        """Load thresholds from centralized config (REQUIRED)."""
        if cls.THRESHOLDS.get("loaded", False) is False:
            try:
                config = get_strategy_config()
                thresholds = config.get_tier_thresholds()
                if thresholds:
                    cls.THRESHOLDS = {
                        "micro": Decimal("0"),
                        "small": Decimal(str(thresholds.get("small", 15000))),
                        "medium": Decimal(str(thresholds.get("medium", 50000))),
                        "large": Decimal(str(thresholds.get("large", 250000))),
                        "loaded": Decimal("1"),  # Mark as loaded
                    }
                    logger.info(f"Tier thresholds loaded from config: {cls.THRESHOLDS}")
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                logger.error(f"Failed to load tier thresholds from config: {e}")
                raise

    @classmethod
    def get_thresholds(cls) -> dict[str, Decimal]:
        """Get thresholds, loading from config if needed."""
        cls._load_thresholds_from_config()
        return {k: v for k, v in cls.THRESHOLDS.items() if k != "loaded"}

    # Mapping from capital_flag (3-tier) to YAML (4-tier)
    # Since capital_flag doesn't have "micro", we map based on capital ranges
    CAPITAL_FLAG_TO_YAML: ClassVar[dict[str, str]] = {
        "small": "small",  # €0-€50k in capital_flag maps to small in YAML (€15k-€50k)
        # Note: This misses the micro tier (<€15k)
        "medium": "medium",  # €50k-€250k
        "large": "large",  # >=€250k
    }

    # Mapping from YAML (4-tier) to Spanish (3-tier)
    YAML_TO_SPANISH: ClassVar[dict[str, str]] = {
        "micro": "bajo",  # <€15k -> bajo
        "small": "bajo",  # €15k-€50k -> bajo
        "medium": "medio",  # €50k-€250k -> medio
        "large": "alto",  # >=€250k -> alto
    }

    # Mapping from Spanish (3-tier) to YAML (4-tier)
    # Use the more specific tier in the range
    SPANISH_TO_YAML: ClassVar[dict[str, str]] = {
        "bajo": "small",  # bajo -> small (medium tier in bajo range)
        "medio": "medium",  # medio -> medium
        "alto": "large",  # alto -> large
    }

    # Mapping from capital_flag (3-tier) to Spanish (3-tier)
    CAPITAL_FLAG_TO_SPANISH: ClassVar[dict[str, str]] = {
        "small": "bajo",
        "medium": "medio",
        "large": "alto",
    }

    # Reverse mapping for validation
    SPANISH_TO_CAPITAL_FLAG: ClassVar[dict[str, str]] = {
        "bajo": "small",
        "medio": "medium",
        "alto": "large",
    }

    # All valid tier names by system
    VALID_TIERS: ClassVar[dict[TierSystem, tuple[str, ...]]] = {
        TierSystem.CAPITAL_FLAG: ("small", "medium", "large"),
        TierSystem.YAML: ("micro", "small", "medium", "large"),
        TierSystem.SPANISH: ("bajo", "medio", "alto"),
        TierSystem.STANDARD: ("micro", "small", "medium", "large"),
    }

    @classmethod
    def get_tier_from_capital(cls, capital: Decimal) -> str:
        """
        Determine tier from capital amount using 4-tier system.

        This matches the investment_profiles.yaml tier structure:
        - micro: < €15k
        - small: €15k - €50k
        - medium: €50k - €250k
        - large: >= €250k

        Thresholds are loaded from config/capital_tiers.yaml if available.

        Args:
            capital: Capital amount in EUR

        Returns:
            Tier name: "micro", "small", "medium", or "large"

        Examples:
            >>> TierMapper.get_tier_from_capital(Decimal("10000"))
            'micro'
            >>> TierMapper.get_tier_from_capital(Decimal("30000"))
            'small'
            >>> TierMapper.get_tier_from_capital(Decimal("100000"))
            'medium'
            >>> TierMapper.get_tier_from_capital(Decimal("500000"))
            'large'
        """
        # Use centralized config (REQUIRED - no fallbacks)
        try:
            config = get_strategy_config()
            tier = config.get_tier_from_capital(capital)
            # Map institutional to large for backward compatibility with 4-tier system
            if tier == "institutional":
                return "large"
            return tier
        except OSError as e:
            logger.error(f"Could not determine tier from config: {e}")
            raise

        # Use hardcoded thresholds as last resort
        thresholds = cls.get_thresholds()
        if capital < thresholds["small"]:
            return "micro"
        elif capital < thresholds["medium"]:
            return "small"
        elif capital < thresholds["large"]:
            return "medium"
        else:
            return "large"

    @classmethod
    def get_capital_flag_tier(cls, capital: Decimal) -> str:
        """
        Determine tier using InputProfile.capital_flag logic (3-tier system).

        This matches the InputProfile.capital_flag property:
        - small: < €50k
        - medium: €50k - €250k
        - large: >= €250k

        Args:
            capital: Capital amount in EUR

        Returns:
            Tier name: "small", "medium", or "large"

        Examples:
            >>> TierMapper.get_capital_flag_tier(Decimal("30000"))
            'small'
            >>> TierMapper.get_capital_flag_tier(Decimal("100000"))
            'medium'
            >>> TierMapper.get_capital_flag_tier(Decimal("500000"))
            'large'
        """
        if capital < Decimal("50000"):
            return "small"
        elif capital < Decimal("250000"):
            return "medium"
        else:
            return "large"

    @classmethod
    def to_yaml_tier(cls, tier: str, source_system: TierSystem | None = None) -> str:
        """
        Convert tier to YAML format (micro, small, medium, large).

        Args:
            tier: Tier name in any supported system
            source_system: Optional source system (auto-detected if None)

        Returns:
            Tier name in YAML format

        Raises:
            ValueError: If tier is invalid or conversion not possible

        Examples:
            >>> TierMapper.to_yaml_tier("small")
            'small'
            >>> TierMapper.to_yaml_tier("bajo")
            'small'
            >>> TierMapper.to_yaml_tier("medium")
            'medium'
        """
        if source_system is None:
            source_system = cls.detect_system(tier)

        if source_system == TierSystem.YAML:
            return tier

        if source_system == TierSystem.CAPITAL_FLAG:
            return cls.CAPITAL_FLAG_TO_YAML.get(tier, tier)

        if source_system == TierSystem.SPANISH:
            return cls.SPANISH_TO_YAML.get(tier, tier)

        # If unknown, assume it's already in YAML format
        if tier in cls.VALID_TIERS[TierSystem.YAML]:
            return tier

        raise ValueError(f"Cannot convert tier '{tier}' from {source_system} to YAML format")

    @classmethod
    def to_spanish(cls, tier: str, source_system: TierSystem | None = None) -> str:
        """
        Convert tier to Spanish format (bajo, medio, alto).

        Args:
            tier: Tier name in any supported system
            source_system: Optional source system (auto-detected if None)

        Returns:
            Tier name in Spanish format

        Raises:
            ValueError: If tier is invalid or conversion not possible

        Examples:
            >>> TierMapper.to_spanish("micro")
            'bajo'
            >>> TierMapper.to_spanish("small")
            'bajo'
            >>> TierMapper.to_spanish("medium")
            'medio'
            >>> TierMapper.to_spanish("large")
            'alto'
        """
        if source_system is None:
            source_system = cls.detect_system(tier)

        if source_system == TierSystem.SPANISH:
            return tier

        # First convert to YAML format, then to Spanish
        yaml_tier = cls.to_yaml_tier(tier, source_system)
        return cls.YAML_TO_SPANISH.get(yaml_tier, tier)

    @classmethod
    def to_capital_flag(cls, tier: str, source_system: TierSystem | None = None) -> str:
        """
        Convert tier to capital_flag format (small, medium, large).

        Args:
            tier: Tier name in any supported system
            source_system: Optional source system (auto-detected if None)

        Returns:
            Tier name in capital_flag format

        Raises:
            ValueError: If tier is invalid or conversion not possible

        Examples:
            >>> TierMapper.to_capital_flag("micro")
            'small'
            >>> TierMapper.to_capital_flag("small")
            'small'
            >>> TierMapper.to_capital_flag("medio")
            'medium'
        """
        if source_system is None:
            source_system = cls.detect_system(tier)

        if source_system == TierSystem.CAPITAL_FLAG:
            return tier

        if source_system == TierSystem.SPANISH:
            return cls.SPANISH_TO_CAPITAL_FLAG.get(tier, tier)

        # From YAML: need to handle micro -> small mapping
        if tier == "micro":
            return "small"
        return tier

    @classmethod
    def detect_system(cls, tier: str) -> TierSystem:
        """
        Detect which tier system a tier name belongs to.

        Args:
            tier: Tier name to detect

        Returns:
            Detected TierSystem

        Raises:
            ValueError: If tier is not recognized in any system

        Examples:
            >>> TierMapper.detect_system("bajo")
            <TierSystem.SPANISH: 'spanish'>
            >>> TierMapper.detect_system("micro")
            <TierSystem.YAML: 'yaml'>
            >>> TierMapper.detect_system("small")
            <TierSystem.CAPITAL_FLAG: 'capital_flag'>
        """
        for system, valid_tiers in cls.VALID_TIERS.items():
            if tier in valid_tiers:
                # Special case: "small", "medium", "large" are in both capital_flag and YAML
                # Prefer capital_flag for these
                if tier in ("small", "medium", "large"):
                    return TierSystem.CAPITAL_FLAG
                return system

        raise ValueError(
            f"Tier '{tier}' not recognized in any system. Valid tiers: {cls.list_all_valid_tiers()}"
        )

    @classmethod
    def is_valid_tier(cls, tier: str, system: TierSystem | None = None) -> bool:
        """
        Check if a tier name is valid.

        Args:
            tier: Tier name to validate
            system: Optional specific system to check against

        Returns:
            True if tier is valid

        Examples:
            >>> TierMapper.is_valid_tier("bajo")
            True
            >>> TierMapper.is_valid_tier("invalid")
            False
        """
        if system is None:
            # Check all systems
            return any(tier in tiers for tiers in cls.VALID_TIERS.values())
        return tier in cls.VALID_TIERS.get(system, ())

    @classmethod
    def list_all_valid_tiers(cls) -> dict[str, tuple[str, ...]]:
        """
        List all valid tier names by system.

        Returns:
            Dictionary mapping system names to valid tier tuples

        Examples:
            >>> TierMapper.list_all_valid_tiers()
            {
                'capital_flag': ('small', 'medium', 'large'),
                'yaml': ('micro', 'small', 'medium', 'large'),
                'spanish': ('bajo', 'medio', 'alto'),
            }
        """
        return {system.value: tiers for system, tiers in cls.VALID_TIERS.items()}

    @classmethod
    def validate_consistency(cls) -> tuple[bool, list[str]]:
        """
        Validate tier mapping consistency across all systems.

        Checks:
        - All mappings are bidirectional
        - No conflicting mappings
        - All tiers in one system can map to another

        Returns:
            Tuple of (is_valid, list_of_warnings)

        Examples:
            >>> is_valid, warnings = TierMapper.validate_consistency()
            >>> if not is_valid:
            ...     for warning in warnings:
            ...         print(warning)
        """
        warnings = []

        # Check bidirectional mappings
        for source, target in cls.CAPITAL_FLAG_TO_SPANISH.items():
            if cls.SPANISH_TO_CAPITAL_FLAG.get(target) != source:
                warnings.append(
                    f"Bidirectional mapping mismatch: {source} -> {target} "
                    f"but {target} -> {cls.SPANISH_TO_CAPITAL_FLAG.get(target)}"
                )

        # Check YAML to Spanish mappings
        for yaml_tier, spanish_tier in cls.YAML_TO_SPANISH.items():
            if (
                spanish_tier in cls.SPANISH_TO_YAML
                and cls.SPANISH_TO_YAML[spanish_tier] != yaml_tier
                and not (yaml_tier == "micro" and spanish_tier == "bajo")
            ):
                # This is expected for bajo -> small (not micro)
                warnings.append(
                    f"YAML-Spanish mapping inconsistency: "
                    f"{yaml_tier} -> {spanish_tier} but "
                    f"{spanish_tier} -> {cls.SPANISH_TO_YAML[spanish_tier]}"
                )

        # Validate capital thresholds are in order
        threshold_values = list(cls.THRESHOLDS.values())
        for i in range(len(threshold_values) - 1):
            if threshold_values[i] >= threshold_values[i + 1]:
                warnings.append(
                    f"Capital thresholds not in order: "
                    f"{threshold_values[i]} >= {threshold_values[i + 1]}"
                )

        is_valid = len(warnings) == 0
        return is_valid, warnings


# ============================================================================
# Convenience Functions
# ============================================================================


def get_tier(capital: Decimal, system: TierSystem = TierSystem.YAML) -> str:
    """
    Get tier from capital amount for a specific system.

    Args:
        capital: Capital amount in EUR
        system: Target tier system (default: YAML)

    Returns:
        Tier name in the requested system

    Examples:
        >>> get_tier(Decimal("30000"))
        'small'
        >>> get_tier(Decimal("30000"), TierSystem.SPANISH)
        'bajo'
    """
    yaml_tier = TierMapper.get_tier_from_capital(capital)

    if system == TierSystem.YAML:
        return yaml_tier
    elif system == TierSystem.SPANISH:
        return TierMapper.to_spanish(yaml_tier, TierSystem.YAML)
    elif system == TierSystem.CAPITAL_FLAG:
        return TierMapper.to_capital_flag(yaml_tier, TierSystem.YAML)
    else:
        return yaml_tier


def normalize_tier(tier: str, target_system: TierSystem = TierSystem.YAML) -> str:
    """
    Normalize a tier name to a specific system.

    Auto-detects the source system and converts to target system.

    Args:
        tier: Tier name in any supported system
        target_system: Target tier system (default: YAML)

    Returns:
        Normalized tier name

    Examples:
        >>> normalize_tier("bajo")
        'small'
        >>> normalize_tier("small", TierSystem.SPANISH)
        'bajo'
    """
    source_system = TierMapper.detect_system(tier)

    if target_system == TierSystem.YAML:
        return TierMapper.to_yaml_tier(tier, source_system)
    elif target_system == TierSystem.SPANISH:
        return TierMapper.to_spanish(tier, source_system)
    elif target_system == TierSystem.CAPITAL_FLAG:
        return TierMapper.to_capital_flag(tier, source_system)
    else:
        return tier


def map_profile_tier_to_config(capital_flag: str, target_format: str = "yaml") -> str:
    """
    Map from InputProfile.capital_flag to config tier format.

    This is the primary function to use when converting from
    InputProfile.capital_flag to config lookups.

    Args:
        capital_flag: Value from InputProfile.capital_flag property
        target_format: Target format ("yaml" or "spanish")

    Returns:
        Tier name in target format

    Examples:
        >>> map_profile_tier_to_config("small", "spanish")
        'bajo'
        >>> map_profile_tier_to_config("medium", "yaml")
        'medium'
        >>> map_profile_tier_to_config("large", "spanish")
        'alto'
    """
    if target_format == "spanish":
        return TierMapper.to_spanish(capital_flag, TierSystem.CAPITAL_FLAG)
    elif target_format == "yaml":
        return TierMapper.to_yaml_tier(capital_flag, TierSystem.CAPITAL_FLAG)
    else:
        logger.warning(f"Unknown target format '{target_format}', using capital_flag as-is")
        return capital_flag


def validate_tier_mapping() -> tuple[bool, list[str]]:
    """
    Validate tier mapping consistency and log warnings.

    This is a convenience wrapper around TierMapper.validate_consistency()
    that also logs the results.

    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    is_valid, warnings = TierMapper.validate_consistency()

    if not is_valid:
        logger.warning("Tier mapping consistency issues detected:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    else:
        logger.info("Tier mapping is consistent across all systems")

    return is_valid, warnings


# Run validation on module import
_is_valid, _warnings = validate_tier_mapping()
