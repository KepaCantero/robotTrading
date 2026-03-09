"""
Tests for Strategy Registry Pattern following Percival's Architecture Patterns with Python.

Tests verify that the Strategy pattern with Registry correctly implements:
- Strategy interface
- Strategy context
- Strategy registration
- Strategy creation
- Strategy lookup and filtering
- Decorator registration
"""
from typing import Any, Dict, List

import pytest

from app.domain.strategies.strategy_registry import (
    BaseStrategy,
    StrategyContext,
    StrategyFactory,
    StrategyRegistry,
    get_default_registry,
    register_strategy,
)

# ============================================================================
# TEST STRATEGIES
# ============================================================================


class MovingAverageStrategy(BaseStrategy):
    """Test moving average strategy."""

    async def execute(self, data: List[float]) -> Dict[str, Any]:
        """Execute MA strategy."""
        short_period = self.config.get("short_period", 10)
        long_period = self.config.get("long_period", 30)

        if len(data) < long_period:
            return {"signal": "hold"}

        short_ma = sum(data[-short_period:]) / short_period
        long_ma = sum(data[-long_period:]) / long_period

        if short_ma > long_ma:
            return {"signal": "buy", "short_ma": short_ma, "long_ma": long_ma}
        elif short_ma < long_ma:
            return {"signal": "sell", "short_ma": short_ma, "long_ma": long_ma}
        else:
            return {"signal": "hold", "short_ma": short_ma, "long_ma": long_ma}

    def get_required_parameters(self) -> List[str]:
        return ["short_period", "long_period"]


class RSIStrategy(BaseStrategy):
    """Test RSI strategy."""

    async def execute(self, data: List[float]) -> Dict[str, Any]:
        """Execute RSI strategy."""
        period = self.config.get("period", 14)

        if len(data) < period:
            return {"signal": "hold"}

        # Simplified RSI calculation
        gains = [max(data[i] - data[i - 1], 0) for i in range(1, len(data))]
        losses = [max(data[i - 1] - data[i], 0) for i in range(1, len(data))]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        if rsi > 70:
            return {"signal": "sell", "rsi": rsi}
        elif rsi < 30:
            return {"signal": "buy", "rsi": rsi}
        else:
            return {"signal": "hold", "rsi": rsi}


class MeanReversionStrategy(BaseStrategy):
    """Test mean reversion strategy."""

    async def execute(self, data: List[float]) -> Dict[str, Any]:
        """Execute mean reversion strategy."""
        period = self.config.get("period", 20)
        threshold = self.config.get("threshold", 2.0)

        if len(data) < period:
            return {"signal": "hold"}

        mean = sum(data[-period:]) / period
        std = (sum((x - mean) ** 2 for x in data[-period:]) / period) ** 0.5

        current = data[-1]
        z_score = (current - mean) / std if std > 0 else 0

        if z_score > threshold:
            return {"signal": "sell", "z_score": z_score}
        elif z_score < -threshold:
            return {"signal": "buy", "z_score": z_score}
        else:
            return {"signal": "hold", "z_score": z_score}


# ============================================================================
# TEST BASE STRATEGY
# ============================================================================


class TestBaseStrategy:
    """Tests for BaseStrategy."""

    def test_strategy_initialization(self):
        """Test strategy initialization with config."""
        config = {"name": "Test Strategy", "description": "Test description", "version": "2.0.0"}

        strategy = MovingAverageStrategy(config)

        assert strategy.name == "Test Strategy"
        assert strategy.description == "Test description"
        assert strategy.version == "2.0.0"

    def test_strategy_get_metadata(self):
        """Test getting strategy metadata."""
        strategy = MovingAverageStrategy({"name": "MA Strategy"})
        metadata = strategy.get_metadata()

        assert metadata["name"] == "MA Strategy"
        assert metadata["class"] == "MovingAverageStrategy"
        assert "required_parameters" in metadata

    def test_strategy_repr(self):
        """Test strategy string representation."""
        strategy = MovingAverageStrategy({"name": "MA", "version": "1.0"})

        repr_str = repr(strategy)
        assert "MovingAverageStrategy" in repr_str
        assert "MA" in repr_str


