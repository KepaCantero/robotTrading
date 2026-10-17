# The folder map

Open `app/` and you'll find seventeen folders. That's a lot, but they group into six simple ideas:

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 470" role="img" aria-label="Map of the app folders, grouped by layer: front door, organizers, the brain, plumbing, time machines, guards">
  <rect x="1" y="1" width="758" height="468" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="20" y="20" width="150" height="54" rx="10" fill="#4D96FF" stroke="#2B2D42" stroke-width="2"/>
    <text x="95" y="53" font-size="13.5" font-weight="bold" fill="#FFFFFF">front door</text>
    <rect x="190" y="20" width="110" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="245" y="53" font-size="14" font-weight="bold" fill="#2B2D42">api</text>
    <rect x="312" y="20" width="140" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="382" y="53" font-size="14" font-weight="bold" fill="#2B2D42">presentation</text>

    <rect x="20" y="92" width="150" height="54" rx="10" fill="#6BCB77" stroke="#2B2D42" stroke-width="2"/>
    <text x="95" y="125" font-size="13.5" font-weight="bold" fill="#2B2D42">organizers</text>
    <rect x="190" y="92" width="140" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="260" y="125" font-size="14" font-weight="bold" fill="#2B2D42">application</text>
    <rect x="342" y="92" width="110" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="397" y="125" font-size="14" font-weight="bold" fill="#2B2D42">services</text>

    <rect x="20" y="164" width="150" height="54" rx="10" fill="#FFD93D" stroke="#2B2D42" stroke-width="2"/>
    <text x="95" y="197" font-size="13.5" font-weight="bold" fill="#2B2D42">the brain</text>
    <rect x="190" y="164" width="110" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="245" y="197" font-size="14" font-weight="bold" fill="#2B2D42">domain</text>
    <rect x="312" y="164" width="110" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="367" y="197" font-size="14" font-weight="bold" fill="#2B2D42">engines</text>

    <rect x="20" y="236" width="150" height="54" rx="10" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2"/>
    <text x="95" y="269" font-size="13.5" font-weight="bold" fill="#FFFFFF">plumbing</text>
    <rect x="190" y="236" width="150" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="265" y="269" font-size="14" font-weight="bold" fill="#2B2D42">infrastructure</text>
    <rect x="352" y="236" width="100" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="402" y="269" font-size="14" font-weight="bold" fill="#2B2D42">shared</text>
    <rect x="464" y="236" width="90" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="509" y="269" font-size="14" font-weight="bold" fill="#2B2D42">core</text>

    <rect x="20" y="308" width="150" height="54" rx="10" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2"/>
    <text x="95" y="341" font-size="13.5" font-weight="bold" fill="#FFFFFF">time machines</text>
    <rect x="190" y="308" width="140" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="260" y="341" font-size="14" font-weight="bold" fill="#2B2D42">backtesting</text>
    <rect x="342" y="308" width="120" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="402" y="341" font-size="14" font-weight="bold" fill="#2B2D42">simulation</text>

    <rect x="20" y="380" width="150" height="54" rx="10" fill="#2B2D42" stroke="#2B2D42" stroke-width="2"/>
    <text x="95" y="413" font-size="13.5" font-weight="bold" fill="#FFFFFF">guards &amp; alarms</text>
    <rect x="190" y="380" width="110" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="245" y="413" font-size="14" font-weight="bold" fill="#2B2D42">security</text>
    <rect x="312" y="380" width="70" height="54" rx="10" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="347" y="413" font-size="14" font-weight="bold" fill="#2B2D42">sre</text>
  </g>
</svg>

## The same map, in words

| Folder | In one line |
|---|---|
| `app/api` | HTTP endpoints — where requests come in |
| `app/presentation` | what the user sees: dashboards, formatting |
| `app/application` | use cases — the order of the steps |
| `app/services` | supporting services around the use cases |
| `app/domain` | strategies, portfolio math, trading rules |
| `app/engines` | data, strategy, risk, execution, portfolio and event engines |
| `app/infrastructure` | databases, brokers, external APIs |
| `app/shared` | small utilities many layers use |
| `app/core` | configuration and the basics |
| `app/backtesting` | run strategies on the past to see how they'd have done |
| `app/simulation` | pretend money, real prices |
| `app/security` | authentication and protection |
| `app/sre` | monitoring, alerts, keeping the thing alive |

## Two honest footnotes

This map is simplified on purpose. Some folders sit between colors — `engines`, for example, could argue it belongs to the domain *or* to the application layer. Don't worry about winning that argument. If you remember "front door, organizers, brain, plumbing, time machines, guards", you already know 90% of it.

And `tests/` isn't in the picture because it doesn't live inside `app/` — but it watches over everything. When you change the brain, the tests are what tell you if it still thinks straight.
