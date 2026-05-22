import { redisClient } from './lib/redis';
import { pgPool } from './lib/postgres';
import { parseAttribution } from './lib/attribution';

const QUEUE_KEY  = process.env.REDIS_QUEUE_KEY  || 'events_queue';
const BATCH_SIZE = Number(process.env.WORKER_BATCH_SIZE)  || 100;
const INTERVAL_MS = Number(process.env.WORKER_INTERVAL_MS) || 3000;

interface RawEvent {
  session_id: string;
  page_url:   string;
  referrer:   string;
  user_agent: string;
  timestamp:  string;
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

  // ── Insert events ────────────────────────────────────────────────
  await pgPool.query(
    `INSERT INTO events (session_id, page_url, referrer, user_agent, timestamp)
     SELECT * FROM unnest($1::text[], $2::text[], $3::text[], $4::text[], $5::timestamptz[])`,
    [
      events.map(e => e.session_id),
      events.map(e => e.page_url),
      events.map(e => e.referrer   || ''),
      events.map(e => e.user_agent || ''),
      events.map(e => e.timestamp  || new Date().toISOString()),
    ],
  );

  // ── Upsert sessions ──────────────────────────────────────────────
  // Each event touches its session: first-ever INSERT sets attribution,
  // subsequent conflicts only update last_seen + page_count.
  for (const ev of events) {
    const attr = parseAttribution(ev.page_url, ev.referrer || '');
    await pgPool.query(
      `INSERT INTO sessions
         (session_id, first_seen, last_seen, entry_url, referrer,
          source, medium, channel, placement, campaign_id,
          utm_source, utm_medium, utm_campaign, page_count)
       VALUES ($1,$2,$2,$3,$4, $5,$6,$7,$8,$9, $10,$11,$12, 1)
       ON CONFLICT (session_id) DO UPDATE
         SET last_seen  = GREATEST(sessions.last_seen, EXCLUDED.last_seen),
             page_count = sessions.page_count + 1`,
      [
        ev.session_id,
        ev.timestamp || new Date().toISOString(),
        ev.page_url,
        ev.referrer || '',
        attr.source,  attr.medium,  attr.channel,
        attr.placement, attr.campaign_id,
        attr.utm_source, attr.utm_medium, attr.utm_campaign,
      ],
    );
  }

  console.log(`[worker] inserted ${events.length} events, upserted sessions`);
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
