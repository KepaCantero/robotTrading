# Requirements: app/domain/services/backtesting/backtest_engine.py

## Source File Analysis
- **File Path**: `app/domain/services/backtesting/backtest_engine.py`
- **Lines of Code**: 644
- **Status**: Analysis Complete

## Purpose
Implements an institutional-grade backtesting engine for algorithmic trading strategies with:
- Realistic transaction costs and slippage modeling
- Market impact analysis for large orders
- Multi-year simulation capability
- Survivorship bias correction support
- Corporate actions and dividend reinvestment handling
- Comprehensive performance metrics calculation

Reference: López de Prado (2018) "Advances in Financial Machine Learning" - PnL distribution analysis, backtesting overfitting detection, Harrah's bias prevention

## Dependencies

### Internal
None - Pure domain service with no internal dependencies

### External
- `dataclasses`: Data class decorators for value objects
- `datetime.date`, `datetime.datetime`: Date/time handling
- `decimal.Decimal`: Precise financial calculations
- `enum.Enum`: Enumeration types
- `typing`: Type hints (Dict, List, Optional, Tuple)
- `numpy`: Numerical computing (arrays, statistical functions)
- `numpy.typing.NDArray`: Typed numpy arrays
- `scipy.stats`: Statistical functions (skewness, kurtosis)

## Classes/Functions

### class OrderSide(str, Enum)
**Purpose**: Enumeration for order sides (buy/sell)

**Values**:
- `BUY = "buy"`
- `SELL = "sell"`

---

### class OrderType(str, Enum)
**Purpose**: Enumeration for order types

**Values**:
- `MARKET = "market"`
- `LIMIT = "limit"`
- `STOP = "stop"`

---

### class OrderStatus(str, Enum)
**Purpose**: Enumeration for order statuses

**Values**:
- `PENDING = "pending"`
- `FILLED = "filled"`
- `PARTIALLY_FILLED = "partially_filled"`
- `CANCELLED = "cancelled"`
- `REJECTED = "rejected"`

---

### @dataclass class Trade
**Purpose**: Represents a single trade execution

**Attributes**:
- `symbol: str` - Trading symbol
- `side: OrderSide` - Buy or sell
- `quantity: Decimal` - Number of shares/contracts
- `price: Decimal` - Execution price
- `timestamp: datetime` - Execution timestamp
- `commission: Decimal` - Trading commission (default: 0)
- `slippage: Decimal` - Slippage cost (default: 0)
- `market_impact: Decimal` - Market impact cost (default: 0)

**Properties**:
- `notional_value: Decimal` - Total value (quantity * price)
- `total_cost: Decimal` - Total cost including commission, slippage, and market impact

---

### @dataclass class BacktestConfig
**Purpose**: Configuration parameters for backtesting

**Attributes**:
- `initial_capital: Decimal` - Starting capital
- `start_date: date` - Backtest start date
- `end_date: date` - Backtest end date
- `commission_per_share: Decimal` - Per-share commission (default: $0.005)
- `commission_min: Decimal` - Minimum commission (default: $1.0)
- `slippage_model: Optional[str]` - Slippage model type (default: "linear")
- `slippage_rate: float` - Slippage rate (default: 0.001 = 0.1%)
- `market_impact: bool` - Enable market impact (default: True)
- `dividend_reinvestment: bool` - Reinvest dividends (default: True)
- `survivorship_bias_correction: bool` - Enable bias correction (default: True)
- `benchmark_symbol: Optional[str]` - Benchmark for comparison
- `max_position_size: Optional[Decimal]` - Max position size limit
- `max_portfolio_exposure: Optional[float]` - Max portfolio exposure

---

### @dataclass class PerformanceMetrics
**Purpose**: Comprehensive performance metrics from backtest

