# Requirements: app/domain/services/backtesting/transaction_costs.py

## Source File Analysis
- **File Path**: `app/domain/services/backtesting/transaction_costs.py`
- **Lines of Code**: 491
- **Status**: Analysis Complete

## Purpose
Implements various transaction cost models for realistic backtesting including:
- Linear cost model (per-share commission)
- Piecewise linear cost model (volume discounts)
- Market impact models (Almgren-Chriss, Square Root)

References Almgren, R., & Chriss, N. (2001) "Optimal Execution of Portfolio Transactions"

## Dependencies

### Internal
None - Pure domain service with no internal dependencies

### External
- `from __future__ import annotations` - Modern type hints
- `abc.ABC, abstractmethod` - Abstract base classes
- `dataclasses.dataclass` - Data structures
- `decimal.Decimal` - Precise financial calculations
- `enum.Enum` - Cost model types
- `typing.List, Optional, Tuple` - Type hints
- `numpy as np` - Mathematical operations

## Classes/Functions

### class CostModelType(str, Enum)
**Purpose**: Enumeration of available cost model types
**Values**: LINEAR, PIECEWISE_LINEAR, NONLINEAR

### @dataclass CostBreakdown
**Purpose**: Detailed breakdown of transaction costs
**Attributes**:
- `commission: Decimal` - Broker commission
- `exchange_fees: Decimal` - Exchange fees
- `sec_fees: Decimal` - SEC fees (US stocks)
- `nasdaq_fees: Decimal` - NASDAQ fees
- `slippage: Decimal` - Price slippage
- `market_impact: Decimal` - Market impact
- `total: Decimal` - Total cost

**Methods**:
- `cost_as_percentage(self) -> float` - Total cost as percentage (line 45-49)

### class TransactionCostModel(ABC)
**Purpose**: Base abstract class for transaction cost models

**Abstract Methods**:
- `calculate_cost(symbol, side, quantity, price, volume=None, adv=None) -> CostBreakdown` (line 65-88)
- `estimate_total_cost(trades: List[Tuple[...]]) -> Decimal` (line 91-104)

### class LinearCostModel(TransactionCostModel)
**Purpose**: Linear transaction cost model (fixed + per-share)

**Init** (line 116-136):
- `commission_per_share: Decimal = Decimal("0.005")`
- `min_commission: Decimal = Decimal("1.0")`
- `exchange_fee_rate: Decimal = Decimal("0.00023")`
- `sec_fee_rate: Decimal = Decimal("0.0000082")`

**Methods**:
- `calculate_cost(...) -> CostBreakdown` (line 137-175)
- `estimate_total_cost(...) -> Decimal` (line 177-186)

### class PiecewiseLinearCostModel(TransactionCostModel)
**Purpose**: Cost model with volume-based tiered pricing

**Init** (line 201-217):
- `tiers: List[Tuple[Decimal, Decimal]]` - Volume discount tiers
- `min_commission: Decimal = Decimal("1.0")`

**Methods**:
- `_get_rate_for_quantity(quantity: Decimal) -> Decimal` (line 219-224)
- `calculate_cost(...) -> CostBreakdown` (line 226-262)
- `estimate_total_cost(...) -> Decimal` (line 264-273)

### class MarketImpactModel(ABC)
**Purpose**: Base abstract class for market impact models

**Abstract Methods**:
- `calculate_impact(quantity, price, adv, volatility=0.2, participation_rate=None) -> Decimal` (line 280-301)

### class AlmgrenChristModel(MarketImpactModel)
**Purpose**: Almgren-Chriss market impact model implementation

**Constants** (line 319-323):
- `DEFAULT_PERMANENT_IMPACT = 0.1` (Gamma)
- `DEFAULT_TEMPORARY_IMPACT = 0.05` (Eta)
- `DEFAULT_VOLATILITY_IMPACT = 0.5` (Lambda)

**Init** (line 325-342):
- `permanent_impact: float` - Gamma parameter
- `temporary_impact: float` - Eta parameter
- `volatility_impact: float` - Lambda parameter

**Methods**:
- `calculate_impact(...) -> Decimal` (line 343-388)
- `calculate_permanent_impact(quantity, adv) -> float` (line 390-397)
- `calculate_temporary_impact(quantity, adv, volatility=0.2) -> float` (line 399-407)

### class SquareRootImpactModel(MarketImpactModel)
**Purpose**: Square root market impact model (simpler, widely used)

