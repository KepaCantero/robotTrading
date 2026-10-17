# AlgoTrading

A full-featured algorithmic trading platform for research and paper trading: strategy
design, ML-enhanced signals, rigorous backtesting with walk-forward validation, live
dashboards, and production-grade operations tooling (SRE, monitoring, deployment).

> ⚠️ **Disclaimer** — This project is for research and education. It is not financial
> advice and has not been reviewed for live-money use. Use at your own risk.

## Features

- **Backtesting engine** — event-driven simulation, walk-forward and enhanced
  walk-forward validation, meta-labeling, comprehensive metric suites, and
  profile-batched runs over historical data.
- **Strategy library** — momentum (modular), ensemble strategies (weighted /
  regime-selector / voting), ML and reinforcement-learning strategies with drift
  detection and feature-importance analysis.
- **Portfolio & risk** — portfolio optimization (mean-variance and beyond), risk
  engines, position sizing, and per-strategy capital allocation.
- **Market simulation** — microstructure exchange simulator informed by
  *Trading and Exchanges* (Larry Harris) for realistic fills.
- **API** — FastAPI backend with routers for market data, portfolio, strategies,
  signals, optimization, paper trading, and more (`/docs` for OpenAPI UI).
- **Dashboards** — modern **NiceGUI** dashboard (backtest results, runner,
  profitability, config viewer, history comparison) plus legacy Streamlit dashboards.
- **Paper trading** — end-to-end paper-trading loop with start/stop scripts.
- **Spain tax engine** — compliance and tax-efficiency engines for Spanish residency
  (IRPF, Modelo 721) with FOGAIN-aware rules.
- **SRE tooling** — golden-signals monitoring, toil tracking, alerting, and on-call
  runbooks.
- **Operations** — Docker Compose stack (Postgres, Redis, ELK, Prometheus, Grafana,
  nginx), Alembic migrations, Kubernetes/Helm/Terraform deployment configs.

## Architecture

Clean-architecture layering under `app/`:

```
┌─────────────────────────────────────────────────────────┐
│ presentation/   FastAPI routers, NiceGUI + Streamlit UIs│
├─────────────────────────────────────────────────────────┤
│ application/    Use cases, handlers, orchestration      │
├─────────────────────────────────────────────────────────┤
│ domain/         Strategies, portfolio, trading logic    │
│                 market analysis, optimization, entities │
├─────────────────────────────────────────────────────────┤
│ engines/        Risk, strategy, portfolio, execution,   │
│                 data and event engines                  │
├─────────────────────────────────────────────────────────┤
│ infrastructure/ Persistence, brokers, feeds,            │
│                 repositories, resilience                │
├─────────────────────────────────────────────────────────┤
│ services/       Application services (portfolio,        │
│                 signals, compliance, tax, ...)          │
├─────────────────────────────────────────────────────────┤
│ shared/ sre/ security/ simulation/ backtesting/ core/   │
└─────────────────────────────────────────────────────────┘
```

## Quickstart

Requires Python ≥ 3.9 (3.11 recommended). The dependency set is heavy
(torch / tensorflow / xgboost / stable-baselines3), so the first install takes a while.

```bash
git clone https://github.com/KepaCantero/robotTrading.git
cd robotTrading

python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # then fill in the keys you want to use

# API (http://localhost:8000, docs at /docs)
uvicorn app.main:app --reload

# NiceGUI dashboard (http://localhost:8080)
python -m app.presentation.dashboard.nicegui_app.app
```

Paper trading (API + Streamlit dashboard):

```bash
./scripts/start_paper_trading.sh
./scripts/stop_paper_trading.sh
```

Full stack via Docker Compose (Postgres, Redis, ELK, Prometheus, Grafana, nginx):

```bash
docker compose up -d        # or: make up
```

## Testing

```bash
pytest                      # full suite, coverage gate at 80%
make test-cov               # same via Makefile
```

The suite includes unit, integration, and backtesting tests (~525 test files),
property-based tests (Hypothesis), and uses the sample data in `data/historical/`.

## Project structure

```
app/                 Source code (see architecture above)
tests/               Unit / integration / backtesting test suites
config/              YAML configuration (environments, strategies, risk, rules/)
docs/                User, developer, architecture and SRE documentation
scripts/             QA, DB, deployment, maintenance and paper-trading scripts
examples/            Example scripts for services and strategies
data/historical/     Sample CSV data used by the test suite
models/registry/     Model registry metadata (trained .joblib artifacts are
                     generated at runtime and not committed)
deploy/ logging/     Kubernetes / Helm / monitoring, ELK stack configs
infrastructure/      Terraform
alembic/             Database migrations
.ralph/ .claude/ .tasks/ .requirements/ .openhands/
                     AI-assisted development artifacts (requirements audit
                     trails, agent roles and prompts) — kept intentionally
                     as part of the development workflow of this project
```

## Configuration

All secrets come from the environment (see `.env.example`): broker keys
(Alpaca, Interactive Brokers), data providers (Alpha Vantage, Marketaux, NewsAPI),
Telegram notifications, database and Redis credentials. Never commit real keys.

## Documentation

- [Quickstart](docs/quickstart.md) · [Installation](docs/installation.md) ·
  [User guide](docs/user/USER_GUIDE.md) · [Paper trading](docs/user/PAPER_TRADING.md)
- [Architecture](docs/architecture/ARCHITECTURE.md) ·
  [Developer guide](docs/developer/GETTING_STARTED.md)
- [API reference](docs/api/API_REFERENCE.md)

## License

Personal project by Kepa Cantero. All rights reserved unless stated otherwise.
