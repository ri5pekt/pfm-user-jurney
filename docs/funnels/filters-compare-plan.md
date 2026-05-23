# Funnels — Filters & Compare With: Dev Plan

Reference screenshots: `hotjar-filters-menu.png`, `hotjar-filters-country.png`,
`hotjar-compare-loading.png`, `hotjar-compare-result.png`

---

## 1. What We're Building

### Filters
A "+ Add filter" button above the funnel chart that narrows down which sessions
are included in the funnel computation. Filters are applied server-side before
step matching begins.

### Compare With
A second independent filter group ("+ Compare with...") that runs the same funnel
steps against a different session segment and overlays a second colored bar
alongside the first in every step column.

---

## 2. Available Filter Dimensions

Based on actual DB columns:

| Dimension        | Source                     | Operator(s)                        |
|------------------|----------------------------|------------------------------------|
| Country          | `sessions.country` (ISO-2) | is any of (multi-select)           |
| City             | `sessions.city`            | contains / equals                  |
| Entry page       | `sessions.entry_url`       | contains / equals / starts_with    |
| Referrer         | `sessions.referrer`        | contains / equals                  |
| Channel          | `sessions.channel`         | is any of (multi-select)           |
| Source           | `sessions.source`          | is any of (multi-select)           |
| UTM Campaign     | `sessions.utm_campaign`    | contains / equals                  |
| UTM Medium       | `sessions.utm_medium`      | contains / equals                  |
| Page count       | `sessions.page_count`      | > / >= / < / <=                    |
| Has order        | `sessions.order_id`        | is set / is not set                |

Start with: **Country**, **Channel**, **Entry page**, **Referrer**.
Add more later without backend changes (all columns already exist).

---

## 3. Data Model

### API request shape (extending existing `POST /funnels/compute`)

```ts
interface FunnelFilter {
  field:    'country' | 'channel' | 'source' | 'entry_url' | 'referrer' | 'utm_campaign' | 'utm_medium' | 'page_count' | 'has_order'
  operator: 'is_any'    // multi-value: country, channel, source
           | 'contains' | 'equals' | 'starts_with'   // string
           | 'gt' | 'gte' | 'lt' | 'lte'             // numeric
           | 'is_set' | 'is_not_set'                  // presence
  values:   string[]    // for is_any, contains, equals, starts_with; empty for is_set/is_not_set
}

interface FunnelRequest {
  steps:    FunnelStep[]
  start:    string
  end:      string
  filters:  FunnelFilter[]         // primary segment (already exists, extend)
  compare?: FunnelFilter[]         // new: second segment (optional)
}

interface FunnelResponse {
  primary:  FunnelResult           // same shape as current result
  compare?: FunnelResult           // present only when compare filters sent
}
```

---

## 4. Backend Changes (`admin-api/src/routes/funnels.ts`)

### 4a. Filter application helper

```ts
function buildFilterWhere(filters: FunnelFilter[]): { sql: string; params: any[] } {
  // Builds a SQL WHERE fragment + positional params from filters array
  // Returns '' if no filters
}
```

Apply `WHERE` to the session fetch query:
```sql
SELECT session_id FROM sessions
WHERE first_seen >= $1 AND first_seen <= $2
  AND <filter_where>
```

This replaces the current unconditional session load — filters were already
partially implemented as `FunnelFilter` but not applied to the session query.

### 4b. Dual computation

When `compare` is present in the request body, run the same step-matching
pipeline twice (once per filter set) and return both results.

No new endpoints needed — the same `POST /funnels/compute` handles both.

### 4c. Country list endpoint (new)

```
GET /funnels/filter-values?field=country
```

Returns distinct non-null values for that field from the `sessions` table,
ordered by count DESC. Used by the filter picker to populate suggestions.

```ts
const allowed = ['country','channel','source','utm_campaign','utm_medium']
```

---

## 5. Frontend Changes

### 5a. FilterBar component (`FunnelsView.vue` or its own file)

```
[ Country is "US", "UK"  ×]  [+ Add filter]
```

- "+ Add filter" opens a **FilterMenu** dropdown with grouped options
- Clicking an option opens a **FilterEditor** popover specific to that field type:
  - **Multi-select** (country, channel, source): searchable checkbox list.
    Country values fetched from `/funnels/filter-values?field=country`.
  - **String** (entry_url, referrer, utm_campaign): operator select + text input
  - **Presence** (has_order): no input, just "is set" / "is not set" toggle

Active filters render as pill chips. Click a chip to re-open editor. ✕ removes it.

### 5b. CompareBar (`FunnelsView.vue`)

Below the primary FilterBar:

```
[+ Compare with…]
```

When clicked, adds a second FilterBar row in a different accent color (pink/red,
matching Hotjar). The compare filters are sent as `compare` in the API request.

Only one comparison group is needed for V1 (Hotjar supports multiple but that's
complex).

### 5c. FunnelChart updates

When `result.compare` is present, render **two bars side-by-side** in every step
column:
- Left bar: primary color (`#1d4ed8` / `#3b82f6`)
- Right bar: compare color (`#be123c` / `#f43f5e`)

Summary row shows two sets of numbers:
```
27,431        🔵 6.7%   🔴 20%
Started       Overall conversion
```

Each bar's label shows both values stacked or the bar pct inside the fill.

---

## 6. Implementation Order

1. **Backend** — `buildFilterWhere()` + apply to session query in `POST /funnels/compute`
2. **Backend** — dual result when `compare` filters present
3. **Backend** — `GET /funnels/filter-values` endpoint
4. **Frontend** — `FilterChip.vue` (pill display + remove)
5. **Frontend** — `FilterMenu.vue` (grouped dropdown)
6. **Frontend** — `FilterEditor.vue` (per-type input panel — multi-select / string / presence)
7. **Frontend** — Wire primary filters into `FunnelsView.vue` and pass to API
8. **Frontend** — CompareBar (second filter row, different color)
9. **Frontend** — Dual-bar rendering in `FunnelChart.vue`
10. **Deploy**

---

## 7. Component Tree

```
FunnelsView.vue
├── FilterBar.vue (primary filters)
│   ├── FilterChip.vue × N
│   ├── FilterMenu.vue (dropdown)
│   └── FilterEditor.vue (popover per type)
├── FilterBar.vue (compare — same component, compare=true prop)
├── FunnelBuilder.vue (unchanged)
├── FunnelChart.vue (updated for dual bars)
└── date range picker (unchanged)
```

---

## 8. Scope Boundaries (V1)

- **In scope**: Country (multi-select), Channel (multi-select), Entry page (string), Referrer (string)
- **Out of scope for V1**: Device, browser, UTM, page count, has_order, session duration
- **Compare**: one comparison group only
- **No URL persistence** of filter state (V2)
