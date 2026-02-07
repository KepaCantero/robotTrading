# Validation Report: app/tests/ensemble/test_ensemble.py
**Generated:** 2026-02-07T07:10:59Z

## 1. Type Checking (mypy)
/opt/homebrew/lib/python3.13/site-packages/_pytest/terminal.py:1729: error: Pattern matching is only supported in Python 3.10 and greater  [syntax]
**Status:** ❌ FAILED

## 2. Linting (ruff)
**Status:** ⚠️ ISSUES FOUND
```json
[
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 30,
      "row": 12
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/ensemble/test_ensemble.py",
    "fix": {
      "applicability": "safe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 1,
            "row": 13
          },
          "location": {
            "column": 1,
            "row": 12
          }
        }
      ],
      "message": "Remove unused import: `datetime.datetime`"
    },
    "location": {
      "column": 22,
      "row": 12
    },
    "message": "`datetime.datetime` imported but unused",
    "noqa_row": 12,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F841",
    "end_location": {
      "column": 18,
      "row": 450
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/ensemble/test_ensemble.py",
    "fix": {
      "applicability": "unsafe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 21,
            "row": 450
          },
          "location": {
            "column": 9,
            "row": 450
          }
        }
      ],
      "message": "Remove assignment to unused variable `solution2`"
    },
    "location": {
      "column": 9,
      "row": 450
    },
    "message": "Local variable `solution2` is assigned to but never used",
    "noqa_row": 450,
    "url": "https://docs.astral.sh/ruff/rules/unused-variable"
  }
]```

