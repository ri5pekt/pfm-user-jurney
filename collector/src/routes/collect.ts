import { Router, Request, Response } from 'express';
import { isBotRequest, isBotIp } from '../middleware/botFilter';
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
  metadata?:    unknown;
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

  // Accept metadata only if it is a plain non-array object; cap at 2 KB
  const rawMeta = body.metadata;
  let metadata: Record<string, unknown> | null = null;
  if (rawMeta !== null && typeof rawMeta === 'object' && !Array.isArray(rawMeta)) {
    const serialised = JSON.stringify(rawMeta);
    if (serialised.length <= 2048) {
      metadata = rawMeta as Record<string, unknown>;
    }
  }

  if (!session_id || !page_url) return;
  if (isBotRequest(req.headers['user-agent'])) return;
  if (isNoisyUrl(page_url)) return;

  const ip = getClientIp(req);

  // ── IP-based bot check ──────────────────────────────────────────────────
  if (isBotIp(ip)) return;

  // ── Rate limiting — max 60 events per IP per minute ────────────────────
  // Protects against flood/scraper bots that spoof a real browser UA.
  // Threshold is generous enough for power users (fast navigation, prefetch)
  // but will catch automated tools sending dozens of events per second.
  const RATE_LIMIT = Number(process.env.IP_RATE_LIMIT) || 60;
  if (ip) {
    const rateKey = `rate:${ip}`;
    try {
      const count = await redisClient.incr(rateKey);
      if (count === 1) await redisClient.expire(rateKey, 60); // first hit sets 60s window
      if (count > RATE_LIMIT) return; // over limit — drop silently
    } catch {
      // Redis error — don't block on rate limit failure
    }
  }

  const effective_session_id = session_id;

  // For order_completed: dedup by order_id — same order within 24h is silently dropped
  if (event_type === 'order_completed') {
    const orderId = typeof metadata?.order_id === 'string' || typeof metadata?.order_id === 'number'
      ? String(metadata.order_id).trim()
      : '';
    if (orderId) {
      const orderKey = `order:${effective_session_id}:${orderId}`;
      try {
        const seen = await redisClient.get(orderKey);
        if (seen) return; // duplicate order — drop
        await redisClient.set(orderKey, '1', 'EX', 86400); // 24h TTL
      } catch {
        // Redis error — proceed rather than blocking the event
      }
    }
  }

  // Dedup only applies to page_view events — custom events always pass through
  if (event_type === 'page_view') {
    let pathname = page_url;
    try { pathname = new URL(page_url).pathname; } catch { /* keep raw url */ }
    const dedupKey = `dedup:${effective_session_id}`;
    try {
      const lastPath = await redisClient.get(dedupKey);
      if (lastPath === pathname) return; // duplicate within TTL window — drop
      await redisClient.set(dedupKey, pathname, 'EX', 5);
    } catch {
      // Redis error — proceed without dedup rather than dropping the event
    }
  }

  const event = JSON.stringify({
    session_id: effective_session_id,
    event_type,
    page_url,
    referrer,
    user_agent: req.headers['user-agent'] || '',
    ip:         ip ?? '',
    metadata:   metadata ?? null,
    timestamp:  new Date().toISOString(),
  });

  try {
    await redisClient.lpush(process.env.REDIS_QUEUE_KEY || 'events_queue', event);
  } catch (err) {
    console.error('[collector] redis push failed:', err);
  }
});
