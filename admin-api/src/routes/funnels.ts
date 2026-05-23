import { Router, Request, Response } from 'express';
import { pgPool } from '../lib/postgres';

export const funnelsRouter = Router();

type StepType  = 'page_view' | 'custom_event';
type UrlMatch  = 'contains' | 'equals' | 'starts_with';

interface FunnelStep {
  type:        StepType;
  url_match?:  UrlMatch;
  url_value?:  string;
  event_type?: string;
  label:       string;
}

interface FunnelFilter {
  field: 'country' | 'channel' | 'source';
  value: string;
}

interface FunnelRequest {
  steps:   FunnelStep[];
  filters?: FunnelFilter[];
  start?:  string;
  end?:    string;
}

interface RawEvent {
  session_id: string;
  event_type: string;
  page_url:   string;
  ts:         number;
}

function matchesStep(ev: RawEvent, step: FunnelStep): boolean {
  if (step.type === 'page_view') {
    if (ev.event_type !== 'page_view') return false;
    const val = (step.url_value ?? '').trim().toLowerCase();
    if (!val) return true;
    let pathname = ev.page_url.toLowerCase();
    try { pathname = new URL(ev.page_url).pathname.toLowerCase(); } catch { /* keep raw */ }
    const full = ev.page_url.toLowerCase();
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

// GET /funnels/event-types — distinct custom event types for the step picker
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

// POST /funnels/compute
funnelsRouter.post('/compute', async (req: Request, res: Response): Promise<void> => {
  try {
    const body: FunnelRequest = req.body;
    const { steps, filters = [], start, end } = body;

    if (!Array.isArray(steps) || steps.length < 2) {
      res.status(400).json({ error: 'At least 2 steps required' }); return;
    }
    if (steps.length > 8) {
      res.status(400).json({ error: 'Maximum 8 steps' }); return;
    }

    // Build sessions WHERE
    const conds: string[]  = [];
    const vals: unknown[]  = [];
    if (start) conds.push(`first_seen >= $${vals.push(start)}`);
    if (end)   conds.push(`first_seen <= $${vals.push(end)}`);
    for (const f of filters) {
      if (['country', 'channel', 'source'].includes(f.field) && f.value) {
        conds.push(`${f.field} = $${vals.push(f.value)}`);
      }
    }
    const where = conds.length ? 'WHERE ' + conds.join(' AND ') : '';

    const sessRes = await pgPool.query<{ session_id: string }>(
      `SELECT session_id FROM sessions ${where} ORDER BY first_seen DESC LIMIT 100000`,
      vals,
    );
    const sessionIds = sessRes.rows.map(r => r.session_id);

    if (sessionIds.length === 0) {
      res.json({
        total: 0,
        overall_conversion: 0,
        steps: steps.map(s => ({ label: s.label, count: 0, pct_prev: 0, pct_total: 0, drop_off: 0 })),
      });
      return;
    }

    // Load events
    const evRes = await pgPool.query<{ session_id: string; event_type: string; page_url: string; timestamp: string }>(
      `SELECT session_id, event_type, page_url, timestamp
       FROM   events
       WHERE  session_id = ANY($1)
       ORDER  BY session_id, timestamp ASC`,
      [sessionIds],
    );

    // Group by session
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

    // Walk each session through steps in order
    const counts = new Array<number>(steps.length).fill(0);

    for (const sid of sessionIds) {
      const events = bySession.get(sid);
      if (!events || events.length === 0) continue;

      let afterTs = -Infinity;
      let ok = true;
      for (let si = 0; si < steps.length; si++) {
        const match = events.find(ev => ev.ts >= afterTs && matchesStep(ev, steps[si]));
        if (!match) { ok = false; break; }
        counts[si]++;
        afterTs = match.ts + 1; // next step must come strictly after
      }
      void ok;
    }

    const total = counts[0] ?? 0;
    const last  = counts[counts.length - 1] ?? 0;
    const overall_conversion = total > 0 ? Math.round(last / total * 1000) / 10 : 0;

    res.json({
      total,
      overall_conversion,
      steps: steps.map((s, i) => ({
        label:      s.label,
        count:      counts[i],
        pct_prev:   i === 0 ? 100 : (counts[i - 1] > 0 ? Math.round(counts[i] / counts[i - 1] * 1000) / 10 : 0),
        pct_total:  total > 0 ? Math.round(counts[i] / total * 1000) / 10 : 0,
        drop_off:   i === 0 ? 0 : (counts[i - 1] - counts[i]),
      })),
    });
  } catch (err) {
    console.error('[admin-api] /funnels/compute error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
