# Profile Batch Backtesting Services - Quick Reference

## Service Overview

This document provides a quick reference for all services in the profile batch backtesting service layer.

---

## 1. ConfigurationService

**File:** `configuration_service.py`  
**Responsibility:** Load and validate YAML configurations

### Constructor
```python
ConfigurationService(config_path: str)
```

### Key Methods
| Method | Returns | Description |
|--------|---------|-------------|
| `get_capital_tiers()` | `ConfigDict` | Capital tier mappings |
| `load_investment_horizons()` | `List[int]` | Validated horizon values |
| `get_optimization_config()` | `ConfigDict` | Optimization settings |
| `get_validation_config()` | `ConfigDict` | Validation settings |
| `get_acceptance_criteria()` | `ConfigDict` | Acceptance thresholds |
| `get_risk_parameters(risk_key)` | `ConfigDict` | Risk level parameters |
| `get_objective_parameters(obj_key)` | `ConfigDict` | Objective parameters |

---

## 2. ProfileGenerationService

**File:** `profile_generation_service.py`  
**Responsibility:** Generate investor profile combinations

### Constructor
```python
ProfileGenerationService(capital_tiers: ConfigDict)
```

### Key Methods
| Method | Returns | Description |
|--------|---------|-------------|
| `generate_all_profiles(horizons)` | `List[InputProfile]` | All profile combos |
| `get_capital_tier_key(profile)` | `str` (static) | Map tier to config key |

---

## 3. BatchExecutionService

**File:** `batch_execution_service.py`  
**Responsibility:** Execute batch tests (parallel/sequential)

### Constructor
```python
BatchExecutionService(config_path: str, database_service: DatabaseService)
```

### Key Methods
| Method | Returns | Description |
|--------|---------|-------------|
| `run_all_profiles(profiles, backtester_class, parallel, max_workers)` | `Dict[str, ProfileResult]` | Execute all profiles |

---

## 4. DatabaseService

**File:** `database_service.py`  
**Responsibility:** Store and query results

### Constructor
```python
DatabaseService(db_url: str, output_dir: Path)
```

### Key Methods
| Method | Returns | Description |
|--------|---------|-------------|
| `store_result(result)` | `None` | Store single result |
| `batch_store_results(results)` | `None` | Store multiple results |
| `get_best_strategy(objective, tier, risk)` | `Dict[str, Any]` | Query best strategy |

---

## 5. MetricsCalculationService

**File:** `metrics_service.py`  
**Responsibility:** Calculate improvements and comparisons

### Constructor
```python
MetricsCalculationService(acceptance_criteria: ConfigDict)
```

### Key Methods
| Method | Returns | Description |
|--------|---------|-------------|
| `calculate_improvements(baseline, optimized)` | `Dict[str, float]` | Improvement metrics |
| `generate_comparison(baseline, optimized, optuna)` | `BaselineOptimizationComparison` | Full comparison |
| `calculate_parameter_importance(history)` | `Dict[str, float]` | Parameter scores |
| `evaluate_readiness(profile, optimized, improvements)` | `Tuple[bool, str]` | Ready for paper trading? |
| `generate_recommendation(comparison, ready)` | `str` | Final recommendation |

---

## 6. FallbackTracker

**File:** `fallback_tracker.py`  
**Responsibility:** Track fallback metrics thread-safely

### Constructor
```python
FallbackTracker()
```

### Key Methods
| Method | Returns | Description |
|--------|---------|-------------|
| `increment_fallback_counter(type)` | `None` | Increment counter |
| `get_fallback_metrics()` | `Dict[str, int]` | Get all counts |
| `log_fallback_summary()` | `None` | Log summary with interpretation |

**Fallback types:**
- `"profile_config_loader"`: ProfileConfigLoader failed
- `"profile_strategy_mapper"`: ProfileStrategyMapper failed
- `"config_key_mismatch"`: Config key missing

---

## 7. ReportGenerationService

**File:** `report_generation_service.py`  
**Responsibility:** Generate HTML reports and exports

### Constructor
```python
ReportGenerationService(output_dir: str)
```

### Key Methods
| Method | Returns | Description |
|--------|---------|-------------|
| `generate_comparison_report(results)` | `str` | HTML report |
| `generate_batch_summary(results, fallback_metrics)` | `None` | JSON summary |
| `export_results(results, format)` | `Path` | Export to file |

**Export formats:** `"json"`, `"csv"`, `"excel"`

---

## 8. Data Models

**File:** `models.py`  
**Models:** `ProfileResultDB`, `BaselineOptimizationComparison`, `OptimizedStrategy`, `ProfileResult`

