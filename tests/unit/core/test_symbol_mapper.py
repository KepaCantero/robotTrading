"""
Unit Tests for Symbol Mapper Component

Tests the SymbolMapper functionality including:
- Symbol mapping (internal <-> broker)
- Validation
- Multi-broker support
- Error handling
- FIFO tax compliance integration

Author: Backend Developer
Date: 2026-01-25
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from app.core.symbol_mapper import (
    SymbolMapper,
    SymbolMapping,
    SymbolValidator,
    BrokerMappingTables,
    SymbolMapperMixin,
    MappingStatus,
    ValidationError,
    UnknownSymbolError,
    AmbiguousSymbolError,
)
from app.core.interfaces.broker_base import BrokerType


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def symbol_mapper():
    """Create a SymbolMapper instance for testing."""
    return SymbolMapper()


@pytest.fixture
def sample_mapping():
    """Create a sample SymbolMapping."""
    return SymbolMapping(
        internal_symbol="BTC",
        broker_symbol="BTCUSDT",
        broker_name="binance",
        broker_type=BrokerType.CRYPTO,
        asset_class="crypto",
        is_verified=True,
    )


# ============================================================================
# TEST: SYMBOL VALIDATION
# ============================================================================


class TestSymbolValidator:
    """Test suite for SymbolValidator."""

    def test_validate_valid_internal_symbol(self):
        """Test validation of valid internal symbols."""
        valid_symbols = ["BTC", "ETH", "SOL", "EURUSD", "AAPL"]

        for symbol in valid_symbols:
            assert SymbolValidator.validate_internal_symbol(symbol) is True

    def test_validate_invalid_internal_symbol_empty(self):
        """Test that empty symbols raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolValidator.validate_internal_symbol("")

        assert "cannot be empty" in str(exc_info.value)

    def test_validate_invalid_internal_symbol_format(self):
        """Test that invalid symbol formats raise ValidationError."""
        invalid_symbols = ["123", "A", "VERYLONGSYMBOL", "btc", "b t c"]

        for symbol in invalid_symbols:
            with pytest.raises(ValidationError):
                SymbolValidator.validate_internal_symbol(symbol)

    def test_validate_valid_binance_symbol(self):
        """Test validation of valid Binance symbols."""
        valid_symbols = ["BTCUSDT", "ETHUSDT", "EURUSDT"]

        for symbol in valid_symbols:
            assert SymbolValidator.validate_broker_symbol(symbol, "binance") is True

    def test_validate_invalid_binance_symbol(self):
        """Test that invalid Binance symbols raise ValidationError."""
        invalid_symbols = ["BTC", "BTC-USD", "BTC_USDT"]

        for symbol in invalid_symbols:
            with pytest.raises(ValidationError):
                SymbolValidator.validate_broker_symbol(symbol, "binance")

    def test_validate_valid_oanda_symbol(self):
        """Test validation of valid OANDA symbols."""
        valid_symbols = ["EUR_USD", "BTC_USD", "GBP_USD"]

        for symbol in valid_symbols:
            assert SymbolValidator.validate_broker_symbol(symbol, "oanda") is True

    def test_validate_invalid_oanda_symbol(self):
        """Test that invalid OANDA symbols raise ValidationError."""
        invalid_symbols = ["EURUSD", "BTC-USD", "EUR/USD"]

        for symbol in invalid_symbols:
            with pytest.raises(ValidationError):
                SymbolValidator.validate_broker_symbol(symbol, "oanda")

    def test_validate_valid_ibkr_symbol(self):
        """Test validation of valid IBKR symbols."""
        valid_symbols = ["AAPL", "IBKR:BTC", "MSFT"]

        for symbol in valid_symbols:
            assert SymbolValidator.validate_broker_symbol(symbol, "ibkr") is True

    def test_validate_invalid_ibkr_symbol(self):
        """Test that invalid IBKR symbols raise ValidationError."""
        invalid_symbols = ["VERYLONG", "123", "IBKR-USD"]

        for symbol in invalid_symbols:
            with pytest.raises(ValidationError):
                SymbolValidator.validate_broker_symbol(symbol, "ibkr")

    def test_extract_internal_from_binance(self):
        """Test extracting internal symbol from Binance format."""
        assert SymbolValidator.extract_internal_from_broker("BTCUSDT", "binance") == "BTC"
        assert SymbolValidator.extract_internal_from_broker("ETHUSDT", "binance") == "ETH"

    def test_extract_internal_from_oanda(self):
        """Test extracting internal symbol from OANDA format."""
        assert SymbolValidator.extract_internal_from_broker("BTC_USD", "oanda") == "BTC"
        assert SymbolValidator.extract_internal_from_broker("EUR_USD", "oanda") == "EUR"

    def test_extract_internal_from_ibkr(self):
        """Test extracting internal symbol from IBKR format."""
        assert SymbolValidator.extract_internal_from_broker("IBKR:BTC", "ibkr") == "BTC"
        assert SymbolValidator.extract_internal_from_broker("AAPL", "ibkr") == "AAPL"

    def test_extract_internal_from_kraken(self):
        """Test extracting internal symbol from Kraken format."""
        assert SymbolValidator.extract_internal_from_broker("XXBTZUSD", "kraken") == "BTC"
        assert SymbolValidator.extract_internal_from_broker("XETHZUSD", "kraken") == "ETH"


