# The risk engine and circuit breakers

## The short version

Every trade must pass a set of risk checks before it's allowed to leave the system. If a check says no, the trade is skipped — no arguments. Circuit breakers are the louder cousin: they can pause all trading when the code or the market turns dangerous.

## The gates before every trade

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 580" role="img" aria-label="A signal passes four risk gates; any no skips the trade, all yes sends the order to execution">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="578" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="90" y="26" width="400" height="64" rx="14" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="290" y="56" font-size="15" font-weight="bold" fill="#2B2D42">A signal arrives</text>
    <text x="290" y="78" font-size="12" fill="#2B2D42">a strategy wants to trade</text>
    <line x1="290" y1="90" x2="290" y2="112" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <rect x="90" y="116" width="400" height="68" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="290" y="144" font-size="14.5" font-weight="bold" fill="#FFFFFF">1 · Position size</text>
    <text x="290" y="165" font-size="12" fill="#FFFFFF">max 25% of your capital</text>
    <line x1="290" y1="186" x2="290" y2="206" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <text x="302" y="200" font-size="11" fill="#2B2D42" text-anchor="start">yes</text>
    <rect x="90" y="210" width="400" height="68" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="290" y="238" font-size="14.5" font-weight="bold" fill="#FFFFFF">2 · Stop-loss set</text>
    <text x="290" y="259" font-size="12" fill="#FFFFFF">an exit price is required</text>
    <line x1="290" y1="280" x2="290" y2="300" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <text x="302" y="294" font-size="11" fill="#2B2D42" text-anchor="start">yes</text>
    <rect x="90" y="304" width="400" height="68" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="290" y="332" font-size="14.5" font-weight="bold" fill="#FFFFFF">3 · Risk vs reward</text>
    <text x="290" y="353" font-size="12" fill="#FFFFFF">reward at least twice the risk</text>
    <line x1="290" y1="374" x2="290" y2="394" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <text x="302" y="388" font-size="11" fill="#2B2D42" text-anchor="start">yes</text>
    <rect x="90" y="398" width="400" height="68" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="290" y="426" font-size="14.5" font-weight="bold" fill="#FFFFFF">4 · Exposure caps</text>
    <text x="290" y="447" font-size="12" fill="#FFFFFF">symbol 30% · strategy 80% · total 95%</text>
    <line x1="290" y1="468" x2="290" y2="488" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <rect x="90" y="492" width="400" height="64" rx="14" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="290" y="522" font-size="15" font-weight="bold" fill="#FFFFFF">All passed</text>
    <text x="290" y="543" font-size="12" fill="#FFFFFF">the order goes to execution</text>
    <line x1="490" y1="150" x2="568" y2="150" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="529" y="143" font-size="11.5" fill="#2B2D42">no</text>
    <line x1="490" y1="244" x2="568" y2="244" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="529" y="237" font-size="11.5" fill="#2B2D42">no</text>
    <line x1="490" y1="338" x2="568" y2="338" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="529" y="331" font-size="11.5" fill="#2B2D42">no</text>
    <line x1="490" y1="432" x2="568" y2="432" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="529" y="425" font-size="11.5" fill="#2B2D42">no</text>
    <rect x="572" y="120" width="158" height="340" rx="14" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="651" y="284" font-size="14.5" font-weight="bold" fill="#2B2D42">Trade skipped</text>
    <text x="651" y="306" font-size="12" fill="#2B2D42">the reason is logged</text>
  </g>
</svg>

Four gates stand between a signal and an order. A signal is a strategy saying "I want to buy this". Gate one caps position size, the money one trade may use, at 25% of your capital. Gate two demands a stop-loss, an exit price that cuts your loss if the trade goes bad. Gate three wants a possible reward at least twice the possible risk.

Gate four checks exposure, meaning how much of your money is already committed: 30% per symbol, 80% per strategy, 95% overall. A fifth check keeps trading inside regular market hours, 9am to 4pm. When any gate says no, the trade is skipped and the reason lands in the log. The next signal starts fresh.

