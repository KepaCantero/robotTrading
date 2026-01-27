# Configuration Quick Reference

## Two Config Files, Clear Purposes

### `config/profile_batch_backtest.yaml` - Workflow
**What**: Database, symbols, dates, parallelization, output
**When**: Running batch backtests across 180 profiles
**How**: Loaded by `ProfileBatchBacktester`

### `config/backtesting/profile_optimization.yaml` - Parameters
**What**: Model params, threshold ranges, validation settings, profile/tier overrides
**When**: Any backtesting or optimization operation
**How**: Loaded by `ProfileConfigLoader`

---

## Quick Commands

```bash
# Validate all configs
python -m app.core.config_validator --all-backtesting

# Run batch backtest
python run_profile_batch_backtester.py --all

# Load in code
from app.core.config.profile_config_loader import get_profile_config_loader
loader = get_profile_config_loader(profile="aggressive", tier="medium")
```

---

## What Goes Where?

| Setting | Location |
|---------|----------|
| Database URL | `profile_batch_backtest.yaml` |
| Symbols to test | `profile_batch_backtest.yaml` |
| Backtest dates | `profile_batch_backtest.yaml` |
| Capital tiers | `profile_batch_backtest.yaml` |
| Max parallel profiles | `profile_batch_backtest.yaml` |
| Model parameters | `profile_optimization.yaml` |
| Threshold ranges | `profile_optimization.yaml` |
| Validation thresholds | `profile_optimization.yaml` |
| Threading workers | `profile_optimization.yaml` |
| Profile overrides | `profile_optimization.yaml` |
| Tier overrides | `profile_optimization.yaml` |

---

## Common Tasks

### Add a new model parameter
Edit: `config/backtesting/profile_optimization.yaml` -> `models` section

### Change symbols to test
Edit: `config/profile_batch_backtest.yaml` -> `symbols` section

### Adjust validation thresholds
Edit: `config/backtesting/profile_optimization.yaml` -> `validation.thresholds`

### Add profile-specific override
Edit: `config/backtesting/profile_optimization.yaml` -> `profiles` section

### Change parallelization
Edit: `config/profile_batch_backtest.yaml` -> `parallelization` (profile-level)
Edit: `config/backtesting/profile_optimization.yaml` -> `threading` (backtest-level)

---

## Validation

All configs validated automatically on load. Manual validation:

```bash
python -m app.core.config_validator --all-backtesting
```

Expected output:
```
All backtesting configurations are valid!
```

---

**See**: `CONFIG_CONSOLIDATION_SUMMARY.md` for detailed documentation
