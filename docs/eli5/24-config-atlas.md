# The configuration atlas — where every knob lives

## The short version

Every setting in this system comes from one of three places: environment variables, YAML files, or Python defaults. Environment variables hold secrets, hosts, and ports. YAML files hold the trading numbers. Python defaults are the safety net for when neither is set.

Mostly they don't fight, because each knob has one home. When they do overlap, there's a rule: a real environment variable beats the `.env` file, and both beat the Python default. The front door for all of it is `get_config()`.

## The map

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 470" role="img" aria-label="Config map: env vars, YAML files and Python defaults merge into one config object">
  <defs>
    <marker id="cfgArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="468" rx="14" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="30" y="30" width="220" height="88" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="140" y="58" font-size="15" font-weight="bold" fill="#FFFFFF">Environment variables</text>
    <text x="140" y="80" font-size="12" fill="#FFFFFF">.env and .env.prod</text>
    <text x="140" y="98" font-size="12" fill="#FFFFFF">secrets, hosts, ports</text>
    <rect x="270" y="30" width="220" height="88" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="58" font-size="15" font-weight="bold" fill="#FFFFFF">YAML files</text>
    <text x="380" y="80" font-size="12" fill="#FFFFFF">the config/ folder</text>
    <text x="380" y="98" font-size="12" fill="#FFFFFF">thresholds, costs, allocations</text>
    <rect x="510" y="30" width="220" height="88" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="620" y="58" font-size="15" font-weight="bold" fill="#2B2D42">Python defaults</text>
    <text x="620" y="80" font-size="12" fill="#2B2D42">pydantic Field values</text>
    <text x="620" y="98" font-size="12" fill="#2B2D42">the safety net</text>
    <line x1="140" y1="118" x2="140" y2="198" stroke="#2B2D42" stroke-width="2" marker-end="url(#cfgArrow)"/>
    <text x="140" y="165" font-size="11" fill="#2B2D42">strongest</text>
    <line x1="380" y1="118" x2="380" y2="198" stroke="#2B2D42" stroke-width="2" marker-end="url(#cfgArrow)"/>
    <line x1="620" y1="118" x2="620" y2="198" stroke="#2B2D42" stroke-width="2" marker-end="url(#cfgArrow)"/>
    <text x="620" y="165" font-size="11" fill="#2B2D42">fallback</text>
    <rect x="180" y="202" width="400" height="96" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="232" font-size="15" font-weight="bold" fill="#2B2D42">The loaders</text>
    <text x="380" y="254" font-size="12" fill="#2B2D42">CentralizedConfig plus YAMLConfigLoader</text>
    <text x="380" y="272" font-size="12" fill="#2B2D42">env beats file beats default</text>
    <line x1="380" y1="298" x2="380" y2="358" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#cfgArrow)"/>
    <rect x="180" y="362" width="400" height="88" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="392" font-size="15" font-weight="bold" fill="#FFFFFF">One config object</text>
    <text x="380" y="414" font-size="12" fill="#FFFFFF">get_config() serves everyone</text>
    <text x="380" y="432" font-size="12" fill="#FFFFFF">reload_config() starts over</text>
  </g>
</svg>

Here's the load order, verified in the code. `CentralizedConfig` is a pydantic `BaseSettings` with `env_file=".env"`, so it reads real environment variables first, then the file, then its own field defaults. It also walks `config/strategies/` and loads every YAML there. Everything else under `config/` is pulled by `YAMLConfigLoader`, one subsystem at a time.

## Data sources

Prices, fundamentals, and sentiment. One YAML plus a handful of API keys.

- `cache.default_ttl_seconds` (`config/market/data_engine.yaml`) — how long cached data stays fresh — 3600 seconds.
- `sources.ohlcv.default_frequency` (same file) — bar size when nobody asks — `1d`.
- `sources.ohlcv.binance.max_candles_per_request` — page size for Binance history — 1000 candles.
- `sources.sentiment.twitter.sample_size` — tweets analyzed per sentiment check — 10.
- `POLYGON_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY` (`.env`) — paid data feeds; a placeholder means off.
- `YAHOO_FINANCE_ENABLED` (`.env`) — the free fallback feed — true.

## Brokers

Who takes your orders, and what trading costs. Split between user settings, env wiring, and a cost model.

- `broker_settings.broker_type` (`config/user_config.yaml`) — `paper`, `alpaca`, or `ibkr` — paper.
- `broker_settings.ibkr_host` / `ibkr_port` (same file) — where TWS (the IBKR desktop app) listens — `127.0.0.1` and 4001.
- `IB_PORT`, `IB_HOST`, `IB_CLIENT_ID`, `IB_PAPER_TRADING` (`.env`) — the env-side wiring — 7497, localhost, 1, true.
- `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` / `ALPACA_BASE_URL` (`.env`) — the paper-trading broker keys.
- `commission.per_share` (`config/brokers/interactive_brokers.yaml`) — IBKR cost model for backtests — half a cent per share.
- `spread.large_cap_bps` (same file) — assumed bid-ask spread for big stocks — 3 basis points.
- `market_impact.max_participation_rate` (same file) — cap on your share of volume — 10 percent.

## Trading thresholds

