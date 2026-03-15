# BASE_RULES.md - AlgoTrading Codebase

**Last Updated:** 2026-03-15
**Total Rule Files:** 80
**Total Rules Extracted:** 250+ rules organized

---

## Purpose

These are the **BASE RULES** that EVERY production file in algoTrading MUST follow. Each `.requirements.md` file should reference these universal rules plus file-specific rules.

---

## OVERENGINEERING FILTER (READ THIS FIRST)

Before marking ANY rule as a GAP, apply this filter:

### ✅ APPLY (Real Value) - Mark as GAP
- **Prevents bugs:** timeouts, race conditions, data loss, crashes, null pointer exceptions
- **Prevents production incidents:** trading errors, wrong positions, failed orders
- **Reduces duplication significantly:** >30% code reduction
- **Trading system safety:** risk limits, position validation, audit trails
- **Production standards:** logging, monitoring, error handling, structured logs
- **Security:** no hardcoded secrets, input validation, SQL injection prevention

### ❌ SKIP (Overengineering) - Do NOT mark as GAP
- Marginal style improvements (variable naming preference like `data` vs `items`)
- Subjective opinions (one-liners vs multi-line, "clever" code)
- Micro-optimizations without measured bottleneck
- Dogmatic rule-following with no real impact
- "Could be more Pythonic" when current code is clear

---

## CRITICAL RULES - All Files Must Pass

### Priority Levels
- **P0 (Critical):** Security issues, data loss, trading errors, crashes
- **P1 (High):** Production incidents, debugging issues, performance degradation
- **P2 (Medium):** Maintainability, moderate duplication
- **P3 (Low):** Style improvements, subjective naming

---

## 1. FORMATTING & STYLE (01-formatting-style.md)

| Rule ID | Rule | Requirement | Check Command | Priority |
|---------|------|------------|---------------|----------|
| FMT-001 | Line length ≤ 100 | Black enforces 100 char limit | `black --check FILE` | P2 |
| FMT-002 | Import organization | stdlib → third-party → local | `isort --check-only FILE` | P2 |
| FMT-003 | No unused imports | Remove all unused imports | `autoflake --check FILE` | P2 |
| FMT-004 | Double quotes | Prefer double quotes for strings | `black --check FILE` | P3 |
| FMT-005 | Trailing commas | Multi-line collections need trailing comma | `black --check FILE` | P3 |
| FMT-006 | F-strings | Use f-strings not .format() or % | Manual review | P2 |
| FMT-007 | No mutable defaults | Use `None` instead of `[]` or `{}` | `flake8 FILE` | P0 |
| FMT-008 | Context managers | Use context managers for resources | Manual review | P0 |

**Automated Check:**
```bash
black --check app/path/to/file.py
isort --check-only app/path/to/file.py
```

---

## 2. TYPE HINTS (02-type-hints.md)

| Rule ID | Rule | Requirement | Check Command | Priority |
|---------|------|------------|---------------|----------|
| TYP-001 | 100% type coverage | All functions have type hints | `mypy --strict FILE` | P1 |
| TYP-002 | Modern syntax | Use `list[T]`, `dict[K,V]`, `X \| None` | `mypy --strict FILE` | P2 |
| TYP-003 | No Any without justification | Use specific types or Protocol | `mypy --strict FILE` | P1 |
| TYP-004 | Type ignore with comment | All `# type: ignore` have explanation | Manual review | P2 |
| TYP-005 | Class attribute types | All class attributes have type hints | `mypy --strict FILE` | P2 |
| TYP-006 | Protocol for duck typing | Use Protocol instead of ABC | Manual review | P2 |

**Automated Check:**
```bash
mypy --strict app/path/to/file.py
```

---

## 3. SOLID PRINCIPLES (03-solid-principles.md)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| SOL-001 | Single Responsibility | One class, one reason to change | P0 |
| SOL-002 | Open/Closed Principle | Open for extension, closed for modification | P1 |
| SOL-003 | Liskov Substitution | Subtypes substitutable for base types | P1 |
| SOL-004 | Interface Segregation | Small, focused interfaces | P2 |
| SOL-005 | Dependency Inversion | Depend on abstractions (Protocol/ABC) | P0 |

