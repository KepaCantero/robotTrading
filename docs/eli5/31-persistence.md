# Where data lives

## The short version

Everything this system remembers sits in one of four homes. PostgreSQL is the shared ledger: users, portfolios, trades, signals. Redis is the short-term memory for market data. Two SQLite files act as local notebooks, one for backtests and one for swarm runs. Plain files hold the raw stuff, like price CSVs and JSON reports.

Once you know which home a piece of data lives in, you also know how long it lasts and who else can read it. Here's the map:

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 260" role="img" aria-label="The four homes of data: PostgreSQL, Redis, SQLite files and plain files">
  <rect x="1" y="1" width="758" height="258" rx="14" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="20" y="24" width="165" height="190" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="102" y="54" font-size="15" font-weight="bold" fill="#FFFFFF">PostgreSQL</text>
    <text x="102" y="76" font-size="11.5" fill="#FFFFFF">the shared ledger</text>
    <text x="102" y="104" font-size="11.5" fill="#FFFFFF">users · portfolios</text>
    <text x="102" y="126" font-size="11.5" fill="#FFFFFF">trades · positions</text>
    <text x="102" y="148" font-size="11.5" fill="#FFFFFF">signals · market data</text>
    <text x="102" y="170" font-size="11.5" fill="#FFFFFF">backtests · risk metrics</text>
    <text x="102" y="198" font-size="10.5" fill="#FFFFFF">via repositories</text>
    <rect x="205" y="24" width="165" height="190" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="287" y="54" font-size="15" font-weight="bold" fill="#FFFFFF">Redis</text>
    <text x="287" y="76" font-size="11.5" fill="#FFFFFF">the short memory</text>
    <text x="287" y="104" font-size="11.5" fill="#FFFFFF">cached market data</text>
    <text x="287" y="126" font-size="11.5" fill="#FFFFFF">keys expire on their own</text>
    <text x="287" y="148" font-size="11.5" fill="#FFFFFF">set by a TTL</text>
    <text x="287" y="198" font-size="10.5" fill="#FFFFFF">via DistributedCache</text>
    <rect x="390" y="24" width="165" height="190" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="472" y="54" font-size="15" font-weight="bold" fill="#2B2D42">SQLite</text>
    <text x="472" y="76" font-size="11.5" fill="#2B2D42">two local notebooks</text>
    <text x="472" y="104" font-size="11.5" fill="#2B2D42">backtest_results.db</text>
    <text x="472" y="126" font-size="11.5" fill="#2B2D42">one row per run</text>
    <text x="472" y="148" font-size="11.5" fill="#2B2D42">swarm_runs.db</text>
    <text x="472" y="170" font-size="11.5" fill="#2B2D42">runs plus their events</text>
    <rect x="575" y="24" width="165" height="190" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="657" y="54" font-size="15" font-weight="bold" fill="#2B2D42">Plain files</text>
    <text x="657" y="76" font-size="11.5" fill="#2B2D42">just bytes on disk</text>
    <text x="657" y="104" font-size="11.5" fill="#2B2D42">data/historical CSVs</text>
    <text x="657" y="126" font-size="11.5" fill="#2B2D42">AAPL.csv and friends</text>
    <text x="657" y="148" font-size="11.5" fill="#2B2D42">outputs/ JSON reports</text>
    <text x="380" y="236" font-size="11" fill="#2B2D42">coral = shared servers</text>
    <text x="380" y="252" font-size="11" fill="#2B2D42">white = plain local files</text>
  </g>
</svg>

**PostgreSQL — the shared ledger.** This is the database of record, meaning the place where truth is kept. It holds about a dozen tables: `users`, `api_keys`, `portfolios`, `assets`, `positions`, `trades`, `market_data`, `signals`, `backtests`, `risk_metrics` and friends. Your code never writes SQL for them by hand. Repository classes like `TradeRepository` or `BacktestRepository` do all the talking.

**Redis — the short memory.** The data engine wraps Redis in a class called `DistributedCache`. Fetched prices get a key and a TTL (time to live), then they quietly expire. If the `redis` package isn't installed, the same class falls back to plain in-memory caching. The defaults live in `RedisConfig`: localhost, port 6379, database zero.

**SQLite — the two notebooks.** `backtest_results.db` is served by `BacktestResultStore`: one row per run in the `backtest_runs` table, with the key metrics in columns and the full result as JSON. The dashboard's history pages read it. `swarm_runs.db` is served by `SwarmRunStore`: tables `swarm_runs` and `swarm_events`, so Mission Control can replay a run after it ends. Both files use WAL (write-ahead logging), so the API and dashboard processes can share them without blocking each other.

**Plain files.** `data/historical/` holds one CSV per ticker, and that's what backtests replay. `outputs/` holds JSON state and reports. Nothing expires and nobody serves them; they're just files on disk.

## One backtest, three homes

