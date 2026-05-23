import { pgPool } from './postgres';

export interface GeoResult {
  country:    string | null;
  state:      string | null;
  state_name: string | null;
  city:       string | null;
}

const GEO_TIMEOUT_MS = 4000;
const IP_API_BASE    = 'https://pro.ip-api.com/json';

export async function fetchGeoForIp(ip: string, apiKey: string): Promise<GeoResult | null> {
  if (!ip || !apiKey) return null;

  // Check cache first
  try {
    const cached = await pgPool.query<GeoResult & { lookup_count: number }>(
      `SELECT country, state, state_name, city, lookup_count
       FROM ip_geolocation_cache WHERE ip = $1`,
      [ip],
    );
    if (cached.rows.length > 0) {
      const row = cached.rows[0];
      // Bump usage stats asynchronously — don't block
      pgPool.query(
        `UPDATE ip_geolocation_cache
         SET last_seen_at = NOW(), lookup_count = lookup_count + 1
         WHERE ip = $1`,
        [ip],
      ).catch(() => { /* ignore */ });
      return { country: row.country, state: row.state, state_name: row.state_name, city: row.city };
    }
  } catch {
    // Cache miss or table not ready — fall through to API
  }

  // Call ip-api.com Pro
  const url = `${IP_API_BASE}/${encodeURIComponent(ip)}?fields=status,countryCode,region,regionName,city&key=${encodeURIComponent(apiKey)}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), GEO_TIMEOUT_MS);

  try {
    const res  = await fetch(url, { signal: controller.signal });
    clearTimeout(timer);
    const body = await res.json() as {
      status?: string;
      countryCode?: string;
      region?: string;
      regionName?: string;
      city?: string;
    };

    if (body?.status !== 'success') return null;

    const result: GeoResult = {
      country:    body.countryCode  ? String(body.countryCode).toUpperCase()  : null,
      state:      body.region       ? String(body.region).toUpperCase()        : null,
      state_name: body.regionName   ? String(body.regionName)                  : null,
      city:       body.city         ? String(body.city)                        : null,
    };

    // Write to cache (ignore race conditions)
    pgPool.query(
      `INSERT INTO ip_geolocation_cache
         (ip, country, state, state_name, city, lookup_count, first_seen_at, last_seen_at, created_at)
       VALUES ($1, $2, $3, $4, $5, 1, NOW(), NOW(), NOW())
       ON CONFLICT (ip) DO NOTHING`,
      [ip, result.country, result.state, result.state_name, result.city],
    ).catch(() => { /* ignore */ });

    return result;
  } catch {
    clearTimeout(timer);
    return null;
  }
}
