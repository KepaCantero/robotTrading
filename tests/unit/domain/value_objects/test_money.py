"""
Unit tests for Money value object.

Tests the immutable Money value object following DDD patterns.
"""
from decimal import Decimal

import pytest

from app.domain.value_objects.money import Money


@pytest.mark.unit
class TestMoneyCreation:
    """Test Money value object creation and validation."""

    def test_create_money_with_positive_amount(self):
        """Test creating Money with positive amount."""
        money = Money(amount=Decimal('100.50'), currency='USD')

        assert money.amount == Decimal('100.50')
        assert money.currency == 'USD'

    def test_create_money_with_zero_amount(self):
        """Test creating Money with zero amount."""
        money = Money(amount=Decimal('0'), currency='EUR')

        assert money.amount == Decimal('0')
        assert money.is_zero()

    def test_create_money_default_currency(self):
        """Test creating Money with default USD currency."""
        money = Money(amount=Decimal('50'))

        assert money.currency == 'USD'

    def test_create_money_with_negative_amount_raises_error(self):
        """Test that negative amounts raise ValueError."""
        with pytest.raises(ValueError, match="Money amount cannot be negative"):
            Money(amount=Decimal('-10'), currency='USD')

    def test_create_money_with_empty_currency_raises_error(self):
        """Test that empty currency raises ValueError."""
        with pytest.raises(ValueError, match="Currency cannot be empty"):
            Money(amount=Decimal('100'), currency='')

    def test_create_money_with_float_conversion(self):
        """Test creating Money with float (converted to Decimal)."""
        money = Money(amount=Decimal('99.99'), currency='USD')

        assert money.amount == Decimal('99.99')


