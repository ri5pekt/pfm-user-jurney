import { redisClient } from './lib/redis';
import { pgPool } from './lib/postgres';
import { parseAttribution } from './lib/attribution';
import { fetchGeoForIp } from './lib/geo';

const QUEUE_KEY  = process.env.REDIS_QUEUE_KEY  || 'events_queue';
const BATCH_SIZE = Number(process.env.WORKER_BATCH_SIZE)  || 100;
const INTERVAL_MS = Number(process.env.WORKER_INTERVAL_MS) || 3000;

// Max seconds between two events on the same path to be considered a redirect/variant
const DEDUP_WINDOW_MS = 5000;

interface RawEvent {
  session_id:  string;
  event_type:  string;
  page_url:    string;
  referrer:    string;
  user_agent:  string;
  ip:          string;
  metadata:    Record<string, unknown> | null;
  timestamp:   string;
}

function getBasePath(url: string): string {
  try { return new URL(url).pathname; } catch { return url; }
}

/**
 * Within a sorted (ascending) event batch, collapse same-session + same-pathname
 * events that arrive within DEDUP_WINDOW_MS of each other, keeping the LATER one.
 * This handles A/B-test redirects (e.g. /product/x/ → /product/x/?uatc=v3).
 */
function deduplicateEvents(events: RawEvent[]): RawEvent[] {
  const result: RawEvent[] = [];
  const lastEvt = new Map<string, { idx: number; path: string; timeMs: number }>();

  for (const ev of events) {
    const path   = getBasePath(ev.page_url);
    const timeMs = new Date(ev.timestamp).getTime();
    const prev   = lastEvt.get(ev.session_id);

    const isPageView = (ev.event_type || 'page_view') === 'page_view';

    if (isPageView && prev && prev.path === path && timeMs - prev.timeMs <= DEDUP_WINDOW_MS) {
      // Replace the earlier event with this one in-place (keep variant URL)
      result[prev.idx] = ev;
      lastEvt.set(ev.session_id, { idx: prev.idx, path, timeMs });
    } else {
      if (isPageView) lastEvt.set(ev.session_id, { idx: result.length, path, timeMs });
      result.push(ev);
    }
  }

  return result;
}

async function drainBatch(): Promise<void> {
  const pipeline = redisClient.pipeline();
  for (let i = 0; i < BATCH_SIZE; i++) pipeline.rpop(QUEUE_KEY);
  const results = await pipeline.exec();
  if (!results) return;

  const events: RawEvent[] = [];
  for (const [err, value] of results) {
    if (err || !value) continue;
    try { events.push(JSON.parse(value as string) as RawEvent); } catch { /* skip */ }
  }
  if (events.length === 0) return;

  // Sort ascending so the earliest event per session is processed first
  events.sort((a, b) => (a.timestamp < b.timestamp ? -1 : 1));

  // Deduplicate A/B redirect pairs (same path within 5s → keep later/variant)
  const deduped = deduplicateEvents(events);
  if (deduped.length === 0) return;

  // ── Insert events ────────────────────────────────────────────────
  await pgPool.query(
    `INSERT INTO events (session_id, event_type, page_url, referrer, user_agent, timestamp, metadata)
     SELECT * FROM unnest($1::text[], $2::text[], $3::text[], $4::text[], $5::text[], $6::timestamptz[], $7::jsonb[])
     ON CONFLICT DO NOTHING`,
    [
      deduped.map(e => e.session_id),
      deduped.map(e => e.event_type  || 'page_view'),
      deduped.map(e => e.page_url),
      deduped.map(e => e.referrer    || ''),
      deduped.map(e => e.user_agent  || ''),
      deduped.map(e => e.timestamp   || new Date().toISOString()),
      deduped.map(e => e.metadata != null ? JSON.stringify(e.metadata) : null),
    ],
  );

  // ── Geo lookup — batch unique IPs ────────────────────────────────
  const apiKey = process.env.IP_API_KEY?.trim() || null;
  const geoCache = new Map<string, Awaited<ReturnType<typeof fetchGeoForIp>>>();
  if (apiKey) {
    const uniqueIps = [...new Set(deduped.map(e => e.ip).filter(ip => ip && ip.length > 0))];
    await Promise.all(uniqueIps.map(async ip => {
      const geo = await fetchGeoForIp(ip, apiKey);
      geoCache.set(ip, geo);
    }));
  }

  // ── Upsert sessions ──────────────────────────────────────────────
  // Each event touches its session: first-ever INSERT sets attribution + geo,
  // subsequent conflicts only update last_seen + page_count.
  for (const ev of deduped) {
    const attr       = parseAttribution(ev.page_url, ev.referrer || '');
    const geo        = geoCache.get(ev.ip) ?? null;
    const isPageView = (ev.event_type || 'page_view') === 'page_view';
    await pgPool.query(
      `INSERT INTO sessions
         (session_id, first_seen, last_seen, entry_url, referrer,
          source, medium, channel, placement, campaign_id,
          utm_source, utm_medium, utm_campaign, page_count,
          ip, country, state, state_name, city)
       VALUES ($1,$2,$2,$3,$4, $5,$6,$7,$8,$9, $10,$11,$12, $18::int, $13,$14,$15,$16,$17)
       ON CONFLICT (session_id) DO UPDATE
         SET last_seen  = GREATEST(sessions.last_seen, EXCLUDED.last_seen),
             page_count = sessions.page_count + $18::int`,
      [
        ev.session_id,
        ev.timestamp || new Date().toISOString(),
        ev.page_url,
        ev.referrer || '',
        attr.source,  attr.medium,  attr.channel,
        attr.placement, attr.campaign_id,
        attr.utm_source, attr.utm_medium, attr.utm_campaign,
        ev.ip || null,
        geo?.country    ?? null,
        geo?.state      ?? null,
        geo?.state_name ?? null,
        geo?.city       ?? null,
        isPageView ? 1 : 0,
      ],
    );
  }

  console.log(`[worker] inserted ${deduped.length} events (${events.length - deduped.length} deduped), upserted sessions`);
}

async function run(): Promise<void> {
  console.log(`[worker] started — batch: ${BATCH_SIZE}, interval: ${INTERVAL_MS}ms`);
  const tick = async () => {
    try   { await drainBatch(); }
    catch (err) { console.error('[worker] drain error:', err); }
    finally     { setTimeout(tick, INTERVAL_MS); }
  };
  await tick();
}

run().catch(err => { console.error('[worker] fatal:', err); process.exit(1); });
