# How the app runs

## The short version

The same Python app runs in four places: your laptop, a Docker stack, a paper trading setup, and production. Each step up adds realer pieces around unchanged code. Docker packs the app into one image, and Compose wires it to PostgreSQL and Redis on your machine. For the real thing the repo offers two roads: Terraform builds an AWS box, or Kubernetes runs the API as three self-healing pods.

## The ladder of environments

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 380" role="img" aria-label="Diagram of four environments: local dev, docker dev, paper trading, production, each adding more real pieces">
  <defs>
    <marker id="ladArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="378" rx="14" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="20" y="272" width="160" height="76" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="100" y="298" font-size="15" font-weight="bold" fill="#FFFFFF">Local dev</text>
    <text x="100" y="318" font-size="11.5" fill="#FFFFFF">uvicorn, auto-reload</text>
    <text x="100" y="336" font-size="11.5" fill="#FFFFFF">make api-dev · make db</text>
    <line x1="182" y1="286" x2="198" y2="240" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#ladArrow)"/>
    <rect x="200" y="188" width="160" height="76" rx="12" fill="#6BCB77" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="280" y="214" font-size="15" font-weight="bold" fill="#2B2D42">Docker dev</text>
    <text x="280" y="234" font-size="11.5" fill="#2B2D42">postgres, redis, nginx</text>
    <text x="280" y="252" font-size="11.5" fill="#2B2D42">make dev</text>
    <line x1="362" y1="202" x2="378" y2="156" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#ladArrow)"/>
    <rect x="380" y="104" width="160" height="76" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="460" y="130" font-size="15" font-weight="bold" fill="#2B2D42">Paper trading</text>
    <text x="460" y="150" font-size="11.5" fill="#2B2D42">real prices, fake money</text>
    <text x="460" y="168" font-size="11.5" fill="#2B2D42">start_paper_trading.sh</text>
    <line x1="542" y1="118" x2="558" y2="72" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#ladArrow)"/>
    <rect x="560" y="20" width="160" height="76" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="640" y="46" font-size="15" font-weight="bold" fill="#FFFFFF">Production</text>
    <text x="640" y="66" font-size="11.5" fill="#FFFFFF">AWS or Kubernetes</text>
    <text x="640" y="84" font-size="11.5" fill="#FFFFFF">make prod · make deploy</text>
    <text x="380" y="366" font-size="12" fill="#2B2D42">each rung adds realer pieces</text>
  </g>
</svg>

**Local dev — just Python.** Run `make api-dev` and uvicorn serves the API on port 8000 with auto-reload. `make db` starts only PostgreSQL and Redis as containers. Fast to start, fast to break, and the brain layers need zero setup.

**Docker dev — the whole zoo.** `make dev` runs `docker-compose.dev.yml`. You get the app, PostgreSQL, Redis, nginx, worker and scheduler containers, plus Flower, Prometheus and Grafana. Your source folder mounts into the container, so edits show up at once.

**Paper trading — the dress rehearsal.** `scripts/start_paper_trading.sh` starts the API in the background, then the NiceGUI dashboard in front of it. Stop everything with `stop_paper_trading.sh`. Real prices flow, no cash moves.

**Production — pick a road.** `make prod` (or `make deploy`) brings up `docker-compose.prod.yml` against managed AWS databases. Or you apply the Kubernetes manifests in `deploy/k8s`. Same Docker image either way; only the surroundings change.

