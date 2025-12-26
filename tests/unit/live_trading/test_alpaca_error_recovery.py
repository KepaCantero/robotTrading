"""
Unit tests for Alpaca error handling and recovery mechanisms.

Tests:
- Error classification
- Circuit breaker pattern
- Retry logic with exponential backoff
- Position sync recovery
- Error recovery manager
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.services.live_trading.broker_adapters.alpaca_error_handler import (
    AlpacaErrorClassifier,
    CircuitBreaker,
    ErrorRecoveryManager,
    ErrorRecoveryStrategy,
    ErrorType,
    PositionSyncRecovery,
    RetryConfig,
)
from app.services.live_trading.broker_adapters.alpaca_adapter import AlpacaAdapter
from app.services.live_trading.broker_connector import BrokerPosition


class TestErrorClassification:
    """Test error classification."""

    def test_classify_network_error(self):
        """Test classification of network errors."""
        error = Exception("Connection timeout")
        error_type = AlpacaErrorClassifier.classify(error)
        assert error_type == ErrorType.NETWORK_ERROR

    def test_classify_rate_limit_error(self):
        """Test classification of rate limit errors."""
        error = Exception("429 Too Many Requests")
        error_type = AlpacaErrorClassifier.classify(error)
        assert error_type == ErrorType.RATE_LIMIT

    def test_classify_service_unavailable(self):
        """Test classification of service unavailable errors."""
        error = Exception("503 Service Unavailable")
        error_type = AlpacaErrorClassifier.classify(error)
        assert error_type == ErrorType.TEMPORARY_SERVICE_ERROR

    def test_classify_auth_failed(self):
        """Test classification of auth errors."""
        error = Exception("401 Unauthorized: Invalid API Key")
        error_type = AlpacaErrorClassifier.classify(error)
        assert error_type == ErrorType.AUTH_FAILED

    def test_classify_insufficient_funds(self):
        """Test classification of insufficient funds."""
        error = Exception("Insufficient buying power for order")
        error_type = AlpacaErrorClassifier.classify(error)
        assert error_type == ErrorType.INSUFFICIENT_FUNDS

    def test_classify_invalid_symbol(self):
        """Test classification of invalid symbol."""
        error = Exception("Invalid symbol: FAKE123")
        error_type = AlpacaErrorClassifier.classify(error)
        assert error_type == ErrorType.INVALID_SYMBOL

    def test_classify_unknown_error(self):
        """Test classification of unknown error."""
        error = Exception("Some random error")
        error_type = AlpacaErrorClassifier.classify(error)
        assert error_type == ErrorType.UNKNOWN

    def test_is_retryable_network_error(self):
        """Test that network errors are retryable."""
        error = Exception("Connection refused")
        assert AlpacaErrorClassifier.is_retryable(error) is True

    def test_is_not_retryable_insufficient_funds(self):
        """Test that insufficient funds is not retryable."""
        error = Exception("Insufficient buying power")
        assert AlpacaErrorClassifier.is_retryable(error) is False


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_circuit_breaker_initial_state(self):
        """Test that circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_tracks_failures(self):
        """Test that circuit breaker tracks failures."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.state == CircuitBreaker.CLOSED

        cb.record_failure()
        assert cb.failure_count == 2
        assert cb.state == CircuitBreaker.CLOSED

    def test_circuit_breaker_opens_on_threshold(self):
        """Test that circuit breaker opens when threshold reached."""
        cb = CircuitBreaker(failure_threshold=2)

        cb.record_failure()
        cb.record_failure()

        assert cb.state == CircuitBreaker.OPEN
        assert not cb.is_available()

    def test_circuit_breaker_allows_requests_when_closed(self):
        """Test that requests allowed when CLOSED."""
        cb = CircuitBreaker()
        assert cb.is_available() is True

    def test_circuit_breaker_blocks_requests_when_open(self):
        """Test that requests blocked when OPEN."""
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()

        assert cb.is_available() is False

    def test_circuit_breaker_half_open_after_timeout(self):
        """Test that circuit goes HALF_OPEN after timeout."""
        cb = CircuitBreaker(failure_threshold=1, timeout_seconds=0)
        cb.record_failure()

        assert cb.state == CircuitBreaker.OPEN

        # After timeout, should allow test request
        import time

        time.sleep(0.1)
        assert cb.is_available() is True
        assert cb.state == CircuitBreaker.HALF_OPEN

    def test_circuit_breaker_closes_after_recovery(self):
        """Test that circuit closes after successful operations."""
        cb = CircuitBreaker(failure_threshold=2, success_threshold=2)

        # Fail twice to open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN

        # Simulate timeout
        cb.last_failure_time = None  # Skip timeout check for test
        cb._half_open()

        # Recover with successes
        cb.record_success()
        assert cb.state == CircuitBreaker.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitBreaker.CLOSED

    def test_circuit_breaker_resets_failures_on_success_when_closed(self):
        """Test that failures reset when operation succeeds."""
        cb = CircuitBreaker()

        cb.record_failure()
        assert cb.failure_count == 1

        cb.record_success()
        assert cb.failure_count == 0


class TestRetryConfig:
    """Test retry configuration."""

    def test_retry_config_exponential_backoff(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(base_delay=1.0, backoff_factor=2.0, max_delay=30.0)

        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
        assert config.get_delay(3) == 8.0

    def test_retry_config_respects_max_delay(self):
        """Test that retry config respects maximum delay."""
        config = RetryConfig(base_delay=1.0, backoff_factor=2.0, max_delay=5.0)

        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
        assert config.get_delay(3) == 5.0  # Capped at max_delay


class TestPositionSyncRecovery:
    """Test position sync recovery mechanism."""

    def test_position_sync_recovery_initial_state(self):
        """Test initial state of position sync recovery."""
        psr = PositionSyncRecovery()
        assert psr.sync_failure_count == 0
        assert psr.last_successful_sync is None

    def test_position_sync_records_success(self):
        """Test recording successful sync."""
        psr = PositionSyncRecovery()
        psr.sync_failure_count = 5

        psr.record_sync_success()

        assert psr.sync_failure_count == 0
        assert psr.last_successful_sync is not None

    def test_position_sync_records_failure(self):
        """Test recording sync failure."""
        psr = PositionSyncRecovery()

        psr.record_sync_failure()
        assert psr.sync_failure_count == 1

        psr.record_sync_failure()
        assert psr.sync_failure_count == 2

    def test_position_sync_should_retry(self):
        """Test should_retry logic."""
        psr = PositionSyncRecovery(max_retries=3)

        assert psr.should_retry() is True

        psr.record_sync_failure()
        assert psr.should_retry() is True

        psr.record_sync_failure()
        assert psr.should_retry() is True

        psr.record_sync_failure()
        assert psr.should_retry() is False

    def test_position_sync_staleness_check(self):
        """Test staleness check for position data."""
        psr = PositionSyncRecovery()

        # No sync yet - data is stale
        assert psr.is_stale(max_age_seconds=1) is True

        # Record successful sync
        psr.record_sync_success()

        # Data not stale immediately
        assert psr.is_stale(max_age_seconds=10) is False


class TestErrorRecoveryManager:
    """Test error recovery manager."""

    def test_error_recovery_manager_initial_state(self):
        """Test initial state of error recovery manager."""
        manager = ErrorRecoveryManager()

        assert manager.circuit_breaker.state == CircuitBreaker.CLOSED
        assert manager.should_allow_request() is True

    def test_error_recovery_manager_blocks_when_circuit_open(self):
        """Test that manager blocks requests when circuit open."""
        manager = ErrorRecoveryManager()
        manager.circuit_breaker.state = CircuitBreaker.OPEN
        manager.circuit_breaker.last_failure_time = None

        assert manager.should_allow_request() is False

    def test_error_recovery_manager_handles_retryable_error(self):
        """Test handling of retryable error."""
        manager = ErrorRecoveryManager()
        error = Exception("Connection timeout")

        strategy = manager.handle_request_failure(error)

        assert strategy == ErrorRecoveryStrategy.RETRY

    def test_error_recovery_manager_handles_non_retryable_error(self):
        """Test handling of non-retryable error."""
        manager = ErrorRecoveryManager()
        error = Exception("Insufficient buying power")

        strategy = manager.handle_request_failure(error)

        assert strategy == ErrorRecoveryStrategy.FAIL

    def test_error_recovery_manager_callback_on_circuit_open(self):
        """Test that callback is triggered when circuit opens."""
        manager = ErrorRecoveryManager()
        mock_callback = MagicMock()
        manager.on_circuit_open = mock_callback

        # Trigger circuit open
        for _ in range(manager.circuit_breaker.failure_threshold):
            manager.circuit_breaker.record_failure()

        # Try to handle failure when open
        error = Exception("Test error")
        manager.handle_request_failure(error)

        mock_callback.assert_called_once()

    def test_error_recovery_manager_get_retry_delay(self):
        """Test retry delay calculation."""
        manager = ErrorRecoveryManager()

        delay_0 = manager.get_retry_delay(0)
        delay_1 = manager.get_retry_delay(1)
        delay_2 = manager.get_retry_delay(2)

        assert delay_0 < delay_1 < delay_2


class TestAlpacaAdapterRetryLogic:
    """Test retry logic integration in AlpacaAdapter."""

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_on_first_try(self):
        """Test successful operation on first try."""
        adapter = AlpacaAdapter()
        mock_operation = AsyncMock(return_value="success")

        result = await adapter._retry_with_backoff(
            "test_operation", mock_operation
        )

        assert result == "success"
        mock_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_with_backoff_retries_on_transient_error(self):
        """Test retry on transient error."""
        adapter = AlpacaAdapter()
        mock_operation = AsyncMock()
        mock_operation.side_effect = [
            Exception("Connection timeout"),
            Exception("Connection timeout"),
            "success",
        ]

        result = await adapter._retry_with_backoff(
            "test_operation", mock_operation
        )

        assert result == "success"
        assert mock_operation.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff_fails_on_permanent_error(self):
        """Test that permanent errors don't retry."""
        adapter = AlpacaAdapter()
        mock_operation = AsyncMock(side_effect=Exception("Insufficient buying power"))

        with pytest.raises(Exception):
            await adapter._retry_with_backoff("test_operation", mock_operation)

        mock_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_with_backoff_respects_max_attempts(self):
        """Test that max attempts is respected."""
        adapter = AlpacaAdapter()
        adapter.retry_config.max_attempts = 2
        mock_operation = AsyncMock(side_effect=Exception("Connection timeout"))

        with pytest.raises(Exception):
            await adapter._retry_with_backoff("test_operation", mock_operation)

        assert mock_operation.call_count == 2


