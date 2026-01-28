# Enterprise Python Checklist

Complete checklist for enterprise-grade Python production code.

---

## ✅ FORMATTING & STYLE

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Black | `black --check .` | 100% formatted |
| Isort | `isort --check-only .` | 100% organized |
| Autoflake | `autoflake --check .` | No unused imports |
| Flake8 | `flake8 . --max-complexity=10` | 0 errors |
| Ruff | `ruff check .` | 0 errors |

### Rules
- [ ] Line length ≤ 100 characters
- [ ] Double quotes for strings
- [ ] Trailing commas in multi-line collections
- [ ] Imports: future → stdlib → third-party → local
- [ ] No unused imports/variables
- [ ] No mutable defaults (`def func(items: list | None = None)`)
- [ ] Use `is None` instead of `== None`
- [ ] Use f-strings for string interpolation
- [ ] Use `pathlib.Path` instead of `os.path`
- [ ] Context managers for all resources

---

## ✅ TYPE HINTS

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Mypy | `mypy --strict .` | 0 errors |

### Rules
- [ ] 100% type hint coverage (all functions)
- [ ] Use modern syntax: `list[T]`, `dict[K, V]`, `X | None`
- [ ] No `Any` without explicit justification
- [ ] No `# type: ignore` without comment
- [ ] Use `Protocol` for duck typing
- [ ] Use `TypeVar` for generics
- [ ] Use `TypedDict` for structured data
- [ ] Use `Literal` for constants

---

## ✅ DOCUMENTATION

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Pydocstyle | `pydocstyle .` | 100% compliant |
| Interrogate | `interrogate .` | 100% coverage |

### Rules
- [ ] All modules have docstrings
- [ ] All classes have docstrings
- [ ] All public functions have docstrings
- [ ] Docstrings include: Args, Returns, Raises, Examples
- [ ] Use Google style docstrings
- [ ] Document complex logic inline

---

## ✅ SECURITY

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Bandit | `bandit -r . -ll` | 0 issues |
| Safety | `safety check` | 0 vulnerabilities |
| Pip-audit | `pip-audit` | 0 vulnerabilities |

### Rules
- [ ] No hardcoded secrets
- [ ] No SQL injection (parameterized queries)
- [ ] No shell injection (no `shell=True`)
- [ ] Strong crypto (SHA256+, no MD5/SHA1)
- [ ] No `pickle` with untrusted data
- [ ] No `assert` for validation in production
- [ ] Dependencies without CVEs
- [ ] Input validation at system boundaries

---

## ✅ CODE QUALITY

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Radon | `radon cc . -a --min B` | Complexity < 10 |
| Vulture | `vulture . --min-confidence 80` | 0 dead code |
| JSCPD | `jscpd . .` | Duplication < 5% |
| Pylint | `pylint . --fail-under=8.0` | Score ≥ 8.0 |

### Rules
- [ ] Cyclomatic complexity < 10
- [ ] No dead code
- [ ] Code duplication < 5%
- [ ] Functions < 50 lines (ideally < 20)
- [ ] Classes < 300 lines
- [ ] Maximum 7 parameters per function
- [ ] DRY - no code duplication

---

## ✅ TESTING

| Tool | Command | Minimum Score |
|------|---------|---------------|
| Pytest | `pytest .` | 100% pass |
| Coverage | `coverage report --fail-under=80` | > 80% |

### Rules
- [ ] AAA pattern (Arrange-Act-Assert)
- [ ] Descriptive names: `test_<what>_<condition>_<expected>`
- [ ] Tests are independent
- [ ] External dependencies mocked
- [ ] Success and failure paths tested
- [ ] Edge cases covered
- [ ] Exceptions tested with `pytest.raises`
- [ ] Parametrized tests for multiple cases
- [ ] Fixtures for common setup
- [ ] Coverage > 80%
- [ ] Branch coverage tested
- [ ] Tests marked (unit, integration, slow)
- [ ] No flaky tests
- [ ] Tests run quickly

---

## ✅ ARCHITECTURE

### SOLID Principles
- [ ] **S**ingle Responsibility: One reason to change
- [ ] **O**pen/Closed: Open for extension, closed for modification
- [ ] **L**iskov Substitution: Subtypes substitutable
- [ ] **I**nterface Segregation: Small, focused interfaces
- [ ] **D**ependency Inversion: Depend on abstractions

### Layered Architecture
```
presentation → application → domain ← infrastructure
```
- [ ] Dependencies point inward (toward domain)
- [ ] Domain has no framework dependencies
- [ ] Each layer has single responsibility
- [ ] Business logic in domain/application
- [ ] External concerns in infrastructure
- [ ] Interface details in presentation

### Design Patterns
- [ ] Repository pattern for data access
- [ ] Factory for object creation
- [ ] Builder for complex objects
- [ ] Strategy for interchangeable algorithms
- [ ] Observer for notifications
- [ ] Dependency injection for flexibility

---

## ✅ CLEAN CODE