## 3. Security (bandit)
**Status:** ⚠️ ISSUES FOUND
```json
{
  "errors": [],
  "generated_at": "2026-02-07T07:10:59Z",
  "metrics": {
    "./app/tests/ensemble/test_ensemble.py": {
      "CONFIDENCE.HIGH": 87,
      "CONFIDENCE.LOW": 0,
      "CONFIDENCE.MEDIUM": 0,
      "CONFIDENCE.UNDEFINED": 0,
      "SEVERITY.HIGH": 0,
      "SEVERITY.LOW": 87,
      "SEVERITY.MEDIUM": 0,
      "SEVERITY.UNDEFINED": 0,
      "loc": 819,
      "nosec": 0,
      "skipped_tests": 0
    },
    "_totals": {
      "CONFIDENCE.HIGH": 87,
      "CONFIDENCE.LOW": 0,
      "CONFIDENCE.MEDIUM": 0,
      "CONFIDENCE.UNDEFINED": 0,
      "SEVERITY.HIGH": 0,
      "SEVERITY.LOW": 87,
      "SEVERITY.MEDIUM": 0,
      "SEVERITY.UNDEFINED": 0,
      "loc": 819,
      "nosec": 0,
      "skipped_tests": 0
    }
  },
  "results": [
    {
      "code": "124         )\n125         assert len(config.objectives) == 2\n126         assert config.tolerance == 0.01\n",
      "col_offset": 8,
      "end_col_offset": 42,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 125,
      "line_range": [
        125
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "125         assert len(config.objectives) == 2\n126         assert config.tolerance == 0.01\n127 \n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 126,
      "line_range": [
        126
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "156         # Manually check mismatch\n157         assert len(config.objectives) == 2\n158         assert len(config.weights) == 2\n",
      "col_offset": 8,
      "end_col_offset": 42,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 157,
      "line_range": [
        157
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "157         assert len(config.objectives) == 2\n158         assert len(config.weights) == 2\n159         # If mismatched, the config creation would fail or be inconsistent\n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 158,
      "line_range": [
        158
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "174         )\n175         assert solution.rank == 0\n176         assert solution.dominates\n",
      "col_offset": 8,
      "end_col_offset": 33,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 175,
      "line_range": [
        175
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "175         assert solution.rank == 0\n176         assert solution.dominates\n177 \n",
      "col_offset": 8,
      "end_col_offset": 33,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 176,
      "line_range": [
        176
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "206         )\n207         assert config.method == EnsembleMethod.MAJORITY_VOTING\n208         assert config.min_agreement == 0.5\n",
      "col_offset": 8,
      "end_col_offset": 62,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 207,
      "line_range": [
        207
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "207         assert config.method == EnsembleMethod.MAJORITY_VOTING\n208         assert config.min_agreement == 0.5\n209 \n",
      "col_offset": 8,
      "end_col_offset": 42,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 208,
      "line_range": [
        208
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "216         )\n217         assert config.strategy_weights[\"momentum\"] == 0.6\n218 \n",
      "col_offset": 8,
      "end_col_offset": 57,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 217,
      "line_range": [
        217
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "249         )\n250         assert signal.symbol == \"AAPL\"\n251         assert signal.is_actionable\n",
      "col_offset": 8,
      "end_col_offset": 38,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 250,
      "line_range": [
        250
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "250         assert signal.symbol == \"AAPL\"\n251         assert signal.is_actionable\n252 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 251,
      "line_range": [
        251
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "266         )\n267         assert signal.has_consensus\n268 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 267,
      "line_range": [
        267
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "278         )\n279         assert not signal.is_actionable\n280 \n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 279,
      "line_range": [
        279
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "292         )\n293         assert allocation.strategy == \"momentum\"\n294         assert allocation.drift == Decimal(\"0.02\")\n",
      "col_offset": 8,
      "end_col_offset": 48,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 293,
      "line_range": [
        293
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "293         assert allocation.strategy == \"momentum\"\n294         assert allocation.drift == Decimal(\"0.02\")\n295 \n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 294,
      "line_range": [
        294
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "303         )\n304         assert allocation.needs_rebalance\n305 \n",
      "col_offset": 8,
      "end_col_offset": 41,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 304,
      "line_range": [
        304
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "319         )\n320         assert portfolio.total_return == Decimal(\"0.15\")\n321         assert portfolio.is_efficient\n",
      "col_offset": 8,
      "end_col_offset": 56,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 320,
      "line_range": [
        320
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "320         assert portfolio.total_return == Decimal(\"0.15\")\n321         assert portfolio.is_efficient\n322 \n",
      "col_offset": 8,
      "end_col_offset": 37,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 321,
      "line_range": [
        321
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "331         )\n332         assert portfolio.is_well_diversified\n333 \n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 332,
      "line_range": [
        332
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "352         )\n353         assert not metrics.has_redundancy\n354         assert metrics.diversification_quality in [\"excellent\", \"good\", \"moderate\", \"poor\"]\n",
      "col_offset": 8,
      "end_col_offset": 41,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 353,
      "line_range": [
        353
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "353         assert not metrics.has_redundancy\n354         assert metrics.diversification_quality in [\"excellent\", \"good\", \"moderate\", \"poor\"]\n355 \n",
      "col_offset": 8,
      "end_col_offset": 91,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 354,
      "line_range": [
        354
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "368         )\n369         assert metrics.has_redundancy\n370 \n",
      "col_offset": 8,
      "end_col_offset": 37,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 369,
      "line_range": [
        369
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "392         )\n393         assert len(optimizer.strategies) == 3\n394 \n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 393,
      "line_range": [
        393
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "423 \n424         assert isinstance(pareto_front, list)\n425         # Should return at least some solutions\n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 424,
      "line_range": [
        424
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "425         # Should return at least some solutions\n426         assert len(pareto_front) >= 0\n427 \n",
      "col_offset": 8,
      "end_col_offset": 37,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 426,
      "line_range": [
        426
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "456         # But we need the optimizer to check this\n457         assert solution1.dominates  # rank = 0\n458 \n",
      "col_offset": 8,
      "end_col_offset": 34,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 457,
      "line_range": [
        457
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "477             for solution in pareto_front:\n478                 assert solution.crowding_distance >= 0\n479 \n",
      "col_offset": 16,
      "end_col_offset": 54,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 478,
      "line_range": [
        478
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "495         # Same seed should give similar results (may vary slightly due to timing)\n496         assert isinstance(front1, list)\n497         assert isinstance(front2, list)\n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 496,
      "line_range": [
        496
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "496         assert isinstance(front1, list)\n497         assert isinstance(front2, list)\n498 \n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 497,
      "line_range": [
        497
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "510 \n511         assert isinstance(pareto_front, list)\n512 \n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 511,
      "line_range": [
        511
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "526 \n527         assert isinstance(portfolio_return, float)\n528 \n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 527,
      "line_range": [
        527
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "542 \n543         assert isinstance(portfolio_risk, float)\n544         assert portfolio_risk >= 0\n",
      "col_offset": 8,
      "end_col_offset": 48,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 543,
      "line_range": [
        543
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "543         assert isinstance(portfolio_risk, float)\n544         assert portfolio_risk >= 0\n545 \n",
      "col_offset": 8,
      "end_col_offset": 34,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 544,
      "line_range": [
        544
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "561         voting = EnsembleVoting(config=config)\n562         assert voting.method == EnsembleMethod.MAJORITY_VOTING\n563 \n",
      "col_offset": 8,
      "end_col_offset": 62,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 562,
      "line_range": [
        562
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "581 \n582         assert combined is not None\n583         assert combined.signal_type == \"buy\"  # 2 buy vs 1 hold\n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 582,
      "line_range": [
        582
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "582         assert combined is not None\n583         assert combined.signal_type == \"buy\"  # 2 buy vs 1 hold\n584         assert combined.agreement == 2.0 / 3.0\n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 583,
      "line_range": [
        583
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "583         assert combined.signal_type == \"buy\"  # 2 buy vs 1 hold\n584         assert combined.agreement == 2.0 / 3.0\n585 \n",
      "col_offset": 8,
      "end_col_offset": 46,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 584,
      "line_range": [
        584
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "595 \n596         assert combined is not None\n597 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 596,
      "line_range": [
        596
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "606 \n607         assert combined is not None\n608 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 607,
      "line_range": [
        607
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "617 \n618         assert combined is not None\n619 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 618,
      "line_range": [
        618
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "628 \n629         assert combined is not None\n630 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 629,
      "line_range": [
        629
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "680         # Should return None due to low agreement\n681         assert combined is None\n682 \n",
      "col_offset": 8,
      "end_col_offset": 31,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 681,
      "line_range": [
        681
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "692         # 2 buy, 1 hold = 2/3 agreement\n693         assert abs(agreement - 2.0 / 3.0) < 0.01\n694 \n",
      "col_offset": 8,
      "end_col_offset": 48,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 693,
      "line_range": [
        693
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "703 \n704         assert abs(disagreement - (1 - 2.0 / 3.0)) < 0.01\n705 \n",
      "col_offset": 8,
      "end_col_offset": 57,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 704,
      "line_range": [
        704
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "714 \n715         assert 0 <= entropy <= 1\n716 \n",
      "col_offset": 8,
      "end_col_offset": 32,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 715,
      "line_range": [
        715
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "725 \n726         assert \"total_signals\" in summary\n727         assert \"agreement\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 41,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 726,
      "line_range": [
        726
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "726         assert \"total_signals\" in summary\n727         assert \"agreement\" in summary\n728         assert \"disagreement\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 37,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 727,
      "line_range": [
        727
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "727         assert \"agreement\" in summary\n728         assert \"disagreement\" in summary\n729         assert summary[\"total_signals\"] == 3\n",
      "col_offset": 8,
      "end_col_offset": 40,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 728,
      "line_range": [
        728
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "728         assert \"disagreement\" in summary\n729         assert summary[\"total_signals\"] == 3\n730 \n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 729,
      "line_range": [
        729
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "745         )\n746         assert combiner.method == AllocationMethod.EQUAL_WEIGHT\n747 \n",
      "col_offset": 8,
      "end_col_offset": 63,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 746,
      "line_range": [
        746
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "755 \n756         assert len(allocation) == 3\n757         # Equal weights should be ~0.33\n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 756,
      "line_range": [
        756
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "758         for alloc in allocation:\n759             assert abs(float(alloc.weight) - 1.0 / 3.0) < 0.01\n760 \n",
      "col_offset": 12,
      "end_col_offset": 62,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 759,
      "line_range": [
        759
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "768 \n769         assert len(allocation) == 3\n770         # Weights should sum to 1\n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 769,
      "line_range": [
        769
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "771         total_weight = sum(float(a.weight) for a in allocation)\n772         assert abs(total_weight - 1.0) < 0.01\n773 \n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 772,
      "line_range": [
        772
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "781 \n782         assert len(allocation) == 3\n783         total_weight = sum(float(a.weight) for a in allocation)\n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 782,
      "line_range": [
        782
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "783         total_weight = sum(float(a.weight) for a in allocation)\n784         assert abs(total_weight - 1.0) < 0.01\n785 \n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 784,
      "line_range": [
        784
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "797 \n798         assert len(allocation) == 3\n799         total_weight = sum(float(a.weight) for a in allocation)\n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 798,
      "line_range": [
        798
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "799         total_weight = sum(float(a.weight) for a in allocation)\n800         assert abs(total_weight - 1.0) < 0.01\n801 \n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 800,
      "line_range": [
        800
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "809 \n810         assert len(allocation) == 3\n811         total_weight = sum(float(a.weight) for a in allocation)\n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 810,
      "line_range": [
        810
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "811         total_weight = sum(float(a.weight) for a in allocation)\n812         assert abs(total_weight - 1.0) < 0.01\n813 \n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 812,
      "line_range": [
        812
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "822 \n823         assert isinstance(metrics, CombinedPortfolio)\n824         assert metrics.total_return is not None\n",
      "col_offset": 8,
      "end_col_offset": 53,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 823,
      "line_range": [
        823
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "823         assert isinstance(metrics, CombinedPortfolio)\n824         assert metrics.total_return is not None\n825         assert metrics.volatility >= 0\n",
      "col_offset": 8,
      "end_col_offset": 47,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 824,
      "line_range": [
        824
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "824         assert metrics.total_return is not None\n825         assert metrics.volatility >= 0\n826 \n",
      "col_offset": 8,
      "end_col_offset": 38,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 825,
      "line_range": [
        825
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "837 \n838         assert combiner.needs_rebalancing(allocation)\n839 \n",
      "col_offset": 8,
      "end_col_offset": 53,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 838,
      "line_range": [
        838
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "853 \n854         assert isinstance(trades, dict)\n855         assert len(trades) == 3\n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 854,
      "line_range": [
        854
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "854         assert isinstance(trades, dict)\n855         assert len(trades) == 3\n856 \n",
      "col_offset": 8,
      "end_col_offset": 31,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 855,
      "line_range": [
        855
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "865 \n866         assert \"num_strategies\" in summary\n867         assert summary[\"num_strategies\"] == 3\n",
      "col_offset": 8,
      "end_col_offset": 42,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 866,
      "line_range": [
        866
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "866         assert \"num_strategies\" in summary\n867         assert summary[\"num_strategies\"] == 3\n868         assert \"max_weight\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 867,
      "line_range": [
        867
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "867         assert summary[\"num_strategies\"] == 3\n868         assert \"max_weight\" in summary\n869 \n",
      "col_offset": 8,
      "end_col_offset": 38,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 868,
      "line_range": [
        868
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "884         )\n885         assert analyzer.method == \"pearson\"\n886 \n",
      "col_offset": 8,
      "end_col_offset": 43,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 885,
      "line_range": [
        885
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "902 \n903         assert isinstance(metrics, CorrelationMetrics)\n904         assert metrics.mean_correlation is not None\n",
      "col_offset": 8,
      "end_col_offset": 54,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 903,
      "line_range": [
        903
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "903         assert isinstance(metrics, CorrelationMetrics)\n904         assert metrics.mean_correlation is not None\n905         assert -1 <= metrics.mean_correlation <= 1\n",
      "col_offset": 8,
      "end_col_offset": 51,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 904,
      "line_range": [
        904
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "904         assert metrics.mean_correlation is not None\n905         assert -1 <= metrics.mean_correlation <= 1\n906 \n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 905,
      "line_range": [
        905
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "914 \n915         assert isinstance(metrics, CorrelationMetrics)\n916 \n",
      "col_offset": 8,
      "end_col_offset": 54,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 915,
      "line_range": [
        915
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "924 \n925         assert isinstance(metrics, CorrelationMetrics)\n926 \n",
      "col_offset": 8,
      "end_col_offset": 54,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 925,
      "line_range": [
        925
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "941         # May detect redundancy\n942         assert isinstance(metrics.redundant_pairs, list)\n943 \n",
      "col_offset": 8,
      "end_col_offset": 56,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 942,
      "line_range": [
        942
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "950 \n951         assert metrics.effective_number_bets >= 1.0\n952         assert metrics.effective_number_bets <= len(sample_strategies)\n",
      "col_offset": 8,
      "end_col_offset": 51,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 951,
      "line_range": [
        951
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "951         assert metrics.effective_number_bets >= 1.0\n952         assert metrics.effective_number_bets <= len(sample_strategies)\n953 \n",
      "col_offset": 8,
      "end_col_offset": 70,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 952,
      "line_range": [
        952
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "960 \n961         assert len(metrics.eigenvalues) == len(sample_strategies)\n962 \n",
      "col_offset": 8,
      "end_col_offset": 65,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 961,
      "line_range": [
        961
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "969 \n970         assert metrics.condition_number >= 1.0\n971 \n",
      "col_offset": 8,
      "end_col_offset": 46,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 970,
      "line_range": [
        970
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "980         # Returns None if no redundant pairs, or tuple otherwise\n981         assert most_corr is None or isinstance(most_corr, tuple)\n982 \n",
      "col_offset": 8,
      "end_col_offset": 64,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 981,
      "line_range": [
        981
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "990 \n991         assert least_corr is None or isinstance(least_corr, tuple)\n992 \n",
      "col_offset": 8,
      "end_col_offset": 66,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 991,
      "line_range": [
        991
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1000 \n1001         assert \"num_strategies\" in summary\n1002         assert \"mean_correlation\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 42,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1001,
      "line_range": [
        1001
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1001         assert \"num_strategies\" in summary\n1002         assert \"mean_correlation\" in summary\n1003         assert summary[\"num_strategies\"] == 3\n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1002,
      "line_range": [
        1002
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1002         assert \"mean_correlation\" in summary\n1003         assert summary[\"num_strategies\"] == 3\n1004 \n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1003,
      "line_range": [
        1003
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1011 \n1012         assert \"stability_score\" in stability\n1013         assert 0 <= stability[\"stability_score\"] <= 1\n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1012,
      "line_range": [
        1012
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1012         assert \"stability_score\" in stability\n1013         assert 0 <= stability[\"stability_score\"] <= 1\n1014 \n",
      "col_offset": 8,
      "end_col_offset": 53,
      "filename": "./app/tests/ensemble/test_ensemble.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1013,
      "line_range": [
        1013
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    }
  ]
}```

