"""
T12.1: Unit Tests for ErrorHandling

Tests cover:
- Custom exception classes
- Fallback strategy pattern
- Retry logic with exponential backoff
- Timeout protection
- Error logging and statistics
- Graceful degradation
"""

import pytest
import asyncio
from datetime import datetime

from app.services.error_handling import (
    ErrorHandler,
    ServiceException,
    BacktestException,
    ValidationException,
    ConfigurationException,
    ParameterizationException,
    RecommendationException,
    PortfolioException,
    FallbackStrategy,
    ConservativeBacktestFallback,
    EqualWeightPortfolioFallback,
    ConservativeRecommendationFallback,
)


@pytest.fixture
def error_handler():
    """Create ErrorHandler instance."""
    return ErrorHandler()


@pytest.fixture
def sample_fallback_context():
    """Sample context for fallback strategies."""
    return {
        "capital": 50000,
        "strategy_name": "momentum_modular",
        "assets": ["AAPL", "MSFT", "GOOGL"]
    }


# =============================================================================
# Test Custom Exception Classes
# =============================================================================

class TestCustomExceptions:
    """Test custom exception classes."""

    def test_service_exception_creation(self):
        """Test creating ServiceException."""
        exc = ServiceException(
            service_name="TestService",
            message="Test error",
            error_code="TEST_ERROR"
        )
        assert exc.service_name == "TestService"
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.timestamp is not None

    def test_backtest_exception_creation(self):
        """Test creating BacktestException."""
        exc = BacktestException(
            message="Backtest failed",
            error_code="BACKTEST_TIMEOUT"
        )
        assert exc.service_name == "BacktestOrchestrator"
        assert exc.message == "Backtest failed"
        assert exc.error_code == "BACKTEST_TIMEOUT"

    def test_validation_exception_creation(self):
        """Test creating ValidationException."""
        exc = ValidationException("Validation failed")
        assert exc.service_name == "ValidationEngine"
        assert exc.message == "Validation failed"

    def test_configuration_exception_creation(self):
        """Test creating ConfigurationException."""
        exc = ConfigurationException("Config save failed")
        assert exc.service_name == "ConfigurationRepository"
        assert exc.message == "Config save failed"

    def test_parametrization_exception_creation(self):
        """Test creating ParameterizationException."""
        exc = ParameterizationException("Parametrization failed")
        assert exc.service_name == "ModuleParametrizer"

    def test_recommendation_exception_creation(self):
        """Test creating RecommendationException."""
        exc = RecommendationException("Recommendation scoring failed")
        assert exc.service_name == "StrategyRecommender"

    def test_portfolio_exception_creation(self):
        """Test creating PortfolioException."""
        exc = PortfolioException("Portfolio optimization failed")
        assert exc.service_name == "PortfolioConstructor"


# =============================================================================
# Test Fallback Strategies
# =============================================================================

class TestFallbackStrategies:
    """Test fallback strategy implementations."""

    @pytest.mark.asyncio
    async def test_conservative_backtest_fallback(self, sample_fallback_context):
        """Test conservative backtest fallback strategy."""
        strategy = ConservativeBacktestFallback()

        # Test can_handle
        exc = BacktestException("Backtest failed")
        assert strategy.can_handle(exc) is True

        exc_wrong = ValidationException("Validation failed")
        assert strategy.can_handle(exc_wrong) is False

        # Test execute
        result = await strategy.execute(sample_fallback_context)
        assert result["is_fallback"] is True
        assert result["total_return"] == 0.05
        assert result["sharpe_ratio"] == 0.5
        assert result["viability_status"] == "CONDITIONAL"

    @pytest.mark.asyncio
    async def test_equal_weight_portfolio_fallback(self, sample_fallback_context):
        """Test equal-weight portfolio fallback strategy."""
        strategy = EqualWeightPortfolioFallback()

        # Test can_handle
        exc = PortfolioException("Portfolio optimization failed")
        assert strategy.can_handle(exc) is True

        # Test execute
        result = await strategy.execute(sample_fallback_context)
        assert result["is_fallback"] is True
        assert result["strategy"] == "equal_weight"
        assert len(result["allocation"]) == 3
        assert abs(result["allocation"]["AAPL"] - 1/3) < 0.01

    @pytest.mark.asyncio
    async def test_conservative_recommendation_fallback(self, sample_fallback_context):
        """Test conservative recommendation fallback strategy."""
        strategy = ConservativeRecommendationFallback()

        # Test can_handle
        exc = RecommendationException("Recommendation failed")
        assert strategy.can_handle(exc) is True

        # Test execute
        result = await strategy.execute(sample_fallback_context)
        assert result["is_fallback"] is True
        assert result["recommendation"] == "HOLD"
        assert result["confidence_level"] == "LOW"
        assert result["score"] == 50


