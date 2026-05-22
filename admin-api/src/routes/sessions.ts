import { Router, Request, Response } from 'express';
import { pgPool } from '../lib/postgres';

export const sessionsRouter = Router();

// GET /sessions?page=1&limit=20&channel=paid_social&source=Facebook
sessionsRouter.get('/', async (req: Request, res: Response): Promise<void> => {
  const page    = Math.max(1, parseInt(req.query.page   as string) || 1);
  const limit   = Math.min(100, parseInt(req.query.limit as string) || 20);
  const offset  = (page - 1) * limit;
  const channel = (req.query.channel as string) || '';
  const source  = (req.query.source  as string) || '';

  const conditions: string[] = [];
  const params: unknown[]    = [];

  if (channel) { params.push(channel); conditions.push(`channel = $${params.length}`); }
  if (source)  { params.push(source);  conditions.push(`source  = $${params.length}`); }

  const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';

  const countRow = await pgPool.query(`SELECT COUNT(*) FROM sessions ${where}`, params);
  const total    = parseInt(countRow.rows[0].count, 10);

  params.push(limit, offset);
  const rows = await pgPool.query(
    `SELECT session_id, first_seen, last_seen, entry_url, referrer,
            source, medium, channel, placement, campaign_id,
            utm_source, utm_medium, utm_campaign, page_count
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