The strategy gates. These live in Python, not YAML: `TradingThresholds` in `app/shared/config/params/trading_thresholds.py`.

- `min_signal_strength` — weakest signal that still counts — 60 out of 100.
- `min_signal_confidence` — the doubt filter — 70.
- `rsi_oversold` / `rsi_overbought` — classic RSI fences — 30 and 70.
- `max_position_size` — cap for one position — a tenth of capital.
- `stop_loss_pct` / `take_profit_pct` — default exits — 5 and 15 percent.
- `DEFAULT_STOP_LOSS_PERCENT`, `DEFAULT_TAKE_PROFIT_PERCENT` (`.env`) — env overrides for the same idea — 5 and 15 percent.

## Risk

Brakes and circuit breakers. Three homes, sadly, so check all of them.

- `risk_limits.max_daily_loss` (`config/user_config.yaml`) — the daily loss brake — 5 percent.
- `risk_limits.kill_switch_enabled` (same file) — the big off button — true.
- `position_sizing.default.max_percent` (`config/risk/risk_management.yaml`) — single-position cap — a quarter of capital.
- `circuit_breaker_daily_loss` (Python `TradingThresholds`) — the code-side breaker — 5 percent.
- `circuit_breaker.level_1_threshold` (`config/environments/production.yaml`) — first halt level — minus 7 percent.
- `CIRCUIT_BREAKER_LEVEL_1_THRESHOLD` (`.env.prod.example`) — the same brake, set from env.
- `risk.max_var_daily_pct` (`config/environments/production.yaml`) — daily VaR (value at risk) limit — 2 percent.

## Portfolio

Capital slices and rebalancing. Almost everything is in one YAML.

- `strategy_allocations.momentum.capital_allocation.target_weight` (`config/portfolio/portfolio.yaml`) — the momentum slice — 60 percent.
- `strategy_allocations.mean_reversion...target_weight` (same file) — the mean reversion slice — 25 percent.
- `strategy_allocations.pairs_trading...target_weight` (same file) — pairs trading — 15 percent.
- `rebalancing.threshold` — drift that triggers a rebalance — 5 percent.
- `portfolio.total_capital` — the starting pot — 100000 dollars.
- `symbol_mappings` (same file) — each ticker's sector and country, used for diversification.

## Infrastructure

Databases, ports, and limits. Mostly env vars, with a per-stage YAML on top.

- `DATABASE_URL` / `DB_PASSWORD` (`.env`) — the Postgres connection; the password must come from env, never code.
- `REDIS_URL` (`.env`) — the cache.
- `API_PORT` (`.env`) — FastAPI's front door — 8000.
- `DASHBOARD_PORT` (`.env`) — the NiceGUI dashboard — 8501.
- `monitoring.memory_limit_mb` (`config/environments/production.yaml`) — RAM ceiling — 4096 MB.
- `rate_limiting.ibkr.requests_per_second` (same file) — the broker throttle — 50.
- `CONFIG_DIR` (env) — moves the whole `config/` folder somewhere else.
- `config/environments/development.yaml`, `staging.yaml`, `production.yaml` — one flavor per stage.

## Security

Secrets and tokens. Rule 28 of the engineering rulebook: no hardcoded credentials, ever.

- `SECRET_KEY` (`.env`) — signs the JWT login tokens — minimum 32 characters.
- `ACCESS_TOKEN_EXPIRE_MINUTES` (`.env`) — how long a login lasts — 30 minutes.
- `ALLOW_WEAK_SECRET_KEY` (`.env`) — a dev-only escape hatch — keep it false.
- `config/secrets.yaml.example` — the YAML secret shelf; copy to `secrets.yaml`, never commit it. Holds `marketaux_api_key`, webhook URLs, and `encryption_key`.
- `python scripts/validate_security.py` — checks all of the above before you ship.

## The big one

`app/shared/config/centralized_config.py` is the giant in the middle. It's 860 lines today, and it's the facade everyone imports. The refactoring plan (`docs/REFACTORING_PLAN_GOD_CLASSES.md`) counted its whole family at 3,816 lines doing 12-plus jobs, and wants it split into about eight focused files.

The split has started: the `params/` folder already holds `trading_thresholds.py` (876 lines) and friends. But `app/shared/config/trading_config.py` still holds 2,099 lines and a second `CentralizedConfig`. So there are two front doors, each with its own `get_config()`. Check which one your code imports before you add a knob.

## Where it lives in the code

- `config/` — the YAML atlas: `market/`, `brokers/`, `risk/`, `portfolio/`, `strategies/`, `environments/`, `rollout/`.
- `app/shared/config/centralized_config.py` — the facade, `get_config()`, and the strategy YAML loader.
- `app/shared/config/params/trading_thresholds.py` — the Python trading defaults.
- `app/shared/config/trading_config.py` — the older twin facade.
- `app/shared/config/config_loader.py` — `YAMLConfigLoader` and the `CONFIG_DIR` override.
- `.env.example` and `.env.prod.example` — every env var, grouped and commented.

## Want to go deeper?

Where next? [The component playbook](13-component-playbook.md) explains the logic behind each knob. [Deployment](28-deployment.md) shows how config ships to each stage. And [the IBKR connection](12-ibkr.md) covers the broker wiring.