**Critical Violations:**
- ❌ Class doing validation + DB + email (violates SRP)
- ❌ Direct instantiation of dependencies (violates DIP)
- ✅ Separate classes with single responsibilities
- ✅ Dependency injection via constructor

---

## 4. ARCHITECTURE (05-architecture.md, 11-enterprise-architecture.md, 18-clean-architecture-structure.md)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| ARCH-001 | Layered architecture | presentation → application → domain ← infrastructure | P0 |
| ARCH-002 | Dependencies inward | Domain knows nothing about other layers | P0 |
| ARCH-003 | No framework in domain | Domain has no FastAPI/SQLAlchemy imports | P0 |
| ARCH-004 | Small functions | Functions < 20 lines (ideally) | P2 |
| ARCH-005 | Early returns | Use guard clauses to avoid nesting | P2 |
| ARCH-006 | Value objects immutable | Use `@dataclass(frozen=True)` | P1 |
| ARCH-007 | Composition > inheritance | Prefer composition over deep inheritance | P2 |

**Layer Structure:**
```
app/
├── domain/          # Business entities (no framework dependencies)
├── application/     # Use cases and orchestration
├── infrastructure/  # External concerns (DB, APIs)
└── presentation/     # Interface layer (API, CLI)
```

---

## 5. TESTING (06-testing.md, 15-testing-comprehensive.md, 21-tdd-python-testing.md)

| Rule ID | Rule | Requirement | Check Command | Priority |
|---------|------|------------|---------------|----------|
| TST-001 | AAA pattern | Arrange-Act-Assert structure | Manual review | P1 |
| TST-002 | Descriptive names | `test_<what>_<condition>_<expected>` | Manual review | P1 |
| TST-003 | Parametrized tests | Use `@pytest.mark.parametrize` for cases | `pytest FILE` | P2 |
| TST-004 | Mock external deps | Use `unittest.mock` for external services | `pytest FILE` | P1 |
| TST-005 | Coverage > 80% | Minimum test coverage | `coverage report` | P0 |
| TST-006 | Exception testing | Test exceptions with `pytest.raises` | `pytest FILE` | P1 |
| TST-007 | Async testing | Use `@pytest.mark.asyncio` for async tests | `pytest FILE` | P1 |
| TST-008 | Fixtures | Use fixtures for common setup | Manual review | P2 |

**Test Pattern:**
```python
def test_function_success():
    # Arrange - Set up test data
    # Act - Execute the function
    # Assert - Verify the result
```

---

## 6. SECURITY (28-security-and-secrets.md)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| SEC-001 | No hardcoded secrets | Use environment variables | **P0** |
| SEC-002 | Environment validation | Pydantic Settings for config | **P0** |
| SEC-003 | TLS/SSL required | HTTPS only for external APIs | **P0** |
| SEC-004 | HMAC signing | Sign all API requests with HMAC | **P0** |
| SEC-005 | Audit logging | Log all trading operations | **P0** |
| SEC-006 | Rate limiting | Implement rate limits for APIs | P1 |
| SEC-007 | Input validation | Validate at system boundaries | **P0** |
| SEC-008 | Strong crypto | Use bcrypt/argon2 for passwords | P0 |
| SEC-009 | JWT auth | Use JWT for authentication | P1 |
| SEC-010 | Encryption at rest | Encrypt sensitive data on disk | P0 |

**CRITICAL:**
- ✅ Secrets in environment variables
- ❌ Hardcoded API keys/secrets
- ✅ HTTPS/TLS for all network calls
- ❌ HTTP for any API communication

---

## 7. LOGGING & OBSERVABILITY (09-logging-observability.md, 12-logging-observability.md)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| LOG-001 | Structured logging | Use JSON format (structlog) | P1 |
| LOG-002 | Context in logs | Include correlation IDs | P1 |
| LOG-003 | Appropriate levels | Use appropriate level (debug/info/error) | P1 |
| LOG-004 | Error logging | Log exceptions with stack traces | **P0** |
| LOG-005 | No sensitive data | Never log passwords/tokens | **P0** |
| LOG-006 | Timing info | Add execution time for operations | P2 |
| LOG-007 | Health checks | Implement health check endpoints | P1 |

