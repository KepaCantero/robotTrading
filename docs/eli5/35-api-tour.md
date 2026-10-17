# A tour of the HTTP API

## The short version

The API is one FastAPI app. It serves 174 endpoints: 172 spread over 14 routers, plus two declared in `app/main.py` itself. Almost everything is open to read without a key. The calls that change things — loading strategies, tuning parameters, placing live orders — ask for an `X-API-Key` header first.

Two guards do the asking, and they don't cover the same ground. `AuthMiddleware` is the outer gate: it only runs outside debug mode, and it only guards write calls on `/strategies` and `/optimization`. The `@require_auth` decorator sits on 30 single endpoints, always on, whatever the mode. It rejects Bearer tokens today, and with no keys in the environment it turns everyone away — it fails closed.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 310" role="img" aria-label="Any request reaches the auth gate; public endpoints like health and docs pass free, writes like strategy changes need a key">
  <defs>
    <marker id="t35arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="308" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="280" y="14" width="200" height="54" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="38" font-size="15" font-weight="bold" fill="#FFFFFF">Any request</text>
    <text x="380" y="58" font-size="11" fill="#FFFFFF">any method, any path</text>
    <line x1="380" y1="68" x2="380" y2="96" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#t35arrow)"/>
    <rect x="230" y="100" width="300" height="70" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="126" font-size="15" font-weight="bold" fill="#FFFFFF">The auth gate</text>
    <text x="380" y="146" font-size="11" fill="#FFFFFF">middleware + @require_auth</text>
    <text x="380" y="162" font-size="11" fill="#FFFFFF">no key, no entry — 401</text>
    <line x1="300" y1="170" x2="195" y2="206" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#t35arrow)"/>
    <line x1="460" y1="170" x2="565" y2="206" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#t35arrow)"/>
    <rect x="25" y="212" width="340" height="86" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="195" y="238" font-size="13.5" font-weight="bold" fill="#2B2D42">Public — most reads</text>
    <text x="195" y="258" font-size="11" fill="#2B2D42">root · health · docs</text>
    <text x="195" y="274" font-size="11" fill="#2B2D42">portfolio · market-data · momentum</text>
    <text x="195" y="290" font-size="11" fill="#2B2D42">analytics · cost-analysis · capa2</text>
    <rect x="395" y="212" width="340" height="86" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="565" y="238" font-size="13.5" font-weight="bold" fill="#2B2D42">Key needed — the writes</text>
    <text x="565" y="258" font-size="11" fill="#2B2D42">strategies · optimization writes</text>
    <text x="565" y="274" font-size="11" fill="#2B2D42">live orders · feeds · rebalance</text>
    <text x="565" y="290" font-size="11" fill="#2B2D42">paper trades · breaker reset</text>
  </g>
</svg>

## Root and health

- `GET /` — app name, version, links to docs. Auth: public.
- `GET /health`, `GET /health/detailed` — the checks (database, broker, memory, positions); same plus platform detail. Auth: public.

## `/capa2` — investor profiling

- `POST /process-input`, `POST /generate-profile`, `POST /parametrize-modules` — validate input, build the profile, apply it to modules. Auth: public.
- `POST /execute-backtest`, `GET /backtest-status/{job_id}`, `POST /complete-workflow`, `GET /workflow-status/{workflow_id}` — start a backtest or the whole workflow; poll it. Auth: public.
- `GET /health`, `GET /status/jobs` — service health; summary of all jobs. Auth: public.

## `/portfolio` — positions and breakers

- `GET /` — portfolio summary, breaker states included. Auth: public.
- `GET /positions`, `GET /positions/{symbol}` — every position, or one by symbol. Auth: public.
- `GET /asset-universe`, `GET /market-regime/{symbol}` — supported assets; regime data for one symbol. Auth: public.
- `POST /simulate-trade`, `GET /circuit-breakers`, `POST /circuit-breakers/{name}/reset`, `GET /health` — simulate a trade, no money moves; breaker states, reset one; health. Auth: public.

## `/signals` — the signal queue

- `POST /evaluate`, `GET /next`, `POST /execute/{signal_id}` — score a signal, fetch the best one, execute it. Auth: public.
- `GET /statistics`, `GET /symbol/{symbol}`, `GET /health` — processing stats; signals per symbol; health. Auth: public.
- `POST /clear-expired`, `POST /thresholds`, `POST /position-size-limit` — drop old signals; retune thresholds; cap position size. Auth: public.

## `/strategies` — load and run

