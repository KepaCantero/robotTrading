"""
Regulatory Compliance Module for algoTrading System.

This module provides regulatory compliance tracking for different jurisdictions:
- PDT (Pattern Day Trader) rule enforcement for USA accounts
- Wash sale tracking for USA accounts
- Order pattern analysis (layering, spoofing, marking the close)
- Geographic restrictions and KYC compliance

IMPORTANT: Country-Specific Rules
- USA: PDT rule applies, wash sale rule applies
- Spain (ES): No PDT rule, no wash sale rule
- UK: Different regulatory framework
- EU: MiFID II regulations

Usage:
    from app.services.compliance import (
        ComplianceManager,
        Country,
        TradeRecord,
    )

    # Create compliance manager for Spain
    compliance = ComplianceManager(country=Country.ES)

    # Check if trade is allowed
    trade = TradeRecord(
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("100"),
        price=Decimal("150"),
        trade_date=date.today(),
    )

    allowed, violations = compliance.check_trade_allowed(
        trade=trade,
        account_equity=Decimal("100000"),
    )

    if not allowed:
        logger.warning(f"Trade rejected: {violations}")
"""

from app.services.compliance.manager import (
    ComplianceManager,
    ComplianceReport,
    ComplianceViolation,
    Country,
    TradeRecord,
)
from app.services.compliance.order_pattern_analyzer import OrderPatternAnalyzer
from app.services.compliance.pdt_tracker import PDTTracker
from app.services.compliance.wash_sale_tracker import WashSaleTracker

__all__ = [
    # Main manager
    "ComplianceManager",
    # Enums and data classes
    "Country",
    "TradeRecord",
    "ComplianceViolation",
    "ComplianceReport",
    # Individual trackers (can be used standalone)
    "PDTTracker",
    "WashSaleTracker",
    "OrderPatternAnalyzer",
]
