import { Router, Request, Response } from 'express';
import { isBotRequest } from '../middleware/botFilter';
import { redisClient } from '../lib/redis';

// Regional store subpaths — excluded from tracking
const REGIONAL_PREFIXES = ['/es/', '/fr/', '/de/', '/ca/', '/gb/', '/au/', '/it/'];

// WooCommerce translated product paths (WPML)
const TRANSLATED_PATH_PATTERNS = [/^\/producto\//];

function isRegionalUrl(url: string): boolean {
  try {
    const { pathname } = new URL(url);
    if (REGIONAL_PREFIXES.some((p) =>
      pathname.startsWith(p) || pathname === p.slice(0, -1),
    )) return true;
    if (TRANSLATED_PATH_PATTERNS.some((p) => p.test(pathname))) return true;
    return false;
  } catch {
    return false;
  }
}

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

interface CollectBody {
  session_id?: unknown;
  page_url?:   unknown;
  referrer?:   unknown;
}

export const collectRouter = Router();

collectRouter.post('/', async (req: Request, res: Response): Promise<void> => {
  res.status(204).end();

  const body       = req.body as CollectBody;
  const session_id = typeof body.session_id === 'string' ? body.session_id.trim() : '';
  const page_url   = typeof body.page_url   === 'string' ? body.page_url.trim()   : '';
  const referrer   = typeof body.referrer   === 'string' ? body.referrer.trim()   : '';

  if (!session_id || !page_url) return;
  if (isBotRequest(req.headers['user-agent'])) return;
  if (isRegionalUrl(page_url)) return;
  if (isNoisyUrl(page_url)) return;

  const event = JSON.stringify({
    session_id,
    page_url,
    referrer,
    user_agent: req.headers['user-agent'] || '',
    timestamp:  new Date().toISOString(),
  });

  try {
    await redisClient.lpush(process.env.REDIS_QUEUE_KEY || 'events_queue', event);
  } catch (err) {
    console.error('[collector] redis push failed:', err);
  }
});
