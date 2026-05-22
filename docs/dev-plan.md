# Development Plan — PFM User Journey Tracker

---

## Infrastructure

| | |
|---|---|
| **VPS IP** | `72.62.148.226` |
| **Subdomain** | `uj.pfm-qa.com` → A record → `72.62.148.226` |
| **SSH** | `ssh root@72.62.148.226` |
| **Deploy path** | `/var/www/pfm-uj/` |
| **Git repo** | `https://github.com/ri5pekt/pfm-user-jurney.git` |
| **Deploy method** | SSH → `git pull` → `docker compose build && up -d` |
| **Host nginx** | Already running — manages other projects on port 80/443 |
| **Our nginx** | NOT a Docker service in prod — host nginx proxies to our containers |

> **Critical:** The VPS runs other projects. Never touch `/etc/nginx/sites-enabled/` configs belonging to other projects. Our config lives at `/etc/nginx/sites-available/uj-pfm-qa` only.

---

## Domain & Routing (single subdomain)

| Path | Service |
|---|---|
| `POST uj.pfm-qa.com/p` | Collector API (event ingestion) |
| `uj.pfm-qa.com/admin/` | Vue 3 dashboard (frontend) |
| `uj.pfm-qa.com/api/` | Admin API (dashboard data) |

nginx on VPS acts as reverse proxy for all three. SSL via Let's Encrypt when ready (certbot, single command).

---

## Monorepo Structure

```
pfm-user-jurney/
├── collector/          # Node.js + TS — receives POST /p events
├── worker/             # Node.js + TS — drains Redis → PostgreSQL
├── admin-api/          # Node.js + TS — aggregation endpoints for dashboard
├── frontend/           # Vue 3 + Vite + PrimeVue + Cytoscape.js
├── shared/             # Shared TypeScript types (events, sessions, etc.)
├── nginx/
│   ├── dev.conf        # local dev Docker nginx config
│   ├── prod.conf       # (unused — host nginx owns prod)
│   └── vps-site.conf   # host nginx config → copy to /etc/nginx/sites-available/
├── scripts/
│   ├── migrate.sql     # DB schema + indexes
│   ├── deploy.sh       # VPS pull + rebuild
│   └── test-page/
│       └── index.html  # smoke-test page for DNS/nginx verification
├── deploy/
│   └── vps_init.py     # paramiko script — first-time VPS setup + test page upload
├── docker-compose.yml       # production (no Docker nginx — host nginx proxies in)
├── docker-compose.dev.yml   # local dev (hot reload + Docker nginx)
└── docs/
    ├── user-journey-tracker.md
    └── dev-plan.md
```

---

## Tech Stack

| Layer | Choice |
|---|---|
| Collector API | Node.js + Express + TypeScript |
| Worker | Node.js + TypeScript (standalone process) |
| Admin API | Node.js + Express + TypeScript |
| Frontend | Vue 3 + Vite + PrimeVue + Cytoscape.js |
| Queue | Redis (latest) |
| Database | PostgreSQL 16 |
| Auth | JWT — login page in frontend, token validated by admin API |
| Dev | nodemon + ts-node (APIs), Vite HMR (frontend) |
| VPS Proxy | nginx (existing) + reverse proxy config for `uj.pfm-qa.com` |
| SSL | Let's Encrypt / certbot (enable on deploy) |
| Container | Docker Compose (dev + prod profiles) |

---

## Phase 1 — Data Collection

Build order:

- [ ] 1. **Repo scaffold** — monorepo folders, `docker-compose.yml`, `docker-compose.dev.yml`, `.env.example`
- [ ] 2. **Database schema** — `scripts/migrate.sql`: `events` table + indexes on `session_id`, `timestamp`
- [ ] 3. **Collector API** — `POST /p`, Origin validation, bot filter, push to Redis queue
- [ ] 4. **Worker** — pulls from Redis in batches, bulk-inserts into PostgreSQL
- [ ] 5. **Tracking script** — vanilla JS (`app.js`), UUID session, 2hr expiry, fires `POST /p` silently
- [ ] 6. **nginx config** — local dev config + VPS prod config routing `/p` to collector
- [ ] 7. **Local smoke test** — `docker compose -f docker-compose.dev.yml up`, verify end-to-end

**Exit criteria:** A page visit writes a row to PostgreSQL.

---

## Phase 2 — Admin Dashboard

- [ ] 1. **Admin API** — endpoints: sessions list, journey graph data, traffic sources, time filters
- [ ] 2. **JWT auth** — `POST /api/auth/login` → token; middleware guards all `/api/` routes
- [ ] 3. **Frontend scaffold** — Vue 3 + Vite + PrimeVue, router, auth store (Pinia)
- [ ] 4. **Login page** — simple form, stores JWT in `localStorage`
- [ ] 5. **Journey graph** — Cytoscape.js: nodes = pages, edges = transitions, thickness = volume, color = traffic source
- [ ] 6. **Funnel view** — PrimeVue table + chart showing drop-off between pages
- [ ] 7. **Time filters** — today / 7 days / custom range (PrimeVue DatePicker)
- [ ] 8. **nginx** — add `/admin/` and `/api/` routing to VPS config

**Exit criteria:** Login → see a live journey graph from real PostgreSQL data.

---

## Phase 3 — Analytics Expansion

- [ ] Funnel builder (user-defined page sequences)
- [ ] Bot filtering refinement (headless browser detection, known bot UA lists)
- [ ] Additional event types (`add_to_cart`, `purchase`, `checkout_start`, `exit`, `click`)
- [ ] Performance optimization (composite indexes, materialized views, query caching)

---

## VPS Port Map

Host nginx owns ports 80/443. Docker containers bind to `127.0.0.1` only — never exposed publicly.

| Service | Host binding | Container port | Who connects |
|---|---|---|---|
| Collector API | `127.0.0.1:3101` | `3001` | host nginx → proxy_pass |
| Admin API | `127.0.0.1:3102` | `3002` | host nginx → proxy_pass |
| Frontend (prod static) | — | — | served directly by host nginx from `/var/www/pfm-uj/frontend/` |
| Frontend (Vite dev) | `localhost:5173` | `5173` | browser direct (dev only) |
| Redis | internal Docker net only | `6379` | worker + collector |
| PostgreSQL 16 | internal Docker net only | `5432` | worker + admin-api |

> **Rule:** If a port above conflicts with an existing project on the VPS, increment it (e.g. 3101 → 3111) and update both `docker-compose.yml` and `nginx/vps-site.conf`.

---

## SSL (Let's Encrypt)

Once HTTP is confirmed working:

```bash
certbot --nginx -d uj.pfm-qa.com --non-interactive --agree-tos \
  --email denis@particleformen.com --redirect
systemctl reload nginx
```
