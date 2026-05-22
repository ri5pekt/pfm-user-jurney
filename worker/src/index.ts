import { redisClient } from './lib/redis';
import { pgPool } from './lib/postgres';

const QUEUE_KEY = process.env.REDIS_QUEUE_KEY || 'events_queue';
const BATCH_SIZE = Number(process.env.WORKER_BATCH_SIZE) || 100;
const INTERVAL_MS = Number(process.env.WORKER_INTERVAL_MS) || 3000;

interface RawEvent {
  session_id: string;
  page_url: string;
  referrer: string;
  user_agent: string;
  timestamp: string;
}

async function drainBatch(): Promise<void> {
  // Pop up to BATCH_SIZE items atomically using a pipeline
  const pipeline = redisClient.pipeline();
  for (let i = 0; i < BATCH_SIZE; i++) {
    pipeline.rpop(QUEUE_KEY);
  }
  const results = await pipeline.exec();
  if (!results) return;

  const events: RawEvent[] = [];
  for (const [err, value] of results) {
    if (err || !value) continue;
    try {
      events.push(JSON.parse(value as string) as RawEvent);
    } catch {
      // skip malformed entries
    }
  }

  if (events.length === 0) return;

  // Bulk insert using a single query with unnest
  const sessionIds = events.map((e) => e.session_id);
  const pageUrls = events.map((e) => e.page_url);
  const referrers = events.map((e) => e.referrer || '');
  const userAgents = events.map((e) => e.user_agent || '');
  const timestamps = events.map((e) => e.timestamp || new Date().toISOString());

  await pgPool.query(
    `INSERT INTO events (session_id, page_url, referrer, user_agent, timestamp)
     SELECT * FROM unnest(
       $1::text[], $2::text[], $3::text[], $4::text[], $5::timestamptz[]
     )`,
    [sessionIds, pageUrls, referrers, userAgents, timestamps],
  );

  console.log(`[worker] inserted ${events.length} events`);
}

async function run(): Promise<void> {
  console.log(
    `[worker] started — batch size: ${BATCH_SIZE}, interval: ${INTERVAL_MS}ms`,
  );

  const tick = async () => {
    try {
      await drainBatch();
    } catch (err) {
      console.error('[worker] drain error:', err);
    } finally {
      setTimeout(tick, INTERVAL_MS);
    }
  };

  await tick();
}

run().catch((err) => {
  console.error('[worker] fatal error:', err);
  process.exit(1);
});