- `GET /`, `GET /available`, `GET /loaded` — overview; names you can load; names loaded now. Auth: key, role admin or user.
- `POST /load`, `POST /activate`, `POST /deactivate`, `DELETE /unload/{strategy_name}` — load a strategy, switch it on or off, drop it. Auth: key, role admin.
- `GET /{strategy_name}`, `GET /{strategy_name}/metrics` — one strategy's details and its metrics. Auth: key, role admin or user.
- `PUT /{strategy_name}/parameters` — change its parameters. Auth: key, role admin.
- `POST /execution/start`, `POST /execution/stop`, `POST /execution/reset-stats` — run, halt, reset the engine. Auth: key, role admin.
- `GET /metrics/all`, `GET /execution/stats` — metrics for all strategies; engine counters. Auth: public.

## `/momentum` — momentum analysis

- `GET /`, `GET /indicators/{symbol}` — overview of the system; indicators for one symbol. Auth: public.
- `POST /analyze`, `POST /analyze/batch`, `GET /analyze/{symbol}` — analyze one symbol or many; read one back. Auth: public.
- `GET /signals`, `GET /signals/top`, `GET /signals/{symbol}` — current signals; top picks; one symbol. Auth: public.
- `POST /strategies`, `GET /strategies` — create a momentum config; list them. Auth: public.
- `GET /strategies/{strategy_name}`, `PUT /strategies/{strategy_name}`, `DELETE /strategies/{strategy_name}`, `GET /strategies/{strategy_name}/signals` — read, update, delete one config; its signals. Auth: public.
- `GET /analyses`, `GET /analyses/{analysis_id}`, `DELETE /analyses/{analysis_id}`, `GET /health`, `GET /stats` — stored analyses: list, read, delete; health; counters. Auth: public.

## `/assets` — the asset universe

- `GET /` — overview of every universe. Auth: public.
- `GET /{symbol}`, `GET /{symbol}/liquidity` — one asset's details; its liquidity metrics. Auth: public.
- `GET /liquid/{asset_class}`, `GET /rankings`, `GET /rankings/{asset_class}` — most liquid per class; rankings, overall or per class. Auth: public.
- `POST /filter`, `POST /filter/{asset_class}` — filter assets by your criteria. Auth: public.
- `GET /universe`, `GET /universe/{asset_class}`, `GET /classes`, `GET /exchanges` — the universe; per class; classes; exchanges. Auth: public.
- `POST /refresh-liquidity`, `POST /identify/{asset_class}`, `GET /health`, `GET /stats` — recompute liquidity; rebuild a class; health; stats. Auth: public.

## `/market-data` — quotes and feeds

- `GET /quotes`, `GET /quotes/top-liquid`, `GET /quotes/{symbol}` — quotes: many, the top set, one. Auth: public.
- `GET /historical/{symbol}` — bars between two dates you choose. Auth: public.
- `POST /feeds` — create a data feed config. Auth: key, role admin.
- `GET /feeds`, `GET /feeds/{config_id}` — list configs; read one. Auth: public.
- `POST /feeds/{config_id}/connect`, `POST /feeds/{config_id}/disconnect` — connect a feed; cut it off. Auth: public.
- `POST /subscribe`, `GET /status`, `POST /cache/clear`, `GET /cache/stats` — live subscriptions; service status; cache clear and stats. Auth: public.

## `/paper-trading` — fake-money books

- `POST /portfolios` — create a paper portfolio. Auth: key.
- `GET /portfolios`, `GET /portfolios/{portfolio_id}` — list portfolios; read one. Auth: public.
- `POST /sessions`, `GET /sessions`, `GET /sessions/{session_id}`, `POST /sessions/{session_id}/close` — create, list, read, close a session. Auth: public.
- `POST /portfolios/{portfolio_id}/trades` — record a paper trade. Auth: key, role admin or trader.
- `GET /portfolios/{portfolio_id}/trades`, `GET /trades/{trade_id}` — a portfolio's trades; one trade. Auth: public.
- `GET /portfolios/{portfolio_id}/positions`, `GET /portfolios/{portfolio_id}/positions/{symbol}` — positions, all or one. Auth: public.
- `POST /market/update`, `GET /configs`, `GET /configs/{config_id}`, `GET /portfolios/{portfolio_id}/stats`, `GET /health` — refresh prices; configs; portfolio stats; health. Auth: public.

## `/portfolio-analytics` — performance math