**Returns Metrics**:
- `total_return: float` - Total return percentage
- `annualized_return: float` - Annualized return
- `sharpe_ratio: float` - Risk-adjusted return (Sharpe)
- `sortino_ratio: float` - Downside risk-adjusted return
- `calmar_ratio: float` - Return/max drawdown ratio
- `max_drawdown: float` - Maximum drawdown
- `max_drawdown_duration: int` - Drawdown duration in days
- `volatility: float` - Standard deviation of returns
- `annualized_volatility: float` - Annualized volatility
- `win_rate: float` - Percentage of winning trades
- `profit_factor: float` - Gross profit/gross loss ratio
- `avg_trade_return: float` - Average trade return
- `total_trades: int` - Total number of trades
- `winning_trades: int` - Number of winning trades
- `losing_trades: int` - Number of losing trades
- `best_trade: float` - Best single trade return
- `worst_trade: float` - Worst single trade return
- `avg_win: float` - Average winning trade
- `avg_loss: float` - Average losing trade
- `expectancy: float` - Expected value per trade
- `skewness: float` - Return distribution skewness
- `kurtosis: float` - Return distribution kurtosis
- `var_95: float` - Value at Risk at 95% confidence
- `var_99: float` - Value at Risk at 99% confidence
- `cvar_95: float` - Conditional VaR at 95%
- `information_ratio: float` - Excess return/tracking error
- `tracking_error: float` - Tracking error vs benchmark
- `beta: float` - Systematic risk vs benchmark
- `alpha: float` - Excess return over CAPM

---

### @dataclass class BacktestResult
**Purpose**: Container for complete backtest results

**Attributes**:
- `config: BacktestConfig` - Configuration used
- `trades: List[Trade]` - All executed trades
- `equity_curve: List[Tuple[date, Decimal]]` - Daily equity values
- `returns: List[float]` - Daily returns
- `positions: Dict[str, Decimal]` - Final positions
- `cash: Decimal` - Final cash balance
- `final_capital: Decimal` - Total final capital
- `metrics: Optional[PerformanceMetrics]` - Calculated metrics

**Properties**:
- `total_trades: int` - Number of trades executed

---

### class BacktestEngine
**Purpose**: Core backtesting engine with institutional-grade features

**Key Methods**:

#### `__init__(config: BacktestConfig)`
Initialize backtest with configuration

#### `reset() -> None`
Reset engine to initial state

#### `update_prices(prices: Dict[str, Decimal], current_date: date) -> None`
Update prices for all symbols and record equity curve

#### `execute_order(symbol, side, quantity, order_type, price_limit) -> Optional[Trade]`
Execute order with realistic cost modeling:
- Slippage calculation
- Market impact for large orders
- Commission calculation
- Cash/position validation

#### `calculate_metrics(benchmark_returns) -> PerformanceMetrics`
Calculate comprehensive performance metrics including Sharpe, Sortino, drawdowns, VaR, CVaR, alpha/beta

#### `handle_dividend(symbol, dividend_per_share) -> Decimal`
Handle dividend payments with optional reinvestment

#### `close_all_positions() -> List[Trade]`
Close all positions at current market prices

## Business Logic

### Order Execution Flow
1. Validate order (quantity > 0, price available)
2. Check limit order conditions if applicable
3. Calculate slippage based on model (linear/percentage)
4. Calculate market impact for large orders
5. Calculate execution price with adjustments
6. Calculate commission
7. Validate cash/position availability
8. Execute trade and update state
9. Record trade with all cost components

### Slippage Models
- **linear**: `price * quantity * rate / 1000`
- **percentage**: `price * rate`

### Market Impact
- Simplified square-root law: `impact ~ (quantity / adv)^0.5`
- Uses `rate * 0.5 * price * sqrt(quantity)`

### Performance Metrics Calculation
- Returns-based: Sharpe, Sortino, Calmar, volatility
- Drawdown analysis: Max drawdown, duration
- Trade analysis: Win rate, profit factor, expectancy
- Distribution: Skewness, kurtosis, VaR, CVaR
- Benchmark-relative: Alpha, beta, information ratio, tracking error

## Data Models

### Core Value Objects
- `OrderSide`, `OrderType`, `OrderStatus` - Enums for order attributes
- `Trade` - Immutable trade record with all cost components
- `BacktestConfig` - Immutable configuration
- `PerformanceMetrics` - Immutable metrics container
- `BacktestResult` - Complete results container

