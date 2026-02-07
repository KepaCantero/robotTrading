# Requirements: engines/risk_engine/stress_testers/advanced_stress_scenarios.py

## Source File Analysis
- **File Path**: `app/engines/risk_engine/stress_testers/advanced_stress_scenarios.py`
- **Lines of Code**: 871
- **Language**: Python 3.10+
- **Purpose**: Advanced stress testing scenarios for liquidity, counterparty, and operational risk (Hull Chapter 20)

## Dependencies
### Internal
- `app.models.portfolio.Portfolio` - Portfolio model for risk analysis

### External
- `logging` - Structured logging
- `datetime` - Timestamp management
- `typing` - Type hints (Dict, List, Optional, Any)
- `numpy` - Numerical computations

## Classes/Functions

### LiquidityRiskStressTester
Tests portfolio resilience under liquidity crisis scenarios.

**Key Methods:**
- `_initialize_liquidity_scenarios()` - Defines 6 stress scenarios (baseline to flash crash)
- `calculate_liquidity_adjusted_var()` - Computes L-VaR = VaR + Liquidity Cost
- `run_liquidity_stress_tests()` - Batch execution of all scenarios
- `_interpret_lvar()` - Risk interpretation based on adjustment percentage

**Scenarios:**
1. Baseline Liquidity (1.0x multipliers)
2. Mild Liquidity Drought (2.0x spread, 0.7x volume)
3. Moderate Liquidity Crisis (4.0x spread, 0.4x volume)
4. Severe Liquidity Crisis (10.0x spread, 0.1x volume)
5. Flash Crash Liquidity Evaporation (20.0x spread, 30-min duration)
6. Asset-Specific Liquidity Crisis (8.0x spread for specific assets)

### CounterpartyRiskStressTester
Tests portfolio exposure to counterparty defaults.

**Key Methods:**
- `_initialize_counterparty_scenarios()` - Defines default scenarios (single to systemic)
- `calculate_counterparty_exposure()` - Computes LGD and CVA
- `_assess_counterparty_risk()` - Risk level classification (CRITICAL to LOW)

**Scenarios:**
1. Single Minor Counterparty Default (5% stress PD)
2. Single Major Counterparty Default (50% stress PD, 0.2 correlation increase)
3. Multiple Counterparty Defaults (3 defaults, 40% correlation)
4. Systemic Default Contagion (10 defaults, 80% correlation, 40% recovery)

### OperationalRiskStressTester
Tests resilience to operational failures.

**Key Methods:**
- `_initialize_operational_scenarios()` - Defines failure scenarios
- `calculate_operational_risk_impact()` - Estimates losses from operational events
- `_assess_operational_risk()` - Risk classification (0.5-5% loss thresholds)

**Scenarios:**
1. Trading System Outage (4 hours)
2. Critical Data Feed Failure (2 hours)
3. Settlement System Failure (24 hours, 1.5x penalties)
4. Operational Human Error (5% position error)
5. Cybersecurity Incident (48 hours, 2% reputation loss)
6. Critical Vendor Failure (12 hours)

### AdvancedStressTestOrchestrator
Combines all stress testing dimensions.

**Key Methods:**
- `run_comprehensive_advanced_stress_tests()` - Executes all test categories
- `_generate_overall_assessment()` - Aggregates risk scores
- `_risk_level_to_score()` - Maps LOW/MODERATE/HIGH/CRITICAL to 1-4 scale

## Business Logic

### Liquidity-Adjusted VaR Formula
```
L-VaR = VaR + 0.5 * Spread * Position Size + Market Impact Cost
```

### Counterparty Expected Loss
```
Expected Loss = Exposure * (1 - Recovery Rate) * PD * Correlation Multiplier
```

### Operational Loss Calculation
- Trading halt: `loss = portfolio_value * volatility * sqrt(duration)`
- Settlement delay: `loss = portfolio_value * penalty_rate * duration`
- Human error: `loss = portfolio_value * error_size_pct`

## Data Models

### Input Data Structures
- `portfolio`: Portfolio object with positions and total_equity
- `base_var`: Float, base VaR calculation
- `portfolio_volatility`: Float, daily volatility
- `counterparty_data`: Dict mapping counterparty -> {exposure, credit_quality, recovery_rate}

### Output Data Structures
```python
{
    'scenario': str,  # Scenario name
    'base_var': float,
    'liquidity_cost': float,  # or equivalent for other risk types
    'liquidity_adjusted_var': float,
    'liquidity_adjustment_pct': float,
    'risk_assessment': {
        'level': str,  # 'LOW' to 'CRITICAL'
        'action': str  # Recommended action
    }
}
```

## API Contracts

### LiquidityRiskStressTester.calculate_liquidity_adjusted_var()
**Args:**
- `portfolio`: Portfolio - Portfolio to analyze
- `base_var`: float - Base VaR
- `scenario_name`: str - Scenario identifier (default: 'moderate_liquidity_crisis')

