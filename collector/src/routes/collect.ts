import { Router, Request, Response } from 'express';
import { isBotRequest } from '../middleware/botFilter';
import { redisClient } from '../lib/redis';

// Regional store subpaths — excluded from tracking for now
const REGIONAL_PREFIXES = ['/es/', '/fr/', '/de/', '/ca/', '/gb/', '/au/', '/it/'];

function isRegionalUrl(url: string): boolean {
  try {
    const { pathname } = new URL(url);
    // Match both /gb/... (with content) and bare /gb or /gb? (redirect pages)
    return REGIONAL_PREFIXES.some((p) =>
      pathname.startsWith(p) || pathname === p.slice(0, -1),
    );
  } catch {
    return false;
  }
}

// Paths that are noise / internal tooling — not real user page views
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
  session_id?: unknown;
  page_url?: unknown;
  referrer?: unknown;
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
    referrer:   referrer,
    user_agent: req.headers['user-agent'] || '',
    timestamp:  new Date().toISOString(),
  });

  try {
    await redisClient.lpush(process.env.REDIS_QUEUE_KEY || 'events_queue', event);
  } catch (err) {
    console.error('[collector] redis push failed:', err);
  }
});
