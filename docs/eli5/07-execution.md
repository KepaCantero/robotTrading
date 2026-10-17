# Order execution and paper trading

## The short version

Execution turns a trading decision into a fill — the moment shares actually change hands. This page follows an order through its states and shows what a fill costs. Then it explains paper trading, where you trade real prices with fake money.

## The life of an order

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 330" role="img" aria-label="Order state diagram: PENDING to SUBMITTED to PARTIALLY_FILLED to FILLED, with CANCELLED and REJECTED">
  <defs>
    <marker id="arrow07a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker>
  </defs>
  <rect x="1" y="1" width="758" height="328" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="30" y="70" width="140" height="56" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="100" y="103" font-size="14" font-weight="bold" fill="#2B2D42">PENDING</text>
    <rect x="215" y="70" width="150" height="56" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="290" y="103" font-size="14" font-weight="bold" fill="#2B2D42">SUBMITTED</text>
    <rect x="400" y="70" width="150" height="56" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="475" y="94" font-size="14" font-weight="bold" fill="#2B2D42">PARTIALLY</text>
    <text x="475" y="112" font-size="14" font-weight="bold" fill="#2B2D42">FILLED</text>
    <rect x="590" y="70" width="140" height="56" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="660" y="103" font-size="14" font-weight="bold" fill="#2B2D42">FILLED</text>
    <rect x="180" y="240" width="150" height="56" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="255" y="273" font-size="14" font-weight="bold" fill="#2B2D42">CANCELLED</text>
    <rect x="470" y="240" width="150" height="56" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="545" y="273" font-size="14" font-weight="bold" fill="#2B2D42">REJECTED</text>
    <line x1="170" y1="98" x2="211" y2="98" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07a)"/>
    <line x1="365" y1="98" x2="396" y2="98" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07a)"/>
    <text x="380" y="86" font-size="11" fill="#2B2D42">part fills</text>
    <line x1="550" y1="98" x2="586" y2="98" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07a)"/>
    <line x1="268" y1="128" x2="250" y2="236" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07a)"/>
    <text x="188" y="185" font-size="11" fill="#2B2D42">you cancel</text>
    <line x1="330" y1="128" x2="510" y2="236" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07a)"/>
    <text x="430" y="176" font-size="11" fill="#2B2D42">the broker says no</text>
  </g>
</svg>

An order starts as PENDING and becomes SUBMITTED when the system sends it out. The fill — the shares actually bought or sold — can arrive all at once or in pieces. Orders end two ways: you cancel them, or a check fails and the order is REJECTED. These six states come straight from `OrderStatus` in `app/domain/models/order.py`. The broker contract in `app/shared/interfaces/broker_base.py` adds more for live trading, like ACK_RECEIVED, EXPIRED and FAILED.

## From approval to fill

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 360" role="img" aria-label="Execution flow: approved order, execution costs, then a paper path or a live broker path">
  <defs>
    <marker id="arrow07b" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker>
  </defs>
  <rect x="1" y="1" width="758" height="358" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="25" y="40" width="175" height="80" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="112" y="82" font-size="14" font-weight="bold" fill="#FFFFFF">Approved order</text>
    <line x1="200" y1="80" x2="258" y2="80" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07b)"/>
    <rect x="260" y="35" width="220" height="90" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="370" y="66" font-size="14" font-weight="bold" fill="#2B2D42">Execution costs</text>
    <text x="370" y="88" font-size="11" fill="#2B2D42">commission 0.1%</text>
    <text x="370" y="106" font-size="11" fill="#2B2D42">slippage + impact</text>
    <line x1="335" y1="125" x2="195" y2="238" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07b)"/>
    <text x="215" y="185" font-size="11" fill="#2B2D42">paper mode</text>
    <line x1="405" y1="125" x2="565" y2="238" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07b)"/>
    <text x="545" y="185" font-size="11" fill="#2B2D42">live mode</text>
    <rect x="40" y="240" width="310" height="92" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="195" y="284" font-size="14" font-weight="bold" fill="#FFFFFF">Paper trading engine</text>
    <text x="195" y="306" font-size="11" fill="#FFFFFF">live prices, fake money</text>
    <rect x="410" y="240" width="310" height="92" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="565" y="272" font-size="14" font-weight="bold" fill="#FFFFFF">Broker adapter</text>
    <text x="565" y="294" font-size="11" fill="#FFFFFF">real broker, real money</text>
    <text x="565" y="312" font-size="11" fill="#FFFFFF">contract only, for now</text>
  </g>
