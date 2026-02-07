# Requirements: app/domain/strategies/quality_screen.py

## Source File Analysis
- **File Path**: `app/domain/strategies/quality_screen.py`
- **Lines of Code**: 553
- **Status**: Analysis Complete

## Purpose
Implements quality-based stock selection strategy based on fundamental metrics that identify high-quality, profitable companies. References Novy-Marx (2013) "The Other Side of Value: Gross Profitability Premium" and Berkin & Swedroe quality investing concepts.

## Dependencies

### Internal
None - Pure domain service

### External
- `from __future__ import annotations` - Modern type hints
- `dataclasses.dataclass` - Data structures
- `enum.Enum` - Signal enumeration
- `typing.Dict, List, Tuple` - Type hints
- `numpy as np` - Statistical calculations

## Classes/Functions

### class QualitySignal(str, Enum)
**Purpose**: Signal enumeration for quality investing
**Values**: HIGH_QUALITY, GOOD_QUALITY, AVERAGE_QUALITY, LOW_QUALITY, POOR_QUALITY

### @dataclass QualityMetrics
**Purpose**: Comprehensive quality metrics for a company

**Attributes**:
- `symbol: str` - Stock symbol
- `gross_profit_margin: float` - Gross profit / revenue
- `operating_profit_margin: float` - Operating income / revenue
- `net_profit_margin: float` - Net income / revenue
- `return_on_equity: float` - ROE
- `return_on_assets: float` - ROA
- `return_on_invested_capital: float` - ROIC
- `free_cash_flow_margin: float` - FCF / revenue
- `current_ratio: float` - Current assets / current liabilities
- `quick_ratio: float` - (Current assets - inventory) / current liabilities
- `debt_to_equity: float` - D/E ratio
- `interest_coverage: float` - EBIT / interest expense
- `altman_z_score: float` - Bankruptcy risk score
- `accruals: float` - Net income - cash flow from operations
- `earnings_smoothness: float` - Std dev of earnings (lower is better)
- `earnings_consistency: float` - Years of positive earnings
- `revenue_growth: float` - Revenue CAGR
- `earnings_growth: float` - Earnings CAGR
- `fcf_growth: float` - Free cash flow CAGR
- `price_to_book: float` - P/B ratio
- `price_to_earnings: float` - P/E ratio
- `enterprise_value_to_ebitda: float` - EV/EBITDA

**Properties**:
- `profitability_score(self) -> float` (line 68-112) - Calculate profitability score (0-1)
- `financial_health_score(self) -> float` (line 115-151) - Calculate financial health score (0-1)
- `overall_quality_score(self) -> float` (line 154-185) - Calculate overall quality score (0-1)
- `quality_category(self) -> QualitySignal` (line 188-201) - Get quality category

**Methods**:
- `is_quality_stock(self, threshold: float = 0.6) -> bool` (line 203-205)

### @dataclass QualityPortfolio
**Purpose**: Portfolio constructed using quality strategy

**Attributes**:
- `positions: Dict[str, float]` - Symbol -> weight
- `portfolio_quality_score: float` - Weighted average quality score
- `portfolio_profitability: float` - Weighted average profitability
- `portfolio_financial_health: float` - Weighted average financial health

**Properties**:
- `quality_grade(self) -> QualitySignal` (line 218-229) - Get portfolio quality grade

### class QualityInvesting
**Purpose**: Quality investing strategy domain service

**Init** (line 246-274):
- `min_quality_score: float = 0.6`
- `min_roe: float = 0.10`
- `min_profit_margin: float = 0.05`
- `max_debt_to_equity: float = 1.0`
- `min_interest_coverage: float = 2.0`
- `quality_weight: float = 0.7`
- `value_weight: float = 0.3`

**Methods**:
- `screen_quality_stocks(quality_metrics: Dict[str, QualityMetrics]) -> List[str]` (line 276-295)
- `_passes_screen(metrics: QualityMetrics) -> bool` (line 297-321)
- `rank_quality_stocks(quality_metrics: Dict[str, QualityMetrics]) -> List[Tuple[str, float]]` (line 323-348)
- `_calculate_quality_value_score(metrics: QualityMetrics) -> float` (line 350-374)
- `construct_portfolio(quality_metrics, capital, max_positions=25, min_weight=0.02, max_weight=0.06) -> QualityPortfolio` (line 376-453)
- `_apply_weight_constraints(weights, min_weight, max_weight) -> Dict[str, float]` (line 455-468)
- `generate_signal(metrics, current_price, fair_value=0.0) -> QualitySignal` (line 470-517)
- `calculate_gross_profitability_premium(quality_metrics, returns) -> Tuple[float, float]` (line 519-552)

