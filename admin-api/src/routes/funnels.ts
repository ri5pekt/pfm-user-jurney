import { Router, Request, Response } from 'express';
import { pgPool } from '../lib/postgres';

export const funnelsRouter = Router();

type StepType       = 'page_view' | 'custom_event';
type UrlMatch       = 'contains' | 'equals' | 'starts_with';
type FilterField    = 'country' | 'channel' | 'source' | 'entry_url' | 'referrer';
type FilterOperator = 'is_any' | 'contains' | 'equals' | 'starts_with' | 'is_set' | 'is_not_set';

const ALLOWED_FILTER_FIELDS: FilterField[] = ['country', 'channel', 'source', 'entry_url', 'referrer'];
const ALLOWED_VALUE_FIELDS  = ['country', 'channel', 'source', 'utm_campaign', 'utm_medium'];

interface FunnelStep {
  type:        StepType;
  url_match?:  UrlMatch;
  url_value?:  string;
  event_type?: string;
  label:       string;
}

interface FunnelFilter {
  field:    FilterField;
  operator: FilterOperator;
  values:   string[];
}

interface FunnelRequest {
  steps:    FunnelStep[];
  filters?: FunnelFilter[];
  compare?: FunnelFilter[];
  start?:   string;
  end?:     string;
}

interface StepResult {
  label:     string;
  count:     number;
  pct_prev:  number;
  pct_total: number;
  drop_off:  number;
}

interface FunnelResult {
  total:               number;
  overall_conversion:  number;
  steps:               StepResult[];
}

interface RawEvent {
  session_id: string;
  event_type: string;
  page_url:   string;
  ts:         number;
}

// ─── helpers ────────────────────────────────────────────────────────────────

function matchesStep(ev: RawEvent, step: FunnelStep): boolean {
  if (step.type === 'page_view') {
    if (ev.event_type !== 'page_view') return false;
    const val = (step.url_value ?? '').trim().toLowerCase();
    if (!val) return true;
    const full = ev.page_url.toLowerCase();
    let pathname = full;
    try { pathname = new URL(ev.page_url).pathname.toLowerCase(); } catch { /* keep raw */ }
    switch (step.url_match ?? 'contains') {
      case 'contains':    return full.includes(val) || pathname.includes(val);
      case 'equals':      return pathname === val || full === val;
      case 'starts_with': return pathname.startsWith(val);
      default:            return full.includes(val);
    }
  }
  if (step.type === 'custom_event') {
    return ev.event_type === (step.event_type ?? '');
  }
  return false;
}

/**
 * Builds the extra WHERE clauses (beyond date range) from a filter array.
 * params are appended to the provided array; SQL placeholders start at startIdx.
 */
function applyFilters(
  filters: FunnelFilter[],
  conds: string[],
  params: unknown[],
): void {
  for (const f of filters) {
    if (!ALLOWED_FILTER_FIELDS.includes(f.field)) continue;
    const col = f.field;   // already validated — safe to interpolate

    switch (f.operator) {
      case 'is_any':
        if (f.values.length > 0) {
          conds.push(`${col} = ANY($${params.push(f.values)})`);
        }
        break;
      case 'contains':
        if (f.values[0]) {
          conds.push(`${col} ILIKE $${params.push('%' + f.values[0] + '%')}`);
        }
        break;
      case 'equals':
        if (f.values[0]) {
          conds.push(`${col} = $${params.push(f.values[0])}`);
        }
        break;
      case 'starts_with':
        if (f.values[0]) {
          conds.push(`${col} ILIKE $${params.push(f.values[0] + '%')}`);
        }
        break;
      case 'is_set':
        conds.push(`(${col} IS NOT NULL AND ${col} <> '')`);
        break;
      case 'is_not_set':
        conds.push(`(${col} IS NULL OR ${col} = '')`);
        break;
    }
  }
}

async function fetchSessionIds(
  start: string | undefined,
  end:   string | undefined,
  filters: FunnelFilter[],
): Promise<string[]> {
  const conds: string[]  = [];
  const params: unknown[] = [];
  if (start) conds.push(`first_seen >= $${params.push(start)}`);
  if (end)   conds.push(`first_seen <= $${params.push(end)}`);
  applyFilters(filters, conds, params);
  const where = conds.length ? 'WHERE ' + conds.join(' AND ') : '';
  const r = await pgPool.query<{ session_id: string }>(
    `SELECT session_id FROM sessions ${where} ORDER BY first_seen DESC LIMIT 100000`,
    params,
  );
  return r.rows.map(r => r.session_id);
}

function computeResult(steps: FunnelStep[], sessionIds: string[], bySession: Map<string, RawEvent[]>): FunnelResult {
  const counts = new Array<number>(steps.length).fill(0);

  for (const sid of sessionIds) {
    const events = bySession.get(sid);
    if (!events || events.length === 0) continue;
    let afterTs = -Infinity;
    for (let si = 0; si < steps.length; si++) {
      const match = events.find(ev => ev.ts >= afterTs && matchesStep(ev, steps[si]));
      if (!match) break;
      counts[si]++;
      afterTs = match.ts + 1;
    }
  }

  const total = counts[0] ?? 0;
  const last  = counts[counts.length - 1] ?? 0;
  const pct   = (n: number, d: number) => d > 0 ? Math.round(n / d * 10000) / 100 : 0;

  return {
    total,
    overall_conversion: pct(last, total),
    steps: steps.map((s, i) => ({
      label:     s.label,
      count:     counts[i],
      pct_prev:  i === 0 ? 100 : pct(counts[i], counts[i - 1]),
      pct_total: pct(counts[i], total),
      drop_off:  i === 0 ? 0 : (counts[i - 1] - counts[i]),
    })),
  };
}

