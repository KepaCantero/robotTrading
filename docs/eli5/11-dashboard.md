# The backtesting dashboard

## The short version

The dashboard is a small web app that rides on top of your backtests. NiceGUI (a Python library that turns plain functions into web pages) draws every screen. You pick a strategy, run a test, and read the verdict — no terminal needed.

## The shell and its drawer

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 356" role="img" aria-label="AppShell holds the drawer and the routed content; five shared services sit behind it">
  <defs>
    <marker id="arrowDash" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="354" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="90" y="20" width="580" height="230" rx="14" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="46" font-size="15" font-weight="bold" fill="#2B2D42">AppShell — layout &amp; routes</text>
    <rect x="110" y="80" width="250" height="158" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="235" y="100" font-size="11" fill="#FFFFFF">Backtest Runner — /</text>
    <text x="235" y="116" font-size="11" fill="#FFFFFF">Results — /results</text>
    <text x="235" y="132" font-size="11" fill="#FFFFFF">History &amp; Compare — /history</text>
    <text x="235" y="148" font-size="11" fill="#FFFFFF">Objectives — /objectives</text>
    <text x="235" y="164" font-size="11" fill="#FFFFFF">Config Viewer — /config</text>
    <text x="235" y="180" font-size="11" fill="#FFFFFF">Profitability — /profitability</text>
    <text x="235" y="196" font-size="11" fill="#FFFFFF">Agent Swarm — /swarm</text>
    <text x="235" y="212" font-size="11" fill="#FFFFFF">Documentation — /docs/</text>
    <rect x="380" y="80" width="270" height="158" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="515" y="163" font-size="12" font-weight="bold" fill="#2B2D42">one render() per route</text>
    <line x1="515" y1="250" x2="515" y2="282" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowDash)"/>
    <rect x="15" y="286" width="138" height="48" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="84" y="314" font-size="11" font-weight="bold" fill="#2B2D42">BacktestResultStore</text>
    <rect x="163" y="286" width="138" height="48" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="232" y="314" font-size="11" font-weight="bold" fill="#2B2D42">BacktestRunner</text>
    <rect x="311" y="286" width="138" height="48" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="314" font-size="11" font-weight="bold" fill="#2B2D42">ProfitabilityEngine</text>
    <rect x="459" y="286" width="138" height="48" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="528" y="314" font-size="11" font-weight="bold" fill="#2B2D42">Capa2PipelineExecutor</text>
    <rect x="607" y="286" width="138" height="48" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="676" y="314" font-size="11" font-weight="bold" fill="#2B2D42">SwarmRunStore</text>
  </g>
</svg>

`create_app()` builds five shared services and injects them into `AppShell`. The shell draws the drawer, the header, and one route per page. The drawer isn't hardcoded — it's built from the `PAGES` list in `theme.py`, so navigation and routes can't drift apart. Each page module exposes a `render()` function and takes only the services it needs.

## What happens when you open a page

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 410" role="img" aria-label="A page visit flows from the browser through a ui.page route and a service to SQLite, then the answer returns">
  <defs>
    <marker id="arrowFlow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="408" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <line x1="62" y1="90" x2="62" y2="360" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowFlow)"/>
    <text x="46" y="225" font-size="12" fill="#2B2D42" transform="rotate(-90 46 225)">your request goes down</text>
    <line x1="698" y1="360" x2="698" y2="90" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowFlow)"/>
    <text x="716" y="225" font-size="12" fill="#2B2D42" transform="rotate(90 716 225)">the answer comes back up</text>
    <rect x="160" y="30" width="440" height="70" rx="14" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="60" font-size="16" font-weight="bold" fill="#FFFFFF">Your browser</text>
    <text x="380" y="84" font-size="12.5" fill="#FFFFFF">asks for /results</text>
    <line x1="380" y1="100" x2="380" y2="118" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowFlow)"/>
    <rect x="160" y="122" width="440" height="70" rx="14" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="152" font-size="15" font-weight="bold" fill="#2B2D42">@ui.page route</text>
    <text x="380" y="176" font-size="12.5" fill="#2B2D42">the page's render() runs</text>
    <line x1="380" y1="192" x2="380" y2="210" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowFlow)"/>
    <rect x="160" y="214" width="440" height="70" rx="14" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="244" font-size="14" font-weight="bold" fill="#2B2D42">BacktestResultStore</text>
    <text x="380" y="268" font-size="12.5" fill="#2B2D42">fetches run records</text>
    <line x1="380" y1="284" x2="380" y2="302" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowFlow)"/>
    <rect x="160" y="306" width="440" height="70" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="336" font-size="13" font-weight="bold" fill="#FFFFFF">SQLite — backtest_results.db</text>
    <text x="380" y="360" font-size="12.5" fill="#FFFFFF">one row per backtest run</text>
  </g>
