# Funnels — Dev Plan

Reference screenshots: `01-empty-builder.png` → `06-funnel-result.png`

---

## Overview

Build a Hotjar-style funnel analysis screen that lets users define an ordered sequence of steps
and instantly see how many sessions pass through each step, where they drop off, and the
overall conversion rate.

---

## What we can support (given our data)

| Step type      | Implemented via                          | Notes                              |
|----------------|------------------------------------------|------------------------------------|
| Viewed page    | `events.event_type = 'page_view'`        | URL filter: contains / equals / starts with |
| Custom event   | `events.event_type = <value>`            | e.g. `order_completed`             |

**Not supported** (no click/interaction tracking): Clicked element, Rage click, U-turn.

Session-level filters:
| Filter      | Column                  |
|-------------|-------------------------|
| Country     | `sessions.country`      |
| Channel     | `sessions.channel`      |
| Source      | `sessions.source`       |
| Page count  | `sessions.page_count`   |

---

## Data model

### Step definition (frontend → API)

```ts
type StepType = 'page_view' | 'custom_event'
type UrlMatch = 'contains' | 'equals' | 'starts_with'

interface FunnelStep {
  type:        StepType
  // page_view only:
  url_match?:  UrlMatch
  url_value?:  string
  // custom_event only:
  event_type?: string   // e.g. "order_completed"
  label:       string   // human-readable, auto-generated
}

interface FunnelFilter {
  field:  'country' | 'channel' | 'source'
  value:  string
}

interface FunnelRequest {
  steps:   FunnelStep[]
  filters: FunnelFilter[]
  start:   string   // ISO
  end:     string   // ISO
}
```

### API response

```ts
interface FunnelStepResult {
  label:    string
  count:    number   // sessions that reached this step
  pct_prev: number   // % of previous step (drop-through rate)
  pct_total: number  // % of step 1 (overall)
  drop_off: number   // sessions lost vs previous step
}

interface FunnelResult {
  total:               number   // step 1 count
  overall_conversion:  number   // step N / step 1 * 100
  steps:               FunnelStepResult[]
}
```

---

## Funnel computation logic (server-side, SQL)

The funnel is **ordered** — a session must satisfy step N before step N+1 (by timestamp).

```
For each session in date range that matches optional filters:
  Check if the session has an event matching step 1.
  If yes → count[1]++, find the earliest matching timestamp t1.
  Check if the session has an event matching step 2 WHERE timestamp > t1.
  If yes → count[2]++, find earliest t2.
  ...repeat for all steps.
```

Implementation: a single SQL query using `EXISTS` subqueries with timestamp chaining,
or a server-side loop over session IDs (acceptable for typical dashboard volumes).

**Recommended approach**: server-side JS loop (same pattern as overview/funnel) for
flexibility, since SQL timestamp chaining with N dynamic steps is complex to generate safely.

---

## API

### `POST /funnels/compute`

**Request body**: `FunnelRequest`

**Response**: `FunnelResult`

**Validation**:
- Min 2 steps, max 8 steps
- Date range required
- Each `page_view` step must have `url_value` (non-empty)
- Each `custom_event` step must have `event_type`

---

## Frontend components

### 1. `FunnelsView.vue` — top-level page

Layout (two-panel, stacked vertically):
- Top: `FunnelBuilder` (step editor)
- Bottom: `FunnelChart` (results, hidden until computed)

Date range controls (reuse VueDatePicker range, same as Overview), presets: 24h / 7d / 30d / Custom.

### 2. `FunnelBuilder.vue`

- Numbered step list
- Each step row: type badge + description + ✕ remove button
- "+ Add step" button at the bottom → shows type picker dropdown
- Step type picker:
  - **Viewed page** → inline config: `where URL [contains ▼] [text input]` + Apply
  - **Custom event** → inline config: `event type [dropdown of known event types]` + Apply
- "Compute Funnel" button (enabled when ≥ 2 steps configured)
- Optional: "+ Add filter" (country / channel / source)

### 3. `FunnelChart.vue`

Visual:
- Horizontal bar of time presets (24h / 7d / 30d / Custom) — controls date range
- Summary row: **Overall conversion X%**
- One column per step:
  - Vertical bar (height proportional to count / step-1-count)
  - Step label below
  - Count + % label on bar
- Below each bar (except step 1):
  - `→ N (X%) Reached step`
  - `↓ N (X%) Dropped off`

---

## Implementation order (TODOs)

1. **Admin API** — `POST /funnels/compute` endpoint
2. **Admin API** — register router in `index.ts`
3. **Frontend** — `FunnelsView.vue` + route in `router/index.ts`
4. **Frontend** — `FunnelBuilder.vue` (step editor)
5. **Frontend** — `FunnelChart.vue` (result visualization)
6. **Frontend** — add "Funnels" tab to `DashboardView.vue`
7. **Deploy**

---

## Known event types (live data)

| event_type      | Count   |
|-----------------|---------|
| page_view       | 125,779 |
| order_completed | 997     |

The "Custom event" step type picker will be pre-populated with these + allow free-text entry.

---

## Out of scope for V1

- Saving / naming funnels (no persistence)
- "Clicked element" step type (no click tracking)
- "Compare with" segment comparison
- Avg. time to convert (needs timestamp delta — can add in V2)
- Session replay integration
