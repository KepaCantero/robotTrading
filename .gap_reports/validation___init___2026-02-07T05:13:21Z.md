# Validation Report: app/domain/entities/__init__.py
**Generated:** 2026-02-07T05:13:21Z

## 1. Type Checking (mypy)
app/microstructure/trading_mechanisms.py:74: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/trading_mechanisms.py:238: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/trading_mechanisms.py:290: error: Incompatible return value type (got "Union[Decimal, Literal[0]]", expected "Decimal")  [return-value]
app/microstructure/trading_mechanisms.py:294: error: Incompatible return value type (got "Union[Decimal, Literal[0]]", expected "Decimal")  [return-value]
app/microstructure/trading_mechanisms.py:641: error: Unsupported operand types for * ("Decimal" and "float")  [operator]
app/microstructure/trading_mechanisms.py:645: error: Unsupported operand types for * ("float" and "Decimal")  [operator]
app/microstructure/trading_mechanisms.py:758: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
app/microstructure/trading_mechanisms.py:885: error: Argument "key" to "max" has incompatible type "Callable[[str], object]"; expected "Callable[[str], Union[SupportsDunderLT[Any], SupportsDunderGT[Any]]]"  [arg-type]
app/microstructure/trading_mechanisms.py:885: error: Incompatible return value type (got "object", expected "Union[SupportsDunderLT[Any], SupportsDunderGT[Any]]")  [return-value]
app/microstructure/trading_mechanisms.py:915: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/trading_mechanisms.py:916: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/trading_mechanisms.py:917: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/trading_mechanisms.py:918: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/domain/entities/portfolio.py:580: error: Missing positional arguments "stop_loss_pct", "take_profit_pct" in call to "RiskParameters"  [call-arg]
app/domain/factories/__init__.py:466: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
app/domain/factories/__init__.py:467: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
app/domain/factories/__init__.py:468: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
app/domain/factories/__init__.py:469: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
app/domain/factories/__init__.py:470: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
app/domain/factories/__init__.py:471: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
app/domain/factories/__init__.py:472: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
app/domain/factories/__init__.py:473: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
app/domain/factories/__init__.py:474: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
app/domain/factories/__init__.py:698: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
app/data/feeds.py:95: error: Name "HTTPError" is not defined  [name-defined]
app/data/feeds.py:95: error: Name "RequestException" is not defined  [name-defined]
app/data/feeds.py:114: error: Name "HTTPError" is not defined  [name-defined]
app/data/feeds.py:114: error: Name "RequestException" is not defined  [name-defined]
app/data/feeds.py:228: error: Name "HTTPError" is not defined  [name-defined]
app/data/feeds.py:228: error: Name "RequestException" is not defined  [name-defined]
app/data/feeds.py:251: error: Name "HTTPError" is not defined  [name-defined]
app/data/feeds.py:251: error: Name "RequestException" is not defined  [name-defined]
app/data/feeds.py:375: error: Name "HTTPError" is not defined  [name-defined]
app/data/feeds.py:375: error: Name "RequestException" is not defined  [name-defined]
app/data/feeds.py:398: error: Name "HTTPError" is not defined  [name-defined]
app/data/feeds.py:398: error: Name "RequestException" is not defined  [name-defined]
app/data/feeds.py:539: error: Name "HTTPError" is not defined  [name-defined]
app/data/feeds.py:539: error: Name "RequestException" is not defined  [name-defined]
app/data/real_market_data.py:28: error: Library stubs not installed for "requests.exceptions"  [import-untyped]
app/data/real_market_data.py:28: note: Hint: "python3 -m pip install types-requests"
app/data/real_market_data.py:28: note: (or run "mypy --install-types" to install all missing stub packages)
app/data/real_market_data.py:28: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
app/data/real_market_data.py:520: error: Incompatible return value type (got "dict[str, float]", expected "dict[str, int]")  [return-value]
app/sre/automation/toil_tracker.py:1109: error: Module has no attribute "JSONEncodeError"; maybe "JSONDecodeError" or "JSONEncoder"?  [attr-defined]
app/microstructure/price_discovery.py:46: error: All conditional function variants must have identical signatures  [misc]
app/microstructure/price_discovery.py:46: note: Original:
app/microstructure/price_discovery.py:46: note:     def coint(*args: Any, **kwargs: Any) -> Any
app/microstructure/price_discovery.py:46: note: Redefinition:
app/microstructure/price_discovery.py:46: note:     def coint(y1: Any, y2: Any) -> Any
app/microstructure/price_discovery.py:102: error: All conditional function variants must have identical signatures  [misc]
app/microstructure/price_discovery.py:102: note: Original:
app/microstructure/price_discovery.py:102: note:     def adfuller(*args: Any, **kwargs: Any) -> Any
app/microstructure/price_discovery.py:102: note: Redefinition:
app/microstructure/price_discovery.py:102: note:     def adfuller(x: Any, maxlag: Any = ..., regression: Any = ...) -> Any
app/microstructure/price_discovery.py:251: error: Name "Tuple" is not defined  [name-defined]
app/microstructure/price_discovery.py:251: note: Did you forget to import it from "typing"? (Suggestion: "from typing import Tuple")
app/microstructure/price_discovery.py:516: error: Unsupported operand types for / ("int" and "SupportsDunderLT[Any]")  [operator]
app/microstructure/price_discovery.py:516: error: Unsupported operand types for / ("int" and "SupportsDunderGT[Any]")  [operator]
app/microstructure/price_discovery.py:516: note: Right operand is of type "Union[SupportsDunderLT[Any], SupportsDunderGT[Any]]"
app/microstructure/price_discovery.py:797: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/price_discovery.py:934: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/price_discovery.py:983: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/price_discovery.py:984: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/models.py:299: error: Name "Tuple" is not defined  [name-defined]
app/microstructure/models.py:299: note: Did you forget to import it from "typing"? (Suggestion: "from typing import Tuple")
app/microstructure/models.py:354: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/models.py:381: error: Incompatible types in assignment (expression has type "float", variable has type "int")  [assignment]
app/microstructure/models.py:383: error: Incompatible types in assignment (expression has type "float", variable has type "int")  [assignment]
app/microstructure/models.py:839: error: Name "weights" already defined on line 833  [no-redef]
app/microstructure/models.py:870: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/models.py:933: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/models.py:934: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/models.py:935: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/models.py:936: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/models.py:937: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/models.py:938: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/order_flow.py:71: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/order_flow.py:73: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/order_flow.py:201: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/order_flow.py:228: error: Incompatible return value type (got "Union[Decimal, float]", expected "Decimal")  [return-value]
app/microstructure/order_flow.py:550: error: Incompatible types in assignment (expression has type "floating[Any]", variable has type "float")  [assignment]
app/microstructure/order_flow.py:551: error: Incompatible types in assignment (expression has type "floating[Any]", variable has type "float")  [assignment]
app/microstructure/order_flow.py:568: error: Incompatible types in assignment (expression has type "datetime", variable has type "int")  [assignment]
app/microstructure/order_flow.py:571: error: Argument "forecast_time" to "OrderFlowForecast" has incompatible type "int"; expected "datetime"  [arg-type]
app/microstructure/order_flow.py:604: error: Dict entry 2 has incompatible type "str": "str"; expected "str": "float"  [dict-item]
app/microstructure/order_flow.py:620: error: Dict entry 2 has incompatible type "str": "str"; expected "str": "float"  [dict-item]
app/microstructure/order_flow.py:649: error: Dict entry 2 has incompatible type "str": "str"; expected "str": "float"  [dict-item]
app/microstructure/order_flow.py:712: error: Argument 1 to "_generate_recommendations" of "OrderFlowAnalyzer" has incompatible type "Decimal"; expected "float"  [arg-type]
app/microstructure/order_flow.py:845: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/order_flow.py:846: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/liquidity.py:68: error: Name "Dict" is not defined  [name-defined]
app/microstructure/liquidity.py:68: note: Did you forget to import it from "typing"? (Suggestion: "from typing import Dict")
app/microstructure/liquidity.py:205: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/liquidity.py:256: error: Argument "total_bid_depth" to "DepthProfile" has incompatible type "Union[Decimal, Literal[0]]"; expected "Decimal"  [arg-type]
app/microstructure/liquidity.py:257: error: Argument "total_ask_depth" to "DepthProfile" has incompatible type "Union[Decimal, Literal[0]]"; expected "Decimal"  [arg-type]
app/microstructure/liquidity.py:539: error: Unsupported operand types for / ("Decimal" and "float")  [operator]
app/microstructure/liquidity.py:583: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/liquidity.py:647: error: Argument "depth" to "calculate_liquidity_score" of "LiquidityAnalyzer" has incompatible type "Union[Decimal, int]"; expected "Decimal"  [arg-type]
app/microstructure/liquidity.py:658: error: Argument "quoted_depth" to "LiquidityMetrics" has incompatible type "Union[Decimal, int]"; expected "Decimal"  [arg-type]
app/microstructure/liquidity.py:704: error: Name "Dict" is not defined  [name-defined]
app/microstructure/liquidity.py:704: note: Did you forget to import it from "typing"? (Suggestion: "from typing import Dict")
app/microstructure/liquidity.py:704: error: Name "List" is not defined  [name-defined]
app/microstructure/liquidity.py:704: note: Did you forget to import it from "typing"? (Suggestion: "from typing import List")
app/microstructure/liquidity.py:704: error: Name "Tuple" is not defined  [name-defined]
app/microstructure/liquidity.py:704: note: Did you forget to import it from "typing"? (Suggestion: "from typing import Tuple")
app/microstructure/liquidity.py:768: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/liquidity.py:890: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/liquidity.py:931: error: X | Y syntax for unions requires Python 3.10  [syntax]
app/microstructure/liquidity.py:932: error: X | Y syntax for unions requires Python 3.10  [syntax]
**Status:** ❌ FAILED

