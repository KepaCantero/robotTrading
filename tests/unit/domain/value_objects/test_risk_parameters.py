"""
Unit tests for RiskParameters value object.

Tests the immutable RiskParameters value object following DDD patterns.
"""
import pytest
from decimal import Decimal

from app.domain.value_objects.risk_parameters import RiskParameters


@pytest.mark.unit
class TestRiskParametersCreation:
    """Test RiskParameters value object creation and validation."""

    def test_create_risk_parameters_with_valid_attributes(self):
        """Test creating RiskParameters with valid attributes."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.03'),
            take_profit_pct=Decimal('0.06'),
            risk_reward_ratio=Decimal('2'),
            max_daily_loss_pct=Decimal('0.05'),
            max_drawdown_pct=Decimal('0.15'),
        )

        assert params.max_position_size == Decimal('0.10')
        assert params.max_portfolio_exposure == Decimal('1.5')
        assert params.stop_loss_pct == Decimal('0.03')
        assert params.take_profit_pct == Decimal('0.06')

    def test_create_with_negative_max_position_size_raises_error(self):
        """Test that negative max_position_size raises ValueError."""
        with pytest.raises(ValueError, match="Max position size must be positive"):
            RiskParameters(
                max_position_size=Decimal('-0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('0.03'),
                take_profit_pct=Decimal('0.06'),
            )

    def test_create_with_zero_max_position_size_raises_error(self):
        """Test that zero max_position_size raises ValueError."""
        with pytest.raises(ValueError, match="Max position size must be positive"):
            RiskParameters(
                max_position_size=Decimal('0'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('0.03'),
                take_profit_pct=Decimal('0.06'),
            )

    def test_create_with_negative_max_portfolio_exposure_raises_error(self):
        """Test that negative max_portfolio_exposure raises ValueError."""
        with pytest.raises(ValueError, match="Max portfolio exposure must be positive"):
            RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('-1.5'),
                stop_loss_pct=Decimal('0.03'),
                take_profit_pct=Decimal('0.06'),
            )

    def test_create_with_stop_loss_out_of_range_raises_error(self):
        """Test that stop_loss_pct outside 0-1 range raises ValueError."""
        with pytest.raises(ValueError, match="Stop loss must be between 0 and 1"):
            RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('-0.03'),
                take_profit_pct=Decimal('0.06'),
            )

        with pytest.raises(ValueError, match="Stop loss must be between 0 and 1"):
            RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('1.5'),
                take_profit_pct=Decimal('0.06'),
            )

    def test_create_with_zero_stop_loss_raises_error(self):
        """Test that zero stop_loss_pct raises ValueError."""
        with pytest.raises(ValueError, match="Stop loss must be between 0 and 1"):
            RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('0'),
                take_profit_pct=Decimal('0.06'),
            )

    def test_create_with_negative_take_profit_raises_error(self):
        """Test that negative take_profit_pct raises ValueError."""
        with pytest.raises(ValueError, match="Take profit must be positive"):
            RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('0.03'),
                take_profit_pct=Decimal('-0.06'),
            )

    def test_create_with_negative_risk_reward_ratio_raises_error(self):
        """Test that negative risk_reward_ratio raises ValueError."""
        with pytest.raises(ValueError, match="Risk/reward ratio must be positive"):
            RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('0.03'),
                take_profit_pct=Decimal('0.06'),
                risk_reward_ratio=Decimal('-2'),
            )

    def test_create_with_invalid_max_daily_loss_raises_error(self):
        """Test that max_daily_loss_pct outside 0-1 range raises ValueError."""
        with pytest.raises(ValueError, match="Max daily loss must be between 0 and 1"):
            RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('0.03'),
                take_profit_pct=Decimal('0.06'),
                max_daily_loss_pct=Decimal('-0.05'),
            )

        with pytest.raises(ValueError, match="Max daily loss must be between 0 and 1"):
            RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('0.03'),
                take_profit_pct=Decimal('0.06'),
                max_daily_loss_pct=Decimal('1.5'),
            )

    def test_create_with_invalid_max_drawdown_raises_error(self):
        """Test that max_drawdown_pct outside 0-1 range raises ValueError."""
        with pytest.raises(ValueError, match="Max drawdown must be between 0 and 1"):
            RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('0.03'),
                take_profit_pct=Decimal('0.06'),
                max_drawdown_pct=Decimal('-0.15'),
            )

        with pytest.raises(ValueError, match="Max drawdown must be between 0 and 1"):
            RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('0.03'),
                take_profit_pct=Decimal('0.06'),
                max_drawdown_pct=Decimal('1.5'),
            )


@pytest.mark.unit
class TestRiskParametersImmutability:
    """Test RiskParameters value object immutability."""

    def test_risk_parameters_is_frozen(self):
        """Test that RiskParameters dataclass is frozen (immutable)."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.03'),
            take_profit_pct=Decimal('0.06'),
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            params.max_position_size = Decimal('0.20')

    def test_risk_parameters_hash_is_consistent(self):
        """Test that RiskParameters hash is consistent for same values."""
        params1 = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.03'),
            take_profit_pct=Decimal('0.06'),
        )
        params2 = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.03'),
            take_profit_pct=Decimal('0.06'),
        )

        assert hash(params1) == hash(params2)


