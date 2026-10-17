# ELI5 — AlgoTrading, explained simply

This folder is the friendly part of the documentation. No jargon walls, no 4,000-line file names. Just what the system does, how a trade happens, and where things live in the code.

Everything here is written in simple English (around B2 level). If a sentence makes you stop and re-read it, that sentence is broken — fix it or open an issue.

## The pages

**The basics**

1. [How the system works](01-how-the-system-works.md) — the big picture, layer by layer.
2. [The life of a trade](02-life-of-a-trade.md) — follow one order from "the price moved" to "position updated".
3. [The folder map](03-folder-map.md) — what lives in each folder inside `app/`.

**One page per subsystem**

4. [The data pipeline](04-data-pipeline.md) — where prices and news come from.
5. [The strategies](05-strategies.md) — momentum, mean reversion, pairs trading, and the ensembles.
6. [The risk engine](06-risk-engine.md) — limits, gates, and circuit breakers.
7. [Execution](07-execution.md) — the order lifecycle and paper trading.
8. [The portfolio](08-portfolio.md) — positions, cash, and allocation.
9. [Backtesting](09-backtesting.md) — replay the past, get a verdict.
10. [Security](10-security.md) — API keys, JWT, and secrets.
11. [The dashboard](11-dashboard.md) — the NiceGUI app, with docs at `/docs`.
12. [The IBKR connection](12-ibkr.md) — how IBKR plugs in, and what is real today.
13. [The component playbook](13-component-playbook.md) — the logic each component applies.

**The rulebook and its sources**

20. [The trading rulebook](20-trading-rules.md) — every trading rule, grouped by the book it comes from.
21. [The engineering rulebook](21-engineering-rules.md) — the Python rules the code must follow.
22. [The bibliography](22-bibliography.md) — the books behind the rules, and where each idea landed.

**One page per hat**

14. [Newcomer](14-hat-newcomer.md) — your first week on the project.
15. [Trader](15-hat-trader.md) — what the robot does with your money.
16. [Developer](16-hat-developer.md) — where to code, and how it fits together.
17. [Quant](17-hat-quant.md) — strategies, metrics, and backtests.
18. [SRE](18-hat-sre.md) — keeping the system alive and observable.
19. [Security](19-hat-security.md) — keys, secrets, and audits.

## The ELI5 palette

Every diagram in these pages uses the same small set of colors, so your eyes learn the meaning once and reuse it everywhere:

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 130" role="img" aria-label="The ELI5 color palette">
  <rect x="1" y="1" width="738" height="128" rx="14" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="20" y="18" width="100" height="56" rx="10" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="70" y="51" font-size="13" font-weight="bold" fill="#2B2D42">Sunflower</text>
    <text x="70" y="94" font-size="11" fill="#2B2D42" font-family="monospace">#FFD93D</text>
    <rect x="138" y="18" width="100" height="56" rx="10" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="188" y="51" font-size="13" font-weight="bold" fill="#FFFFFF">Coral</text>
    <text x="188" y="94" font-size="11" fill="#2B2D42" font-family="monospace">#FF6B6B</text>
    <rect x="256" y="18" width="100" height="56" rx="10" fill="#4D96FF" stroke="#2B2D42" stroke-width="2"/>
    <text x="306" y="51" font-size="13" font-weight="bold" fill="#FFFFFF">Sky</text>
    <text x="306" y="94" font-size="11" fill="#2B2D42" font-family="monospace">#4D96FF</text>
    <rect x="374" y="18" width="100" height="56" rx="10" fill="#6BCB77" stroke="#2B2D42" stroke-width="2"/>
    <text x="424" y="51" font-size="13" font-weight="bold" fill="#2B2D42">Mint</text>
    <text x="424" y="94" font-size="11" fill="#2B2D42" font-family="monospace">#6BCB77</text>
    <rect x="492" y="18" width="100" height="56" rx="10" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="542" y="51" font-size="13" font-weight="bold" fill="#FFFFFF">Grape</text>
    <text x="542" y="94" font-size="11" fill="#2B2D42" font-family="monospace">#9B5DE5</text>
    <rect x="610" y="18" width="100" height="56" rx="10" fill="#2B2D42" stroke="#2B2D42" stroke-width="2"/>
    <text x="660" y="51" font-size="13" font-weight="bold" fill="#FFFFFF">Ink</text>
    <text x="660" y="94" font-size="11" fill="#2B2D42" font-family="monospace">#2B2D42</text>
  </g>
</svg>

And each color always means the same thing:

| Color | We use it for |
|---|---|
| Sky `#4D96FF` | entry points — where requests and data come in |
| Mint `#6BCB77` | coordination — deciding the order of steps |
| Sunflower `#FFD93D` | the trading brain — strategies, signals, rules |
| Coral `#FF6B6B` | the outside world and things that can hurt you — infrastructure, risk |
| Grape `#9B5DE5` | results and people — portfolio, dashboards, backtests |
| Ink `#2B2D42` | text, borders and neutral boxes |
| Cream `#FFF9E6` | the background of every diagram |

## Diagram rules

- Diagrams are inline `<svg>` blocks with a `viewBox`, never a fixed width, so they scale on any screen.
- Boxes are rounded (`rx="12"` or more) with an ink border 2–2.5 px wide.
- Six words per line inside a box, maximum. If it doesn't fit, the diagram is too complicated.
- Copy the palette above. Don't invent new colors — the meaning lives in the repetition.

## A note about rendering (important)

GitHub strips inline `<svg>` from markdown files for security reasons. In VS Code's markdown preview, in MkDocs and in most other viewers, the diagrams look right. So does the dashboard: it serves this whole site at `http://localhost:8503/docs/` (`make dashboard`). On github.com you'll see empty gaps. If a page must render there, turn that one diagram into [Mermaid](https://mermaid.js.org) (GitHub renders it natively) or a standalone `.svg` file.

## Keeping the human voice

These rules keep the pages easy to read:

- Short sentences. Contractions. Talk to "you".
- One idea per paragraph.
- When you use a technical term, explain it in the same sentence.
- Read it out loud. If you run out of breath, split the sentence.

Want a machine to check the style? Run the page through a humanizing pass (the Étincel or WriteHuman MCP servers). Or lint it with [Vale](https://vale.sh) and a readability config.
