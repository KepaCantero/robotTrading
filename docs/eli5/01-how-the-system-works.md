# How the system works

## The short version

AlgoTrading is a Python service that watches the market and decides whether a trade is worth taking. If it is, the system checks that the risk is okay and places the order. No human has to press a button. You can watch everything it does through a dashboard or by calling the API.

It's a big codebase, but the idea behind it is simple. Keep that in mind when the folder names get long.

## The layer cake

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 600" role="img" aria-label="Diagram of the four layers: you, API, application, domain, infrastructure, with PostgreSQL and Redis at the bottom">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="598" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <line x1="62" y1="140" x2="62" y2="460" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="46" y="300" font-size="12" fill="#2B2D42" transform="rotate(-90 46 300)">a request goes down</text>
    <line x1="698" y1="460" x2="698" y2="140" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="716" y="300" font-size="12" fill="#2B2D42" transform="rotate(90 716 300)">answers come back up</text>

    <rect x="120" y="30" width="520" height="80" rx="14" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="62" font-size="18" font-weight="bold" fill="#FFFFFF">You</text>
    <text x="380" y="86" font-size="12.5" fill="#FFFFFF">dashboard · scripts · API calls</text>

    <line x1="380" y1="112" x2="380" y2="132" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>

    <rect x="120" y="136" width="520" height="80" rx="14" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="168" font-size="17" font-weight="bold" fill="#FFFFFF">API layer — FastAPI</text>
    <text x="380" y="192" font-size="12.5" fill="#FFFFFF">app/api · app/presentation — the front door</text>

    <line x1="380" y1="218" x2="380" y2="238" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>

    <rect x="120" y="242" width="520" height="80" rx="14" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="274" font-size="17" font-weight="bold" fill="#2B2D42">Application layer — the organizer</text>
    <text x="380" y="298" font-size="12.5" fill="#2B2D42">app/application · app/services</text>

    <line x1="380" y1="324" x2="380" y2="344" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>

    <rect x="120" y="348" width="520" height="80" rx="14" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="380" font-size="17" font-weight="bold" fill="#2B2D42">Domain layer — the brain</text>
    <text x="380" y="404" font-size="12.5" fill="#2B2D42">app/domain · app/engines — strategies &amp; trading rules</text>

    <line x1="380" y1="430" x2="380" y2="450" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>

    <rect x="120" y="454" width="520" height="80" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="486" font-size="17" font-weight="bold" fill="#FFFFFF">Infrastructure layer — the hands</text>
    <text x="380" y="510" font-size="12.5" fill="#FFFFFF">app/infrastructure — databases, brokers, news APIs</text>

    <line x1="290" y1="536" x2="272" y2="550" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>
    <line x1="470" y1="536" x2="488" y2="550" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrow)"/>

    <rect x="170" y="552" width="200" height="44" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="270" y="580" font-size="14" font-weight="bold" fill="#2B2D42">PostgreSQL</text>
    <rect x="390" y="552" width="200" height="44" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="490" y="580" font-size="14" font-weight="bold" fill="#2B2D42">Redis</text>
  </g>
</svg>

The code sits in layers. A request travels from the top to the bottom, and the answer travels back up. Each layer has one job and mostly ignores the others.

**API layer — the front door.** FastAPI lives here (`app/api`, `app/presentation`). It receives your requests, checks that you're allowed to make them, and passes them along. It doesn't think about trading at all.

**Application layer — the organizer.** `app/application` and `app/services` decide the order of the steps: get the data, run the strategy, save the result, send an alert. Like a good project manager, it doesn't do the specialist work itself.

**Domain layer — the brain.** `app/domain` and `app/engines` hold the actual trading knowledge: strategies, portfolio math, risk rules. On purpose, this layer knows nothing about databases or brokers. It just thinks.

**Infrastructure layer — the hands.** `app/infrastructure` does all the talking: PostgreSQL, Redis, brokers, external news APIs. If the outside world is involved, the code lives here.

## Why bother with layers?

Because the brain becomes easy to test. Since the domain layer doesn't know about databases, you can test a strategy with fake data in milliseconds, with zero setup. And if you ever switch brokers or databases, the brain doesn't change at all.

## Where the code starts

When the service boots, it runs `app/main.py`, which sets up FastAPI. During development you start it with uvicorn. For paper trading (real prices, fake money), the repo has two small scripts:

```bash
./start_paper_trading.sh   # start
./stop_paper_trading.sh    # stop
```

## Want to go deeper?

- `docs/architecture.md` — the classic architecture overview, more detail.
- `docs/developer/SYSTEM_OVERVIEW.md` — the developer's version.
- [The life of a trade](02-life-of-a-trade.md) — the next page in this series.
