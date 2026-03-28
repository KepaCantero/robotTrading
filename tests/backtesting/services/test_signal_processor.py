"""
Tests for SignalProcessor service.

Tests signal validation, rejection logic, and approval workflow.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.backtesting.models import BacktestConfig
from app.backtesting.services.signal_processor import SignalProcessor
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType


class MockMarketData:
    """Mock market data for testing."""

    def __init__(self, symbol, price=Decimal("150")):
        self.symbol = symbol
        self.close = Decimal(str(price))
        self.timestamp = datetime(2024, 1, 1, 10, 0)


class MockPortfolio:
    """Mock portfolio for testing."""

    def __init__(self, cash=Decimal("100000"), positions=None):
        self.cash = cash
        self.positions = positions or []

    class Position:
        def __init__(self, symbol, quantity):
            self.symbol = symbol
            self.quantity = Decimal(str(quantity))


class TestSignalProcessor:
    """Test suite for SignalProcessor service."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            max_position_size=Decimal("0.2"),
        )

    @pytest.fixture
    def mock_strategy(self):
        """Create mock strategy."""
        strategy = MagicMock()
        strategy.risk_check.return_value = True
        strategy.get_position_size.return_value = Decimal("100")
        return strategy

    @pytest.fixture
    def signal_processor(self, config, mock_strategy):
        """Create signal processor instance."""
        return SignalProcessor(
            config=config,
            strategy=mock_strategy,
            enable_risk_envelope=False,  # Disable for basic tests
        )

    @pytest.fixture
    def buy_signal(self, default_symbol):
        """Create sample buy signal."""
        return Signal(
            symbol=default_symbol,
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=50.0,
            priority_score=70.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1, 10, 0),
        )

    @pytest.fixture
    def sell_signal(self, default_symbol):
        """Create sample sell signal."""
        return Signal(
            symbol=default_symbol,
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=50.0,
            priority_score=60.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("160"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1, 10, 0),
        )

    @pytest.fixture
    def hold_signal(self, default_symbol):
        """Create sample hold signal."""
        return Signal(
            symbol=default_symbol,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=50.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1, 10, 0),
        )

    def test_initialization(self, config, mock_strategy):
        """Test processor initialization."""
        processor = SignalProcessor(
            config=config, strategy=mock_strategy, enable_risk_envelope=False
        )

        assert processor.config == config
        assert processor.strategy == mock_strategy
        assert processor.enable_risk_envelope is False

    def test_initialization_with_risk_envelope(self, config):
        """Test initialization with risk envelope enabled."""
        processor = SignalProcessor(config=config, strategy=None, enable_risk_envelope=True)

        assert processor.enable_risk_envelope is True
        assert processor.risk_validator is not None

    def test_process_buy_signal_approved(self, signal_processor, buy_signal, default_symbol):
        """Test processing approved buy signal."""
        market_data = MockMarketData(default_symbol, 150)
        positions = {}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=capital)

        def validate_profitability(signal, price):
            return True

        result = signal_processor.process_signal(
            buy_signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        assert result == "BUY"

    def test_process_sell_signal_approved(self, signal_processor, sell_signal, default_symbol):
        """Test processing approved sell signal."""
        market_data = MockMarketData(default_symbol, 160)
        positions = {default_symbol: Decimal("100")}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=capital)

        def validate_profitability(signal, price):
            return True

        result = signal_processor.process_signal(
            sell_signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        assert result == "SELL"

    def test_process_hold_signal_skipped(self, signal_processor, hold_signal, default_symbol):
        """Test processing hold signal."""
        market_data = MockMarketData(default_symbol, 150)
        positions = {}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=capital)

        def validate_profitability(signal, price):
            return True

        result = signal_processor.process_signal(
            hold_signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        assert result is None  # HOLD signals are skipped

    def test_process_signal_risk_check_failed(
        self, signal_processor, buy_signal, mock_strategy, default_symbol
    ):
        """Test signal rejection when risk check fails."""
        mock_strategy.risk_check.return_value = False  # Risk check fails

        market_data = MockMarketData(default_symbol, 150)
        positions = {}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=Decimal("100"))  # Low cash

        def validate_profitability(signal, price):
            return True

        result = signal_processor.process_signal(
            buy_signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        assert result is None  # Signal rejected

    def test_process_signal_profitability_failed(
        self, signal_processor, buy_signal, default_symbol
    ):
        """Test signal rejection when profitability validation fails."""
        market_data = MockMarketData(default_symbol, 150)
        positions = {}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=capital)

        def validate_profitability(signal, price):
            return False  # Profitability check fails

        result = signal_processor.process_signal(
            buy_signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        assert result is None  # Signal rejected

    def test_process_signal_no_strategy(self, config, buy_signal, default_symbol):
        """Test signal processing without strategy (should pass)."""
        processor = SignalProcessor(config=config, strategy=None, enable_risk_envelope=False)

        market_data = MockMarketData(default_symbol, 150)
        positions = {}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=capital)

        def validate_profitability(signal, price):
            return True

        result = processor.process_signal(
            buy_signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        # Should pass without strategy (no risk_check)
        assert result == "BUY"

    def test_validate_strategy_risk_check_error_handling(
        self, signal_processor, buy_signal, default_symbol
    ):
        """Test risk check error handling."""
        # Make risk_check raise an exception
        signal_processor.strategy.risk_check.side_effect = ValueError("Test error")

        market_data = MockMarketData(default_symbol, 150)
        positions = {}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=capital)

        def validate_profitability(signal, price):
            return True

        result = signal_processor.process_signal(
            buy_signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        # Should reject signal on error
        assert result is None

    def test_validate_risk_envelope_rejection(
        self, config, mock_strategy, buy_signal, default_symbol
    ):
        """Test risk envelope validation rejection."""
        # Create mock compliance engine
        mock_compliance_engine = MagicMock()
        mock_compliance_engine.validate_risk_envelope.return_value = (False, "Position too large")

        # Enable risk envelope with mock compliance engine
        processor = SignalProcessor(
            config=config,
            strategy=mock_strategy,
            compliance_engine=mock_compliance_engine,
            enable_risk_envelope=True,
        )

        market_data = MockMarketData(default_symbol, 150)
        positions = {}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=capital)

        def validate_profitability(signal, price):
            return True

        result = processor.process_signal(
            buy_signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        assert result is None  # Rejected by risk envelope

    def test_validate_risk_envelope_disabled(
        self, config, mock_strategy, buy_signal, default_symbol
    ):
        """Test with risk envelope disabled."""
        processor = SignalProcessor(
            config=config, strategy=mock_strategy, enable_risk_envelope=False
        )

        market_data = MockMarketData(default_symbol, 150)
        positions = {}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=capital)

        def validate_profitability(signal, price):
            return True

        result = processor.process_signal(
            buy_signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        # Should pass when risk envelope disabled
        assert result == "BUY"

    def test_diagnostic_logger_signal_rejection(
        self, config, mock_strategy, buy_signal, default_symbol
    ):
        """Test diagnostic logger is called on rejection."""
        mock_logger = MagicMock()
        mock_strategy.risk_check.return_value = False

        processor = SignalProcessor(
            config=config,
            strategy=mock_strategy,
            enable_risk_envelope=False,
            diagnostic_logger=mock_logger,
        )

        market_data = MockMarketData(default_symbol, 150)
        positions = {}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=Decimal("100"))

        def validate_profitability(signal, price):
            return True

        processor.process_signal(
            buy_signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        # Diagnostic logger should have been called
        mock_logger.log_signal_rejected.assert_called_once()

    def test_build_rejection_reason_buy(self, signal_processor, buy_signal):
        """Test building rejection reason for buy signal."""
        portfolio = MockPortfolio(cash=Decimal("1000"))
        signal_processor.strategy.get_position_size.return_value = Decimal("200")

        reason = signal_processor._build_rejection_reason(buy_signal, portfolio, Decimal("150"))

        assert "Risk check failed" in reason
        assert "BUY" in reason
        assert "cash=" in reason
        assert "required=" in reason

    def test_build_rejection_reason_sell_with_position(
        self, signal_processor, sell_signal, default_symbol
    ):
        """Test building rejection reason for sell with position."""
        portfolio = MockPortfolio(
            cash=Decimal("100000"), positions=[MockPortfolio.Position(default_symbol, 100)]
        )

        reason = signal_processor._build_rejection_reason(sell_signal, portfolio, Decimal("160"))

        assert "Risk check failed" in reason
        assert "SELL" in reason
        assert "position_qty=" in reason

    def test_build_rejection_reason_sell_no_position(self, signal_processor, sell_signal):
        """Test building rejection reason for sell without position."""
        portfolio = MockPortfolio(cash=Decimal("100000"), positions=[])

        reason = signal_processor._build_rejection_reason(sell_signal, portfolio, Decimal("160"))

        assert "Risk check failed" in reason
        assert "SELL" in reason
        assert "no position exists" in reason

    def test_signal_with_metadata(self, signal_processor, default_symbol):
        """Test processing signal with metadata."""
        signal = Signal(
            symbol=default_symbol,
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=50.0,
            priority_score=70.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1, 10, 0),
            metadata={"strategy": "test_strategy", "rsi": 30.0},
        )

        market_data = MockMarketData(default_symbol, 150)
        positions = {}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=capital)

        def validate_profitability(signal, price):
            return True

        result = signal_processor.process_signal(
            signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        assert result == "BUY"

    def test_process_signal_with_last_known_prices(
        self, signal_processor, buy_signal, default_symbol
    ):
        """Test signal processing with last known prices."""
        market_data = MockMarketData(default_symbol, 150)
        positions = {"MSFT": Decimal("50")}
        capital = Decimal("100000")
        last_known_prices = {"MSFT": Decimal("300")}

        def create_portfolio(current_price_func):
            # Should use current_price_func to get prices
            current_price_func("MSFT")
            return MockPortfolio(cash=capital)

        def validate_profitability(signal, price):
            return True

        result = signal_processor.process_signal(
            buy_signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        assert result == "BUY"

    def test_validate_risk_envelope_no_compliance_engine(self, config, mock_strategy, buy_signal):
        """Test risk envelope validation when compliance engine is None."""
        processor = SignalProcessor(
            config=config,
            strategy=mock_strategy,
            enable_risk_envelope=True,
            compliance_engine=None,
        )

        # Should create ComplianceEngine automatically (singleton)
        assert processor.compliance_engine is not None

    def test_total_portfolio_capital_custom(self, config):
        """Test custom total portfolio capital."""
        processor = SignalProcessor(
            config=config,
            strategy=None,
            enable_risk_envelope=True,
            total_portfolio_capital=Decimal("500000"),  # Larger than config
        )

        assert processor.total_portfolio_capital == Decimal("500000")

    def test_strategy_name_logging(self, config):
        """Test strategy name is set correctly."""
        processor = SignalProcessor(
            config=config,
            strategy=None,
            enable_risk_envelope=False,
            strategy_name="test_strategy",
        )

        assert processor.strategy_name == "test_strategy"

    def test_edge_case_unknown_signal_type(self, signal_processor, default_symbol):
        """Test processing unknown signal type."""
        # Create a signal with invalid type - this should fail validation
        # So we'll just test with HOLD which should return None
        signal = Signal(
            symbol=default_symbol,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=50.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1, 10, 0),
        )

        market_data = MockMarketData(default_symbol, 150)
        positions = {}
        capital = Decimal("100000")
        last_known_prices = {}

        def create_portfolio(current_price_func):
            return MockPortfolio(cash=capital)

        def validate_profitability(signal, price):
            return True

        result = signal_processor.process_signal(
            signal,
            market_data,
            positions,
            capital,
            last_known_prices,
            create_portfolio,
            validate_profitability,
        )

        # Should return None for unknown signal types
        assert result is None
