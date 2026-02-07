# Requirements: app/portfolio/multi_asset/multi_asset_portfolio.py

**Status:** PASSED
**Last Audited:** 2026-02-07
**Batch:** 0096

## File Purpose
Multi-asset portfolio management system supporting construction, rebalancing, and risk management across different asset classes. Includes asset class allocation, within-class strategies, position limits, and risk contribution analysis.

## Base Rules Compliance
See ../../BASE_RULES.md for universal rules. This file complies with:
- FMT-001 to FMT-008 (Formatting & Style)
- TYP-001 to TYP-006 (Type Hints)
- SOL-001 to SOL-005 (SOLID Principles)
- ARCH-001 to ARCH-007 (Architecture)
- LOG-001 to LOG-007 (Logging)

## File-Specific Requirements

### 1. Portfolio Construction (P0 - TRD)

| Rule ID | Requirement | Implementation | Status |
|---------|-------------|----------------|--------|
| PC-001 | Target weights validation | Must sum to 1.0 ± 0.01 | PASS |
| PC-002 | Non-negative weights | All weights >= 0 | PASS |
| PC-003 | Asset class existence | Validates known asset classes | PASS |
| PC-004 | Within-class allocation | Multiple strategies supported | PASS |
| PC-005 | Position limits | Min/max position size enforced | PASS |

### 2. Rebalancing Logic (P0 - TRD)

| Rule ID | Requirement | Check | Status |
|---------|-------------|-------|--------|
| RB-001 | Threshold check | Only rebalance when deviation > threshold | PASS |
| RB-002 | Trade generation | Calculates required trades | PASS |
| RB-003 | Cost estimation | Trading cost in bps | PASS |
| RB-004 | Preserve state | Returns current/target weights | PASS |

### 3. Risk Management (P0 - TRD)

| Rule ID | Requirement | Check | Status |
|---------|-------------|-------|--------|
| RSK-001 | Risk contributions | MCTR calculation by asset class | PASS |
| RSK-002 | Covariance handling | Handles singular matrices | PASS |
| RSK-003 | Normalization | Contributions sum to 1 | PASS |
| RSK-004 | Fallback values | Returns equal weights on error | PASS |

### 4. Configuration (P1)

| Rule ID | Requirement | Check | Status |
|---------|-------------|-------|--------|
| CFG-001 | Pydantic validation | MultiAssetConfig with field validators | PASS |
| CFG-002 | Cross-field validation | max_position >= min_position | PASS |
| CFG-003 | Asset class validation | Unique names, at least one enabled | PASS |
| CFG-004 | Extra forbid | No unexpected fields | PASS |

## Acceptance Criteria

### AC-PC-001: Weight Sum Validation
```bash
# Test target weights must sum to 1.0
python -c "
from app.portfolio.multi_asset.multi_asset_portfolio import MultiAssetPortfolioManager, MultiAssetConfig
from app.portfolio.multi_asset.asset_class import AssetClassConfig, AssetClassType
from decimal import Decimal

config = MultiAssetConfig(asset_classes=[
    AssetClassConfig(name='equity', type=AssetClassType.EQUITY, enabled=True)
])

manager = MultiAssetPortfolioManager(config)

try:
    manager._validate_target_weights({'equity': Decimal('0.5')})  # Sums to 0.5
    print('FAIL: Should reject weights not summing to 1')
except ValueError as e:
    print('PASS: Weight validation works')
"
```

### AC-PC-002: Position Limits
```bash
# Test position size limits are enforced
python -c "
from app.portfolio.multi_asset.multi_asset_portfolio import MultiAssetPortfolioManager, MultiAssetConfig
from app.portfolio.multi_asset.asset_class import AssetClassConfig, AssetClassType
from decimal import Decimal

config = MultiAssetConfig(
    asset_classes=[
        AssetClassConfig(name='equity', type=AssetClassType.EQUITY, enabled=True)
    ],
    min_position_size=Decimal('0.01'),
    max_position_size=Decimal('0.20')
)

manager = MultiAssetPortfolioManager(config)
weights = {'a': Decimal('0.30'), 'b': Decimal('0.70')}  # 'a' exceeds max
limited = manager._apply_position_limits(weights)
assert limited['a'] == Decimal('0.20'), f'Expected 0.20, got {limited[\"a\"]}'
print('PASS')
"
```