## The breaker that guards the code

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 320" role="img" aria-label="State diagram of the API circuit breaker: closed, open, half-open, and the transitions between them">
  <defs>
    <marker id="arrow2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="318" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="285" y="30" width="190" height="80" rx="13" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="61" font-size="16" font-weight="bold" fill="#2B2D42">HALF_OPEN</text>
    <text x="380" y="85" font-size="12" fill="#2B2D42">a few test calls</text>
    <rect x="70" y="170" width="190" height="80" rx="13" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="165" y="201" font-size="16" font-weight="bold" fill="#2B2D42">CLOSED</text>
    <text x="165" y="225" font-size="12" fill="#2B2D42">calls flow normally</text>
    <rect x="500" y="170" width="190" height="80" rx="13" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="595" y="201" font-size="16" font-weight="bold" fill="#FFFFFF">OPEN</text>
    <text x="595" y="225" font-size="12" fill="#FFFFFF">calls are blocked</text>
    <line x1="260" y1="210" x2="496" y2="210" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow2)"/>
    <text x="379" y="200" font-size="11.5" fill="#2B2D42">5 failures in a row</text>
    <line x1="565" y1="170" x2="455" y2="106" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow2)"/>
    <text x="548" y="126" font-size="11.5" fill="#2B2D42">5 quiet minutes</text>
    <line x1="308" y1="106" x2="200" y2="170" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow2)"/>
    <text x="215" y="126" font-size="11.5" fill="#2B2D42">3 test calls succeed</text>
    <path d="M 475 70 L 620 70 L 620 166" fill="none" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow2)"/>
    <text x="548" y="60" font-size="11.5" fill="#2B2D42">a test fails</text>
  </g>
</svg>

This breaker protects the machine, not the money. Every outside call — market data, orders, the broker — can fail, and the breaker counts those failures. The names come straight from the code: `CircuitState.CLOSED`, `OPEN` and `HALF_OPEN`. Five failures in a row open the circuit, so one broken service can't drag the rest down. After five quiet minutes it goes half-open and lets three test calls through.

If those test calls succeed, the circuit closes again. If one fails, it opens right back up. There are four of these breakers, one each for API errors, the data service, order execution and the broker connection.

## The breaker that guards the market

This one watches the market itself, using SPY as a proxy, a stand-in for the whole market. A 7% drop triggers `LEVEL_1` and trading pauses for 15 minutes. A 13% drop is `LEVEL_2`, same pause. A 20% drop is `LEVEL_3`, and trading stops for the rest of the day. It also reads the VIX, an index of expected market fear: 25 means warning, 35 means pause everything.

When it fires, all trading pauses and every pending order is cancelled. A loop then asks every 60 seconds whether the halt is still in place. The moment it lifts, trading resumes on its own — no human needed. That's the design: a failed gate costs you one trade, a tripped breaker costs you only time.

## Where it lives in the code

- `app/domain/services/trading_validators.py` — `TradingValidator`, the gates for position size, stop-loss, risk vs reward and trading hours.
- `app/services/compliance/compliance_engine.py` — `ComplianceEngine.validate_risk_envelope()`, the exposure caps per symbol, strategy and portfolio.
- `app/engines/risk_engine/__init__.py` — `RiskEngine`, which bundles the risk parts and keeps a history of every assessment.
- `app/engines/risk_engine/risk_limits_enforcer.py` — `RiskLimitsEnforcer.check_var_limits()`, which turns VaR into actions. VaR, or value at risk, estimates your worst likely loss.
- `app/services/api_circuit_breaker.py` — `CircuitState` and the API `CircuitBreakerManager`, the CLOSED / OPEN / HALF_OPEN machine.
- `app/services/circuit_breaker_manager.py` — the market breaker: `CircuitBreakerLevel`, `TradingStatus`, pause and resume.
- `app/shared/protocols/i_pre_trade_validator.py` — the `IPreTradeValidator` contract that pre-trade checks follow.

## Want to go deeper?

- [The life of a trade](02-life-of-a-trade.md) — see where these gates sit in a trade's journey.
- [Strategies](05-strategies.md) — meet the code that creates the signals being checked.
- [Execution](07-execution.md) — what happens once every check says yes.
