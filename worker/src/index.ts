import { redisClient } from './lib/redis';
import { pgPool } from './lib/postgres';
import { parseAttribution } from './lib/attribution';
import { fetchGeoForIp } from './lib/geo';
import { getRates, toUsd } from './lib/fx';

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
  // First-ever INSERT sets attribution + geo.
  // Subsequent events (ON CONFLICT) update timing and page count.
  // Attribution upgrade: if the session was previously "direct" (or had no
  // utm_campaign) and this event carries richer attribution, promote it.
  // This handles cases where the landing page lost UTMs via a redirect but
  // a subsequent page in the same session carries the original UTMs.
  for (const ev of deduped) {
    const attr       = parseAttribution(ev.page_url, ev.referrer || '');
    const geo        = geoCache.get(ev.ip) ?? null;
    const isPageView = (ev.event_type || 'page_view') === 'page_view';
    await pgPool.query(
      `INSERT INTO sessions
         (session_id, first_seen, last_seen, entry_url, referrer,
          source, medium, channel, placement, campaign_id,
          utm_source, utm_medium, utm_campaign, page_count,
          ip, country, state, state_name, city,
          attribution_method, fingerprint_stitched)
       VALUES ($1,$2,$2,$3,$4, $5,$6,$7,$8,$9, $10,$11,$12, $18::int, $13,$14,$15,$16,$17, $19, false)
       ON CONFLICT (session_id) DO UPDATE
         SET last_seen  = GREATEST(sessions.last_seen, EXCLUDED.last_seen),
             page_count = sessions.page_count + $18::int,

             -- Promote source/channel if session was previously unattributed (direct)
             -- and this event carries a richer signal
             source      = CASE WHEN sessions.source = 'direct' AND EXCLUDED.source <> 'direct'
                                THEN EXCLUDED.source      ELSE sessions.source      END,
             medium      = CASE WHEN sessions.source = 'direct' AND EXCLUDED.source <> 'direct'
                                THEN EXCLUDED.medium      ELSE sessions.medium      END,
             channel     = CASE WHEN sessions.source = 'direct' AND EXCLUDED.source <> 'direct'
                                THEN EXCLUDED.channel     ELSE sessions.channel     END,
             utm_source  = CASE WHEN sessions.source = 'direct' AND EXCLUDED.source <> 'direct'
                                THEN EXCLUDED.utm_source  ELSE sessions.utm_source  END,
             utm_medium  = CASE WHEN sessions.source = 'direct' AND EXCLUDED.source <> 'direct'
                                THEN EXCLUDED.utm_medium  ELSE sessions.utm_medium  END,

             -- Promote attribution_method alongside source/channel
             attribution_method = CASE WHEN sessions.source = 'direct' AND EXCLUDED.source <> 'direct'
                                       THEN EXCLUDED.attribution_method
                                       ELSE sessions.attribution_method END,

             -- Promote utm_campaign independently: upgrade any session missing it
             -- (regardless of source) if this event has one
             utm_campaign = CASE WHEN (sessions.utm_campaign IS NULL OR sessions.utm_campaign = '')
                                      AND EXCLUDED.utm_campaign <> ''
                                 THEN EXCLUDED.utm_campaign ELSE sessions.utm_campaign END`,
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
        attr.attribution_method,
      ],
    );
  }

  // ── Enrich sessions with order data ─────────────────────────────
  // Only runs for order_completed events that carry metadata with order_id + value + currency
  const orderEvents = deduped.filter(e =>
    e.event_type === 'order_completed' &&
    e.metadata != null &&
    typeof e.metadata.order_id !== 'undefined' &&
    typeof e.metadata.value    === 'number' &&
    typeof e.metadata.currency === 'string',
  );

  if (orderEvents.length > 0) {
    const fxKey = process.env.FX_API_KEY?.trim() || null;
    const rates  = fxKey ? await getRates(fxKey) : null;

    for (const ev of orderEvents) {
      const meta       = ev.metadata!;
      const orderId    = String(meta.order_id);
      const amount     = meta.value as number;
      const currency   = meta.currency as string;
      const revenueUsd = rates ? toUsd(amount, currency, rates) : null;

      await pgPool.query(
        `UPDATE sessions
         SET order_id    = $1,
             revenue_usd = $2
         WHERE session_id = $3
           AND order_id IS NULL`,
        [orderId, revenueUsd, ev.session_id],
      );
    }
  }

  // ── Fingerprint-based session merge ──────────────────────────────
  // When fp_collected arrives for a direct/new session and a prior session with
  // the same fingerprint exists (within stitch window, richer attribution), absorb
  // the new session into the prior one rather than copying attribution across two rows:
  //   1. Migrate all events from new session → prior session
  //   2. Absorb page_count + last_seen into prior session; set fingerprint_stitched
  //   2b. Move order_id / revenue_usd from new → prior (critical for thank-you pages)
  //   3. Delete new session row
  //   4. Write Redis redirect key so the collector transparently routes any future
  //      events with the new session_id to the canonical prior session_id
  // If no merge applies, just upsert fp_sessions for future lookups.
  const stitchWindowDays    = Number(process.env.FP_STITCH_WINDOW_DAYS)        || 30;
  const mergeRedirectSecs   = (Number(process.env.FP_MERGE_REDIRECT_TTL_HOURS) || 24) * 3600;

  const fpEvents = deduped.filter(e =>
    e.event_type === 'fp_collected' &&
    typeof e.metadata?.fp === 'string' &&
    (e.metadata.fp as string).length > 0,
  );

  for (const ev of fpEvents) {
    const fp = (ev.metadata!.fp as string).trim();
    if (!fp) continue;

    // Read current session state (post-upsert in this batch)
    const sessionRes = await pgPool.query(
      `SELECT channel, page_count, last_seen, source, medium, placement,
              campaign_id, utm_source, utm_medium, utm_campaign, attribution_method
       FROM sessions WHERE session_id = $1`,
      [ev.session_id],
    );
    if (sessionRes.rows.length === 0) continue;
    const sess = sessionRes.rows[0];

    const isDirect = sess.channel === 'direct' || sess.channel === '';
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let prior: Record<string, any> | null = null;
    let priorIsRicher = false;

    if (isDirect) {
      const fpRes = await pgPool.query(
        `SELECT * FROM fp_sessions
         WHERE fingerprint = $1
           AND last_seen > NOW() - ($2 || ' days')::INTERVAL`,
        [fp, stitchWindowDays],
      );
      if (fpRes.rows.length > 0) {
        prior = fpRes.rows[0];
        priorIsRicher = !!(prior.channel && prior.channel !== 'direct' && prior.channel !== '');
      }
    }

    if (isDirect && priorIsRicher && prior) {
      const newSid   = ev.session_id;
      const priorSid = prior.session_id as string;

      // 1. Migrate all events from newSid → priorSid
      await pgPool.query(
        `UPDATE events SET session_id = $1 WHERE session_id = $2`,
        [priorSid, newSid],
      );

      // 2. Absorb newSid's timing and page_count into priorSid;
      //    set fingerprint_stitched to record that a merge occurred
      await pgPool.query(
        `UPDATE sessions SET
           last_seen            = GREATEST(last_seen, $1),
           page_count           = page_count + $2,
           fingerprint_stitched = true
         WHERE session_id = $3`,
        [sess.last_seen ?? new Date().toISOString(), sess.page_count ?? 0, priorSid],
      );

      // 2b. Move order data from newSid → priorSid if present.
      //     order_completed fires on the thank-you page which may land on session B.
      //     The events row is already migrated in step 1, but order_id/revenue_usd are
      //     denormalized onto the sessions row and must be copied before B is deleted.
      //     COALESCE preserves any order already on priorSid (don't overwrite a purchase).
      await pgPool.query(
        `UPDATE sessions SET
           order_id    = COALESCE(sessions.order_id,    b.order_id),
           revenue_usd = COALESCE(sessions.revenue_usd, b.revenue_usd)
         FROM (SELECT order_id, revenue_usd FROM sessions WHERE session_id = $1) AS b
         WHERE sessions.session_id = $2
           AND b.order_id IS NOT NULL`,
        [newSid, priorSid],
      );

      // 3. Delete the now-empty session row for newSid
      await pgPool.query(
        `DELETE FROM sessions WHERE session_id = $1`,
        [newSid],
      );

      // 4. Write Redis redirect key — collector will rewrite newSid → priorSid
      //    on every future event for the lifetime of the client session (24h)
      try {
        await redisClient.set(`merged:${newSid}`, priorSid, 'EX', mergeRedirectSecs);
      } catch {
        // Redis write failure is non-fatal; fp_sessions Postgres upsert still proceeds
      }

      // Upsert fp_sessions using prior session's richer attribution
      await pgPool.query(
        `INSERT INTO fp_sessions
           (fingerprint, session_id, source, medium, channel, placement, campaign_id,
            utm_source, utm_medium, utm_campaign, attribution_method)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
         ON CONFLICT (fingerprint) DO UPDATE SET
           session_id    = EXCLUDED.session_id,
           last_seen     = NOW(),
           session_count = fp_sessions.session_count + 1,
           source        = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.source        ELSE fp_sessions.source        END,
           medium        = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.medium        ELSE fp_sessions.medium        END,
           channel       = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.channel       ELSE fp_sessions.channel       END,
           placement     = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.placement     ELSE fp_sessions.placement     END,
           campaign_id   = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.campaign_id   ELSE fp_sessions.campaign_id   END,
           utm_source    = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.utm_source    ELSE fp_sessions.utm_source    END,
           utm_medium    = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.utm_medium    ELSE fp_sessions.utm_medium    END,
           utm_campaign  = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.utm_campaign  ELSE fp_sessions.utm_campaign  END,
           attribution_method = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                     THEN EXCLUDED.attribution_method
                                     ELSE fp_sessions.attribution_method END`,
        [
          fp, priorSid,
          prior.source, prior.medium, prior.channel,
          prior.placement, prior.campaign_id,
          prior.utm_source, prior.utm_medium, prior.utm_campaign,
          prior.attribution_method,
        ],
      );
    } else {
      // No merge — just upsert fp_sessions so this session is available for future lookups
      await pgPool.query(
        `INSERT INTO fp_sessions
           (fingerprint, session_id, source, medium, channel, placement, campaign_id,
            utm_source, utm_medium, utm_campaign, attribution_method)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
         ON CONFLICT (fingerprint) DO UPDATE SET
           session_id    = EXCLUDED.session_id,
           last_seen     = NOW(),
           session_count = fp_sessions.session_count + 1,
           source        = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.source        ELSE fp_sessions.source        END,
           medium        = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.medium        ELSE fp_sessions.medium        END,
           channel       = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.channel       ELSE fp_sessions.channel       END,
           placement     = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.placement     ELSE fp_sessions.placement     END,
           campaign_id   = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.campaign_id   ELSE fp_sessions.campaign_id   END,
           utm_source    = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.utm_source    ELSE fp_sessions.utm_source    END,
           utm_medium    = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.utm_medium    ELSE fp_sessions.utm_medium    END,
           utm_campaign  = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                THEN EXCLUDED.utm_campaign  ELSE fp_sessions.utm_campaign  END,
           attribution_method = CASE WHEN EXCLUDED.channel <> 'direct' AND EXCLUDED.channel <> ''
                                     THEN EXCLUDED.attribution_method
                                     ELSE fp_sessions.attribution_method END`,
        [
          fp, ev.session_id,
          sess.source, sess.medium, sess.channel,
          sess.placement, sess.campaign_id,
          sess.utm_source, sess.utm_medium, sess.utm_campaign,
          sess.attribution_method || 'direct',
        ],
      );
    }
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