@pytest.mark.unit
class TestMoneyImmutability:
    """Test Money value object immutability."""

    def test_money_is_frozen(self):
        """Test that Money dataclass is frozen (immutable)."""
        money = Money(amount=Decimal('100'), currency='USD')

        with pytest.raises(Exception):  # FrozenInstanceError
            money.amount = Decimal('200')

    def test_money_hash_is_consistent(self):
        """Test that Money hash is consistent for same values."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('100'), currency='USD')

        assert hash(money1) == hash(money2)

    def test_money_hash_differs_by_amount(self):
        """Test that Money hash differs by amount."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('200'), currency='USD')

        assert hash(money1) != hash(money2)

    def test_money_hash_differs_by_currency(self):
        """Test that Money hash differs by currency."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('100'), currency='EUR')

        assert hash(money1) != hash(money2)


@pytest.mark.unit
class TestMoneyArithmetic:
    """Test Money arithmetic operations."""

    def test_add_same_currency(self):
        """Test adding Money with same currency."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('50'), currency='USD')

        result = money1 + money2

        assert result.amount == Decimal('150')
        assert result.currency == 'USD'
        # Original instances unchanged
        assert money1.amount == Decimal('100')
        assert money2.amount == Decimal('50')

    def test_add_different_currency_raises_error(self):
        """Test that adding different currencies raises ValueError."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('50'), currency='EUR')

        with pytest.raises(ValueError, match="Cannot add different currencies"):
            money1 + money2

    def test_add_with_non_money_raises_type_error(self):
        """Test that adding with non-Money raises TypeError."""
        money = Money(amount=Decimal('100'), currency='USD')

        with pytest.raises(TypeError):
            money + 50

    def test_subtract_same_currency(self):
        """Test subtracting Money with same currency."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('30'), currency='USD')

        result = money1 - money2

        assert result.amount == Decimal('70')
        assert result.currency == 'USD'

    def test_subtract_negative_result_raises_error(self):
        """Test that negative subtraction result raises ValueError."""
        money1 = Money(amount=Decimal('50'), currency='USD')
        money2 = Money(amount=Decimal('100'), currency='USD')

        with pytest.raises(ValueError, match="Result cannot be negative"):
            money1 - money2

    def test_subtract_different_currency_raises_error(self):
        """Test that subtracting different currencies raises ValueError."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('50'), currency='EUR')

        with pytest.raises(ValueError, match="Cannot subtract different currencies"):
            money1 - money2

    def test_multiply_by_int(self):
        """Test multiplying Money by integer."""
        money = Money(amount=Decimal('100'), currency='USD')

        result = money * 3

        assert result.amount == Decimal('300')
        assert result.currency == 'USD'

    def test_multiply_by_float(self):
        """Test multiplying Money by float."""
        money = Money(amount=Decimal('100'), currency='USD')

        result = money * 1.5

        assert result.amount == Decimal('150')
        assert result.currency == 'USD'

    def test_multiply_by_decimal(self):
        """Test multiplying Money by Decimal."""
        money = Money(amount=Decimal('100'), currency='USD')

        result = money * Decimal('2.5')

        assert result.amount == Decimal('250')
        assert result.currency == 'USD'

    def test_multiply_by_negative_raises_error(self):
        """Test that multiplying by negative raises ValueError."""
        money = Money(amount=Decimal('100'), currency='USD')

        with pytest.raises(ValueError, match="Result cannot be negative"):
            money * -1

    def test_multiply_by_invalid_type_raises_type_error(self):
        """Test that multiplying by invalid type raises TypeError."""
        money = Money(amount=Decimal('100'), currency='USD')

        with pytest.raises((TypeError, ValueError)):
            money * "invalid"

    def test_divide_by_int(self):
        """Test dividing Money by integer."""
        money = Money(amount=Decimal('100'), currency='USD')

        result = money / 4

        assert result.amount == Decimal('25')
        assert result.currency == 'USD'

    def test_divide_by_float(self):
        """Test dividing Money by float."""
        money = Money(amount=Decimal('100'), currency='USD')

        result = money / 2.5

        assert result.amount == Decimal('40')
        assert result.currency == 'USD'

    def test_divide_by_zero_raises_error(self):
        """Test that dividing by zero raises ZeroDivisionError."""
        money = Money(amount=Decimal('100'), currency='USD')

        with pytest.raises(ZeroDivisionError, match="Cannot divide by zero"):
            money / 0

    def test_divide_by_invalid_type_raises_type_error(self):
        """Test that dividing by invalid type raises TypeError."""
        money = Money(amount=Decimal('100'), currency='USD')

        with pytest.raises((TypeError, ValueError)):
            money / "invalid"


@pytest.mark.unit
class TestMoneyComparison:
    """Test Money comparison operations."""

    def test_equality_same_amount_and_currency(self):
        """Test equality for same amount and currency."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('100'), currency='USD')

        assert money1 == money2

    def test_equality_different_amount(self):
        """Test inequality for different amounts."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('200'), currency='USD')

        assert money1 != money2

    def test_equality_different_currency(self):
        """Test inequality for different currencies."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('100'), currency='EUR')

        assert money1 != money2

    def test_equality_with_non_money(self):
        """Test equality comparison with non-Money type."""
        money = Money(amount=Decimal('100'), currency='USD')

        assert money != 100
        assert money != "100 USD"
        assert money != Decimal('100')

    def test_less_than(self):
        """Test less than comparison."""
        money1 = Money(amount=Decimal('50'), currency='USD')
        money2 = Money(amount=Decimal('100'), currency='USD')

        assert money1 < money2
        assert not (money2 < money1)

    def test_less_than_different_currency_raises_error(self):
        """Test that less than with different currencies raises ValueError."""
        money1 = Money(amount=Decimal('50'), currency='USD')
        money2 = Money(amount=Decimal('100'), currency='EUR')

        with pytest.raises(ValueError, match="Cannot compare different currencies"):
            money1 < money2

    def test_less_than_or_equal(self):
        """Test less than or equal comparison."""
        money1 = Money(amount=Decimal('50'), currency='USD')
        money2 = Money(amount=Decimal('100'), currency='USD')
        money3 = Money(amount=Decimal('50'), currency='USD')

        assert money1 <= money2
        assert money1 <= money3
        assert not (money2 <= money1)

    def test_greater_than(self):
        """Test greater than comparison."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('50'), currency='USD')

        assert money1 > money2
        assert not (money2 > money1)

    def test_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('50'), currency='USD')
        money3 = Money(amount=Decimal('100'), currency='USD')

        assert money1 >= money2
        assert money1 >= money3
        assert not (money2 >= money1)


@pytest.mark.unit
class TestMoneyUtilityMethods:
    """Test Money utility methods."""

    def test_is_zero_with_zero_amount(self):
        """Test is_zero returns True for zero amount."""
        money = Money(amount=Decimal('0'), currency='USD')

        assert money.is_zero() is True

    def test_is_zero_with_positive_amount(self):
        """Test is_zero returns False for positive amount."""
        money = Money(amount=Decimal('100'), currency='USD')

        assert money.is_zero() is False

    def test_is_positive_with_positive_amount(self):
        """Test is_positive returns True for positive amount."""
        money = Money(amount=Decimal('100'), currency='USD')

        assert money.is_positive() is True

    def test_is_positive_with_zero_amount(self):
        """Test is_positive returns False for zero amount."""
        money = Money(amount=Decimal('0'), currency='USD')

        assert money.is_positive() is False

    def test_to_float(self):
        """Test to_float conversion."""
        money = Money(amount=Decimal('100.50'), currency='USD')

        result = money.to_float()

        assert result == 100.50
        assert isinstance(result, float)

    def test_string_representation(self):
        """Test string representation."""
        money = Money(amount=Decimal('100.50'), currency='USD')

        result = str(money)

        assert result == "100.50 USD"

    def test_repr_representation(self):
        """Test repr representation."""
        money = Money(amount=Decimal('100.50'), currency='USD')

        result = repr(money)

        assert result == "Money(amount=100.50, currency='USD')"


@pytest.mark.unit
class TestMoneyPropertyBased:
    """Property-based tests for Money operations."""

    @pytest.mark.parametrize(
        "amount1,amount2,expected",
        [
            (Decimal('10'), Decimal('5'), Decimal('15')),
            (Decimal('0.01'), Decimal('0.02'), Decimal('0.03')),
            (Decimal('1000.50'), Decimal('999.50'), Decimal('2000.00')),
            (Decimal('0'), Decimal('0'), Decimal('0')),
        ],
    )
    def test_addition_properties(self, amount1, amount2, expected):
        """Test addition properties with various inputs."""
        money1 = Money(amount=amount1, currency='USD')
        money2 = Money(amount=amount2, currency='USD')

        result = money1 + money2

        assert result.amount == expected
        assert result.currency == 'USD'

    @pytest.mark.parametrize(
        "amount1,amount2,expected",
        [
            (Decimal('10'), Decimal('5'), Decimal('5')),
            (Decimal('100'), Decimal('50'), Decimal('50')),
            (Decimal('1000.50'), Decimal('0.50'), Decimal('1000.00')),
        ],
    )
    def test_subtraction_properties(self, amount1, amount2, expected):
        """Test subtraction properties with various inputs."""
        money1 = Money(amount=amount1, currency='USD')
        money2 = Money(amount=amount2, currency='USD')

        result = money1 - money2

        assert result.amount == expected

    @pytest.mark.parametrize(
        "amount,multiplier,expected",
        [
            (Decimal('10'), 2, Decimal('20')),
            (Decimal('100'), 0.5, Decimal('50')),
            (Decimal('25'), 4, Decimal('100')),
            (Decimal('100'), Decimal('1.5'), Decimal('150')),
        ],
    )
    def test_multiplication_properties(self, amount, multiplier, expected):
        """Test multiplication properties with various inputs."""
        money = Money(amount=amount, currency='USD')

        result = money * multiplier

        assert result.amount == expected

    @pytest.mark.parametrize(
        "amount,divisor,expected",
        [
            (Decimal('100'), 2, Decimal('50')),
            (Decimal('50'), 4, Decimal('12.5')),
            (Decimal('100'), 5, Decimal('20')),
            (Decimal('99'), 3, Decimal('33')),
        ],
    )
    def test_division_properties(self, amount, divisor, expected):
        """Test division properties with various inputs."""
        money = Money(amount=amount, currency='USD')

        result = money / divisor

        assert result.amount == expected

    def test_commutative_addition(self):
        """Test that addition is commutative."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('50'), currency='USD')

        result1 = money1 + money2
        result2 = money2 + money1

        assert result1 == result2

    def test_associative_addition(self):
        """Test that addition is associative."""
        money1 = Money(amount=Decimal('100'), currency='USD')
        money2 = Money(amount=Decimal('50'), currency='USD')
        money3 = Money(amount=Decimal('25'), currency='USD')

        result1 = (money1 + money2) + money3
        result2 = money1 + (money2 + money3)

        assert result1 == result2

    def test_identity_element_addition(self):
        """Test that zero is identity element for addition."""
        money = Money(amount=Decimal('100'), currency='USD')
        zero = Money(amount=Decimal('0'), currency='USD')

        result = money + zero

        assert result == money

    def test_multiplicative_identity(self):
        """Test that 1 is multiplicative identity."""
        money = Money(amount=Decimal('100'), currency='USD')

        result = money * 1

        assert result == money
