"""
Unit tests for Order entity.

Tests the Order entity with comprehensive state machine following Tomasini's methodology.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.domain.entities.order import (
    Order,
    OrderEvent,
    OrderFill,
    OrderSide,
    OrderStatus,
    OrderType,
)


@pytest.mark.unit
class TestOrderCreation:
    """Test Order entity creation and validation."""

    def test_create_order_with_valid_attributes(self):
        """Test creating order with valid attributes."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        assert order.order_id == 'order_1'
        assert order.symbol == 'AAPL'
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == Decimal('100')
        assert order.status == OrderStatus.PENDING

    def test_create_order_with_limit_price(self):
        """Test creating limit order with price."""
        order = Order(
            order_id='order_2',
            symbol='MSFT',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal('50'),
            price=Decimal('150.00'),
        )

        assert order.price == Decimal('150.00')
        assert order.order_type == OrderType.LIMIT

    def test_create_order_with_stop_loss(self):
        """Test creating stop-loss order with stop price."""
        order = Order(
            order_id='order_3',
            symbol='TSLA',
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LOSS,
            quantity=Decimal('25'),
            stop_price=Decimal('200.00'),
        )

        assert order.stop_price == Decimal('200.00')
        assert order.order_type == OrderType.STOP_LOSS

    def test_create_order_with_empty_order_id_raises_error(self):
        """Test that empty order_id raises ValueError."""
        with pytest.raises(ValueError, match="Order ID cannot be empty"):
            Order(
                order_id='',
                symbol='AAPL',
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('100'),
            )

    def test_create_order_with_negative_quantity_raises_error(self):
        """Test that negative quantity raises ValueError."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            Order(
                order_id='order_1',
                symbol='AAPL',
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('-100'),
            )

    def test_create_order_with_zero_quantity_raises_error(self):
        """Test that zero quantity raises ValueError."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            Order(
                order_id='order_1',
                symbol='AAPL',
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('0'),
            )

    def test_create_order_with_negative_price_raises_error(self):
        """Test that negative price raises ValueError."""
        with pytest.raises(ValueError, match="Price must be positive"):
            Order(
                order_id='order_1',
                symbol='AAPL',
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal('100'),
                price=Decimal('-50'),
            )

    def test_create_order_with_negative_stop_price_raises_error(self):
        """Test that negative stop price raises ValueError."""
        with pytest.raises(ValueError, match="Stop price must be positive"):
            Order(
                order_id='order_1',
                symbol='AAPL',
                side=OrderSide.BUY,
                order_type=OrderType.STOP_LOSS,
                quantity=Decimal('100'),
                stop_price=Decimal('-50'),
            )

    def test_create_order_records_create_event(self):
        """Test that order creation records CREATE event."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        assert len(order.event_history) == 1
        assert order.event_history[0]['event'] == OrderEvent.CREATE.value
        assert order.event_history[0]['status'] == OrderStatus.PENDING.value


@pytest.mark.unit
class TestOrderValidation:
    """Test Order validation logic."""

    def test_validate_market_order_success(self):
        """Test validation of valid market order."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
            time_in_force='IOC',  # Immediate or Cancel doesn't require expiry
        )

        result = order.validate()

        assert result is True
        assert order.is_validated is True
        assert order.status == OrderStatus.VALIDATED

    def test_validate_limit_order_with_price_success(self):
        """Test validation of valid limit order."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal('100'),
            price=Decimal('150'),
            time_in_force='DAY',  # DAY orders don't require expiry
        )

        result = order.validate()

        assert result is True

    def test_validate_limit_order_without_price_fails(self):
        """Test validation fails for limit order without price."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal('100'),
        )

        result = order.validate()

        assert result is False
        assert "Limit orders must have a price" in order.validation_errors
        assert order.status == OrderStatus.REJECTED

    def test_validate_stop_loss_order_without_stop_price_fails(self):
        """Test validation fails for stop-loss order without stop price."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LOSS,
            quantity=Decimal('100'),
        )

        result = order.validate()

        assert result is False
        assert "orders must have a stop price" in order.validation_errors[0]

    def test_validate_with_invalid_time_in_force_fails(self):
        """Test validation fails with invalid time in force."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
            time_in_force='INVALID',
        )

        result = order.validate()

        assert result is False
        assert "Invalid time in force" in order.validation_errors[0]

    def test_validate_gtc_order_without_expiry_fails(self):
        """Test validation fails for GTC order without expiry."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal('100'),
            price=Decimal('150'),
            time_in_force='GTC',
        )

        result = order.validate()

        assert result is False
        assert "GTC orders must have an expiry time" in order.validation_errors[0]


@pytest.mark.unit
class TestOrderStateTransitions:
    """Test Order state machine transitions."""

    def test_submit_order_from_validated_state(self):
        """Test submitting order from VALIDATED state."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()

        order.submit()

        assert order.status == OrderStatus.SUBMITTED
        assert order.submitted_at is not None

    def test_submit_order_from_pending_state_raises_error(self):
        """Test that submitting from PENDING state raises ValueError."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        with pytest.raises(ValueError, match="Cannot submit order with status pending"):
            order.submit()

    def test_acknowledge_order_from_submitted_state(self):
        """Test acknowledging order from SUBMITTED state."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()

        order.acknowledge(broker_order_id='broker_123')

        assert order.status == OrderStatus.ACKNOWLEDGED
        assert order.broker_order_id == 'broker_123'

    def test_acknowledge_order_from_non_submitted_state_raises_error(self):
        """Test that acknowledging from non-SUBMITTED state raises ValueError."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        with pytest.raises(ValueError, match="Cannot acknowledge order with status pending"):
            order.acknowledge()


@pytest.mark.unit
class TestOrderFilling:
    """Test Order filling logic."""

    def test_fill_order_completely(self):
        """Test complete order fill."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()

        order.fill(fill_price=Decimal('150'))

        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == Decimal('100')
        assert order.avg_fill_price == Decimal('150')
        assert order.filled_at is not None
        assert len(order.fills) == 1

    def test_fill_order_partially(self):
        """Test partial order fill."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()

        order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('50'))

        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_quantity == Decimal('50')
        assert order.avg_fill_price == Decimal('150')
        assert len(order.fills) == 1

    def test_fill_order_multiple_partial_fills(self):
        """Test multiple partial fills leading to complete fill."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()

        # First partial fill
        order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('30'))
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_quantity == Decimal('30')

        # Second partial fill
        order.fill(fill_price=Decimal('151'), fill_quantity=Decimal('40'))
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_quantity == Decimal('70')

        # Final fill
        order.fill(fill_price=Decimal('152'), fill_quantity=Decimal('30'))
        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == Decimal('100')

        # Average price calculation: (30*150 + 40*151 + 30*152) / 100 = 150.7
        expected_avg = (30 * 150 + 40 * 151 + 30 * 152) / 100
        assert order.avg_fill_price == Decimal(str(expected_avg))

    def test_fill_order_with_negative_quantity_raises_error(self):
        """Test that filling with negative quantity raises ValueError."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()

        with pytest.raises(ValueError, match="Fill quantity must be positive"):
            order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('-10'))

    def test_fill_order_exceeding_quantity_raises_error(self):
        """Test that filling exceeding quantity raises ValueError."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()
        order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('50'))

        with pytest.raises(ValueError, match="Fill quantity exceeds order quantity"):
            order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('60'))

    def test_fill_order_from_invalid_state_raises_error(self):
        """Test that filling from invalid state raises ValueError."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        with pytest.raises(ValueError, match="Cannot fill order with status pending"):
            order.fill(fill_price=Decimal('150'))

    def test_fill_order_with_fee(self):
        """Test order fill with transaction fee."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()

        order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('100'), fee=Decimal('1.50'))

        assert len(order.fills) == 1
        assert order.fills[0].fee == Decimal('1.50')
        assert order.get_total_fees() == Decimal('1.50')


