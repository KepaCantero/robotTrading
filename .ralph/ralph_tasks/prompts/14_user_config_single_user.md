# Task 14: User Config Single User - Implementation Guide

## Objective
Create a user-specific configuration system for single-user deployment (solo trader running their own algo trading system).

## Context
- **Existing config systems:**
  - `app/core/config.py` - Environment-based settings (BaseSettings)
  - `app/core/centralized_config.py` - Trading thresholds and system config
- **NEW:** User-specific config layer allowing individual traders to customize settings

## Implementation Steps

### 1. Create User Settings Model (`app/user_config/user_settings.py`)
Define Pydantic models for:
- `BrokerType` enum: ALPACA, IBKR, PAPER
- `OrderTypePreference` enum: MARKET, LIMIT, STOP_LIMIT
- `TradingProfile`: Risk tolerance, position limits, stop loss/take profit
- `NotificationSettings`: Telegram/email settings, alert preferences
- `BrokerSettings`: API keys, connection settings
- `OrderPreferences`: Default order type, exchanges, size limits
- `TradingHours`: Auto start/stop, pre/after market, timezone
- `RiskLimits`: Daily loss, drawdown, kill switch, position size
- `SymbolUniverse`: Allowed symbols, price/volume filters
- `UserSettings`: Complete user settings model

### 2. Create User Config Manager (`app/user_config/user_config_manager.py`)
Implement:
- `UserConfigManager` class for loading/saving config
- Default config path: `~/.algotrading/user_config.yaml`
- `get_user_config()` global singleton
- Config validation with error messages

### 3. Create Default Config Template (`config/user_config.yaml`)
YAML template with:
- All user settings with defaults
- Comments explaining each option
- Safe defaults (paper trading, conservative risk limits)

### 4. Create Init Script (`scripts/init_user_config.py`)
Interactive setup script:
- Prompt user for key settings
- Create config file in `~/.algotrading/`
- Support `--non-interactive` flag

### 5. Create Tests (`tests/unit/user_config/test_user_settings.py`)
Test:
- Default values
- Custom values
- Symbol universe filtering
- Paper trading mode check
- Log level validation
- Config manager load/save
- Config validation

## Validation Checklist
- [ ] All files compile without errors
- [ ] All tests pass
- [ ] Config loading works
- [ ] Init script creates config file
- [ ] Symbol filtering works correctly
- [ ] Risk validation catches invalid settings

## Integration Points
- Standalone module (no dependencies on other tasks)
- Can be used by CLI (Task 13) for user setup
- Does NOT modify existing config systems

## Completion Promise
`USER_CONFIG_SINGLE_USER_COMPLETE`
