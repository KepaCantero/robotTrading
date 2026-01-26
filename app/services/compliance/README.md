# Regulatory Compliance Module

## Overview

This module provides regulatory compliance tracking for different jurisdictions in the algoTrading system. It ensures that trading activities comply with country-specific regulations, preventing violations and legal issues.

## Country-Specific Rules

### USA (United States)
- **PDT Rule**: Pattern Day Trader rule applies
  - Minimum $25,000 account equity required for day trading
  - Maximum 3 day trades in 5-business-day rolling period
- **Wash Sale Rule**: Applies (IRC Section 1091)
  - Loss disallowed if substantially identical security purchased within 30 days
- **Regulatory Authority**: SEC/FINRA

### Spain (ES)
- **No PDT Rule**: No day trading restrictions
- **No Wash Sale Rule**: All losses are fully deductible
- **Regulatory Authority**: CNMV (Comision Nacional del Mercado de Valores)

### UK/EU
- **No PDT Rule**: No day trading restrictions
- **MiFID II**: Market abuse regulations apply
- **Regulatory Authority**: FCA (UK), ESMA (EU)

## Features

### 1. PDT (Pattern Day Trader) Tracker
Enforces FINRA PDT rule for USA accounts:

```python
from app.services.compliance import PDTTracker, Country

tracker = PDTTracker(country=Country.US)

# Check if trade would violate PDT
allowed, message = tracker.check_pdt_limit(
    account_equity=Decimal("30000"),
    symbol="AAPL",
    side="BUY",
)

# Get current status
status = tracker.get_status(account_equity=Decimal("30000"))
```

### 2. Wash Sale Tracker
Tracks wash sales for USA tax compliance:

```python
from app.services.compliance import WashSaleTracker, Country

tracker = WashSaleTracker(country=Country.US)

# Check if sale would be wash sale
is_wash = tracker.is_wash_sale(
    symbol="AAPL",
    sale_date=date.today(),
    sale_price=Decimal("140"),
)

# Calculate wash sale impact
is_wash, disallowed_loss, deductible_loss = tracker.check_wash_sale_impact(
    symbol="AAPL",
    sale_date=date.today(),
    sale_price=Decimal("140"),
    cost_basis=Decimal("150"),
)
```

### 3. Order Pattern Analyzer
Detects manipulative trading patterns:

```python
from app.services.compliance import OrderPatternAnalyzer

analyzer = OrderPatternAnalyzer()

# Analyze order for suspicious patterns
patterns = analyzer.analyze_order(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    price=Decimal("150"),
    order_type="LIMIT",
)

# Record order
analyzer.record_order(
    order_id="12345",
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    price=Decimal("150"),
    order_type="LIMIT",
)
```

**Detected Patterns:**
- **Layering**: Multiple orders at same price level
- **Spoofing**: Orders with intent to cancel
- **Excessive Cancellation**: High order-to-trade ratio
- **Marking the Close**: Trading near market close
- **Momentum Ignition**: Rapid trading to trigger price movements

### 4. Compliance Manager (Unified Interface)

```python
from app.services.compliance import ComplianceManager, Country, TradeRecord

# Create compliance manager
compliance = ComplianceManager(
    country=Country.ES,
    account_equity=Decimal("100000"),
)

# Check if trade is allowed
trade = TradeRecord(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    price=Decimal("150"),
    trade_date=date.today(),
    order_id="order_123",
)

allowed, violations = compliance.check_trade_allowed(
    trade=trade,
    account_equity=Decimal("100000"),
)

if not allowed:
    logger.warning(f"Trade rejected: {violations}")
else:
    # Record the trade
    compliance.record_trade(trade)

# Generate compliance report
report = compliance.generate_report()
```

## Usage Examples

### Example 1: Spain Account (No Restrictions)

```python
from app.services.compliance import ComplianceManager, Country, TradeRecord
from decimal import Decimal
from datetime import date

# Spain - no PDT or wash sale rules
compliance = ComplianceManager(country=Country.ES)

trade = TradeRecord(
    symbol="SAN.MC",
    side="BUY",
    quantity=Decimal("1000"),
    price=Decimal("4.50"),
    trade_date=date.today(),
)

allowed, violations = compliance.check_trade_allowed(trade)
# allowed = True (no restrictions)
```

### Example 2: USA Account with PDT Restriction

```python
# USA - PDT rules apply
compliance = ComplianceManager(
    country=Country.US,
    account_equity=Decimal("20000"),  # Below $25k
)

trade = TradeRecord(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    price=Decimal("150"),
    trade_date=date.today(),
)

allowed, violations = compliance.check_trade_allowed(trade)
# allowed = False ("PDT restriction: Account equity $20,000 < $25,000 minimum")
```