# ============================================================================
# TEST STRATEGY CONTEXT
# ============================================================================


class TestStrategyContext:
    """Tests for StrategyContext."""

    @pytest.mark.asyncio
    async def test_set_and_execute_strategy(self):
        """Test setting and executing a strategy."""
        context = StrategyContext()
        strategy = MovingAverageStrategy({"short_period": 5, "long_period": 10})

        context.set_strategy(strategy)

        data = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        result = await context.execute_strategy(data)

        assert result["signal"] in ["buy", "sell", "hold"]

    @pytest.mark.asyncio
    async def test_execute_without_set_raises_error(self):
        """Test that executing without setting strategy raises error."""
        context = StrategyContext()

        with pytest.raises(RuntimeError, match="No strategy set"):
            await context.execute_strategy([])

    def test_get_current_strategy(self):
        """Test getting current strategy."""
        context = StrategyContext()
        strategy = MovingAverageStrategy({})

        assert context.get_strategy() is None

        context.set_strategy(strategy)

        assert context.get_strategy() is strategy

    @pytest.mark.asyncio
    async def test_execution_history(self):
        """Test that execution history is recorded."""
        context = StrategyContext()
        strategy = MovingAverageStrategy({"short_period": 5, "long_period": 10})

        context.set_strategy(strategy)

        await context.execute_strategy([100, 101, 102, 103, 104])
        await context.execute_strategy([105, 106, 107, 108, 109])

        history = context.get_execution_history()

        assert len(history) == 2
        assert history[0]["success"] is True
        assert "duration_ms" in history[0]

    @pytest.mark.asyncio
    async def test_switch_strategies(self):
        """Test switching strategies at runtime."""
        context = StrategyContext()

        # Use MA strategy
        ma_strategy = MovingAverageStrategy({"short_period": 5, "long_period": 10})
        context.set_strategy(ma_strategy)
        result1 = await context.execute_strategy([100, 101, 102, 103, 104])

        # Switch to RSI strategy
        rsi_strategy = RSIStrategy({"period": 5})
        context.set_strategy(rsi_strategy)
        result2 = await context.execute_strategy([100, 101, 102, 103, 104])

        assert "signal" in result1
        assert "signal" in result2


# ============================================================================
# TEST STRATEGY REGISTRY
# ============================================================================