**Logging Example:**
```python
log.info(
    "Processing order",
    order_id=order_id,
    user_id=user_id,
    action="process_order",
)
```

---

## 8. ASYNC PATTERNS (07-async-patterns.md, 13-async-patterns.md, 24-asyncio-concurrency-trading.md)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| ASYNC-001 | Use async def | Mark async functions properly | **P0** |
| ASYNC-002 | Await async calls | Don't forget await | **P0** |
| ASYNC-003 | Async context managers | Use `async with` for async resources | **P0** |
| ASYNC-004 | No blocking in async | No `time.sleep()` in async functions | **P0** |
| ASYNC-005 | Timeouts | Set timeouts for external calls | **P1** |
| ASYNC-006 | Error handling | Handle `asyncio.TimeoutError` | **P1** |
| ASYNC-007 | Run blocking in executor | Use `run_in_executor` for blocking I/O | P1 |

---

## 9. CONFIGURATION (08-configuration.md, 14-configuration-management.md)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| CFG-001 | Pydantic Settings | Use Pydantic Settings for type-safe config | P1 |
| CFG-002 | Environment variables | Use environment variables for deployment | **P0** |
| CFG-003 | Validation | Validate all configuration values | P1 |
| CFG-004 | Extra forbid | Set `extra="forbid"` to catch typos | P2 |
| CFG-005 | Environment prefix | Use environment prefix to avoid conflicts | P2 |
| CFG-006 | Field validators | Add field validators for complex validation | P2 |
| CFG-007 | Feature flags | Implement feature flags for gradual rollouts | P2 |

**Configuration Example:**
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="forbid",
    )
    api_key: str = Field(..., min_length=32)
```

---

## 10. CLEAN CODE (05-architecture.md, 25-clean-code-python-trading.md)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| CC-001 | Descriptive names | Names should reveal intent | P2 |
| CC-002 | DRY | No code duplication | P1 |
| CC-003 | KISS | Keep it simple, stupid | P1 |
| CC-004 | YAGNI | Implement what's needed | P2 |
| CC-005 | Early returns | Guard clauses to reduce nesting | P2 |
| CC-006 | Explicit error handling | Specific exceptions raised/caught | **P0** |
| CC-007 | Small functions | Functions < 20 lines (ideally) | P2 |

---

## 11. DESIGN PATTERNS (04-design-patterns.md, 10-advanced-patterns.md)

| Rule ID | Rule | When to Use | Priority |
|---------|------|-------------|----------|
| DP-001 | Repository pattern | Data access layer | P1 |
| DP-002 | Factory pattern | Runtime type selection | P2 |
| DP-003 | Strategy pattern | Multiple trading strategies | P1 |
| DP-004 | Dependency injection | All services | **P0** |
| DP-005 | Observer pattern | Event notification | P2 |
| DP-006 | Builder pattern | Complex objects with optional parts | P2 |

**Critical Pattern:**
```python
# ✅ Dependency Injection (REQUIRED)
class Service:
    def __init__(self, repository: Repository, logger: Logger):
        self._repository = repository
        self._logger = logger

# ❌ Direct instantiation (NOT ALLOWED)
class Service:
    def __init__(self):
        self._repository = PostgreSQLDatabase()  # Tight coupling!
