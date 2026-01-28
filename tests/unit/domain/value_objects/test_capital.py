"""
Unit tests for Capital value object.

Tests the immutable Capital value object following DDD patterns.
"""
import pytest
from decimal import Decimal

from app.domain.value_objects.capital import Capital, CapitalTier


@pytest.mark.unit
class TestCapitalCreation:
    """Test Capital value object creation and validation."""

    def test_create_capital_with_valid_attributes(self):
        """Test creating Capital with valid attributes."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            currency='USD',
            max_leverage=Decimal('2'),
            max_positions=15
        )

        assert capital.amount == Decimal('100000')
        assert capital.tier == CapitalTier.MEDIUM
        assert capital.currency == 'USD'
        assert capital.max_leverage == Decimal('2')
        assert capital.max_positions == 15

    def test_create_capital_with_negative_amount_raises_error(self):
        """Test that negative amount raises ValueError."""
        with pytest.raises(ValueError, match="Capital amount must be positive"):
            Capital(
                amount=Decimal('-1000'),
                tier=CapitalTier.MICRO
            )

    def test_create_capital_with_zero_amount_raises_error(self):
        """Test that zero amount raises ValueError."""
        with pytest.raises(ValueError, match="Capital amount must be positive"):
            Capital(
                amount=Decimal('0'),
                tier=CapitalTier.MICRO
            )

    def test_create_capital_with_negative_leverage_raises_error(self):
        """Test that negative leverage raises ValueError."""
        with pytest.raises(ValueError, match="Max leverage must be positive"):
            Capital(
                amount=Decimal('10000'),
                tier=CapitalTier.SMALL,
                max_leverage=Decimal('-1')
            )

    def test_create_capital_with_zero_leverage_raises_error(self):
        """Test that zero leverage raises ValueError."""
        with pytest.raises(ValueError, match="Max leverage must be positive"):
            Capital(
                amount=Decimal('10000'),
                tier=CapitalTier.SMALL,
                max_leverage=Decimal('0')
            )

    def test_create_capital_with_negative_max_positions_raises_error(self):
        """Test that negative max_positions raises ValueError."""
        with pytest.raises(ValueError, match="Max positions must be positive"):
            Capital(
                amount=Decimal('10000'),
                tier=CapitalTier.SMALL,
                max_positions=-5
            )

    def test_create_capital_with_zero_max_positions_raises_error(self):
        """Test that zero max_positions raises ValueError."""
        with pytest.raises(ValueError, match="Max positions must be positive"):
            Capital(
                amount=Decimal('10000'),
                tier=CapitalTier.SMALL,
                max_positions=0
            )


@pytest.mark.unit
class TestCapitalImmutability:
    """Test Capital value object immutability."""

    def test_capital_is_frozen(self):
        """Test that Capital dataclass is frozen (immutable)."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            capital.amount = Decimal('200000')

    def test_capital_hash_is_consistent(self):
        """Test that Capital hash is consistent for same values."""
        capital1 = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            currency='USD'
        )
        capital2 = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            currency='USD'
        )

        assert hash(capital1) == hash(capital2)


