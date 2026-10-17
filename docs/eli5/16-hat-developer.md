# The developer's guide

Who this is for: you change the code. You need to know where a change goes, how to check it, and which house rules will bite you in review.

## Your mental model

Four layers pass requests down and answers up: API, application, domain, infrastructure. The domain layer is the brain and knows nothing about databases or brokers, so you can test it with fake data in milliseconds.

The engines do the live work: data, strategy, risk, execution, portfolio. When you forget which layer you're in, the folder map settles it.

## Read this first

1. [How the system works](01-how-the-system-works.md) — the layer rules your patch must respect.
2. [The folder map](03-folder-map.md) — where a new file goes, group by group.
3. [Strategies](05-strategies.md) — `BaseStrategy`, `Signal`, and the exact files behind each brain.
4. [The life of a trade](02-life-of-a-trade.md) — the loop your code ends up serving.
5. [The component playbook](13-component-playbook.md) — per-component notes for deeper changes.

## Your flows

- Place a change in the right layer: [the folder map](03-folder-map.md).
- Add or tune a strategy: [strategies](05-strategies.md) — extend `BaseStrategy`, implement `generate_signals()` and `risk_check()`.
- Feed data in: [the data pipeline](04-data-pipeline.md) — sources, normalizer, cleaning, cache.
- Gate a trade: [the risk engine](06-risk-engine.md) — validators, compliance, breakers.
- Fill orders and charge costs: [execution](07-execution.md).

## Your commands

```bash
make lint          # ruff check + mypy
make type-check    # mypy alone
make format        # ruff format + autofix
make test          # pytest, verbose
make test-cov      # same, but fails under 80% coverage
```

## Watch out

- `engines` straddles the domain and application layers. Don't win that argument — match your neighbors.
- The test suite has known failures. Check the baseline before you trust a red run as yours.
- `make test-cov` hard-fails below 80% coverage, even with green tests.
- State machines live in `app/domain/models/` (`order.py`, `signal.py`). Touch them and half the system feels it.
