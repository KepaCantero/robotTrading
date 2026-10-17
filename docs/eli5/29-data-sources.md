# The catalog of data sources

## The short version

This page is the reference sheet: every well the robot can drink from, and what each one costs you. Page 4 explains the pipeline itself; this page lists the sources it draws on. Each entry gets a role: primary, fallback, or offline.

## The source map

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 560" role="img" aria-label="Diagram: market APIs, mood feeds, offline CSVs and Yahoo flow into the Data Engine and Data Loader, which feed strategies, backtests and the dashboard">
  <defs>
    <marker id="s29arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker>
  </defs>
  <rect x="1" y="1" width="758" height="558" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="30" y="40" width="200" height="110" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="130" y="70" font-size="15" font-weight="bold" fill="#FFFFFF">Market data APIs</text>
    <text x="130" y="95" font-size="11.5" fill="#FFFFFF">1 Polygon · 2 Alpaca</text>
    <text x="130" y="115" font-size="11.5" fill="#FFFFFF">3 Binance · 4 IBKR</text>
    <text x="130" y="137" font-size="10.5" fill="#FFFFFF">try in this order</text>
    <rect x="30" y="170" width="200" height="110" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="130" y="200" font-size="15" font-weight="bold" fill="#FFFFFF">News &amp; mood feeds</text>
    <text x="130" y="225" font-size="11.5" fill="#FFFFFF">Twitter · Reddit</text>
    <text x="130" y="245" font-size="11.5" fill="#FFFFFF">NewsAPI · Marketaux</text>
    <text x="130" y="265" font-size="11.5" fill="#FFFFFF">· Alpha Vantage</text>
    <rect x="30" y="300" width="200" height="100" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="130" y="330" font-size="15" font-weight="bold" fill="#FFFFFF">Offline CSVs</text>
    <text x="130" y="355" font-size="11.5" fill="#FFFFFF">Stooq daily files</text>
    <text x="130" y="375" font-size="11.5" fill="#FFFFFF">data/historical/</text>
    <rect x="30" y="420" width="200" height="90" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="130" y="450" font-size="15" font-weight="bold" fill="#FFFFFF">Yahoo Finance</text>
    <text x="130" y="475" font-size="11.5" fill="#FFFFFF">free, no key</text>
    <text x="130" y="495" font-size="11.5" fill="#FFFFFF">backtest fallback</text>
    <rect x="300" y="40" width="200" height="240" rx="14" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="400" y="75" font-size="17" font-weight="bold" fill="#2B2D42">Data Engine</text>
    <text x="400" y="97" font-size="11.5" fill="#2B2D42">app/engines/data_engine</text>
    <rect x="315" y="125" width="170" height="110" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="400" y="155" font-size="12" fill="#2B2D42">picks first source</text>
    <text x="400" y="180" font-size="12" fill="#2B2D42">normalize · clean</text>
    <text x="400" y="205" font-size="12" fill="#2B2D42">cache · stream</text>
    <rect x="300" y="330" width="200" height="110" rx="14" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="400" y="365" font-size="16" font-weight="bold" fill="#2B2D42">Data Loader</text>
    <text x="400" y="390" font-size="11.5" fill="#2B2D42">CSV first, then Yahoo</text>
    <text x="400" y="412" font-size="11.5" fill="#2B2D42">Quote objects out</text>
    <rect x="570" y="140" width="160" height="180" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="650" y="190" font-size="14" font-weight="bold" fill="#FFFFFF">Strategies</text>
    <text x="650" y="220" font-size="14" font-weight="bold" fill="#FFFFFF">Backtests</text>
    <text x="650" y="250" font-size="14" font-weight="bold" fill="#FFFFFF">Dashboard</text>
    <text x="650" y="285" font-size="11" fill="#FFFFFF">eat the clean rows</text>
    <line x1="232" y1="95" x2="286" y2="115" stroke="#2B2D42" stroke-width="2" marker-end="url(#s29arrow)"/>
    <line x1="232" y1="225" x2="286" y2="205" stroke="#2B2D42" stroke-width="2" marker-end="url(#s29arrow)"/>
    <line x1="232" y1="350" x2="286" y2="365" stroke="#2B2D42" stroke-width="2" marker-end="url(#s29arrow)"/>
    <line x1="232" y1="465" x2="286" y2="410" stroke="#2B2D42" stroke-width="2" marker-end="url(#s29arrow)"/>
    <line x1="500" y1="150" x2="556" y2="190" stroke="#2B2D42" stroke-width="2" marker-end="url(#s29arrow)"/>
    <line x1="500" y1="385" x2="556" y2="270" stroke="#2B2D42" stroke-width="2" marker-end="url(#s29arrow)"/>
  </g>
</svg>

Coral is the outside world, mint picks and shapes, white loads files, grape is where data lands. The numbers on the market box are the engine's fallback order.

## Polygon

- Gives you OHLCV bars (open, high, low, close, volume) for stocks, plus option chains on the same key.
- Env var: `POLYGON_API_KEY`, from polygon.io. Paid plans; the free tier is delayed.
- Limits: one call asks for up to 50,000 bars, though the YAML config mentions 10,000.
- Role: primary. First in the engine's chain, and the only wired options provider.
- One gap: the date-range wiring is half-built. The code computes the range, then drops it.