</svg>

NiceGUI turns each `@ui.page` function into a real URL. When your browser asks for `/results`, that function runs. It calls `BacktestResultStore`, which reads rows from SQLite (a database that's just one file on disk). When a backtest finishes, `BacktestRunner` saves one row to the same file. That's why the History page can compare runs from last week.

## The docs live inside it

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 190" role="img" aria-label="make dashboard builds the MkDocs site, then the app serves it at /docs">
  <defs>
    <marker id="arrowDocs" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="188" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="20" y="50" width="210" height="90" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="125" y="86" font-size="13" font-weight="bold" fill="#2B2D42">make dashboard</text>
    <text x="125" y="110" font-size="11" fill="#2B2D42">docs first, then the app</text>
    <line x1="230" y1="95" x2="258" y2="95" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowDocs)"/>
    <rect x="262" y="50" width="210" height="90" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="367" y="86" font-size="13" font-weight="bold" fill="#2B2D42">site/</text>
    <text x="367" y="110" font-size="11" fill="#2B2D42">MkDocs static HTML</text>
    <line x1="472" y1="95" x2="500" y2="95" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowDocs)"/>
    <rect x="504" y="50" width="236" height="90" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="622" y="80" font-size="12.5" font-weight="bold" fill="#FFFFFF">dashboard mounts /docs/</text>
    <text x="622" y="103" font-size="11" fill="#FFFFFF">Starlette StaticFiles</text>
    <text x="622" y="121" font-size="11" fill="#FFFFFF">serves the files as-is</text>
  </g>
</svg>

`make dashboard` runs `mkdocs build` before it starts the app. MkDocs turns the markdown in `docs/` into static HTML (files that need no server code) under `site/`. The dashboard mounts that folder at `/docs/`, and `html=True` makes `/docs/` open the index page. So this very page ships inside the app at `http://localhost:8503/docs/`. Skip the build and you still get a page — it just tells you to run `make docs-build`.

## Where it lives in the code

- `app/presentation/dashboard/nicegui_app/app.py` — `create_app()`: builds the services, injects them, mounts `/docs`.
- `app/presentation/dashboard/nicegui_app/layout.py` — `AppShell`: the drawer (from the `PAGES` list in `theme.py`) and every `@ui.page` route.
- `app/presentation/dashboard/nicegui_app/pages/` — one `render()` module per page.
- `app/presentation/dashboard/nicegui_app/__main__.py` — `ui.run()`; the port comes from the `DASHBOARD_PORT` env variable, 8503 by default.
- `Makefile` — `make dashboard`: docs build first, then the app, on port 8503.
- `scripts/start_paper_trading.sh` — starts the same app beside paper trading, with `DASHBOARD_PORT=8501`.

## Want to go deeper?

- [Backtesting](09-backtesting.md) — what the runner actually computes.
- [The folder map](03-folder-map.md) — where everything else in `app/` lives.
- [How the system works](01-how-the-system-works.md) — the big picture, layer by layer.
