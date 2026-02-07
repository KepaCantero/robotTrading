# Validation Report: app/tests/analysis/test_fundamental_law.py
**Generated:** 2026-02-07T07:10:56Z

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
      "column": 12,
      "row": 17
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/analysis/test_fundamental_law.py",
    "fix": {
      "applicability": "safe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 1,
            "row": 18
          },
          "location": {
            "column": 1,
            "row": 17
          }
        }
      ],
      "message": "Remove unused import: `math`"
    },
    "location": {
      "column": 8,
      "row": 17
    },
    "message": "`math` imported but unused",
    "noqa_row": 17,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 30,
      "row": 18
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/analysis/test_fundamental_law.py",
    "fix": {
      "applicability": "safe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 1,
            "row": 19
          },
          "location": {
            "column": 1,
            "row": 18
          }
        }
      ],
      "message": "Remove unused import"
    },
    "location": {
      "column": 22,
      "row": 18
    },
    "message": "`datetime.datetime` imported but unused",
    "noqa_row": 18,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 41,
      "row": 18
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/analysis/test_fundamental_law.py",
    "fix": {
      "applicability": "safe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 1,
            "row": 19
          },
          "location": {
            "column": 1,
            "row": 18
          }
        }
      ],
      "message": "Remove unused import"
    },
    "location": {
      "column": 32,
      "row": 18
    },
    "message": "`datetime.timedelta` imported but unused",
    "noqa_row": 18,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F841",
    "end_location": {
      "column": 10,
      "row": 1051
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/analysis/test_fundamental_law.py",
    "fix": {
      "applicability": "unsafe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 1,
            "row": 1052
          },
          "location": {
            "column": 1,
            "row": 1051
          }
        }
      ],
      "message": "Remove assignment to unused variable `n`"
    },
    "location": {
      "column": 9,
      "row": 1051
    },
    "message": "Local variable `n` is assigned to but never used",
    "noqa_row": 1051,
    "url": "https://docs.astral.sh/ruff/rules/unused-variable"
  }
]```

## 3. Security (bandit)
**Status:** ⚠️ ISSUES FOUND
```json
{
  "errors": [],
  "generated_at": "2026-02-07T07:10:57Z",
  "metrics": {
    "./app/tests/analysis/test_fundamental_law.py": {
      "CONFIDENCE.HIGH": 115,
      "CONFIDENCE.LOW": 0,
      "CONFIDENCE.MEDIUM": 0,
      "CONFIDENCE.UNDEFINED": 0,
      "SEVERITY.HIGH": 0,
      "SEVERITY.LOW": 115,
      "SEVERITY.MEDIUM": 0,
      "SEVERITY.UNDEFINED": 0,
      "loc": 845,
      "nosec": 0,
      "skipped_tests": 0
    },
    "_totals": {
      "CONFIDENCE.HIGH": 115,
      "CONFIDENCE.LOW": 0,
      "CONFIDENCE.MEDIUM": 0,
      "CONFIDENCE.UNDEFINED": 0,
      "SEVERITY.HIGH": 0,
      "SEVERITY.LOW": 115,
      "SEVERITY.MEDIUM": 0,
      "SEVERITY.UNDEFINED": 0,
      "loc": 845,
      "nosec": 0,
      "skipped_tests": 0
    }
  },
  "results": [
    {
      "code": "148         )\n149         assert components.information_ratio == Decimal(\"1.0\")\n150         assert components.information_coefficient == Decimal(\"0.05\")\n",
      "col_offset": 8,
      "end_col_offset": 61,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 149,
      "line_range": [
        149
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "149         assert components.information_ratio == Decimal(\"1.0\")\n150         assert components.information_coefficient == Decimal(\"0.05\")\n151 \n",
      "col_offset": 8,
      "end_col_offset": 68,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 150,
      "line_range": [
        150
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "160         )\n161         assert components.validate()\n162 \n",
      "col_offset": 8,
      "end_col_offset": 36,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 161,
      "line_range": [
        161
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "171         )\n172         assert components.validate(tolerance=Decimal(\"0.02\"))\n173 \n",
      "col_offset": 8,
      "end_col_offset": 61,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 172,
      "line_range": [
        172
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "207         theoretical = components.get_theoretical_ir()\n208         assert theoretical == Decimal(\"1.000\")\n209 \n",
      "col_offset": 8,
      "end_col_offset": 46,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "219         gap = components.get_efficiency_gap()\n220         assert gap == Decimal(\"0.200\")\n221 \n",
      "col_offset": 8,
      "end_col_offset": 38,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 220,
      "line_range": [
        220
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "234         )\n235         assert metrics.ic == Decimal(\"0.05\")\n236 \n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 235,
      "line_range": [
        235
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "245         )\n246         assert metrics.is_significant()\n247 \n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 246,
      "line_range": [
        246
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "256         )\n257         assert not metrics.is_significant()\n258 \n",
      "col_offset": 8,
      "end_col_offset": 43,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 257,
      "line_range": [
        257
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "267         )\n268         assert metrics.is_significant(alpha=0.001)\n269         assert not metrics.is_significant(alpha=0.0001)\n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 268,
      "line_range": [
        268
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "268         assert metrics.is_significant(alpha=0.001)\n269         assert not metrics.is_significant(alpha=0.0001)\n270 \n",
      "col_offset": 8,
      "end_col_offset": 55,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 269,
      "line_range": [
        269
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "279         )\n280         assert metrics.get_skill_level() == \"excellent\"\n281 \n",
      "col_offset": 8,
      "end_col_offset": 55,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 280,
      "line_range": [
        280
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "290         )\n291         assert metrics.get_skill_level() == \"good\"\n292 \n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 291,
      "line_range": [
        291
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "301         )\n302         assert metrics.get_skill_level() == \"fair\"\n303 \n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 302,
      "line_range": [
        302
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "312         )\n313         assert metrics.get_skill_level() == \"poor\"\n314 \n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 313,
      "line_range": [
        313
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "323         )\n324         assert metrics.get_signal_persistence() == \"long\"\n325 \n",
      "col_offset": 8,
      "end_col_offset": 57,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 324,
      "line_range": [
        324
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "334         )\n335         assert metrics.get_signal_persistence() == \"short\"\n336 \n",
      "col_offset": 8,
      "end_col_offset": 58,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 335,
      "line_range": [
        335
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "345         )\n346         assert metrics.get_signal_persistence() == \"unknown\"\n347 \n",
      "col_offset": 8,
      "end_col_offset": 60,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 346,
      "line_range": [
        346
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "359         )\n360         assert metrics.annual_breadth == Decimal(\"5200\")\n361 \n",
      "col_offset": 8,
      "end_col_offset": 56,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 360,
      "line_range": [
        360
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "368         )\n369         assert metrics.get_breadth_category() == \"high\"\n370 \n",
      "col_offset": 8,
      "end_col_offset": 55,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "377         )\n378         assert metrics.get_breadth_category() == \"medium\"\n379 \n",
      "col_offset": 8,
      "end_col_offset": 57,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 378,
      "line_range": [
        378
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "386         )\n387         assert metrics.get_breadth_category() == \"low\"\n388 \n",
      "col_offset": 8,
      "end_col_offset": 54,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 387,
      "line_range": [
        387
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "396         sqrt_val = metrics.get_breadth_sqrt()\n397         assert abs(sqrt_val - Decimal(\"20.00\")) < Decimal(\"0.01\")\n398 \n",
      "col_offset": 8,
      "end_col_offset": 65,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 397,
      "line_range": [
        397
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "421         )\n422         assert analysis.strategy_name == \"Test Strategy\"\n423         assert analysis.skill_level == \"good\"\n",
      "col_offset": 8,
      "end_col_offset": 56,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 422,
      "line_range": [
        422
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "422         assert analysis.strategy_name == \"Test Strategy\"\n423         assert analysis.skill_level == \"good\"\n424 \n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 423,
      "line_range": [
        423
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "433         summary = analysis.get_summary()\n434         assert \"Momentum Strategy\" in summary\n435         assert \"IR: 0.80\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 434,
      "line_range": [
        434
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "434         assert \"Momentum Strategy\" in summary\n435         assert \"IR: 0.80\" in summary\n436         assert \"IC: 0.040\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 36,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 435,
      "line_range": [
        435
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "435         assert \"IR: 0.80\" in summary\n436         assert \"IC: 0.040\" in summary\n437         assert \"Skill: good\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 37,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 436,
      "line_range": [
        436
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "436         assert \"IC: 0.040\" in summary\n437         assert \"Skill: good\" in summary\n438 \n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 437,
      "line_range": [
        437
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "448         plan = analysis.get_improvement_plan()\n449         assert \"Improve alpha model\" in plan\n450         assert \"Reduce constraints\" in plan\n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 449,
      "line_range": [
        449
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "449         assert \"Improve alpha model\" in plan\n450         assert \"Reduce constraints\" in plan\n451 \n",
      "col_offset": 8,
      "end_col_offset": 43,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 450,
      "line_range": [
        450
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "460         plan = analysis.get_improvement_plan()\n461         assert \"Improvement Plan\" in plan\n462         assert len(plan) > 0\n",
      "col_offset": 8,
      "end_col_offset": 41,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 461,
      "line_range": [
        461
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "461         assert \"Improvement Plan\" in plan\n462         assert len(plan) > 0\n463 \n",
      "col_offset": 8,
      "end_col_offset": 28,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 462,
      "line_range": [
        462
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "472         decomp = analysis.get_ir_decomposition()\n473         assert \"information_ratio\" in decomp\n474         assert \"ic_contribution\" in decomp\n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 473,
      "line_range": [
        473
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "473         assert \"information_ratio\" in decomp\n474         assert \"ic_contribution\" in decomp\n475         assert \"breadth_contribution\" in decomp\n",
      "col_offset": 8,
      "end_col_offset": 42,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 474,
      "line_range": [
        474
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "474         assert \"ic_contribution\" in decomp\n475         assert \"breadth_contribution\" in decomp\n476         assert decomp[\"information_ratio\"] == 0.8\n",
      "col_offset": 8,
      "end_col_offset": 47,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 475,
      "line_range": [
        475
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "475         assert \"breadth_contribution\" in decomp\n476         assert decomp[\"information_ratio\"] == 0.8\n477 \n",
      "col_offset": 8,
      "end_col_offset": 49,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 476,
      "line_range": [
        476
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "489         calculator = ICCalculator(min_observations=30)\n490         assert calculator.min_observations == 30\n491 \n",
      "col_offset": 8,
      "end_col_offset": 48,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 490,
      "line_range": [
        490
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "495         metrics = calculator.calculate_ic(sample_forecasts, sample_returns)\n496         assert isinstance(metrics, ICMetrics)\n497         assert isinstance(metrics.ic, Decimal)\n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "496         assert isinstance(metrics, ICMetrics)\n497         assert isinstance(metrics.ic, Decimal)\n498 \n",
      "col_offset": 8,
      "end_col_offset": 46,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "504         # Should be very high (close to 1.0)\n505         assert metrics.ic > Decimal(\"0.9\")\n506 \n",
      "col_offset": 8,
      "end_col_offset": 42,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 505,
      "line_range": [
        505
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "512         # Should be close to 0\n513         assert abs(metrics.ic) < Decimal(\"0.3\")\n514 \n",
      "col_offset": 8,
      "end_col_offset": 47,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 513,
      "line_range": [
        513
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "533         metrics = calculator.calculate_ic(sample_forecasts, sample_returns, method=\"spearman\")\n534         assert isinstance(metrics.ic_rank, Decimal)\n535 \n",
      "col_offset": 8,
      "end_col_offset": 51,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 534,
      "line_range": [
        534
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "552         # Should successfully calculate with remaining valid data\n553         assert isinstance(metrics, ICMetrics)\n554 \n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 553,
      "line_range": [
        553
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "558         decay = calculator.calculate_ic_decay(sample_forecasts, sample_returns, periods=[1, 2, 3])\n559         assert len(decay) == 3\n560         assert all(isinstance(d, Decimal) for d in decay)\n",
      "col_offset": 8,
      "end_col_offset": 30,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 559,
      "line_range": [
        559
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "559         assert len(decay) == 3\n560         assert all(isinstance(d, Decimal) for d in decay)\n561 \n",
      "col_offset": 8,
      "end_col_offset": 57,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 560,
      "line_range": [
        560
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "566         p_value, is_sig = calculator.test_significance(ic=0.25, n_observations=100)\n567         assert 0 <= p_value <= 1\n568         assert is_sig  # IC=0.25 with n=100 should be significant\n",
      "col_offset": 8,
      "end_col_offset": 32,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 567,
      "line_range": [
        567
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "567         assert 0 <= p_value <= 1\n568         assert is_sig  # IC=0.25 with n=100 should be significant\n569 \n",
      "col_offset": 8,
      "end_col_offset": 21,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 568,
      "line_range": [
        568
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "575         # Should NOT be significant (p > 0.05)\n576         assert isinstance(is_sig, bool)\n577         assert not is_sig  # Low IC should not be significant\n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 576,
      "line_range": [
        576
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "576         assert isinstance(is_sig, bool)\n577         assert not is_sig  # Low IC should not be significant\n578 \n",
      "col_offset": 8,
      "end_col_offset": 25,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 577,
      "line_range": [
        577
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "582         ci = calculator.calculate_confidence_interval(ic=0.05, n=100)\n583         assert len(ci) == 2\n584         assert ci[0] < 0.05 < ci[1]  # CI should contain the IC\n",
      "col_offset": 8,
      "end_col_offset": 27,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "583         assert len(ci) == 2\n584         assert ci[0] < 0.05 < ci[1]  # CI should contain the IC\n585 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "595         rolling_ic = calculator.calculate_rolling_ic(sample_forecasts, sample_returns, window=30)\n596         assert isinstance(rolling_ic, pd.Series)\n597         assert len(rolling_ic) > 0\n",
      "col_offset": 8,
      "end_col_offset": 48,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "596         assert isinstance(rolling_ic, pd.Series)\n597         assert len(rolling_ic) > 0\n598 \n",
      "col_offset": 8,
      "end_col_offset": 34,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 597,
      "line_range": [
        597
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "618         metrics = calculator.calculate_breadth(n_assets=100, rebalance_frequency=\"weekly\")\n619         assert metrics.annual_breadth == Decimal(\"5200\")  # 52 \u00d7 100\n620         assert metrics.independence_factor == Decimal(\"0.5\")  # Default\n",
      "col_offset": 8,
      "end_col_offset": 56,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 619,
      "line_range": [
        619
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "619         assert metrics.annual_breadth == Decimal(\"5200\")  # 52 \u00d7 100\n620         assert metrics.independence_factor == Decimal(\"0.5\")  # Default\n621 \n",
      "col_offset": 8,
      "end_col_offset": 60,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 620,
      "line_range": [
        620
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "625         metrics = calculator.calculate_breadth(n_assets=50, rebalance_frequency=\"daily\")\n626         assert metrics.annual_breadth == Decimal(\"12600\")  # 252 \u00d7 50\n627 \n",
      "col_offset": 8,
      "end_col_offset": 57,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 626,
      "line_range": [
        626
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "631         metrics = calculator.calculate_breadth(n_assets=200, rebalance_frequency=\"monthly\")\n632         assert metrics.annual_breadth == Decimal(\"2400\")  # 12 \u00d7 200\n633 \n",
      "col_offset": 8,
      "end_col_offset": 56,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 632,
      "line_range": [
        632
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "652         # Should be close to 1.0\n653         assert factor >= Decimal(\"0.9\")\n654 \n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 653,
      "line_range": [
        653
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "663         # Should be low (1/n = 0.2)\n664         assert factor <= Decimal(\"0.3\")\n665 \n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 664,
      "line_range": [
        664
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "669         factor = calculator.calculate_independence_factor(sample_correlation_matrix)\n670         assert Decimal(\"0\") <= factor <= Decimal(\"1\")\n671 \n",
      "col_offset": 8,
      "end_col_offset": 53,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 670,
      "line_range": [
        670
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "682         metrics = calculator.calculate_from_returns(returns)\n683         assert metrics.effective_breadth > 0\n684         assert metrics.independence_factor > 0\n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 683,
      "line_range": [
        683
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "683         assert metrics.effective_breadth > 0\n684         assert metrics.independence_factor > 0\n685 \n",
      "col_offset": 8,
      "end_col_offset": 46,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 684,
      "line_range": [
        684
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "693         )\n694         assert abs(br - Decimal(\"400\")) < Decimal(\"10\")\n695 \n",
      "col_offset": 8,
      "end_col_offset": 55,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 694,
      "line_range": [
        694
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "705         )\n706         assert abs(br - Decimal(\"1600\")) < Decimal(\"50\")\n707 \n",
      "col_offset": 8,
      "end_col_offset": 56,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 706,
      "line_range": [
        706
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "727         decomp = calculator.decompose_breadth(returns)\n728         assert \"n_assets\" in decomp\n729         assert \"periods_per_year\" in decomp\n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "728         assert \"n_assets\" in decomp\n729         assert \"periods_per_year\" in decomp\n730         assert \"independence_factor\" in decomp\n",
      "col_offset": 8,
      "end_col_offset": 43,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "729         assert \"periods_per_year\" in decomp\n730         assert \"independence_factor\" in decomp\n731         assert \"effective_breadth\" in decomp\n",
      "col_offset": 8,
      "end_col_offset": 46,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 730,
      "line_range": [
        730
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "730         assert \"independence_factor\" in decomp\n731         assert \"effective_breadth\" in decomp\n732         assert decomp[\"n_assets\"] == 5\n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 731,
      "line_range": [
        731
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "731         assert \"effective_breadth\" in decomp\n732         assert decomp[\"n_assets\"] == 5\n733 \n",
      "col_offset": 8,
      "end_col_offset": 38,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 732,
      "line_range": [
        732
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "745         calculator = FundamentalLawCalculator()\n746         assert isinstance(calculator.ic_calculator, ICCalculator)\n747         assert isinstance(calculator.breadth_calculator, BreadthCalculator)\n",
      "col_offset": 8,
      "end_col_offset": 65,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "746         assert isinstance(calculator.ic_calculator, ICCalculator)\n747         assert isinstance(calculator.breadth_calculator, BreadthCalculator)\n748 \n",
      "col_offset": 8,
      "end_col_offset": 75,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 747,
      "line_range": [
        747
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "756         )\n757         assert components.information_ratio == Decimal(\"1.0\")\n758         assert components.breadth_sqrt == calculator._calculate_breadth_sqrt(Decimal(\"400\"))\n",
      "col_offset": 8,
      "end_col_offset": 61,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 757,
      "line_range": [
        757
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "757         assert components.information_ratio == Decimal(\"1.0\")\n758         assert components.breadth_sqrt == calculator._calculate_breadth_sqrt(Decimal(\"400\"))\n759 \n",
      "col_offset": 8,
      "end_col_offset": 92,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 758,
      "line_range": [
        758
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "768         )\n769         assert components.transfer_coefficient == Decimal(\"0.5\")\n770 \n",
      "col_offset": 8,
      "end_col_offset": 64,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "799         # IR should be clamped to non-negative by the function\n800         assert components.information_ratio >= 0\n801         assert isinstance(components.information_coefficient, Decimal)\n",
      "col_offset": 8,
      "end_col_offset": 48,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "800         assert components.information_ratio >= 0\n801         assert isinstance(components.information_coefficient, Decimal)\n802 \n",
      "col_offset": 8,
      "end_col_offset": 70,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 801,
      "line_range": [
        801
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "822         analysis = calculator.analyze_strategy(components, \"Test Strategy\")\n823         assert analysis.strategy_name == \"Test Strategy\"\n824         assert analysis.skill_level in [\"excellent\", \"good\", \"fair\", \"poor\"]\n",
      "col_offset": 8,
      "end_col_offset": 56,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "823         assert analysis.strategy_name == \"Test Strategy\"\n824         assert analysis.skill_level in [\"excellent\", \"good\", \"fair\", \"poor\"]\n825         assert analysis.breadth_assessment in [\"high\", \"medium\", \"low\"]\n",
      "col_offset": 8,
      "end_col_offset": 76,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "824         assert analysis.skill_level in [\"excellent\", \"good\", \"fair\", \"poor\"]\n825         assert analysis.breadth_assessment in [\"high\", \"medium\", \"low\"]\n826 \n",
      "col_offset": 8,
      "end_col_offset": 71,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "838         comparison = calculator.compare_strategies(strategies)\n839         assert len(comparison) == 2\n840         assert \"IR\" in comparison.columns\n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 839,
      "line_range": [
        839
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "839         assert len(comparison) == 2\n840         assert \"IR\" in comparison.columns\n841         assert \"IC\" in comparison.columns\n",
      "col_offset": 8,
      "end_col_offset": 41,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 840,
      "line_range": [
        840
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "840         assert \"IR\" in comparison.columns\n841         assert \"IC\" in comparison.columns\n842 \n",
      "col_offset": 8,
      "end_col_offset": 41,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 841,
      "line_range": [
        841
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "851         )\n852         assert abs(ic - Decimal(\"0.05\")) < Decimal(\"0.01\")\n853 \n",
      "col_offset": 8,
      "end_col_offset": 58,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 852,
      "line_range": [
        852
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "857         sqrt_val = calculator._calculate_breadth_sqrt(Decimal(\"400\"))\n858         assert abs(sqrt_val - Decimal(\"20.0\")) < Decimal(\"0.01\")\n859 \n",
      "col_offset": 8,
      "end_col_offset": 64,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 858,
      "line_range": [
        858
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "862         calculator = FundamentalLawCalculator()\n863         assert calculator._assess_skill_level(Decimal(\"0.06\")) == \"excellent\"\n864         assert calculator._assess_skill_level(Decimal(\"0.04\")) == \"good\"\n",
      "col_offset": 8,
      "end_col_offset": 77,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 863,
      "line_range": [
        863
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "863         assert calculator._assess_skill_level(Decimal(\"0.06\")) == \"excellent\"\n864         assert calculator._assess_skill_level(Decimal(\"0.04\")) == \"good\"\n865         assert calculator._assess_skill_level(Decimal(\"0.02\")) == \"fair\"\n",
      "col_offset": 8,
      "end_col_offset": 72,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 864,
      "line_range": [
        864
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "864         assert calculator._assess_skill_level(Decimal(\"0.04\")) == \"good\"\n865         assert calculator._assess_skill_level(Decimal(\"0.02\")) == \"fair\"\n866         assert calculator._assess_skill_level(Decimal(\"0.005\")) == \"poor\"\n",
      "col_offset": 8,
      "end_col_offset": 72,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 865,
      "line_range": [
        865
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "865         assert calculator._assess_skill_level(Decimal(\"0.02\")) == \"fair\"\n866         assert calculator._assess_skill_level(Decimal(\"0.005\")) == \"poor\"\n867 \n",
      "col_offset": 8,
      "end_col_offset": 73,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "870         calculator = FundamentalLawCalculator()\n871         assert calculator._assess_breadth(Decimal(\"1500\")) == \"high\"\n872         assert calculator._assess_breadth(Decimal(\"500\")) == \"medium\"\n",
      "col_offset": 8,
      "end_col_offset": 68,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 871,
      "line_range": [
        871
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "871         assert calculator._assess_breadth(Decimal(\"1500\")) == \"high\"\n872         assert calculator._assess_breadth(Decimal(\"500\")) == \"medium\"\n873         assert calculator._assess_breadth(Decimal(\"50\")) == \"low\"\n",
      "col_offset": 8,
      "end_col_offset": 69,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 872,
      "line_range": [
        872
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "872         assert calculator._assess_breadth(Decimal(\"500\")) == \"medium\"\n873         assert calculator._assess_breadth(Decimal(\"50\")) == \"low\"\n874 \n",
      "col_offset": 8,
      "end_col_offset": 65,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 873,
      "line_range": [
        873
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "877         calculator = FundamentalLawCalculator()\n878         assert calculator._assess_ir(Decimal(\"1.5\")) == \"excellent\"\n879         assert calculator._assess_ir(Decimal(\"0.7\")) == \"good\"\n",
      "col_offset": 8,
      "end_col_offset": 67,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 878,
      "line_range": [
        878
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "878         assert calculator._assess_ir(Decimal(\"1.5\")) == \"excellent\"\n879         assert calculator._assess_ir(Decimal(\"0.7\")) == \"good\"\n880         assert calculator._assess_ir(Decimal(\"0.3\")) == \"fair\"\n",
      "col_offset": 8,
      "end_col_offset": 62,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 879,
      "line_range": [
        879
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "879         assert calculator._assess_ir(Decimal(\"0.7\")) == \"good\"\n880         assert calculator._assess_ir(Decimal(\"0.3\")) == \"fair\"\n881         assert calculator._assess_ir(Decimal(\"0.1\")) == \"poor\"\n",
      "col_offset": 8,
      "end_col_offset": 62,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 880,
      "line_range": [
        880
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "880         assert calculator._assess_ir(Decimal(\"0.3\")) == \"fair\"\n881         assert calculator._assess_ir(Decimal(\"0.1\")) == \"poor\"\n882 \n",
      "col_offset": 8,
      "end_col_offset": 62,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 881,
      "line_range": [
        881
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "885         calculator = FundamentalLawCalculator()\n886         assert calculator._assess_tc(Decimal(\"0.9\")) == \"excellent\"\n887         assert calculator._assess_tc(Decimal(\"0.7\")) == \"good\"\n",
      "col_offset": 8,
      "end_col_offset": 67,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 886,
      "line_range": [
        886
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "886         assert calculator._assess_tc(Decimal(\"0.9\")) == \"excellent\"\n887         assert calculator._assess_tc(Decimal(\"0.7\")) == \"good\"\n888         assert calculator._assess_tc(Decimal(\"0.5\")) == \"fair\"\n",
      "col_offset": 8,
      "end_col_offset": 62,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 887,
      "line_range": [
        887
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "887         assert calculator._assess_tc(Decimal(\"0.7\")) == \"good\"\n888         assert calculator._assess_tc(Decimal(\"0.5\")) == \"fair\"\n889         assert calculator._assess_tc(Decimal(\"0.3\")) == \"poor\"\n",
      "col_offset": 8,
      "end_col_offset": 62,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 888,
      "line_range": [
        888
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "888         assert calculator._assess_tc(Decimal(\"0.5\")) == \"fair\"\n889         assert calculator._assess_tc(Decimal(\"0.3\")) == \"poor\"\n890 \n",
      "col_offset": 8,
      "end_col_offset": 62,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 889,
      "line_range": [
        889
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "921         # Verify results\n922         assert isinstance(analysis, StrategyAnalysis)\n923         assert analysis.strategy_name == \"Integration Test Strategy\"\n",
      "col_offset": 8,
      "end_col_offset": 53,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 922,
      "line_range": [
        922
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "922         assert isinstance(analysis, StrategyAnalysis)\n923         assert analysis.strategy_name == \"Integration Test Strategy\"\n924         # Components should be valid (IR is non-negative after clamping)\n",
      "col_offset": 8,
      "end_col_offset": 68,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 923,
      "line_range": [
        923
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "924         # Components should be valid (IR is non-negative after clamping)\n925         assert components.validate(tolerance=Decimal(\"1.0\"))  # Allow larger tolerance\n926 \n",
      "col_offset": 8,
      "end_col_offset": 60,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
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
      "code": "953         # Verify we got some IC values\n954         assert len(ics) > 0\n955         assert br_metrics.effective_breadth > 0\n",
      "col_offset": 8,
      "end_col_offset": 27,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 954,
      "line_range": [
        954
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "954         assert len(ics) > 0\n955         assert br_metrics.effective_breadth > 0\n956 \n",
      "col_offset": 8,
      "end_col_offset": 47,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 955,
      "line_range": [
        955
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "988         # Verify results\n989         assert len(comparison) == 3\n990         assert all(name in analyses for name in strategies.keys())\n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 989,
      "line_range": [
        989
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "989         assert len(comparison) == 3\n990         assert all(name in analyses for name in strategies.keys())\n991 \n",
      "col_offset": 8,
      "end_col_offset": 66,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 990,
      "line_range": [
        990
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "993         ir_values = comparison[\"IR\"].values\n994         assert all(abs(ir - 0.7) < 0.2 for ir in ir_values)\n995 \n",
      "col_offset": 8,
      "end_col_offset": 59,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 994,
      "line_range": [
        994
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1014         )\n1015         assert components.breadth == Decimal(\"0\")\n1016         assert components.breadth_sqrt == Decimal(\"0\")\n",
      "col_offset": 8,
      "end_col_offset": 49,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1015,
      "line_range": [
        1015
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1015         assert components.breadth == Decimal(\"0\")\n1016         assert components.breadth_sqrt == Decimal(\"0\")\n1017 \n",
      "col_offset": 8,
      "end_col_offset": 54,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1016,
      "line_range": [
        1016
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1023         # Handle edge case of perfect correlation\n1024         assert metrics.ic <= Decimal(\"1.0\")\n1025 \n",
      "col_offset": 8,
      "end_col_offset": 43,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1024,
      "line_range": [
        1024
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1032         # Should return zero IC for constant series\n1033         assert metrics.ic == Decimal(\"0\")\n1034 \n",
      "col_offset": 8,
      "end_col_offset": 41,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1033,
      "line_range": [
        1033
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1038         metrics = calculator.calculate_breadth(n_assets=1, rebalance_frequency=\"weekly\")\n1039         assert metrics.annual_breadth == Decimal(\"52\")\n1040 \n",
      "col_offset": 8,
      "end_col_offset": 54,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1039,
      "line_range": [
        1039
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1044         metrics = calculator.calculate_breadth(n_assets=5000, rebalance_frequency=\"daily\")\n1045         assert metrics.annual_breadth == Decimal(\"1260000\")  # 252 \u00d7 5000\n1046 \n",
      "col_offset": 8,
      "end_col_offset": 59,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1045,
      "line_range": [
        1045
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1055         # Should still return a valid factor\n1056         assert Decimal(\"0\") <= factor <= Decimal(\"1\")\n",
      "col_offset": 8,
      "end_col_offset": 53,
      "filename": "./app/tests/analysis/test_fundamental_law.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1056,
      "line_range": [
        1056
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    }
  ]
}```

## 4. Complexity (radon)
app/tests/analysis/test_fundamental_law.py
    M 717:4 TestBreadthCalculator.test_decompose_breadth - B (7)
    C 897:0 TestFundamentalLawIntegration - B (6)
    M 927:4 TestFundamentalLawIntegration.test_ic_and_breadth_integration - B (6)
    M 425:4 TestStrategyAnalysis.test_get_summary - A (5)
    M 464:4 TestStrategyAnalysis.test_get_ir_decomposition - A (5)
    M 860:4 TestFundamentalLawCalculator.test_assess_skill_level - A (5)
    M 875:4 TestFundamentalLawCalculator.test_assess_ir - A (5)
    M 883:4 TestFundamentalLawCalculator.test_assess_tc - A (5)
    M 957:4 TestFundamentalLawIntegration.test_strategy_comparison_workflow - A (5)
    C 400:0 TestStrategyAnalysis - A (4)
    M 672:4 TestBreadthCalculator.test_calculate_from_returns - A (4)
    C 740:0 TestFundamentalLawCalculator - A (4)
    M 814:4 TestFundamentalLawCalculator.test_analyze_strategy - A (4)
    M 827:4 TestFundamentalLawCalculator.test_compare_strategies - A (4)
    M 868:4 TestFundamentalLawCalculator.test_assess_breadth - A (4)
    M 900:4 TestFundamentalLawIntegration.test_full_workflow_analysis - A (4)
    F 88:0 sample_correlation_matrix - A (3)
    C 137:0 TestFundamentalLawComponents - A (3)
    M 140:4 TestFundamentalLawComponents.test_creation_valid - A (3)
    C 223:0 TestICMetrics - A (3)
    M 259:4 TestICMetrics.test_is_significant_custom_alpha - A (3)
    C 349:0 TestBreadthMetrics - A (3)
    M 414:4 TestStrategyAnalysis.test_creation - A (3)
    M 439:4 TestStrategyAnalysis.test_get_improvement_plan_with_suggestions - A (3)
    M 452:4 TestStrategyAnalysis.test_get_improvement_plan_without_suggestions - A (3)
    C 484:0 TestICCalculator - A (3)
    M 492:4 TestICCalculator.test_calculate_ic_valid - A (3)
    M 555:4 TestICCalculator.test_calculate_ic_decay - A (3)
    M 562:4 TestICCalculator.test_test_significance - A (3)
    M 570:4 TestICCalculator.test_test_significance_low_ic - A (3)
    M 579:4 TestICCalculator.test_calculate_confidence_interval - A (3)
    M 592:4 TestICCalculator.test_calculate_rolling_ic - A (3)
    C 612:0 TestBreadthCalculator - A (3)
    M 615:4 TestBreadthCalculator.test_calculate_breadth_weekly - A (3)
    M 743:4 TestFundamentalLawCalculator.test_initialization - A (3)
    M 749:4 TestFundamentalLawCalculator.test_calculate_fundamental_law - A (3)
    M 791:4 TestFundamentalLawCalculator.test_decompose_ir - A (3)
    C 1002:0 TestEdgeCases - A (3)
    M 1005:4 TestEdgeCases.test_zero_breadth - A (3)
    M 152:4 TestFundamentalLawComponents.test_validate_perfect_law - A (2)
    M 163:4 TestFundamentalLawComponents.test_validate_with_tolerance - A (2)
    M 198:4 TestFundamentalLawComponents.test_get_theoretical_ir - A (2)
    M 210:4 TestFundamentalLawComponents.test_get_efficiency_gap - A (2)
    M 226:4 TestICMetrics.test_creation - A (2)
    M 237:4 TestICMetrics.test_is_significant_true - A (2)
    M 248:4 TestICMetrics.test_is_significant_false - A (2)
    M 271:4 TestICMetrics.test_get_skill_level_excellent - A (2)
    M 282:4 TestICMetrics.test_get_skill_level_good - A (2)
    M 293:4 TestICMetrics.test_get_skill_level_fair - A (2)
    M 304:4 TestICMetrics.test_get_skill_level_poor - A (2)
    M 315:4 TestICMetrics.test_get_signal_persistence_long - A (2)
    M 326:4 TestICMetrics.test_get_signal_persistence_short - A (2)
    M 337:4 TestICMetrics.test_get_signal_persistence_empty - A (2)
    M 352:4 TestBreadthMetrics.test_creation - A (2)
    M 362:4 TestBreadthMetrics.test_get_breadth_category_high - A (2)
    M 371:4 TestBreadthMetrics.test_get_breadth_category_medium - A (2)
    M 380:4 TestBreadthMetrics.test_get_breadth_category_low - A (2)
    M 389:4 TestBreadthMetrics.test_get_breadth_sqrt - A (2)
    M 487:4 TestICCalculator.test_initialization - A (2)
    M 499:4 TestICCalculator.test_calculate_ic_perfect_correlation - A (2)
    M 507:4 TestICCalculator.test_calculate_ic_uncorrelated - A (2)
    M 530:4 TestICCalculator.test_calculate_ic_spearman - A (2)
    M 542:4 TestICCalculator.test_calculate_ic_with_nans - A (2)
    M 622:4 TestBreadthCalculator.test_calculate_breadth_daily - A (2)
    M 628:4 TestBreadthCalculator.test_calculate_breadth_monthly - A (2)
    M 646:4 TestBreadthCalculator.test_calculate_independence_factor_uncorrelated - A (2)
    M 655:4 TestBreadthCalculator.test_calculate_independence_factor_correlated - A (2)
    M 666:4 TestBreadthCalculator.test_calculate_independence_factor_sample_matrix - A (2)
    M 686:4 TestBreadthCalculator.test_estimate_required_breadth - A (2)
    M 696:4 TestBreadthCalculator.test_estimate_required_breadth_with_tc - A (2)
    M 760:4 TestFundamentalLawCalculator.test_calculate_fundamental_law_with_tc - A (2)
    M 843:4 TestFundamentalLawCalculator.test_calculate_required_ic_for_target_ir - A (2)
    M 854:4 TestFundamentalLawCalculator.test_calculate_breadth_sqrt - A (2)
    M 1018:4 TestEdgeCases.test_perfect_correlation_ic - A (2)
    M 1026:4 TestEdgeCases.test_constant_series_ic - A (2)
    M 1035:4 TestEdgeCases.test_single_asset_breadth - A (2)
    M 1041:4 TestEdgeCases.test_very_large_breadth - A (2)
    M 1047:4 TestEdgeCases.test_negative_correlation_matrix - A (2)
    F 41:0 sample_forecasts - A (1)
    F 52:0 sample_returns - A (1)
    F 66:0 sample_benchmark_returns - A (1)
    F 77:0 sample_portfolio_returns - A (1)
    F 104:0 perfect_forecasts_and_returns - A (1)
    F 116:0 uncorrelated_forecasts_and_returns - A (1)
    M 174:4 TestFundamentalLawComponents.test_validate_negative_ir_raises - A (1)
    M 186:4 TestFundamentalLawComponents.test_validate_negative_ic_raises - A (1)
    M 404:4 TestStrategyAnalysis.sample_components - A (1)
    M 515:4 TestICCalculator.test_calculate_ic_different_lengths_raises - A (1)
    M 522:4 TestICCalculator.test_calculate_ic_insufficient_data_raises - A (1)
    M 536:4 TestICCalculator.test_calculate_ic_invalid_method_raises - A (1)
    M 586:4 TestICCalculator.test_calculate_confidence_interval_invalid_ic_raises - A (1)
    M 599:4 TestICCalculator.test_calculate_rolling_ic_insufficient_data_raises - A (1)
    M 634:4 TestBreadthCalculator.test_calculate_breadth_invalid_frequency_raises - A (1)
    M 640:4 TestBreadthCalculator.test_calculate_breadth_negative_assets_raises - A (1)
    M 708:4 TestBreadthCalculator.test_estimate_required_breadth_zero_ic_raises - A (1)
    M 771:4 TestFundamentalLawCalculator.test_calculate_fundamental_law_negative_ir_raises - A (1)
    M 781:4 TestFundamentalLawCalculator.test_calculate_fundamental_law_invalid_ic_raises - A (1)
    M 803:4 TestFundamentalLawCalculator.test_decompose_ir_different_lengths_raises - A (1)

98 blocks (classes, functions, methods) analyzed.
Average complexity: A (2.489795918367347)

## 5. Maintainability Index
app/tests/analysis/test_fundamental_law.py - C (7.16)

## 6. Syntax Check
**Status:** ✅ PASSED

## 7. Import Validation
**Status:** ✅ PASSED

---
## Summary
**Validation completed at:** 2026-02-07T07:10:56Z

