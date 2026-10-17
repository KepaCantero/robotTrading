# The SRE's guide

Who this is for: you keep the service alive. You care about startup, ports, logs, failure behavior, and what to check when it pages you.

## Your mental model

Docker Compose runs PostgreSQL and Redis, uvicorn runs the API on port 8000, and NiceGUI serves dashboards on 8501 or 8503. Circuit breakers wrap every outside call: five failures open the circuit, five quiet minutes move it to half-open, three good tests close it.

A second breaker watches the market itself, using SPY and VIX, and can pause all trading. The `app/sre` folder holds the monitoring and alerts on top.

## Read this first

1. [The risk engine](06-risk-engine.md) — both breakers, their thresholds, and how trading resumes.
2. [The dashboard](11-dashboard.md) — ports, the docs mount, and how the app boots.
3. [How the system works](01-how-the-system-works.md) — what runs where, and the paper trading scripts.
4. [The component playbook](13-component-playbook.md) — per-component runbook notes.

## Your flows

- Know your breakers: [the risk engine](06-risk-engine.md) — API breaker states, market levels, 60-second resume loop.
- Serve the humans: [the dashboard](11-dashboard.md) — build docs, mount `/docs`, pick the port.
- Understand the loop you're keeping alive: [the life of a trade](02-life-of-a-trade.md).
- Watch the money paths: [execution](07-execution.md) and [the portfolio](08-portfolio.md).
- Know who can call what: [security](10-security.md) — lockouts will look like outages.

## Your commands

```bash
make up            # compose: postgres, redis, API on :8000
make down          # stop services
make logs          # follow compose logs
make health        # curl /health on :8000
make docs-build    # refresh site/ so /docs works
make dashboard     # docs build, then the app on :8503
```

## Watch out

- `/docs/` shows a placeholder until `site/` exists. Run `make docs-build` first; `make dashboard` does it for you.
- Ctrl+C stops only the dashboard. The paper-script API survives in the background — the stop script kills it via `.api_server.pid`.
- `make clean` runs `docker-compose down -v`. Volumes go too, and whatever lived in them.
- The market breaker resumes trading on its own after a halt. Don't restart the service to "fix" it.