- `POST /performance-metrics` — compute performance from returns you send. Auth: key.
- `GET /performance-metrics/{portfolio_id}`, `GET /risk-metrics/{portfolio_id}` — stored performance; risk metrics. Auth: public.
- `GET /analytics/{portfolio_id}`, `GET /allocation/{portfolio_id}`, `GET /summary/{portfolio_id}`, `GET /health-check`, `POST /compare` — full bundle; allocation; summary; health; compare portfolios. Auth: public.
- `POST /rebalance` — get a rebalancing plan. Auth: key, role admin or trader.

## `/cost-analysis` — fees and slippage

- `POST /analyze-trade`, `POST /analyze-strategy` — cost of one trade; of a whole strategy. Auth: public.
- `POST /validate-profitability` — does the strategy clear its costs? Auth: public.
- `GET /cost-parameters`, `POST /cost-parameters`, `GET /cost-breakdown/{trade_id}`, `GET /strategy-costs/{strategy_name}` — read or update fees; one trade's breakdown; costs per strategy. Auth: public.

## `/optimization` — parameter search

- `POST /optimize-parameters` — search for the best parameters. Auth: key, role admin or trader.
- `POST /out-of-sample-test`, `POST /validate-config` — test on unseen data; check a config. Auth: key in production, public in debug.
- `GET /artifacts`, `GET /artifacts/{artifact_id}`, `GET /artifacts/{artifact_id}/metrics` — saved runs; one run; its metrics. Auth: public.
- `DELETE /artifacts/{artifact_id}` — delete a run. Auth: key, role admin.
- `GET /summary`, `GET /methods`, `GET /parameter-types` — summary; supported methods and types. Auth: public.
- `GET /strategies/{strategy_name}/best-parameters`, `GET /health` — best parameters so far; health. Auth: public.

## `/live-trading` — the real-money bridge

- `POST /start`, `POST /stop`, `GET /status` — start or stop the bridge; read its state. Auth: key for start and stop.
- `POST /orders` — place an order. Auth: key.
- `GET /orders`, `GET /orders/{order_id}` — list orders; read one. Auth: public.
- `DELETE /orders/{order_id}`, `POST /orders/cancel-all` — cancel one order; cancel all. Auth: key.
- `GET /account`, `GET /positions`, `GET /positions/{symbol}` — account and balance; positions, all or one. Auth: public.
- `POST /risk/validate`, `GET /risk/limits`, `PATCH /risk/limits` — check a trade against the limits; read or change them. Auth: public to read, key for the rest.
- `GET /executions`, `GET /executions/{execution_id}`, `GET /audit/trail`, `GET /audit/report`, `GET /audit/non-compliant`, `GET /audit/statistics` — fills, list or one; the audit box: trail, report, violations, stats. Auth: public.
- `GET /statistics`, `GET /signals/pending`, `GET /signals/statistics` — trading stats; unexecuted signals and their counts. Auth: public.
- `GET /portfolio/snapshot`, `GET /portfolio/history`, `GET /portfolio/daily-return` — snapshot; value history; today's return. Auth: public.
- `POST /rules`, `DELETE /rules/{rule_id}` — add or remove an alert-to-trade rule. Auth: key.

## `/trading-error-handler` — errors and breakers

- `POST /handle-error` — run one error through the rules. Auth: public.
- `GET /statistics`, `GET /health`, `GET /circuit-breakers` — error counts, breakers, retries; breaker state per context. Auth: public.
- `POST /circuit-breakers/reset` — reset one breaker. Auth: key, role admin.
- `GET /contexts`, `GET /actions`, `GET /rules/{context}` — valid contexts; valid actions; rules per context. Auth: public.

## Interactive docs

FastAPI builds the endpoint list for you. Open `http://localhost:8000/docs` for Swagger UI: click a route, fill the boxes, try it. `/redoc` and `/openapi.json` give the same list in other shapes. The dashboard is a separate NiceGUI app, not this one — see [the dashboard page](11-dashboard.md).

## Where it lives in the code

- `app/main.py` — creates the app, adds the middleware, includes all 14 routers.
- `app/presentation/api/` — one file per router: `strategies.py`, `live_trading.py`, `market_data.py`, and the rest.
- `app/api/cost_analysis.py` — the cost router, the only one outside `presentation/`.
- `app/presentation/api/middleware.py` — the outer gate: which paths it guards, which headers it reads.
- `app/presentation/api/security.py` — the `@require_auth` decorator, its key checks and role checks.
- `app/presentation/api/deployment.py` — a guarded router that `main.py` never includes, so it sleeps.

## Want to go deeper?

- [Security](10-security.md) — keys, roles and lockouts: the guards behind this gate.
- [How the system works](01-how-the-system-works.md) — where the API sits in the layer cake.
- [The dashboard](11-dashboard.md) — the other face of the system, with the docs site inside it.
