# AlgoTrading Microagent Configuration

## Project Overview

AlgoTrading is a Python-based algorithmic trading system with the following stack:
- **Language**: Python 3.9+
- **Framework**: FastAPI (async API layer)
- **ORM**: SQLAlchemy with Alembic migrations
- **Task Queue**: Custom persistent queue implementation
- **Cache**: Redis via distributed cache layer
- **Database**: PostgreSQL
- **Broker Integrations**: Alpaca, Interactive Brokers (IBKR)

## Architecture

The project follows Clean Architecture with these layers:

```
app/
  core/               # Core models, protocols, input profiles
  domain/             # Business logic, strategies, factories, services
  application/        # Use cases, application services
  infrastructure/     # Persistence, messaging, middleware, feeds
  presentation/       # Dashboard API router
  engines/            # Data engine, portfolio engine, strategy engines, context engine
  services/           # Live trading, position sizing, FIFO tax, Hurst analysis
  security/           # Input validation, secret management, API key rotation
  sre/                # Alert fatigue prevention, dead man's switch, reconciliation
  backtesting/        # Standard engine, walk-forward, drift detection, labeling
  simulation/         # Order book simulation
```

## Key Domain Strategies

- **Momentum**: Core momentum strategy with indicator calculations
- **Covered Call**: Options strategy with Greeks calculator, roll analyzer, position manager
- **FX Carry Trade**: Currency carry calculator with FX rates provider
- **FX Intermarket**: Correlation analyzer for intermarket FX relationships

## Coding Standards

### Formatting and Linting
- **Formatter**: `ruff format` (replaces black/isort)
- **Linter**: `ruff check` (replaces flake8)
- **Type Checker**: `mypy` with `ignore_missing_imports = true`
- **Line length**: 100 characters
- **Target**: Python 3.9

### Testing
- **Framework**: pytest
- **Coverage minimum**: 80%
- **Test structure**: `tests/unit/`, `tests/integration/`, `tests/performance/`, `tests/backtesting/`
- **Enforcement**: `--cov-fail-under=80` in CI

### Security
- **Static analysis**: bandit
- **Dependency audit**: safety
- **Secret management**: `app/security/secret_manager.py` and `app/security/secrets_manager.py`
- **Input validation**: `app/security/input_validation.py`

## Common Commands

```bash
make lint          # Run ruff check + mypy
make format        # Auto-format with ruff
make test          # Run test suite
make test-cov      # Run tests with 80% coverage gate
make security      # Run bandit + safety scans
make type-check    # Run mypy
make migrate       # Run Alembic migrations
```

## Important Patterns

1. **Repository Pattern**: Database access through `_base_repository.py`, `_trading_repositories.py`, `_analytics_repositories.py`, `_user_portfolio_repositories.py`
2. **Unit of Work**: `app/domain/repositories/unit_of_work.py`
3. **Protocol-based contracts**: `app/core/protocols/` for interfaces
4. **Strategy factory**: `app/domain/factories/` for strategy instantiation
5. **Event-driven hooks**: `.ralph/hooks/` for pre/post tool validation

## File Organization Conventions

- Domain strategies live in `app/domain/strategies/<strategy_name>/` as self-contained packages
- Each strategy package contains: `__init__.py`, models, calculator/analyzer, and supporting modules
- Requirements documents are in `.requirements/app/domain/strategies/<strategy_name>/`
- Test files mirror the source structure: `tests/strategies/<strategy_name>/`

## CI/CD Pipeline

- **CI Workflow**: `.github/workflows/ci-cd.yml` - lint, type-check, test, build, deploy
- **Testing Workflow**: `.github/workflows/testing.yml` - unit, integration, performance, security tests
- **Coverage enforcement**: 80% minimum for unit tests, 60% for integration tests
- **Security scanning**: Trivy (container), Bandit (code), Safety (dependencies)

## Ralph Agent Configuration

- Config: `.ralph/ralph.yml`
- Hooks: `.ralph/hooks/pre_tool_use.py`, `.ralph/hooks/post_tool_use.py`, `.ralph/hooks/stop.py`
- Presets: `.ralph/presets/` for loop modes
- Memories: `.ralph/agent/memories.md` for persistent learning
- Tasks: `.ralph/ralph_tasks/` for task definitions