```

---

## 12. CODE QUALITY (00-checklist.md, 19-enterprise-checklist.md)

| Rule ID | Rule | Requirement | Check Command | Priority |
|---------|------|------------|---------------|----------|
| QL-001 | Complexity < 10 | Cyclomatic complexity per function | `radon cc FILE -a` | P1 |
| QL-002 | No dead code | Remove unused code | `vulture FILE` | P2 |
| QL-003 | Duplication < 5% | Code duplication percentage | `jscpd FILE FILE` | P1 |
| QL-004 | Pylint ≥ 8.0 | Pylint score minimum | `pylint FILE` | P2 |
| QL-005 | Functions < 50 lines | Maximum function length | Manual review | P2 |
| QL-006 | Classes < 300 lines | Maximum class length | Manual review | P2 |
| QL-007 | Max 7 parameters | Maximum parameters per function | Manual review | P1 |

---

## 13. TRADING-SPECIFIC RULES

### Portfolio Optimization (papers/48-papers-markowitz, 46-lopez-de-prado)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| TRD-001 | Covariance validation | Validate matrix is positive semidefinite | **P0** |
| TRD-002 | Risk validation | Validate orders before execution | **P0** |
| TRD-003 | Position limits | Enforce max position size | **P0** |
| TRD-004 | Audit trail | Log all trade decisions | **P0** |
| TRD-005 | Price validation | Validate price inputs | **P1** |
| TRD-006 | Transaction costs | Include costs in backtesting | **P1** |
| TRD-007 | Annualization | Document TRADING_DAYS = 252 | P2 |

### Risk Management (13-john-hull, 52-papers-artzner)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| RSK-001 | VaR calculation | Calculate Value at Risk | **P0** |
| RSK-002 | Expected Shortfall | Calculate ES for tail risk | **P0** |
| RSK-003 | Drawdown control | Implement max drawdown limits | **P0** |
| RSK-004 | Circuit breakers | Implement trading halt conditions | **P1** |

### Backtesting (41-pardo-evaluation-optimization, 10-robert-carver-systematic-trading)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| BT-001 | Walk-forward validation | Use walk-forward validation | **P0** |
| BT-002 | Out-of-sample testing | Test on unseen data | **P0** |
| BT-003 | No look-ahead bias | Ensure no future data leakage | **P0** |
| BT-004 | Realistic costs | Include slippage and commissions | **P0** |
| BT-005 | Multiple periods | Test across different market regimes | **P1** |

### Execution (42-kissell, 29-barry-johnson, 44-papers-almgren-chriss)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| EXE-001 | Order validation | Validate order parameters | **P0** |
| EXE-002 | Execution timing | Handle execution timing properly | **P1** |
| EXE-003 | Market impact | Consider market impact of trades | P1 |
| EXE-004 | Order splitting | Split large orders to reduce impact | P2 |

---

## 14. SRE & PERFORMANCE (19-high-performance-python.md, 20-sre-site-reliability-engineering.md, 23-high-performance-python-optimization)

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| PERF-001 | List comprehensions | Use list comprehensions over loops | P2 |
| PERF-002 | Generators for large data | Use generators for large datasets | P2 |
| PERF-003 | Sets for O(1) lookups | Use sets for membership tests | P2 |
| PERF-004 | Profile before optimizing | Measure before optimizing | P2 |
| PERF-005 | Numba JIT | Use Numba for hot paths | P2 |
| PERF-006 | Async I/O | Use async/await for I/O concurrency | P1 |

---

## 15. ARCHITECTURE BOUNDARIES & FILE SYSTEM (05-architecture.md, 16-cosmic-python-architecture-patterns.md, 18-clean-architecture-structure.md)

**See also:**
- `.requirements/ARCHITECTURE_REQUIREMENTS.md` - Detailed layer architecture rules
- `.requirements/FILE_SYSTEM_REQUIREMENTS.md` - File naming and directory rules

### 15.1 Layer Dependency Rules

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| ARCH-DEP-001 | Domain layer purity | Domain has NO dependencies on other layers | **P0** |
| ARCH-DEP-002 | Application dependencies | Application depends ONLY on Domain + Core/Protocols | **P0** |
| ARCH-DEP-003 | Infrastructure implements interfaces | Infrastructure implements Domain/Core Protocols | **P0** |
| ARCH-DEP-004 | Presentation uses Application | Presentation layer uses Application services only | **P0** |
| ARCH-DEP-005 | Dependency direction | All dependencies point INWARD toward Domain | **P0** |

### 15.2 Architecture Anti-Patterns (PROHIBITED)

| Rule ID | Anti-Pattern | Description | Priority |
|---------|--------------|-------------|----------|
| ARCH-ANTI-001 | Domain importing infrastructure | Domain files importing from app/infrastructure/ | **P0** |
| ARCH-ANTI-002 | Domain importing services | Domain files importing from app/services/ | **P0** |
| ARCH-ANTI-003 | Circular imports | Module A imports B, B imports A | **P0** |
| ARCH-ANTI-004 | God classes | Classes > 300 lines | P1 |
| ARCH-ANTI-005 | God functions | Functions > 50 lines | P1 |
| ARCH-ANTI-006 | Framework in domain | FastAPI, SQLAlchemy, httpx imports in domain/ | **P0** |
| ARCH-ANTI-007 | Hardcoded dependencies | Direct instantiation instead of DI | **P0** |

### 15.3 File Naming Rules

| Rule ID | Rule | Pattern | Priority |
|---------|------|---------|----------|
| ARCH-NAM-001 | File names | `snake_case.py` | P2 |
| ARCH-NAM-002 | Class names | `PascalCase` | P2 |
| ARCH-NAM-003 | Function names | `snake_case` | P2 |
| ARCH-NAM-004 | Constants | `UPPER_SNAKE_CASE` | P2 |
| ARCH-NAM-005 | Private members | `_leading_underscore` | P2 |

### 15.4 Module Rules

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| ARCH-MOD-001 | Package initialization | Every package has `__init__.py` | P1 |
| ARCH-MOD-002 | Public API exports | `__init__.py` exports public API with `__all__` | P1 |
| ARCH-MOD-003 | No logic in init | No business logic in `__init__.py` | P1 |
| ARCH-MOD-004 | No circular imports | PROHIBITED circular imports between modules | **P0** |
| ARCH-MOD-005 | DI for cycles | Use dependency injection to avoid cycles | **P0** |

### 15.5 Size Limits

| Rule ID | Type | Limit | Priority |
|---------|------|-------|----------|
| ARCH-FILE-001 | File | 300 lines max | P1 |
| ARCH-FILE-002 | Function | 50 lines max | P1 |
| ARCH-FILE-003 | Class | 300 lines max | P1 |
| ARCH-FILE-004 | Parameters | 7 max per function | P2 |
| ARCH-FILE-005 | Complexity | 10 max cyclomatic | P1 |

### 15.6 File System Rules

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| FS-001 | Package init | Every Python package has `__init__.py` | P1 |
| FS-002 | No logic in init | No business logic in `__init__.py` | P1 |
| FS-003 | Tests mirror source | `tests/unit/` mirrors `app/` structure | P1 |
| FS-004 | Config separate | Config files in `config/`, not `app/` | P1 |
| FS-005 | Logs dedicated | Log files in `logs/`, not scattered | P2 |

**Verification Commands:**
```bash
# Domain layer purity - NO matches expected
grep -r "from app.services\|from app.infrastructure\|from app.api" app/domain/

