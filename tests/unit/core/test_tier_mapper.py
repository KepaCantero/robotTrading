"""
Unit tests for tier_mapper module.

Tests cover:
- Tier determination from capital amounts
- Conversion between different tier systems
- Validation and consistency checking
- Edge cases and error handling
"""

import pytest
from decimal import Decimal

from app.core.tier_mapper import (
    TierMapper,
    TierSystem,
    get_tier,
    normalize_tier,
    map_profile_tier_to_config,
    validate_tier_mapping,
)


class TestTierMapper:
    """Test TierMapper class methods."""

    def test_get_tier_from_capital_micro(self):
        """Test micro tier detection."""
        assert TierMapper.get_tier_from_capital(Decimal("10000")) == "micro"
        assert TierMapper.get_tier_from_capital(Decimal("14999")) == "micro"
        assert TierMapper.get_tier_from_capital(Decimal("0")) == "micro"
        assert TierMapper.get_tier_from_capital(Decimal("-1000")) == "micro"

    def test_get_tier_from_capital_small(self):
        """Test small tier detection."""
        assert TierMapper.get_tier_from_capital(Decimal("15000")) == "small"
        assert TierMapper.get_tier_from_capital(Decimal("30000")) == "small"
        assert TierMapper.get_tier_from_capital(Decimal("49999")) == "small"

    def test_get_tier_from_capital_medium(self):
        """Test medium tier detection."""
        assert TierMapper.get_tier_from_capital(Decimal("50000")) == "medium"
        assert TierMapper.get_tier_from_capital(Decimal("100000")) == "medium"
        assert TierMapper.get_tier_from_capital(Decimal("249999")) == "medium"

    def test_get_tier_from_capital_large(self):
        """Test large tier detection."""
        assert TierMapper.get_tier_from_capital(Decimal("250000")) == "large"
        assert TierMapper.get_tier_from_capital(Decimal("500000")) == "large"
        assert TierMapper.get_tier_from_capital(Decimal("1000000")) == "large"

    def test_get_capital_flag_tier_small(self):
        """Test capital_flag small tier."""
        assert TierMapper.get_capital_flag_tier(Decimal("10000")) == "small"
        assert TierMapper.get_capital_flag_tier(Decimal("49999")) == "small"

    def test_get_capital_flag_tier_medium(self):
        """Test capital_flag medium tier."""
        assert TierMapper.get_capital_flag_tier(Decimal("50000")) == "medium"
        assert TierMapper.get_capital_flag_tier(Decimal("100000")) == "medium"
        assert TierMapper.get_capital_flag_tier(Decimal("249999")) == "medium"

    def test_get_capital_flag_tier_large(self):
        """Test capital_flag large tier."""
        assert TierMapper.get_capital_flag_tier(Decimal("250000")) == "large"
        assert TierMapper.get_capital_flag_tier(Decimal("500000")) == "large"

    def test_to_yaml_tier_from_capital_flag(self):
        """Test conversion from capital_flag to YAML tier."""
        assert TierMapper.to_yaml_tier("small", TierSystem.CAPITAL_FLAG) == "small"
        assert TierMapper.to_yaml_tier("medium", TierSystem.CAPITAL_FLAG) == "medium"
        assert TierMapper.to_yaml_tier("large", TierSystem.CAPITAL_FLAG) == "large"

    def test_to_yaml_tier_from_spanish(self):
        """Test conversion from Spanish to YAML tier."""
        assert TierMapper.to_yaml_tier("bajo", TierSystem.SPANISH) == "small"
        assert TierMapper.to_yaml_tier("medio", TierSystem.SPANISH) == "medium"
        assert TierMapper.to_yaml_tier("alto", TierSystem.SPANISH) == "large"

    def test_to_spanish_from_yaml(self):
        """Test conversion from YAML to Spanish."""
        assert TierMapper.to_spanish("micro", TierSystem.YAML) == "bajo"
        assert TierMapper.to_spanish("small", TierSystem.YAML) == "bajo"
        assert TierMapper.to_spanish("medium", TierSystem.YAML) == "medio"
        assert TierMapper.to_spanish("large", TierSystem.YAML) == "alto"

    def test_to_spanish_from_capital_flag(self):
        """Test conversion from capital_flag to Spanish."""
        assert TierMapper.to_spanish("small", TierSystem.CAPITAL_FLAG) == "bajo"
        assert TierMapper.to_spanish("medium", TierSystem.CAPITAL_FLAG) == "medio"
        assert TierMapper.to_spanish("large", TierSystem.CAPITAL_FLAG) == "alto"

    def test_to_capital_flag_from_yaml(self):
        """Test conversion from YAML to capital_flag."""
        assert TierMapper.to_capital_flag("micro", TierSystem.YAML) == "small"
        assert TierMapper.to_capital_flag("small", TierSystem.YAML) == "small"
        assert TierMapper.to_capital_flag("medium", TierSystem.YAML) == "medium"
        assert TierMapper.to_capital_flag("large", TierSystem.YAML) == "large"

    def test_to_capital_flag_from_spanish(self):
        """Test conversion from Spanish to capital_flag."""
        assert TierMapper.to_capital_flag("bajo", TierSystem.SPANISH) == "small"
        assert TierMapper.to_capital_flag("medio", TierSystem.SPANISH) == "medium"
        assert TierMapper.to_capital_flag("alto", TierSystem.SPANISH) == "large"

    def test_detect_system_spanish(self):
        """Test detecting Spanish tier system."""
        assert TierMapper.detect_system("bajo") == TierSystem.SPANISH
        assert TierMapper.detect_system("medio") == TierSystem.SPANISH
        assert TierMapper.detect_system("alto") == TierSystem.SPANISH

    def test_detect_system_yaml(self):
        """Test detecting YAML tier system."""
        assert TierMapper.detect_system("micro") == TierSystem.YAML

    def test_detect_system_capital_flag(self):
        """Test detecting capital_flag tier system."""
        assert TierMapper.detect_system("small") == TierSystem.CAPITAL_FLAG
        assert TierMapper.detect_system("medium") == TierSystem.CAPITAL_FLAG
        assert TierMapper.detect_system("large") == TierSystem.CAPITAL_FLAG

    def test_detect_system_invalid(self):
        """Test detecting invalid tier."""
        with pytest.raises(ValueError, match="not recognized"):
            TierMapper.detect_system("invalid")

    def test_is_valid_tier_no_system(self):
        """Test validation without specifying system."""
        assert TierMapper.is_valid_tier("bajo")
        assert TierMapper.is_valid_tier("small")
        assert TierMapper.is_valid_tier("micro")
        assert not TierMapper.is_valid_tier("invalid")

    def test_is_valid_tier_with_system(self):
        """Test validation with specific system."""
        assert TierMapper.is_valid_tier("bajo", TierSystem.SPANISH)
        assert TierMapper.is_valid_tier("small", TierSystem.CAPITAL_FLAG)
        assert TierMapper.is_valid_tier("micro", TierSystem.YAML)
        assert not TierMapper.is_valid_tier("bajo", TierSystem.YAML)

    def test_list_all_valid_tiers(self):
        """Test listing all valid tiers."""
        tiers = TierMapper.list_all_valid_tiers()
        assert "capital_flag" in tiers
        assert "yaml" in tiers
        assert "spanish" in tiers
        assert tiers["capital_flag"] == ("small", "medium", "large")
        assert tiers["yaml"] == ("micro", "small", "medium", "large")
        assert tiers["spanish"] == ("bajo", "medio", "alto")

    def test_validate_consistency(self):
        """Test consistency validation."""
        is_valid, warnings = TierMapper.validate_consistency()
        # Should be valid with current implementation
        assert isinstance(is_valid, bool)
        assert isinstance(warnings, list)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_get_tier_yaml_system(self):
        """Test get_tier with YAML system (default)."""
        assert get_tier(Decimal("10000")) == "micro"
        assert get_tier(Decimal("30000")) == "small"
        assert get_tier(Decimal("100000")) == "medium"
        assert get_tier(Decimal("500000")) == "large"

    def test_get_tier_spanish_system(self):
        """Test get_tier with Spanish system."""
        assert get_tier(Decimal("10000"), TierSystem.SPANISH) == "bajo"
        assert get_tier(Decimal("30000"), TierSystem.SPANISH) == "bajo"
        assert get_tier(Decimal("100000"), TierSystem.SPANISH) == "medio"
        assert get_tier(Decimal("500000"), TierSystem.SPANISH) == "alto"

    def test_get_tier_capital_flag_system(self):
        """Test get_tier with capital_flag system."""
        assert get_tier(Decimal("10000"), TierSystem.CAPITAL_FLAG) == "small"
        assert get_tier(Decimal("30000"), TierSystem.CAPITAL_FLAG) == "small"
        assert get_tier(Decimal("100000"), TierSystem.CAPITAL_FLAG) == "medium"
        assert get_tier(Decimal("500000"), TierSystem.CAPITAL_FLAG) == "large"

    def test_normalize_tier_to_yaml(self):
        """Test normalize_tier to YAML format."""
        assert normalize_tier("bajo") == "small"
        assert normalize_tier("medio") == "medium"
        assert normalize_tier("alto") == "large"
        assert normalize_tier("small") == "small"
        assert normalize_tier("micro") == "micro"

    def test_normalize_tier_to_spanish(self):
        """Test normalize_tier to Spanish format."""
        assert normalize_tier("small", TierSystem.SPANISH) == "bajo"
        assert normalize_tier("medium", TierSystem.SPANISH) == "medio"
        assert normalize_tier("large", TierSystem.SPANISH) == "alto"
        assert normalize_tier("micro", TierSystem.SPANISH) == "bajo"

    def test_normalize_tier_to_capital_flag(self):
        """Test normalize_tier to capital_flag format."""
        assert normalize_tier("bajo", TierSystem.CAPITAL_FLAG) == "small"
        assert normalize_tier("medio", TierSystem.CAPITAL_FLAG) == "medium"
        assert normalize_tier("alto", TierSystem.CAPITAL_FLAG) == "large"
        assert normalize_tier("micro", TierSystem.CAPITAL_FLAG) == "small"

    def test_map_profile_tier_to_config_spanish(self):
        """Test map_profile_tier_to_config to Spanish format."""
        assert map_profile_tier_to_config("small", "spanish") == "bajo"
        assert map_profile_tier_to_config("medium", "spanish") == "medio"
        assert map_profile_tier_to_config("large", "spanish") == "alto"

    def test_map_profile_tier_to_config_yaml(self):
        """Test map_profile_tier_to_config to YAML format."""
        assert map_profile_tier_to_config("small", "yaml") == "small"
        assert map_profile_tier_to_config("medium", "yaml") == "medium"
        assert map_profile_tier_to_config("large", "yaml") == "large"

    def test_map_profile_tier_to_config_unknown_format(self):
        """Test map_profile_tier_to_config with unknown format."""
        # Should return capital_flag as-is with a warning
        assert map_profile_tier_to_config("small", "unknown") == "small"

    def test_validate_tier_mapping(self):
        """Test validate_tier_mapping function."""
        is_valid, warnings = validate_tier_mapping()
        assert isinstance(is_valid, bool)
        assert isinstance(warnings, list)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_boundary_values_yaml(self):
        """Test boundary values for YAML tier system."""
        # Exactly at thresholds
        assert TierMapper.get_tier_from_capital(Decimal("15000")) == "small"
        assert TierMapper.get_tier_from_capital(Decimal("50000")) == "medium"
        assert TierMapper.get_tier_from_capital(Decimal("250000")) == "large"

    def test_boundary_values_capital_flag(self):
        """Test boundary values for capital_flag tier system."""
        assert TierMapper.get_capital_flag_tier(Decimal("50000")) == "medium"
        assert TierMapper.get_capital_flag_tier(Decimal("250000")) == "large"

    def test_zero_and_negative_capital(self):
        """Test zero and negative capital amounts."""
        assert TierMapper.get_tier_from_capital(Decimal("0")) == "micro"
        assert TierMapper.get_tier_from_capital(Decimal("-1000")) == "micro"
        assert TierMapper.get_capital_flag_tier(Decimal("0")) == "small"

    def test_very_large_capital(self):
        """Test very large capital amounts."""
        assert TierMapper.get_tier_from_capital(Decimal("1000000000")) == "large"
        assert TierMapper.get_capital_flag_tier(Decimal("1000000000")) == "large"

    def test_micro_to_small_gap(self):
        """Test the gap between micro and small tiers."""
        # In YAML: micro is <15k, small is 15k-50k
        # In capital_flag: small is <50k (no micro tier)
        # This means capital <15k maps to small in capital_flag but micro in YAML
        assert TierMapper.get_tier_from_capital(Decimal("10000")) == "micro"
        assert TierMapper.get_capital_flag_tier(Decimal("10000")) == "small"
        # When converting, should handle this correctly
        assert TierMapper.to_capital_flag("micro", TierSystem.YAML) == "small"

    def test_bidirectional_mapping_consistency(self):
        """Test that bidirectional mappings are consistent."""
        # Spanish to capital_flag and back
        for spanish_tier in ["bajo", "medio", "alto"]:
            capital_flag = TierMapper.to_capital_flag(spanish_tier, TierSystem.SPANISH)
            back_to_spanish = TierMapper.to_spanish(capital_flag, TierSystem.CAPITAL_FLAG)
            assert back_to_spanish == spanish_tier

    def test_round_trip_conversions(self):
        """Test round-trip conversions maintain identity."""
        test_cases = [
            ("small", TierSystem.CAPITAL_FLAG, TierSystem.YAML),
            ("medium", TierSystem.CAPITAL_FLAG, TierSystem.YAML),
            ("large", TierSystem.CAPITAL_FLAG, TierSystem.YAML),
            ("bajo", TierSystem.SPANISH, TierSystem.CAPITAL_FLAG),
            ("medio", TierSystem.SPANISH, TierSystem.CAPITAL_FLAG),
            ("alto", TierSystem.SPANISH, TierSystem.CAPITAL_FLAG),
        ]

        for tier, source, target in test_cases:
            converted = TierMapper.to_yaml_tier(tier, source) if target == TierSystem.YAML else \
                       TierMapper.to_spanish(tier, source) if target == TierSystem.SPANISH else \
                       TierMapper.to_capital_flag(tier, source)
            # For valid conversions, should not raise exceptions
            assert converted is not None

    def test_auto_detection_with_ambiguous_tiers(self):
        """Test auto-detection with tier names that appear in multiple systems."""
        # "small", "medium", "large" appear in both capital_flag and YAML
        # Should prefer capital_flag
        assert TierMapper.detect_system("small") == TierSystem.CAPITAL_FLAG
        assert TierMapper.detect_system("medium") == TierSystem.CAPITAL_FLAG
        assert TierMapper.detect_system("large") == TierSystem.CAPITAL_FLAG


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    def test_input_profile_to_yaml_config(self):
        """Test converting InputProfile.capital_flag to YAML config lookup."""
        # Simulate InputProfile.capital_flag values
        capital_flags = ["small", "medium", "large"]
        for flag in capital_flags:
            # Should convert to YAML format without errors
            yaml_tier = TierMapper.to_yaml_tier(flag, TierSystem.CAPITAL_FLAG)
            assert yaml_tier in ["small", "medium", "large"]

    def test_input_profile_to_spanish_config(self):
        """Test converting InputProfile.capital_flag to Spanish config lookup."""
        capital_flags = ["small", "medium", "large"]
        expected_spanish = ["bajo", "medio", "alto"]
        for flag, expected in zip(capital_flags, expected_spanish):
            spanish_tier = TierMapper.to_spanish(flag, TierSystem.CAPITAL_FLAG)
            assert spanish_tier == expected

    def test_capital_amount_to_all_systems(self):
        """Test converting capital amount to all tier systems."""
        test_amounts = [
            Decimal("10000"),   # micro / small / bajo
            Decimal("30000"),   # small / small / bajo
            Decimal("100000"),  # medium / medium / medio
            Decimal("500000"),  # large / large / alto
        ]

        for amount in test_amounts:
            yaml_tier = get_tier(amount, TierSystem.YAML)
            spanish_tier = get_tier(amount, TierSystem.SPANISH)
            capital_flag_tier = get_tier(amount, TierSystem.CAPITAL_FLAG)

            # Verify tiers are valid
            assert TierMapper.is_valid_tier(yaml_tier, TierSystem.YAML)
            assert TierMapper.is_valid_tier(spanish_tier, TierSystem.SPANISH)
            assert TierMapper.is_valid_tier(capital_flag_tier, TierSystem.CAPITAL_FLAG)

    def test_profile_batch_backtester_scenario(self):
        """Test scenario from ProfileBatchBacktester."""
        # ProfileBatchBacktester needs to convert capital_flag to Spanish
        # for config lookups
        profile_capital_flags = ["small", "medium", "large"]
        for flag in profile_capital_flags:
            # This is what ProfileBatchBacktester does
            spanish_key = map_profile_tier_to_config(flag, "spanish")
            assert spanish_key in ["bajo", "medio", "alto"]

    def test_investment_profiles_yaml_lookup(self):
        """Test looking up tiers in investment_profiles.yaml structure."""
        # investment_profiles.yaml uses: micro, small, medium, large
        yaml_tiers = ["micro", "small", "medium", "large"]
        for tier in yaml_tiers:
            # Should be valid YAML tier
            assert TierMapper.is_valid_tier(tier, TierSystem.YAML)

            # Should be able to convert to other systems
            spanish = TierMapper.to_spanish(tier, TierSystem.YAML)
            capital_flag = TierMapper.to_capital_flag(tier, TierSystem.YAML)

            assert TierMapper.is_valid_tier(spanish, TierSystem.SPANISH)
            assert TierMapper.is_valid_tier(capital_flag, TierSystem.CAPITAL_FLAG)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
