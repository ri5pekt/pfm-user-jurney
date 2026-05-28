import { Router, Request, Response } from 'express';
import { pgPool } from '../lib/postgres';

export const sessionsRouter = Router();

// GET /sessions?page=1&limit=20&channel=paid_social&source=Facebook&utm_campaign=GA0PVYXNNA&min_pages=3&orders_only=1&order_id=3903895&user_email=john@example.com
sessionsRouter.get('/', async (req: Request, res: Response): Promise<void> => {
  const page    = Math.max(1, parseInt(req.query.page   as string) || 1);
  const limit   = Math.min(100, parseInt(req.query.limit as string) || 20);
  const offset  = (page - 1) * limit;
  const channel      = (req.query.channel      as string) || '';
  const source       = (req.query.source       as string) || '';
  const utm_campaign = (req.query.utm_campaign as string) || '';
  const session_id   = (req.query.session_id   as string) || '';
  const order_id     = (req.query.order_id     as string) || '';
  const user_email   = (req.query.user_email   as string) || '';
  const min_pages    = parseInt(req.query.min_pages  as string) || 0;
  const orders_only  = req.query.orders_only  === '1';

  const conditions: string[] = [];
  const params: unknown[]    = [];

  if (channel)      { params.push(channel);      conditions.push(`channel      = $${params.length}`); }
  if (source)       { params.push(source);       conditions.push(`source       = $${params.length}`); }
  if (utm_campaign) {
    if (utm_campaign === '(not set)') {
      conditions.push(`(utm_campaign IS NULL OR utm_campaign = '')`);
    } else {
      params.push(utm_campaign); conditions.push(`utm_campaign = $${params.length}`);
    }
  }
  if (session_id) { params.push(`%${session_id}%`); conditions.push(`session_id ILIKE $${params.length}`); }
  if (order_id)   { params.push(`%${order_id}%`);   conditions.push(`order_id   ILIKE $${params.length}`); }
  if (user_email) { params.push(`%${user_email}%`); conditions.push(`user_email ILIKE $${params.length}`); }
  if (min_pages > 0) { params.push(min_pages); conditions.push(`page_count >= $${params.length}`); }
  if (orders_only) {
    conditions.push(`order_id IS NOT NULL`);
  }
  const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';

  const countRow = await pgPool.query(`SELECT COUNT(*) FROM sessions ${where}`, params);
  const total    = parseInt(countRow.rows[0].count, 10);

  params.push(limit, offset);
  const rows = await pgPool.query(
    `SELECT session_id, first_seen, last_seen, entry_url, referrer,
            source, medium, channel, placement, campaign_id,
            utm_source, utm_medium, utm_campaign, page_count,
            country, state_name, city,
            order_id, revenue_usd,
            attribution_method, user_email
     FROM   sessions ${where}
     ORDER  BY first_seen DESC
     LIMIT  $${params.length - 1} OFFSET $${params.length}`,
    params,
  );

  res.json({ sessions: rows.rows, total, page, limit });
});

// GET /sessions/stats — channel + source breakdown
sessionsRouter.get('/stats', async (_req: Request, res: Response): Promise<void> => {
  const [byChannel, bySource] = await Promise.all([
    pgPool.query(
      `SELECT channel, COUNT(*) AS count
       FROM   sessions
       WHERE  channel <> '' AND channel <> 'internal'
       GROUP  BY channel
       ORDER  BY count DESC`,
    ),
    pgPool.query(
      `SELECT source, channel, COUNT(*) AS count
       FROM   sessions
       WHERE  source <> '' AND source <> 'direct' AND source <> 'internal'
       GROUP  BY source, channel
       ORDER  BY count DESC
       LIMIT  20`,
    ),
  ]);

  res.json({
    by_channel: byChannel.rows,
    by_source:  bySource.rows,
  });
});

// GET /sessions/:id — full session detail + all events
sessionsRouter.get('/:id', async (req: Request, res: Response): Promise<void> => {
  const session_id = req.params.id;

  const [sessionRow, eventsRow] = await Promise.all([
    pgPool.query(`SELECT * FROM sessions WHERE session_id = $1`, [session_id]),
    pgPool.query(
      `SELECT timestamp, event_type, page_url, referrer, metadata, user_agent
       FROM   events
       WHERE  session_id = $1
       ORDER  BY timestamp ASC`,
      [session_id],
    ),
  ]);

  if (sessionRow.rows.length === 0) {
    res.status(404).json({ error: 'Session not found' }); return;
  }

  res.json({ session: sessionRow.rows[0], events: eventsRow.rows });
});
