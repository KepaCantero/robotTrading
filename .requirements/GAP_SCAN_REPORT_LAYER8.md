# GAP Violation Scan Report - Layer 8

**Date**: 2026-02-05T20:17:34.452490
**Files Scanned**: 13
**Total Violations**: 49

## Detailed Results


### app/presentation/controllers/capa2_endpoints.py

**Total Violations**: 22

#### magic_number (22)

- Line 239: {'line': 239, 'number': 8, 'code': 'input_id = f"input_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"'}
- Line 274: {'line': 274, 'number': 8, 'code': 'profile_id = f"profile_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"'}
- Line 281: {'line': 281, 'number': 5, 'code': 'risk_profile=5,'}
- Line 303: {'line': 303, 'number': 17, 'code': 'Applies investment profile to 17+ trading modules.'}
- Line 307: {'line': 307, 'number': 8, 'code': 'parameter_set_id = f"params_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp'}
- ... and 17 more


### app/presentation/controllers/momentum.py

**Total Violations**: 10

#### magic_number (10)

- Line 262: {'line': 262, 'number': 24, 'code': 'max_age_hours: int = Query(24, ge=1, description="Maximum signal age in hours"),'}
- Line 263: {'line': 263, 'number': 50, 'code': 'limit: int = Query(50, ge=1, le=200, description="Maximum number of signals to r'}
- Line 332: {'line': 332, 'number': 50, 'code': 'limit: int = Query(10, ge=1, le=50, description="Number of top signals to return'}
- Line 418: {'line': 418, 'number': 24, 'code': 'signal_duration=strategy_data.get("signal_duration", 24),'}
- Line 419: {'line': 419, 'number': 30, 'code': 'rsi_oversold=strategy_data.get("rsi_oversold", 30),'}
- ... and 5 more


### app/presentation/controllers/optimization.py

**Total Violations**: 2

#### magic_number (2)

- Line 296: {'line': 296, 'number': 12, 'code': 'data_end_date=date(2023, 12, 31),'}
- Line 296: {'line': 296, 'number': 31, 'code': 'data_end_date=date(2023, 12, 31),'}


### app/presentation/controllers/portfolio.py

**Total Violations**: 1

#### magic_number (1)

- Line 6: {'line': 6, 'number': 95, 'code': 'Security Compliance: 95%'}


### app/presentation/controllers/portfolio_analytics.py

**Total Violations**: 4

#### magic_number (4)

- Line 147: {'line': 147, 'number': 50, 'code': 'quantity=Decimal("50"),'}
- Line 158: {'line': 158, 'number': 25, 'code': 'quantity=Decimal("25"),'}
- Line 320: {'line': 320, 'number': 60, 'code': 'equity_allocation = request.target_equity_allocation or Decimal("60")'}
- Line 321: {'line': 321, 'number': 40, 'code': 'cash_allocation = request.target_cash_allocation or Decimal("40")'}


### app/presentation/controllers/profitability_validation.py

**Total Violations**: 5

#### magic_number (5)

- Line 121: {'line': 121, 'number': 50, 'code': 'if len(requests) > 50:  # Límite de seguridad'}
- Line 124: {'line': 124, 'number': 50, 'code': 'detail="Maximum 50 strategies can be validated in a single batch",'}
- Line 331: {'line': 331, 'number': 5, 'code': 'min_profit_margin=Decimal("5"),'}
- Line 334: {'line': 334, 'number': 15, 'code': 'max_drawdown_limit=Decimal("15"),'}
- Line 335: {'line': 335, 'number': 50, 'code': 'min_win_rate=Decimal("50"),'}


### app/presentation/controllers/signals.py

**Total Violations**: 2

#### magic_number (1)

- Line 296: {'line': 296, 'number': 60, 'code': 'max_age_minutes: int = 60,'}

#### long_line (1)

- Line 358: {'line': 358, 'length': 115, 'preview': '"message": f"Updated thresholds: confidence={confidence_threshold}%, liquidity={...'}


### app/presentation/controllers/strategies.py

**Total Violations**: 1

#### magic_number (1)

- Line 2: {'line': 2, 'number': 31, 'code': 'API endpoints para gestión de estrategias - TASK-31'}


### app/presentation/controllers/trading_error_handler.py

**Total Violations**: 2

#### missing_return_type (1)

- Line 93: {'line': 93, 'function': '__init__', 'code': 'def __init__(self, message: str):'}

#### magic_number (1)

- Line 3: {'line': 3, 'number': 14, 'code': 'TASK-14: Unificación de Error Handling'}