class TestStrategyRegistry:
    """Tests for StrategyRegistry."""

    def test_register_strategy(self):
        """Test registering a strategy."""
        registry = StrategyRegistry()

        registry.register(
            name="ma_short",
            strategy_class=MovingAverageStrategy,
            description="Short-term MA strategy",
            category="trend",
            tags=["ma", "short"],
        )

        assert "ma_short" in registry
        assert len(registry) == 1

    def test_register_duplicate_without_replace_raises_error(self):
        """Test that registering duplicate without replace raises error."""
        registry = StrategyRegistry()

        registry.register("ma", MovingAverageStrategy)

        with pytest.raises(ValueError, match="already registered"):
            registry.register("ma", RSIStrategy)

    def test_register_duplicate_with_replace(self):
        """Test that registering with replace works."""
        registry = StrategyRegistry()

        registry.register("strategy", MovingAverageStrategy)
        registry.register("strategy", RSIStrategy, replace=True)

        metadata = registry.get_metadata("strategy")
        assert metadata.strategy_class == RSIStrategy

    def test_register_invalid_class_raises_error(self):
        """Test that registering non-strategy class raises error."""
        registry = StrategyRegistry()

        class NotAStrategy:
            pass

        with pytest.raises(TypeError, match="must inherit from BaseStrategy"):
            registry.register("invalid", NotAStrategy)

    def test_unregister_strategy(self):
        """Test unregistering a strategy."""
        registry = StrategyRegistry()

        registry.register("ma", MovingAverageStrategy)
        assert "ma" in registry

        registry.unregister("ma")
        assert "ma" not in registry

    def test_unregister_nonexistent_raises_error(self):
        """Test that unregistering non-existent strategy raises error."""
        registry = StrategyRegistry()

        with pytest.raises(KeyError):
            registry.unregister("nonexistent")

    def test_create_strategy_instance(self):
        """Test creating a strategy instance."""
        registry = StrategyRegistry()

        registry.register("ma", MovingAverageStrategy)

        strategy = registry.create(name="ma", config={"short_period": 10, "long_period": 30})

        assert isinstance(strategy, MovingAverageStrategy)
        assert strategy.config["short_period"] == 10

    def test_create_nonexistent_raises_error(self):
        """Test that creating non-existent strategy raises error."""
        registry = StrategyRegistry()

        with pytest.raises(KeyError):
            registry.create("nonexistent", {})

    def test_create_disabled_strategy_raises_error(self):
        """Test that creating disabled strategy raises error."""
        registry = StrategyRegistry()

        registry.register("ma", MovingAverageStrategy, enabled=False)

        with pytest.raises(ValueError, match="is disabled"):
            registry.create("ma", {})

    def test_get_metadata(self):
        """Test getting strategy metadata."""
        registry = StrategyRegistry()

        registry.register(
            name="ma",
            strategy_class=MovingAverageStrategy,
            description="MA strategy",
            category="trend",
            tags=["ma", "crossover"],
        )

        metadata = registry.get_metadata("ma")

        assert metadata.name == "ma"
        assert metadata.description == "MA strategy"
        assert metadata.category == "trend"
        assert "ma" in metadata.tags

    def test_list_strategies_all(self):
        """Test listing all strategies."""
        registry = StrategyRegistry()

        registry.register("ma", MovingAverageStrategy, category="trend")
        registry.register("rsi", RSIStrategy, category="momentum")
        registry.register("mr", MeanReversionStrategy, category="mean_reversion", enabled=False)

        strategies = registry.list_strategies()

        assert len(strategies) == 3

    def test_list_strategies_by_category(self):
        """Test listing strategies by category."""
        registry = StrategyRegistry()

        registry.register("ma_short", MovingAverageStrategy, category="trend")
        registry.register("ma_long", MovingAverageStrategy, category="trend")
        registry.register("rsi", RSIStrategy, category="momentum")

        trend_strategies = registry.list_strategies(category="trend")

        assert len(trend_strategies) == 2
        assert all(s.category == "trend" for s in trend_strategies)

    def test_list_strategies_enabled_only(self):
        """Test listing only enabled strategies."""
        registry = StrategyRegistry()

        registry.register("ma", MovingAverageStrategy, enabled=True)
        registry.register("rsi", RSIStrategy, enabled=False)

        enabled = registry.list_strategies(enabled_only=True)

        assert len(enabled) == 1
        assert enabled[0].name == "ma"

    def test_list_strategies_by_tags(self):
        """Test listing strategies by tags."""
        registry = StrategyRegistry()

        registry.register("ma_short", MovingAverageStrategy, tags=["ma", "short", "crossover"])
        registry.register("ma_long", MovingAverageStrategy, tags=["ma", "long"])
        registry.register("rsi", RSIStrategy, tags=["momentum", "oscillator"])

        ma_strategies = registry.list_strategies(tags=["ma"])

        assert len(ma_strategies) == 2
        crossover_strategies = registry.list_strategies(tags=["ma", "crossover"])
        assert len(crossover_strategies) == 1

    def test_find_by_category(self):
        """Test finding strategies by category."""
        registry = StrategyRegistry()

        registry.register("ma", MovingAverageStrategy, category="trend")
        registry.register("rsi", RSIStrategy, category="momentum")

        trend_strategies = registry.find_by_category("trend")

        assert len(trend_strategies) == 1
        assert trend_strategies[0].name == "ma"

    def test_enable_strategy(self):
        """Test enabling a strategy."""
        registry = StrategyRegistry()

        registry.register("ma", MovingAverageStrategy, enabled=False)
        assert registry.get_metadata("ma").enabled is False

        registry.enable("ma")
        assert registry.get_metadata("ma").enabled is True

    def test_disable_strategy(self):
        """Test disabling a strategy."""
        registry = StrategyRegistry()

        registry.register("ma", MovingAverageStrategy, enabled=True)
        assert registry.get_metadata("ma").enabled is True

        registry.disable("ma")
        assert registry.get_metadata("ma").enabled is False

    def test_categories(self):
        """Test getting list of categories."""
        registry = StrategyRegistry()

        registry.register("ma", MovingAverageStrategy, category="trend")
        registry.register("rsi", RSIStrategy, category="momentum")
        registry.register("mr", MeanReversionStrategy, category="mean_reversion")

        categories = registry.categories()

        assert "trend" in categories
        assert "momentum" in categories
        assert "mean_reversion" in categories
        assert len(categories) == 3

    def test_contains_operator(self):
        """Test 'in' operator for checking strategy existence."""
        registry = StrategyRegistry()

        registry.register("ma", MovingAverageStrategy)

        assert "ma" in registry
        assert "rsi" not in registry