## 4. Complexity (radon)
app/tests/ensemble/test_ensemble.py
    M 717:4 TestEnsembleVoting.test_voting_summary - A (5)
    C 282:0 TestStrategyAllocation - A (4)
    C 307:0 TestCombinedPortfolio - A (4)
    C 335:0 TestCorrelationMetrics - A (4)
    M 459:4 TestParetoFrontOptimizer.test_crowding_distance_calculation - A (4)
    M 573:4 TestEnsembleVoting.test_majority_voting - A (4)
    C 737:0 TestStrategyCombiner - A (4)
    M 748:4 TestStrategyCombiner.test_equal_weight_allocation - A (4)
    M 761:4 TestStrategyCombiner.test_risk_parity_allocation - A (4)
    M 774:4 TestStrategyCombiner.test_mean_variance_allocation - A (4)
    M 786:4 TestStrategyCombiner.test_regime_dependent_allocation - A (4)
    M 802:4 TestStrategyCombiner.test_hierarchical_risk_parity - A (4)
    M 814:4 TestStrategyCombiner.test_portfolio_metrics_calculation - A (4)
    M 840:4 TestStrategyCombiner.test_rebalance_calculation - A (4)
    M 857:4 TestStrategyCombiner.test_allocation_summary - A (4)
    M 895:4 TestCorrelationAnalyzer.test_correlation_analysis - A (4)
    M 993:4 TestCorrelationAnalyzer.test_correlation_summary - A (4)
    C 113:0 TestObjectiveConfig - A (3)
    M 116:4 TestObjectiveConfig.test_objective_config_creation - A (3)
    M 147:4 TestObjectiveConfig.test_objective_config_mismatch_objectives_weights - A (3)
    C 162:0 TestParetoSolution - A (3)
    M 165:4 TestParetoSolution.test_pareto_solution_creation - A (3)
    C 198:0 TestEnsembleConfig - A (3)
    M 201:4 TestEnsembleConfig.test_ensemble_config_creation - A (3)
    C 237:0 TestEnsembleSignal - A (3)
    M 240:4 TestEnsembleSignal.test_ensemble_signal_creation - A (3)
    M 285:4 TestStrategyAllocation.test_strategy_allocation_creation - A (3)
    M 310:4 TestCombinedPortfolio.test_combined_portfolio_creation - A (3)
    M 338:4 TestCorrelationMetrics.test_correlation_metrics_creation - A (3)
    C 377:0 TestParetoFrontOptimizer - A (3)
    M 407:4 TestParetoFrontOptimizer.test_optimizer_basic_optimization - A (3)
    M 428:4 TestParetoFrontOptimizer.test_optimizer_missing_strategy_data - A (3)
    M 480:4 TestParetoFrontOptimizer.test_optimizer_with_seed - A (3)
    M 529:4 TestParetoFrontOptimizer.test_portfolio_risk_calculation - A (3)
    C 552:0 TestEnsembleVoting - A (3)
    C 876:0 TestCorrelationAnalyzer - A (3)
    M 944:4 TestCorrelationAnalyzer.test_effective_number_bets - A (3)
    M 1005:4 TestCorrelationAnalyzer.test_stability_test - A (3)
    M 210:4 TestEnsembleConfig.test_ensemble_config_custom_weights - A (2)
    M 253:4 TestEnsembleSignal.test_ensemble_signal_consensus - A (2)
    M 269:4 TestEnsembleSignal.test_ensemble_signal_not_actionable - A (2)
    M 296:4 TestStrategyAllocation.test_strategy_allocation_needs_rebalance - A (2)
    M 323:4 TestCombinedPortfolio.test_combined_portfolio_well_diversified - A (2)
    M 356:4 TestCorrelationMetrics.test_correlation_metrics_with_redundancy - A (2)
    M 380:4 TestParetoFrontOptimizer.test_optimizer_initialization - A (2)
    M 444:4 TestParetoFrontOptimizer.test_pareto_solution_dominance - A (2)
    M 499:4 TestParetoFrontOptimizer.test_single_objective_optimization - A (2)
    M 513:4 TestParetoFrontOptimizer.test_portfolio_return_calculation - A (2)
    M 555:4 TestEnsembleVoting.test_voting_initialization - A (2)
    M 586:4 TestEnsembleVoting.test_weighted_voting - A (2)
    M 598:4 TestEnsembleVoting.test_soft_voting - A (2)
    M 609:4 TestEnsembleVoting.test_confidence_weighted_voting - A (2)
    M 620:4 TestEnsembleVoting.test_rank_averaging - A (2)
    M 631:4 TestEnsembleVoting.test_voting_with_low_agreement - A (2)
    M 683:4 TestEnsembleVoting.test_agreement_calculation - A (2)
    M 695:4 TestEnsembleVoting.test_disagreement_calculation - A (2)
    M 706:4 TestEnsembleVoting.test_entropy_calculation - A (2)
    M 740:4 TestStrategyCombiner.test_combiner_initialization - A (2)
    M 827:4 TestStrategyCombiner.test_needs_rebalancing - A (2)
    M 879:4 TestCorrelationAnalyzer.test_analyzer_initialization - A (2)
    M 907:4 TestCorrelationAnalyzer.test_spearman_correlation - A (2)
    M 917:4 TestCorrelationAnalyzer.test_kendall_correlation - A (2)
    M 927:4 TestCorrelationAnalyzer.test_redundancy_detection - A (2)
    M 954:4 TestCorrelationAnalyzer.test_eigenvalues_calculation - A (2)
    M 963:4 TestCorrelationAnalyzer.test_condition_number - A (2)
    M 972:4 TestCorrelationAnalyzer.test_most_correlated_pair - A (2)
    M 983:4 TestCorrelationAnalyzer.test_least_correlated_pair - A (2)
    F 44:0 sample_strategies - A (1)
    F 50:0 sample_returns_data - A (1)
    F 63:0 sample_signals - A (1)
    M 128:4 TestObjectiveConfig.test_objective_config_weights_validation - A (1)
    M 136:4 TestObjectiveConfig.test_objective_config_negative_weights - A (1)
    M 178:4 TestParetoSolution.test_pareto_solution_weights_sum - A (1)
    M 189:4 TestParetoSolution.test_pareto_solution_empty_weights - A (1)
    M 219:4 TestEnsembleConfig.test_ensemble_config_invalid_weights_sum - A (1)
    M 228:4 TestEnsembleConfig.test_ensemble_config_min_strategies - A (1)
    M 395:4 TestParetoFrontOptimizer.test_optimizer_invalid_strategies - A (1)
    M 564:4 TestEnsembleVoting.test_voting_invalid_config - A (1)
    M 887:4 TestCorrelationAnalyzer.test_analyzer_invalid_method - A (1)

79 blocks (classes, functions, methods) analyzed.
Average complexity: A (2.5569620253164556)

## 5. Maintainability Index
app/tests/ensemble/test_ensemble.py - B (14.14)

## 6. Syntax Check
**Status:** ✅ PASSED

## 7. Import Validation
**Status:** ✅ PASSED

---
## Summary
**Validation completed at:** 2026-02-07T07:10:59Z