@pytest.mark.unit
class TestCapitalMethods:
    """Test Capital value object methods."""

    def test_get_tier(self):
        """Test get_tier method."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.LARGE
        )

        assert capital.get_tier() == CapitalTier.LARGE

    def test_get_amount_returns_money(self):
        """Test get_amount returns Money value object."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            currency='USD'
        )

        money = capital.get_amount()

        assert money.amount == Decimal('100000')
        assert money.currency == 'USD'

    def test_get_max_exposure_without_leverage(self):
        """Test get_max_exposure without leverage."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            max_leverage=Decimal('1')
        )

        max_exposure = capital.get_max_exposure()

        assert max_exposure == Decimal('100000')

    def test_get_max_exposure_with_leverage(self):
        """Test get_max_exposure with leverage."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            max_leverage=Decimal('2')
        )

        max_exposure = capital.get_max_exposure()

        assert max_exposure == Decimal('200000')

    def test_get_max_exposure_with_fractional_leverage(self):
        """Test get_max_exposure with fractional leverage."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.SMALL,
            max_leverage=Decimal('1.5')
        )

        max_exposure = capital.get_max_exposure()

        assert max_exposure == Decimal('150000')

    def test_can_add_position_when_under_limit(self):
        """Test can_add_position returns True when under limit."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            max_positions=10
        )

        assert capital.can_add_position(current_positions=5) is True
        assert capital.can_add_position(current_positions=9) is True

    def test_can_add_position_when_at_limit(self):
        """Test can_add_position returns False when at limit."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            max_positions=10
        )

        assert capital.can_add_position(current_positions=10) is False

    def test_can_add_position_when_over_limit(self):
        """Test can_add_position returns False when over limit."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            max_positions=10
        )

        assert capital.can_add_position(current_positions=15) is False

    def test_is_strategy_enabled_when_strategy_in_list(self):
        """Test is_strategy_enabled returns True when strategy is enabled."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            enabled_strategies=['momentum', 'mean_reversion', 'pairs']
        )

        assert capital.is_strategy_enabled('momentum') is True
        assert capital.is_strategy_enabled('pairs') is True

    def test_is_strategy_enabled_when_strategy_not_in_list(self):
        """Test is_strategy_enabled returns False when strategy is not enabled."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            enabled_strategies=['momentum', 'mean_reversion']
        )

        assert capital.is_strategy_enabled('arbitrage') is False

    def test_is_strategy_enabled_with_empty_list(self):
        """Test is_strategy_enabled returns False with empty strategy list."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            enabled_strategies=[]
        )

        assert capital.is_strategy_enabled('momentum') is False


@pytest.mark.unit
class TestCapitalFromAmount:
    """Test Capital.from_amount factory method."""

    def test_from_amount_micro_tier(self):
        """Test from_amount creates MICRO tier for small amounts."""
        capital = Capital.from_amount(Decimal('10000'))

        assert capital.amount == Decimal('10000')
        assert capital.tier == CapitalTier.MICRO
        assert capital.max_positions == 5
        assert capital.max_leverage == Decimal('1')

    def test_from_amount_small_tier(self):
        """Test from_amount creates SMALL tier."""
        capital = Capital.from_amount(Decimal('25000'))

        assert capital.amount == Decimal('25000')
        assert capital.tier == CapitalTier.SMALL
        assert capital.max_positions == 8
        assert capital.max_leverage == Decimal('1.5')

    def test_from_amount_medium_tier(self):
        """Test from_amount creates MEDIUM tier."""
        capital = Capital.from_amount(Decimal('100000'))

        assert capital.amount == Decimal('100000')
        assert capital.tier == CapitalTier.MEDIUM
        assert capital.max_positions == 15
        assert capital.max_leverage == Decimal('2')

    def test_from_amount_large_tier(self):
        """Test from_amount creates LARGE tier."""
        capital = Capital.from_amount(Decimal('500000'))

        assert capital.amount == Decimal('500000')
        assert capital.tier == CapitalTier.LARGE
        assert capital.max_positions == 20
        assert capital.max_leverage == Decimal('2.5')

    def test_from_amount_institutional_tier(self):
        """Test from_amount creates INSTITUTIONAL tier for large amounts."""
        capital = Capital.from_amount(Decimal('1500000'))

        assert capital.amount == Decimal('1500000')
        assert capital.tier == CapitalTier.INSTITUTIONAL
        assert capital.max_positions == 50
        assert capital.max_leverage == Decimal('3')

    def test_from_amount_with_custom_currency(self):
        """Test from_amount with custom currency."""
        capital = Capital.from_amount(Decimal('100000'), currency='EUR')

        assert capital.currency == 'EUR'

    def test_from_amount_boundary_micro_to_small(self):
        """Test from_amount at MICRO to SMALL boundary."""
        # Just under boundary
        capital1 = Capital.from_amount(Decimal('14999'))
        assert capital1.tier == CapitalTier.MICRO

        # At boundary
        capital2 = Capital.from_amount(Decimal('15000'))
        assert capital2.tier == CapitalTier.SMALL

    def test_from_amount_boundary_small_to_medium(self):
        """Test from_amount at SMALL to MEDIUM boundary."""
        # Just under boundary
        capital1 = Capital.from_amount(Decimal('49999'))
        assert capital1.tier == CapitalTier.SMALL

        # At boundary
        capital2 = Capital.from_amount(Decimal('50000'))
        assert capital2.tier == CapitalTier.MEDIUM

    def test_from_amount_boundary_medium_to_large(self):
        """Test from_amount at MEDIUM to LARGE boundary."""
        # Just under boundary
        capital1 = Capital.from_amount(Decimal('249999'))
        assert capital1.tier == CapitalTier.MEDIUM

        # At boundary
        capital2 = Capital.from_amount(Decimal('250000'))
        assert capital2.tier == CapitalTier.LARGE

    def test_from_amount_boundary_large_to_institutional(self):
        """Test from_amount at LARGE to INSTITUTIONAL boundary."""
        # Just under boundary
        capital1 = Capital.from_amount(Decimal('999999'))
        assert capital1.tier == CapitalTier.LARGE

        # At boundary
        capital2 = Capital.from_amount(Decimal('1000000'))
        assert capital2.tier == CapitalTier.INSTITUTIONAL


@pytest.mark.unit
class TestCapitalTierEnum:
    """Test CapitalTier enumeration."""

    def test_tier_values(self):
        """Test that all tier enum values are correct."""
        assert CapitalTier.MICRO.value == "micro"
        assert CapitalTier.SMALL.value == "small"
        assert CapitalTier.MEDIUM.value == "medium"
        assert CapitalTier.LARGE.value == "large"
        assert CapitalTier.INSTITUTIONAL.value == "institutional"

    def test_tier_comparison(self):
        """Test tier enum comparison."""
        tier1 = CapitalTier.MEDIUM
        tier2 = CapitalTier.MEDIUM

        assert tier1 == tier2
        assert tier1 != CapitalTier.LARGE


@pytest.mark.unit
class TestCapitalPropertyBased:
    """Property-based tests for Capital operations."""

    @pytest.mark.parametrize("amount,leverage,expected", [
        (Decimal('100000'), Decimal('1'), Decimal('100000')),
        (Decimal('100000'), Decimal('2'), Decimal('200000')),
        (Decimal('100000'), Decimal('1.5'), Decimal('150000')),
        (Decimal('50000'), Decimal('3'), Decimal('150000')),
        (Decimal('1000000'), Decimal('2.5'), Decimal('2500000')),
    ])
    def test_max_exposure_calculation(self, amount, leverage, expected):
        """Test max exposure calculation with various inputs."""
        capital = Capital(
            amount=amount,
            tier=CapitalTier.MEDIUM,
            max_leverage=leverage
        )

        result = capital.get_max_exposure()

        assert result == expected

    @pytest.mark.parametrize("max_positions,current_positions,expected", [
        (5, 0, True),
        (5, 4, True),
        (5, 5, False),
        (5, 6, False),
        (10, 9, True),
        (10, 10, False),
        (10, 15, False),
    ])
    def test_can_add_position_various_scenarios(self, max_positions, current_positions, expected):
        """Test can_add_position with various scenarios."""
        capital = Capital(
            amount=Decimal('100000'),
            tier=CapitalTier.MEDIUM,
            max_positions=max_positions
        )

        result = capital.can_add_position(current_positions)

        assert result is expected

    @pytest.mark.parametrize("amount,expected_tier", [
        (Decimal('1000'), CapitalTier.MICRO),
        (Decimal('10000'), CapitalTier.MICRO),
        (Decimal('14999'), CapitalTier.MICRO),
        (Decimal('15000'), CapitalTier.SMALL),
        (Decimal('30000'), CapitalTier.SMALL),
        (Decimal('49999'), CapitalTier.SMALL),
        (Decimal('50000'), CapitalTier.MEDIUM),
        (Decimal('100000'), CapitalTier.MEDIUM),
        (Decimal('249999'), CapitalTier.MEDIUM),
        (Decimal('250000'), CapitalTier.LARGE),
        (Decimal('500000'), CapitalTier.LARGE),
        (Decimal('999999'), CapitalTier.LARGE),
        (Decimal('1000000'), CapitalTier.INSTITUTIONAL),
        (Decimal('5000000'), CapitalTier.INSTITUTIONAL),
    ])
    def test_from_amount_tier_classification(self, amount, expected_tier):
        """Test tier classification for various amounts."""
        capital = Capital.from_amount(amount)

        assert capital.tier == expected_tier