@pytest.mark.unit
class TestOrderCancellation:
    """Test Order cancellation logic."""

    def test_request_cancel_from_acknowledged_state(self):
        """Test requesting cancel from ACKNOWLEDGED state."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()

        order.request_cancel()

        assert order.status == OrderStatus.CANCEL_PENDING

    def test_confirm_cancel_from_cancel_pending_state(self):
        """Test confirming cancel from CANCEL_PENDING state."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()
        order.request_cancel()

        order.confirm_cancel()

        assert order.status == OrderStatus.CANCELLED
        assert order.cancelled_at is not None

    def test_request_cancel_from_filled_state_raises_error(self):
        """Test that cancelling filled order raises ValueError."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()
        order.fill(fill_price=Decimal('150'))

        with pytest.raises(ValueError, match="Cannot cancel order with status filled"):
            order.request_cancel()

    def test_confirm_cancel_from_non_pending_state_raises_error(self):
        """Test that confirming cancel from non-CANCEL_PENDING state raises ValueError."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        with pytest.raises(ValueError, match="Cannot confirm cancel for order with status pending"):
            order.confirm_cancel()


@pytest.mark.unit
class TestOrderRejection:
    """Test Order rejection logic."""

    def test_reject_order_with_reason(self):
        """Test rejecting order with reason."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        order.reject(reason="Insufficient capital")

        assert order.status == OrderStatus.REJECTED
        assert order.rejection_reason == "Insufficient capital"

    def test_reject_filled_order_raises_error(self):
        """Test that rejecting filled order raises ValueError."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()
        order.fill(fill_price=Decimal('150'))

        with pytest.raises(ValueError, match="Cannot reject order with status filled"):
            order.reject(reason="Test rejection")


