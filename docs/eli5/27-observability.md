# Observability: logs, metrics and alerts

## The short version

Observability means you can ask the system a question and get an answer without writing new code. Questions like "why did we sell AAPL at 14:02?" or "is the robot even alive?"

The repo answers them with three tools. Logs record what happened, one line at a time. Metrics turn behavior into numbers you can chart. Alerts poke you when a number goes where it shouldn't. One of the three runs by default; the other two you switch on yourself.

## The three pillars

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 410" role="img" aria-label="The three pillars of observability: logs, metrics, alerts, and the real components in each">
  <defs>
    <marker id="arrowPillars27" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="408" rx="14" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="30" y="20" width="220" height="60" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="140" y="45" font-size="17" font-weight="bold" fill="#FFFFFF">Logs</text>
    <text x="140" y="66" font-size="12" fill="#FFFFFF">what happened, when</text>
    <rect x="30" y="96" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="140" y="122" font-size="12.5" font-weight="bold" fill="#2B2D42">logging_config.py</text>
    <text x="140" y="142" font-size="11" fill="#2B2D42">runs on import</text>
    <rect x="30" y="172" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="140" y="198" font-size="12.5" font-weight="bold" fill="#2B2D42">logs/ rotating files</text>
    <text x="140" y="218" font-size="11" fill="#2B2D42">all · warnings · errors</text>
    <rect x="30" y="248" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="140" y="274" font-size="12.5" font-weight="bold" fill="#2B2D42">correlation ID per line</text>
    <text x="140" y="294" font-size="11" fill="#2B2D42">secrets are scrubbed</text>
    <rect x="30" y="324" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="140" y="350" font-size="12.5" font-weight="bold" fill="#2B2D42">Filebeat → Logstash</text>
    <text x="140" y="370" font-size="11" fill="#2B2D42">Elasticsearch · Kibana :5601</text>
    <rect x="270" y="20" width="220" height="60" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="45" font-size="17" font-weight="bold" fill="#FFFFFF">Metrics</text>
    <text x="380" y="66" font-size="12" fill="#FFFFFF">behavior as numbers</text>
    <rect x="270" y="96" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="122" font-size="12.5" font-weight="bold" fill="#2B2D42">golden_signals.py</text>
    <text x="380" y="142" font-size="11" fill="#2B2D42">latency · traffic · errors</text>
    <rect x="270" y="172" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="198" font-size="12.5" font-weight="bold" fill="#2B2D42">saturation (psutil)</text>
    <text x="380" y="218" font-size="11" fill="#2B2D42">CPU · RAM · disk</text>
    <rect x="270" y="248" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="274" font-size="12.5" font-weight="bold" fill="#2B2D42">metrics_collector.py</text>
    <text x="380" y="294" font-size="11" fill="#2B2D42">batches 1000 points</text>
    <rect x="270" y="324" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="380" y="350" font-size="12.5" font-weight="bold" fill="#2B2D42">QuestDB time-series</text>
    <text x="380" y="370" font-size="11" fill="#2B2D42">keeps 90 days</text>
    <rect x="510" y="20" width="220" height="60" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="620" y="45" font-size="17" font-weight="bold" fill="#2B2D42">Alerts</text>
    <text x="620" y="66" font-size="12" fill="#2B2D42">who gets told</text>
    <rect x="510" y="96" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="620" y="122" font-size="12.5" font-weight="bold" fill="#2B2D42">12 rule templates</text>
    <text x="620" y="142" font-size="11" fill="#2B2D42">drawdown · latency · costs</text>
    <rect x="510" y="172" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="620" y="198" font-size="12.5" font-weight="bold" fill="#2B2D42">AlertManager</text>
    <text x="620" y="218" font-size="11" fill="#2B2D42">dedups the noise</text>
    <rect x="510" y="248" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="620" y="274" font-size="12.5" font-weight="bold" fill="#2B2D42">fatigue prevention</text>
    <text x="620" y="294" font-size="11" fill="#2B2D42">groups and ranks</text>
    <rect x="510" y="324" width="220" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="620" y="350" font-size="12.5" font-weight="bold" fill="#2B2D42">Slack · Telegram · email</text>
    <text x="620" y="370" font-size="11" fill="#2B2D42">Discord · plain webhook</text>
  </g>
</svg>

**Logs — the diary.** Every warning and error lands in rotating files under `logs/`: `all.log` for INFO and up, plus separate `warnings.log` and `errors.log`. Each line gets a correlation ID — a short tag that ties every line of one request together — and timing in milliseconds. A filter scrubs passwords and API keys before they touch disk, so secrets never reach the files.

For real searching, the repo ships an ELK stack in `docker-compose.logging.yml`. Filebeat tails the log files, Logstash enriches each line, Elasticsearch indexes them, and Kibana gives you search at `localhost:5601`. Metricbeat adds host CPU and RAM; Curator deletes old data. It's opt-in — start it with `docker compose -f docker-compose.logging.yml up -d`.

**Metrics — the numbers.** Two collectors feed the pillar. `golden_signals.py` tracks Google SRE's four health signals: latency (how slow), traffic (how busy), errors (how many fail) and saturation (how full the machine is). Saturation comes from psutil, which reads CPU, RAM and disk straight from the OS. Trading numbers flow through `metrics_collector.py` into QuestDB — a database built for timestamped numbers, called a time-series database. It batches up to 1000 points per write and keeps 90 days.

**Alerts — the phone call.** The `AlertingOrchestrator` wires four pieces together: a rule engine, an alert manager, a metrics alerter and a notification dispatcher. Twelve rule templates ship by default. Three templates watch drawdown at 5, 10 and 15 percent; 15 halts trading. Then come a volatility spike, cost overruns, a Sharpe drop and two or four losses in a row. The last three watch the machine: fill ratio under 95 percent, latency over a second, and error rate over 5 percent.

