import { Router, Request, Response } from 'express';
import { isBotRequest } from '../middleware/botFilter';
import { redisClient } from '../lib/redis';

// Noise paths — internal tools, WooCommerce null products, etc.
const NOISE_PATTERNS = [
  /\/product\/null(\/|$|\?)/,
  /\/product\/undefined(\/|$|\?)/,
  /\/lpage\/page-validator(\/|$|\?)/,
  /\/null(\/|$|\?)/,
];

function isNoisyUrl(url: string): boolean {
  try {
    const { pathname } = new URL(url);
    return NOISE_PATTERNS.some((p) => p.test(pathname));
  } catch {
    return false;
  }
}

const EVENT_TYPE_RE = /^[a-z][a-z0-9_]{0,63}$/;

interface CollectBody {
  session_id?:  unknown;
  page_url?:    unknown;
  referrer?:    unknown;
  event_type?:  unknown;
}

function getClientIp(req: import('express').Request): string | null {
  const forwarded = (req.headers['x-forwarded-for'] as string) ?? '';
  const first = forwarded.split(',')[0]?.trim();
  return first || (req.headers['x-real-ip'] as string) || req.socket.remoteAddress || null;
}

export const collectRouter = Router();

collectRouter.post('/', async (req: Request, res: Response): Promise<void> => {
  res.status(204).end();

  const body       = req.body as CollectBody;
  const session_id = typeof body.session_id === 'string' ? body.session_id.trim() : '';
  const page_url   = typeof body.page_url   === 'string' ? body.page_url.trim()   : '';
  const referrer   = typeof body.referrer   === 'string' ? body.referrer.trim()   : '';
  const raw_type   = typeof body.event_type === 'string' ? body.event_type.trim().toLowerCase() : 'page_view';
  const event_type = EVENT_TYPE_RE.test(raw_type) ? raw_type : 'page_view';

  if (!session_id || !page_url) return;
  if (isBotRequest(req.headers['user-agent'])) return;
  if (isNoisyUrl(page_url)) return;

  // Dedup only applies to page_view events — custom events always pass through
  if (event_type === 'page_view') {
    let pathname = page_url;
    try { pathname = new URL(page_url).pathname; } catch { /* keep raw url */ }
    const dedupKey = `dedup:${session_id}`;
    try {
      const lastPath = await redisClient.get(dedupKey);
      if (lastPath === pathname) return; // duplicate within TTL window — drop
      await redisClient.set(dedupKey, pathname, 'EX', 5);
    } catch {
      // Redis error — proceed without dedup rather than dropping the event
    }
  }

  const ip = getClientIp(req);

  const event = JSON.stringify({
    session_id,
    event_type,
    page_url,
    referrer,
    user_agent: req.headers['user-agent'] || '',
    ip:         ip ?? '',
    timestamp:  new Date().toISOString(),
  });

  try {
    await redisClient.lpush(process.env.REDIS_QUEUE_KEY || 'events_queue', event);
  } catch (err) {
    console.error('[collector] redis push failed:', err);
  }
});
