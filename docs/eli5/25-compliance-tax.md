# Compliance and taxes: the referee and the tax office

## The short version

Before any order leaves this system, one engine gets a veto. The compliance engine checks every trade against a kill switch, size caps, and risk limits. If something smells wrong, the trade is blocked and the reason is logged. After the trade, the same engine grades how well it was executed.

Then there's the money you may owe Spain. When a trade closes, the Spain tax engine works out the tax on your profit, using Spanish rates. It also banks losses you can reuse, and it watches the €50,000 foreign-asset report you might owe Hacienda.

## The flow: one proposal, many referees

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 400" role="img" aria-label="Diagram: a trade proposal passes the compliance engine and pre-trade gates, is allowed or blocked, then gets post-trade analysis and a report">
  <defs>
    <marker id="arrA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
    <marker id="arrNoA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#FF6B6B"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="398" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="25" y="30" width="150" height="110" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="100" y="66" font-size="14.5" font-weight="bold" fill="#FFFFFF">Trade proposal</text>
    <text x="100" y="90" font-size="11" fill="#FFFFFF">a strategy says</text>
    <text x="100" y="108" font-size="11" fill="#FFFFFF">buy 100 AAPL</text>
    <rect x="205" y="30" width="150" height="110" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="280" y="66" font-size="14.5" font-weight="bold" fill="#2B2D42">Compliance engine</text>
    <text x="280" y="90" font-size="11" fill="#2B2D42">SystemBus walks</text>
    <text x="280" y="108" font-size="11" fill="#2B2D42">21 stops, 9 phases</text>
    <rect x="385" y="30" width="150" height="110" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="460" y="62" font-size="14" font-weight="bold" fill="#2B2D42">Pre-trade gates</text>
    <text x="460" y="86" font-size="11" fill="#2B2D42">kill switch · Kelly cap</text>
    <text x="460" y="104" font-size="11" fill="#2B2D42">risk:reward · envelope</text>
    <rect x="565" y="30" width="150" height="110" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="640" y="66" font-size="14.5" font-weight="bold" fill="#2B2D42">Order goes out</text>
    <text x="640" y="90" font-size="11" fill="#2B2D42">to the broker</text>
    <text x="640" y="108" font-size="11" fill="#2B2D42">or the simulator</text>
    <line x1="177" y1="85" x2="201" y2="85" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrA)"/>
    <line x1="357" y1="85" x2="381" y2="85" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrA)"/>
    <line x1="537" y1="85" x2="561" y2="85" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrA)"/>
    <rect x="205" y="250" width="150" height="110" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="280" y="286" font-size="14.5" font-weight="bold" fill="#FFFFFF">Blocked</text>
    <text x="280" y="310" font-size="11" fill="#FFFFFF">reason logged,</text>
    <text x="280" y="328" font-size="11" fill="#FFFFFF">nothing is sent</text>
    <rect x="385" y="250" width="150" height="110" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="460" y="286" font-size="14" font-weight="bold" fill="#FFFFFF">Post-trade analysis</text>
    <text x="460" y="310" font-size="11" fill="#FFFFFF">shortfall · impact</text>
    <text x="460" y="328" font-size="11" fill="#FFFFFF">spread · latency</text>
    <rect x="565" y="250" width="150" height="110" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="640" y="286" font-size="14.5" font-weight="bold" fill="#FFFFFF">Report</text>
    <text x="640" y="310" font-size="11" fill="#FFFFFF">SLO metrics</text>
    <text x="640" y="328" font-size="11" fill="#FFFFFF">decision log</text>
    <path d="M 430 140 V 195 H 280 V 246" fill="none" stroke="#FF6B6B" stroke-width="2.5" marker-end="url(#arrNoA)"/>
    <text x="280" y="238" font-size="12.5" font-weight="bold" fill="#FF6B6B">NO — the limits say stop</text>
    <path d="M 640 140 V 195 H 460 V 246" fill="none" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrA)"/>
    <line x1="537" y1="305" x2="561" y2="305" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrA)"/>
  </g>