- [ ] Descriptive, meaningful names
- [ ] Functions small (< 20 lines)
- [ ] DRY - no duplication
- [ ] YAGNI - implement what's needed
- [ ] KISS - keep it simple
- [ ] Early returns to avoid nesting
- [ ] Structured logging (no print statements)
- [ ] Explicit error handling
- [ ] Composition over inheritance
- [ ] Value objects immutable

---

## ✅ ASYNC/AWAIT

- [ ] Use `async def` for async functions
- [ ] `await` all async calls
- [ ] Use `async with` for async context managers
- [ ] Use `async for` for async iterators
- [ ] No blocking calls in async functions
- [ ] Use `asyncio.sleep()` instead of `time.sleep()`
- [ ] Run blocking I/O in executor
- [ ] Set timeouts for external calls
- [ ] Handle `asyncio.TimeoutError`
- [ ] Cancel tasks properly on cleanup
- [ ] Test async code with `@pytest.mark.asyncio`

---

## ✅ CONFIGURATION

- [ ] Use Pydantic Settings for type safety
- [ ] Never hardcode secrets in code
- [ ] Use environment variables for deployment values
- [ ] Validate all configuration values
- [ ] Provide sensible defaults
- [ ] Document all fields
- [ ] Environment-specific configuration files
- [ ] Encrypt secrets at rest
- [ ] Use environment variables for secrets
- [ ] Implement feature flags
- [ ] Support hot-reload when needed
- [ ] Use environment prefix to avoid conflicts
- [ ] Set `extra="forbid"` to catch typos

---

## ✅ LOGGING & OBSERVABILITY

- [ ] Use structured logging (JSON format)
- [ ] Include context in all logs
- [ ] Use appropriate log levels
- [ ] Log at entry/exit points
- [ ] Log errors with stack traces
- [ ] Include correlation IDs
- [ ] Add timing information
- [ ] Don't log sensitive data (passwords, tokens, PII)
- [ ] Use log aggregation (ELK, CloudWatch)
- [ ] Set up retention policies
- [ ] Monitor log volume and errors
- [ ] Use metrics for quantitative monitoring
- [ ] Use tracing for request flow
- [ ] Implement health checks
- [ ] Set up alerts on error patterns

---

## ✅ PERFORMANCE

- [ ] List comprehensions over loops
- [ ] Generators for large data
- [ ] Sets for O(1) lookups
- [ ] Async/await for I/O concurrency
- [ ] Caching where appropriate
- [ ] Lazy loading when possible
- [ ] Profile before optimizing
- [ ] Measure performance impact
- [ ] Consider algorithmic complexity
- [ ] Use built-in functions (often faster)

---

## CI/CD Pipeline Example

```yaml
# .github/workflows/qa.yml
name: Python QA Pipeline

on: [push, pull_request]

jobs:
  qa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install black isort autoflake flake8 ruff mypy pylint
          pip install bandit radon vulture pydocstyle interrogate
          pip install safety pip-audit pytest coverage
          pip install bandit safety semgrep jscpd

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

---

## Pre-commit Configuration

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

---

## Quick Reference Commands

```bash
# Format code
black .
isort .

# Check linting
flake8 . --max-complexity=10
ruff check .
pylint . --fail-under=8.0

# Type checking
mypy --strict .

# Documentation
pydocstyle .
interrogate . --fail-under=100

# Security
bandit -r . -ll
safety check
pip-audit

# Quality
radon cc . -a --min B
vulture . --min-confidence 80

# Testing
pytest .
coverage run -m pytest
coverage report --fail-under=80
```

---

## Summary: Enterprise Python Standards

Your code must:
1. ✅ Pass all 20+ QA tools without errors
2. ✅ Follow SOLID principles
3. ✅ Use Clean Architecture
4. ✅ Have 100% type hints
5. ✅ Have 100% docstrings
6. ✅ Be 100% testable with >80% coverage
7. ✅ Use appropriate Design Patterns
8. ✅ Have 0 security vulnerabilities
9. ✅ Have cyclomatic complexity < 10
10. ✅ Follow AAA pattern for tests
11. ✅ Use fixtures for test setup
12. ✅ Include parametrized tests
13. ✅ Cover success, error, and edge cases
14. ✅ Include performance tests
15. ✅ Use structured logging
16. ✅ Have environment-based configuration
17. ✅ Handle errors explicitly
18. ✅ Use async/await properly
19. ✅ Be documented and maintainable
20. ✅ Be production-ready

**RESUMEN EJECUTIVO**: Código profesional enterprise-grade que pasa TODAS las herramientas de QA, sigue SOLID y Clean Architecture, tiene 100% type hints y docstrings, 100% testeable con cobertura >80%, usa Design Patterns apropiados, tiene 0 vulnerabilidades de seguridad, complejidad ciclomática < 10, y tests que siguen AAA pattern con fixtures, parametrized tests, mocks, y cobertura de casos exitosos, de error, edge cases y performance.