The manager dedups — dedup means one incident makes one alert, not fifty copies. Fatigue prevention then groups and ranks what reaches you. Five channels can deliver: Slack, Telegram, Discord, email over SMTP, and a plain webhook.

## From break to your phone

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 190" role="img" aria-label="Flow: something breaks, a log line is written, a metric lands in QuestDB, a rule fires, the dispatcher dedups, Slack pings you">
  <defs>
    <marker id="arrowFlow27" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="188" rx="14" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <text x="380" y="30" font-size="13" font-weight="bold" fill="#2B2D42">an error's journey to your phone</text>
    <rect x="20" y="52" width="104" height="92" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="72" y="90" font-size="12.5" font-weight="bold" fill="#FFFFFF">something</text>
    <text x="72" y="107" font-size="12.5" font-weight="bold" fill="#FFFFFF">breaks</text>
    <text x="72" y="128" font-size="10.5" fill="#FFFFFF">an order fails</text>
    <line x1="124" y1="98" x2="140" y2="98" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowFlow27)"/>
    <rect x="140" y="52" width="104" height="92" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="192" y="90" font-size="12.5" font-weight="bold" fill="#2B2D42">log line</text>
    <text x="192" y="107" font-size="10.5" fill="#2B2D42">written to</text>
    <text x="192" y="128" font-size="10.5" fill="#2B2D42">logs/errors.log</text>
    <line x1="244" y1="98" x2="260" y2="98" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowFlow27)"/>
    <rect x="260" y="52" width="104" height="92" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="312" y="90" font-size="12.5" font-weight="bold" fill="#FFFFFF">metric</text>
    <text x="312" y="107" font-size="10.5" fill="#FFFFFF">error rate,</text>
    <text x="312" y="128" font-size="10.5" fill="#FFFFFF">into QuestDB</text>
    <line x1="364" y1="98" x2="380" y2="98" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowFlow27)"/>
    <rect x="380" y="52" width="104" height="92" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="432" y="90" font-size="12.5" font-weight="bold" fill="#2B2D42">rule fires</text>
    <text x="432" y="107" font-size="10.5" fill="#2B2D42">error rate</text>
    <text x="432" y="128" font-size="10.5" fill="#2B2D42">over 5 percent</text>
    <line x1="484" y1="98" x2="500" y2="98" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowFlow27)"/>
    <rect x="500" y="52" width="104" height="92" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="552" y="90" font-size="12.5" font-weight="bold" fill="#2B2D42">dispatcher</text>
    <text x="552" y="107" font-size="10.5" fill="#2B2D42">dedup,</text>
    <text x="552" y="128" font-size="10.5" fill="#2B2D42">pick severity</text>
    <line x1="604" y1="98" x2="620" y2="98" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowFlow27)"/>
    <rect x="620" y="52" width="104" height="92" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="672" y="90" font-size="12.5" font-weight="bold" fill="#FFFFFF">Slack pings</text>
    <text x="672" y="107" font-size="12.5" font-weight="bold" fill="#FFFFFF">you</text>
    <text x="672" y="128" font-size="10.5" fill="#FFFFFF">Telegram · email too</text>
  </g>
</svg>

The loop runs once a minute by default: the alerter queries the metrics, the rules vote, and matching rules raise alerts through the dispatcher. The webhook URL comes from the `ALERT_WEBHOOK_URL` environment variable, which `config/environments/production.yaml` wires in. No URL set, the channel stays silent.

Two watchdogs sit beside the loop. A dead man's switch flips if the system goes quiet — no heartbeat means something ate the process. And the toil tracker in `app/sre/automation/` logs how many minutes humans spend on manual work, so you can prove what deserves automating.

## What runs today

File logging is wired: `logging_config.py` configures itself the moment it's imported, so the `logs/` files always exist. The rest is opt-in. Nothing in `app/main.py` starts the ELK stack, QuestDB writes or the alert loop. The production dashboard accepts an orchestrator, and the error-budget code expects one, but you have to hand it over. The full chain works; you just flip the switches.

## Where it lives in the code

- `app/infrastructure/logging/logging_config.py` — file logging, correlation IDs, secret scrubbing. Always on.
- `app/infrastructure/logging/trading_decision_logger.py` — a dedicated diary for every trade decision.
- `app/services/centralized_logging.py` — service-level structured logs for the ELK pipeline.
- `docker-compose.logging.yml` and `logging/` — the ELK stack and its Elasticsearch, Logstash, Kibana and Filebeat configs.
- `app/sre/monitoring/` — `golden_signals.py` and `trading_metrics.py`.
- `app/services/metrics_database/` — `questdb_connector.py`, `metrics_collector.py`, `metrics_query_engine.py`.
- `app/application/alerting/alerting_orchestrator.py` — the conductor that starts and stops the alert loop.
- `app/services/alerting_system/` — `rule_templates.py` (the 12 rules) and `notification_channels.py` (the five channels).
- `app/sre/alert_fatigue_prevention/` and `app/sre/dead_mans_switch/` — alert quality and the silence alarm.
- `docs/sre/GOLDEN_SIGNALS_MONITORING.md` and `docs/sre/TOIL_TRACKING.md` — the deeper manuals.

## Want to go deeper?

- [The SRE's guide](18-hat-sre.md) — the hat this page serves: breakers, ports, runbooks.
- [The dashboard](11-dashboard.md) — where health and alerts surface to humans.
- [Deployment](28-deployment.md) — how these pieces get started in each environment.