### AC-PC-003: Risk Contributions
```bash
# Test risk contributions sum to 1
python -c "
from app.portfolio.multi_asset.multi_asset_portfolio import MultiAssetPortfolioManager, MultiAssetConfig
from app.portfolio.multi_asset.asset_class import AssetClassConfig, AssetClassType
from decimal import Decimal
import pandas as pd

config = MultiAssetConfig(asset_classes=[
    AssetClassConfig(name='equity', type=AssetClassType.EQUITY, enabled=True)
])
manager = MultiAssetPortfolioManager(config)

# Mock portfolio with allocations
from app.portfolio.multi_asset.models import MultiAssetPortfolio, MultiAssetAllocation
from app.portfolio.multi_asset.asset_class import AssetClass

alloc = MultiAssetAllocation(
    asset_class=AssetClass(name='equity', type=AssetClassType.EQUITY),
    weight=Decimal('1.0'),
    assets={'AAPL': Decimal('1.0')},
    expected_return=Decimal('0.1'),
    risk=Decimal('0.2')
)
portfolio = MultiAssetPortfolio(
    name='Test',
    allocations={'equity': alloc},
    total_value=Decimal('1000000'),
    last_rebalanced=None,
    rebalance_threshold=Decimal('0.05'),
    currency='USD'
)

returns = pd.DataFrame({'AAPL': [0.01, 0.02, 0.015]})
contributions = manager.calculate_risk_contributions(portfolio, returns)
total = sum(contributions.values())
assert abs(total - Decimal('1')) < Decimal('0.01'), f'Sum = {total}, expected 1'
print('PASS')
"
```

### AC-PC-004: Type Safety
```bash
# Verify type hints
mypy --strict app/portfolio/multi_asset/multi_asset_portfolio.py
# Expected: 0 errors (may have some in dynamic parts)
```

## Audit Findings

### Strengths
1. **Comprehensive Validation:** Pydantic config with cross-field validators
2. **Risk Management:** Proper MCTR calculation for risk contributions
3. **Error Handling:** Graceful fallbacks when calculations fail
4. **Clean Results:** Dataclass results (PortfolioConstructionResult, RebalanceResult)
5. **Asset Class Support:** Flexible multi-asset architecture

### Observations
1. **Decimal Arithmetic:** All financial calculations use Decimal
2. **Logging:** Uses logging module appropriately
3. **Error Results:** Returns structured error objects, not exceptions
4. **Position Sizing:** Handles fractional vs whole shares (line 706-716)
5. **Cost Estimation:** Trading cost in bps applied correctly (line 734-736)

### Code Quality
- Line count: ~817 lines (acceptable for complex portfolio manager)
- Function complexity: Risk calculation is appropriately complex
- Well-structured private methods (_validate_, _calculate_, _create_)
- No security concerns (no secrets, no external calls)

### Mathematical Correctness
- MCTR formula: (w * (Σw)_i) / σ_p² correctly implemented (line 456)
- Risk aggregation: By asset class from individual assets (lines 461-469)
- Normalization: Ensures contributions sum to 1 (lines 474-476)

### Rebalancing Logic
The rebalancing logic (lines 306-406) correctly:
1. Calculates current weights from portfolio
2. Checks if rebalancing needed (threshold-based)
3. Generates trades for each asset class
4. Estimates trading costs
5. Returns structured result

### Edge Case Handling
- Empty data: Returns equal contributions (line 435)
- Zero variance: Returns equal contributions (line 447)
- Missing asset classes: Skips with warning (line 241-243)
- No market data: Uses cash proxy (line 249-251)

## Test Coverage Requirements
- Portfolio construction with valid/invalid weights
- Rebalancing threshold logic
- Risk contribution calculation
- Position limit enforcement
- Edge cases: empty data, zero variance, missing classes
- Trade generation accuracy

## Integration Points
- Depends on: app.portfolio.multi_asset.asset_class
- Depends on: app.portfolio.multi_asset.models
- Used by: Application layer for portfolio management
- Used by: Backtesting for portfolio simulation

## Documentation Requirements
- Document rebalancing algorithm
- Explain risk contribution methodology
- Add examples for asset class configuration
- Document position sizing rules

## References
- Modern Portfolio Theory (Markowitz)
- Risk Parity and Risk Budgeting (Qian, Ma)
- Multi-Asset Investing (Darst)

---
*Last updated: 2026-02-07*
