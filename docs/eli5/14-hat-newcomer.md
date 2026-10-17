# The newcomer's guide

Who this is for: it's your first days with this repo. You don't need to trade or to write Python yet. You just need to find your way around without drowning in folder names.

## Your mental model

This is one Python service that watches prices and decides on trades by itself. It runs a loop: fresh data in, a signal out, a risk check, then the order and the bookkeeping.

You can watch the whole thing from a browser. Paper mode trades fake money against real prices, so nothing you click can cost you anything. Start there.

## Read this first

1. [How the system works](01-how-the-system-works.md) — the layer cake; every other page assumes you know it.
2. [The life of a trade](02-life-of-a-trade.md) — one full loop, from "the price moved" to "position updated".
3. [The folder map](03-folder-map.md) — seventeen folders in six groups; the maze stops feeling random.
4. [The dashboard](11-dashboard.md) — the screens you'll actually click on, and why docs ride along inside.
5. [Security](10-security.md) — why every API call wants a key, so you don't fight the door blindly.

## Your flows

- Get the big picture and watch a request walk the layers: [how the system works](01-how-the-system-works.md).
- Follow one trade through its six steps: [the life of a trade](02-life-of-a-trade.md).
- Find code by folder instead of by memory: [the folder map](03-folder-map.md).
- See it live with fake money: paper trading in [execution](07-execution.md).
- Watch runs and results from the browser: [the dashboard](11-dashboard.md).

## Your commands

```bash
make dashboard                      # build docs, then serve the app on :8503
./scripts/start_paper_trading.sh    # API on :8000 + dashboard on :8501, paper money
./scripts/stop_paper_trading.sh     # kill the background API server
make test                           # run the test suite
```

## Watch out

- GitHub strips the inline diagrams from these pages. Read them in the dashboard at `/docs/` or in VS Code's preview.
- `/docs/` only works after a build. `make dashboard` builds for you; starting the bare app doesn't.
- `make test` has known failures. Read the output before you assume you broke something.
- In paper mode, Ctrl+C stops only the dashboard. The API keeps running, so use the stop script.
- The start script opens `.env` for editing if it's missing. That file holds real keys — don't commit it.
