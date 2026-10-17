# The life of a trade

Imagine the service is awake and running. Over and over, quietly, it runs the same loop. Here is one full turn of that loop:

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 320" role="img" aria-label="The trade loop: market data, strategy, risk check, execution, portfolio, audit trail, then back to the start">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
    <marker id="arrowNo" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#FF6B6B"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="958" height="318" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <circle cx="80" cy="86" r="15" fill="#2B2D42"/>
    <text x="80" y="91" font-size="14" font-weight="bold" fill="#FFFFFF">1</text>
    <rect x="16" y="96" width="128" height="96" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="80" y="130" font-size="14.5" font-weight="bold" fill="#FFFFFF">Market data</text>
    <text x="80" y="152" font-size="11" fill="#FFFFFF">prices, volume,</text>
    <text x="80" y="168" font-size="11" fill="#FFFFFF">news (data_engine)</text>

    <circle cx="240" cy="86" r="15" fill="#2B2D42"/>
    <text x="240" y="91" font-size="14" font-weight="bold" fill="#FFFFFF">2</text>
    <rect x="176" y="96" width="128" height="96" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="240" y="130" font-size="14.5" font-weight="bold" fill="#2B2D42">Strategy</text>
    <text x="240" y="152" font-size="11" fill="#2B2D42">buy, sell or wait?</text>
    <text x="240" y="168" font-size="11" fill="#2B2D42">(strategy_engines)</text>

    <circle cx="400" cy="86" r="15" fill="#2B2D42"/>
    <text x="400" y="91" font-size="14" font-weight="bold" fill="#FFFFFF">3</text>
    <rect x="336" y="96" width="128" height="96" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="400" y="130" font-size="14.5" font-weight="bold" fill="#FFFFFF">Risk check</text>
    <text x="400" y="152" font-size="11" fill="#FFFFFF">are the limits</text>
    <text x="400" y="168" font-size="11" fill="#FFFFFF">ok? (risk_engine)</text>

    <circle cx="560" cy="86" r="15" fill="#2B2D42"/>
    <text x="560" y="91" font-size="14" font-weight="bold" fill="#FFFFFF">4</text>
    <rect x="496" y="96" width="128" height="96" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="560" y="130" font-size="14.5" font-weight="bold" fill="#2B2D42">Execution</text>
    <text x="560" y="152" font-size="11" fill="#2B2D42">the order goes</text>
    <text x="560" y="168" font-size="11" fill="#2B2D42">out (execution)</text>

    <circle cx="720" cy="86" r="15" fill="#2B2D42"/>
    <text x="720" y="91" font-size="14" font-weight="bold" fill="#FFFFFF">5</text>
    <rect x="656" y="96" width="128" height="96" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="720" y="130" font-size="14.5" font-weight="bold" fill="#FFFFFF">Portfolio</text>
    <text x="720" y="152" font-size="11" fill="#FFFFFF">positions &amp; cash</text>
    <text x="720" y="168" font-size="11" fill="#FFFFFF">updated</text>

    <circle cx="880" cy="86" r="15" fill="#2B2D42"/>
    <text x="880" y="91" font-size="14" font-weight="bold" fill="#FFFFFF">6</text>
    <rect x="816" y="96" width="128" height="96" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="880" y="130" font-size="14.5" font-weight="bold" fill="#2B2D42">Audit trail</text>
    <text x="880" y="152" font-size="11" fill="#2B2D42">everything logged,</text>
    <text x="880" y="168" font-size="11" fill="#2B2D42">compliance checks</text>

    <line x1="148" y1="144" x2="172" y2="144" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <line x1="308" y1="144" x2="332" y2="144" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <line x1="468" y1="144" x2="492" y2="144" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <line x1="628" y1="144" x2="652" y2="144" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <line x1="788" y1="144" x2="812" y2="144" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>

    <line x1="400" y1="192" x2="400" y2="220" stroke="#FF6B6B" stroke-width="2.5" marker-end="url(#arrowNo)"/>
    <text x="400" y="240" font-size="12.5" font-weight="bold" fill="#FF6B6B">NO — skip this round, stay in cash</text>

    <path d="M 880 192 V 280 H 80 V 202" fill="none" stroke="#2B2D42" stroke-width="2" stroke-dasharray="6 5" marker-end="url(#arrow)"/>
    <text x="480" y="270" font-size="13" font-style="italic" fill="#2B2D42">…and a moment later, it starts all over again</text>
  </g>
</svg>

## The six steps, with a bit more detail

**1. Market data arrives.** The `data_engine` collects prices, trading volume and sometimes news. This is the raw material. Without fresh data, nothing else happens.

**2. A strategy has an opinion.** The strategy engines look at the data and produce a *signal*: buy, sell, or do nothing. A momentum strategy, for example, asks one simple question — "has this price been going up?" — and answers it with math.

**3. The risk engine votes.** Before any money moves, the `risk_engine` checks the limits: position size, how much we could lose, how exposed the portfolio already is. It can say no. When it says no, nothing happens that round — and that's not a failure, that's the design working.

**4. The order goes out.** The execution engine sends the approved order. In paper mode it goes to the simulator; in live mode it goes to a real broker. Same code path, different destination.

**5. The portfolio updates.** The `portfolio_engine` records the new position, the cash spent or received, and the running profit and loss. Now the system's memory matches reality.

**6. Everything is written down.** The trade lands in the audit trail, and compliance checks run after the fact. If anyone ever asks "why did the robot buy that?", the answer is sitting in the logs.

Then the loop starts again, a few seconds later, forever (or until you run `./stop_paper_trading.sh`).

One detail worth noticing: no signal can skip step 3. Not even a strategy that has been winning for six months gets a free pass past the risk engine.
