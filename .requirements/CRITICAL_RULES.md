# CRITICAL RULES - AlgoTrading Codebase

**Last Updated:** 2026-02-01
**Total Rules:** 81 files in /rules (26 Python QA + 55 Trading)

---

## Purpose

These are the **CRITICAL RULES** that EVERY production file MUST follow. Each file's `.requirements.md` should reference these universal rules plus any file-specific rules.

**Overengineering Criteria:** A rule is only marked as a GAP if fixing it:
- Prevents real bugs (timeouts, race conditions, data loss)
- Prevents production incidents (trading errors, wrong positions)
- Reduces duplication significantly (>30% code reduction)
- Is a production standard (logging, monitoring, error handling)
- Impacts trading system safety (risk limits, position validation)

**SKIP (Overengineering):** Marginal style improvements, subjective naming, micro-optimizations without measured bottleneck.

---

## 1. FORMATTING & STYLE (01-formatting-style.md)

| Rule | Requirement | Check Command |
|------|-------------|---------------|
| Line length ≤ 100 | Black enforces 100 char limit | `black --check .` |
| Import organization | stdlib → third-party → local | `isort --check-only .` |
| No unused imports | Remove all unused imports | `autoflake --check .` |
| Double quotes | Prefer double quotes for strings | `black --check .` |
| Trailing commas | Multi-line collections need trailing comma | `black --check .` |
| F-strings | Use f-strings not .format() or % | Manual review |
| No mutable defaults | Use `None` instead of `[]` or `{}` | `flake8 .` |

**CRITICAL:**
- ✅ **PASS:** All code formatted with Black
- ✅ **PASS:** Imports organized with Isort
- ❌ **FAIL:** Lines > 100 characters
- ❌ **FAIL:** Unused imports present

---

## 2. TYPE HINTS (02-type-hints.md)

| Rule | Requirement | Check Command |
|------|-------------|---------------|
| 100% type coverage | All functions have type hints | `mypy --strict .` |
| Modern syntax | Use `list[T]`, `dict[K,V]`, `X \| None` | `mypy --strict .` |
| No Any without justification | Use specific types or Protocol | `mypy --strict .` |
| Type ignore with comment | All `# type: ignore` have explanation | Manual review |

**CRITICAL:**
- ✅ **PASS:** All public functions have type hints
- ✅ **PASS:** Return types specified
- ❌ **FAIL:** Missing type hints on public API
- ❌ **FAIL:** Using `Any` without justification

---

## 3. SOLID PRINCIPLES (03-solid-principles.md)

| Rule | Requirement | Impact |
|------|-------------|--------|
| **S**RP | Single responsibility - one reason to change | Prevents coupling |
| **O**CP | Open for extension, closed for modification | Enables plugin architecture |
| **L**SP | Subtypes substitutable for base types | Prevents inheritance bugs |
| **I**SP | Small, focused interfaces | Prevents fat interfaces |
| **D**IP | Depend on abstractions (Protocol/ABC) | Enables testing |

**CRITICAL:**
- ✅ **PASS:** Class has single responsibility
- ✅ **PASS:** Uses dependency injection
- ❌ **FAIL:** Class doing multiple things (validation + DB + email)
- ❌ **FAIL:** Direct instantiation of dependencies (hard to test)

---

## 4. ARCHITECTURE (05-architecture.md)

| Rule | Requirement | Impact |
|------|-------------|--------|
| Layered architecture | presentation → application → domain ← infrastructure | Testability |
| Dependencies inward | Domain knows nothing about other layers | Decoupling |
| No framework in domain | Domain has no FastAPI/SQLAlchemy imports | Portability |
| Small functions | Functions < 20 lines (ideally) | Maintainability |
| Early returns | Use guard clauses to avoid nesting | Readability |

**CRITICAL:**
- ✅ **PASS:** Correct layer positioning
- ✅ **PASS:** Dependencies point inward
- ❌ **FAIL:** Domain layer importing infrastructure
- ❌ **FAIL:** Deep nesting (>3 levels)

---

## 5. TESTING (06-testing.md)

| Rule | Requirement | Check Command |
|------|-------------|---------------|
| AAA pattern | Arrange-Act-Assert structure | Manual review |
| Descriptive names | `test_<what>_<condition>_<expected>` | Manual review |
| Parametrized tests | Use `@pytest.mark.parametrize` for cases | `pytest .` |
| Mock external deps | Use `unittest.mock` for external services | `pytest .` |
| Coverage > 80% | Minimum test coverage | `coverage report` |

**CRITICAL:**
- ✅ **PASS:** Tests follow AAA pattern
- ✅ **PASS:** External dependencies mocked
- ❌ **FAIL:** Coverage below 80%
- ❌ **FAIL:** No tests for error paths

---

## 6. SECURITY (28-security-and-secrets.md)

| Rule | Requirement | Impact |
|------|-------------|--------|
| No hardcoded secrets | Use environment variables | CRITICAL |
| Environment validation | Pydantic Settings for config | CRITICAL |
| TLS/SSL required | HTTPS only for external APIs | CRITICAL |
| HMAC signing | Sign all API requests with HMAC | CRITICAL |
| Audit logging | Log all trading operations | CRITICAL |
| Rate limiting | Implement rate limits for APIs | HIGH |
| Input validation | Validate at system boundaries | HIGH |

**CRITICAL:**
- ✅ **PASS:** Secrets in environment variables
- ✅ **PASS:** TLS/SSL for all network calls
- ❌ **FAIL:** Hardcoded API keys/secrets
- ❌ **FAIL:** No audit logging for trades

---

## 7. LOGGING & OBSERVABILITY (09-logging-observability.md)

