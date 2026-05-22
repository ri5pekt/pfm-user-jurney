/**
 * One-time backfill: regenerate sessions table from all existing events in the DB.
 * Run with: npx ts-node src/backfill.ts
 */
import { pgPool } from './lib/postgres';
import { parseAttribution } from './lib/attribution';

const DEDUP_WINDOW_MS = 5000;

function getBasePath(url: string): string {
  try { return new URL(url).pathname; } catch { return url; }
}

async function run() {
  console.log('Connecting to DB…');
  const client = await pgPool.connect();

  try {
    // Load all events ordered by timestamp (oldest first)
    console.log('Loading events…');
    const { rows: events } = await client.query<{
      session_id: string;
      page_url:   string;
      referrer:   string;
      timestamp:  string;
    }>(`SELECT session_id, page_url, referrer, timestamp
        FROM events ORDER BY timestamp ASC`);

    console.log(`  ${events.length} events loaded`);

    // Group by session — deduplicate and build per-session first/last/count
    const firstEvent = new Map<string, { page_url: string; referrer: string; timestamp: string }>();
    const lastSeen   = new Map<string, string>();
    const pageCount  = new Map<string, number>();

    // Track last event per session for deduplication
    const lastEvtPath = new Map<string, { path: string; timeMs: number }>();
    let dedupedCount = 0;

    for (const ev of events) {
      const path   = getBasePath(ev.page_url);
      const timeMs = new Date(ev.timestamp).getTime();
      const prev   = lastEvtPath.get(ev.session_id);

      // Skip if same path within dedup window (A/B redirect — previous event is the dupe)
      if (prev && prev.path === path && timeMs - prev.timeMs <= DEDUP_WINDOW_MS) {
        // Replace the first_event entry if this is the first page
        if (!firstEvent.has(ev.session_id)) {
          firstEvent.set(ev.session_id, { page_url: ev.page_url, referrer: ev.referrer, timestamp: ev.timestamp });
        }
        lastEvtPath.set(ev.session_id, { path, timeMs });
        lastSeen.set(ev.session_id, ev.timestamp);
        dedupedCount++;
        continue;
      }

      lastEvtPath.set(ev.session_id, { path, timeMs });

      if (!firstEvent.has(ev.session_id)) {
        firstEvent.set(ev.session_id, { page_url: ev.page_url, referrer: ev.referrer, timestamp: ev.timestamp });
      }
      lastSeen.set(ev.session_id, ev.timestamp);
      pageCount.set(ev.session_id, (pageCount.get(ev.session_id) ?? 0) + 1);
    }

    const sessionIds = Array.from(firstEvent.keys());
    console.log(`  ${sessionIds.length} unique sessions (${dedupedCount} A/B redirect dupes removed)`);

    // Clear sessions and backfill
    console.log('Truncating sessions…');
    await client.query('TRUNCATE TABLE sessions');

    console.log('Inserting sessions…');
    let done = 0;
    for (const sid of sessionIds) {
      const first = firstEvent.get(sid)!;
      const attr  = parseAttribution(first.page_url, first.referrer);

      await client.query(
        `INSERT INTO sessions
           (session_id, first_seen, last_seen, entry_url, referrer,
            source, medium, channel, placement, campaign_id,
            utm_source, utm_medium, utm_campaign, page_count)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
         ON CONFLICT (session_id) DO NOTHING`,
        [
          sid,
          first.timestamp,
          lastSeen.get(sid),
          first.page_url,
          first.referrer,
          attr.source, attr.medium, attr.channel, attr.placement, attr.campaign_id,
          attr.utm_source, attr.utm_medium, attr.utm_campaign,
          pageCount.get(sid) ?? 1,
        ],
      );

      done++;
      if (done % 500 === 0) process.stdout.write(`  ${done}/${sessionIds.length}\r`);
    }

    // Verify
    const { rows: [{ count }] } = await client.query('SELECT COUNT(*) FROM sessions');
    console.log(`\nDone. Sessions in DB: ${count}`);

    const { rows: breakdown } = await client.query(
      `SELECT channel, source, COUNT(*) AS n FROM sessions GROUP BY channel, source ORDER BY n DESC LIMIT 15`
    );
    console.log('\nChannel breakdown:');
    for (const r of breakdown) console.log(`  ${r.channel.padEnd(18)} ${String(r.source).padEnd(20)} ${r.n}`);

  } finally {
    client.release();
    await pgPool.end();
  }
}

run().catch(err => { console.error(err); process.exit(1); });