## 2. Linting (ruff)
**Status:** ⚠️ ISSUES FOUND
```json
[
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 35,
      "row": 12
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/domain/entities/__init__.py",
    "fix": null,
    "location": {
      "column": 27,
      "row": 12
    },
    "message": "`.backtest.Backtest` imported but unused; consider using `importlib.util.find_spec` to test for availability",
    "noqa_row": 12,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 51,
      "row": 12
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/domain/entities/__init__.py",
    "fix": null,
    "location": {
      "column": 37,
      "row": 12
    },
    "message": "`.backtest.BacktestStatus` imported but unused; consider using `importlib.util.find_spec` to test for availability",
    "noqa_row": 12,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 65,
      "row": 12
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/domain/entities/__init__.py",
    "fix": null,
    "location": {
      "column": 53,
      "row": 12
    },
    "message": "`.backtest.BacktestType` imported but unused; consider using `importlib.util.find_spec` to test for availability",
    "noqa_row": 12,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 35,
      "row": 19
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/domain/entities/__init__.py",
    "fix": null,
    "location": {
      "column": 27,
      "row": 19
    },
    "message": "`.position.Position` imported but unused; consider using `importlib.util.find_spec` to test for availability",
    "noqa_row": 19,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 29,
      "row": 26
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/domain/entities/__init__.py",
    "fix": null,
    "location": {
      "column": 24,
      "row": 26
    },
    "message": "`.trade.Trade` imported but unused; consider using `importlib.util.find_spec` to test for availability",
    "noqa_row": 26,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 53,
      "row": 33
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/domain/entities/__init__.py",
    "fix": null,
    "location": {
      "column": 37,
      "row": 33
    },
    "message": "`.pre_trade_analysis.PreTradeAnalysis` imported but unused; consider using `importlib.util.find_spec` to test for availability",
    "noqa_row": 33,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 55,
      "row": 40
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/domain/entities/__init__.py",
    "fix": null,
    "location": {
      "column": 38,
      "row": 40
    },
    "message": "`.post_trade_analysis.PostTradeAnalysis` imported but unused; consider using `importlib.util.find_spec` to test for availability",
    "noqa_row": 40,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 62,
      "row": 47
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/domain/entities/__init__.py",
    "fix": null,
    "location": {
      "column": 41,
      "row": 47
    },
    "message": "`.portfolio_optimization.PortfolioOptimization` imported but unused; consider using `importlib.util.find_spec` to test for availability",
    "noqa_row": 47,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  }
]```

## 3. Security (bandit)
**Status:** ✅ PASSED

## 4. Complexity (radon)

## 5. Maintainability Index
app/domain/entities/__init__.py - A (100.00)

## 6. Syntax Check
**Status:** ✅ PASSED

## 7. Import Validation
**Status:** ✅ PASSED

---
## Summary
**Validation completed at:** 2026-02-07T05:13:21Z