| Rule | Requirement | Impact |
|------|-------------|--------|
| Structured logging | Use JSON format (structlog) | HIGH |
| Context in logs | Include correlation IDs | HIGH |
| Log levels | Use appropriate level (debug/info/error) | HIGH |
| Error logging | Log exceptions with stack traces | CRITICAL |
| No sensitive data | Never log passwords/tokens | CRITICAL |
| Timing info | Add execution time for operations | MEDIUM |

**CRITICAL:**
- ✅ **PASS:** Errors logged with context
- ✅ **PASS:** No sensitive data in logs
- ❌ **FAIL:** Using print() instead of logging
- ❌ **FAIL:** Errors without stack traces

---

## 8. ASYNC PATTERNS (07-async-patterns.md)

| Rule | Requirement | Impact |
|------|-------------|--------|
| Use async def | Mark async functions properly | CRITICAL |
| Await async calls | Don't forget await | CRITICAL |
| Async context managers | Use `async with` for async resources | CRITICAL |
| No blocking in async | No `time.sleep()` in async functions | CRITICAL |
| Timeouts | Set timeouts for external calls | HIGH |
| Error handling | Handle asyncio.TimeoutError | HIGH |

**CRITICAL:**
- ✅ **PASS:** Proper async/await usage
- ✅ **PASS:** Async context managers used
- ❌ **FAIL:** Blocking calls in async functions
- ❌ **FAIL:** Missing await on async calls

---

## 9. CLEAN CODE (from 05-architecture.md)

| Rule | Requirement | Impact |
|------|-------------|--------|
| Descriptive names | Names should reveal intent | MEDIUM |
| DRY | No code duplication | HIGH |
| KISS | Keep it simple, stupid | HIGH |
| YAGNI | Implement what's needed | MEDIUM |
| Early returns | Guard clauses to reduce nesting | HIGH |
| Composition > inheritance | Prefer composition over deep inheritance | MEDIUM |

**CRITICAL:**
- ✅ **PASS:** No obvious code duplication
- ✅ **PASS:** Early returns used
- ❌ **FAIL:** Inconsistent naming
- ❌ **FAIL:** Duplicated code blocks

---

## 10. DESIGN PATTERNS (04-design-patterns.md)

| Rule | Requirement | When to Use |
|------|-------------|-------------|
| Repository | Abstract data access | Data access layer |
| Factory | Create objects without specifying class | Runtime type selection |
| Strategy | Interchangeable algorithms | Multiple trading strategies |
| Dependency Injection | Inject dependencies via constructor | All services |
| Observer | Event notification | Price updates, events |

**CRITICAL:**
- ✅ **PASS:** Repository pattern for data access
- ✅ **PASS:** Strategy pattern for trading algorithms
- ❌ **FAIL:** Direct database calls in business logic
- ❌ **FAIL:** Hardcoded dependencies

---

## 11. TRADING-SPECIFIC (various trading/*.md)

| Rule | Requirement | Impact |
|------|-------------|--------|
| Risk validation | Validate orders before execution | CRITICAL |
| Position limits | Enforce max position size | CRITICAL |
| Audit trail | Log all trade decisions | CRITICAL |
| Price validation | Validate price inputs | HIGH |
| Symbol validation | Validate trading symbols | HIGH |
| Backtesting realism | Include transaction costs | HIGH |

**CRITICAL:**
- ✅ **PASS:** Orders validated before execution
- ✅ **PASS:** All trades logged for audit
- ❌ **FAIL:** No risk checks on orders
- ❌ **FAIL:** Missing audit trail

---

## 12. CODE QUALITY (from 00-checklist.md)

| Rule | Requirement | Check Command |
|------|-------------|---------------|
| Complexity < 10 | Cyclomatic complexity per function | `radon cc . -a` |
| No dead code | Remove unused code | `vulture .` |
| Duplication < 5% | Code duplication percentage | `jscpd . .` |
| Pylint ≥ 8.0 | Pylint score minimum | `pylint .` |

**CRITICAL:**
- ✅ **PASS:** Complexity under 10
- ✅ **PASS:** No dead code
- ❌ **FAIL:** High complexity function
- ❌ **FAIL:** Significant code duplication

---

## Quick Reference for File Requirements

When creating a `.requirements.md` file for any production code:

1. **ALWAYS reference this file:** `See ../../CRITICAL_RULES.md for universal rules`

2. **File-specific rules:** Only document rules UNIQUE to this file (e.g., "Must validate covariance matrix is positive semidefinite" for MVO)

3. **Overengineering filter:** Before marking a GAP, ask:
   - Does this prevent a real bug?
   - Does this impact trading safety?
   - Does this reduce duplication significantly?
   - Is this a production standard?

4. **Critical vs Minor:**
   - **P0 (Critical):** Security, data loss, trading errors, crashes
   - **P1 (High):** Production incidents, debugging issues
   - **P2 (Medium):** Maintainability, moderate duplication
   - **P3 (Low):** Style improvements, subjective naming

---

## Acceptance Criteria Template

For each file, define deterministic acceptance criteria:

```bash
# Example: Type hints coverage
AC-001: All public functions have type hints
Check: grep -c "def.*->" app/path/to/file.py | wc -l == N_PUBLIC_FUNCTIONS
Expected: 0 functions without return type hints

# Example: No hardcoded secrets
AC-002: No API keys or secrets in code
Check: grep -r "api_key\|secret\|password" app/path/to/file.py | grep -v "os.environ\|getenv\|Settings"
Expected: 0 hardcoded secrets

# Example: Error logging
AC-003: All exception paths log errors
Check: grep -c "logger.error\|log.error" app/path/to/file.py >= N_EXCEPTION_HANDLERS
Expected: All exception handlers have error logging
```

---

**END OF CRITICAL RULES**
