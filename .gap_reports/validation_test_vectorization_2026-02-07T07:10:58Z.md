# Validation Report: app/tests/analysis/test_vectorization.py
**Generated:** 2026-02-07T07:10:58Z

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
      "column": 15,
      "row": 11
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/analysis/test_vectorization.py",
    "fix": {
      "applicability": "safe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 1,
            "row": 12
          },
          "location": {
            "column": 1,
            "row": 11
          }
        }
      ],
      "message": "Remove unused import: `logging`"
    },
    "location": {
      "column": 8,
      "row": 11
    },
    "message": "`logging` imported but unused",
    "noqa_row": 11,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F404",
    "end_location": {
      "column": 35,
      "row": 13
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/analysis/test_vectorization.py",
    "fix": null,
    "location": {
      "column": 1,
      "row": 13
    },
    "message": "`from __future__` imports must occur at the beginning of the file",
    "noqa_row": 13,
    "url": "https://docs.astral.sh/ruff/rules/late-future-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 11,
      "row": 15
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/analysis/test_vectorization.py",
    "fix": {
      "applicability": "safe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 1,
            "row": 16
          },
          "location": {
            "column": 1,
            "row": 15
          }
        }
      ],
      "message": "Remove unused import: `ast`"
    },
    "location": {
      "column": 8,
      "row": 15
    },
    "message": "`ast` imported but unused",
    "noqa_row": 15,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 12,
      "row": 16
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/analysis/test_vectorization.py",
    "fix": {
      "applicability": "safe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 1,
            "row": 17
          },
          "location": {
            "column": 1,
            "row": 16
          }
        }
      ],
      "message": "Remove unused import: `time`"
    },
    "location": {
      "column": 8,
      "row": 16
    },
    "message": "`time` imported but unused",
    "noqa_row": 16,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 31,
      "row": 19
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/analysis/test_vectorization.py",
    "fix": {
      "applicability": "safe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 1,
            "row": 20
          },
          "location": {
            "column": 1,
            "row": 19
          }
        }
      ],
      "message": "Remove unused import"
    },
    "location": {
      "column": 27,
      "row": 19
    },
    "message": "`unittest.mock.Mock` imported but unused",
    "noqa_row": 19,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 38,
      "row": 19
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/analysis/test_vectorization.py",
    "fix": {
      "applicability": "safe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 1,
            "row": 20
          },
          "location": {
            "column": 1,
            "row": 19
          }
        }
      ],
      "message": "Remove unused import"
    },
    "location": {
      "column": 33,
      "row": 19
    },
    "message": "`unittest.mock.patch` imported but unused",
    "noqa_row": 19,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "F401",
    "end_location": {
      "column": 20,
      "row": 22
    },
    "filename": "/Users/kepa.cantero/Projects/algoTrading/app/tests/analysis/test_vectorization.py",
    "fix": {
      "applicability": "safe",
      "edits": [
        {
          "content": "",
          "end_location": {
            "column": 1,
            "row": 23
          },
          "location": {
            "column": 1,
            "row": 22
          }
        }
      ],
      "message": "Remove unused import: `pandas`"
    },
    "location": {
      "column": 18,
      "row": 22
    },
    "message": "`pandas` imported but unused",
    "noqa_row": 22,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  }
]```

## 3. Security (bandit)
**Status:** ⚠️ ISSUES FOUND
```json
{
  "errors": [],
  "generated_at": "2026-02-07T07:10:58Z",
  "metrics": {
    "./app/tests/analysis/test_vectorization.py": {
      "CONFIDENCE.HIGH": 147,
      "CONFIDENCE.LOW": 0,
      "CONFIDENCE.MEDIUM": 0,
      "CONFIDENCE.UNDEFINED": 0,
      "SEVERITY.HIGH": 0,
      "SEVERITY.LOW": 147,
      "SEVERITY.MEDIUM": 0,
      "SEVERITY.UNDEFINED": 0,
      "loc": 842,
      "nosec": 0,
      "skipped_tests": 0
    },
    "_totals": {
      "CONFIDENCE.HIGH": 147,
      "CONFIDENCE.LOW": 0,
      "CONFIDENCE.MEDIUM": 0,
      "CONFIDENCE.UNDEFINED": 0,
      "SEVERITY.HIGH": 0,
      "SEVERITY.LOW": 147,
      "SEVERITY.MEDIUM": 0,
      "SEVERITY.UNDEFINED": 0,
      "loc": 842,
      "nosec": 0,
      "skipped_tests": 0
    }
  },
  "results": [
    {
      "code": "148 \n149         assert issue.file_path == \"/path/to/file.py\"\n150         assert issue.line_number == 42\n",
      "col_offset": 8,
      "end_col_offset": 52,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "149         assert issue.file_path == \"/path/to/file.py\"\n150         assert issue.line_number == 42\n151         assert issue.issue_type == \"for_loop\"\n",
      "col_offset": 8,
      "end_col_offset": 38,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "150         assert issue.line_number == 42\n151         assert issue.issue_type == \"for_loop\"\n152         assert issue.severity == \"high\"\n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 151,
      "line_range": [
        151
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "151         assert issue.issue_type == \"for_loop\"\n152         assert issue.severity == \"high\"\n153 \n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 152,
      "line_range": [
        152
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "191 \n192         assert critical_issue.get_severity_weight() == 10\n193 \n",
      "col_offset": 8,
      "end_col_offset": 57,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 192,
      "line_range": [
        192
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "203 \n204         assert high_issue.get_severity_weight() == 5\n205 \n",
      "col_offset": 8,
      "end_col_offset": 52,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 204,
      "line_range": [
        204
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "218         summary = issue.get_display_summary()\n219         assert \"[HIGH]\" in summary\n220         assert \"/path/to/file.py:42\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 34,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 219,
      "line_range": [
        219
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "219         assert \"[HIGH]\" in summary\n220         assert \"/path/to/file.py:42\" in summary\n221         assert \"for_loop\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 47,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "220         assert \"/path/to/file.py:42\" in summary\n221         assert \"for_loop\" in summary\n222         assert \"Test issue\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 36,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 221,
      "line_range": [
        221
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "221         assert \"for_loop\" in summary\n222         assert \"Test issue\" in summary\n223 \n",
      "col_offset": 8,
      "end_col_offset": 38,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 222,
      "line_range": [
        222
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "244 \n245         assert report.total_files_scanned == 10\n246         assert report.total_issues_found == 5\n",
      "col_offset": 8,
      "end_col_offset": 47,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 245,
      "line_range": [
        245
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "245         assert report.total_files_scanned == 10\n246         assert report.total_issues_found == 5\n247         assert report.vectorization_score == Decimal(\"85.0\")\n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "246         assert report.total_issues_found == 5\n247         assert report.vectorization_score == Decimal(\"85.0\")\n248 \n",
      "col_offset": 8,
      "end_col_offset": 60,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 247,
      "line_range": [
        247
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "260 \n261         assert report.get_grade() == \"A\"\n262 \n",
      "col_offset": 8,
      "end_col_offset": 40,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 261,
      "line_range": [
        261
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "274 \n275         assert report.get_grade() == \"B\"\n276 \n",
      "col_offset": 8,
      "end_col_offset": 40,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 275,
      "line_range": [
        275
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "288 \n289         assert report.get_grade() == \"F\"\n290 \n",
      "col_offset": 8,
      "end_col_offset": 40,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 289,
      "line_range": [
        289
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "305         summary = report.get_summary()\n306         assert \"85.0\" in summary\n307         assert \"Grade: B\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 32,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 306,
      "line_range": [
        306
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "306         assert \"85.0\" in summary\n307         assert \"Grade: B\" in summary\n308         assert \"Files Scanned: 10\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 36,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 307,
      "line_range": [
        307
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "307         assert \"Grade: B\" in summary\n308         assert \"Files Scanned: 10\" in summary\n309         assert \"Total Issues: 5\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 308,
      "line_range": [
        308
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "308         assert \"Files Scanned: 10\" in summary\n309         assert \"Total Issues: 5\" in summary\n310 \n",
      "col_offset": 8,
      "end_col_offset": 43,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 309,
      "line_range": [
        309
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "322 \n323         assert report.is_compliant(threshold=80.0) is True\n324         assert report.is_compliant(threshold=90.0) is False\n",
      "col_offset": 8,
      "end_col_offset": 58,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 323,
      "line_range": [
        323
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "323         assert report.is_compliant(threshold=80.0) is True\n324         assert report.is_compliant(threshold=90.0) is False\n325 \n",
      "col_offset": 8,
      "end_col_offset": 59,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "346 \n347         assert result.function_name == \"test_func\"\n348         assert result.speedup == 10.0\n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 347,
      "line_range": [
        347
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "347         assert result.function_name == \"test_func\"\n348         assert result.speedup == 10.0\n349 \n",
      "col_offset": 8,
      "end_col_offset": 37,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 348,
      "line_range": [
        348
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "388         summary = result.get_summary()\n389         assert \"array_sum\" in summary\n390         assert \"1,000,000\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 37,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 389,
      "line_range": [
        389
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "389         assert \"array_sum\" in summary\n390         assert \"1,000,000\" in summary\n391         assert \"10.00x\" in summary\n",
      "col_offset": 8,
      "end_col_offset": 37,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 390,
      "line_range": [
        390
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "390         assert \"1,000,000\" in summary\n391         assert \"10.00x\" in summary\n392 \n",
      "col_offset": 8,
      "end_col_offset": 34,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 391,
      "line_range": [
        391
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "404         )\n405         assert result_excellent.get_performance_grade() == \"A+\"\n406 \n",
      "col_offset": 8,
      "end_col_offset": 63,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 405,
      "line_range": [
        405
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "416         )\n417         assert result_poor.get_performance_grade() == \"F\"\n418 \n",
      "col_offset": 8,
      "end_col_offset": 57,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 417,
      "line_range": [
        417
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "431         result_dict = result.to_dict()\n432         assert result_dict[\"function_name\"] == \"test_func\"\n433         assert result_dict[\"speedup\"] == 10.0\n",
      "col_offset": 8,
      "end_col_offset": 58,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 432,
      "line_range": [
        432
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "432         assert result_dict[\"function_name\"] == \"test_func\"\n433         assert result_dict[\"speedup\"] == 10.0\n434         assert \"performance_grade\" in result_dict\n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 433,
      "line_range": [
        433
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "433         assert result_dict[\"speedup\"] == 10.0\n434         assert \"performance_grade\" in result_dict\n435 \n",
      "col_offset": 8,
      "end_col_offset": 49,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "447         auditor = VectorizationAuditor()\n448         assert auditor.exclude_dirs is not None\n449         assert \"*.py\" in auditor.file_patterns\n",
      "col_offset": 8,
      "end_col_offset": 47,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 448,
      "line_range": [
        448
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "448         assert auditor.exclude_dirs is not None\n449         assert \"*.py\" in auditor.file_patterns\n450 \n",
      "col_offset": 8,
      "end_col_offset": 46,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "458 \n459         assert len(issues) > 0\n460         assert any(issue.issue_type == \"for_loop\" for issue in issues)\n",
      "col_offset": 8,
      "end_col_offset": 30,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 459,
      "line_range": [
        459
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "459         assert len(issues) > 0\n460         assert any(issue.issue_type == \"for_loop\" for issue in issues)\n461         assert any(issue.issue_type == \"range_len\" for issue in issues)\n",
      "col_offset": 8,
      "end_col_offset": 70,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 460,
      "line_range": [
        460
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "460         assert any(issue.issue_type == \"for_loop\" for issue in issues)\n461         assert any(issue.issue_type == \"range_len\" for issue in issues)\n462 \n",
      "col_offset": 8,
      "end_col_offset": 71,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "470 \n471         assert len(issues) > 0\n472         assert any(issue.issue_type in {\"for_loop\", \"range_len\"} for issue in issues)\n",
      "col_offset": 8,
      "end_col_offset": 30,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 471,
      "line_range": [
        471
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "471         assert len(issues) > 0\n472         assert any(issue.issue_type in {\"for_loop\", \"range_len\"} for issue in issues)\n473 \n",
      "col_offset": 8,
      "end_col_offset": 85,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 472,
      "line_range": [
        472
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "481 \n482         assert len(issues) > 0\n483         assert any(issue.issue_type == \"apply\" for issue in issues)\n",
      "col_offset": 8,
      "end_col_offset": 30,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 482,
      "line_range": [
        482
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "482         assert len(issues) > 0\n483         assert any(issue.issue_type == \"apply\" for issue in issues)\n484 \n",
      "col_offset": 8,
      "end_col_offset": 67,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 483,
      "line_range": [
        483
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "492 \n493         assert len(issues) > 0\n494         assert any(issue.issue_type == \"iterrows\" for issue in issues)\n",
      "col_offset": 8,
      "end_col_offset": 30,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 493,
      "line_range": [
        493
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "493         assert len(issues) > 0\n494         assert any(issue.issue_type == \"iterrows\" for issue in issues)\n495 \n",
      "col_offset": 8,
      "end_col_offset": 70,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 494,
      "line_range": [
        494
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "504         # Should have minimal or no issues\n505         assert len(issues) == 0\n506 \n",
      "col_offset": 8,
      "end_col_offset": 31,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "529         score = auditor.calculate_score([])\n530         assert score == Decimal(\"100.0\")\n531 \n",
      "col_offset": 8,
      "end_col_offset": 40,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 530,
      "line_range": [
        530
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "556         score = auditor.calculate_score(issues)\n557         assert score == Decimal(\"85.0\")\n558 \n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 557,
      "line_range": [
        557
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "574         score = auditor.calculate_score(issues)\n575         assert score == Decimal(\"0\")\n576 \n",
      "col_offset": 8,
      "end_col_offset": 36,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 575,
      "line_range": [
        575
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "593         # With just 1 high issue, we may not get specific recommendations\n594         assert isinstance(recommendations, list)\n595 \n",
      "col_offset": 8,
      "end_col_offset": 48,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 594,
      "line_range": [
        594
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "608 \n609         assert report.total_files_scanned >= 2  # May find more .py files\n610         assert report.total_issues_found > 0\n",
      "col_offset": 8,
      "end_col_offset": 46,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 609,
      "line_range": [
        609
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "609         assert report.total_files_scanned >= 2  # May find more .py files\n610         assert report.total_issues_found > 0\n611         assert isinstance(report.vectorization_score, Decimal)\n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 610,
      "line_range": [
        610
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "610         assert report.total_issues_found > 0\n611         assert isinstance(report.vectorization_score, Decimal)\n612 \n",
      "col_offset": 8,
      "end_col_offset": 62,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 611,
      "line_range": [
        611
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "619         issues = auditor.audit_code_snippet(code)\n620         assert any(issue.issue_type == \"for_loop\" for issue in issues)\n621 \n",
      "col_offset": 8,
      "end_col_offset": 70,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "628         issues = auditor.audit_code_snippet(code)\n629         assert any(issue.issue_type == \"range_len\" for issue in issues)\n630 \n",
      "col_offset": 8,
      "end_col_offset": 71,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "637         issues = auditor.audit_code_snippet(code)\n638         assert any(issue.issue_type == \"enumerate\" for issue in issues)\n639 \n",
      "col_offset": 8,
      "end_col_offset": 71,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 638,
      "line_range": [
        638
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "645         issues = auditor.audit_code_snippet(code)\n646         assert any(issue.issue_type == \"apply\" for issue in issues)\n647 \n",
      "col_offset": 8,
      "end_col_offset": 67,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 646,
      "line_range": [
        646
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "654         issues = auditor.audit_code_snippet(code)\n655         assert any(issue.issue_type == \"iterrows\" for issue in issues)\n656 \n",
      "col_offset": 8,
      "end_col_offset": 70,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 655,
      "line_range": [
        655
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "662         issues = auditor.audit_code_snippet(code)\n663         assert any(issue.issue_type == \"list_comp\" for issue in issues)\n664 \n",
      "col_offset": 8,
      "end_col_offset": 71,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 663,
      "line_range": [
        663
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "676         benchmark = VectorizationBenchmark()\n677         assert benchmark.warmup_iterations == 3\n678         assert benchmark.benchmark_iterations == 10\n",
      "col_offset": 8,
      "end_col_offset": 47,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 677,
      "line_range": [
        677
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "677         assert benchmark.warmup_iterations == 3\n678         assert benchmark.benchmark_iterations == 10\n679 \n",
      "col_offset": 8,
      "end_col_offset": 51,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 678,
      "line_range": [
        678
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "683 \n684         assert isinstance(result, BenchmarkResult)\n685         assert result.function_name == \"array_sum\"\n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "684         assert isinstance(result, BenchmarkResult)\n685         assert result.function_name == \"array_sum\"\n686         assert result.vectorized_time > 0\n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 685,
      "line_range": [
        685
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "685         assert result.function_name == \"array_sum\"\n686         assert result.vectorized_time > 0\n687         assert result.non_vectorized_time > 0\n",
      "col_offset": 8,
      "end_col_offset": 41,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 686,
      "line_range": [
        686
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "686         assert result.vectorized_time > 0\n687         assert result.non_vectorized_time > 0\n688         assert result.speedup > 0\n",
      "col_offset": 8,
      "end_col_offset": 45,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 687,
      "line_range": [
        687
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "687         assert result.non_vectorized_time > 0\n688         assert result.speedup > 0\n689 \n",
      "col_offset": 8,
      "end_col_offset": 33,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 688,
      "line_range": [
        688
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "693 \n694         assert isinstance(result, BenchmarkResult)\n695         assert result.function_name == \"ewm_mean\"\n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "694         assert isinstance(result, BenchmarkResult)\n695         assert result.function_name == \"ewm_mean\"\n696         assert result.speedup > 0\n",
      "col_offset": 8,
      "end_col_offset": 49,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 695,
      "line_range": [
        695
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "695         assert result.function_name == \"ewm_mean\"\n696         assert result.speedup > 0\n697 \n",
      "col_offset": 8,
      "end_col_offset": 33,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 696,
      "line_range": [
        696
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "701 \n702         assert isinstance(result, BenchmarkResult)\n703         assert result.function_name == \"rolling_mean\"\n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 702,
      "line_range": [
        702
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "702         assert isinstance(result, BenchmarkResult)\n703         assert result.function_name == \"rolling_mean\"\n704         assert result.speedup > 0\n",
      "col_offset": 8,
      "end_col_offset": 53,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 703,
      "line_range": [
        703
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "703         assert result.function_name == \"rolling_mean\"\n704         assert result.speedup > 0\n705 \n",
      "col_offset": 8,
      "end_col_offset": 33,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "709 \n710         assert isinstance(result, BenchmarkResult)\n711         assert result.function_name == \"correlation_matrix\"\n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 710,
      "line_range": [
        710
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "710         assert isinstance(result, BenchmarkResult)\n711         assert result.function_name == \"correlation_matrix\"\n712         assert result.speedup > 0\n",
      "col_offset": 8,
      "end_col_offset": 59,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 711,
      "line_range": [
        711
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "711         assert result.function_name == \"correlation_matrix\"\n712         assert result.speedup > 0\n713 \n",
      "col_offset": 8,
      "end_col_offset": 33,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 712,
      "line_range": [
        712
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "717 \n718         assert isinstance(result, BenchmarkResult)\n719         assert result.function_name == \"elementwise_arithmetic\"\n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 718,
      "line_range": [
        718
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "718         assert isinstance(result, BenchmarkResult)\n719         assert result.function_name == \"elementwise_arithmetic\"\n720         assert result.speedup > 0\n",
      "col_offset": 8,
      "end_col_offset": 63,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 719,
      "line_range": [
        719
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "719         assert result.function_name == \"elementwise_arithmetic\"\n720         assert result.speedup > 0\n721 \n",
      "col_offset": 8,
      "end_col_offset": 33,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 720,
      "line_range": [
        720
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "725 \n726         assert isinstance(result, BenchmarkResult)\n727         assert result.function_name == \"boolean_filtering\"\n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "726         assert isinstance(result, BenchmarkResult)\n727         assert result.function_name == \"boolean_filtering\"\n728         assert result.speedup > 0\n",
      "col_offset": 8,
      "end_col_offset": 58,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "727         assert result.function_name == \"boolean_filtering\"\n728         assert result.speedup > 0\n729 \n",
      "col_offset": 8,
      "end_col_offset": 33,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "733 \n734         assert isinstance(result, BenchmarkResult)\n735         assert result.function_name == \"groupby_aggregation\"\n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 734,
      "line_range": [
        734
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "734         assert isinstance(result, BenchmarkResult)\n735         assert result.function_name == \"groupby_aggregation\"\n736         assert result.speedup > 0\n",
      "col_offset": 8,
      "end_col_offset": 60,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 735,
      "line_range": [
        735
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "735         assert result.function_name == \"groupby_aggregation\"\n736         assert result.speedup > 0\n737 \n",
      "col_offset": 8,
      "end_col_offset": 33,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 736,
      "line_range": [
        736
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "741 \n742         assert isinstance(result, BenchmarkResult)\n743         assert result.function_name == \"percentage_change\"\n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 742,
      "line_range": [
        742
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "742         assert isinstance(result, BenchmarkResult)\n743         assert result.function_name == \"percentage_change\"\n744         assert result.speedup > 0\n",
      "col_offset": 8,
      "end_col_offset": 58,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 743,
      "line_range": [
        743
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "743         assert result.function_name == \"percentage_change\"\n744         assert result.speedup > 0\n745 \n",
      "col_offset": 8,
      "end_col_offset": 33,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 744,
      "line_range": [
        744
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "749 \n750         assert len(results) > 0\n751         assert all(isinstance(r, BenchmarkResult) for r in results)\n",
      "col_offset": 8,
      "end_col_offset": 31,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 750,
      "line_range": [
        750
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "750         assert len(results) > 0\n751         assert all(isinstance(r, BenchmarkResult) for r in results)\n752 \n",
      "col_offset": 8,
      "end_col_offset": 67,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 751,
      "line_range": [
        751
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "761 \n762         assert \"VECTORIZATION BENCHMARK REPORT\" in report\n763         assert \"Average speedup\" in report\n",
      "col_offset": 8,
      "end_col_offset": 57,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 762,
      "line_range": [
        762
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "762         assert \"VECTORIZATION BENCHMARK REPORT\" in report\n763         assert \"Average speedup\" in report\n764         assert \"array_sum\" in report or \"elementwise\" in report\n",
      "col_offset": 8,
      "end_col_offset": 42,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 763,
      "line_range": [
        763
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "763         assert \"Average speedup\" in report\n764         assert \"array_sum\" in report or \"elementwise\" in report\n765 \n",
      "col_offset": 8,
      "end_col_offset": 63,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 764,
      "line_range": [
        764
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "770         # Vectorized should be faster\n771         assert result.vectorized_time < result.non_vectorized_time\n772         assert result.speedup > 1.0\n",
      "col_offset": 8,
      "end_col_offset": 66,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 771,
      "line_range": [
        771
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "771         assert result.vectorized_time < result.non_vectorized_time\n772         assert result.speedup > 1.0\n773 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "785         pattern = VectorizationPatterns.elementwise_operation()\n786         assert \"Non-vectorized\" in pattern\n787         assert \"Vectorized\" in pattern\n",
      "col_offset": 8,
      "end_col_offset": 42,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 786,
      "line_range": [
        786
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "786         assert \"Non-vectorized\" in pattern\n787         assert \"Vectorized\" in pattern\n788         assert \"arr * 2\" in pattern\n",
      "col_offset": 8,
      "end_col_offset": 38,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 787,
      "line_range": [
        787
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "787         assert \"Vectorized\" in pattern\n788         assert \"arr * 2\" in pattern\n789 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 788,
      "line_range": [
        788
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "792         pattern = VectorizationPatterns.filtering()\n793         assert \"mask\" in pattern\n794         assert \"np.where\" in pattern\n",
      "col_offset": 8,
      "end_col_offset": 32,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 793,
      "line_range": [
        793
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "793         assert \"mask\" in pattern\n794         assert \"np.where\" in pattern\n795 \n",
      "col_offset": 8,
      "end_col_offset": 36,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 794,
      "line_range": [
        794
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "798         pattern = VectorizationPatterns.rolling_calculation()\n799         assert \".rolling(\" in pattern\n800         assert \".mean()\" in pattern\n",
      "col_offset": 8,
      "end_col_offset": 37,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 799,
      "line_range": [
        799
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "799         assert \".rolling(\" in pattern\n800         assert \".mean()\" in pattern\n801 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "804         pattern = VectorizationPatterns.groupby_aggregation()\n805         assert \".groupby(\" in pattern\n806         assert \".mean()\" in pattern\n",
      "col_offset": 8,
      "end_col_offset": 37,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 805,
      "line_range": [
        805
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "805         assert \".groupby(\" in pattern\n806         assert \".mean()\" in pattern\n807 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 806,
      "line_range": [
        806
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "810         pattern = VectorizationPatterns.correlation_matrix()\n811         assert \"np.corrcoef\" in pattern\n812 \n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 811,
      "line_range": [
        811
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "815         pattern = VectorizationPatterns.conditional_assignment()\n816         assert \"np.where\" in pattern\n817 \n",
      "col_offset": 8,
      "end_col_offset": 36,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 816,
      "line_range": [
        816
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "820         pattern = VectorizationPatterns.exponential_weighted()\n821         assert \".ewm(\" in pattern\n822 \n",
      "col_offset": 8,
      "end_col_offset": 33,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 821,
      "line_range": [
        821
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "825         pattern = VectorizationPatterns.percentage_change()\n826         assert \".pct_change()\" in pattern\n827 \n",
      "col_offset": 8,
      "end_col_offset": 41,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 826,
      "line_range": [
        826
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "831         # Just check that it's a valid string with relevant content\n832         assert isinstance(pattern, str)\n833         assert len(pattern) > 0\n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 832,
      "line_range": [
        832
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "832         assert isinstance(pattern, str)\n833         assert len(pattern) > 0\n834         assert \"cumsum\" in pattern.lower() or \"cumulative\" in pattern.lower()\n",
      "col_offset": 8,
      "end_col_offset": 31,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 833,
      "line_range": [
        833
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "833         assert len(pattern) > 0\n834         assert \"cumsum\" in pattern.lower() or \"cumulative\" in pattern.lower()\n835 \n",
      "col_offset": 8,
      "end_col_offset": 77,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 834,
      "line_range": [
        834
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "838         pattern = VectorizationPatterns.shift_lag()\n839         assert \".shift(\" in pattern\n840 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "843         pattern = VectorizationPatterns.rank_percentile()\n844         assert \".rank()\" in pattern\n845 \n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 844,
      "line_range": [
        844
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "848         pattern = VectorizationPatterns.distance_matrix()\n849         assert \"pdist\" in pattern or \"broadcasting\" in pattern\n850 \n",
      "col_offset": 8,
      "end_col_offset": 62,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 849,
      "line_range": [
        849
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "853         pattern = VectorizationPatterns.interpolation()\n854         assert \".ffill()\" in pattern or \".interpolate(\" in pattern\n855 \n",
      "col_offset": 8,
      "end_col_offset": 66,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "858         pattern = VectorizationPatterns.difference_operations()\n859         assert \"np.diff\" in pattern or \".diff()\" in pattern\n860 \n",
      "col_offset": 8,
      "end_col_offset": 59,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 859,
      "line_range": [
        859
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "863         pattern = VectorizationPatterns.value_counts_mode()\n864         assert \".value_counts()\" in pattern\n865 \n",
      "col_offset": 8,
      "end_col_offset": 43,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "868         pattern = VectorizationPatterns.outer_product()\n869         assert \"np.outer\" in pattern or \"broadcasting\" in pattern\n870 \n",
      "col_offset": 8,
      "end_col_offset": 65,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 869,
      "line_range": [
        869
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "873         pattern = VectorizationPatterns.datetime_operations()\n874         assert \"dayofweek\" in pattern or \"hour\" in pattern\n875 \n",
      "col_offset": 8,
      "end_col_offset": 58,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 874,
      "line_range": [
        874
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "879 \n880         assert isinstance(patterns, dict)\n881         assert len(patterns) > 0\n",
      "col_offset": 8,
      "end_col_offset": 41,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "880         assert isinstance(patterns, dict)\n881         assert len(patterns) > 0\n882         assert all(isinstance(v, str) for v in patterns.values())\n",
      "col_offset": 8,
      "end_col_offset": 32,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "881         assert len(patterns) > 0\n882         assert all(isinstance(v, str) for v in patterns.values())\n883 \n",
      "col_offset": 8,
      "end_col_offset": 65,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 882,
      "line_range": [
        882
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "887 \n888         assert isinstance(suggestion, str)\n889         assert len(suggestion) > 0\n",
      "col_offset": 8,
      "end_col_offset": 42,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "888         assert isinstance(suggestion, str)\n889         assert len(suggestion) > 0\n890 \n",
      "col_offset": 8,
      "end_col_offset": 34,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "894 \n895         assert isinstance(examples, dict)\n896         assert \"simple_returns\" in examples\n",
      "col_offset": 8,
      "end_col_offset": 41,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 895,
      "line_range": [
        895
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "895         assert isinstance(examples, dict)\n896         assert \"simple_returns\" in examples\n897         assert \"moving_average\" in examples\n",
      "col_offset": 8,
      "end_col_offset": 43,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 896,
      "line_range": [
        896
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "896         assert \"simple_returns\" in examples\n897         assert \"moving_average\" in examples\n898         assert \"bollinger_bands\" in examples\n",
      "col_offset": 8,
      "end_col_offset": 43,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 897,
      "line_range": [
        897
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "897         assert \"moving_average\" in examples\n898         assert \"bollinger_bands\" in examples\n899 \n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 898,
      "line_range": [
        898
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "904         for name, example in examples.items():\n905             assert \"Non-vectorized\" in example or \"vectorized\" in example.lower()\n906 \n",
      "col_offset": 12,
      "end_col_offset": 81,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "910 \n911         assert isinstance(comparisons, dict)\n912         assert all(isinstance(v, tuple) and len(v) == 2 for v in comparisons.values())\n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 911,
      "line_range": [
        911
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "911         assert isinstance(comparisons, dict)\n912         assert all(isinstance(v, tuple) and len(v) == 2 for v in comparisons.values())\n913 \n",
      "col_offset": 8,
      "end_col_offset": 86,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 912,
      "line_range": [
        912
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "940         # Verify report\n941         assert report.total_files_scanned >= 2\n942         assert report.total_issues_found > 0\n",
      "col_offset": 8,
      "end_col_offset": 46,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 941,
      "line_range": [
        941
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "941         assert report.total_files_scanned >= 2\n942         assert report.total_issues_found > 0\n943 \n",
      "col_offset": 8,
      "end_col_offset": 44,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "945         summary = report.get_summary()\n946         assert len(summary) > 0\n947 \n",
      "col_offset": 8,
      "end_col_offset": 31,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 946,
      "line_range": [
        946
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "957 \n958         assert len(results) > 0\n959         assert len(report) > 0\n",
      "col_offset": 8,
      "end_col_offset": 31,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 958,
      "line_range": [
        958
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "958         assert len(results) > 0\n959         assert len(report) > 0\n960         assert \"VECTORIZATION BENCHMARK REPORT\" in report\n",
      "col_offset": 8,
      "end_col_offset": 30,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 959,
      "line_range": [
        959
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "959         assert len(report) > 0\n960         assert \"VECTORIZATION BENCHMARK REPORT\" in report\n961 \n",
      "col_offset": 8,
      "end_col_offset": 57,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 960,
      "line_range": [
        960
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "972 \n973         assert len(issues) > 0\n974         assert all(len(issue.vectorized_alternative) > 0 for issue in issues)\n",
      "col_offset": 8,
      "end_col_offset": 30,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 973,
      "line_range": [
        973
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "973         assert len(issues) > 0\n974         assert all(len(issue.vectorized_alternative) > 0 for issue in issues)\n975 \n",
      "col_offset": 8,
      "end_col_offset": 77,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 974,
      "line_range": [
        974
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "987         if float(score) < 80:\n988             assert len(recommendations) > 0\n989 \n",
      "col_offset": 12,
      "end_col_offset": 43,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 988,
      "line_range": [
        988
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1007         # Vectorized operations are so fast that small variations cause large % differences\n1008         assert (\n1009             abs(result1.vectorized_time - result2.vectorized_time) / result1.vectorized_time < 2.0\n1010         )\n1011 \n",
      "col_offset": 8,
      "end_col_offset": 9,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1008,
      "line_range": [
        1008,
        1009,
        1010
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1015 \n1016         assert result.speedup > 1.0\n1017         assert result.function_name == \"array_sum\"\n",
      "col_offset": 8,
      "end_col_offset": 35,
      "filename": "./app/tests/analysis/test_vectorization.py",
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
      "code": "1016         assert result.speedup > 1.0\n1017         assert result.function_name == \"array_sum\"\n1018 \n",
      "col_offset": 8,
      "end_col_offset": 50,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1017,
      "line_range": [
        1017
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1030         issues = auditor.audit_code_snippet(\"\")\n1031         assert len(issues) == 0\n1032 \n",
      "col_offset": 8,
      "end_col_offset": 31,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1031,
      "line_range": [
        1031
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1035         issues = auditor.audit_code_snippet(\"x = 5\")\n1036         assert len(issues) == 0\n1037 \n",
      "col_offset": 8,
      "end_col_offset": 31,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1036,
      "line_range": [
        1036
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1045         issues = auditor.audit_code_snippet(code)\n1046         assert len(issues) == 0\n1047 \n",
      "col_offset": 8,
      "end_col_offset": 31,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1046,
      "line_range": [
        1046
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1057         # May detect 0, 1, or 2 issues depending on the AST structure\n1058         assert isinstance(issues, list)\n1059 \n",
      "col_offset": 8,
      "end_col_offset": 39,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1058,
      "line_range": [
        1058
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1066         issues = auditor.audit_code_snippet(code)\n1067         assert len(issues) > 0\n1068 \n",
      "col_offset": 8,
      "end_col_offset": 30,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1067,
      "line_range": [
        1067
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1088         # as they're not always for numerical arrays\n1089         assert not any(\"list_comp\" in issue.issue_type for issue in issues)\n1090 \n",
      "col_offset": 8,
      "end_col_offset": 75,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1089,
      "line_range": [
        1089
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    },
    {
      "code": "1099         # String operations are different from numerical\n1100         assert len(issues) == 0 or all(\n1101             \"numerical\" in issue.description.lower() or \"calculation\" in issue.description.lower()\n1102             for issue in issues\n1103         )\n",
      "col_offset": 8,
      "end_col_offset": 9,
      "filename": "./app/tests/analysis/test_vectorization.py",
      "issue_confidence": "HIGH",
      "issue_cwe": {
        "id": 703,
        "link": "https://cwe.mitre.org/data/definitions/703.html"
      },
      "issue_severity": "LOW",
      "issue_text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.",
      "line_number": 1100,
      "line_range": [
        1100,
        1101,
        1102,
        1103
      ],
      "more_info": "https://bandit.readthedocs.io/en/1.9.3/plugins/b101_assert_used.html",
      "test_id": "B101",
      "test_name": "assert_used"
    }
  ]
}```

## 4. Complexity (radon)
app/tests/analysis/test_vectorization.py
    M 680:4 TestVectorizationBenchmark.test_benchmark_sum - B (6)
    M 137:4 TestVectorizationIssue.test_create_valid_issue - A (5)
    M 206:4 TestVectorizationIssue.test_get_display_summary - A (5)
    M 291:4 TestVectorizationReport.test_get_summary - A (5)
    C 671:0 TestVectorizationBenchmark - A (5)
    M 891:4 TestVectorizationPatterns.test_get_trading_specific_examples - A (5)
    C 134:0 TestVectorizationIssue - A (4)
    C 230:0 TestVectorizationReport - A (4)
    M 233:4 TestVectorizationReport.test_create_report - A (4)
    M 376:4 TestBenchmarkResult.test_get_summary - A (4)
    M 419:4 TestBenchmarkResult.test_to_dict - A (4)
    M 451:4 TestVectorizationAuditor.test_audit_file_with_for_loops - A (4)
    M 596:4 TestVectorizationAuditor.test_audit_directory - A (4)
    M 690:4 TestVectorizationBenchmark.test_benchmark_ewm_calculate - A (4)
    M 698:4 TestVectorizationBenchmark.test_benchmark_rolling_calculation - A (4)
    M 706:4 TestVectorizationBenchmark.test_benchmark_correlation - A (4)
    M 714:4 TestVectorizationBenchmark.test_benchmark_elementwise_operation - A (4)
    M 722:4 TestVectorizationBenchmark.test_benchmark_filtering - A (4)
    M 730:4 TestVectorizationBenchmark.test_benchmark_groupby - A (4)
    M 738:4 TestVectorizationBenchmark.test_benchmark_percentage_change - A (4)
    M 753:4 TestVectorizationBenchmark.test_generate_report - A (4)
    M 783:4 TestVectorizationPatterns.test_elementwise_operation_pattern - A (4)
    M 828:4 TestVectorizationPatterns.test_cumulative_operations_pattern - A (4)
    M 876:4 TestVectorizationPatterns.test_get_all_patterns - A (4)
    C 920:0 TestIntegration - A (4)
    M 923:4 TestIntegration.test_full_audit_workflow - A (4)
    M 948:4 TestIntegration.test_full_benchmark_workflow - A (4)
    C 996:0 TestPerformance - A (4)
    M 180:4 TestVectorizationIssue.test_get_severity_weight - A (3)
    M 311:4 TestVectorizationReport.test_is_compliant - A (3)
    C 332:0 TestBenchmarkResult - A (3)
    M 335:4 TestBenchmarkResult.test_create_valid_result - A (3)
    M 393:4 TestBenchmarkResult.test_get_performance_grade - A (3)
    C 442:0 TestVectorizationAuditor - A (3)
    M 445:4 TestVectorizationAuditor.test_auditor_initialization - A (3)
    M 463:4 TestVectorizationAuditor.test_audit_code_snippet_with_for_loops - A (3)
    M 474:4 TestVectorizationAuditor.test_audit_code_snippet_with_apply - A (3)
    M 485:4 TestVectorizationAuditor.test_audit_code_snippet_with_iterrows - A (3)
    M 559:4 TestVectorizationAuditor.test_calculate_score_bottoms_out_at_zero - A (3)
    M 674:4 TestVectorizationBenchmark.test_benchmark_initialization - A (3)
    M 746:4 TestVectorizationBenchmark.test_run_all_benchmarks - A (3)
    M 766:4 TestVectorizationBenchmark.test_benchmark_results_show_speedup - A (3)
    C 780:0 TestVectorizationPatterns - A (3)
    M 790:4 TestVectorizationPatterns.test_filtering_pattern - A (3)
    M 796:4 TestVectorizationPatterns.test_rolling_calculation_pattern - A (3)
    M 802:4 TestVectorizationPatterns.test_groupby_aggregation_pattern - A (3)
    M 884:4 TestVectorizationPatterns.test_get_suggestion_for_issue - A (3)
    M 900:4 TestVectorizationPatterns.test_trading_examples_contain_vectorized_alternatives - A (3)
    M 907:4 TestVectorizationPatterns.test_get_performance_comparison - A (3)
    M 962:4 TestIntegration.test_patterns_and_auditor_integration - A (3)
    M 976:4 TestIntegration.test_score_and_recommendations_correlation - A (3)
    M 1012:4 TestPerformance.test_large_array_benchmark - A (3)
    C 1025:0 TestEdgeCases - A (3)
    C 1075:0 TestRegression - A (3)
    M 249:4 TestVectorizationReport.test_get_grade_a - A (2)
    M 263:4 TestVectorizationReport.test_get_grade_b - A (2)
    M 277:4 TestVectorizationReport.test_get_grade_f - A (2)
    M 496:4 TestVectorizationAuditor.test_audit_vectorized_code - A (2)
    M 527:4 TestVectorizationAuditor.test_calculate_score_no_issues - A (2)
    M 532:4 TestVectorizationAuditor.test_calculate_score_with_issues - A (2)
    M 577:4 TestVectorizationAuditor.test_generate_recommendations - A (2)
    M 613:4 TestVectorizationAuditor.test_check_for_loops_detection - A (2)
    M 622:4 TestVectorizationAuditor.test_check_range_len_detection - A (2)
    M 631:4 TestVectorizationAuditor.test_check_enumerate_detection - A (2)
    M 640:4 TestVectorizationAuditor.test_check_apply_detection - A (2)
    M 648:4 TestVectorizationAuditor.test_check_iterrows_detection - A (2)
    M 657:4 TestVectorizationAuditor.test_check_list_comp_detection - A (2)
    M 808:4 TestVectorizationPatterns.test_correlation_matrix_pattern - A (2)
    M 813:4 TestVectorizationPatterns.test_conditional_assignment_pattern - A (2)
    M 818:4 TestVectorizationPatterns.test_exponential_weighted_pattern - A (2)
    M 823:4 TestVectorizationPatterns.test_percentage_change_pattern - A (2)
    M 836:4 TestVectorizationPatterns.test_shift_lag_pattern - A (2)
    M 841:4 TestVectorizationPatterns.test_rank_percentile_pattern - A (2)
    M 846:4 TestVectorizationPatterns.test_distance_matrix_pattern - A (2)
    M 851:4 TestVectorizationPatterns.test_interpolation_pattern - A (2)
    M 856:4 TestVectorizationPatterns.test_difference_operations_pattern - A (2)
    M 861:4 TestVectorizationPatterns.test_value_counts_mode_pattern - A (2)
    M 866:4 TestVectorizationPatterns.test_outer_product_pattern - A (2)
    M 871:4 TestVectorizationPatterns.test_datetime_operations_pattern - A (2)
    M 999:4 TestPerformance.test_benchmark_reproducibility - A (2)
    M 1028:4 TestEdgeCases.test_empty_code_snippet - A (2)
    M 1033:4 TestEdgeCases.test_single_line_code - A (2)
    M 1038:4 TestEdgeCases.test_code_with_only_imports - A (2)
    M 1048:4 TestEdgeCases.test_nested_loops_detection - A (2)
    M 1060:4 TestEdgeCases.test_complex_expressions_in_loop - A (2)
    M 1078:4 TestRegression.test_no_false_positives_for_dict_comprehension - A (2)
    M 1091:4 TestRegression.test_string_operations_not_flagged - A (2)
    F 40:0 sample_code_with_for_loops - A (1)
    F 60:0 sample_code_with_apply - A (1)
    F 73:0 sample_code_with_iterrows - A (1)
    F 87:0 sample_vectorized_code - A (1)
    F 107:0 temp_code_file - A (1)
    F 118:0 auditor - A (1)
    F 124:0 benchmark - A (1)
    M 154:4 TestVectorizationIssue.test_invalid_severity_raises_error - A (1)
    M 167:4 TestVectorizationIssue.test_invalid_issue_type_raises_error - A (1)
    M 350:4 TestBenchmarkResult.test_invalid_vectorized_time_raises_error - A (1)
    M 363:4 TestBenchmarkResult.test_invalid_non_vectorized_time_raises_error - A (1)
    M 507:4 TestVectorizationAuditor.test_audit_nonexistent_file_raises_error - A (1)
    M 515:4 TestVectorizationAuditor.test_audit_invalid_syntax_raises_error - A (1)

100 blocks (classes, functions, methods) analyzed.
Average complexity: A (2.76)

## 5. Maintainability Index
app/tests/analysis/test_vectorization.py - C (1.91)

## 6. Syntax Check
**Status:** ❌ FAILED

## 7. Import Validation
**Status:** ✅ PASSED

---
## Summary
**Validation completed at:** 2026-02-07T07:10:58Z

