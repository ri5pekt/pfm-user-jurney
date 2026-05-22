import { Router, Request, Response } from 'express';
import { requireAuth } from '../middleware/auth';
import { pgPool } from '../lib/postgres';

export const eventsRouter = Router();

eventsRouter.get('/', requireAuth, async (req: Request, res: Response): Promise<void> => {
  try {
    const page   = Math.max(1, parseInt(req.query.page  as string) || 1);
    const limit  = Math.min(100, Math.max(1, parseInt(req.query.limit as string) || 20));
    const offset = (page - 1) * limit;

    const [rows, count] = await Promise.all([
      pgPool.query(
        `SELECT id, session_id, page_url, referrer, timestamp
         FROM events
         ORDER BY timestamp DESC
         LIMIT $1 OFFSET $2`,
        [limit, offset],
      ),
      pgPool.query('SELECT COUNT(*)::int AS total FROM events'),
    ]);

    res.json({
      events: rows.rows,
      total:  count.rows[0].total as number,
      page,
      limit,
    });
  } catch (err) {
    console.error('[admin-api] /events error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