@pytest.mark.unit
class TestOrderSuspension:
    """Test Order suspension logic."""

    def test_suspend_order_from_acknowledged_state(self):
        """Test suspending order from ACKNOWLEDGED state."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()

        order.suspend()

        assert order.status == OrderStatus.SUSPENDED

    def test_unsuspend_order_from_suspended_state(self):
        """Test unsuspending order from SUSPENDED state."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()
        order.suspend()

        order.unsuspend()

        assert order.status == OrderStatus.ACKNOWLEDGED

    def test_suspend_order_from_non_acknowledged_state_raises_error(self):
        """Test that suspending from non-ACKNOWLEDGED state raises ValueError."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        with pytest.raises(ValueError, match="Cannot suspend order with status pending"):
            order.suspend()


@pytest.mark.unit
class TestOrderExpiration:
    """Test Order expiration logic."""

    def test_expire_order_from_pending_state(self):
        """Test expiring order from PENDING state."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        order.expire()

        assert order.status == OrderStatus.EXPIRED

    def test_expire_order_from_suspended_state(self):
        """Test expiring order from SUSPENDED state."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()
        order.suspend()

        order.expire()

        assert order.status == OrderStatus.EXPIRED

    def test_expire_filled_order_raises_error(self):
        """Test that expiring filled order raises ValueError."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()
        order.fill(fill_price=Decimal('150'))

        with pytest.raises(ValueError, match="Cannot expire order with status filled"):
            order.expire()


