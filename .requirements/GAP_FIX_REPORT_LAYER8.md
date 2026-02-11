# GAP Fix Report - Layer 8

**Date**: 2026-02-05T20:18:07.038463
**Files Processed**: 13
**Total Fixes Applied**: 219

## Detailed Results


### capa2_endpoints.py

**Status**: fixed

**Fixes Applied**: 35

**Fixes**:

- Line 96: Replaced magic number 600 with DEFAULT_VALUE_600
- Line 239: Replaced magic number 8 with DEFAULT_VALUE_8
- Line 255: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 274: Replaced magic number 8 with DEFAULT_VALUE_8
- Line 281: Replaced magic number 5 with DEFAULT_VALUE_5
- Line 290: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 303: Replaced magic number 17 with DEFAULT_VALUE_17
- Line 307: Replaced magic number 8 with DEFAULT_VALUE_8
- Line 313: Replaced magic number 17 with DEFAULT_VALUE_17
- Line 325: Replaced magic number 400 with DEFAULT_VALUE_400

**Backup**: app/presentation/controllers/capa2_endpoints.py.backup


### momentum.py

**Status**: fixed

**Fixes Applied**: 73

**Fixes**:

- Line 50: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 65: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 80: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 86: Replaced magic number 404 with DEFAULT_VALUE_404
- Line 138: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 204: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 218: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 224: Replaced magic number 404 with DEFAULT_VALUE_404
- Line 262: Replaced magic number 24 with MAX_24
- Line 263: Replaced magic number 50 with MAX_50

**Backup**: app/presentation/controllers/momentum.py.backup


### optimization.py

**Status**: fixed

**Fixes Applied**: 25

**Fixes**:

- Line 91: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 93: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 95: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 124: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 126: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 128: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 151: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 177: Replaced magic number 404 with DEFAULT_VALUE_404
- Line 184: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 205: Replaced magic number 500 with DEFAULT_VALUE_500

**Backup**: app/presentation/controllers/optimization.py.backup


### paper_trading.py

**Status**: skipped



### portfolio.py

**Status**: fixed

**Fixes Applied**: 23

**Fixes**:

- Line 6: Replaced magic number 95 with DEFAULT_PERCENT_95
- Line 87: Replaced magic number 503 with DEFAULT_VALUE_503
- Line 94: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 117: Replaced magic number 503 with DEFAULT_VALUE_503
- Line 123: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 147: Replaced magic number 404 with DEFAULT_VALUE_404
- Line 152: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 175: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 200: Replaced magic number 404 with DEFAULT_VALUE_404
- Line 206: Replaced magic number 500 with DEFAULT_VALUE_500

**Backup**: app/presentation/controllers/portfolio.py.backup


### portfolio_analytics.py

**Status**: fixed

**Fixes Applied**: 5

**Fixes**:

- Line 147: Replaced magic number 50 with DEFAULT_VALUE_50
- Line 158: Replaced magic number 25 with DEFAULT_VALUE_25
- Line 320: Replaced magic number 60 with DEFAULT_VALUE_60
- Line 321: Replaced magic number 40 with DEFAULT_VALUE_40
- Added 4 constants after imports

**Backup**: app/presentation/controllers/portfolio_analytics.py.backup


### portfolio_controller.py

**Status**: skipped



### profitability_validation.py

**Status**: fixed

**Fixes Applied**: 30

**Fixes**:

- Line 65: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 70: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 73: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 89: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 118: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 121: Replaced magic number 50 with DEFAULT_VALUE_50
- Line 123: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 124: Replaced magic number 50 with MAX_50
- Line 146: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 174: Replaced magic number 400 with DEFAULT_VALUE_400

**Backup**: app/presentation/controllers/profitability_validation.py.backup


### signals.py

**Status**: fixed

**Fixes Applied**: 23

**Fixes**:

- Line 119: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 141: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 175: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 266: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 291: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 296: Replaced magic number 60 with MAX_60
- Line 320: Replaced magic number 500 with DEFAULT_VALUE_500
- Line 346: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 351: Replaced magic number 400 with DEFAULT_VALUE_400
- Line 362: Replaced magic number 500 with DEFAULT_VALUE_500

**Backup**: app/presentation/controllers/signals.py.backup


### strategies.py

**Status**: fixed

**Fixes Applied**: 2

**Fixes**:

- Line 2: Replaced magic number 31 with DEFAULT_VALUE_31
- Added 1 constants after imports

**Backup**: app/presentation/controllers/strategies.py.backup


### strategy_controller.py

**Status**: skipped



### trading_error_handler.py

**Status**: fixed

**Fixes Applied**: 3

**Fixes**:

- Line 3: Replaced magic number 14 with DEFAULT_VALUE_14
- Added 1 constants after imports
- Line 97: Added return type Dict[str, Any] to __init__

**Backup**: app/presentation/controllers/trading_error_handler.py.backup


### dashboard_views.py

**Status**: skipped


