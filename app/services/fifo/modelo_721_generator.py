"""
Modelo 721 Generator - Spain Tax Report Generator

Generates Modelo 721 reports for Hacienda (Spanish tax authority).

CRITICAL FOR SPAIN RESIDENTS:
- Modelo 721: MANDATORY reporting of cryptocurrency holdings
- Applies to ALL crypto holdings (no minimum threshold)
- Due date: January 1 - March 31 of the following year
- Reporting period: January 1 - December 31 (previous calendar year)
- Required: Saldo a 31 de diciembre (balance on December 31st)
- Required: Valor en EUR (value in Euros using official exchange rates)
- Required: Identificación de exchanges (exchange identification)
- Required: Fecha y hora de cada transacción (date and time of each transaction)

This module provides:
1. Annual report generation
2. Dec 31 balance snapshots for crypto holdings
3. Capital gains calculations
4. CSV export format for Hacienda submission

Author: Claude (FIFO Database Integration - Phase 2.1)
Date: 2026-01-25
"""

import csv
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_transaction
from app.tax.database.fifo_schema import (
    Account,
    AssetType,
    BalanceSnapshot,
    Lot,
    LotStatus,
    TaxReport,
    Transaction,
    TransactionType,
)

logger = logging.getLogger(__name__)


@dataclass
class CryptoBalance:
    """Cryptocurrency balance for Modelo 721."""

    symbol: str
    quantity: Decimal
    balance_eur: Decimal
    exchange_rate_eur: Decimal
    exchanges: List[str]
    captured_at: datetime


@dataclass
class TransactionDetail:
    """Transaction detail for Modelo 721."""

    occurred_at: datetime
    symbol: str
    tx_type: str
    quantity: Decimal
    total_value_eur: Decimal
    exchange_name: str
    tx_hash: Optional[str] = None


@dataclass
class CapitalGainLoss:
    """Capital gain or loss for tax reporting."""

    symbol: str
    tax_year: int
    lots_closed: int
    total_proceeds: Decimal
    total_cost_basis: Decimal
    net_gain: Decimal
    net_loss: Decimal
    long_term_gain: Decimal
    short_term_gain: Decimal


@dataclass
class Modelo721Report:
    """Complete Modelo 721 report."""

    tax_year: int
    user_id: UUID
    report_date: date
    generated_at: datetime

    # Holdings as of December 31
    dec31_balances: List[CryptoBalance]
    total_holdings_eur: Decimal

    # Transactions during the year
    transactions: List[TransactionDetail]
    total_transactions: int

    # Capital gains/losses
    capital_gains_losses: List[CapitalGainLoss]
    total_gain_eur: Decimal
    total_loss_eur: Decimal
    net_gain_loss_eur: Decimal

    # Exchanges used
    exchanges_used: List[str]

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "tax_year": self.tax_year,
            "user_id": str(self.user_id),
            "report_date": self.report_date.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "dec31_balances": [
                {
                    "symbol": b.symbol,
                    "quantity": str(b.quantity),
                    "balance_eur": str(b.balance_eur),
                    "exchange_rate_eur": str(b.exchange_rate_eur),
                    "exchanges": b.exchanges,
                    "captured_at": b.captured_at.isoformat(),
                }
                for b in self.dec31_balances
            ],
            "total_holdings_eur": str(self.total_holdings_eur),
            "total_transactions": self.total_transactions,
            "total_gain_eur": str(self.total_gain_eur),
            "total_loss_eur": str(self.total_loss_eur),
            "net_gain_loss_eur": str(self.net_gain_loss_eur),
            "exchanges_used": self.exchanges_used,
        }