### ProfileResultDB (SQLAlchemy)
```python
# Database columns
id, profile_id, objective, risk_tolerance, capital_tier, investment_horizon
baseline_sharpe, baseline_return, baseline_max_dd, baseline_win_rate
optimized_sharpe, optimized_return, optimized_max_dd, optimized_win_rate
sharpe_improvement, return_improvement, max_dd_improvement, win_rate_improvement
best_parameters, walk_forward_passed, monte_carlo_passed, out_of_sample_passed
ready_for_paper_trading, recommendation, created_at, updated_at
```

### BaselineOptimizationComparison (dataclass)
```python
sharpe_improvement, return_improvement, max_dd_improvement, win_rate_improvement
sharpe_significant, return_significant
parameter_importance: Dict[str, float]
recommended, confidence, reason
```

### OptimizedStrategy (dataclass)
```python
profile_id, baseline_metrics, optimized_metrics, best_parameters
optimization_history, walk_forward_results, monte_carlo_results, out_of_sample_results
comparison, ready_for_paper_trading, recommendation
```

### ProfileResult (dataclass)
```python
profile_id, profile, baseline_results, optimization_results
best_parameters, improvement_metrics, comparison
ready_for_paper_trading, recommendation, created_at
strategy_mapping, enabled_strategies, learning_engines, ensemble_config, per_strategy_results
```

---

## Usage Patterns

### Pattern 1: Using ConfigurationService
```python
config_service = ConfigurationService("config/profile_batch_backtest.yaml")
tiers = config_service.get_capital_tiers()
horizons = config_service.load_investment_horizons()
```

### Pattern 2: Using ProfileGenerationService
```python
gen_service = ProfileGenerationService(capital_tiers)
profiles = gen_service.generate_all_profiles(horizons)
```

### Pattern 3: Using DatabaseService
```python
db_service = DatabaseService("sqlite:///results.db", Path("output"))
db_service.store_result(profile_result)
best = db_service.get_best_strategy("growth", "medio", "alto")
```

### Pattern 4: Using MetricsCalculationService
```python
metrics_service = MetricsCalculationService(acceptance_criteria)
improvements = metrics_service.calculate_improvements(baseline, optimized)
comparison = metrics_service.generate_comparison(baseline, optimized, optuna_results)
ready, rec = metrics_service.evaluate_readiness(profile, optimized, improvements)
```

### Pattern 5: Using FallbackTracker
```python
fallback_tracker = FallbackTracker()
# Track fallbacks
fallback_tracker.increment_fallback_counter("profile_config_loader")
# Log summary at end
fallback_tracker.log_fallback_summary()
```

### Pattern 6: Using ReportGenerationService
```python
report_service = ReportGenerationService("output")
html = report_service.generate_comparison_report(results)
report_service.export_results(results, format="excel")
```

---

## Type Aliases

```python
ConfigDict = Dict[str, Any]
MetricsDict = Dict[str, Union[float, int, str, bool, None]]
ParameterDict = Dict[str, Any]
OptimizationHistoryEntry = Dict[str, Any]
ValidationResultDict = Dict[str, Any]
PerStrategyResultsDict = Dict[str, Dict[str, Any]]
```

---

## Thread Safety

- **FallbackTracker:** Uses `threading.Lock` for all counter operations
- **DatabaseService:** Uses `threading.Lock` for batch operations
- **Other services:** Stateless or read-only, inherently thread-safe

---

## Error Handling

All services use proper exception handling:

```python
# Database errors
from sqlalchemy.exc import IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError

# File I/O errors
try:
    with open(path) as f:
        ...
except FileNotFoundError:
    logger.error(f"File not found: {path}")
```

---

## Dependencies

```python
# Core
from pathlib import Path
from typing import Dict, List, Optional, Any
from decimal import Decimal
import logging
import threading

# External
import yaml
import pandas as pd
import numpy as np
from jinja2 import Template

# SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import *

# App imports
from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.core.tier_mapper import map_profile_tier_to_config
from app.services.profile_driven_trading.profile_strategy_mapper import StrategyMapping
```

---

## Testing Guidelines

### Unit Test Example
```python
def test_configuration_service():
    service = ConfigurationService("test_config.yaml")
    horizons = service.load_investment_horizons()
    assert isinstance(horizons, list)
    assert all(isinstance(h, int) for h in horizons)
```

### Integration Test Example
```python
def test_profile_generation():
    config_service = ConfigurationService("test_config.yaml")
    gen_service = ProfileGenerationService(config_service.get_capital_tiers())
    horizons = config_service.load_investment_horizons()
    profiles = gen_service.generate_all_profiles(horizons)
    assert len(profiles) > 0
```

---

For more detailed information, see:
- `PROFILE_BATCH_REFACTORING_REPORT.md` - Full refactoring report
- `IMPLEMENTATION_SUMMARY.md` - Implementation status
- Individual service files - Complete docstrings