# ============================================================================
# TEST: BROKER MAPPING TABLES
# ============================================================================


class TestBrokerMappingTables:
    """Test suite for BrokerMappingTables."""

    def test_get_binance_mapping(self):
        """Test getting Binance mapping."""
        assert BrokerMappingTables.get_default_mapping("binance", "BTC") == "BTCUSDT"
        assert BrokerMappingTables.get_default_mapping("binance", "ETH") == "ETHUSDT"

    def test_get_oanda_mapping(self):
        """Test getting OANDA mapping."""
        assert BrokerMappingTables.get_default_mapping("oanda", "BTC") == "BTC_USD"
        assert BrokerMappingTables.get_default_mapping("oanda", "EUR") == "EUR_USD"

    def test_get_ibkr_mapping(self):
        """Test getting IBKR mapping."""
        assert BrokerMappingTables.get_default_mapping("ibkr", "BTC") == "IBKR:BTC"
        assert BrokerMappingTables.get_default_mapping("ibkr", "AAPL") == "AAPL"

    def test_get_degiro_mapping(self):
        """Test getting Degiro mapping."""
        assert BrokerMappingTables.get_default_mapping("degiro", "VWCE") == "VWCE"
        assert BrokerMappingTables.get_default_mapping("degiro", "AAPL") == "AAPL"

    def test_get_unknown_broker_mapping(self):
        """Test that unknown broker returns None."""
        assert BrokerMappingTables.get_default_mapping("unknown", "BTC") is None

    def test_get_all_broker_symbols(self):
        """Test getting all broker symbols for internal symbol."""
        brokers = BrokerMappingTables.get_all_broker_symbols("BTC")

        assert "binance" in brokers
        assert brokers["binance"] == "BTCUSDT"
        assert "oanda" in brokers
        assert brokers["oanda"] == "BTC_USD"
        assert "ibkr" in brokers
        assert brokers["ibkr"] == "IBKR:BTC"


# ============================================================================
# TEST: SYMBOL MAPPING DATA CLASS
# ============================================================================


class TestSymbolMapping:
    """Test suite for SymbolMapping dataclass."""

    def test_create_valid_mapping(self, sample_mapping):
        """Test creating a valid symbol mapping."""
        assert sample_mapping.internal_symbol == "BTC"
        assert sample_mapping.broker_symbol == "BTCUSDT"
        assert sample_mapping.broker_name == "binance"
        assert sample_mapping.broker_type == BrokerType.CRYPTO

    def test_mapping_normalizes_symbols(self):
        """Test that symbols are normalized to uppercase."""
        mapping = SymbolMapping(
            internal_symbol="btc",
            broker_symbol="btcusdt",
            broker_name="Binance",
            broker_type=BrokerType.CRYPTO,
        )

        assert mapping.internal_symbol == "BTC"
        assert mapping.broker_symbol == "BTCUSDT"
        assert mapping.broker_name == "binance"

    def test_mapping_validation_empty_internal_symbol(self):
        """Test that empty internal symbol raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolMapping(
                internal_symbol="",
                broker_symbol="BTCUSDT",
                broker_name="binance",
                broker_type=BrokerType.CRYPTO,
            )

        assert "cannot be empty" in str(exc_info.value)

    def test_mapping_validation_empty_broker_symbol(self):
        """Test that empty broker symbol raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolMapping(
                internal_symbol="BTC",
                broker_symbol="",
                broker_name="binance",
                broker_type=BrokerType.CRYPTO,
            )

        assert "cannot be empty" in str(exc_info.value)

    def test_mapping_to_dict(self, sample_mapping):
        """Test converting mapping to dictionary."""
        mapping_dict = sample_mapping.to_dict()

        assert isinstance(mapping_dict, dict)
        assert mapping_dict['internal_symbol'] == "BTC"
        assert mapping_dict['broker_symbol'] == "BTCUSDT"
        assert mapping_dict['broker_name'] == "binance"
        assert 'id' in mapping_dict
        assert 'created_at' in mapping_dict