## Business Logic

### Quality Scoring System
**Profitability Score** (50% weight):
- Gross margin >40%: 0.2 points (excellent)
- Operating margin >15%: 0.2 points
- ROE >15%: 0.2 points
- ROIC >12%: 0.2 points
- FCF margin >10%: 0.2 points

**Financial Health Score** (30% weight):
- Current ratio >2: 0.2 points
- Quick ratio >1: 0.2 points
- Debt-to-equity <0.3: 0.3 points
- Interest coverage >10: 0.3 points

**Earnings Quality Score** (20% weight):
- Low accruals: 0.5 points
- High earnings consistency: 0.5 points

### Screening Criteria
- Minimum quality score: 0.6 (configurable)
- Minimum ROE: 10%
- Minimum profit margin: 5%
- Maximum D/E: 1.0
- Minimum interest coverage: 2.0
- Altman Z-score >1.8 (avoid distress zone)

### Portfolio Construction
1. Screen quality stocks
2. Rank by quality-value composite score
3. Select top N stocks (default 25)
4. Equal-weight with quality adjustments
5. Apply weight constraints (2%-6%)
6. Normalize to 100%

### Gross Profitability Premium
Compares returns of high-gross-margin (>40%) vs low-gross-margin (<20%) stocks to validate the quality factor.

## Critical Rules (from BASE_RULES.md)

### TYP-001: Type Hints Coverage
**Status**: ✅ PASSED
- All functions have complete type hints
- Uses modern `from __future__ import annotations`

### ARCH-003: Domain Layer Purity
**Status**: ✅ PASSED
- No framework dependencies (FastAPI, SQLAlchemy, etc.)
- Pure domain service with numpy only for calculations

### SOL-001: Single Responsibility Principle
**Status**: ✅ PASSED
- QualityMetrics: Data and scoring
- QualityPortfolio: Portfolio representation
- QualityInvesting: Strategy logic

### QL-001: Cyclomatic Complexity
**Status**: ⚠️ ACCEPTABLE
- Average complexity: B (5.95)
- Highest methods: profitability_score (C=16), financial_health_score (C=13)
- Complex scoring logic is acceptable for business rules

### FMT-003: No Unused Imports
**Status**: ✅ FIXED
- Removed unused `Decimal` import
- Removed unused `Optional` import

### CC-006: Explicit Error Handling
**Status**: N/A (Pure calculation module - no I/O operations)

### TRD-002: Risk Validation
**Status**: ✅ PASSED
- Altman Z-score check for bankruptcy risk
- Financial health validation
- Position weight constraints (min/max)

### TRD-003: Position Limits
**Status**: ✅ PASSED
- Max positions: 25 (configurable)
- Min weight: 2%
- Max weight: 6%

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T05:27:00Z |
| **Audit Status** | PASSED |

## Notes

### Strengths
1. **Academic foundation**: References Novy-Marx (2013) gross profitability premium
2. **Comprehensive metrics**: 20+ fundamental metrics
3. **Multi-dimensional scoring**: Profitability, health, earnings quality
4. **Risk-aware**: Altman Z-score for bankruptcy risk
5. **Flexible construction**: Quality-value composite scoring
6. **Clean domain design**: No framework dependencies

### Code Fixes Applied
1. Removed unused `Decimal` import
2. Removed unused `Optional` import

### Quality Factor Implementation
The quality factor is based on research showing that high-quality companies (high profitability, low debt) generate superior risk-adjusted returns. The scoring system weights:
- **Profitability (50%)**: The primary quality indicator
- **Financial Health (30%)**: Balance sheet strength
- **Earnings Quality (20%)**: Sustainability of earnings

### Maintainability
- Maintainability Index: A (38.38) - Good
- Complexity is acceptable for scoring logic
- Well-documented with inline comments
- Clear separation of concerns

---
*Analysis completed 2026-02-07T05:27:00Z*
