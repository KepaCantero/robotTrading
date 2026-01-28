# Python QA Checklist

Complete checklist for validating Python code before committing to production.

## Quick Reference

- [ ] All code formatted with Black (100 char line length)
- [ ] Imports organized with Isort
- [ ] No unused imports (Autoflake/Ruff)
- [ ] Passes Flake8 (max complexity 10)
- [ ] Passes Ruff linting
- [ ] Passes Pylint (8.0+ score)
- [ ] 100% type hint coverage (Mypy strict mode)
- [ ] All functions/classes documented (Pydocstyle)
- [ ] 100% docstring coverage (Interrogate)
- [ ] No security issues (Bandit)
- [ ] No dependency vulnerabilities (Safety)
- [ ] No code duplication (JSCPD < 5%)
- [ ] Cyclomatic complexity < 10 (Radon)
- [ ] No dead code (Vulture)
- [ ] Test coverage > 80% (Coverage.py)
- [ ] All tests pass (Pytest)
- [ ] No import cycles (Import Linter)
- [ ] Performance checked (Perflint)
- [ ] Semantic issues checked (Semgrep)
- [ ] Dependencies audited (Pip-audit)

## 1. Formatting & Style

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Black | `black --check .` | 100% formatted |
| Isort | `isort --check-only .` | 100% organized |
| Autoflake | `autoflake --check .` | No unused imports |
| Flake8 | `flake8 .` | 0 errors |
| Ruff | `ruff check .` | 0 errors |

## 2. Type Checking

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Mypy | `mypy --strict .` | 0 errors |

**Requirements:**
- All functions must have type hints for parameters and return types
- Use modern syntax: `list[T]`, `dict[K, V]`, `X | None`
- No `Any` types without explicit `# type: ignore` with justification

## 3. Documentation

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Pydocstyle | `pydocstyle .` | 100% compliant |
| Interrogate | `interrogate .` | 100% coverage |

**Requirements:**
- All modules need docstrings
- All classes need docstrings
- All functions need docstrings with Args/Returns/Raises
- Follow Google style docstrings

## 4. Security & Safety

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Bandit | `bandit -r .` | 0 issues |
| Safety | `safety check` | 0 vulnerabilities |
| Pip-audit | `pip-audit` | 0 vulnerabilities |

## 5. Code Quality

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Radon | `radon cc . -a` | Complexity < 10 |
| Vulture | `vulture .` | 0 dead code |
| JSCPD | `jscpd .` | Duplication < 5% |
| Pylint | `pylint .` | Score 8.0+ |

## 6. Testing

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Pytest | `pytest .` | 100% pass |
| Coverage.py | `coverage run -m pytest && coverage report` | > 80% |

**Requirements:**
- Follow AAA pattern (Arrange-Act-Assert)
- Use parametrized tests for multiple cases
- Mock external dependencies
- Test both success and failure paths

## 7. Additional Checks

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Import Linter | `import-linter .` | No cycles |
| Perflint | `perflint .` | No issues |
| Semgrep | `semgrep .` | 0 findings |

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Python QA

on: [push, pull_request]

jobs:
  qa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install black isort autoflake flake8 ruff mypy pylint bandit radon vulture pydocstyle interrogate safety pip-audit pytest coverage semgrep

      # Format checks
      - run: black --check .
      - run: isort --check-only .
      - run: autoflake --check .

      # Linting
      - run: flake8 . --max-complexity=10
      - run: ruff check .
      - run: pylint . --fail-under=8.0

      # Type checking
      - run: mypy --strict .

      # Documentation
      - run: pydocstyle .
      - run: interrogate . --fail-under=100

      # Security
      - run: bandit -r . -ll
      - run: safety check
      - run: pip-audit

      # Quality
      - run: radon cc . -a --min B
      - run: vulture . --min-confidence 80
      - run: jscpd . .

      # Testing
      - run: coverage run -m pytest
      - run: coverage report --fail-under=80
```

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        args: [--line-length=100]

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: [--profile, black]

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-complexity=10]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.15
    hooks:
      - id: ruff

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        args: [--strict]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: [-ll]
```