class Modelo721Generator:
    """
    Generate Modelo 721 reports for Hacienda.

    This generator creates comprehensive tax reports for cryptocurrency
    holdings and transactions, compliant with Spanish tax requirements.

    Usage:
        generator = Modelo721Generator()
        report = await generator.generate_annual_report(user_id, 2024)
        csv_path = await generator.export_to_csv(report, "/path/to/output.csv")
    """

    def __init__(self, user_id: Optional[UUID] = None):
        """
        Initialize Modelo 721 generator.

        Args:
            user_id: User UUID for tax reporting
        """
        self.user_id = user_id
        self.logger = logging.getLogger(self.__class__.__name__)

    async def generate_annual_report(
        self, user_id: UUID, year: int, include_dec31_snapshot: bool = True
    ) -> Modelo721Report:
        """
        Generate Modelo 721 report for a tax year.

        Args:
            user_id: User UUID
            year: Tax year (e.g., 2024)
            include_dec31_snapshot: Whether to calculate Dec 31 balances

        Returns:
            Modelo721Report with complete tax information

        Raises:
            ValueError: If year is invalid or no data found
        """
        try:
            self.logger.info(f"Generating Modelo 721 report for user {user_id}, year {year}")

            # Validate year
            if year < 2021 or year > datetime.now().year:
                raise ValueError(f"Invalid tax year: {year}")

            async with get_db_transaction() as session:
                # Get all crypto accounts for user
                accounts = await self._get_crypto_accounts(session, user_id)

                if not accounts:
                    self.logger.warning(f"No crypto accounts found for user {user_id}")
                    return self._create_empty_report(user_id, year)

                # Generate Dec 31 balance snapshots
                dec31_balances = []
                if include_dec31_snapshot:
                    dec31_balances = await self._calculate_dec31_snapshot(session, accounts, year)

                # Get all transactions for the year
                transactions = await self._get_annual_transactions(session, accounts, year)

                # Calculate capital gains/losses
                capital_gains_losses = await self._calculate_capital_gains(session, accounts, year)

                # Calculate totals
                total_holdings_eur = sum(b.balance_eur for b in dec31_balances)
                total_gain = sum(g.net_gain for g in capital_gains_losses)
                total_loss = sum(g.net_loss for g in capital_gains_losses)

                # Get exchanges used
                exchanges_used = list(set(acc.exchange_name for acc in accounts))

                # Create report
                report = Modelo721Report(
                    tax_year=year,
                    user_id=user_id,
                    report_date=date(year, 12, 31),
                    generated_at=datetime.now(timezone.utc),
                    dec31_balances=dec31_balances,
                    total_holdings_eur=total_holdings_eur,
                    transactions=transactions,
                    total_transactions=len(transactions),
                    capital_gains_losses=capital_gains_losses,
                    total_gain_eur=total_gain,
                    total_loss_eur=total_loss,
                    net_gain_loss_eur=total_gain - total_loss,
                    exchanges_used=exchanges_used,
                )

                self.logger.info(
                    f"Modelo 721 report generated: {len(dec31_balances)} holdings, "
                    f"{len(transactions)} transactions, net gain/loss: {total_gain - total_loss} EUR"
                )

                return report

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            self.logger.error(f"Error generating Modelo 721 report: {e}", exc_info=True)
            raise

    async def _get_crypto_accounts(
        self, session: AsyncSession, user_id: UUID
    ) -> List[Account]:
        """Get all crypto accounts for user."""
        stmt = select(Account).where(
            Account.user_id == user_id,
            Account.asset_type == AssetType.CRYPTO,
            Account.is_active == True,
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def _calculate_dec31_snapshot(
        self, session: AsyncSession, accounts: List[Account], year: int
    ) -> List[CryptoBalance]:
        """
        Calculate Dec 31 balance for crypto holdings.

        This is the CRITICAL requirement for Modelo 721: the balance
        and value in EUR as of December 31st of the tax year.

        Args:
            session: Database session
            accounts: List of crypto accounts
            year: Tax year

        Returns:
            List of CryptoBalance objects
        """
        balances = {}

        # Get last snapshot of the year for each account
        for account in accounts:
            stmt = (
                select(BalanceSnapshot)
                .where(
                    BalanceSnapshot.account_id == account.id,
                    extract("year", BalanceSnapshot.captured_at) == year,
                )
                .order_by(BalanceSnapshot.captured_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            snapshot = result.scalars().first()

            if snapshot:
                symbol = account.currency
                if symbol not in balances:
                    balances[symbol] = {
                        "quantity": snapshot.balance,
                        "balance_eur": snapshot.balance_eur,
                        "exchange_rate_eur": snapshot.exchange_rate_eur,
                        "exchanges": [],
                        "captured_at": snapshot.captured_at,
                    }
                else:
                    balances[symbol]["quantity"] += snapshot.balance
                    balances[symbol]["balance_eur"] += snapshot.balance_eur

                if account.exchange_name not in balances[symbol]["exchanges"]:
                    balances[symbol]["exchanges"].append(account.exchange_name)

        # Convert to CryptoBalance objects
        return [
            CryptoBalance(
                symbol=symbol,
                quantity=balances[symbol]["quantity"],
                balance_eur=balances[symbol]["balance_eur"],
                exchange_rate_eur=balances[symbol]["exchange_rate_eur"],
                exchanges=balances[symbol]["exchanges"],
                captured_at=balances[symbol]["captured_at"],
            )
            for symbol in sorted(balances.keys())
        ]

    async def _get_annual_transactions(
        self, session: AsyncSession, accounts: List[Account], year: int
    ) -> List[TransactionDetail]:
        """
        Get all transactions for the tax year.

        Args:
            session: Database session
            accounts: List of accounts
            year: Tax year

        Returns:
            List of TransactionDetail objects
        """
        account_ids = [acc.id for acc in accounts]

        stmt = (
            select(Transaction)
            .where(
                Transaction.account_id.in_(account_ids),
                extract("year", Transaction.occurred_at) == year,
            )
            .order_by(Transaction.occurred_at)
        )

        result = await session.execute(stmt)
        transactions = result.scalars().all()

        return [
            TransactionDetail(
                occurred_at=tx.occurred_at,
                symbol=tx.symbol,
                tx_type=tx.tx_type.value,
                quantity=tx.quantity,
                total_value_eur=tx.total_value or Decimal("0"),
                exchange_name=tx.account.exchange_name,
                tx_hash=tx.exchange_tx_id,
            )
            for tx in transactions
        ]

    async def _calculate_capital_gains(
        self, session: AsyncSession, accounts: List[Account], year: int
    ) -> List[CapitalGainLoss]:
        """
        Calculate capital gains and losses for the tax year.

        Args:
            session: Database session
            accounts: List of accounts
            year: Tax year

        Returns:
            List of CapitalGainLoss objects per symbol
        """
        account_ids = [acc.id for acc in accounts]

        # Get all lots closed during the year
        stmt = select(Lot).where(
            Lot.account_id.in_(account_ids),
            Lot.tax_year_closed == year,
            Lot.status == LotStatus.CLOSED,
        )
        result = await session.execute(stmt)
        lots = result.scalars().all()

        # Group by symbol
        gains_by_symbol: Dict[str, Dict[str, Any]] = {}

        for lot in lots:
            symbol = lot.symbol

            if symbol not in gains_by_symbol:
                gains_by_symbol[symbol] = {
                    "lots_closed": 0,
                    "total_proceeds": Decimal("0"),
                    "total_cost_basis": Decimal("0"),
                    "long_term_gain": Decimal("0"),
                    "short_term_gain": Decimal("0"),
                }

            gains_by_symbol[symbol]["lots_closed"] += 1

            # Get sell transaction for proceeds
            if lot.transactions:
                for tx in lot.transactions:
                    if tx.tx_type == TransactionType.SELL:
                        gains_by_symbol[symbol]["total_proceeds"] += tx.total_value or Decimal(
                            "0"
                        )
                        break

            gains_by_symbol[symbol]["total_cost_basis"] += lot.cost_basis_open

            # Separate long-term vs short-term
            if lot.is_long_term:
                gains_by_symbol[symbol]["long_term_gain"] += lot.realized_gain or Decimal("0")
            else:
                gains_by_symbol[symbol]["short_term_gain"] += lot.realized_gain or Decimal("0")

        # Convert to CapitalGainLoss objects
        return [
            CapitalGainLoss(
                symbol=symbol,
                tax_year=year,
                lots_closed=data["lots_closed"],
                total_proceeds=data["total_proceeds"],
                total_cost_basis=data["total_cost_basis"],
                net_gain=max(Decimal("0"), data["total_proceeds"] - data["total_cost_basis"]),
                net_loss=max(Decimal("0"), data["total_cost_basis"] - data["total_proceeds"]),
                long_term_gain=data["long_term_gain"],
                short_term_gain=data["short_term_gain"],
            )
            for symbol, data in sorted(gains_by_symbol.items())
        ]

    def _create_empty_report(self, user_id: UUID, year: int) -> Modelo721Report:
        """Create an empty report when no data is found."""
        return Modelo721Report(
            tax_year=year,
            user_id=user_id,
            report_date=date(year, 12, 31),
            generated_at=datetime.now(timezone.utc),
            dec31_balances=[],
            total_holdings_eur=Decimal("0"),
            transactions=[],
            total_transactions=0,
            capital_gains_losses=[],
            total_gain_eur=Decimal("0"),
            total_loss_eur=Decimal("0"),
            net_gain_loss_eur=Decimal("0"),
            exchanges_used=[],
        )

    async def export_to_csv(
        self, report: Modelo721Report, output_path: str, format_type: str = "hacienda"
    ) -> str:
        """
        Export Modelo 721 report to CSV format.

        Args:
            report: Modelo721Report to export
            output_path: Path to output CSV file
            format_type: CSV format ("hacienda" or "detailed")

        Returns:
            Path to generated CSV file

        Raises:
            IOError: If file cannot be written
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if format_type == "hacienda":
                await self._export_hacienda_format(report, output_file)
            else:
                await self._export_detailed_format(report, output_file)

            self.logger.info(f"Modelo 721 CSV exported to {output_file}")
            return str(output_file)

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error exporting CSV: {e}", exc_info=True)
            raise

    async def _export_hacienda_format(self, report: Modelo721Report, output_file: Path) -> None:
        """
        Export in Hacienda official format.

        Format requirements:
        - Fecha de la transacción (Transaction date)
        - Operación (Operation: BUY, SELL, TRANSFER)
        - Criptomoneda (Cryptocurrency)
        - Número de criptomonedas (Number of cryptocurrencies)
        - Valor en euros (Value in euros)
        - Contraparte (Counterparty/exchange)
        """
        with output_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(
                [
                    "Fecha",
                    "Operación",
                    "Criptomoneda",
                    "Número de criptomonedas",
                    "Valor en euros",
                    "Contraparte",
                ]
            )

            # Transactions
            for tx in report.transactions:
                writer.writerow(
                    [
                        tx.occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
                        tx.tx_type,
                        tx.symbol,
                        str(tx.quantity),
                        str(tx.total_value_eur),
                        tx.exchange_name,
                    ]
                )

            # Dec 31 holdings
            writer.writerow([])
            writer.writerow(["SALDO A 31 DE DICIEMBRE"])
            writer.writerow(["Criptomoneda", "Cantidad", "Valor en euros", "Exchanges"])

            for balance in report.dec31_balances:
                writer.writerow(
                    [
                        balance.symbol,
                        str(balance.quantity),
                        str(balance.balance_eur),
                        ", ".join(balance.exchanges),
                    ]
                )

            # Summary
            writer.writerow([])
            writer.writerow(["RESUMEN"])
            writer.writerow(["Año fiscal", report.tax_year])
            writer.writerow(["Total ganancias EUR", str(report.total_gain_eur)])
            writer.writerow(["Total pérdidas EUR", str(report.total_loss_eur)])
            writer.writerow(["Ganancia neta EUR", str(report.net_gain_loss_eur)])
            writer.writerow(["Total holdings EUR (31 dic)", str(report.total_holdings_eur)])

    async def _export_detailed_format(self, report: Modelo721Report, output_file: Path) -> None:
        """
        Export in detailed format for internal analysis.
        """
        with output_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(
                [
                    "Report Type",
                    "Tax Year",
                    "User ID",
                    "Report Date",
                    "Generated At",
                ]
            )
            writer.writerow(
                [
                    "Modelo 721",
                    report.tax_year,
                    str(report.user_id),
                    report.report_date.isoformat(),
                    report.generated_at.isoformat(),
                ]
            )

            writer.writerow([])

            # Holdings section
            writer.writerow(["=== BALANCES A 31 DE DICIEMBRE ==="])
            writer.writerow(
                ["Symbol", "Quantity", "Balance EUR", "Exchange Rate EUR", "Exchanges", "Captured At"]
            )

            for balance in report.dec31_balances:
                writer.writerow(
                    [
                        balance.symbol,
                        str(balance.quantity),
                        str(balance.balance_eur),
                        str(balance.exchange_rate_eur),
                        ", ".join(balance.exchanges),
                        balance.captured_at.isoformat(),
                    ]
                )

            writer.writerow([])

            # Capital gains section
            writer.writerow(["=== GANANCIAS Y PÉRDIDAS DE CAPITAL ==="])
            writer.writerow(
                [
                    "Symbol",
                    "Lots Closed",
                    "Total Proceeds EUR",
                    "Total Cost Basis EUR",
                    "Net Gain EUR",
                    "Net Loss EUR",
                    "Long-Term Gain EUR",
                    "Short-Term Gain EUR",
                ]
            )

            for gain_loss in report.capital_gains_losses:
                writer.writerow(
                    [
                        gain_loss.symbol,
                        str(gain_loss.lots_closed),
                        str(gain_loss.total_proceeds),
                        str(gain_loss.total_cost_basis),
                        str(gain_loss.net_gain),
                        str(gain_loss.net_loss),
                        str(gain_loss.long_term_gain),
                        str(gain_loss.short_term_gain),
                    ]
                )

            writer.writerow([])

            # Transactions section
            writer.writerow(["=== TRANSACCIONES ==="])
            writer.writerow(
                ["Occurred At", "Symbol", "Type", "Quantity", "Value EUR", "Exchange", "TX Hash"]
            )

            for tx in report.transactions:
                writer.writerow(
                    [
                        tx.occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
                        tx.symbol,
                        tx.tx_type,
                        str(tx.quantity),
                        str(tx.total_value_eur),
                        tx.exchange_name,
                        tx.tx_hash or "",
                    ]
                )

    async def save_report_to_database(self, report: Modelo721Report) -> UUID:
        """
        Save generated report to database for audit trail.

        Args:
            report: Modelo721Report to save

        Returns:
            UUID of saved report record

        Raises:
            RuntimeError: If database save fails
        """
        try:
            async with get_db_transaction() as session:
                # Create tax report record
                tax_report = TaxReport(
                    user_id=report.user_id,
                    report_type="modelo_721",
                    tax_year=report.tax_year,
                    report_data=report.to_dict(),
                    total_holdings_eur=report.total_holdings_eur,
                    total_gain_eur=report.total_gain_eur,
                    total_loss_eur=report.total_loss_eur,
                    status="final",
                    is_amended=False,
                    report_date=datetime(report.tax_year, 12, 31),
                )

                session.add(tax_report)
                await session.flush()

                self.logger.info(f"Modelo 721 report saved to database: {tax_report.id}")
                return tax_report.id

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            self.logger.error(f"Error saving report to database: {e}", exc_info=True)
            raise RuntimeError(f"Failed to save report: {e}")

    async def get_previous_year_reports(self, user_id: UUID) -> List[TaxReport]:
        """
        Get all previous Modelo 721 reports for a user.

        Useful for amendment and historical analysis.

        Args:
            user_id: User UUID

        Returns:
            List of TaxReport objects
        """
        try:
            async with get_db_transaction() as session:
                stmt = select(TaxReport).where(
                    TaxReport.user_id == user_id,
                    TaxReport.report_type == "modelo_721",
                ).order_by(TaxReport.tax_year.desc())

                result = await session.execute(stmt)
                return list(result.scalars().all())

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            self.logger.error(f"Error getting previous reports: {e}")
            return []


# Singleton instance
_modelo_721_generator_instance: Optional[Modelo721Generator] = None


def get_modelo_721_generator(user_id: Optional[UUID] = None) -> Modelo721Generator:
    """
    Get or create the Modelo 721 generator singleton.

    Args:
        user_id: Optional user UUID for tax reporting

    Returns:
        Modelo721Generator: Shared generator instance
    """
    global _modelo_721_generator_instance
    if _modelo_721_generator_instance is None:
        _modelo_721_generator_instance = Modelo721Generator(user_id=user_id)
    return _modelo_721_generator_instance