@pytest.mark.unit
class TestOrderUtilityMethods:
    """Test Order utility methods."""

    def test_is_filled(self):
        """Test is_filled method."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()
        order.fill(fill_price=Decimal('150'))

        assert order.is_filled() is True

    def test_is_partially_filled(self):
        """Test is_partially_filled method."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()
        order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('50'))

        assert order.is_partially_filled() is True

    def test_is_pending(self):
        """Test is_pending method."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()

        assert order.is_pending() is True

        order.submit()
        assert order.is_pending() is True

        order.acknowledge()
        assert order.is_pending() is True

        order.fill(fill_price=Decimal('150'))
        assert order.is_pending() is False

    def test_is_terminal(self):
        """Test is_terminal method."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        # Non-terminal states
        assert order.is_terminal() is False
        order.validate()
        assert order.is_terminal() is False
        order.submit()
        assert order.is_terminal() is False
        order.acknowledge()
        assert order.is_terminal() is False

        # Terminal state: FILLED
        order.fill(fill_price=Decimal('150'))
        assert order.is_terminal() is True

    def test_is_active(self):
        """Test is_active method."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()

        assert order.is_active() is True

        order.fill(fill_price=Decimal('150'))
        assert order.is_active() is False

    def test_get_remaining_quantity(self):
        """Test get_remaining_quantity method."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()

        assert order.get_remaining_quantity() == Decimal('100')

        order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('30'))
        assert order.get_remaining_quantity() == Decimal('70')

        order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('70'))
        assert order.get_remaining_quantity() == Decimal('0')

    def test_get_fill_rate(self):
        """Test get_fill_rate method."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()

        assert order.get_fill_rate() == 0.0

        order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('50'))
        assert order.get_fill_rate() == 0.5

        order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('50'))
        assert order.get_fill_rate() == 1.0

    def test_get_total_fees(self):
        """Test get_total_fees method."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )
        order.validate()
        order.submit()
        order.acknowledge()

        order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('50'), fee=Decimal('0.50'))
        order.fill(fill_price=Decimal('150'), fill_quantity=Decimal('50'), fee=Decimal('0.50'))

        assert order.get_total_fees() == Decimal('1.00')

    def test_get_age_seconds(self):
        """Test get_age_seconds method."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        # Age should be very small (just created)
        age = order.get_age_seconds()
        assert age >= 0
        assert age < 1  # Less than 1 second

    def test_to_dict(self):
        """Test to_dict method."""
        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
        )

        result = order.to_dict()

        assert result['order_id'] == 'order_1'
        assert result['symbol'] == 'AAPL'
        assert result['side'] == 'buy'
        assert result['order_type'] == 'market'
        assert result['quantity'] == '100'
        assert result['status'] == 'pending'


@pytest.mark.unit
class TestOrderCallbacks:
    """Test Order callback functionality."""

    def test_on_fill_callback(self):
        """Test on_fill callback is triggered."""
        callback_mock = Mock()

        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
            on_fill=callback_mock,
        )
        order.validate()
        order.submit()
        order.acknowledge()

        order.fill(fill_price=Decimal('150'))

        callback_mock.assert_called_once()
        assert callback_mock.call_args[0][0].quantity == Decimal('100')

    def test_on_cancel_callback(self):
        """Test on_cancel callback is triggered."""
        callback_mock = Mock()

        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
            on_cancel=callback_mock,
        )
        order.validate()
        order.submit()
        order.acknowledge()
        order.request_cancel()

        order.confirm_cancel()

        callback_mock.assert_called_once()

    def test_on_reject_callback(self):
        """Test on_reject callback is triggered."""
        callback_mock = Mock()

        order = Order(
            order_id='order_1',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100'),
            on_reject=callback_mock,
        )

        order.reject(reason="Test rejection")

        callback_mock.assert_called_once_with("Test rejection")


@pytest.mark.unit
class TestOrderFillEntity:
    """Test OrderFill value object."""

    def test_create_order_fill(self):
        """Test creating OrderFill record."""
        fill = OrderFill(
            fill_id='fill_1',
            quantity=Decimal('100'),
            price=Decimal('150'),
            timestamp=datetime.utcnow(),
        )

        assert fill.fill_id == 'fill_1'
        assert fill.quantity == Decimal('100')
        assert fill.price == Decimal('150')
        assert fill.fee is None
        assert fill.liquidity is None

    def test_create_order_fill_with_fee_and_liquidity(self):
        """Test creating OrderFill with fee and liquidity."""
        fill = OrderFill(
            fill_id='fill_2',
            quantity=Decimal('50'),
            price=Decimal('151'),
            timestamp=datetime.utcnow(),
            fee=Decimal('0.75'),
            liquidity='maker',
        )

        assert fill.fee == Decimal('0.75')
        assert fill.liquidity == 'maker'


@pytest.mark.unit
class TestOrderEnums:
    """Test Order-related enumerations."""

    def test_order_side_enum(self):
        """Test OrderSide enum values."""
        assert OrderSide.BUY.value == 'buy'
        assert OrderSide.SELL.value == 'sell'

    def test_order_type_enum(self):
        """Test OrderType enum values."""
        assert OrderType.MARKET.value == 'market'
        assert OrderType.LIMIT.value == 'limit'
        assert OrderType.STOP_LOSS.value == 'stop_loss'
        assert OrderType.TAKE_PROFIT.value == 'take_profit'
        assert OrderType.STOP_LIMIT.value == 'stop_limit'

    def test_order_status_enum(self):
        """Test OrderStatus enum values."""
        assert OrderStatus.PENDING.value == 'pending'
        assert OrderStatus.VALIDATED.value == 'validated'
        assert OrderStatus.SUBMITTED.value == 'submitted'
        assert OrderStatus.ACKNOWLEDGED.value == 'acknowledged'
        assert OrderStatus.PARTIALLY_FILLED.value == 'partially_filled'
        assert OrderStatus.FILLED.value == 'filled'
        assert OrderStatus.CANCELLED.value == 'cancelled'
        assert OrderStatus.REJECTED.value == 'rejected'

    def test_order_event_enum(self):
        """Test OrderEvent enum values."""
        assert OrderEvent.CREATE.value == 'create'
        assert OrderEvent.VALIDATE.value == 'validate'
        assert OrderEvent.SUBMIT.value == 'submit'
        assert OrderEvent.ACKNOWLEDGE.value == 'acknowledge'
        assert OrderEvent.FILL.value == 'fill'
        assert OrderEvent.CANCEL_REQUEST.value == 'cancel_request'
        assert OrderEvent.CANCEL_CONFIRM.value == 'cancel_confirm'
        assert OrderEvent.REJECT.value == 'reject'
