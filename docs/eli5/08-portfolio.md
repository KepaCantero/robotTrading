# The portfolio, positions and allocation

## The short version

Your portfolio is one money pot: the cash you have, plus every position you still hold. A position is a bet on one symbol, and it's `open` until you close it. On top sits an allocator that splits the pot between strategies, so no single one eats everything.

## What's inside a portfolio

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 290" role="img" aria-label="A Portfolio holds positions, capital and P and L">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="288" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="280" y="24" width="200" height="58" rx="14" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="48" font-size="16" font-weight="bold" fill="#FFFFFF">Portfolio</text>
    <text x="380" y="69" font-size="11.5" fill="#FFFFFF">one account, one currency</text>
    <line x1="340" y1="84" x2="160" y2="126" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <line x1="380" y1="84" x2="380" y2="126" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <line x1="420" y1="84" x2="600" y2="126" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <rect x="60" y="130" width="200" height="104" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="160" y="156" font-size="14" font-weight="bold" fill="#2B2D42">Position</text>
    <text x="160" y="180" font-size="11" fill="#2B2D42">symbol · side · quantity</text>
    <text x="160" y="200" font-size="11" fill="#2B2D42">avg_entry_price · current_price</text>
    <text x="160" y="220" font-size="11" fill="#2B2D42">status: open or closed</text>
    <rect x="280" y="130" width="200" height="104" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="156" font-size="14" font-weight="bold" fill="#2B2D42">Capital</text>
    <text x="380" y="180" font-size="11" fill="#2B2D42">amount · currency</text>
    <rect x="500" y="130" width="200" height="104" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="600" y="156" font-size="14" font-weight="bold" fill="#FFFFFF">P&amp;L</text>
    <text x="600" y="180" font-size="11" fill="#FFFFFF">get_total_pnl()</text>
  </g>
</svg>

Here's the real shape of it. The `Portfolio` dataclass keeps a `positions` dict — the key is a symbol, the value is a `Position`. It also holds `capital`, a small value object with an `amount` and a `currency`. Ask for `get_total_value()` and you get cash plus positions; ask for `get_total_pnl()` and you get profit and loss.

Each `Position` tracks its `side` (long or short), `quantity`, `avg_entry_price` and `current_price`. It also remembers `stop_loss`, `take_profit`, plus the highest and lowest price since entry. The portfolio itself has a status: `ACTIVE`, `SUSPENDED`, `FROZEN` or `CLOSED`.

## The life of a position

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 280" role="img" aria-label="Trade states: open, partially filled, closed and cancelled">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="278" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="40" y="100" width="170" height="56" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2"/>
    <text x="125" y="133" font-size="14" font-weight="bold" fill="#FFFFFF">Order fills</text>
    <line x1="212" y1="128" x2="294" y2="128" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <rect x="300" y="96" width="160" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="121" font-size="14" font-weight="bold" fill="#2B2D42">OPEN</text>
    <text x="380" y="143" font-size="10.5" fill="#2B2D42">entry_price · entry_time</text>
    <line x1="462" y1="110" x2="566" y2="64" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="540" y="92" font-size="10.5" fill="#2B2D42">part fills</text>
    <rect x="570" y="30" width="170" height="60" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="655" y="65" font-size="11.5" font-weight="bold" fill="#2B2D42">PARTIALLY_FILLED</text>
    <line x1="640" y1="92" x2="466" y2="212" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <line x1="380" y1="162" x2="380" y2="196" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <rect x="300" y="200" width="160" height="64" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="224" font-size="14" font-weight="bold" fill="#FFFFFF">CLOSED</text>
    <text x="380" y="246" font-size="10.5" fill="#FFFFFF">exit_price · exit_time · pnl</text>
    <line x1="330" y1="162" x2="206" y2="196" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <rect x="40" y="200" width="170" height="60" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="125" y="235" font-size="13" font-weight="bold" fill="#2B2D42">CANCELLED</text>
  </g>
</svg>

Trades carry the real state machine, and it lives in `TradeStatus`. A trade starts `OPEN` the moment your order fills. `PARTIALLY_FILLED` means the broker filled only part of it. `CLOSED` sets `exit_price`, `exit_time` and `pnl` — the model rejects a closed trade that's missing them. `CANCELLED` means the order died before filling, so no position was created. A `Position` is simpler: it stays `OPEN` until the last share leaves, then turns `CLOSED`.

## How the money gets split

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 300" role="img" aria-label="The allocation manager splits total capital across three strategies by weight">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="298" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="40" y="72" width="180" height="64" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2"/>
    <text x="130" y="97" font-size="14" font-weight="bold" fill="#FFFFFF">Total capital</text>
    <text x="130" y="118" font-size="11" fill="#FFFFFF">total_capital</text>
    <line x1="222" y1="104" x2="294" y2="104" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <rect x="300" y="58" width="230" height="92" rx="14" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="415" y="84" font-size="14" font-weight="bold" fill="#2B2D42">MultiStrategy</text>
    <text x="415" y="104" font-size="14" font-weight="bold" fill="#2B2D42">AllocationManager</text>
    <line x1="500" y1="60" x2="576" y2="56" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <line x1="532" y1="112" x2="576" y2="148" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <line x1="500" y1="150" x2="576" y2="240" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <rect x="580" y="24" width="150" height="60" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="655" y="59" font-size="13" font-weight="bold" fill="#2B2D42">momentum · 50%</text>
    <rect x="580" y="118" width="150" height="60" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="655" y="153" font-size="13" font-weight="bold" fill="#2B2D42">mean_reversion · 25%</text>
    <rect x="580" y="212" width="150" height="60" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="655" y="247" font-size="13" font-weight="bold" fill="#2B2D42">pairs_trading · 25%</text>
  </g>
</svg>

One class does the splitting: `MultiStrategyAllocationManager`, in `app/services/multi_strategy_allocation.py`. Its default plan gives momentum 50%, mean reversion 25% and pairs trading 25%. The numbers come from the central config, so you can change them without touching code. Each `StrategyCapitalAllocation` also carries a `min_weight` and a `max_weight`.

As results come in, `update_weight()` nudges a strategy's weight and clamps it between those bounds. A second layer, `MultiAssetPortfolioManager`, splits money across asset classes like stocks and bonds. It rebalances when weights drift more than `rebalance_threshold` — 5% by default.

## Where it lives in the code

- `app/domain/entities/portfolio.py` and `app/domain/entities/position.py` — the `Portfolio` and `Position` entities, with their status enums.
- `app/backtesting/models.py` — the canonical `Trade` and `TradeStatus` (`open`, `partially_filled`, `closed`, `cancelled`).
- `app/services/multi_strategy_allocation.py` — `StrategyCapitalAllocation` and `MultiStrategyAllocationManager`.
- `app/domain/portfolio/multi_asset/` — `MultiAssetPortfolio`, `MultiAssetAllocation` and the asset-class rebalancer.
- `app/domain/portfolio_optimization/` and `app/engines/portfolio_engine/` — optimizers (mean-variance, Black-Litterman, hierarchical risk parity) and rebalancers.
- `app/services/portfolio_builder.py`, `portfolio_config_manager.py` and `portfolio_rebalancer.py` — build, configure and rebalance a portfolio.

## Where to go next

- [The life of a trade](02-life-of-a-trade.md) — see the moment a position opens.
- [Strategies](05-strategies.md) — meet the three brains your money feeds.
