# Modular Configuration Architecture

## Overview

The configuration system has been refactored into a modular architecture to improve maintainability and scalability. The original `centralized_config.py` file (3386 lines) has been split into specialized modules.

## Directory Structure

```
app/core/config/
├── __init__.py              # Existing ProfileConfigLoader exports
├── base.py                  # Base classes and utilities
├── signal_risk.py           # Signal thresholds, risk management, circuit breakers
├── position_sizing.py       # Position sizing and portfolio allocation
├── technical_indicators.py  # Technical indicators and analysis parameters
├── infrastructure.py        # Database, Redis, API, logging, monitoring
├── compliance.py            # Compliance Engine configuration
└── trading_config.py        # Main aggregated configuration (for backward compatibility)
```

## Module Descriptions

### 1. `base.py`
- `Environment` enum (DEVELOPMENT, TESTING, STAGING, PRODUCTION)
- `ConfigBase` - Base class for all configuration models
- `SettingsBase` - Base class for settings that load from environment variables

### 2. `signal_risk.py`
- `SignalThresholds` - Signal strength, confidence, scoring parameters
- `RiskManagementThresholds` - Stop loss, take profit, exposure limits
- `CircuitBreakerThresholds` - Circuit breaker parameters
- `SlippageThresholds` - Volatility and spread thresholds
- `PerformanceThresholds` - Latency and execution time thresholds

### 3. `position_sizing.py`
- `PositionSizingThresholds` - Position size limits, ATR filter, trailing stop
- `PortfolioAllocationThresholds` - Strategy weights, rebalancing parameters
- `AccountConfiguration` - Account settings, tax optimization

### 4. `technical_indicators.py`
- `TechnicalIndicatorThresholds` - RSI, Z-scores, correlation thresholds
- `WindowSizes` - Moving average windows, sequence lengths
- `ConversionMultipliers` - BPS, percentage, milliseconds multipliers
- `PerformanceMetrics` - Sharpe ratio, fill rate, confidence thresholds
- `FundamentalAnalysisThresholds` - P/E, P/B, ROE, dividend thresholds
- `DividendThresholds` - Dividend yield, growth, payout ratio
- `FXCarryTradeThresholds` - FX rate simulation, interest differential
- `CoveredCallThresholds` - OTM percentage, DTE parameters

### 5. `infrastructure.py`
- `DatabaseConfig` - PostgreSQL and QuestDB configuration
- `RedisConfig` - Redis cache configuration
- `APIConfig` - API server configuration
- `LoggingConfig` - Logging parameters
- `MonitoringConfig` - Prometheus, Grafana, alerts

### 6. `compliance.py`
- Hastie (Statistical Learning) thresholds
- Lopez de Prado (Meta-labeling) thresholds
- O'Hara (Microstructure) thresholds
- Backtesting, execution, and strategy health thresholds
- Confidence adjustment thresholds
- Risk management thresholds
- SLO and TDD thresholds
- Post-trade analysis thresholds

### 7. `trading_config.py`
- `TradingThresholds` - Aggregated trading configuration
- `StrategyConfig` - Individual strategy configuration
- `CurrencyHedgingConfig` - Currency hedging parameters
- `SectorCountryDiversificationConfig` - Diversification constraints
- `CentralizedConfig` - Main configuration class
- Helper functions: `get_config()`, `get_trading_threshold()`, etc.

## Usage

### For New Code

Import directly from the modular components:

```python
from app.core.config.signal_risk import SignalThresholds, RiskManagementThresholds
from app.core.config.position_sizing import PositionSizingThresholds
from app.core.config.compliance import ComplianceConfig

# Use specific configuration classes
signal_config = SignalThresholds()
risk_config = RiskManagementThresholds()
```

### For Existing Code (Backward Compatibility)

Continue using `centralized_config.py` - it will be updated to import from the modular components:

```python
from app.core.centralized_config import get_config, CentralizedConfig

config = get_config()
print(config.trading.min_signal_strength)
print(config.compliance.MIN_LIQUIDITY_SCORE)
```

## Migration Path

1. **Phase 1** (Current): Create modular structure
   - ✅ Created base.py, signal_risk.py, position_sizing.py, etc.
   - ✅ Created trading_config.py with aggregated configuration

2. **Phase 2**: Update centralized_config.py
   - Import from modular components instead of defining locally
   - Maintain all existing exports for backward compatibility

3. **Phase 3**: Gradual migration
   - New code imports from modular components
   - Existing code continues to work through centralized_config.py
   - Gradually update imports file by file

## Benefits

1. **Maintainability**: Each module is focused and easier to understand
2. **Scalability**: New configuration can be added to appropriate modules
3. **Testability**: Individual modules can be tested in isolation
4. **Backward Compatibility**: Existing code continues to work without changes
5. **Code Organization**: Related configuration is grouped together

## Configuration Hierarchy

```
CentralizedConfig
├── environment: Environment
├── debug: bool
├── trading: TradingThresholds
│   ├── Signal thresholds
│   ├── Risk management
│   ├── Position sizing
│   ├── Circuit breakers
│   └── Performance thresholds
├── compliance: ComplianceConfig
│   ├── Hastie thresholds
│   ├── Lopez de Prado thresholds
│   ├── O'Hara thresholds
│   └── Execution thresholds
├── database: DatabaseConfig
├── redis: RedisConfig
├── api: APIConfig
├── logging: LoggingConfig
├── monitoring: MonitoringConfig
├── currency_hedging: CurrencyHedgingConfig
├── diversification: SectorCountryDiversificationConfig
└── strategies: Dict[str, StrategyConfig]
```

## Adding New Configuration

1. Identify the appropriate module (or create a new one)
2. Add the configuration class with proper Field definitions
3. Add validators if needed
4. Export from the module's `__all__`
5. Update `trading_config.py` if it's a core configuration

Example:

```python
# In app/core/config/signal_risk.py
class NewFeatureThresholds(ConfigBase):
    new_param: float = Field(default=0.5, description="New parameter")

# Add to __all__ in the module
__all__ = ["SignalThresholds", "NewFeatureThresholds", ...]
```