# ============================================================================
# TEST: SYMBOL MAPPER MAIN CLASS
# ============================================================================


class TestSymbolMapper:
    """Test suite for SymbolMapper."""

    # ========================================================================
    # Tests: map_internal_to_broker
    # ========================================================================

    def test_map_internal_to_broker_binance(self, symbol_mapper):
        """Test mapping internal symbol to Binance format."""
        assert symbol_mapper.map_internal_to_broker("BTC", "binance") == "BTCUSDT"
        assert symbol_mapper.map_internal_to_broker("ETH", "binance") == "ETHUSDT"

    def test_map_internal_to_broker_oanda(self, symbol_mapper):
        """Test mapping internal symbol to OANDA format."""
        assert symbol_mapper.map_internal_to_broker("BTC", "oanda") == "BTC_USD"
        assert symbol_mapper.map_internal_to_broker("EUR", "oanda") == "EUR_USD"

    def test_map_internal_to_broker_ibkr(self, symbol_mapper):
        """Test mapping internal symbol to IBKR format."""
        assert symbol_mapper.map_internal_to_broker("BTC", "ibkr") == "IBKR:BTC"
        assert symbol_mapper.map_internal_to_broker("AAPL", "ibkr") == "AAPL"

    def test_map_internal_to_broker_kraken(self, symbol_mapper):
        """Test mapping internal symbol to Kraken format."""
        assert symbol_mapper.map_internal_to_broker("BTC", "kraken") == "XXBTZUSD"
        assert symbol_mapper.map_internal_to_broker("ETH", "kraken") == "XETHZUSD"

    def test_map_internal_to_broker_coinbase(self, symbol_mapper):
        """Test mapping internal symbol to Coinbase format."""
        assert symbol_mapper.map_internal_to_broker("BTC", "coinbase") == "BTC-USD"
        assert symbol_mapper.map_internal_to_broker("ETH", "coinbase") == "ETH-USD"

    def test_map_internal_to_broker_normalizes_input(self, symbol_mapper):
        """Test that input is normalized."""
        assert symbol_mapper.map_internal_to_broker("btc", "BINANCE") == "BTCUSDT"
        assert symbol_mapper.map_internal_to_broker("  btc  ", " binance ") == "BTCUSDT"

    def test_map_internal_to_broker_invalid_symbol(self, symbol_mapper):
        """Test that invalid symbols raise ValidationError."""
        with pytest.raises(ValidationError):
            symbol_mapper.map_internal_to_broker("", "binance")

    def test_map_internal_to_broker_unknown_broker_fallback(self, symbol_mapper):
        """Test fallback for unknown brokers."""
        # Should construct broker symbol using heuristics
        result = symbol_mapper.map_internal_to_broker("DOGE", "unknown_broker")
        assert "DOGE" in result

    # ========================================================================
    # Tests: map_broker_to_internal
    # ========================================================================

    def test_map_broker_to_internal_binance(self, symbol_mapper):
        """Test mapping Binance symbol to internal format."""
        assert symbol_mapper.map_broker_to_internal("BTCUSDT", "binance") == "BTC"
        assert symbol_mapper.map_broker_to_internal("ETHUSDT", "binance") == "ETH"

    def test_map_broker_to_internal_oanda(self, symbol_mapper):
        """Test mapping OANDA symbol to internal format."""
        assert symbol_mapper.map_broker_to_internal("BTC_USD", "oanda") == "BTC"
        assert symbol_mapper.map_broker_to_internal("EUR_USD", "oanda") == "EUR"

    def test_map_broker_to_internal_ibkr(self, symbol_mapper):
        """Test mapping IBKR symbol to internal format."""
        assert symbol_mapper.map_broker_to_internal("IBKR:BTC", "ibkr") == "BTC"
        assert symbol_mapper.map_broker_to_internal("AAPL", "ibkr") == "AAPL"

    def test_map_broker_to_internal_kraken(self, symbol_mapper):
        """Test mapping Kraken symbol to internal format."""
        assert symbol_mapper.map_broker_to_internal("XXBTZUSD", "kraken") == "BTC"
        assert symbol_mapper.map_broker_to_internal("XETHZUSD", "kraken") == "ETH"

    def test_map_broker_to_internal_coinbase(self, symbol_mapper):
        """Test mapping Coinbase symbol to internal format."""
        assert symbol_mapper.map_broker_to_internal("BTC-USD", "coinbase") == "BTC"
        assert symbol_mapper.map_broker_to_internal("ETH-USD", "coinbase") == "ETH"

    def test_map_broker_to_internal_normalizes_input(self, symbol_mapper):
        """Test that input is normalized."""
        assert symbol_mapper.map_broker_to_internal("btcusdt", "BINANCE") == "BTC"
        assert symbol_mapper.map_broker_to_internal("  btcusdt  ", " binance ") == "BTC"

    # ========================================================================
    # Tests: add_mapping
    # ========================================================================

    @pytest.mark.asyncio
    async def test_add_mapping_valid(self, symbol_mapper):
        """Test adding a valid mapping."""
        mapping = await symbol_mapper.add_mapping(
            internal_symbol="DOGE",
            broker_symbol="DOGEUSDT",
            broker_name="binance",
            broker_type=BrokerType.CRYPTO,
            asset_class="crypto",
        )

        assert mapping.internal_symbol == "DOGE"
        assert mapping.broker_symbol == "DOGEUSDT"
        assert mapping.broker_name == "binance"

    @pytest.mark.asyncio
    async def test_add_mapping_invalid_internal_symbol(self, symbol_mapper):
        """Test that invalid internal symbol raises ValidationError."""
        with pytest.raises(ValidationError):
            await symbol_mapper.add_mapping(
                internal_symbol="",
                broker_symbol="DOGEUSDT",
                broker_name="binance",
                broker_type=BrokerType.CRYPTO,
            )

    @pytest.mark.asyncio
    async def test_add_mapping_invalid_broker_symbol(self, symbol_mapper):
        """Test that invalid broker symbol raises ValidationError."""
        with pytest.raises(ValidationError):
            await symbol_mapper.add_mapping(
                internal_symbol="DOGE",
                broker_symbol="INVALID",
                broker_name="binance",
                broker_type=BrokerType.CRYPTO,
            )

    @pytest.mark.asyncio
    async def test_add_mapping_with_metadata(self, symbol_mapper):
        """Test adding a mapping with metadata."""
        metadata = {"precision": 8, "min_quantity": "0.00000001"}
        mapping = await symbol_mapper.add_mapping(
            internal_symbol="DOGE",
            broker_symbol="DOGEUSDT",
            broker_name="binance",
            broker_type=BrokerType.CRYPTO,
            metadata=metadata,
        )

        assert mapping.metadata == metadata

    # ========================================================================
    # Tests: get_all_brokers_for_symbol
    # ========================================================================

    def test_get_all_brokers_for_btc(self, symbol_mapper):
        """Test getting all brokers for BTC."""
        brokers = symbol_mapper.get_all_brokers_for_symbol("BTC")

        assert isinstance(brokers, dict)
        assert "binance" in brokers
        assert brokers["binance"] == "BTCUSDT"
        assert "oanda" in brokers
        assert brokers["oanda"] == "BTC_USD"
        assert "ibkr" in brokers
        assert brokers["ibkr"] == "IBKR:BTC"

    def test_get_all_brokers_for_eth(self, symbol_mapper):
        """Test getting all brokers for ETH."""
        brokers = symbol_mapper.get_all_brokers_for_symbol("ETH")

        assert isinstance(brokers, dict)
        assert "binance" in brokers
        assert brokers["binance"] == "ETHUSDT"

    def test_get_all_brokers_normalizes_input(self, symbol_mapper):
        """Test that input is normalized."""
        brokers = symbol_mapper.get_all_brokers_for_symbol("btc")

        # Should still work with lowercase input
        assert isinstance(brokers, dict)
        assert len(brokers) > 0

    def test_get_all_brokers_invalid_symbol(self, symbol_mapper):
        """Test that invalid symbol raises ValidationError."""
        with pytest.raises(ValidationError):
            symbol_mapper.get_all_brokers_for_symbol("")

    # ========================================================================
    # Tests: validate_mapping
    # ========================================================================

    def test_validate_mapping_valid_binance(self, symbol_mapper):
        """Test validating a valid Binance mapping."""
        is_valid, error = symbol_mapper.validate_mapping("BTC", "BTCUSDT", "binance")

        assert is_valid is True
        assert error is None

    def test_validate_mapping_valid_oanda(self, symbol_mapper):
        """Test validating a valid OANDA mapping."""
        is_valid, error = symbol_mapper.validate_mapping("BTC", "BTC_USD", "oanda")

        assert is_valid is True
        assert error is None

    def test_validate_mapping_mismatch(self, symbol_mapper):
        """Test that mismatched mappings fail validation."""
        is_valid, error = symbol_mapper.validate_mapping("BTC", "ETHUSDT", "binance")

        assert is_valid is False
        assert error is not None
        assert "mismatch" in error.lower()

    def test_validate_mapping_invalid_symbol(self, symbol_mapper):
        """Test that invalid symbols fail validation."""
        is_valid, error = symbol_mapper.validate_mapping("", "BTCUSDT", "binance")

        assert is_valid is False
        assert error is not None

    # ========================================================================
    # Tests: Utility Methods
    # ========================================================================

    def test_get_supported_brokers(self, symbol_mapper):
        """Test getting list of supported brokers."""
        brokers = symbol_mapper.get_supported_brokers()

        assert isinstance(brokers, list)
        assert "binance" in brokers
        assert "oanda" in brokers
        assert "ibkr" in brokers
        assert "degiro" in brokers

    def test_get_statistics(self, symbol_mapper):
        """Test getting mapper statistics."""
        stats = symbol_mapper.get_statistics()

        assert isinstance(stats, dict)
        assert "cached_mappings" in stats
        assert "supported_brokers" in stats
        assert "default_tables_available" in stats

    def test_clear_cache(self, symbol_mapper):
        """Test clearing the cache."""
        # Add something to cache
        symbol_mapper.map_internal_to_broker("BTC", "binance")

        # Clear cache
        symbol_mapper.clear_cache()

        # Check stats
        stats = symbol_mapper.get_statistics()
        assert stats['cached_mappings'] == 0

    def test_construct_broker_symbol_binance(self, symbol_mapper):
        """Test constructing Binance symbol."""
        result = symbol_mapper._construct_broker_symbol("DOGE", "binance")
        assert result == "DOGEUSDT"

    def test_construct_broker_symbol_oanda(self, symbol_mapper):
        """Test constructing OANDA symbol."""
        result = symbol_mapper._construct_broker_symbol("DOGE", "oanda")
        assert result == "DOGE_USD"

    def test_construct_broker_symbol_ibkr(self, symbol_mapper):
        """Test constructing IBKR symbol."""
        result = symbol_mapper._construct_broker_symbol("DOGE", "ibkr")
        assert result == "IBKR:DOGE"