## Alpaca

- Gives you daily or intraday stock bars from the `/v2/stocks/{symbol}/bars` endpoint.
- Env vars: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_BASE_URL` (paper URL by default).
- Limits: up to 10,000 bars per call.
- Role: fallback, second in the chain. The same keys also run paper trading, so you likely have them.

## Binance

- Gives you crypto candles — BTCUSDT and friends — from the public `/api/v3/klines` endpoint.
- Env vars: none. The public API needs no key at all.
- Limits: 1,000 candles per call; the config can page through more.
- Role: fallback for crypto, third in the chain. No stock data lives here.

## IBKR (Interactive Brokers)

- Gives you bars and live prices straight from your broker, through TWS or IB Gateway (their desktop apps).
- Env vars: `IB_HOST`, `IB_PORT` (`7497` paper, `7496` live), `IB_CLIENT_ID`, `IB_ACCOUNT`.
- Limits: no internet API key — instead you need their app running and logged in.
- Role: fallback, last in the chain. It's also the road to real trading; page 12 covers it.

## Alpha Vantage

- Gives you company fundamentals plus a news feed with sentiment scores already computed.
- Env var: `ALPHA_VANTAGE_API_KEY`. The free tier exists but throttles you hard.
- Role: real today, on two roads — a fundamentals source and one of three news providers.
- Heads-up: `docs/developer/DATA_SOURCES.md` still lists this as "future". That's stale; the code is live.

## Financial Modeling Prep

- Gives you company profiles, income statements, balance sheets, and ratios like P/E.
- Env var: `FMP_API_KEY`, from financialmodelingprep.com.
- Role: primary for fundamentals. Connecting fails fast when the key is missing.
- Alpha Vantage covers the same ground as its backup.

## Stooq CSVs and Yahoo Finance

- Stooq is a free price-history site. The repo keeps seven of its daily OHLCV files in `data/historical/`: AAPL, AMZN, GOOGL, META, MSFT, NVDA, TSLA.
- No env var, no network. This is the offline road, and backtests live on it. Some files reach back to 1984.
- Stooq is provenance (where the files came from), not code — no script here re-downloads them.
- Yahoo is the live backup: `YAHOO_FINANCE_ENABLED=True`, no key, free, delayed 15 minutes.
- The `DataLoader` tries three Yahoo roads in order: the v8 chart API direct, the `yfinance` library, then `yahoo_fin`.

## Twitter (X)

- Gives you a mood score from recent tweets that mention your symbol.
- Env var: `TWITTER_BEARER_TOKEN`. It only works through the optional `tweepy` library.
- Limits: 100 tweets per search, and only the first 10 get scored.
- Honest bit: scoring is keyword matching — "moon" counts as good, "crash" as bad. The direct API path is not implemented.

## Reddit

- Gives you a mood score from posts in r/wallstreetbets, r/stocks and r/investing.
- Env vars: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`. Public reads work without them.
- Limits: 25 posts per request and 50 total by default; ten get sampled for the score.
- Honest bit: same crude keyword scoring as Twitter.

## News APIs: NewsAPI and Marketaux

- One class, three providers picked by config: NewsAPI (the default), Marketaux, Alpha Vantage.
- Env vars: `NEWS_API_KEY`, `MARKETAUX_API_KEY` — Alpha Vantage reuses its own key.
- Marketaux is the fancy one: sentiment arrives pre-scored, in English and Spanish, weighted by match strength.
- Limits: up to 100 articles per call; ten titles get sampled for the local score.

## Options and FX extras

- `OptionsVolatilitySource` pulls option chains (strikes, implied volatility, Greeks) from Polygon's snapshot endpoint.
- Its IBKR branch just logs "not implemented yet" and returns — a stub, not a source.
- The forex risk tracker reads official exchange rates from the ECB and Banco de España.

## Fallback order

The verified chain in `data_engine.py` is: **polygon → alpaca → binance → ibkr**. The engine takes the first one present in your config. It doesn't retry the next on failure — a failed call just returns an empty list.

Backtests run their own chain: the CSV file first, then the three Yahoo roads. Fundamentals take whoever's configured, FMP or Alpha Vantage. Sentiment is different: it fans out to every configured feed at once, then merges the scores.

## Where it lives

- `app/engines/data_engine/sources/ohlcv_sources.py` — Polygon, Alpaca, Binance, IBKR, plus an unused Yahoo class.
- `app/engines/data_engine/sources/fundamental_sources.py` — FMP and Alpha Vantage fundamentals.
- `app/engines/data_engine/sources/sentiment_sources.py` — Twitter, Reddit, and the news providers.
- `app/engines/data_engine/sources/options_sources.py` — Polygon option chains and the IBKR stub.
- `app/engines/data_engine/data_engine.py` — the fallback list and the fan-out logic.
- `app/backtesting/data_loader.py` — the CSV and Yahoo roads, `Quote` objects out.
- `config/market/data_engine.yaml` — per-source limits and defaults.
- `.env.example` — every key name, with where to get each one.
- `data/historical/` — the seven Stooq CSVs.

## Want to go deeper?

- [The data pipeline](04-data-pipeline.md) — how these sources feed one engine.
- [The IBKR connection](12-ibkr.md) — the broker feed in detail.
- [The config atlas](24-config-atlas.md) — every knob, including these.