# Domain no frameworks - NO matches expected
grep -r "from fastapi\|from sqlalchemy\|import httpx" app/domain/

# File size check
find app -name "*.py" -exec wc -l {} \; | awk '$1 > 300 {print}'
```

---

## 16. COSMIC PYTHON PATTERNS (16-cosmic-python-architecture-patterns.md)

| Rule ID | Pattern | Requirement | Priority |
|---------|---------|-------------|----------|
| COSMIC-001 | Repository Pattern | Abstract data access behind Repository interface | **P0** |
| COSMIC-002 | Service Layer | Use service layer for orchestration | P1 |
| COSMIC-003 | Unit of Work | Atomic transactions with commit/rollback | **P0** |
| COSMIC-004 | Domain Events | Publish events for cross-module communication | P2 |
| COSMIC-005 | Value Objects | Immutable value objects for domain concepts | P1 |
| COSMIC-006 | Aggregates | Group related entities with aggregate root | P1 |
| COSMIC-007 | Message Bus | Decouple event handlers from publishers | P2 |

**Critical Pattern:**
```python
# ✅ Repository Pattern (REQUIRED for data access)
class TradeRepositoryProtocol(Protocol):
    def save(self, trade: Trade) -> None: ...
    def find_by_id(self, trade_id: str) -> Trade | None: ...