**Returns:**
- `Dict`: L-VaR with interpretation

**Raises:**
- KeyError: Unknown scenario name
- AttributeError: Invalid portfolio object

### CounterpartyRiskStressTester.calculate_counterparty_exposure()
**Args:**
- `portfolio`: Portfolio - Portfolio to analyze
- `counterparty_data`: Dict - Counterparty information
- `scenario_name`: str - Default scenario (default: 'single_major_default')

**Returns:**
- `Dict`: Exposure, LGD, CVA, risk assessment

### OperationalRiskStressTester.calculate_operational_risk_impact()
**Args:**
- `portfolio`: Portfolio - Portfolio to analyze
- `portfolio_volatility`: float - Daily volatility
- `scenario_name`: str - Failure scenario (default: 'system_outage')

**Returns:**
- `Dict`: Estimated loss, loss percentage, risk level

### AdvancedStressTestOrchestrator.run_comprehensive_advanced_stress_tests()
**Args:**
- `portfolio`: Portfolio - Portfolio to test
- `base_var`: float - Base VaR
- `portfolio_volatility`: float - Daily volatility
- `counterparty_data`: Optional[Dict] - Counterparty data (optional)

**Returns:**
- `Dict`: Comprehensive results with overall assessment

## Error Handling

### Exception Handling Strategy
- **ValueError**: Invalid numerical inputs, negative values where positive required
- **TypeError**: Type conversion failures, None values where numeric expected
- **AttributeError**: Missing portfolio attributes
- **KeyError**: Unknown scenario names

### Error Responses
```python
{'error': 'Descriptive error message'}
```

### Logging
- ERROR: Calculation failures with stack traces
- WARNING: Missing optional data (counterparty_data)
- INFO: Scenario execution summaries

## Performance Considerations

### Optimization Targets
- Liquidity VaR calculation: O(n) where n = number of positions
- Scenario parallelization: Independent calculations enable parallel execution
- Memory: Single portfolio state, no large data structures

### Computational Complexity
- Liquidity stress test: O(n) per scenario
- Counterparty stress test: O(m) where m = number of counterparties
- Operational stress test: O(1) per scenario
- Full comprehensive test: O(n * s_liquidity + m * s_counterparty + s_operational)

### Best Practices
- Use scenario_names=None to run all scenarios (batch optimization)
- Provide counterparty_data only if needed (saves computation)
- Cache results for repeated scenario executions

## Testing Strategy

### Unit Tests Required
1. **LiquidityRiskStressTester**
   - Test each scenario with known inputs/outputs
   - Verify L-VaR calculation accuracy
   - Test edge cases (empty portfolio, zero volume)

2. **CounterpartyRiskStressTester**
   - Test LGD calculation with various recovery rates
   - Verify CVA approximation
   - Test correlation multiplier application

3. **OperationalRiskStressTester**
   - Test each impact type calculation
   - Verify duration-based loss formulas
   - Test risk level thresholds

### Integration Tests Required
1. AdvancedStressTestOrchestrator with real Portfolio
2. End-to-end stress testing workflow
3. Result aggregation accuracy

### Edge Cases to Test
- Empty portfolio
- Single position portfolio
- Zero base_var
- Zero volatility
- Missing counterparty_data
- Unknown scenario names

### Performance Tests
- Benchmark: 100 positions, 6 liquidity scenarios < 100ms
- Benchmark: 50 counterparties, 4 scenarios < 50ms
- Benchmark: Full comprehensive test < 500ms

## Security Considerations

### Input Validation
- Validate portfolio.total_equity > 0
- Validate base_var is finite and non-negative
- Validate portfolio_volatility is finite and non-negative
- Validate scenario_name exists in scenarios dict

### Output Sanitization
- All monetary values rounded to 2 decimal places
- Percentages clamped to 0-100 range
- Risk levels validated against allowed values

### Audit Trail
- Log all stress test executions with timestamp
- Record scenario parameters used
- Log any deviations from expected behavior

## Compliance

### Regulatory References
- Hull, "Risk Management and Financial Institutions", Chapter 20
- Basel III liquidity risk requirements
- FRTB (Fundamental Review of the Trading Book) stress testing

### Documentation Requirements
- Stress testing methodology documentation
- Scenario selection rationale
- Result interpretation guidelines
- Model validation requirements

## Maintenance

### Version History
- v1.0.0: Initial implementation with Hull Chapter 20 scenarios

### Future Enhancements
- Add custom scenario builder
- Implement scenario correlation analysis
- Add macroeconomic stress scenarios
- Implement scenario clustering for efficiency

---
*Requirements completed on 2026-02-07*
*GAP Audit Status: PASSED*