### Example 3: Day Trade Counting

```python
from datetime import timedelta

compliance = ComplianceManager(
    country=Country.US,
    account_equity=Decimal("50000"),
)

today = date.today()

# Execute 3 day trades
for i in range(3):
    buy = TradeRecord(
        symbol=f"STOCK{i}",
        side="BUY",
        quantity=Decimal("100"),
        price=Decimal("100"),
        trade_date=today,
    )
    sell = TradeRecord(
        symbol=f"STOCK{i}",
        side="SELL",
        quantity=Decimal("100"),
        price=Decimal("105"),
        trade_date=today,
    )

    compliance.record_trade(buy)
    compliance.record_trade(sell)

# Check remaining day trades
remaining = compliance.get_day_trades_remaining()
# remaining = 0 (all 3 used)

# Next day trade would be blocked
trade4 = TradeRecord(
    symbol="STOCK3",
    side="BUY",
    quantity=Decimal("100"),
    price=Decimal("100"),
    trade_date=today,
)
allowed, violations = compliance.check_trade_allowed(trade4)
# allowed = False ("PDT limit reached: 3/3 day trades")
```

### Example 4: Wash Sale Detection

```python
compliance = ComplianceManager(country=Country.US)

# Buy AAPL
buy = TradeRecord(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    price=Decimal("150"),
    trade_date=date.today() - timedelta(days=10),
)
compliance.record_trade(buy)

# Sell at loss within 30 days
sell = TradeRecord(
    symbol="AAPL",
    side="SELL",
    quantity=Decimal("100"),
    price=Decimal("140"),  # $10 loss
    trade_date=date.today(),
)

allowed, violations = compliance.check_trade_allowed(sell)
# May warn about wash sale (loss disallowed for tax)
```

## API Reference

### ComplianceManager

**Methods:**
- `check_trade_allowed(trade, account_equity)` - Check if trade complies
- `record_trade(trade)` - Record executed trade
- `generate_report()` - Get compliance status report
- `can_day_trade()` - Check if day trading allowed
- `get_day_trades_remaining()` - Get remaining day trades (USA)
- `get_violations(severity=None)` - Get compliance violations
- `update_equity(new_equity)` - Update account equity

### PDTTracker

**Constants:**
- `PDT_MIN_EQUITY` = $25,000
- `MAX_DAY_TRADES` = 3
- `ROLLING_WINDOW_DAYS` = 5

**Methods:**
- `check_pdt_limit(account_equity, symbol, side)` - Check PDT compliance
- `record_trade(symbol, side, quantity, price, trade_date)` - Record trade
- `get_status(account_equity)` - Get PDT status
- `get_day_trades(days)` - Get day trade history

### WashSaleTracker

**Constants:**
- `WASH_SALE_WINDOW_DAYS` = 30

**Methods:**
- `is_wash_sale(symbol, sale_date, sale_price)` - Check wash sale
- `check_wash_sale_impact(symbol, sale_date, sale_price, cost_basis)` - Calculate impact
- `get_wash_sales(start_date)` - Get wash sale list
- `get_wash_sale_summary()` - Get summary statistics

### OrderPatternAnalyzer

**Thresholds:**
- `LAYERING_THRESHOLD` = 3 orders
- `CANCELLATION_RATE_THRESHOLD` = 80%
- `RAPID_ORDER_THRESHOLD` = 10 orders in 60 seconds

**Methods:**
- `analyze_order(symbol, side, quantity, price, order_type)` - Analyze patterns
- `record_order(order_id, symbol, side, quantity, price, order_type)` - Record order
- `record_cancellation(order_id)` - Record cancellation
- `record_fill(order_id, fill_quantity)` - Record fill
- `get_order_to_trade_ratio(symbol)` - Get cancellation ratio

## Testing

Run compliance tests:

```bash
pytest tests/unit/services/compliance/ -v
```

## Important Notes

1. **Country-Specific**: Always specify the correct country for compliance rules
2. **Pre-Trade Check**: Always call `check_trade_allowed()` before executing
3. **Post-Trade Record**: Always call `record_trade()` after execution
4. **Spain vs USA**: Spain has significantly fewer restrictions than USA
5. **Tax Implications**: Wash sales have tax consequences in USA
6. **Pattern Detection**: Order patterns are monitored for all countries

## Legal Disclaimer

This module provides basic compliance tracking but does not replace legal advice. Always consult with a qualified tax professional or legal advisor for specific compliance requirements.

## References

- FINRA Rule 4210: Margin Requirements
- IRS Publication 550: Investment Income and Expenses
- MiFID II: EU Markets in Financial Instruments Directive
- CNMV Regulations: Spanish securities laws
