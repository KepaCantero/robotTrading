# Centralized Configuration System

## Overview

The centralized configuration system eliminates magic values scattered throughout the codebase and provides a unified way to manage all application settings, trading thresholds, and strategy parameters.

## Features

- **Unified Configuration**: Single source of truth for all application settings
- **Environment-Specific**: Different configurations for development, testing, staging, and production
- **Strategy-Specific Parameters**: Individual configuration for each trading strategy
- **Validation**: Built-in validation for all configuration values
- **Hot Reloading**: Ability to reload configuration without restarting the application
- **Type Safety**: Pydantic models ensure type safety and validation

## Configuration Structure

### Trading Thresholds

```python
class TradingThresholds(BaseModel):
    # Signal thresholds
    min_signal_strength: float = 60.0
    min_signal_confidence: float = 70.0
    min_liquidity_score: float = 50.0
    
    # RSI thresholds
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    
    # Position sizing
    max_position_size: float = 0.1
    min_position_size: float = 0.01
    
    # Risk management
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.15
    daily_loss_limit: float = 0.05
    max_drawdown_limit: float = 0.15
    
    # Exposure limits
    max_total_exposure: float = 0.8
    max_sector_exposure: float = 0.3
    max_correlation: float = 0.7
    
    # Circuit breaker thresholds
    circuit_breaker_daily_loss: float = 0.03
    circuit_breaker_drawdown: float = 0.1
    circuit_breaker_volatility: float = 0.05
    circuit_breaker_error_rate: float = 0.05
    
    # Latency thresholds
    max_latency_ms: int = 1000
    max_execution_time_ms: int = 500
```

### Strategy Configuration

Each strategy has its own configuration file in `config/strategies/`:

```yaml
# config/strategies/momentum.yaml
momentum:
  name: "momentum"
  enabled: true
  weight: 1.0
  
  # Strategy-specific parameters
  parameters:
    rsi_threshold: 40
    momentum_threshold: 0.02
    volume_threshold: 1.5
    lookback_period: 14
    
  # Risk parameters (override global if needed)
  max_position_size: 0.1
  stop_loss_pct: 0.05
  take_profit_pct: 0.10
  
  # Performance thresholds
  min_sharpe_ratio: 1.2
  max_drawdown: 0.12
  min_win_rate: 0.45
```

### Environment Configuration

Environment-specific settings are managed through `.env` files:

```bash
# config/centralized.env
ENVIRONMENT=development
DEBUG=true

# Trading Thresholds
MIN_SIGNAL_STRENGTH=60.0
MIN_SIGNAL_CONFIDENCE=70.0
MIN_LIQUIDITY_SCORE=50.0

# Risk Management
STOP_LOSS_PCT=0.05
TAKE_PROFIT_PCT=0.15
DAILY_LOSS_LIMIT=0.05
MAX_DRAWDOWN_LIMIT=0.15

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=algotrading_dev
DB_USER=postgres
DB_PASSWORD=password
```

## Usage

### Basic Usage

```python
from app.core.centralized_config import get_config, get_trading_threshold, get_strategy_config

# Get global configuration
config = get_config()

# Get specific trading threshold
max_position_size = get_trading_threshold("max_position_size")

# Get strategy configuration
momentum_config = get_strategy_config("momentum")
```

### Strategy Integration

Strategies automatically load their configuration:

```python
class MomentumStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Load strategy-specific configuration
        strategy_config = get_strategy_config("momentum")
        if strategy_config:
            params = strategy_config.parameters
            self.rsi_threshold = Decimal(str(params.get("rsi_threshold", 40)))
            
            # Use strategy-specific risk parameters or fallback to global
            self.stop_loss = Decimal(str(strategy_config.stop_loss_pct or get_trading_threshold("stop_loss_pct")))
```

### Updating Configuration

```python
from app.core.centralized_config import update_strategy_config, save_strategy_config

# Update strategy configuration
update_strategy_config("momentum", {
    "enabled": True,
    "weight": 1.2,
    "parameters": {
        "rsi_threshold": 35,
        "momentum_threshold": 0.03
    }
})

# Save to file
save_strategy_config("momentum")
```

## Migration from Magic Values

The system includes a migration script to convert hardcoded values to centralized configuration:

```bash
# Scan for magic values
python scripts/migrate_configuration.py --scan-only

# Apply migration
python scripts/migrate_configuration.py

# Validate configuration
python scripts/migrate_configuration.py --validate-only
```

## Configuration Files

### Global Configuration
- `config/centralized.env` - Environment variables
- `app/core/centralized_config.py` - Configuration models and logic

### Strategy Configurations
- `config/strategies/momentum.yaml` - Momentum strategy settings
- `config/strategies/mean_reversion.yaml` - Mean reversion strategy settings
- `config/strategies/pairs_trading.yaml` - Pairs trading strategy settings

### Environment-Specific
- `config/development.env` - Development environment
- `config/testing.env` - Testing environment
- `config/staging.env` - Staging environment
- `config/production.env` - Production environment

## Validation

The configuration system includes comprehensive validation:

```python
# Validate entire configuration
is_valid = validate_configuration()

# Get configuration summary
summary = get_config_summary()
```

## Benefits

1. **Eliminates Magic Values**: No more hardcoded numbers scattered throughout the code
2. **Centralized Management**: All settings in one place
3. **Environment-Specific**: Different configurations for different environments
4. **Strategy-Specific**: Individual parameters for each trading strategy
5. **Type Safety**: Pydantic models ensure data integrity
6. **Hot Reloading**: Update configuration without restarting
7. **Validation**: Built-in validation prevents invalid configurations
8. **Documentation**: Self-documenting configuration structure

## Best Practices

1. **Use Configuration Functions**: Always use `get_trading_threshold()` instead of hardcoded values
2. **Strategy-Specific Overrides**: Use strategy-specific parameters when needed
3. **Environment Variables**: Use environment variables for sensitive data
4. **Validation**: Always validate configuration after changes
5. **Documentation**: Document any new configuration parameters
6. **Testing**: Test configuration changes thoroughly

## Troubleshooting

### Common Issues

1. **Configuration Not Loading**: Check file paths and permissions
2. **Validation Errors**: Verify parameter ranges and types
3. **Strategy Not Found**: Ensure strategy configuration file exists
4. **Environment Variables**: Check `.env` file loading

### Debug Commands

```bash
# Validate current configuration
python scripts/migrate_configuration.py --validate-only

# Scan for remaining magic values
python scripts/migrate_configuration.py --scan-only

# Get configuration summary
python -c "from app.core.centralized_config import get_config_summary; print(get_config_summary())"
```

## Future Enhancements

1. **Dynamic Configuration**: Real-time configuration updates via API
2. **Configuration UI**: Web interface for configuration management
3. **Configuration Versioning**: Track configuration changes over time
4. **A/B Testing**: Support for configuration experiments
5. **Configuration Templates**: Predefined configuration templates for common scenarios