// ─── routes ─────────────────────────────────────────────────────────────────

// GET /funnels/event-types
funnelsRouter.get('/event-types', async (_req: Request, res: Response): Promise<void> => {
  const result = await pgPool.query<{ event_type: string; count: string }>(
    `SELECT event_type, COUNT(*) AS count
     FROM   events
     WHERE  event_type <> 'page_view'
     GROUP  BY event_type
     ORDER  BY count DESC
     LIMIT  50`,
  );
  res.json(result.rows);
});

// GET /funnels/filter-values?field=country
funnelsRouter.get('/filter-values', async (req: Request, res: Response): Promise<void> => {
  const field = req.query.field as string;
  if (!ALLOWED_VALUE_FIELDS.includes(field)) {
    res.status(400).json({ error: 'Invalid field' }); return;
  }
  const r = await pgPool.query<{ value: string; count: string }>(
    `SELECT ${field} AS value, COUNT(*) AS count
     FROM   sessions
     WHERE  ${field} IS NOT NULL AND ${field} <> ''
     GROUP  BY ${field}
     ORDER  BY count DESC
     LIMIT  150`,
  );
  res.json(r.rows);
});

// POST /funnels/compute
funnelsRouter.post('/compute', async (req: Request, res: Response): Promise<void> => {
  try {
    const body: FunnelRequest = req.body;
    const { steps, filters = [], compare, start, end } = body;

    if (!Array.isArray(steps) || steps.length < 2) {
      res.status(400).json({ error: 'At least 2 steps required' }); return;
    }
    if (steps.length > 8) {
      res.status(400).json({ error: 'Maximum 8 steps' }); return;
    }

    // Fetch sessions for primary segment
    const primaryIds = await fetchSessionIds(start, end, filters);

    if (primaryIds.length === 0) {
      const empty = {
        total: 0, overall_conversion: 0,
        steps: steps.map(s => ({ label: s.label, count: 0, pct_prev: 0, pct_total: 0, drop_off: 0 })),
      };
      res.json({ primary: empty }); return;
    }

    // Load all events for primary sessions
    const allIds = compare
      ? [...new Set([...primaryIds, ...(await fetchSessionIds(start, end, compare ?? []))])]
      : primaryIds;

    const evRes = await pgPool.query<{ session_id: string; event_type: string; page_url: string; timestamp: string }>(
      `SELECT session_id, event_type, page_url, timestamp
       FROM   events
       WHERE  session_id = ANY($1)
       ORDER  BY session_id, timestamp ASC`,
      [allIds],
    );

    const bySession = new Map<string, RawEvent[]>();
    for (const ev of evRes.rows) {
      if (!bySession.has(ev.session_id)) bySession.set(ev.session_id, []);
      bySession.get(ev.session_id)!.push({
        session_id: ev.session_id,
        event_type: ev.event_type,
        page_url:   ev.page_url,
        ts:         new Date(ev.timestamp).getTime(),
      });
    }

    const primary = computeResult(steps, primaryIds, bySession);

    if (!compare || compare.length === 0) {
      res.json({ primary }); return;
    }

    // Fetch compare segment session IDs (may overlap with primary — that's fine)
    const compareIds = await fetchSessionIds(start, end, compare);
    const compareResult = computeResult(steps, compareIds, bySession);

    res.json({ primary, compare: compareResult });
  } catch (err) {
    console.error('[admin-api] /funnels/compute error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ── Saved funnels ────────────────────────────────────────────────────────────

// GET /funnels/saved — list all saved funnels
funnelsRouter.get('/saved', async (_req: Request, res: Response): Promise<void> => {
  try {
    const result = await pgPool.query(
      `SELECT id, name, created_by, created_at FROM saved_funnels ORDER BY created_at DESC`,
    );
    res.json(result.rows);
  } catch (err) {
    console.error('[admin-api] GET /funnels/saved error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /funnels/saved/:id — get full config for one saved funnel
funnelsRouter.get('/saved/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const result = await pgPool.query(
      `SELECT id, name, config, created_by, created_at FROM saved_funnels WHERE id = $1`,
      [req.params.id],
    );
    if (result.rows.length === 0) { res.status(404).json({ error: 'Not found' }); return; }
    res.json(result.rows[0]);
  } catch (err) {
    console.error('[admin-api] GET /funnels/saved/:id error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /funnels/saved — create a new saved funnel
funnelsRouter.post('/saved', async (req: Request, res: Response): Promise<void> => {
  const { name, config, created_by } = req.body as { name?: string; config?: unknown; created_by?: string };
  if (!name?.trim() || !config) { res.status(400).json({ error: 'name and config are required' }); return; }
  try {
    const result = await pgPool.query(
      `INSERT INTO saved_funnels (name, config, created_by) VALUES ($1, $2, $3) RETURNING id, name, created_by, created_at`,
      [name.trim(), JSON.stringify(config), created_by ?? null],
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error('[admin-api] POST /funnels/saved error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /funnels/saved/:id — delete a saved funnel
funnelsRouter.delete('/saved/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    await pgPool.query(`DELETE FROM saved_funnels WHERE id = $1`, [req.params.id]);
    res.status(204).end();
  } catch (err) {
    console.error('[admin-api] DELETE /funnels/saved/:id error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
