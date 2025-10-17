# AlgoTrading Testing System

A comprehensive testing system with specialized agents that execute tests, diagnose failures, and apply automated fixes.

## 🎯 Purpose

When you write **"test [scope]"**, this system triggers a coordinated group of agents responsible for executing all automated tests, validating integration consistency, and debugging any failed test cases.

If any test fails, a dedicated **Fixer Agent** is automatically invoked to analyze, patch, and re-run tests until the system returns to a stable state.

## 🧩 Agent Roles

### 🧑‍🔬 Lead Tester

- Reads `.memory` and project context (task tree, modules, dependencies)
- Determines test scope (unit, integration, end-to-end, performance)
- Coordinates all specialized agents and ensures consistent reporting

### ⚙️ Test Executor

- Runs all tests via the project's configured test runner (e.g., `pytest`, `unittest`, `jest`)
- Captures detailed output, logs, and stack traces
- Detects test flakiness and runtime environment issues

### 🧠 Failure Diagnostician

- Parses failed test logs and traces to identify **root causes** (logic bug, dependency issue, misconfigured mock, outdated test, etc.)
- Categorizes failure by **type** (Regression / Environment / Integration / Data / Logic)
- Suggests minimal viable fix strategy

### 🔧 Auto-Fixer Agent

- Reads `.memory` and recent diffs
- Implements code patches for broken logic or incorrect assumptions
- Can modify test cases or production code only when failure cause is unambiguous
- Commits fixes in a new branch `fix/test-failure-[id]` and re-runs failing tests
- Updates `.memory` if architecture, interfaces, or behavior expectations change

### 🧩 Integration Verifier

- Ensures data flow and module interactions remain consistent after fixes
- Validates that no regressions were introduced
- Runs partial regression suite for modified components

### 🔒 QA Quality Guardian

- Checks test coverage metrics and enforces thresholds (e.g., 90%+)
- Verifies that test design matches conventions (AAA pattern, mock usage, naming)
- Suggests missing test cases or redundant ones

### 🧰 Environment & Dependency Auditor

- Confirms the correct environment (Python, Node, Docker, AWS, etc.) is active
- Verifies versions, virtualenv, Docker Compose services, or `.env` files
- Detects dependency drift (e.g., `pip freeze` mismatch) or outdated images

## 🚀 Quick Start

### Basic Usage

```python
from .orchestrator import TestingOrchestrator

# Initialize orchestrator
orchestrator = TestingOrchestrator(
    project_path="/path/to/project",
    memory_bank_path=".memory"
)

# Run all tests
report = await orchestrator.test_all()

# Run specific test scope
report = await orchestrator.test_unit()
report = await orchestrator.test_integration()
report = await orchestrator.test_e2e()

# Run tests with automatic fixing
report = await orchestrator.test_with_fixes("unit")
```

### Convenience Functions

```python
from .orchestrator import test_all, test_unit, test_integration, test_with_fixes

# Quick test execution
report = await test_all("/path/to/project")
report = await test_unit("/path/to/project")
report = await test_integration("/path/to/project")

# Test with automatic fixing
report = await test_with_fixes("/path/to/project", "unit")
```

## 📊 Output Format

The system generates comprehensive test reports with the following structure:

### Executive Summary

- Overall status (✅ Stable Build / ⚠️ Partial Coverage / ❌ Unstable Build)
- Key metrics (total tests, success rate, passed/failed/errors)
- Key insights and recommendations

### Test Results Table

| Phase            | Agent            | Test Name                            | Status    | Duration | Output                                                                        |
| ---------------- | ---------------- | ------------------------------------ | --------- | -------- | ----------------------------------------------------------------------------- |
| test_execution   | ⚙️ Test Executor | test_calculate_risk_ratio            | ❌ Failed | 0.5s     | TypeError: unsupported operand type(s) for /: 'str' and 'int'                 |
| failure_handling | 🧠 Diagnostician | Diagnosis: test_calculate_risk_ratio | ✅ Passed | 0.1s     | Error Type: type_error, Root Cause: String value passed to division operation |
| failure_handling | 🔧 Auto-Fixer    | Fix: test_calculate_risk_ratio       | ✅ Passed | 0.2s     | Applied fix: Convert string to float before division                          |

### Test Metrics

- **Total Duration**: 15.2s
- **Average Duration**: 0.3s
- **Success Rate**: 85.5%
- **Coverage**: 92% (+1%)

### Recommendations