# ============================================================================
# TEST: SYMBOL MAPPER MIXIN
# ============================================================================


class MockBrokerWithMixin(SymbolMapperMixin):
    """Mock broker for testing SymbolMapperMixin."""

    def get_broker_name(self):
        return "binance"


class TestSymbolMapperMixin:
    """Test suite for SymbolMapperMixin."""

    def test_mixin_map_to_broker(self):
        """Test mapping to broker using mixin."""
        broker = MockBrokerWithMixin()
        result = broker.map_to_broker("BTC")

        assert result == "BTCUSDT"

    def test_mixin_map_from_broker(self):
        """Test mapping from broker using mixin."""
        broker = MockBrokerWithMixin()
        result = broker.map_from_broker("BTCUSDT")

        assert result == "BTC"

    def test_mixin_validate_symbol_mapping(self):
        """Test validating symbol mapping using mixin."""
        broker = MockBrokerWithMixin()
        is_valid, error = broker.validate_symbol_mapping("BTC", "BTCUSDT")

        assert is_valid is True
        assert error is None


# ============================================================================
# TEST: INTEGRATION WITH FIFO
# ============================================================================


class TestFIFOIntegration:
    """Test suite for FIFO tax compliance integration."""

    def test_fifo_across_brokers(self, symbol_mapper):
        """Test that FIFO works across multiple brokers."""
        # Simulate buying on Binance
        binance_symbol = symbol_mapper.map_internal_to_broker("BTC", "binance")
        assert binance_symbol == "BTCUSDT"

        # Simulate selling on OANDA
        oanda_symbol = symbol_mapper.map_internal_to_broker("BTC", "oanda")
        assert oanda_symbol == "BTC_USD"

        # Both should normalize to same internal symbol for FIFO
        assert symbol_mapper.map_broker_to_internal(binance_symbol, "binance") == "BTC"
        assert symbol_mapper.map_broker_to_internal(oanda_symbol, "oanda") == "BTC"

    def test_multi_broker_tracking(self, symbol_mapper):
        """Test tracking assets across multiple brokers."""
        brokers = symbol_mapper.get_all_brokers_for_symbol("BTC")

        # Should have mappings for all supported brokers
        assert len(brokers) > 0

        # All should normalize to same internal symbol
        for broker_name, broker_symbol in brokers.items():
            internal = symbol_mapper.map_broker_to_internal(broker_symbol, broker_name)
            assert internal == "BTC"

    def test_tax_report_consistency(self, symbol_mapper):
        """Test that tax reports are consistent across brokers."""
        # Simulate transaction on different brokers
        transactions = [
            ("BTCUSDT", "binance"),
            ("BTC_USD", "oanda"),
            ("IBKR:BTC", "ibkr"),
            ("XXBTZUSD", "kraken"),
        ]

        # All should normalize to same internal symbol
        internal_symbols = [
            symbol_mapper.map_broker_to_internal(symbol, broker) for symbol, broker in transactions
        ]

        # All should be "BTC"
        assert all(s == "BTC" for s in internal_symbols)

        # This ensures FIFO calculations are consistent
        # for Modelo 721 tax reporting