### State Management
- `_cash: Decimal` - Current cash balance
- `_positions: Dict[str, Decimal]` - Current positions
- `_trades: List[Trade]` - All executed trades
- `_equity_curve: List[Tuple[date, Decimal]]` - Historical equity
- `_returns: List[float]` - Daily returns
- `_prices: Dict[str, Decimal]` - Current prices
- `_dividends: Dict[str, List[Tuple[date, Decimal]]]` - Dividend history

## API Contracts

### Public Interface
```python
# Initialize
engine = BacktestEngine(config)

# Run simulation
for date in date_range:
    prices = get_prices(date)
    engine.update_prices(prices, date)

    # Generate signals and execute orders
    for signal in signals:
        engine.execute_order(symbol, side, quantity)

# Get results
result = engine.get_result()
metrics = engine.calculate_metrics()
```

## Error Handling

### Validation Checks
- Quantity must be positive
- Price must be available
- Sufficient cash for buys
- Sufficient position for sells
- Limit order price conditions

### Graceful Handling
- Returns `None` for invalid orders
- Returns `0.0` for empty metrics
- Handles missing benchmark data

## Performance Considerations

### Computational Complexity
- Order execution: O(1) per order
- Metrics calculation: O(n) where n = number of return periods
- Trade matching: O(n²) for round-trip analysis (could be optimized)

### Memory Usage
- Stores full equity curve: O(days)
- Stores all trades: O(trades)
- Stores price history: O(symbols)

### Optimization Opportunities
- Trade matching could use position tracking instead of reverse search
- Metrics calculation could be incremental

## Testing Strategy

### Unit Tests Needed
- Order execution with various types (market, limit, stop)
- Slippage calculation accuracy
- Market impact calculation
- Commission calculation
- Dividend handling with/without reinvestment
- Position limits enforcement
- Cash validation
- Edge cases (zero quantity, missing prices, insufficient funds)

### Integration Tests Needed
- Full backtest workflow
- Multi-day simulation
- Multiple symbols
- Benchmark comparison
- Corporate actions

### Performance Tests Needed
- Large trade counts (>1000 orders)
- Long date ranges (>10 years)
- Many symbols (>100)

## Critical Rules (from BASE_RULES.md)

### TYP-001: Type hints
- ✅ All functions have complete type hints
- ✅ Uses `from __future__ import annotations` for modern syntax
- ✅ Proper use of `Optional` for nullable types

### LOG-001: Structured logging
- ❌ GAP: No structured logging implementation
- Recommendation: Add structlog for order execution, errors, state changes

### ERR-001: Error handling
- ⚠️ Partial: Returns `None` for failed orders but no logging
- Recommendation: Log failed order reasons for debugging

### ARCH-001: Layered architecture
- ✅ Domain layer - no framework dependencies
- ✅ Pure domain service with no external infrastructure dependencies

### CC-001: Descriptive names
- ✅ Clear, self-documenting names
- ✅ Enum values are explicit

### QL-001: Complexity
- ⚠️ WARNING: `calculate_metrics()` has complexity E (31) - exceeds recommended threshold
- ⚠️ WARNING: `execute_order()` has complexity C (20) - moderate
- Recommendation: Consider extracting metric calculation to separate service

### TRD-002: Risk validation
- ✅ Validates order quantities
- ✅ Checks cash availability
- ✅ Checks position availability
- ⚠️ Could add more position size limits

### TRD-004: Audit trail
- ✅ All trades recorded with full details
- ✅ Equity curve tracks all changes
- ⚠️ Could add order rejection reasons

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T05:20:00Z |
| **Audit Status** | PASSED_WITH_NOTES |

**Notes**:
- Fixed: Type casting for numpy float operations (lines 547, 550-551)
- Code follows clean architecture principles
- High complexity in metrics calculation is acceptable for comprehensive analysis
- Missing structured logging is not critical for domain service (handled by application layer)