**Init** (line 419-426):
- `coefficient: float = 0.1` - Impact coefficient (0.05-0.2 typical)

**Methods**:
- `calculate_impact(...) -> Decimal` (line 428-463)

### @dataclass ImpactParameters
**Purpose**: Parameters container for market impact calculation
**Attributes**: adv, volatility, market_cap, spread, price (line 467-475)

### @dataclass TemporaryImpact
**Purpose**: Temporary market impact data (line 478-483)

### @dataclass PermanentImpact
**Purpose**: Permanent market impact data (line 486-491)

## Business Logic

### Cost Calculation Flow
1. **Linear Model**: `costs = fixed_commission + per_share_rate * quantity`
2. **Piecewise Linear**: Apply tiered rates based on volume thresholds
3. **SEC Fees**: Only applied to sell orders (`side.lower() == "sell"`)
4. **Market Impact**: Separate models for different impact calculations

### Market Impact Models
- **Almgren-Chriss**: Impact = temporary + permanent components
  - Temporary: depends on execution speed and volatility
  - Permanent: moves price persistently based on participation rate
- **Square Root**: `Impact = coefficient * sigma * sqrt(Q/ADV)`

### Key Formulas
- Participation rate: `min(qty_float / adv_float, 1.0)`
- Daily volatility: `volatility / sqrt(252)` (252 trading days)
- Permanent impact: `gamma * participation_rate`
- Temporary impact: `eta * (quantity/adv) * daily_vol`

## Critical Rules (from BASE_RULES.md)

### TYP-001: Type Hints Coverage
**Status**: ✅ PASSED
- All functions have complete type hints
- Uses modern `from __future__ import annotations`
- Return types specified for all methods

### TYP-002: Modern Type Syntax
**Status**: ✅ PASSED
- Uses `Optional[T]` for nullable types
- Proper use of `List`, `Tuple` from typing
- `Decimal` type for all financial calculations

### ARCH-003: Domain Layer Purity
**Status**: ✅ PASSED
- No framework imports (FastAPI, SQLAlchemy, etc.)
- Pure domain service with abstract base classes
- Only standard library + numpy for calculations

### SOL-001: Single Responsibility Principle
**Status**: ✅ PASSED
- Each class has one clear responsibility
- Base classes define interfaces
- Concrete classes implement specific models

### SOL-004: Interface Segregation
**Status**: ✅ PASSED
- `TransactionCostModel` ABC defines minimal interface
- `MarketImpactModel` ABC separates impact concerns

### QL-001: Cyclomatic Complexity
**Status**: ✅ PASSED
- Average complexity: A (1.64)
- All functions rated A (1-3 complexity)
- Maximum complexity: 3 (very low)

### CC-006: Explicit Error Handling
**Status**: N/A (No I/O operations - pure calculation module)

### TRD-006: Transaction Costs
**Status**: ✅ PASSED
- Comprehensive cost modeling
- Includes commission, fees, slippage, market impact
- Realistic US stock cost structure

### TRD-007: Annualization
**Status**: ✅ PASSED
- Documents TRADING_DAYS = 252 (line 372, 406)
- Proper daily volatility conversion: `volatility / sqrt(252)`

### BT-004: Realistic Costs
**Status**: ✅ PASSED
- Models real US market fee structure
- SEC fees: $0.0000082 per share (sells only)
- Exchange fees: $0.00023 per share
- NASDAQ fees: $0.0001 per share

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T05:22:00Z |
| **Audit Status** | PASSED |

## Notes

### Strengths
1. **Clean domain design**: No framework dependencies, pure business logic
2. **Academic foundation**: References Almgren-Chriss paper for credibility
3. **Multiple models**: Linear, piecewise linear, and impact models
4. **Precise calculations**: Uses `Decimal` for all financial values
5. **Low complexity**: Very maintainable code (avg complexity 1.64)
6. **Proper abstraction**: ABCs for clean interface definitions

### Cost Model Details
- **SEC fees**: Only on sell orders (regulatory requirement met)
- **Volume discounts**: Piecewise model supports tiered pricing
- **Market impact**: Separate models for different trading strategies
- **US market focus**: Realistic fee structure for US equities

### Model Selection Guidance
- **Linear**: Small retail orders, simple backtesting
- **Piecewise Linear**: Institutional volume with tiered pricing
- **Almgren-Chriss**: Large orders where execution timing matters
- **Square Root**: Quick approximation for many assets

---
*Analysis completed 2026-02-07T05:22:00Z*
