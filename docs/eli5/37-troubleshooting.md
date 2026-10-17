# Troubleshooting and FAQ

## The short version

Most trouble here falls into four buckets: ports, missing data, tool setup, and keys. Before anything else, read the exact error text and check what is listening. Every entry below comes from real code in this repo, with the file or command that fixes it.

## Dashboards and docs

### The /docs page says "Documentation site is not built yet."

Symptom: you open `http://localhost:8503/docs/` and see "Documentation site is not built yet."
Cause: `site/` has no `index.html`, so the app skips the mount (see `_mount_documentation` in `app/presentation/dashboard/nicegui_app/app.py`).
Fix: run `make docs-build`, or `make dashboard` (it builds first), then restart.

### Diagrams show as empty gaps on github.com

Symptom: the inline `<svg>` diagrams in docs/eli5 render fine locally but leave blank space on GitHub.
Cause: GitHub strips inline SVG from markdown for security.
Fix: read the page in VS Code preview, or in the dashboard at `http://localhost:8503/docs/`.

### mkdocs build warns your new page is missing from the nav

Symptom: `make docs-build` prints a warning that a page "exists in the docs directory, but is not included in the 'nav'".
Cause: `nav:` in `mkdocs.yml` is a hand-written list, so a new file stays invisible until you add it.
Fix: add the path under `nav:` in `mkdocs.yml`, then rebuild.

### "address already in use" when starting the API or dashboard

Symptom: uvicorn or NiceGUI dies with `[Errno 48] address already in use` on port 8000 or 8503.
Cause: an older run still holds the port; the start script only warns "already running".
Fix: find it with `lsof -Pi :8000 -sTCP:LISTEN -t`, `kill` that PID, or run `scripts/stop_paper_trading.sh`.

### The paper script prints 8501, but nothing loads there

Symptom: `scripts/start_paper_trading.sh` prints "Dashboard: http://localhost:8501" and that page won't open.
Cause: the banner text is stale; the script really starts the app with `DASHBOARD_PORT=8503`.
Fix: open `http://localhost:8503` instead.

### `make docs-lint` fails with "vale: command not found"

Symptom: `make docs-lint`, or the `vale-eli5` pre-commit hook, fails with `vale: command not found`.
Cause: the vale binary lives in `~/.local/bin`, which may not be on your PATH.
Fix: `export PATH="$HOME/.local/bin:$PATH"` (the note in `.pre-commit-config.yaml` says the same).

## Data and backtests

### Backtest crashes with FileNotFoundError for a CSV

Symptom: `FileNotFoundError: CSV file not found: data/historical/BABA.csv` (any symbol).
Cause: CSV mode reads `data/historical/{symbol}.csv` (see `app/backtesting/data_loader.py`), and only seven tickers ship there.
Fix: pick AAPL, AMZN, GOOGL, META, MSFT, NVDA or TSLA, or load with `source="yfinance"`.

### "No data available from Yahoo Finance"

Symptom: `RuntimeError: No data available from Yahoo Finance for {symbol}`.
Cause: all three fetchers failed — the v8 API, yfinance, and yahoo_fin. Usually rate limits or no network.
Fix: wait and retry, or use the local CSVs.

### Results and History pages are empty

Symptom: the dashboard opens fine, but `/results` and `/history` show nothing to pick.
Cause: those pages only read saved rows from `backtest_results.db`, and the file has none yet.
Fix: run a backtest on the Backtest Runner page (`/`) first — each run writes one row.

### Tests fail with "Invalid frequency: H"

Symptom: pytest fails at setup with `ValueError: Invalid frequency: H`.
Cause: pandas 3 removed the uppercase `H` alias for hourly.
Fix: use lowercase `h` in resample and `freq` calls (that was commit `b814341e`).

### Database connection refused on port 5432

Symptom: the API or a script fails with connection refused or OperationalError on `localhost:5432`.
Cause: Postgres runs as a Docker container; nothing listens on 5432 until it starts.
Fix: `make db` (runs `docker-compose up -d postgres redis`), then `make migrate`.

## Development tools

### The start script quits with "Virtual environment not found"

Symptom: `scripts/start_paper_trading.sh` exits with "Please run: python3 -m venv .venv".
Cause: there is no `.venv/` in the repo root, and the script refuses to continue.
Fix: `python3 -m venv .venv`, activate it, rerun. Note `make docs-serve` also calls `.venv/bin/mkdocs` directly.

### pre-commit fails on a new bandit finding

Symptom: the bandit hook fails on an issue that used to pass.
Cause: known findings live in the `.bandit.baseline.json` baseline; your new code adds one outside it.
Fix: fix the code, or refresh the baseline: `bandit -r app/ -ll -f json -o .bandit.baseline.json`.

### pre-commit flags a secret in your diff

Symptom: the detect-secrets hook fails with "potential secrets about to be committed".
Cause: a real key or token in your change, checked against `.secrets.baseline`.
Fix: remove the secret, then refresh with `detect-secrets scan --baseline .secrets.baseline`.

### `npx: command not found` for the Étincel MCP

Symptom: the humanizing pass (Étincel MCP, mentioned in docs/eli5/README.md) won't start; `npx` is missing.
Cause: node is installed under `~/.local/node`, and its `bin` is not on your PATH.
Fix: `export PATH="$HOME/.local/node/bin:$PATH"`.

## Security and keys

### API returns 401 even with a key

Symptom: calls to the API return 401 or 403 although you sent a key.
Cause: the header must be `X-API-Key` and match an `AUTH_API_KEY_*` env var (`app/security/authentication/user_store.py`).
Fix: set `AUTH_API_KEY_TRADER_KEY` and `AUTH_API_KEY_TRADER_KEY_USER` in `.env`, and send the `X-API-Key` header.

### "ENCRYPTION_KEY or SECRET_KEY environment variable required"

Symptom: the secrets manager raises that error at startup.
Cause: neither environment variable is set.
Fix: export `ENCRYPTION_KEY` (or `SECRET_KEY`) before starting the app.
