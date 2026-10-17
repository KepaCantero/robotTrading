# The Agent Swarm and Mission Control

## The short version

The Agent Swarm is a friendly costume for the CAPA 2 pipeline. CAPA 2 is the system's parametrization workflow: it turns your capital, goal and risk level into a final deploy decision. The swarm dresses its ten steps as "agents" with names, colors and status bubbles. Mission Control is the dashboard page (`/swarm`) where you launch a run and watch those agents work. Nothing here is simulated — each agent calls the real component, in order, in about a second.

## The swarm: ten agents and two helpers

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 380" role="img" aria-label="The swarm: the executor above ten agent boxes, with the event bus and the SQLite store below">
  <defs>
    <marker id="arrowA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker>
  </defs>
  <rect x="1" y="1" width="758" height="378" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="180" y="24" width="400" height="60" rx="14" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/><text x="380" y="49" font-size="15" font-weight="bold" fill="#2B2D42">Capa2PipelineExecutor</text><text x="380" y="70" font-size="11.5" fill="#2B2D42">runs the ten agents in order</text>
    <line x1="380" y1="84" x2="380" y2="110" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowA)"/>
    <rect x="30" y="116" width="132" height="56" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/><text x="96" y="140" font-size="12.5" font-weight="bold" fill="#2B2D42">T1.1</text><text x="96" y="158" font-size="10" fill="#2B2D42">Input Processor</text>
    <rect x="178" y="116" width="132" height="56" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/><text x="244" y="140" font-size="12.5" font-weight="bold" fill="#2B2D42">T2.1</text><text x="244" y="158" font-size="10" fill="#2B2D42">Profile Generator</text>
    <rect x="326" y="116" width="132" height="56" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/><text x="392" y="140" font-size="12.5" font-weight="bold" fill="#2B2D42">T3.1</text><text x="392" y="158" font-size="10" fill="#2B2D42">Module Parametrizer</text>
    <rect x="474" y="116" width="132" height="56" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/><text x="540" y="140" font-size="12.5" font-weight="bold" fill="#2B2D42">T4.1</text><text x="540" y="158" font-size="10" fill="#2B2D42">Backtest Orchestrator</text>
    <rect x="622" y="116" width="132" height="56" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/><text x="688" y="140" font-size="12.5" font-weight="bold" fill="#2B2D42">T5.1</text><text x="688" y="158" font-size="10" fill="#2B2D42">Validation Engine</text>
    <rect x="30" y="182" width="132" height="56" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/><text x="96" y="206" font-size="12.5" font-weight="bold" fill="#2B2D42">T6.1</text><text x="96" y="224" font-size="10" fill="#2B2D42">Strategy Recommender</text>
    <rect x="178" y="182" width="132" height="56" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/><text x="244" y="206" font-size="12.5" font-weight="bold" fill="#2B2D42">T7.1</text><text x="244" y="224" font-size="10" fill="#2B2D42">Portfolio Constructor</text>
    <rect x="326" y="182" width="132" height="56" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/><text x="392" y="206" font-size="12.5" font-weight="bold" fill="#2B2D42">T8.1</text><text x="392" y="224" font-size="10" fill="#2B2D42">Risk Scaling</text>
    <rect x="474" y="182" width="132" height="56" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/><text x="540" y="206" font-size="12.5" font-weight="bold" fill="#2B2D42">T9.1</text><text x="540" y="224" font-size="10" fill="#2B2D42">Reporting Generator</text>
    <rect x="622" y="182" width="132" height="56" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/><text x="688" y="206" font-size="12.5" font-weight="bold" fill="#2B2D42">T10.1</text><text x="688" y="224" font-size="10" fill="#2B2D42">Deploy Decision</text>
    <line x1="200" y1="238" x2="200" y2="296" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowA)"/>
    <text x="212" y="272" font-size="11" fill="#2B2D42" text-anchor="start">events</text>
    <line x1="560" y1="238" x2="560" y2="296" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowA)"/>
    <text x="572" y="272" font-size="11" fill="#2B2D42" text-anchor="start">run + events</text>
    <rect x="60" y="300" width="280" height="60" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/><text x="200" y="325" font-size="13" font-weight="bold" fill="#2B2D42">AgentEventBus</text><text x="200" y="345" font-size="11" fill="#2B2D42">in-process event pipe</text>
    <rect x="420" y="300" width="280" height="60" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/><text x="560" y="325" font-size="13" font-weight="bold" fill="#FFFFFF">SwarmRunStore</text><text x="560" y="345" font-size="11" fill="#FFFFFF">SQLite · swarm_runs.db</text>
  </g>
</svg>

Each agent is one real CAPA 2 component — the same code the API uses. The executor (Capa2PipelineExecutor) is the coordinator: it builds each agent's input, awaits it, and checks the result. The event bus is a small in-process pipe; every step publishes a message there. The store writes each run to SQLite, so nothing is lost when the page closes.

What the ten agents do, in their own plain words from the UI:

- **T1.1 Input Processor** — checks that capital, goal and time frame make sense.
- **T2.1 Profile Generator** — builds your investor profile and picks the modules.
- **T3.1 Module Parametrizer** — tunes each module's parameters for that profile.
- **T4.1 Backtest Orchestrator** — replays one year of history (AAPL, MSFT, GOOGL).
- **T5.1 Validation Engine** — checks the gates: costs, capital, feasibility.
- **T6.1 Strategy Recommender** — scores strategies and recommends the best fit.
- **T7.1 Portfolio Constructor** — splits capital across the enabled modules.
- **T8.1 Risk Scaling** — adjusts for market regime, volatility and drawdown.
- **T9.1 Reporting Generator** — writes the report: rating, strengths, weaknesses.
- **T10.1 Deploy Decision** — the verdict: APPROVED, CONDITIONAL or REJECTED.

It works like a relay race: the output of one agent becomes the input of the next. If a stage fails or crashes, the run stops there and every remaining agent is marked SKIPPED. Each finished stage pays 50 XP (experience points — a game score), and a full run adds a 100 XP bonus. Achievements also come from real outcomes: feasibility gate passed, deploy approved, clean run with no warnings.

## The journey of one mission

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 320" role="img" aria-label="A run flows from your form to the executor, to events, then into the store and the Mission Control page">
  <defs>
    <marker id="arrowB" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker>
  </defs>
  <rect x="1" y="1" width="758" height="318" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="30" y="56" width="180" height="88" rx="14" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/><text x="120" y="84" font-size="14" font-weight="bold" fill="#FFFFFF">You press</text><text x="120" y="104" font-size="12.5" fill="#FFFFFF">Run pipeline</text><text x="120" y="126" font-size="10.5" fill="#FFFFFF">capital · goal · risk</text>
    <line x1="210" y1="100" x2="250" y2="100" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowB)"/>
    <rect x="250" y="56" width="190" height="88" rx="14" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/><text x="345" y="84" font-size="14" font-weight="bold" fill="#2B2D42">Executor chains</text><text x="345" y="104" font-size="12.5" fill="#2B2D42">the ten agents</text><text x="345" y="126" font-size="10.5" fill="#2B2D42">T1.1 → T10.1</text>
    <line x1="440" y1="100" x2="480" y2="100" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrowB)"/>
    <rect x="480" y="56" width="250" height="88" rx="14" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/><text x="605" y="84" font-size="13" font-weight="bold" fill="#2B2D42">Each agent reports</text><text x="605" y="104" font-size="12" fill="#2B2D42">input · output · ms</text><text x="605" y="126" font-size="10.5" fill="#2B2D42">+50 XP each</text>
    <line x1="345" y1="144" x2="345" y2="206" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowB)"/>
    <text x="357" y="180" font-size="10.5" fill="#2B2D42" text-anchor="start">saved</text>
    <line x1="605" y1="144" x2="605" y2="206" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowB)"/>
    <text x="617" y="180" font-size="10.5" fill="#2B2D42" text-anchor="start">live · polled</text>
    <rect x="130" y="210" width="280" height="88" rx="14" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/><text x="270" y="238" font-size="14" font-weight="bold" fill="#FFFFFF">SwarmRunStore</text><text x="270" y="258" font-size="11.5" fill="#FFFFFF">swarm_runs.db — SQLite</text><text x="270" y="280" font-size="10.5" fill="#FFFFFF">one row + all events</text>
    <line x1="410" y1="254" x2="480" y2="254" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowB)"/>
    <text x="445" y="246" font-size="10.5" fill="#2B2D42">replay</text>
    <rect x="480" y="210" width="250" height="88" rx="14" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/><text x="605" y="238" font-size="14" font-weight="bold" fill="#FFFFFF">Mission Control</text><text x="605" y="258" font-size="11.5" fill="#FFFFFF">the /swarm page</text><text x="605" y="280" font-size="10.5" fill="#FFFFFF">cards · log · verdict</text>
  </g>
</svg>

You fill in four things on the left: capital, goal, risk level and time frame. Advanced options add a monthly target, the market regime and the volatility level. Press Run pipeline (or ALT+R) and the executor starts. The page polls the run every 250 ms, but redraws only when a version counter has moved — that counter bumps on every event. Click any step to see exactly what went in and what came out, as JSON.

The result card explains the verdict in plain words, with the key numbers next to it. Technical detail hides behind a disclosure: a terminal-style execution log and a bar chart of step durations. History & replay lists past runs; pick one, set a speed, and watch it again (ALT+P). One small drift: the quickstart still calls the button "Launch Mission"; the page says "Run pipeline" today.

## What gets saved

The store (SwarmRunStore) is an async wrapper around SQLite, a single-file database. The file is `swarm_runs.db` at the repo root — `DEFAULT_SWARM_DB_PATH` in the code. It opens in WAL mode (write-ahead logging), so the dashboard and the API can share it safely. Two tables:

- `swarm_runs` — one row per mission: status, request, timestamps, total XP, achievements, results.
- `swarm_events` — one row per event, with a type like `stage_completed` and its JSON payload.

The API endpoint `POST /capa2/complete-workflow` uses the same executor and the same file. So a run started from code lands in the same history as one started from the page.

## The states of a run

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 365" role="img" aria-label="Agent states: IDLE to RUNNING to DONE, or RUNNING to FAILED and then SKIPPED; the run ends completed or failed">
  <defs>
    <marker id="arrowC" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/></marker>
  </defs>
  <rect x="1" y="1" width="758" height="363" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="40" y="56" width="110" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/><text x="95" y="82" font-size="13" font-weight="bold" fill="#2B2D42">IDLE</text><text x="95" y="102" font-size="10" fill="#2B2D42">waiting</text>
    <rect x="175" y="56" width="110" height="64" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/><text x="230" y="82" font-size="13" font-weight="bold" fill="#2B2D42">RUNNING</text><text x="230" y="102" font-size="10" fill="#2B2D42">working now</text>
    <rect x="310" y="56" width="110" height="64" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2"/><text x="365" y="82" font-size="13" font-weight="bold" fill="#2B2D42">DONE</text><text x="365" y="102" font-size="10" fill="#2B2D42">+50 XP</text>
    <rect x="445" y="56" width="110" height="64" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/><text x="500" y="82" font-size="13" font-weight="bold" fill="#FFFFFF">FAILED</text><text x="500" y="102" font-size="10" fill="#FFFFFF">error stored</text>
    <rect x="580" y="56" width="110" height="64" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/><text x="635" y="82" font-size="13" font-weight="bold" fill="#2B2D42">SKIPPED</text><text x="635" y="102" font-size="10" fill="#2B2D42">never ran</text>
    <line x1="150" y1="88" x2="175" y2="88" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <line x1="285" y1="88" x2="310" y2="88" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <line x1="555" y1="88" x2="580" y2="88" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <path d="M 230 120 C 230 178, 500 178, 500 120" fill="none" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <text x="365" y="170" font-size="11" fill="#2B2D42">if a stage fails</text>
    <text x="380" y="225" font-size="12" fill="#2B2D42">the whole run then ends as:</text>
    <rect x="140" y="245" width="150" height="56" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/><text x="215" y="270" font-size="13" font-weight="bold" fill="#2B2D42">running</text><text x="215" y="290" font-size="10" fill="#2B2D42">agents still working</text>
    <rect x="430" y="214" width="170" height="56" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/><text x="515" y="239" font-size="13" font-weight="bold" fill="#FFFFFF">completed</text><text x="515" y="259" font-size="10" fill="#FFFFFF">verdict + XP bonus</text>
    <rect x="430" y="286" width="170" height="56" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/><text x="515" y="311" font-size="13" font-weight="bold" fill="#FFFFFF">failed</text><text x="515" y="331" font-size="10" fill="#FFFFFF">log shows the error</text>
    <line x1="290" y1="273" x2="430" y2="242" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <text x="352" y="248" font-size="10.5" fill="#2B2D42">10/10 done</text>
    <line x1="215" y1="301" x2="430" y2="314" stroke="#2B2D42" stroke-width="2" marker-end="url(#arrowC)"/>
    <text x="310" y="335" font-size="10.5" fill="#2B2D42">a stage fails</text>
  </g>
</svg>

Each agent moves through five statuses: IDLE, RUNNING, DONE, FAILED or SKIPPED. The whole run has three: `running`, `completed` or `failed`. These exact words come from the code — the page just colors them.

## Where it lives in the code

- `app/services/agent_swarm/executor.py` — `Capa2PipelineExecutor`, `AGENT_SPECS` (the ten agents), `SwarmRunRequest`, XP constants.
- `app/services/agent_swarm/store.py` — `SwarmRunStore` and `DEFAULT_SWARM_DB_PATH` (repo-root `swarm_runs.db`).
- `app/services/agent_swarm/events.py` — the eight event types and the `AgentEventBus`.
- `app/services/agent_swarm/serialization.py` — `safe_json`, which turns any payload into readable JSON.
- `app/presentation/dashboard/nicegui_app/pages/swarm.py` — Mission Control itself: form, cards, log, replay.
- `app/presentation/dashboard/nicegui_app/components/agent_card.py` and `components/mission_log.py` — the step rows and the terminal log.
- `app/presentation/controllers/capa2_endpoints.py` — `POST /capa2/complete-workflow`, the API door into the same executor.

One neighbor is easy to mistake for swarm code: `components/run_comparison.py` compares two backtest runs for the History & Compare page. It has nothing to do with swarm missions.

## Want to go deeper?

- [The dashboard](11-dashboard.md) — the `/swarm` page in the context of the whole app.
- [Backtesting](09-backtesting.md) — what T4.1 actually replays.
- [The component playbook](13-component-playbook.md) — the logic each of the ten agents applies.