A single backtest run touches three of the homes at once. Watch it flow:

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 350" role="img" aria-label="A backtest run: dashboard starts it, engine replays a strategy, prices come from Redis, the record goes to PostgreSQL and the SQLite store">
  <defs>
    <marker id="pflow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="348" rx="14" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="190" y="25" width="150" height="80" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="265" y="55" font-size="12.5" font-weight="bold" fill="#FFFFFF">DistributedCache</text>
    <text x="265" y="75" font-size="11.5" fill="#FFFFFF">prices in Redis</text>
    <text x="265" y="93" font-size="11.5" fill="#FFFFFF">fast, then forgotten</text>
    <line x1="265" y1="105" x2="265" y2="131" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#pflow)"/>
    <text x="278" y="124" font-size="10.5" fill="#2B2D42" text-anchor="start">prices</text>
    <rect x="20" y="135" width="140" height="70" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="90" y="165" font-size="13" font-weight="bold" fill="#FFFFFF">You start a run</text>
    <text x="90" y="187" font-size="11.5" fill="#FFFFFF">dashboard or API</text>
    <line x1="160" y1="170" x2="186" y2="170" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#pflow)"/>
    <rect x="190" y="135" width="150" height="70" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="265" y="165" font-size="13" font-weight="bold" fill="#2B2D42">Backtest engine</text>
    <text x="265" y="187" font-size="11.5" fill="#2B2D42">replays a strategy</text>
    <line x1="340" y1="170" x2="366" y2="170" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#pflow)"/>
    <rect x="370" y="135" width="150" height="70" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="445" y="165" font-size="12" font-weight="bold" fill="#FFFFFF">BacktestRunRecord</text>
    <text x="445" y="187" font-size="11.5" fill="#FFFFFF">metrics + full JSON</text>
    <polyline points="520,170 542,170 542,87 554,87" fill="none" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#pflow)"/>
    <polyline points="520,170 542,170 542,257 554,257" fill="none" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#pflow)"/>
    <rect x="560" y="35" width="180" height="105" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="650" y="63" font-size="14" font-weight="bold" fill="#FFFFFF">PostgreSQL</text>
    <text x="650" y="86" font-size="11.5" fill="#FFFFFF">backtests table</text>
    <text x="650" y="108" font-size="11.5" fill="#FFFFFF">written by</text>
    <text x="650" y="130" font-size="11.5" fill="#FFFFFF">BacktestRepository</text>
    <rect x="560" y="205" width="180" height="105" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="650" y="233" font-size="14" font-weight="bold" fill="#2B2D42">SQLite notebook</text>
    <text x="650" y="256" font-size="11.5" fill="#2B2D42">written by</text>
    <text x="650" y="278" font-size="11.5" fill="#2B2D42">BacktestResultStore</text>
    <text x="650" y="300" font-size="11.5" fill="#2B2D42">backtest_results.db</text>
    <text x="380" y="335" font-size="11" fill="#2B2D42">one run · three homes</text>
  </g>
</svg>

You ask for a run, the engine replays a strategy over prices, and `DistributedCache` serves those prices from Redis when they're fresh. The finished run becomes a `BacktestRunRecord`. Its tidy summary goes to PostgreSQL through `BacktestRepository`, and the full record goes to the SQLite notebook through `BacktestResultStore`.

## Migrations

When you change a table in the SQLAlchemy models, the real PostgreSQL schema has to follow. Alembic is the tool that keeps them in sync. A migration is just a versioned Python file that adds or drops columns, and Alembic remembers which ones already ran.

In this repo, `alembic.ini` sits at the root and points at `app/infrastructure/persistence/database/migrations/`. The `env.py` inside takes the database URL from your settings, or from the `ALEMBIC_DB_URL` variable. Two revisions exist today: the initial schema and one for FIFO tax tracking.

The two commands you'll actually type:

```bash
make migrate                          # apply everything: alembic upgrade head
make migration name="add foo table"   # autogenerate a revision from your models
```

There are also helpers in `scripts/migrations/` for status, rollback and stamping. The SQLite stores skip all of this. They run `CREATE TABLE IF NOT EXISTS` the first time they open, so they upgrade themselves.

## Where it lives in the code

- `app/infrastructure/persistence/database/models.py` — the SQLAlchemy tables for PostgreSQL.
- `app/infrastructure/persistence/database/_*_repositories.py` — one file per area, gathered in `repositories.py`.
- `app/infrastructure/persistence/backtest_result_store.py` — SQLite store for backtest runs.
- `app/services/agent_swarm/store.py` — `SwarmRunStore` and its two tables.
- `app/engines/data_engine/cache/distributed_cache.py` — the Redis-plus-PostgreSQL cache.
- `alembic.ini` and `app/infrastructure/persistence/database/migrations/` — schema changes.
- `data/historical/` and `outputs/` — the plain files.

## Want to go deeper?

- [Backtesting](09-backtesting.md) — what produces most of these rows.
- [The agent swarm](23-agent-swarm.md) — the runs behind `swarm_runs.db`.
- [The config atlas](24-config-atlas.md) — where the settings for all of this live.