class TestPositionSyncRecoveryIntegration:
    """Test position sync recovery in adapter."""

    @pytest.mark.asyncio
    async def test_sync_positions_with_recovery_success(self):
        """Test successful position sync."""
        adapter = AlpacaAdapter()
        mock_positions = [
            {
                "symbol": "AAPL",
                "qty": 100,
                "avg_fill_price": 150.0,
                "current_price": 155.0,
            }
        ]
        adapter.client.get_positions = AsyncMock(return_value=mock_positions)

        result = await adapter._sync_positions_with_recovery()

        assert len(result) == 1
        assert "AAPL" in result

    @pytest.mark.asyncio
    async def test_sync_positions_with_recovery_returns_cached_on_failure(self):
        """Test that cached positions returned on sync failure."""
        adapter = AlpacaAdapter()
        # Pre-populate cached positions
        adapter.positions = {
            "CACHED": BrokerPosition(
                symbol="CACHED",
                quantity=Decimal("100"),
                avg_price=Decimal("100"),
                current_price=Decimal("100"),
                market_value=Decimal("10000"),
                unrealized_pl=Decimal("0"),
                unrealized_pl_pct=Decimal("0"),
            )
        }

        adapter.client.get_positions = AsyncMock(side_effect=Exception("Network error"))

        result = await adapter._sync_positions_with_recovery()

        assert "CACHED" in result
        assert len(result) == 1


class TestErrorCallbacks:
    """Test error recovery callbacks."""

    def test_register_error_callbacks(self):
        """Test registering error callbacks."""
        adapter = AlpacaAdapter()
        mock_circuit_callback = MagicMock()
        mock_sync_callback = MagicMock()

        adapter.register_error_callbacks(
            on_circuit_break=mock_circuit_callback,
            on_sync_error=mock_sync_callback,
        )

        assert adapter.on_circuit_break == mock_circuit_callback
        assert adapter.on_sync_error == mock_sync_callback

    def test_get_error_recovery_status(self):
        """Test getting error recovery status."""
        adapter = AlpacaAdapter()

        status = adapter.get_error_recovery_status()

        assert "circuit_breaker" in status
        assert "position_sync" in status
        assert "retry_config" in status
        assert status["circuit_breaker"]["state"] == CircuitBreaker.CLOSED