# ============================================================================
# TEST: ERROR HANDLING
# ============================================================================


class TestErrorHandling:
    """Test suite for error handling."""

    def test_empty_internal_symbol_raises_error(self, symbol_mapper):
        """Test that empty internal symbol raises error."""
        with pytest.raises(ValidationError):
            symbol_mapper.map_internal_to_broker("", "binance")

    def test_empty_broker_symbol_raises_error(self, symbol_mapper):
        """Test that empty broker symbol raises error."""
        with pytest.raises(UnknownSymbolError):
            symbol_mapper.map_broker_to_internal("", "binance")

    def test_invalid_symbol_format_raises_error(self, symbol_mapper):
        """Test that invalid symbol format raises error."""
        with pytest.raises(ValidationError):
            SymbolValidator.validate_internal_symbol("123")

    def test_invalid_broker_symbol_format_raises_error(self, symbol_mapper):
        """Test that invalid broker symbol format raises error."""
        with pytest.raises(ValidationError):
            SymbolValidator.validate_broker_symbol("INVALID-FORMAT", "binance")


# ============================================================================
# TEST: PERFORMANCE
# ============================================================================


class TestPerformance:
    """Test suite for performance optimizations."""

    def test_cache_hit(self, symbol_mapper):
        """Test that cache improves performance."""
        # First call - cache miss
        result1 = symbol_mapper.map_internal_to_broker("BTC", "binance")

        # Second call - cache hit
        result2 = symbol_mapper.map_internal_to_broker("BTC", "binance")

        assert result1 == result2
        assert result1 == "BTCUSDT"

    def test_batch_mapping(self, symbol_mapper):
        """Test batch mapping of multiple symbols."""
        symbols = ["BTC", "ETH", "SOL", "ADA", "DOT"]
        broker_name = "binance"

        results = [symbol_mapper.map_internal_to_broker(s, broker_name) for s in symbols]

        assert len(results) == len(symbols)
        assert all(r.endswith("USDT") for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