@pytest.mark.unit
class TestRiskParametersCalculation:
    """Test RiskParameters calculation methods."""

    def test_get_stop_loss_price_long(self):
        """Test stop loss price calculation for long position."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.05'),  # 5%
            take_profit_pct=Decimal('0.10'),
        )

        entry_price = Decimal('100')
        stop_price = params.get_stop_loss_price(entry_price, side='long')

        assert stop_price == Decimal('95')  # 100 * (1 - 0.05)

    def test_get_stop_loss_price_short(self):
        """Test stop loss price calculation for short position."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.05'),  # 5%
            take_profit_pct=Decimal('0.10'),
        )

        entry_price = Decimal('100')
        stop_price = params.get_stop_loss_price(entry_price, side='short')

        assert stop_price == Decimal('105')  # 100 * (1 + 0.05)

    def test_get_stop_loss_price_long_with_various_percentages(self):
        """Test stop loss calculation with various percentages."""
        test_cases = [
            (Decimal('0.02'), Decimal('98')),  # 2%
            (Decimal('0.05'), Decimal('95')),  # 5%
            (Decimal('0.10'), Decimal('90')),  # 10%
            (Decimal('0.15'), Decimal('85')),  # 15%
        ]

        entry_price = Decimal('100')

        for stop_loss_pct, expected in test_cases:
            params = RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=Decimal('0.10'),
            )

            result = params.get_stop_loss_price(entry_price, side='long')
            assert result == expected

    def test_get_take_profit_price_long(self):
        """Test take profit price calculation for long position."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.05'),
            take_profit_pct=Decimal('0.10'),  # 10%
        )

        entry_price = Decimal('100')
        target_price = params.get_take_profit_price(entry_price, side='long')

        assert target_price == Decimal('110')  # 100 * (1 + 0.10)

    def test_get_take_profit_price_short(self):
        """Test take profit price calculation for short position."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.05'),
            take_profit_pct=Decimal('0.10'),  # 10%
        )

        entry_price = Decimal('100')
        target_price = params.get_take_profit_price(entry_price, side='short')

        assert target_price == Decimal('90')  # 100 * (1 - 0.10)

    def test_get_take_profit_price_long_with_various_percentages(self):
        """Test take profit calculation with various percentages."""
        test_cases = [
            (Decimal('0.05'), Decimal('105')),  # 5%
            (Decimal('0.10'), Decimal('110')),  # 10%
            (Decimal('0.15'), Decimal('115')),  # 15%
            (Decimal('0.20'), Decimal('120')),  # 20%
        ]

        entry_price = Decimal('100')

        for take_profit_pct, expected in test_cases:
            params = RiskParameters(
                max_position_size=Decimal('0.10'),
                max_portfolio_exposure=Decimal('1.5'),
                stop_loss_pct=Decimal('0.05'),
                take_profit_pct=take_profit_pct,
            )

            result = params.get_take_profit_price(entry_price, side='long')
            assert result == expected