# =============================================================================
# Test ErrorHandler with Fallback
# =============================================================================

class TestErrorHandlerWithFallback:
    """Test ErrorHandler with fallback strategies."""

    @pytest.mark.asyncio
    async def test_with_fallback_success(self, error_handler, sample_fallback_context):
        """Test with_fallback when function succeeds."""
        async def successful_fn():
            return {"result": "success"}

        result = await error_handler.with_fallback(
            successful_fn,
            fallback_context=sample_fallback_context
        )
        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_with_fallback_backtest_error(self, error_handler, sample_fallback_context):
        """Test with_fallback triggers backtest fallback on BacktestException."""
        async def failing_fn():
            raise BacktestException("Backtest timeout")

        result = await error_handler.with_fallback(
            failing_fn,
            fallback_context=sample_fallback_context
        )
        assert result["is_fallback"] is True
        assert result["total_return"] == 0.05

    @pytest.mark.asyncio
    async def test_with_fallback_portfolio_error(self, error_handler, sample_fallback_context):
        """Test with_fallback triggers portfolio fallback on PortfolioException."""
        async def failing_fn():
            raise PortfolioException("Optimization failed")

        result = await error_handler.with_fallback(
            failing_fn,
            fallback_context=sample_fallback_context
        )
        assert result["is_fallback"] is True
        assert result["strategy"] == "equal_weight"

    @pytest.mark.asyncio
    async def test_with_fallback_recommendation_error(self, error_handler, sample_fallback_context):
        """Test with_fallback triggers recommendation fallback."""
        async def failing_fn():
            raise RecommendationException("Scoring failed")

        result = await error_handler.with_fallback(
            failing_fn,
            fallback_context=sample_fallback_context
        )
        assert result["is_fallback"] is True
        assert result["recommendation"] == "HOLD"

    @pytest.mark.asyncio
    async def test_error_counting(self, error_handler):
        """Test error counting and logging."""
        assert error_handler.error_count == 0

        async def failing_fn():
            raise BacktestException("Error 1")

        try:
            await error_handler.with_fallback(failing_fn, fallback_context={})
        except Exception:
            pass

        assert error_handler.error_count == 1

    @pytest.mark.asyncio
    async def test_error_log_tracking(self, error_handler):
        """Test error log tracking."""
        async def failing_fn():
            raise BacktestException("Test error", error_code="TEST_CODE")

        try:
            await error_handler.with_fallback(failing_fn, fallback_context={})
        except Exception:
            pass

        stats = error_handler.get_error_stats()
        assert len(stats["error_log"]) > 0
        assert stats["error_log"][0]["error_code"] == "TEST_CODE"


# =============================================================================
# Test Retry Logic
# =============================================================================

class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_immediately(self, error_handler):
        """Test retry when function succeeds immediately."""
        call_count = 0

        async def succeeds_fn():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await error_handler.with_retry(succeeds_fn)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self, error_handler):
        """Test retry succeeds after some failures."""
        call_count = 0

        async def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await error_handler.with_retry(
            sometimes_fails,
            max_retries=3,
            initial_delay=0.01
        )
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_fails_after_max_retries(self, error_handler):
        """Test retry fails after max retries exceeded."""
        async def always_fails():
            raise ValueError("Persistent error")

        with pytest.raises(ValueError):
            await error_handler.with_retry(
                always_fails,
                max_retries=2,
                initial_delay=0.01
            )

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self, error_handler):
        """Test exponential backoff timing."""
        call_times = []

        async def fails_then_succeeds():
            call_times.append(datetime.now())
            if len(call_times) < 3:
                raise ValueError("Temp error")
            return "success"

        await error_handler.with_retry(
            fails_then_succeeds,
            max_retries=3,
            initial_delay=0.01
        )

        # Verify delays increase exponentially
        assert len(call_times) == 3
        delay1 = (call_times[1] - call_times[0]).total_seconds()
        delay2 = (call_times[2] - call_times[1]).total_seconds()
        assert delay2 > delay1  # Second delay should be larger


# =============================================================================
# Test Timeout Protection
# =============================================================================

class TestTimeoutProtection:
    """Test timeout protection for functions."""

    @pytest.mark.asyncio
    async def test_timeout_with_fast_function(self, error_handler):
        """Test timeout with function that completes quickly."""
        async def fast_fn():
            await asyncio.sleep(0.01)
            return "fast_success"

        result = await error_handler.with_timeout(
            fast_fn,
            timeout_seconds=1.0
        )
        assert result == "fast_success"

    @pytest.mark.asyncio
    async def test_timeout_exceeds_limit(self, error_handler):
        """Test timeout when function exceeds time limit."""
        async def slow_fn():
            await asyncio.sleep(0.5)
            return "slow_success"

        with pytest.raises(asyncio.TimeoutError):
            await error_handler.with_timeout(
                slow_fn,
                timeout_seconds=0.1
            )


