# User Journey Tracker

> An anonymous, lightweight event tracking system for ecommerce websites with a powerful admin dashboard for visualizing user journeys, funnels, and traffic source analysis.

**Repository:** [https://github.com/ri5pekt/pfm-user-jurney.git](https://github.com/ri5pekt/pfm-user-jurney.git)

---

## Overview

The User Journey Tracker captures anonymous page-view events from a WooCommerce website and stores them in a dedicated external server, keeping the main website database clean and performant. An admin dashboard provides rich visualizations of how users navigate the site — from entry point to conversion or exit.

The system is designed with two core principles:
- **Zero impact on website performance** — fire-and-forget tracking, no response waiting
- **Full journey reconstruction** — every event contains enough data to rebuild the complete user path

---

## Architecture

```
[WordPress Site]
     |
     | (inline JS snippet)
     |
[Tracking Script]  ──→  POST /event  ──→  [Collector API]  ──→  [Redis Queue]
                                                                       |
                                                               [Worker Process]
                                                                       |
                                                              [PostgreSQL Database]
                                                                       |
                                                              [Admin API]  ──→  [Vue.js Dashboard]
```

---

## Stack

### Tracking Script
- **Vanilla JavaScript** — inlined directly in WordPress `<head>`
- Generates a UUID session ID on first page visit, stored in `localStorage` with a 2-hour expiry
- Fires silently on every page load — no console errors, no blocking, no response handling
- Sends: `session_id`, `page_url`
- Server captures automatically: `referrer`, `user_agent`, `timestamp`

### Backend — Collector API
- **Node.js + Express**
- Receives tracking events and pushes them to the Redis queue
- Validates `Origin` header — only accepts requests from the target domain
- Bot filtering on the server side based on `User-Agent`
- Designed for speed — no heavy processing on ingest

### Backend — Admin API
- **Node.js + Express** (separate service from Collector)
- Queries and aggregates PostgreSQL for the dashboard
- Serves session journeys, funnel data, traffic source breakdowns, and time-range filters

### Queue
- **Redis** — acts as a fast buffer between the Collector API and the database writer
- A worker process pulls batches from the queue every few seconds and writes to PostgreSQL
- Ensures no events are lost during traffic spikes
- Handles peak load of ~1,500 requests/minute comfortably

### Database
- **PostgreSQL**

**Events Table:**
| Column | Type | Description |
|---|---|---|
| `id` | SERIAL PRIMARY KEY | Auto-increment |
| `session_id` | VARCHAR | Anonymous session identifier |
| `page_url` | TEXT | Full URL of visited page |
| `referrer` | TEXT | Previous page or external source |
| `user_agent` | TEXT | For bot filtering |
| `timestamp` | TIMESTAMPTZ | Event time |

**Indexes:** `session_id`, `timestamp`

**Scaling strategy:** Start with a single raw events table. Add materialized views or pre-aggregated tables later if analytics queries become slow.

### Frontend — Admin Dashboard
- **Vue.js** with **PrimeVue** component library
- **Cytoscape.js** for interactive node-graph journey visualization
- PrimeVue provides: date range pickers, data tables, charts, modals

**Dashboard features:**
- Interactive user journey graph (nodes = pages, edges = paths between them)
- Edge thickness and color driven by traffic volume — most used paths stand out visually
- Node color coded by traffic source (Google, direct, social, etc.)
- Funnel view showing drop-off rates between pages
- Time period filtering (today, last 7 days, custom range)
- Entry page analysis with external referrer breakdown

### Infrastructure
- **Single VPS** — 2–4 CPU cores, 4–8 GB RAM, 50–100 GB storage
- **Docker** — all services containerized
- Two main service groups:
  - Collector API + Redis + Worker
  - Admin API + Vue.js frontend + PostgreSQL

---

## Data Flow

1. User visits a page on the WordPress site
2. Inline tracking script runs on page load
3. Script checks `localStorage` for a valid session ID (creates one if missing or expired)
4. `POST /event` fires silently with `session_id` and `page_url`
5. Collector API receives the request, reads `referrer` and `user_agent` from headers
6. Event is pushed to Redis queue
7. Worker process batches Redis queue and bulk-inserts into PostgreSQL
8. Admin dashboard queries Admin API for aggregated journey data
9. Cytoscape.js renders the interactive graph

---

## Session Management

- Session ID: random UUID generated client-side
- Storage: `localStorage`
- Expiry: 2 hours from creation (checked on each page load)
- No personally identifiable information stored — fully anonymous
- GDPR-friendly by design

---

## Referrer Logic

- Referrer is captured from HTTP headers on every request
- Server checks if referrer domain matches the site's own domain
- External referrers (Google, Facebook, direct, etc.) are stored and used to identify traffic sources and entry pages
- Internal referrers are used to reconstruct the navigation path within the session

---

## Scalability Path

| Stage | Data Volume | Action |
|---|---|---|
| Launch | < 1M events | Single events table, no changes needed |
| Growth | 1M–50M events | Add composite indexes, tune queries |
| Scale | 50M+ events | Partition table by month, add materialized views |
| Large scale | 500M+ events | Consider TimescaleDB or ClickHouse for analytics layer |

---

## Future Event Types

The system is designed to extend beyond page views:

- `click` — button or link clicks
- `add_to_cart` — WooCommerce cart events
- `checkout_start` — funnel entry
- `purchase` — conversion event
- `exit` — page exit / session end

---

## Ad Blocker & Privacy Tool Evasion

Ad blockers and privacy extensions (uBlock Origin, Privacy Badger, Ghostery, etc.) maintain blocklists that target specific keywords in URLs, domain names, and request patterns. To maximize event capture rate, avoid any terminology that triggers these lists.

### Blocked Keywords to Avoid

Never use these words in endpoint paths, domain names, or query parameters:

| Avoid | Use Instead |
|---|---|
| `/track` | `/p` or `/ping` |
| `/analytics` | `/a` or `/data` |
| `/collect` | `/c` or `/log` |
| `/event` | `/e` or `/hit` |
| `/beacon` | `/b` |
| `/pixel` | — |
| `/telemetry` | — |
| `/stats` | — |

### Recommended Endpoint

```
POST /p
```

Short, generic, and indistinguishable from any other API call.

### Collector Domain / Subdomain

Avoid subdomains like:
- `analytics.yourdomain.com`
- `track.yourdomain.com`
- `stats.yourdomain.com`

Use something neutral instead:
- `api.yourdomain.com`
- `data.yourdomain.com`
- `cdn.yourdomain.com`
- A completely separate neutral domain unrelated to the main site

### Request Method

Use `POST` rather than `GET` with query parameters — GET requests with tracking-like parameters are more aggressively fingerprinted and blocked.

### Additional Tips

- Serve the tracking script from your own domain, not a third-party CDN, to avoid domain-based blocking
- Do not name the script file with blocked keywords — use something like `app.js` or `main.js` instead of `tracker.js` or `analytics.js`
- Since the collector is a first-party server (your own domain/subdomain), it avoids third-party tracker blocklists entirely — this is the strongest protection

---

## Project Phases

### Phase 1 — Data Collection
- [ ] Build and deploy tracking script
- [ ] Set up Collector API with Redis queue and worker
- [ ] PostgreSQL schema and Docker setup
- [ ] Deploy to VPS and connect to WordPress site

### Phase 2 — Admin Dashboard
- [ ] Admin API with aggregation endpoints
- [ ] Vue.js + PrimeVue project scaffold
- [ ] Cytoscape.js journey graph integration
- [ ] Time range filtering and traffic source views

### Phase 3 — Analytics Expansion
- [ ] Funnel builder
- [ ] Bot filtering refinement
- [ ] Additional event types
- [ ] Performance optimization if needed