</svg>

Every proposal enters through `analyze_pre_trade`, and the kill switch runs first. Lose more than 5% of the day's starting capital and every trade is blocked until the tracker resets.

Then the `SystemBus` walks 21 stops in nine fixed phases: data, context, risk, strategies, microstructure, portfolio, execution, trading checks, and architecture. Three stops are critical — `risk_engine`, `data_engine`, and `live_trading`. If one of those fails, `can_execute` flips to false and the trade dies with a logged reason.

The live-trade path adds gates with real numbers. The Kelly cap says an order can't risk more than 2% of the portfolio. The risk:reward gate wants at least twice the reward for the risk taken. The envelope caps exposure at 30% per symbol, 80% per strategy, and 95% in total.

If the order leaves, the grading starts. `analyze_post_trade` measures implementation shortfall — the gap between the price you saw and the price you got. It also measures market impact, timing cost, and latency against a 100 ms promise. Everything lands in the decision log, so anyone can ask "why?" later.

There's a second, smaller referee set. `OrderPatternAnalyzer` watches for manipulative habits like layering and spoofing — fake orders meant to fool other traders. `ComplianceManager` also keeps the US-only rules, the PDT rule and wash sales, behind a country flag. Spain has neither rule.

## The tax flow: from closed trade to net profit

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 400" role="img" aria-label="Diagram: a closed trade becomes realized profit and loss, the Spain tax engine applies IRPF slices to give net profit, with branches for the loss bank, dividends, and Modelo 720">
  <defs>
    <marker id="arrB" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="398" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="25" y="30" width="150" height="110" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="100" y="62" font-size="14" font-weight="bold" fill="#FFFFFF">A trade closes</text>
    <text x="100" y="86" font-size="11" fill="#FFFFFF">the sell meets</text>
    <text x="100" y="104" font-size="11" fill="#FFFFFF">its buy (FIFO)</text>
    <rect x="205" y="30" width="150" height="110" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="280" y="62" font-size="14" font-weight="bold" fill="#2B2D42">Realized P&amp;L</text>
    <text x="280" y="86" font-size="11" fill="#2B2D42">profit or loss,</text>
    <text x="280" y="104" font-size="11" fill="#2B2D42">lot by lot</text>
    <rect x="385" y="30" width="150" height="110" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="460" y="62" font-size="14" font-weight="bold" fill="#2B2D42">Spain tax engine</text>
    <text x="460" y="86" font-size="11" fill="#2B2D42">IRPF slices:</text>
    <text x="460" y="104" font-size="11" fill="#2B2D42">19% · 21% · 23%</text>
    <rect x="565" y="30" width="150" height="110" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="640" y="62" font-size="14.5" font-weight="bold" fill="#FFFFFF">Net P&amp;L</text>
    <text x="640" y="86" font-size="11" fill="#FFFFFF">gross minus tax,</text>
    <text x="640" y="104" font-size="11" fill="#FFFFFF">logged with the order</text>
    <line x1="177" y1="85" x2="201" y2="85" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrB)"/>
    <line x1="357" y1="85" x2="381" y2="85" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrB)"/>
    <line x1="537" y1="85" x2="561" y2="85" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrB)"/>
    <rect x="205" y="250" width="150" height="110" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="280" y="286" font-size="14.5" font-weight="bold" fill="#2B2D42">Loss bank</text>
    <text x="280" y="310" font-size="11" fill="#2B2D42">losses offset gains</text>
    <text x="280" y="328" font-size="11" fill="#2B2D42">for four years</text>
    <rect x="385" y="250" width="150" height="110" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="460" y="286" font-size="14.5" font-weight="bold" fill="#2B2D42">Dividends</text>
    <text x="460" y="310" font-size="11" fill="#2B2D42">EU tickers 0%</text>
    <text x="460" y="328" font-size="11" fill="#2B2D42">others 19%</text>
    <rect x="565" y="250" width="150" height="110" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="640" y="286" font-size="14.5" font-weight="bold" fill="#FFFFFF">Modelo 720</text>
    <text x="640" y="310" font-size="11" fill="#FFFFFF">over €50,000 abroad</text>
    <text x="640" y="328" font-size="11" fill="#FFFFFF">due by March 31</text>
    <path d="M 430 140 V 195 H 280 V 246" fill="none" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrB)"/>
    <line x1="460" y1="140" x2="460" y2="246" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrB)"/>
    <path d="M 490 140 V 195 H 640 V 246" fill="none" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrB)"/>
  </g>