</svg>

Every fill costs more than the share price. Commission — the broker's fee — defaults to 0.1% of the trade value. Slippage is the gap between the price you wanted and the price you got; the engine estimates it, with 0.05% as the fallback. Market impact is how much your own order pushes the price. SIMPLE mode sets all three to zero; REALISTIC mode charges them. Sometimes only 50–90% of the order fills, and the rest waits.

The paper engine fills your order against live prices and moves fake cash — $100,000 by default. The live path needs a broker adapter, code that talks to a real broker. The repo ships the contract (`broker_base.py`) and a paper broker, so no real broker is wired in yet.

## Paper trading: the two scripts

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 270" role="img" aria-label="Paper trading scripts: start script sets up the environment, then starts the API on port 8000 and the NiceGUI dashboard on port 8501">
  <defs>
    <marker id="arrow07c" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker>
  </defs>
  <rect x="1" y="1" width="758" height="268" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="25" y="50" width="190" height="76" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="120" y="92" font-size="12.5" font-weight="bold" fill="#FFFFFF">start_paper_trading.sh</text>
    <line x1="215" y1="88" x2="263" y2="88" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07c)"/>
    <rect x="265" y="50" width="160" height="76" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="345" y="88" font-size="12" font-weight="bold" fill="#2B2D42">Setup: .env + .venv</text>
    <line x1="425" y1="68" x2="543" y2="60" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07c)"/>
    <line x1="425" y1="108" x2="543" y2="186" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07c)"/>
    <rect x="545" y="22" width="190" height="84" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="640" y="50" font-size="14" font-weight="bold" fill="#FFFFFF">API server</text>
    <text x="640" y="70" font-size="11" fill="#FFFFFF">uvicorn, port 8000</text>
    <text x="640" y="88" font-size="11" fill="#FFFFFF">runs in background</text>
    <rect x="545" y="150" width="190" height="84" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="640" y="178" font-size="14" font-weight="bold" fill="#FFFFFF">Dashboard</text>
    <text x="640" y="198" font-size="11" fill="#FFFFFF">NiceGUI, port 8501</text>
    <text x="640" y="216" font-size="11" fill="#FFFFFF">Ctrl+C stops it</text>
    <rect x="25" y="160" width="190" height="76" rx="12" fill="#2B2D42" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="120" y="190" font-size="12.5" font-weight="bold" fill="#FFFFFF">stop_paper_trading.sh</text>
    <text x="120" y="212" font-size="11" fill="#FFFFFF">kills the API server</text>
    <line x1="215" y1="198" x2="598" y2="108" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow07c)"/>
  </g>
</svg>

Run `./scripts/start_paper_trading.sh` and it prepares `.env`, activates `.venv` and starts two services. The API server (uvicorn — the web server behind FastAPI) runs in the background on port 8000. The NiceGUI dashboard runs in the foreground on port 8501, so Ctrl+C stops it. `./scripts/stop_paper_trading.sh` kills the API server using the PID saved in `.api_server.pid`.

## Where it lives in the code

- `app/domain/models/order.py` and `app/domain/models/paper_trading.py` — the order states, `TradeStatus` and the three simulation modes.
- `app/services/paper_trading_service.py` — the paper engine: costs, partial fills, portfolio updates.
- `app/infrastructure/brokers/paper.py` — a small paper broker.
- `app/shared/interfaces/broker_base.py` — the contract every real broker must implement.
- `app/engines/execution_engine/` — microstructure analysis: how to split big orders cheaply.
- `app/simulation/` — order book, matching engine and cost models for rehearsal.
- `scripts/start_paper_trading.sh` and `scripts/stop_paper_trading.sh` — start and stop everything.

## Want to go deeper?

- [The risk engine](06-risk-engine.md) — what must say yes before an order exists.
- [The portfolio](08-portfolio.md) — the cash and positions that execution updates.
- [Backtesting](09-backtesting.md) — the same cost models, replayed on history.