# ============================================================================
# TEST STRATEGY FACTORY
# ============================================================================


class TestStrategyFactory:
    """Tests for StrategyFactory."""

    def test_create_strategy(self):
        """Test creating a strategy through factory."""
        registry = StrategyRegistry()
        registry.register("ma", MovingAverageStrategy)

        factory = StrategyFactory(registry)
        strategy = factory.create("ma", {"short_period": 10})

        assert isinstance(strategy, MovingAverageStrategy)

    def test_create_context(self):
        """Test creating a context with strategy."""
        registry = StrategyRegistry()
        registry.register("ma", MovingAverageStrategy)

        factory = StrategyFactory(registry)
        context = factory.create_context("ma", {})

        assert isinstance(context, StrategyContext)
        assert context.get_strategy() is not None

    def test_create_batch(self):
        """Test creating multiple strategies."""
        registry = StrategyRegistry()
        registry.register("ma", MovingAverageStrategy)
        registry.register("rsi", RSIStrategy)

        factory = StrategyFactory(registry)
        strategies = factory.create_batch([("ma", {"short_period": 10}), ("rsi", {"period": 14})])

        assert len(strategies) == 2
        assert all(isinstance(s, BaseStrategy) for s in strategies)

    def test_list_available(self):
        """Test listing available strategies."""
        registry = StrategyRegistry()
        registry.register("ma", MovingAverageStrategy)
        registry.register("rsi", RSIStrategy, enabled=False)

        factory = StrategyFactory(registry)
        available = factory.list_available()

        assert "ma" in available
        assert "rsi" not in available


# ============================================================================
# TEST DECORATOR REGISTRATION
# ============================================================================


class TestDecoratorRegistration:
    """Tests for decorator registration."""

    def test_register_strategy_decorator(self):
        """Test using decorator to register strategy."""
        registry = StrategyRegistry()

        @register_strategy(
            name="custom_ma",
            description="Custom MA strategy",
            category="trend",
            tags=["ma", "custom"],
            registry=registry,
        )
        class CustomMAStrategy(BaseStrategy):
            async def execute(self, data):
                return {"signal": "hold"}

        assert "custom_ma" in registry
        metadata = registry.get_metadata("custom_ma")
        assert metadata.description == "Custom MA strategy"
        assert metadata.category == "trend"


# ============================================================================
# TEST GLOBAL REGISTRY
# ============================================================================


class TestGlobalRegistry:
    """Tests for global registry."""

    def test_get_default_registry(self):
        """Test getting default registry."""
        registry = get_default_registry()
        assert isinstance(registry, StrategyRegistry)

    def test_register_and_create_from_default_registry(self):
        """Test registering and creating from default registry."""
        # Note: This would typically be done at module initialization
        # For testing, we use a separate approach


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
