# The Interactive Brokers connection

## The short version

Interactive Brokers (IBKR) is the outside broker this repo can talk to. Your code never calls IBKR's servers directly — it opens a local socket to TWS or IB Gateway, the desktop app you log into. The price-feed code is real and working. The order code exists too, but it isn't wired into live trading yet.

## The road to IBKR

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 352" role="img" aria-label="Diagram: the app calls ib_insync, which connects to TWS or IB Gateway on local ports, which talks to IBKR servers">
  <defs>
    <marker id="arrowIb1" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="350" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="140" y="24" width="480" height="62" rx="14" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="53" font-size="16" font-weight="bold" fill="#FFFFFF">Your app</text>
    <line x1="380" y1="88" x2="380" y2="106" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowIb1)"/>
    <rect x="140" y="110" width="480" height="62" rx="14" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="136" font-size="16" font-weight="bold" fill="#2B2D42">ib_insync library</text>
    <text x="380" y="157" font-size="12.5" fill="#2B2D42">one socket · one client id</text>
    <line x1="380" y1="174" x2="380" y2="192" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowIb1)"/>
    <rect x="110" y="196" width="540" height="76" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="222" font-size="16" font-weight="bold" fill="#FFFFFF">TWS or IB Gateway</text>
    <text x="380" y="243" font-size="12.5" fill="#FFFFFF">TWS: 7497 paper · 7496 live</text>
    <text x="380" y="261" font-size="12.5" fill="#FFFFFF">Gateway: 4001 paper</text>
    <line x1="380" y1="274" x2="380" y2="292" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowIb1)"/>
    <rect x="200" y="296" width="360" height="42" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="322" font-size="15" font-weight="bold" fill="#FFFFFF">IBKR servers</text>
  </g>
</svg>

All traffic goes through one Python library: `ib_insync` (the repo pins `ib-insync>=0.9.86`). It speaks the TWS API, IBKR's protocol, over a TCP socket. But the socket stops on your machine. TWS (Trader Workstation) is IBKR's full trading desktop; IB Gateway is the stripped-down version that only relays traffic. You must run one of them, log in, and switch on its API — `docs/user/PAPER_TRADING.md` lists the clicks. Paper accounts use port 7497 with TWS, or 4001 with IB Gateway; live accounts use 7496. The desktop app then carries every request to IBKR's servers. If it isn't running, connect fails — that's the number one gotcha.

## Where the settings come from

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 322" role="img" aria-label="Diagram: env vars and YAML files feed the adapter rules, which end in an open socket">
  <defs>
    <marker id="arrowIb2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="320" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="40" y="24" width="330" height="76" rx="14" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="205" y="52" font-size="15" font-weight="bold" fill="#FFFFFF">.env file</text>
    <text x="205" y="74" font-size="12" fill="#FFFFFF">IB_HOST · IB_PORT · IB_CLIENT_ID</text>
    <rect x="390" y="24" width="330" height="76" rx="14" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="555" y="52" font-size="15" font-weight="bold" fill="#2B2D42">YAML files</text>
    <text x="555" y="74" font-size="12" fill="#2B2D42">data_engine.yaml · user_config.yaml</text>
    <line x1="205" y1="102" x2="330" y2="136" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowIb2)"/>
    <line x1="555" y1="102" x2="430" y2="136" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowIb2)"/>
    <rect x="140" y="140" width="480" height="76" rx="14" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="166" font-size="15" font-weight="bold" fill="#2B2D42">Adapter rules</text>
    <text x="380" y="187" font-size="12" fill="#2B2D42">host · port · client id</text>
    <line x1="380" y1="218" x2="380" y2="240" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowIb2)"/>
    <rect x="200" y="244" width="360" height="56" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="268" font-size="15" font-weight="bold" fill="#FFFFFF">Socket opens</text>
    <text x="380" y="288" font-size="12.5" fill="#FFFFFF">to TWS or IB Gateway</text>
  </g>
</svg>

Settings live in two places. The adapters read the environment variables first — those win. The YAML files feed the data engine and the user settings instead. On a broken link, the adapters retry up to ten times, doubling the wait from 1 s to 60 s.

The real names, with their defaults:

- `IB_HOST` — where TWS or IB Gateway listens. Default `127.0.0.1`, your own machine.
- `IB_PORT` — the socket port. Default `7497`, TWS paper. Live TWS uses `7496`.
- `IB_CLIENT_ID` — a number that keeps two of your scripts from fighting. Default `1`.
- `IB_ACCOUNT`, `IB_PAPER_TRADING` — account code (the example is `DU9811225`) and the paper flag, `True` by default.
- `TIMEOUT_IB_CONNECT`, `TIMEOUT_IB_READ` — give up after 15 and 30 seconds.
- `config/market/data_engine.yaml`, key `ibkr:` — ports `7497`/`7496`, client id, bar size `1 day`.
- `config/user_config.yaml`, key `broker_settings:` — `ibkr_host`, `ibkr_port: 4001`, `ibkr_client_id`; `broker_type` defaults to `paper`.