# ✅ Service Layer (REQUIRED for use cases)
class ExecutionService:
    def __init__(self, broker: BrokerProtocol, repo: TradeRepositoryProtocol):
        self._broker = broker
        self._repo = repo

    def execute(self, order: Order) -> Execution:
        execution = self._broker.execute_order(order)
        self._repo.save(Trade.from_execution(execution))
        return execution
```

---

## ACCEPTANCE CRITERIA TEMPLATES

For each `.requirements.md` file, define automatable acceptance criteria:

### AC-TYPE-001: Type Hints Coverage
```bash
# All functions have return type hints
grep -E "def [a-z_]+.*->" FILE | wc -l == N_PUBLIC_FUNCTIONS
# Expected: 0 functions without return type
```

### AC-SEC-001: No Hardcoded Secrets
```bash
# No API keys in code
grep -iE "api_key|secret|password|token" FILE | grep -vE "os.environ|getenv|Settings|Field\(" | wc -l == 0
# Expected: 0 hardcoded secrets
```

### AC-LOG-001: Error Logging
```bash
# All exceptions logged
grep -c "logger.error\|log.error" FILE >= N_EXCEPT_HANDLERS
# Expected: All exception handlers have error logging
```

### AC-ARCH-001: Domain Layer Purity
```bash
# Domain has no infrastructure imports
grep -E "from sqlalchemy|from fastapi|import httpx" app/domain/FILE | wc -l == 0
# Expected: 0 infrastructure imports in domain
```

### AC-FMT-001: Black Formatting
```bash
# Code is Black formatted
black --check FILE
# Expected: 0 reformatting needed
```

### AC-SOL-001: No God Objects
```bash
# No class exceeds 300 lines
awk 'NF && NR>300 {exit 1}' FILE && echo "FAIL: File > 300 lines" || echo "PASS"
# Expected: PASS
```

---

## QUICK REFERENCE FOR FILE AUDIT

When creating a `.requirements.md` file:

1. **Always reference:** `See ../../BASE_RULES.md for universal rules`

2. **Only document file-specific rules:** If a rule is in BASE_RULES, just reference it by ID

3. **Apply overengineering filter:** Before marking GAP, ask if it adds real value

4. **Define acceptance criteria:** Each gap should have an automatable check

5. **Priority matters:** Focus on P0 and P1 gaps first

---

## SUMMARY

### By Category

| Category | Rules | P0 | P1 | P2 | P3 |
|----------|-------|----|----|----|----|
| Formatting | 8 | 1 | 6 | 1 | 0 |
| Type Hints | 6 | 0 | 4 | 2 | 0 |
| SOLID | 5 | 2 | 2 | 1 | 0 |
| Architecture | 7 | 3 | 2 | 2 | 0 |
| Architecture Boundaries | 33 | 15 | 14 | 4 | 0 |
| Cosmic Python Patterns | 7 | 2 | 4 | 1 | 0 |
| Testing | 8 | 1 | 5 | 2 | 0 |
| Security | 10 | 7 | 3 | 0 | 0 |
| Logging | 7 | 2 | 4 | 1 | 0 |
| Async | 7 | 4 | 3 | 0 | 0 |
| Config | 7 | 1 | 5 | 1 | 0 |
| Clean Code | 7 | 1 | 3 | 3 | 0 |
| Patterns | 6 | 1 | 3 | 2 | 0 |
| Quality | 7 | 0 | 3 | 4 | 0 |
| Trading | 15 | 10 | 5 | 0 | 0 |
| Performance | 6 | 0 | 2 | 4 | 0 |
| **TOTAL** | **140** | **50** | **68** | **21** | **1** |

### By Priority
- **P0 (Critical):** 50 rules - Security, data integrity, trading safety, architecture boundaries
- **P1 (High):** 68 rules - Production incidents, debugging, performance
- **P2 (Medium):** 21 rules - Maintainability, code quality
- **P3 (Low):** 1 rule - Style preferences

---

**END OF BASE_RULES**

This document is the foundation for ALL requirements documents in the algoTrading codebase.