</svg>

Spain's tax office doesn't care how long you held a position. A gain held for ten seconds is taxed like one held for ten years. There's no US-style long-term rate, and no wash sale rule.

When you sell, shares are matched to buys with FIFO — first in, first out. The match produces a realized profit or loss. Profit is taxed in slices: 19% on the first €6,000, 21% up to €50,000, and 23% above that. A loss pays no tax; it's banked instead, and it can offset gains for the next four years.

Dividends get a simpler test in the wired-in engine: a curated list of EU tickers pays 0% withholding, everything else pays 19%. Foreign holdings add paperwork. Above €50,000 abroad, you owe Hacienda a yearly Modelo 720 report, due by March 31. Crypto holdings get their own yearly form, Modelo 721.

The result rides on `TradeResult` as `spain_tax`, and net profit is simply gross minus tax. One caveat: at order time the engine books zero profit, so the real tax lands when fills settle.

Sharp eyes will find two Spain engines. The one wired into trading, `SpainTaxEngineImpl`, uses the €6,000 and €50,000 slices above. The factory engine uses higher slice limits, roughly €33,000 and €53,400. `SPAIN_TAX_ENGINE.md` documents the factory one, so the doc and the trade path disagree. Trust the code you actually run.

## Rule 28

Rule 28 is the security half of compliance, and its demand is blunt. No key, password, or token ever lives in source code. Secrets come from environment variables, documented in `.env.example`, masked in logs, and rejected when they look weak. Connection strings are built at runtime, never typed in. The doc claims a manager at `app/core/secret_manager.py` plus a validation script. The real manager sits at `app/security/secrets/secret_manager.py`, and that script doesn't exist — the doc drifted, the idea held.

## Where it lives in the code

- `app/services/compliance/compliance_engine.py` — the engine itself: `SystemBus`, kill switch, risk envelope, position sizing, SLO tracking.
- `app/services/compliance/manager.py` — country rules, with `pdt_tracker.py`, `wash_sale_tracker.py`, and `order_pattern_analyzer.py` beside it.
- `app/domain/services/compliance/` — the refactored split: pre-trade checker, post-trade checker, service registry.
- `app/services/tax_efficiency/engines/spain_tax_engine_impl.py` — the Spain engine wired into `execute_trade`.
- `app/services/tax_efficiency/engines/spain_tax_engine.py` and `factory.py` — the config-driven engine and its factory.
- `app/services/fifo/` — FIFO lot matching and the Modelo 721 crypto report.
- `app/shared/protocols/i_spain_tax_engine.py` — the five-method contract every Spain engine signs.
- `app/shared/config/params/risk_config.py` — every threshold on this page, as named config.
- `docs/sre/SECURITY_COMPLIANCE_RULE28.md` and `docs/sre/SPAIN_TAX_ENGINE.md` — the deeper docs, partly stale.

## Want to go deeper?

- [The life of a trade](02-life-of-a-trade.md) — where these gates sit in the trading loop.
- [The risk engine](06-risk-engine.md) — the limits that feed the compliance gates.
- [Security](19-hat-security.md) — the keys, secrets, and audits behind Rule 28.
