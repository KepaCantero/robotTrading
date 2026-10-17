# The market data pipeline

## The short version

Nothing in this system can think until it has prices. Old prices arrive as CSV files on disk; fresh ones arrive from live market APIs. Both roads end in clean, tidy rows that strategies, backtests and the dashboard can trust.

## Where the data comes from

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 420" role="img" aria-label="Diagram: market APIs, news feeds and historical CSVs flow through the Data Engine and the Data Loader to strategies, backtests and the dashboard">
  <defs>
    <marker id="d1arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker>
  </defs>
  <rect x="1" y="1" width="758" height="418" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="30" y="60" width="190" height="90" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="125" y="95" font-size="15" font-weight="bold" fill="#FFFFFF">Market APIs</text>
    <text x="125" y="118" font-size="11.5" fill="#FFFFFF">Polygon · Alpaca ·</text>
    <text x="125" y="136" font-size="11.5" fill="#FFFFFF">Binance · IBKR</text>
    <rect x="30" y="170" width="190" height="90" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="125" y="205" font-size="15" font-weight="bold" fill="#FFFFFF">News &amp; social</text>
    <text x="125" y="228" font-size="11.5" fill="#FFFFFF">news · reddit · twitter</text>
    <rect x="30" y="280" width="190" height="90" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="125" y="315" font-size="15" font-weight="bold" fill="#FFFFFF">Historical CSVs</text>
    <text x="125" y="338" font-size="11.5" fill="#FFFFFF">data/historical/*.csv</text>
    <rect x="290" y="50" width="200" height="230" rx="14" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="390" y="85" font-size="17" font-weight="bold" fill="#2B2D42">Data Engine</text>
    <text x="390" y="107" font-size="11.5" fill="#2B2D42">app/engines/data_engine</text>
    <rect x="305" y="125" width="170" height="110" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="390" y="155" font-size="12" fill="#2B2D42">sources · normalizer</text>
    <text x="390" y="180" font-size="12" fill="#2B2D42">cleaning · cache</text>
    <text x="390" y="205" font-size="12" fill="#2B2D42">streaming · versioning</text>
    <rect x="290" y="280" width="200" height="90" rx="14" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="390" y="315" font-size="16" font-weight="bold" fill="#2B2D42">Data Loader</text>
    <text x="390" y="338" font-size="11.5" fill="#2B2D42">app/backtesting/data_loader.py</text>
    <rect x="560" y="110" width="170" height="150" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="645" y="158" font-size="14" font-weight="bold" fill="#FFFFFF">Strategies</text>
    <text x="645" y="185" font-size="14" font-weight="bold" fill="#FFFFFF">Backtests</text>
    <text x="645" y="212" font-size="14" font-weight="bold" fill="#FFFFFF">Dashboard</text>
    <line x1="222" y1="105" x2="286" y2="112" stroke="#2B2D42" stroke-width="2" marker-end="url(#d1arrow)"/>
    <line x1="222" y1="215" x2="286" y2="205" stroke="#2B2D42" stroke-width="2" marker-end="url(#d1arrow)"/>
    <line x1="222" y1="325" x2="286" y2="325" stroke="#2B2D42" stroke-width="2" marker-end="url(#d1arrow)"/>
    <line x1="492" y1="160" x2="556" y2="170" stroke="#2B2D42" stroke-width="2" marker-end="url(#d1arrow)"/>
    <line x1="492" y1="322" x2="556" y2="240" stroke="#2B2D42" stroke-width="2" marker-end="url(#d1arrow)"/>
  </g>
</svg>

The coral boxes are the outside world. `data/historical/` holds one CSV per symbol with daily OHLCV rows — open, high, low, close and volume. Those files came from Stooq, a free price-history site. The other boxes are live feeds: Polygon, Alpaca, Binance and IBKR for prices, plus news, Reddit and Twitter for mood.

The mint box is the `DataEngine` class, the front door for live data. Call `get_ohlcv()` and it picks a source, normalizes, cleans and caches. Its settings come from `config/market/data_engine.yaml`, and it can also serve fundamentals, sentiment and option chains. The white box is the `DataLoader` class. Backtests use it: it reads a CSV if the file exists, or falls back to Yahoo Finance. Either way you get `Quote` objects — the standard price snapshot defined in `app/domain/models/market_data.py`. The grape box lists the buyers: strategies, backtests and the dashboard.

## The journey of one request

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 580" role="img" aria-label="Diagram: a data request flows through six numbered steps — request, cache check, fetch, normalize, clean, deliver — with a cache-hit shortcut from step two to step six">
  <defs>
    <marker id="d2arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker>
  </defs>
  <rect x="1" y="1" width="758" height="578" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="150" y="30" width="460" height="70" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="55" font-size="15" font-weight="bold" fill="#FFFFFF">A request arrives</text>
    <text x="380" y="78" font-size="11.5" fill="#FFFFFF">get_ohlcv(symbol, start, end)</text>
    <rect x="150" y="120" width="460" height="70" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="145" font-size="15" font-weight="bold" fill="#2B2D42">Check the cache first</text>
    <text x="380" y="168" font-size="11.5" fill="#2B2D42">DistributedCache: Redis, Postgres, memory</text>
    <rect x="150" y="210" width="460" height="70" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="235" font-size="15" font-weight="bold" fill="#FFFFFF">Fetch raw rows</text>
    <text x="380" y="258" font-size="11.5" fill="#FFFFFF">Polygon, Alpaca, Binance, or IBKR</text>
    <rect x="150" y="300" width="460" height="70" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="325" font-size="15" font-weight="bold" fill="#2B2D42">Normalize</text>
    <text x="380" y="348" font-size="11.5" fill="#2B2D42">UnifiedNormalizer — one common shape</text>
    <rect x="150" y="390" width="460" height="70" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="415" font-size="15" font-weight="bold" fill="#2B2D42">Clean and validate</text>
    <text x="380" y="438" font-size="11.5" fill="#2B2D42">outliers, gaps, quality score</text>
    <rect x="150" y="480" width="460" height="70" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="505" font-size="15" font-weight="bold" fill="#FFFFFF">Deliver</text>
    <text x="380" y="528" font-size="11.5" fill="#FFFFFF">clean rows, cached and streamed</text>
    <circle cx="150" cy="65" r="15" fill="#2B2D42"/>
    <text x="150" y="70" font-size="14" font-weight="bold" fill="#FFFFFF">1</text>
    <circle cx="150" cy="155" r="15" fill="#2B2D42"/>
    <text x="150" y="160" font-size="14" font-weight="bold" fill="#FFFFFF">2</text>
    <circle cx="150" cy="245" r="15" fill="#2B2D42"/>
    <text x="150" y="250" font-size="14" font-weight="bold" fill="#FFFFFF">3</text>
    <circle cx="150" cy="335" r="15" fill="#2B2D42"/>
    <text x="150" y="340" font-size="14" font-weight="bold" fill="#FFFFFF">4</text>
    <circle cx="150" cy="425" r="15" fill="#2B2D42"/>
    <text x="150" y="430" font-size="14" font-weight="bold" fill="#FFFFFF">5</text>
    <circle cx="150" cy="515" r="15" fill="#2B2D42"/>
    <text x="150" y="520" font-size="14" font-weight="bold" fill="#FFFFFF">6</text>
    <line x1="380" y1="102" x2="380" y2="114" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#d2arrow)"/>
    <line x1="380" y1="192" x2="380" y2="204" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#d2arrow)"/>
    <line x1="380" y1="282" x2="380" y2="294" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#d2arrow)"/>
    <line x1="380" y1="372" x2="380" y2="384" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#d2arrow)"/>
    <line x1="380" y1="462" x2="380" y2="474" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#d2arrow)"/>
    <path d="M 612 155 L 680 155 L 680 515 L 614 515" fill="none" stroke="#2B2D42" stroke-width="2" marker-end="url(#d2arrow)"/>
    <text x="700" y="300" font-size="11.5" fill="#2B2D42" transform="rotate(90 700 300)">on a cache hit, skip ahead</text>
  </g>
</svg>

Step one is your call: one symbol, one date range. Step two asks the cache first — `DistributedCache` tries Redis, then PostgreSQL, then plain memory. A cache hit jumps straight to step six. Step three fetches raw rows from the first source that's configured and connected.

Step four normalizes: `UnifiedNormalizer` gives every source the same columns, timestamps and symbols. Step five cleans: odd outlier prices get dropped, missing days get filled in, and the batch gets a quality score. Step six delivers the rows, saves them to the cache, and can stream them over WebSockets to live listeners.

## Where it lives in the code

- `app/engines/data_engine/data_engine.py` — the `DataEngine` class: one API for prices, fundamentals, sentiment and options.
- `app/engines/data_engine/sources/` — one module per family: OHLCV feeds, fundamentals, sentiment, options.
- `app/engines/data_engine/normalizers/unified_normalizer.py` — reshapes every source into one common format.
- `app/engines/data_engine/validators/data_cleaning_pipeline.py` — outlier removal, gap filling, quality scoring.
- `app/engines/data_engine/cache/distributed_cache.py` — the `DistributedCache`: Redis, PostgreSQL, memory fallback.
- `app/engines/data_engine/versioning/` — data lineage and schema versions, so you know where rows came from.
- `app/backtesting/data_loader.py` — the `DataLoader`: CSV or Yahoo Finance in, `Quote` objects out.
- `data/historical/` — one CSV per symbol; daily OHLCV rows, some going back to 1984.
- `app/domain/market_analysis/` — microstructure analysis (order flow, liquidity, price discovery) that runs on the data.

## Want to go deeper?

- [Strategies](05-strategies.md) — the code that eats this data.
- [Backtesting](09-backtesting.md) — how old rows replay the past.
- [The folder map](03-folder-map.md) — a guided tour of `app/`.
