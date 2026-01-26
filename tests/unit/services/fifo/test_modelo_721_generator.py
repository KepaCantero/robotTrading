"""
Unit tests for Modelo721Generator service.

Tests Modelo 721 report generation for Spain tax compliance.
"""

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.services.fifo.modelo_721_generator import (
    CapitalGainLoss,
    CryptoBalance,
    Modelo721Generator,
    Modelo721Report,
    TransactionDetail,
)


@pytest.fixture
def modelo_721_generator():
    """Create Modelo 721 generator instance."""
    return Modelo721Generator(user_id=uuid4())


@pytest.fixture
def sample_crypto_balance():
    """Create sample crypto balance."""
    return CryptoBalance(
        symbol="BTC",
        quantity=Decimal("0.5"),
        balance_eur=Decimal("20000.00"),
        exchange_rate_eur=Decimal("40000.00"),
        exchanges=["binance", "ledger"],
        captured_at=datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_transaction_detail():
    """Create sample transaction detail."""
    return TransactionDetail(
        occurred_at=datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc),
        symbol="BTC",
        tx_type="buy",
        quantity=Decimal("0.25"),
        total_value_eur=Decimal("10000.00"),
        exchange_name="binance",
        tx_hash="0x123abc...",
    )


@pytest.fixture
def sample_capital_gain_loss():
    """Create sample capital gain/loss."""
    return CapitalGainLoss(
        symbol="BTC",
        tax_year=2024,
        lots_closed=2,
        total_proceeds=Decimal("15000.00"),
        total_cost_basis=Decimal("10000.00"),
        net_gain=Decimal("5000.00"),
        net_loss=Decimal("0"),
        long_term_gain=Decimal("4000.00"),
        short_term_gain=Decimal("1000.00"),
    )


class TestModelo721Generator:
    """Test suite for Modelo721Generator."""

    def test_initialization(self, modelo_721_generator):
        """Test generator initialization."""
        assert modelo_721_generator is not None
        assert modelo_721_generator.user_id is not None


class TestCryptoBalance:
    """Test suite for CryptoBalance dataclass."""

    def test_crypto_balance_creation(self, sample_crypto_balance):
        """Test crypto balance creation."""
        assert sample_crypto_balance.symbol == "BTC"
        assert sample_crypto_balance.quantity == Decimal("0.5")
        assert sample_crypto_balance.balance_eur == Decimal("20000.00")
        assert "binance" in sample_crypto_balance.exchanges


class TestTransactionDetail:
    """Test suite for TransactionDetail dataclass."""

    def test_transaction_detail_creation(self, sample_transaction_detail):
        """Test transaction detail creation."""
        assert sample_transaction_detail.symbol == "BTC"
        assert sample_transaction_detail.tx_type == "buy"
        assert sample_transaction_detail.quantity == Decimal("0.25")


class TestCapitalGainLoss:
    """Test suite for CapitalGainLoss dataclass."""

    def test_capital_gain_loss_creation(self, sample_capital_gain_loss):
        """Test capital gain/loss creation."""
        assert sample_capital_gain_loss.symbol == "BTC"
        assert sample_capital_gain_loss.tax_year == 2024
        assert sample_capital_gain_loss.lots_closed == 2

    def test_net_calculation(self, sample_capital_gain_loss):
        """Test net gain/loss calculation."""
        # Net should be proceeds - cost basis
        expected_net = Decimal("15000.00") - Decimal("10000.00")
        assert sample_capital_gain_loss.net_gain == expected_net
        assert sample_capital_gain_loss.net_loss == Decimal("0")


class TestModelo721Report:
    """Test suite for Modelo721Report dataclass."""

    @pytest.fixture
    def sample_report(self, sample_crypto_balance, sample_capital_gain_loss):
        """Create sample Modelo 721 report."""
        return Modelo721Report(
            tax_year=2024,
            user_id=uuid4(),
            report_date=date(2024, 12, 31),
            generated_at=datetime.now(timezone.utc),
            dec31_balances=[sample_crypto_balance],
            total_holdings_eur=Decimal("20000.00"),
            transactions=[],
            total_transactions=0,
            capital_gains_losses=[sample_capital_gain_loss],
            total_gain_eur=Decimal("5000.00"),
            total_loss_eur=Decimal("0"),
            net_gain_loss_eur=Decimal("5000.00"),
            exchanges_used=["binance", "ledger"],
        )

    def test_report_creation(self, sample_report):
        """Test report creation."""
        assert sample_report.tax_year == 2024
        assert len(sample_report.dec31_balances) == 1
        assert sample_report.total_holdings_eur == Decimal("20000.00")

    def test_report_to_dict(self, sample_report):
        """Test report serialization to dictionary."""
        report_dict = sample_report.to_dict()

        assert report_dict["tax_year"] == 2024
        assert "dec31_balances" in report_dict
        assert "total_gain_eur" in report_dict
        assert len(report_dict["dec31_balances"]) == 1