@pytest.mark.unit
class TestRiskRewardValidation:
    """Test risk/reward ratio validation."""

    def test_validate_risk_reward_long_meets_minimum(self):
        """Test risk/reward validation for long position meeting minimum."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.05'),
            take_profit_pct=Decimal('0.10'),
            risk_reward_ratio=Decimal('2'),
        )

        # Entry: 100, Target: 110, Stop: 95
        # Potential profit: 10, Potential loss: 5
        # Risk/reward: 10/5 = 2.0 (meets minimum)
        result = params.validate_risk_reward(
            entry_price=Decimal('100'),
            target_price=Decimal('110'),
            stop_price=Decimal('95'),
            side='long',
        )

        assert result is True

    def test_validate_risk_reward_long_below_minimum(self):
        """Test risk/reward validation for long position below minimum."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.05'),
            take_profit_pct=Decimal('0.10'),
            risk_reward_ratio=Decimal('3'),
        )

        # Entry: 100, Target: 110, Stop: 95
        # Potential profit: 10, Potential loss: 5
        # Risk/reward: 10/5 = 2.0 (below minimum of 3.0)
        result = params.validate_risk_reward(
            entry_price=Decimal('100'),
            target_price=Decimal('110'),
            stop_price=Decimal('95'),
            side='long',
        )

        assert result is False

    def test_validate_risk_reward_short_meets_minimum(self):
        """Test risk/reward validation for short position meeting minimum."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.05'),
            take_profit_pct=Decimal('0.10'),
            risk_reward_ratio=Decimal('2'),
        )

        # Entry: 100, Target: 90, Stop: 105
        # Potential profit: 10, Potential loss: 5
        # Risk/reward: 10/5 = 2.0 (meets minimum)
        result = params.validate_risk_reward(
            entry_price=Decimal('100'),
            target_price=Decimal('90'),
            stop_price=Decimal('105'),
            side='short',
        )

        assert result is True

    def test_validate_risk_reward_with_zero_loss_raises_error(self):
        """Test that zero potential loss returns False."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.05'),
            take_profit_pct=Decimal('0.10'),
            risk_reward_ratio=Decimal('2'),
        )

        # Entry and stop are the same (no loss protection)
        result = params.validate_risk_reward(
            entry_price=Decimal('100'),
            target_price=Decimal('110'),
            stop_price=Decimal('100'),
            side='long',
        )

        assert result is False

    def test_validate_risk_reward_various_scenarios(self):
        """Test risk/reward validation with various scenarios."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.05'),
            take_profit_pct=Decimal('0.10'),
            risk_reward_ratio=Decimal('2'),
        )

        test_cases = [
            # (entry, target, stop, side, expected)
            # For long: profit = target - entry, loss = entry - stop
            (
                Decimal('100'),
                Decimal('110'),
                Decimal('95'),
                'long',
                True,
            ),  # profit=10, loss=5, ratio=2:1
            (
                Decimal('100'),
                Decimal('120'),
                Decimal('95'),
                'long',
                True,
            ),  # profit=20, loss=5, ratio=4:1
            (
                Decimal('100'),
                Decimal('105'),
                Decimal('95'),
                'long',
                False,
            ),  # profit=5, loss=5, ratio=1:1 (<2:1)
            (
                Decimal('100'),
                Decimal('105'),
                Decimal('90'),
                'long',
                False,
            ),  # profit=5, loss=10, ratio=0.5:1 (<2:1)
            # For short: profit = entry - target, loss = stop - entry
            (
                Decimal('100'),
                Decimal('90'),
                Decimal('105'),
                'short',
                True,
            ),  # profit=10, loss=5, ratio=2:1
            (
                Decimal('100'),
                Decimal('80'),
                Decimal('105'),
                'short',
                True,
            ),  # profit=20, loss=5, ratio=4:1
        ]

        for entry, target, stop, side, expected in test_cases:
            result = params.validate_risk_reward(entry, target, stop, side)
            assert (
                result is expected
            ), f"Failed for entry={entry}, target={target}, stop={stop}, side={side}. Expected {expected}, got {result}"


@pytest.mark.unit
class TestRiskParametersForTier:
    """Test RiskParameters.for_tier factory method."""

    def test_for_tier_micro(self):
        """Test for_tier creates MICRO tier parameters."""
        params = RiskParameters.for_tier('micro')

        assert params.max_position_size == Decimal('0.20')  # 20%
        assert params.max_portfolio_exposure == Decimal('1.0')  # 100%
        assert params.stop_loss_pct == Decimal('0.05')  # 5%
        assert params.take_profit_pct == Decimal('0.10')  # 10%

    def test_for_tier_small(self):
        """Test for_tier creates SMALL tier parameters."""
        params = RiskParameters.for_tier('small')

        assert params.max_position_size == Decimal('0.15')  # 15%
        assert params.max_portfolio_exposure == Decimal('1.2')  # 120%
        assert params.stop_loss_pct == Decimal('0.04')  # 4%
        assert params.take_profit_pct == Decimal('0.08')  # 8%

    def test_for_tier_medium(self):
        """Test for_tier creates MEDIUM tier parameters."""
        params = RiskParameters.for_tier('medium')

        assert params.max_position_size == Decimal('0.10')  # 10%
        assert params.max_portfolio_exposure == Decimal('1.5')  # 150%
        assert params.stop_loss_pct == Decimal('0.03')  # 3%
        assert params.take_profit_pct == Decimal('0.06')  # 6%

    def test_for_tier_large(self):
        """Test for_tier creates LARGE tier parameters."""
        params = RiskParameters.for_tier('large')

        assert params.max_position_size == Decimal('0.08')  # 8%
        assert params.max_portfolio_exposure == Decimal('1.8')  # 180%
        assert params.stop_loss_pct == Decimal('0.025')  # 2.5%
        assert params.take_profit_pct == Decimal('0.05')  # 5%

    def test_for_tier_institutional(self):
        """Test for_tier creates INSTITUTIONAL tier parameters."""
        params = RiskParameters.for_tier('institutional')

        assert params.max_position_size == Decimal('0.05')  # 5%
        assert params.max_portfolio_exposure == Decimal('2.0')  # 200%
        assert params.stop_loss_pct == Decimal('0.02')  # 2%
        assert params.take_profit_pct == Decimal('0.04')  # 4%

    def test_for_tier_uses_default_risk_reward_ratio(self):
        """Test that for_tier uses default risk/reward ratio."""
        params = RiskParameters.for_tier('micro')

        assert params.risk_reward_ratio == Decimal('2')

    def test_for_tier_all_tiers_use_different_risk_profiles(self):
        """Test that different tiers have progressively tighter risk controls."""
        micro = RiskParameters.for_tier('micro')
        small = RiskParameters.for_tier('small')
        medium = RiskParameters.for_tier('medium')
        large = RiskParameters.for_tier('large')
        institutional = RiskParameters.for_tier('institutional')

        # Max position size should decrease with tier
        assert micro.max_position_size > small.max_position_size
        assert small.max_position_size > medium.max_position_size
        assert medium.max_position_size > large.max_position_size
        assert large.max_position_size > institutional.max_position_size

        # Stop loss should tighten with tier
        assert micro.stop_loss_pct > small.stop_loss_pct
        assert small.stop_loss_pct > medium.stop_loss_pct
        assert medium.stop_loss_pct > large.stop_loss_pct
        assert large.stop_loss_pct > institutional.stop_loss_pct


@pytest.mark.unit
class TestRiskParametersPropertyBased:
    """Property-based tests for RiskParameters operations."""

    @pytest.mark.parametrize(
        "entry_price,stop_pct,side",
        [
            (Decimal('100'), Decimal('0.01'), 'long'),
            (Decimal('100'), Decimal('0.05'), 'long'),
            (Decimal('100'), Decimal('0.10'), 'long'),
            (Decimal('50'), Decimal('0.03'), 'long'),
            (Decimal('200'), Decimal('0.07'), 'short'),
            (Decimal('150'), Decimal('0.04'), 'short'),
        ],
    )
    def test_stop_loss_calculation_properties(self, entry_price, stop_pct, side):
        """Test stop loss calculation properties with various inputs."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=stop_pct,
            take_profit_pct=Decimal('0.10'),
        )

        result = params.get_stop_loss_price(entry_price, side)

        if side == 'long':
            expected = entry_price * (1 - stop_pct)
        else:
            expected = entry_price * (1 + stop_pct)

        assert result == expected

    @pytest.mark.parametrize(
        "entry_price,target_pct,side",
        [
            (Decimal('100'), Decimal('0.05'), 'long'),
            (Decimal('100'), Decimal('0.10'), 'long'),
            (Decimal('100'), Decimal('0.20'), 'long'),
            (Decimal('50'), Decimal('0.15'), 'long'),
            (Decimal('200'), Decimal('0.08'), 'short'),
            (Decimal('150'), Decimal('0.12'), 'short'),
        ],
    )
    def test_take_profit_calculation_properties(self, entry_price, target_pct, side):
        """Test take profit calculation properties with various inputs."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.05'),
            take_profit_pct=target_pct,
        )

        result = params.get_take_profit_price(entry_price, side)

        if side == 'long':
            expected = entry_price * (1 + target_pct)
        else:
            expected = entry_price * (1 - target_pct)

        assert result == expected

    @pytest.mark.parametrize(
        "ratio,profit,loss,expected",
        [
            (Decimal('2'), Decimal('10'), Decimal('5'), True),  # 2:1 ratio
            (Decimal('2'), Decimal('20'), Decimal('10'), True),  # 2:1 ratio
            (Decimal('3'), Decimal('15'), Decimal('5'), True),  # 3:1 ratio
            (Decimal('2'), Decimal('5'), Decimal('5'), False),  # 1:1 ratio (below 2:1)
            (Decimal('3'), Decimal('10'), Decimal('5'), False),  # 2:1 ratio (below 3:1)
            (Decimal('1.5'), Decimal('10'), Decimal('10'), False),  # 1:1 ratio (below 1.5:1)
        ],
    )
    def test_risk_reward_validation_properties(self, ratio, profit, loss, expected):
        """Test risk/reward validation with various scenarios."""
        params = RiskParameters(
            max_position_size=Decimal('0.10'),
            max_portfolio_exposure=Decimal('1.5'),
            stop_loss_pct=Decimal('0.05'),
            take_profit_pct=Decimal('0.10'),
            risk_reward_ratio=ratio,
        )

        # Use entry=100, construct target and stop from profit/loss
        entry = Decimal('100')

        if profit >= loss:
            # For long: target > entry, stop < entry
            target = entry + profit
            stop = entry - loss
            side = 'long'
        else:
            # For short: target < entry, stop > entry
            target = entry - profit
            stop = entry + loss
            side = 'short'

        result = params.validate_risk_reward(entry, target, stop, side)

        assert result is expected