## What comes back

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 780 200" role="img" aria-label="Diagram: TWS returns OHLCV bars, IBKRSource makes dicts, the DataEngine cleans them, strategies and backtests use them">
  <defs>
    <marker id="arrowIb3" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="778" height="198" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="20" y="60" width="185" height="96" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="112" y="88" font-size="14" font-weight="bold" fill="#FFFFFF">TWS / Gateway</text>
    <text x="112" y="112" font-size="12" fill="#FFFFFF">returns OHLCV bars</text>
    <line x1="207" y1="108" x2="223" y2="108" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowIb3)"/>
    <rect x="225" y="60" width="165" height="96" rx="14" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="307" y="88" font-size="14" font-weight="bold" fill="#FFFFFF">IBKRSource</text>
    <text x="307" y="110" font-size="12" fill="#FFFFFF">bars become dicts</text>
    <line x1="392" y1="108" x2="408" y2="108" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowIb3)"/>
    <rect x="410" y="60" width="165" height="96" rx="14" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="492" y="88" font-size="14" font-weight="bold" fill="#2B2D42">DataEngine</text>
    <text x="492" y="112" font-size="12" fill="#2B2D42">cache · clean · UTC</text>
    <line x1="577" y1="108" x2="593" y2="108" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowIb3)"/>
    <rect x="595" y="60" width="165" height="96" rx="14" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="677" y="88" font-size="14" font-weight="bold" fill="#FFFFFF">Who uses it</text>
    <text x="677" y="110" font-size="12" fill="#FFFFFF">strategies · backtests</text>
    <text x="677" y="130" font-size="12" fill="#FFFFFF">dashboard · API</text>
  </g>
</svg>

You ask for a symbol, a date range and a bar size, from `1 min` up to `1 day`. IBKR answers with OHLCV bars: open, high, low, close and volume for each slice of time. `IBKRSource` wraps every bar in a dict of `Decimal` numbers, so float noise can't touch your prices. The DataEngine checks its cache first (Redis or PostgreSQL), fills gaps, drops outliers and normalizes timestamps to UTC. Then strategies, backtests and the API read the clean rows. Two limits: the source only requests US stocks in USD through SMART, IBKR's route across exchanges. And `useRTH=True` means regular trading hours only — no pre-market bars.

## What the app does with it

On the data side, IBKR is one feed among four. If you don't name a source, the engine tries Polygon, then Alpaca, then Binance, then IBKR — the last resort. It's also opt-in: the engine only builds `IBKRSource` when your config has an `ibkr` block under `sources.ohlcv`, and the shipped yaml doesn't. On the order side there's real code but no wiring. `IBKRSpainAdapter` places market, limit and stop orders, cancels them, and reads your account — in EUR, with IBEX 35 contracts. Only the unit tests call it today. `BrokerConnector`, the class that picks your live broker, throws an error if you ask for IBKR: it refuses to fall back to paper quietly. So live orders go through paper or Alpaca, and backtests use `config/brokers/interactive_brokers.yaml` as a pure cost model — commissions, fees, spreads, slippage.

## What's real and what isn't

- Real: the historical-bars feed. Connect, download, convert — it works once TWS or IB Gateway runs with the API on.
- Real but idle: both order adapters, tested yet unreached. The older `ib_adapter.py` even streams live quotes with a five-second cache.
- Refused on purpose: `BrokerConnector` plus IBKR raises an error instead of quietly trading paper. Fail-closed by design.
- Stub: the options source logs "requires TWS, not implemented yet" and stays offline; the backtest loader names `ibkr` but rejects it too.
- Config ahead of code: `production.yaml` calls IBKR the primary broker. The connector doesn't agree yet.

## Where it lives in the code

- `app/engines/data_engine/sources/ohlcv_sources.py` — `IBKRSource`, the historical-bars feed.
- `app/engines/data_engine/data_engine.py` and `config_loader.py` — source registration, fallback order, port defaults.
- `app/services/live_trading/broker_adapters/ibkr_adapter_spain.py` and `ibex35_contracts.py` — orders and account, EUR, IBEX 35.
- `app/services/live_trading/broker_adapters/ib_adapter.py` — the older adapter, with live quotes.
- `app/services/live_trading/broker_connector.py` — picks your broker; refuses IBKR for now.
- `config/market/data_engine.yaml`, `config/user_config.yaml`, `config/brokers/interactive_brokers.yaml` — engine ports, user settings, backtest costs. TWS setup steps live in `docs/user/PAPER_TRADING.md`.

## Want to go deeper?

Next stops: [the data pipeline](04-data-pipeline.md), [execution](07-execution.md), and [the life of a trade](02-life-of-a-trade.md).