- **🔴 High Priority**: Address 3 failed tests
- **🟡 Medium Priority**: Improve test coverage (current: 85%)
- **🟢 Low Priority**: Add more integration tests

## 🧾 Workflow

1. **Initialization**

   - The system loads `.memory`, determines the current module and task context (e.g., `T018: ResourceParametersSetter`)
   - Lead Tester defines test scope and triggers the `Test Executor`

2. **Execution**

   - Tests are run in parallel or sequentially, depending on environment
   - Logs and traces are collected for analysis

3. **Analysis**

   - If all tests pass: mark ✅ **Stable Build**
   - If failures occur:
     - `Failure Diagnostician` analyzes the errors
     - `Auto-Fixer Agent` applies patches
     - Re-run affected tests until stable

4. **Verification**

   - `Integration Verifier` ensures no regressions
   - `QA Quality Guardian` checks coverage and consistency

5. **Memory Update**

   - Update `.memory` with:
     - New dependencies or changes to test infra
     - Fix summaries and rationales
     - Confidence scores for test reliability

6. **Delivery**

   - Output structured **Test Report**, including:
     - ✅ Passed tests count
     - ❌ Failed tests and root causes
     - 🔧 Fix actions
     - 🧠 Lessons learned (to improve coverage or architecture)

## 🎯 Test Scopes

- **`test all`** - Run all tests (unit, integration, e2e)
- **`test unit`** - Run unit tests only
- **`test integration`** - Run integration tests only
- **`test e2e`** - Run end-to-end tests only
- **`test module:executor`** - Run tests for specific module
- **`test task:T014`** - Run tests for specific task

## 🔧 Integration

### Cursor Integration

Add as a **`test` system command**:

```bash
# Test all
test all

# Test specific scope
test unit
test integration
test e2e

# Test with fixes
test unit --fix
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Automated Testing
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Tests
        run: python -m .memory.testing.demo
```

## 📁 Project Structure

```
.memory/testing/
├── agents/
│   ├── __init__.py
│   ├── base_test_agent.py        # Base class for all agents
│   ├── lead_tester.py            # 🧑‍🔬 Lead Tester
│   ├── test_executor.py          # ⚙️ Test Executor
│   ├── failure_diagnostician.py  # 🧠 Failure Diagnostician
│   ├── auto_fixer_agent.py       # 🔧 Auto-Fixer Agent
│   ├── integration_verifier.py   # 🧩 Integration Verifier
│   ├── qa_quality_guardian.py    # 🔒 QA Quality Guardian
│   └── environment_auditor.py    # 🧰 Environment Auditor
├── templates/
│   └── test_report.md            # Report template
├── orchestrator.py               # Main orchestrator
├── report_generator.py           # Report generation
├── demo.py                       # Demo script
└── README.md                     # This file
```

## 🧪 Demo

Run the demo to see the system in action:

```bash
cd .memory/testing
python demo.py
```

Choose between:

1. **Full system demo** - Runs actual tests and shows all agents
2. **Specific agent demo** - Shows individual agent capabilities
3. **Failure diagnosis demo** - Demonstrates failure analysis

## 🔍 Example Command Flow

```
test module:executor

🧑‍🔬 Lead Tester: Context loaded. Running 45 tests.
⚙️ Test Executor: 3 failed → passing logs to Diagnostician.
🧠 Diagnostician: Logic issue in trade validation threshold.
🔧 Auto-Fixer: Applied patch and re-ran → all tests passed.
✅ Integration Verifier: No regressions found.
📊 Final Report: Stable Build (Coverage 93%)
```

## 🎯 System Status

The system provides clear status indicators:

- **✅ Stable Build** - All tests passing, system ready
- **🔄 Fixing in Progress** - Auto-fixer is applying patches
- **❌ Unstable Build** - Critical issues must be addressed

## 🔧 Customization

### Adding New Agents

1. Inherit from `BaseTestAgent`
2. Implement the `execute()` method
3. Add to the orchestrator's agent list
4. Update the `__init__.py` imports

### Custom Test Runners

1. Add new runner configuration to `TestExecutor.test_runners`
2. Implement parser method for the runner
3. Update test command building logic

## 📈 Metrics and Analytics

The system tracks:

- **Test Execution Time**: Duration of test runs
- **Success Rate**: Percentage of passing tests
- **Coverage Metrics**: Code coverage percentage
- **Fix Success Rate**: Percentage of successful auto-fixes
- **Environment Health**: Environment validation status

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add your specialized agent or improvement
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-14  
**Status**: Production Ready