# =============================================================================
# Test Error Statistics
# =============================================================================

class TestErrorStatistics:
    """Test error statistics and reporting."""

    @pytest.mark.asyncio
    async def test_get_error_stats_empty(self, error_handler):
        """Test getting stats from fresh ErrorHandler."""
        stats = error_handler.get_error_stats()
        assert stats["total_errors"] == 0
        assert stats["error_log"] == []
        assert stats["recent_errors"] == []

    @pytest.mark.asyncio
    async def test_get_error_stats_with_errors(self, error_handler):
        """Test getting stats after errors."""
        async def failing_fn():
            raise BacktestException("Error occurred")

        for _ in range(3):
            try:
                await error_handler.with_fallback(failing_fn, fallback_context={})
            except Exception:
                pass

        stats = error_handler.get_error_stats()
        assert stats["total_errors"] == 3
        assert len(stats["error_log"]) == 3
        assert len(stats["recent_errors"]) == 3

    @pytest.mark.asyncio
    async def test_clear_error_log(self, error_handler):
        """Test clearing error log."""
        async def failing_fn():
            raise BacktestException("Error")

        try:
            await error_handler.with_fallback(failing_fn, fallback_context={})
        except Exception:
            pass

        assert error_handler.error_count > 0
        error_handler.clear_error_log()
        assert error_handler.error_count == 0
        assert error_handler.error_log == []

    @pytest.mark.asyncio
    async def test_recent_errors_limit(self, error_handler):
        """Test that recent_errors is limited to last 5."""
        async def failing_fn():
            raise BacktestException("Error")

        # Create 10 errors
        for _ in range(10):
            try:
                await error_handler.with_fallback(failing_fn, fallback_context={})
            except Exception:
                pass

        stats = error_handler.get_error_stats()
        assert len(stats["recent_errors"]) == 5


# =============================================================================
# Test Fallback Strategy Registration
# =============================================================================

class TestFallbackRegistration:
    """Test custom fallback strategy registration."""

    @pytest.mark.asyncio
    async def test_register_custom_fallback(self, error_handler):
        """Test registering custom fallback strategy."""
        class CustomFallback(FallbackStrategy):
            async def execute(self, context):
                return {"custom": "fallback"}

            def can_handle(self, exception):
                return isinstance(exception, ValidationException)

        initial_count = len(error_handler.fallback_strategies)
        error_handler.register_fallback(CustomFallback())
        assert len(error_handler.fallback_strategies) == initial_count + 1

    @pytest.mark.asyncio
    async def test_custom_fallback_execution(self, error_handler):
        """Test executing custom registered fallback."""
        class CustomFallback(FallbackStrategy):
            async def execute(self, context):
                return {"custom": True, "service": "custom_service"}

            def can_handle(self, exception):
                return isinstance(exception, ConfigurationException)

        error_handler.register_fallback(CustomFallback())

        async def failing_fn():
            raise ConfigurationException("Config failed")

        result = await error_handler.with_fallback(
            failing_fn,
            fallback_context={}
        )
        assert result["custom"] is True
        assert result["service"] == "custom_service"


# =============================================================================
# Integration Tests
# =============================================================================

class TestErrorHandlingIntegration:
    """Integration tests for error handling across scenarios."""

    @pytest.mark.asyncio
    async def test_multi_error_scenario(self, error_handler):
        """Test handling multiple different error types."""
        async def backtest_fails():
            raise BacktestException("Backtest timeout")

        async def recommendation_fails():
            raise RecommendationException("Scoring failed")

        # First error
        result1 = await error_handler.with_fallback(
            backtest_fails,
            fallback_context={"capital": 50000}
        )
        assert result1["is_fallback"] is True
        assert "total_return" in result1

        # Second error
        result2 = await error_handler.with_fallback(
            recommendation_fails,
            fallback_context={}
        )
        assert result2["is_fallback"] is True
        assert "recommendation" in result2

        stats = error_handler.get_error_stats()
        assert stats["total_errors"] == 2

    @pytest.mark.asyncio
    async def test_fallback_with_retry_combination(self, error_handler):
        """Test combining retry and fallback strategies."""
        call_count = 0

        async def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("Temp error")
            raise BacktestException("Fatal backtest error")

        # Use retry first
        try:
            await error_handler.with_retry(
                sometimes_fails,
                max_retries=2,
                initial_delay=0.01
            )
        except BacktestException:
            # Then use fallback
            result = await error_handler.with_fallback(
                sometimes_fails,
                fallback_context={"capital": 50000}
            )
            assert result["is_fallback"] is True
