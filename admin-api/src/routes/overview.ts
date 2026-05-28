import { Router, Request, Response } from 'express';
import { pgPool } from '../lib/postgres';

export const overviewRouter = Router();

function normalizePath(url: string): string {
  try {
    let p = new URL(url).pathname;
    p = p.replace(/\/$/, '') || '/';
    // Strip numeric-only segments (order IDs, subscription IDs, etc.)
    p = p.replace(/\/\d+/g, '');
    return p || '/';
  } catch {
    return '/';
  }
}

const PATH_LABELS: Record<string, string> = {
  '/':                      'Home',
  '/cart-page':             'Cart',
  '/checkout':              'Checkout',
  '/thank-you-order':       '✓ Thank You',
  '/best-sellers':          'Best Sellers',
  '/all-products':          'All Products',
  '/build-your-own-bundle': 'Bundle Builder',
  '/particle-magazine':     'Magazine',
  '/faq-support':           'FAQ',
  '/my-account':            'My Account',
  '/my-account/orders':     'My Orders',
  '/my-account/view-order': 'View Order',
  '/my-account/view-subscription': 'My Subscription',
  '/my-account/particle-rewards':  'Rewards',
  '/refund-policy':         'Refund Policy',
  '/pages/about':           'About',
};

function pathLabel(path: string): string {
  if (PATH_LABELS[path]) return PATH_LABELS[path];
  const segs = path.split('/').filter(Boolean);
  if (!segs.length) return 'Home';
  if (segs[0] === 'product' && segs[1])
    return segs[1].replace(/^particle-/, '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  if (segs[0] === 'lpage' && segs[1])
    return 'LP: ' + segs[1].replace(/^particle-/, '').split('-').slice(0, 4).join(' ');
  return '/' + segs.slice(0, 2).join('/');
}

function pageType(path: string): string {
  if (path.includes('thank-you'))  return 'thankyou';
  if (path.includes('checkout'))   return 'checkout';
  if (path.includes('cart'))       return 'cart';
  if (path.startsWith('/lpage'))   return 'landing';
  if (path.startsWith('/product')) return 'product';
  if (path === '/')                return 'home';
  if (path.startsWith('/my-account/view-order') ||
      path.startsWith('/my-account/orders') ||
      path.startsWith('/my-account/view-subscription')) return 'postpurchase';
  return 'page';
}

// GET /overview/funnel?start=ISO&end=ISO
overviewRouter.get('/funnel', async (req: Request, res: Response): Promise<void> => {
  try {
    const start = req.query.start as string | undefined;
    const end   = req.query.end   as string | undefined;

    const conditions: string[] = [];
    const values: unknown[]    = [];
    if (start) { conditions.push(`s.first_seen >= $${values.push(start)}`); }
    if (end)   { conditions.push(`s.first_seen <= $${values.push(end)}`);   }
    const sessWhere = conditions.length ? 'WHERE ' + conditions.map(c => c.replace(/^s\./, '')).join(' AND ') : '';
    const joinWhere = conditions.length ? 'WHERE ' + conditions.join(' AND ') : '';

    // ── Run all heavy queries in parallel ────────────────────────────
    // Previously: loaded all 35k sessions + 72k events into Node.js memory.
    // Now: push all aggregation down to Postgres, return only summary rows.
    const [statsRes, sourceAggRes, countriesRes, funnelRes, pagesRes] = await Promise.all([

      // 1. Total sessions + revenue stats (1 row)
      pgPool.query<{
        total: string; total_revenue: string; aov: string; tracked_orders: string;
      }>(
        `SELECT COUNT(*)                                                    AS total,
                COALESCE(SUM(revenue_usd), 0)::numeric                    AS total_revenue,
                COALESCE(AVG(revenue_usd) FILTER (WHERE revenue_usd IS NOT NULL), 0)::numeric AS aov,
                COUNT(*) FILTER (WHERE order_id IS NOT NULL)               AS tracked_orders
         FROM sessions ${sessWhere}`,
        values,
      ),

      // 2. Source / channel / campaign aggregates (~20-100 rows, not 35k)
      pgPool.query<{
        source: string; channel: string; utm_campaign: string;
        count: string; orders: string; revenue: string;
      }>(
        `SELECT COALESCE(source, 'direct')       AS source,
                COALESCE(channel, 'direct')      AS channel,
                COALESCE(utm_campaign, '')        AS utm_campaign,
                COUNT(*)                          AS count,
                COUNT(*) FILTER (WHERE order_id IS NOT NULL) AS orders,
                COALESCE(SUM(revenue_usd), 0)::numeric       AS revenue
         FROM sessions ${sessWhere}
         GROUP BY 1, 2, 3
         ORDER BY count DESC`,
        values,
      ),

      // 3. Countries (30 rows)
      pgPool.query<{ country: string; count: string }>(
        `SELECT country, COUNT(*) AS count
         FROM sessions
         WHERE country IS NOT NULL AND country <> '' ${conditions.length ? 'AND ' + conditions.map(c => c.replace(/^s\./, '')).join(' AND ') : ''}
         GROUP BY country
         ORDER BY count DESC
         LIMIT 30`,
        values,
      ),

      // 4. Funnel counts via SQL JOIN (1 row — no more loading 72k events)
      pgPool.query<{ cart: string; checkout: string; thankyou: string }>(
        `SELECT
           COUNT(DISTINCT CASE WHEN e.page_url LIKE '%/cart%' OR e.page_url LIKE '%-cart%' THEN e.session_id END) AS cart,
           COUNT(DISTINCT CASE WHEN e.page_url LIKE '%/checkout%'   THEN e.session_id END)                        AS checkout,
           COUNT(DISTINCT CASE WHEN e.page_url LIKE '%thank-you%'   THEN e.session_id END)                        AS thankyou
         FROM events e
         INNER JOIN sessions s ON s.session_id = e.session_id
         ${joinWhere}`,
        values,
      ),

      // 5. Top page URLs by unique sessions (~100-200 rows, not 72k)
      pgPool.query<{ page_url: string; count: string }>(
        `SELECT e.page_url, COUNT(DISTINCT e.session_id) AS count
         FROM events e
         INNER JOIN sessions s ON s.session_id = e.session_id
         WHERE e.event_type = 'page_view'
         ${conditions.length ? 'AND ' + conditions.join(' AND ') : ''}
         GROUP BY e.page_url
         ORDER BY count DESC
         LIMIT 200`,
        values,
      ),
    ]);

    const total = parseInt(statsRes.rows[0].total, 10);
    if (total === 0) {
      res.json({ total: 0, totalRevenue: 0, aov: 0, trackedOrders: 0, countries: [],
        sources: [], landingPages: [], pages: [], productPages: [],
        cart: { count: 0, pct: 0 }, checkout: { count: 0, pct: 0 }, thankyou: { count: 0, pct: 0 } });
      return;
    }

    const totalRevenue  = parseFloat(statsRes.rows[0].total_revenue);
    const aov           = parseFloat(statsRes.rows[0].aov);
    const trackedOrders = parseInt(statsRes.rows[0].tracked_orders, 10);
    const countries     = countriesRes.rows.map(r => ({
      country: r.country,
      count:   parseInt(r.count, 10),
      pct:     Math.round(parseInt(r.count, 10) / total * 100),
    }));

    const cartCount     = parseInt(funnelRes.rows[0]?.cart     ?? '0', 10);
    const checkoutCount = parseInt(funnelRes.rows[0]?.checkout ?? '0', 10);
    const thankyouCount = parseInt(funnelRes.rows[0]?.thankyou ?? '0', 10);

    // ── Build source → channel → campaign hierarchy from flat SQL rows ──
    const CHANNEL_LABELS: Record<string, string> = {
      paid_social:      'Paid Social',   paid_search:      'Paid Search',
      paid_shopping:    'Paid Shopping', paid_other:        'Paid Other',
      email:            'Email',         sms:               'SMS',
      organic_search:   'Organic Search', organic_shopping: 'Organic Shopping',
      organic_social:   'Organic Social', referral:         'Referral',
      direct:           'Direct',
    };

    type CampAgg = { count: number; revenue: number; orders: number };
    type ChanAgg = { count: number; revenue: number; orders: number; camps: Map<string, CampAgg> };
    const srcMap = new Map<string, { count: number; orders: number; revenue: number; chans: Map<string, ChanAgg> }>();

    for (const row of sourceAggRes.rows) {
      const src  = row.source || 'direct';
      const chan  = row.channel || 'direct';
      const camp  = row.utm_campaign || '';
      const cnt   = parseInt(row.count, 10);
      const ords  = parseInt(row.orders, 10);
      const rev   = parseFloat(row.revenue);

      if (!srcMap.has(src)) srcMap.set(src, { count: 0, orders: 0, revenue: 0, chans: new Map() });
      const srcAgg = srcMap.get(src)!;
      srcAgg.count   += cnt;
      srcAgg.orders  += ords;
      srcAgg.revenue += rev;

      if (!srcAgg.chans.has(chan)) srcAgg.chans.set(chan, { count: 0, orders: 0, revenue: 0, camps: new Map() });
      const chanAgg = srcAgg.chans.get(chan)!;
      chanAgg.count   += cnt;
      chanAgg.orders  += ords;
      chanAgg.revenue += rev;

      if (!chanAgg.camps.has(camp)) chanAgg.camps.set(camp, { count: 0, orders: 0, revenue: 0 });
      const campAgg = chanAgg.camps.get(camp)!;
      campAgg.count   += cnt;
      campAgg.orders  += ords;
      campAgg.revenue += rev;
    }

    const pct = (n: number) => Math.round((n / total) * 100);

    const sources = Array.from(srcMap.entries())
      .map(([id, { count, orders, revenue, chans }]) => {
        const label     = !id || id === 'direct' ? 'Direct' : id;
        const convRate  = count > 0 ? Math.round(orders / count * 1000) / 10 : 0;

        const breakdown = Array.from(chans.entries())
          .map(([chan, agg]) => {
            const chanConvRate = agg.count > 0 ? Math.round(agg.orders / agg.count * 1000) / 10 : 0;
            const allCamps = Array.from(agg.camps.entries())
              .map(([camp, c]) => ({
                label:   camp || '(not set)',
                count:   c.count,
                orders:  c.orders,
                revenue: Math.round(c.revenue * 100) / 100,
                pct:     Math.round((c.count / agg.count) * 100),
              }))
              .sort((a, b) => b.count - a.count);
            const campBreakdown = allCamps.some(c => c.label !== '(not set)') ? allCamps : [];
            return {
              label:    CHANNEL_LABELS[chan] ?? chan,
              key:      chan,
              count:    agg.count,
              orders:   agg.orders,
              revenue:  Math.round(agg.revenue * 100) / 100,
              pct:      Math.round((agg.count / count) * 100),
              convRate: chanConvRate,
              breakdown: campBreakdown,
            };
          })
          .sort((a, b) => b.count - a.count);

        const hasNamedCampaigns   = breakdown.some(ch => ch.breakdown && ch.breakdown.length > 0);
        const hasMultipleChannels = breakdown.length > 1;
        const finalBreakdown      = (hasNamedCampaigns || hasMultipleChannels) ? breakdown : [];

        return { id, label, count, pct: pct(count), orders, convRate, revenue: Math.round(revenue * 100) / 100, breakdown: finalBreakdown };
      })
      .sort((a, b) => b.count - a.count);

    // ── Aggregate page visits from compact SQL result (~200 rows) ────
    const landingCount      = new Map<string, number>();
    const pageCount         = new Map<string, number>();
    const productCount      = new Map<string, number>();
    const postPurchaseCount = new Map<string, number>();

    for (const row of pagesRes.rows) {
      const path  = normalizePath(row.page_url);
      const count = parseInt(row.count, 10);
      const type  = pageType(path);

      if      (type === 'landing')      landingCount.set(path,      (landingCount.get(path)      ?? 0) + count);
      else if (type === 'home' || type === 'page') pageCount.set(path, (pageCount.get(path) ?? 0) + count);
      else if (type === 'product')      productCount.set(path,      (productCount.get(path)      ?? 0) + count);
      else if (type === 'postpurchase') postPurchaseCount.set(path, (postPurchaseCount.get(path) ?? 0) + count);
    }

    const toArr = (m: Map<string, number>) =>
      Array.from(m.entries())
        .map(([path, count]) => ({ id: path, label: pathLabel(path), type: pageType(path), count, pct: pct(count) }))
        .sort((a, b) => b.count - a.count);

    res.json({
      total,
      totalRevenue:  Math.round(totalRevenue * 100) / 100,
      aov:           Math.round(aov * 100) / 100,
      trackedOrders,
      countries,
      sources,
      landingPages:      toArr(landingCount),
      pages:             toArr(pageCount),
      productPages:      toArr(productCount),
      postPurchasePages: toArr(postPurchaseCount),
      cart:     { count: cartCount,     pct: pct(cartCount) },
      checkout: { count: checkoutCount, pct: pct(checkoutCount) },
      thankyou: { count: thankyouCount, pct: pct(thankyouCount) },
    });
  } catch (err) {
    console.error('[admin-api] /overview/funnel error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /overview/flow?min_pages=2&limit=300
overviewRouter.get('/flow', async (req: Request, res: Response): Promise<void> => {
  try {
    const minPages = Math.max(2, parseInt(req.query.min_pages as string) || 2);
    const limit    = Math.min(1000, parseInt(req.query.limit as string) || 300);

    const sessionsRes = await pgPool.query<{
      session_id: string; channel: string; source: string;
    }>(
      `SELECT session_id, channel, source
       FROM sessions
       WHERE page_count >= $1
       ORDER BY first_seen DESC
       LIMIT $2`,
      [minPages, limit],
    );

    if (sessionsRes.rows.length === 0) {
      res.json({ nodes: [], edges: [] });
      return;
    }

    const sessionIds = sessionsRes.rows.map(r => r.session_id);

    const eventsRes = await pgPool.query<{
      session_id: string; page_url: string; timestamp: string;
    }>(
      `SELECT session_id, page_url, timestamp
       FROM events
       WHERE session_id = ANY($1)
       ORDER BY session_id, timestamp`,
      [sessionIds],
    );

    const sessionEvents = new Map<string, { page_url: string; ts: number }[]>();
    for (const ev of eventsRes.rows) {
      if (!sessionEvents.has(ev.session_id)) sessionEvents.set(ev.session_id, []);
      sessionEvents.get(ev.session_id)!.push({
        page_url: ev.page_url,
        ts: new Date(ev.timestamp).getTime(),
      });
    }

    const nodeCount = new Map<string, number>();
    const nodeType  = new Map<string, string>();
    const nodeLabel = new Map<string, string>();
    const edgeCount = new Map<string, number>();

    for (const session of sessionsRes.rows) {
      const events = sessionEvents.get(session.session_id) ?? [];
      if (events.length === 0) continue;

      const paths: string[] = [];
      let lastPath = '';
      let lastTs   = 0;
      for (const ev of events) {
        const path = normalizePath(ev.page_url);
        if (path === lastPath && ev.ts - lastTs < 5000) continue;
        paths.push(path);
        lastPath = path;
        lastTs   = ev.ts;
      }
      if (paths.length === 0) continue;

      const srcId    = `src:${session.channel}:${session.source}`;
      const srcLabel = session.source === 'direct' ? 'Direct' : session.source;
      nodeCount.set(srcId, (nodeCount.get(srcId) ?? 0) + 1);
      nodeType.set(srcId,  'source');
      nodeLabel.set(srcId, srcLabel);

      const firstId = `page:${paths[0]}`;
      nodeCount.set(firstId, (nodeCount.get(firstId) ?? 0) + 1);
      nodeType.set(firstId,  pageType(paths[0]));
      nodeLabel.set(firstId, pathLabel(paths[0]));

      const e0 = `${srcId}||${firstId}`;
      edgeCount.set(e0, (edgeCount.get(e0) ?? 0) + 1);

      for (let i = 1; i < paths.length; i++) {
        const fromId = `page:${paths[i - 1]}`;
        const toId   = `page:${paths[i]}`;
        nodeCount.set(toId, (nodeCount.get(toId) ?? 0) + 1);
        nodeType.set(toId,  pageType(paths[i]));
        nodeLabel.set(toId, pathLabel(paths[i]));

        const ek = `${fromId}||${toId}`;
        edgeCount.set(ek, (edgeCount.get(ek) ?? 0) + 1);
      }
    }

    const nodes = Array.from(nodeCount.entries()).map(([id, count]) => ({
      id,
      label: nodeLabel.get(id) ?? id,
      type:  nodeType.get(id)  ?? 'page',
      count,
    }));

    const edges = Array.from(edgeCount.entries()).map(([key, count]) => {
      const sep = key.indexOf('||');
      return { source: key.slice(0, sep), target: key.slice(sep + 2), count };
    });

    res.json({ nodes, edges, sessions_analyzed: sessionsRes.rows.length });
  } catch (err) {
    console.error('[admin-api] /overview/flow error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