## What production actually looks like

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 445" role="img" aria-label="Diagram of production: terraform lane with EC2, RDS and ElastiCache, and a kubernetes lane with ingress, pods, postgres and redis">
  <defs>
    <marker id="topArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="443" rx="14" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="280" y="14" width="200" height="52" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="36" font-size="15" font-weight="bold" fill="#FFFFFF">You</text>
    <text x="380" y="56" font-size="11.5" fill="#FFFFFF">api.algotrading.com</text>
    <line x1="340" y1="68" x2="188" y2="96" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#topArrow)"/>
    <line x1="420" y1="68" x2="572" y2="96" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#topArrow)"/>
    <rect x="20" y="100" width="330" height="316" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="185" y="126" font-size="15" font-weight="bold" fill="#FFFFFF">Terraform — AWS</text>
    <text x="185" y="144" font-size="11" fill="#FFFFFF">main.tf + user_data.sh</text>
    <rect x="40" y="156" width="290" height="78" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="185" y="180" font-size="13.5" font-weight="bold" fill="#2B2D42">EC2 t3.medium</text>
    <text x="185" y="200" font-size="11" fill="#2B2D42">compose: app, nginx, redis</text>
    <text x="185" y="218" font-size="11" fill="#2B2D42">systemd + cron babysit</text>
    <line x1="130" y1="236" x2="116" y2="254" stroke="#2B2D42" stroke-width="2" marker-end="url(#topArrow)"/>
    <line x1="240" y1="236" x2="254" y2="254" stroke="#2B2D42" stroke-width="2" marker-end="url(#topArrow)"/>
    <rect x="40" y="260" width="140" height="74" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="110" y="284" font-size="13" font-weight="bold" fill="#2B2D42">RDS</text>
    <text x="110" y="302" font-size="11" fill="#2B2D42">PostgreSQL</text>
    <text x="110" y="318" font-size="11" fill="#2B2D42">encrypted, 7-day</text>
    <text x="110" y="334" font-size="11" fill="#2B2D42">backups</text>
    <rect x="190" y="260" width="140" height="74" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="260" y="284" font-size="13" font-weight="bold" fill="#2B2D42">ElastiCache</text>
    <text x="260" y="302" font-size="11" fill="#2B2D42">Redis</text>
    <text x="260" y="318" font-size="11" fill="#2B2D42">encrypted</text>
    <text x="185" y="362" font-size="11" fill="#FFFFFF">databases hide in</text>
    <text x="185" y="378" font-size="11" fill="#FFFFFF">private subnets</text>
    <rect x="410" y="100" width="330" height="316" rx="14" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="575" y="126" font-size="15" font-weight="bold" fill="#FFFFFF">Kubernetes — deploy/k8s</text>
    <text x="575" y="144" font-size="11" fill="#FFFFFF">helm values mirror this</text>
    <rect x="430" y="156" width="290" height="62" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2"/>
    <text x="575" y="180" font-size="13.5" font-weight="bold" fill="#FFFFFF">nginx ingress</text>
    <text x="575" y="200" font-size="11" fill="#FFFFFF">TLS + rate limit</text>
    <line x1="575" y1="220" x2="575" y2="234" stroke="#2B2D42" stroke-width="2" marker-end="url(#topArrow)"/>
    <rect x="430" y="238" width="290" height="70" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2"/>
    <text x="575" y="262" font-size="13.5" font-weight="bold" fill="#FFFFFF">API pods x3</text>
    <text x="575" y="280" font-size="11" fill="#FFFFFF">HPA grows 3-10</text>
    <text x="575" y="296" font-size="11" fill="#FFFFFF">probes hit /health</text>
    <line x1="505" y1="310" x2="505" y2="326" stroke="#2B2D42" stroke-width="2" marker-end="url(#topArrow)"/>
    <line x1="645" y1="310" x2="645" y2="326" stroke="#2B2D42" stroke-width="2" marker-end="url(#topArrow)"/>
    <rect x="430" y="330" width="140" height="56" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="500" y="354" font-size="13" font-weight="bold" fill="#2B2D42">PostgreSQL</text>
    <text x="500" y="372" font-size="11" fill="#2B2D42">in-cluster</text>
    <rect x="580" y="330" width="140" height="56" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2"/>
    <text x="650" y="354" font-size="13" font-weight="bold" fill="#2B2D42">Redis</text>
    <text x="650" y="372" font-size="11" fill="#2B2D42">in-cluster</text>
    <text x="575" y="404" font-size="11" fill="#FFFFFF">Prometheus + Grafana watch</text>
    <text x="380" y="437" font-size="12" fill="#2B2D42">two roads, one image</text>
  </g>
</svg>

**The Terraform road.** `infrastructure/terraform/main.tf` builds a VPC with public and private subnets in two zones. Inside it: an EC2 instance, RDS PostgreSQL and ElastiCache Redis. Both databases sit in private subnets, encrypted, with seven days of backups. On first boot, `user_data.sh` installs Docker, writes a `.env` with the database endpoints, and registers a systemd service. A cron job checks the containers every five minutes; another one backs up nightly.

**The Kubernetes road.** The Deployment in `deploy/k8s` runs three API pods with rolling updates and health probes on `/health`. A Horizontal Pod Autoscaler grows them from three to ten pods when CPU passes seventy percent. The ingress terminates TLS through cert-manager and rate-limits requests. Helm values in `deploy/helm` mirror the same numbers.

Two honest notes. The `worker` and `scheduler` Docker targets exist but still just run uvicorn, because no Celery app module exists yet. And the Kubernetes image is a placeholder, `ghcr.io/YOUR_ORG`, so point it at your own registry first.

One moving part sits under both roads: migrations. Alembic schema changes live in `app/infrastructure/persistence/database/migrations`. Run `make migrate` to apply them, and `make migration name="add table"` to create one.

## Ports and processes

- `8000` — the API. uvicorn locally, in every container, and in every pod.
- `8001` — the metrics port for the API in Kubernetes (`/metrics`).
- `8501` — the dashboard address that `start_paper_trading.sh` prints.
- `8503` — where the NiceGUI dashboard actually listens (`make dashboard`).
- `5432` — PostgreSQL: compose container, RDS, or in-cluster pod.
- `6379` — Redis: compose container, ElastiCache, or in-cluster pod.
- `80 / 443` — nginx and the Kubernetes ingress. HTTPS ends here.
- `9090` Prometheus · `3000` Grafana · `5601` Kibana · `9200` Elasticsearch · `5555` Flower.
- `7497` — IBKR's TWS gateway, from `.env.prod.example`.

## Where it lives

- `Dockerfile` — one image, five build targets: production, development, testing, worker, scheduler.
- `docker-compose.yml`, `.dev.yml`, `.prod.yml`, `.logging.yml` — the base, dev, prod and ELK stacks.
- `deploy/` — k8s manifests, Helm values, nginx configs, Prometheus and Grafana setup.
- `infrastructure/terraform/` — `main.tf` and `user_data.sh`, everything AWS.
- `Makefile` — every shortcut: `up`, `down`, `dev`, `build`, `deploy`, `prod`, `migrate`.
- `alembic.ini` — points Alembic at the migrations folder inside `app/`.
- `scripts/start_paper_trading.sh` and `stop_paper_trading.sh` — the rehearsal controls.

## Want to go deeper?

- [The SRE hat](18-hat-sre.md) — keeping all of this alive day to day.
- [Observability](27-observability.md) — the metrics and logs stack in detail.
- [The config atlas](24-config-atlas.md) — every knob, and where it's set.
