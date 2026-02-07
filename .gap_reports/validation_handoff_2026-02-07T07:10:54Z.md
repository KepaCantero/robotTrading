# Validation Report: app/sre/oncall/handoff.py
**Generated:** 2026-02-07T07:10:54Z

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
app/sre/oncall/escalation.py:894: error: Need type annotation for "by_severity" (hint: "by_severity: dict[<type>, <type>] = ...")  [var-annotated]
app/sre/oncall/escalation.py:899: error: Need type annotation for "by_status" (hint: "by_status: dict[<type>, <type>] = ...")  [var-annotated]
app/sre/oncall/dashboard.py:663: error: Unsupported operand types for > ("str" and "int")  [operator]
app/sre/oncall/dashboard.py:663: note: Left operand is of type "Union[float, int, str]"
app/sre/oncall/handoff.py:594: error: Name "session_id" is not defined  [name-defined]
app/sre/oncall/handoff.py:611: error: Name "session_id" is not defined  [name-defined]
app/sre/oncall/__init__.py:48: error: Module "app.sre.oncall.handoff" has no attribute "HandoffChecklist"  [attr-defined]
app/sre/oncall/__init__.py:49: error: Module "app.sre.oncall.rotation" has no attribute "RotationSchedule"  [attr-defined]
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
    "code": "F821",
    "end_location": {
      "column": 36,
      "row": 594
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/sre/oncall/handoff.py",
    "fix": null,
    "location": {
      "column": 26,
      "row": 594
    },
    "message": "Undefined name `session_id`",
    "noqa_row": 594,
    "url": "https://docs.astral.sh/ruff/rules/undefined-name"
  },
  {
    "cell": null,
    "code": "F821",
    "end_location": {
      "column": 46,
      "row": 611
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/sre/oncall/handoff.py",
    "fix": null,
    "location": {
      "column": 36,
      "row": 611
    },
    "message": "Undefined name `session_id`",
    "noqa_row": 611,
    "url": "https://docs.astral.sh/ruff/rules/undefined-name"
  }
]```

## 3. Security (bandit)
**Status:** ⚠️ ISSUES FOUND
```json
{
  "errors": [],
  "generated_at": "2026-02-07T07:10:55Z",
  "metrics": {
    "./app/sre/oncall/handoff.py": {
      "CONFIDENCE.HIGH": 1,
      "CONFIDENCE.LOW": 0,
      "CONFIDENCE.MEDIUM": 0,
      "CONFIDENCE.UNDEFINED": 0,
      "SEVERITY.HIGH": 0,
      "SEVERITY.LOW": 0,
      "SEVERITY.MEDIUM": 1,
      "SEVERITY.UNDEFINED": 0,
      "loc": 731,
      "nosec": 0,
      "skipped_tests": 0
    },
    "_totals": {
      "CONFIDENCE.HIGH": 1,
      "CONFIDENCE.LOW": 0,
      "CONFIDENCE.MEDIUM": 0,
      "CONFIDENCE.UNDEFINED": 0,
      "SEVERITY.HIGH": 0,
      "SEVERITY.LOW": 0,
      "SEVERITY.MEDIUM": 1,
      "SEVERITY.UNDEFINED": 0,
      "loc": 731,
      "nosec": 0,
      "skipped_tests": 0
    }
  },
  "results": [
    {
      "code": "606                             notes=comp_row[4],\n607                             artifacts=eval(comp_row[5]) if comp_row[5] else [],\n608                         )\n",
      "col_offset": 38,
      "end_col_offset": 55,
      "filename": "./app/sre/oncall/handoff.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 78,
        "link": "https://cwe.mitre.org/data/definitions/78.html"
      },
      "issue_severity": "MEDIUM",
      "issue_text": "Use of possibly insecure function - consider using safer ast.literal_eval.",
      "line_number": 607,
      "line_range": [
        607
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/blacklists/blacklist_calls.html#b307-eval",
      "test_id": "B307",
      "test_name": "blacklist"
    }
  ]
}```

## 4. Complexity (radon)
app/sre/oncall/handoff.py
    M 270:4 HandoffSession.calculate_quality_score - C (11)
    M 698:4 HandoffManager.complete_handoff - B (10)
    M 553:4 HandoffManager._load_sessions - B (9)
    M 805:4 HandoffManager._save_session - B (8)
    M 876:4 HandoffManager.get_handoff_metrics - B (8)
    M 176:4 HandoffSession.__post_init__ - B (7)
    C 356:0 HandoffManager - B (6)
    C 153:0 HandoffSession - A (5)
    M 309:4 HandoffSession.to_dict - A (5)
    M 250:4 HandoffSession.get_completion_percentage - A (4)
    M 258:4 HandoffSession.get_required_remaining - A (4)
    M 767:4 HandoffManager.complete_checklist_item - A (4)
    M 218:4 HandoffSession.complete_item - A (3)
    M 434:4 HandoffManager.__init__ - A (3)
    M 670:4 HandoffManager.start_handoff - A (3)
    C 58:0 ChecklistItem - A (2)
    C 100:0 HandoffContext - A (2)
    M 192:4 HandoffSession.start - A (2)
    M 199:4 HandoffSession.complete - A (2)
    M 458:4 HandoffManager.initialize - A (2)
    M 474:4 HandoffManager._init_database - A (2)
    M 618:4 HandoffManager.create_handoff - A (2)
    C 35:0 HandoffStatus - A (1)
    C 45:0 ChecklistItemType - A (1)
    M 74:4 ChecklistItem.to_dict - A (1)
    C 88:0 ChecklistCompletion - A (1)
    M 132:4 HandoffContext.to_dict - A (1)
    M 207:4 HandoffSession.fail - A (1)
    M 213:4 HandoffSession.cancel - A (1)
    C 330:0 HandoffConfig - A (1)

30 blocks (classes, functions, methods) analyzed.
Average complexity: A (3.7333333333333334)

## 5. Maintainability Index
app/sre/oncall/handoff.py - A (35.89)

## 6. Syntax Check
**Status:** ✅ PASSED

## 7. Import Validation
**Status:** ✅ PASSED

---
## Summary
**Validation completed at:** 2026-02-07T07:10:54Z

