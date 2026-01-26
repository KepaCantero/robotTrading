"""
FIFO Trading Database Schema - Spain Tax Compliance (Modelo 721)

CRITICAL FOR SPAIN RESIDENTS:
- Modelo 720: Foreign assets > €50k
- Modelo 721: Cryptocurrency holdings (ANY amount)
- FIFO tracking: MANDATORY for Hacienda
- Multi-exchange tracking: Binance, Coinbase, Kraken, Ledger, etc.

Architecture:
- PostgreSQL for relational data (trades, lots)
- TimescaleDB extension for time-series (prices, balances)
- Immutable audit trail (Hacienda puede auditar)

Phase 0.3: Timezone Awareness
- All timestamps use timezone-aware datetime
- Exchange timezone tracking (for Phase 3 implementation)

Author: Claude (Multi-Market Expansion)
Date: 2025-01-25
Status: DESIGN PHASE - Not implemented
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================


class AssetType(str, Enum):
    """Tipo de activo para Modelo 721/720"""

    CRYPTO = "crypto"  # Modelo 721
    STOCK_US = "stock_us"  # Modelo 720
    STOCK_EU = "stock_eu"  # No reporting (UE)
    FOREX = "forex"  # Modelo 720
    ETF = "etf"  # Modelo 720


class ExchangeType(str, Enum):
    """Tipo de exchange/plataforma"""

    CEX = "cex"  # Centralized (Binance, Coinbase)
    DEX = "dex"  # Decentralized (Uniswap)
    BROKER = "broker"  # Traditional broker (IBKR, Degiro)
    WALLET = "wallet"  # Hardware wallet (Ledger, Trezor)
    OTC = "otc"  # Over-the-counter


class TransactionType(str, Enum):
    """Tipo de transacción"""

    BUY = "buy"
    SELL = "sell"
    TRANSFER_IN = "transfer_in"  # Deposit to exchange
    TRANSFER_OUT = "transfer_out"  # Withdraw from exchange
    STAKING_REWARD = "staking_reward"  # Staking income
    MINING_REWARD = "mining_reward"  # Mining income
    AIRDROP = "airdrop"  # Airdrop (taxable event!)
    FORK = "fork"  # Chain split (taxable event!)
    FEE = "fee"  # Trading fee
    GAS = "gas"  # Network fee


class LotStatus(str, Enum):
    """Estado de un lote FIFO"""

    OPEN = "open"  # Disponible para vender
    CLOSED = "closed"  # Vendido completamente
    PARTIAL = "partial"  # Vendido parcialmente


# ============================================================================
# TABLES
# ============================================================================


class Account(Base):
    """
    Cuenta de trading/broker.

    Una cuenta = Un exchange + Un currency.

    Ejemplo:
    - Binance BTC wallet
    - Coinbase EUR wallet
    - Ledger ETH wallet
    - IBKR USD account
    """

    __tablename__ = "accounts"

    # Primary key
    id: UUID = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identification
    user_id: UUID = sa.Column(UUID(as_uuid=True), nullable=False, index=True)
    account_name: str = sa.Column(sa.String(100), nullable=False)
    exchange_type: ExchangeType = sa.Column(sa.Enum(ExchangeType), nullable=False)
    exchange_name: str = sa.Column(sa.String(100), nullable=False)  # "Binance", "Coinbase", "IBKR"

    # Currency
    currency: str = sa.Column(sa.String(10), nullable=False)  # "BTC", "ETH", "EUR", "USD"

    # Account details (encrypted at rest)
    api_key_encrypted: Optional[str] = sa.Column(sa.Text, nullable=True)
    api_secret_encrypted: Optional[str] = sa.Column(sa.Text, nullable=True)
    wallet_address: Optional[str] = sa.Column(sa.String(255), nullable=True)  # For DEX/Wallets

    # Balance tracking
    balance_cached: Decimal = sa.Column(sa.Numeric(36, 18), default=Decimal("0"))
    balance_updated_at: Optional[datetime] = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    last_sync_at: Optional[datetime] = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    # Metadata
    is_active: bool = sa.Column(sa.Boolean, default=True)
    created_at: datetime = sa.Column(
        sa.TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    closed_at: Optional[datetime] = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    # JSON for extra fields
    meta_data: Dict = sa.Column(JSONB, default=dict)

    # Relationships
    transactions = sa.orm.relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )
    lots = sa.orm.relationship("Lot", back_populates="account", cascade="all, delete-orphan")
    balances = sa.orm.relationship(
        "BalanceSnapshot", back_populates="account", cascade="all, delete-orphan"
    )

    __table_args__ = (
        sa.Index('idx_accounts_user_active', 'user_id', 'is_active'),
        sa.Index('idx_accounts_exchange_currency', 'exchange_name', 'currency'),
    )


class Transaction(Base):
    """
    Transacción individual con tracking FIFO.

    CRITICAL: Cada transacción debe ser inmutable para auditoría.
    """

    __tablename__ = "transactions"

    # Primary key
    id: UUID = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # External ID (from exchange) - PREVENTS DUPLICATES
    external_id: str = sa.Column(sa.String(255), nullable=False, index=True)
    exchange_tx_id: Optional[str] = sa.Column(
        sa.String(255), nullable=True
    )  # Raw TX hash for crypto

    # Account
    account_id: UUID = sa.Column(UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=False)
    account = sa.orm.relationship("Account", back_populates="transactions")

    # Asset
    asset_type: AssetType = sa.Column(sa.Enum(AssetType), nullable=False)
    symbol: str = sa.Column(sa.String(20), nullable=False, index=True)  # "BTC", "AAPL", "EURUSD"

    # Transaction details
    tx_type: TransactionType = sa.Column(sa.Enum(TransactionType), nullable=False)
    side: Optional[str] = sa.Column(sa.String(10), nullable=True)  # "BUY", "SELL" (for trades)

    # Quantities - ALWAYS DECIMAL
    quantity: Decimal = sa.Column(sa.Numeric(36, 18), nullable=False)
    quantity_symbol: str = sa.Column(sa.String(20), nullable=False)  # "BTC", "USD"

    # Prices - ALWAYS DECIMAL
    price: Optional[Decimal] = sa.Column(sa.Numeric(36, 18), nullable=True)  # Unit price
    total_value: Optional[Decimal] = sa.Column(
        sa.Numeric(36, 18), nullable=True
    )  # quantity * price

    # Fees - CRITICAL FOR TAX BASIS
    fee_amount: Decimal = sa.Column(sa.Numeric(36, 18), default=Decimal("0"))
    fee_currency: str = sa.Column(sa.String(10), nullable=False)
    fee_included: bool = sa.Column(sa.Boolean, default=False)  # If fee is included in total_value

    # Timestamps - TIMEZONE AWARE
    occurred_at: datetime = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False, index=True)
    recorded_at: datetime = sa.Column(
        sa.TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Settlement (for stocks/forex)
    settled_at: Optional[datetime] = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    settlement_date: Optional[datetime] = sa.Column(sa.DATE, nullable=True)

    # FIFO linking
    lot_id: Optional[UUID] = sa.Column(UUID(as_uuid=True), sa.ForeignKey('lots.id'), nullable=True)
    lot = sa.orm.relationship("Lot", back_populates="transactions", foreign_keys=[lot_id])

    # Tax-related fields
    is_taxable: bool = sa.Column(sa.Boolean, default=True)
    tax_year: int = sa.Column(
        sa.Integer, nullable=True, index=True
    )  # For Modelo 721 annual filtering

    # Counterparty (for transfers)
    from_account_id: Optional[UUID] = sa.Column(
        UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=True
    )
    to_account_id: Optional[UUID] = sa.Column(
        UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=True
    )
    from_address: Optional[str] = sa.Column(sa.String(255), nullable=True)  # Crypto address
    to_address: Optional[str] = sa.Column(sa.String(255), nullable=True)  # Crypto address

    # Metadata
    notes: Optional[str] = sa.Column(sa.Text, nullable=True)
    meta_data: Dict = sa.Column(JSONB, default=dict)

    # Audit fields
    created_at: datetime = sa.Column(
        sa.TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = sa.Column(
        sa.TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    is_verified: bool = sa.Column(sa.Boolean, default=False)  # Verified against exchange API

    __table_args__ = (
        sa.UniqueConstraint('external_id', 'account_id', name='uq_tx_external_account'),
        sa.Index('idx_transactions_symbol_type', 'symbol', 'tx_type'),
        sa.Index('idx_transactions_occurred', 'occurred_at'),
        sa.Index('idx_transactions_tax_year', 'tax_year'),
    )

    @hybrid_property
    def cost_basis(self) -> Decimal:
        """
        Cost basis para cálculo fiscal.

        Para BUY: total_value + fees
        Para SELL: Se calcula basado en lotes FIFO cerrados
        """
        if self.tx_type == TransactionType.BUY:
            return (self.total_value or Decimal("0")) + self.fee_amount
        elif self.tx_type == TransactionType.SELL:
            # Cost basis comes from closed lots
            # This is calculated during lot closure
            return self.meta_data.get('cost_basis_from_lots', Decimal("0"))
        else:
            return Decimal("0")


class Lot(Base):
    """
    Lote FIFO para tracking de cost basis.

    Cada BUY crea uno o más lotes.
    Cada SELL cierra lotes en orden FIFO.
    """

    __tablename__ = "lots"

    # Primary key
    id: UUID = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Account
    account_id: UUID = sa.Column(UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=False)
    account = sa.orm.relationship("Account", back_populates="lots")

    # Asset
    symbol: str = sa.Column(sa.String(20), nullable=False, index=True)
    asset_type: AssetType = sa.Column(sa.Enum(AssetType), nullable=False)

    # Original purchase (cost basis)
    opening_transaction_id: UUID = sa.Column(
        UUID(as_uuid=True), sa.ForeignKey('transactions.id'), nullable=False
    )
    quantity_opened: Decimal = sa.Column(sa.Numeric(36, 18), nullable=False)
    cost_basis_open: Decimal = sa.Column(
        sa.Numeric(36, 18), nullable=False
    )  # Total cost (price + fees)

    # Current status
    quantity_remaining: Decimal = sa.Column(sa.Numeric(36, 18), nullable=False)
    status: LotStatus = sa.Column(sa.Enum(LotStatus), default=LotStatus.OPEN, nullable=False)

    # Realized gains (when closed)
    realized_gain: Optional[Decimal] = sa.Column(sa.Numeric(36, 18), nullable=True)
    realized_loss: Optional[Decimal] = sa.Column(sa.Numeric(36, 18), nullable=True)

    # Dates
    opened_at: datetime = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False)
    closed_at: Optional[datetime] = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    # Holding period (for tax classification)
    holding_period_days: Optional[int] = sa.Column(sa.Integer, nullable=True)

    # Tax year (when closed)
    tax_year_closed: Optional[int] = sa.Column(sa.Integer, nullable=True)

    # Relationships
    transactions = sa.orm.relationship(
        "Transaction", back_populates="lot", foreign_keys=[Transaction.lot_id]
    )

    # Metadata
    meta_data: Dict = sa.Column(JSONB, default=dict)

    __table_args__ = (
        sa.Index('idx_lots_symbol_status', 'symbol', 'status'),
        sa.Index('idx_lots_opened', 'opened_at'),
        sa.CheckConstraint('quantity_remaining >= 0', name='ck_lot_remaining_positive'),
        sa.CheckConstraint(
            'quantity_remaining <= quantity_opened', name='ck_lot_remaining_le_opened'
        ),
    )

    @hybrid_property
    def is_long_term(self) -> Optional[bool]:
        """True if holding period > 1 year (for Spain LT tax rate)"""
        if self.closed_at is None:
            return None
        return (self.closed_at - self.opened_at).days >= 365


class BalanceSnapshot(Base):
    """
    Snapshot de balance para tracking histórico.

    Necesario para Modelo 721 (valor a 31 de diciembre).
    """

    __tablename__ = "balance_snapshots"

    # Primary key
    id: UUID = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Account
    account_id: UUID = sa.Column(UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=False)
    account = sa.orm.relationship("Account", back_populates="balances")

    # Snapshot details
    snapshot_type: str = sa.Column(sa.String(20), nullable=False)  # "eod", "monthly", "annual"
    balance: Decimal = sa.Column(sa.Numeric(36, 18), nullable=False)

    # Valuation in EUR (for Modelo 721)
    balance_eur: Decimal = sa.Column(sa.Numeric(36, 18), nullable=False)  # Converted to EUR
    exchange_rate_eur: Decimal = sa.Column(sa.Numeric(18, 8), nullable=False)  # Rate used

    # Timestamp
    captured_at: datetime = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False, index=True)

    # Source
    source: str = sa.Column(sa.String(50), nullable=False)  # "api", "manual", "estimated"

    __table_args__ = (
        sa.Index('idx_balances_account_captured', 'account_id', 'captured_at'),
        sa.Index('idx_balances_annual', 'account_id', sa.text("date_trunc('year', captured_at)")),
    )


class TaxReport(Base):
    """
    Reporte fiscal generado (Modelo 721/720).

    Cada reporte es inmutable para auditoría.
    """

    __tablename__ = "tax_reports"

    # Primary key
    id: UUID = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User
    user_id: UUID = sa.Column(UUID(as_uuid=True), nullable=False, index=True)

    # Report type
    report_type: str = sa.Column(sa.String(20), nullable=False)  # "modelo_720", "modelo_721"
    tax_year: int = sa.Column(sa.Integer, nullable=False)

    # Report data (JSON for flexibility)
    report_data: Dict = sa.Column(JSONB, nullable=False)

    # Summary fields (for easy querying)
    total_holdings_eur: Decimal = sa.Column(sa.Numeric(36, 18), nullable=False)
    total_gain_eur: Decimal = sa.Column(sa.Numeric(36, 18), nullable=False)
    total_loss_eur: Decimal = sa.Column(sa.Numeric(36, 18), nullable=False)

    # Status
    status: str = sa.Column(sa.String(20), default="draft")  # "draft", "final", "filed"
    is_amended: bool = sa.Column(sa.Boolean, default=False)
    amended_from_id: Optional[UUID] = sa.Column(UUID(as_uuid=True), nullable=True)

    # Dates
    report_date: datetime = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False)  # As of date
    generated_at: datetime = sa.Column(
        sa.TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    filed_at: Optional[datetime] = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    # Validation
    checksum: str = sa.Column(sa.String(64), nullable=True)  # SHA-256 of report_data

    __table_args__ = (
        sa.UniqueConstraint(
            'user_id',
            'report_type',
            'tax_year',
            'is_amended',
            name='uq_tax_report_user_type_year_amended',
        ),
        sa.Index('idx_tax_reports_user_year', 'user_id', 'tax_year'),
    )


# ============================================================================
# FIFO CALCULATOR
# ============================================================================


@dataclass
class FIFOCalculation:
    """
    Resultado de cálculo FIFO.

    Para cada venta, calcula:
    1. Qué lotes se cierran (en orden FIFO)
    2. Cost basis de esos lotes
    3. Gain/Loss realizados
    """

    symbol: str
    sell_transaction_id: UUID
    quantity_sold: Decimal
    lots_closed: List[UUID]  # Lot IDs closed
    cost_basis: Decimal
    proceeds: Decimal
    gain: Decimal
    loss: Decimal
    holding_period_days: int


class FIFOProcessor:
    """
    Procesador FIFO para cálculo fiscal.

    Lógica:
    1. Para cada BUY → Crear nuevo lot
    2. Para cada SELL → Cerrar lotes en orden FIFO
    3. Para TRANSFER → Rastrear cost basis entre cuentas
    """

    def __init__(self, session):
        self.session = session

    def process_buy(self, transaction: Transaction) -> Lot:
        """
        Procesar compra → Crear nuevo lote.

        Args:
            transaction: BUY transaction

        Returns:
            Lot creado
        """
        lot = Lot(
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            asset_type=transaction.asset_type,
            opening_transaction_id=transaction.id,
            quantity_opened=transaction.quantity,
            cost_basis_open=transaction.cost_basis,
            quantity_remaining=transaction.quantity,
            status=LotStatus.OPEN,
            opened_at=transaction.occurred_at,
        )
        self.session.add(lot)
        self.session.flush()
        return lot

    def process_sell(self, transaction: Transaction, strict_fifo: bool = True) -> FIFOCalculation:
        """
        Procesar venta → Cerrar lotes FIFO.

        Args:
            transaction: SELL transaction
            strict_fifo: Si True, error si no hay suficientes lotes

        Returns:
            FIFOCalculation con details

        Raises:
            ValueError: Si no hay suficientes lotes disponibles
        """
        # Query open lots for this symbol, ordered by opened_at (FIFO)
        open_lots = (
            self.session.query(Lot)
            .filter(
                Lot.account_id == transaction.account_id,
                Lot.symbol == transaction.symbol,
                Lot.status == LotStatus.OPEN,
                Lot.quantity_remaining > 0,
            )
            .order_by(Lot.opened_at)  # FIFO = oldest first
            .all()
        )

        quantity_to_close = transaction.quantity
        lots_closed = []
        total_cost_basis = Decimal("0")
        total_quantity_closed = Decimal("0")

        for lot in open_lots:
            if quantity_to_close <= 0:
                break

            # How much of this lot to close?
            close_from_lot = min(quantity_to_close, lot.quantity_remaining)

            # Update lot
            lot.quantity_remaining -= close_from_lot
            total_cost_basis += (lot.cost_basis_open / lot.quantity_opened) * close_from_lot

            # If lot fully closed
            if lot.quantity_remaining == 0:
                lot.status = LotStatus.CLOSED
                lot.closed_at = transaction.occurred_at
                lot.holding_period_days = (transaction.occurred_at - lot.opened_at).days
                lot.tax_year_closed = transaction.occurred_at.year

            lots_closed.append(lot.id)
            quantity_to_close -= close_from_lot
            total_quantity_closed += close_from_lot

        # Validation
        if quantity_to_close > 0 and strict_fifo:
            raise ValueError(
                f"Insufficient lots to sell {transaction.quantity} {transaction.symbol}. "
                f"Missing {quantity_to_close}. Available: {sum([l.quantity_remaining for l in open_lots])}"
            )

        # Calculate gain/loss
        proceeds = transaction.total_value or Decimal("0")
        gain = max(Decimal("0"), proceeds - total_cost_basis)
        loss = max(Decimal("0"), total_cost_basis - proceeds)

        # Create FIFO calculation record
        fifo_calc = FIFOCalculation(
            symbol=transaction.symbol,
            sell_transaction_id=transaction.id,
            quantity_sold=total_quantity_closed,
            lots_closed=lots_closed,
            cost_basis=total_cost_basis,
            proceeds=proceeds,
            gain=gain,
            loss=loss,
            holding_period_days=0,  # Weighted average could be calculated
        )

        # Link transaction to lots
        transaction.meta_data['fifo_calculation'] = {
            'lots_closed': lots_closed,
            'cost_basis': str(total_cost_basis),
            'gain': str(gain),
            'loss': str(loss),
        }

        return fifo_calc

    def process_transfer(
        self, transaction: Transaction, from_account: Account, to_account: Account
    ) -> None:
        """
        Procesar transferencia entre cuentas/exchanges.

        CRITICAL: Mantener cost basis original.

        Args:
            transaction: TRANSFER_OUT transaction
            from_account: Source account
            to_account: Destination account
        """
        # For tracking, we create a "virtual" lot in the destination
        # with the SAME cost basis as the source

        # Find the lot(s) being transferred
        # This requires tracking which specific BTC/ETH are moving
        # Implementation depends on whether exchange reports this granularity

        # For now, create a placeholder lot in destination


# ============================================================================
# MODELO 721 GENERATOR
# ============================================================================


class Modelo721Generator:
    """
    Generador de datos para Modelo 721 (Criptomonedas).

    Requerimientos Hacienda:
    - Saldo a 31 de diciembre de cada criptomoneda
    - Valor en EUR (usando tipo de cambio oficial)
    - Identificación de exchanges utilizados
    - Fecha y hora de cada transacción
    """

    def __init__(self, session):
        self.session = session

    def generate_annual_report(self, user_id: UUID, year: int) -> TaxReport:
        """
        Generar reporte Modelo 721 para un año.

        Args:
            user_id: User UUID
            year: Año fiscal

        Returns:
            TaxReport con datos completos
        """
        # Get all crypto accounts
        crypto_accounts = (
            self.session.query(Account)
            .filter(
                Account.user_id == user_id,
                Account.asset_type == AssetType.CRYPTO,
                Account.is_active == True,
            )
            .all()
        )

        # For each symbol, calculate balance at Dec 31
        balances = {}

        for account in crypto_accounts:
            # Get last snapshot of the year
            snapshot = (
                self.session.query(BalanceSnapshot)
                .filter(
                    BalanceSnapshot.account_id == account.id,
                    sa.extract('year', BalanceSnapshot.captured_at) == year,
                )
                .order_by(sa.desc(BalanceSnapshot.captured_at))
                .first()
            )

            if snapshot:
                symbol = account.currency
                if symbol not in balances:
                    balances[symbol] = Decimal("0")
                balances[symbol] += snapshot.balance_eur

        # Calculate total gains/losses for the year
        closed_lots = (
            self.session.query(Lot)
            .filter(
                Lot.account_id.in_([a.id for a in crypto_accounts]),
                Lot.tax_year_closed == year,
                Lot.status == LotStatus.CLOSED,
            )
            .all()
        )

        total_gain = sum([lot.realized_gain or Decimal("0") for lot in closed_lots])
        total_loss = sum([lot.realized_loss or Decimal("0") for lot in closed_lots])

        # Create report
        report = TaxReport(
            user_id=user_id,
            report_type="modelo_721",
            tax_year=year,
            report_data={
                "balances_by_symbol": {k: str(v) for k, v in balances.items()},
                "total_holdings_eur": str(sum(balances.values())),
                "exchanges_used": [a.exchange_name for a in crypto_accounts],
                "closed_transactions": len(closed_lots),
            },
            total_holdings_eur=sum(balances.values()),
            total_gain_eur=total_gain,
            total_loss_eur=total_loss,
            report_date=datetime(year, 12, 31),
        )

        return report


# ============================================================================
# ALEMBIC MIGRATIONS
# ============================================================================

"""
Ejecutar para crear las tablas:

    alembic revision --autogenerate -m "Add FIFO tracking for Modelo 721"
    alembic upgrade head

Requisitos previos:
    pip install sqlalchemy psycopg2-binary alembic
"""
