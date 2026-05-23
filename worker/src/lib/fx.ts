import { redisClient } from './redis';

const CACHE_KEY  = 'fx:rates';
const CACHE_TTL  = 6 * 60 * 60; // 6 hours in seconds
const API_BASE   = 'https://v6.exchangerate-api.com/v6';
const TIMEOUT_MS = 8000;

type Rates = Record<string, number>;

async function fetchRatesFromApi(apiKey: string): Promise<Rates | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res  = await fetch(`${API_BASE}/${apiKey}/latest/USD`, { signal: controller.signal });
    clearTimeout(timer);
    const body = await res.json() as { result?: string; conversion_rates?: Rates };
    if (body?.result !== 'success' || !body.conversion_rates) return null;
    return body.conversion_rates;
  } catch {
    clearTimeout(timer);
    return null;
  }
}

/**
 * Returns cached rates from Redis, refreshing from the API when the cache
 * has expired (TTL 6 hours = 4 updates per day maximum).
 */
export async function getRates(apiKey: string): Promise<Rates | null> {
  try {
    const cached = await redisClient.get(CACHE_KEY);
    if (cached) return JSON.parse(cached) as Rates;
  } catch { /* Redis miss — fall through to API */ }

  const rates = await fetchRatesFromApi(apiKey);
  if (!rates) return null;

  try {
    await redisClient.set(CACHE_KEY, JSON.stringify(rates), 'EX', CACHE_TTL);
  } catch { /* ignore cache write failure */ }

  console.log('[fx] rates refreshed from exchangerate-api.com');
  return rates;
}

/**
 * Convert `amount` in `currency` to USD.
 * Returns null if currency unknown or rates unavailable.
 */
export function toUsd(amount: number, currency: string, rates: Rates): number | null {
  const upper = currency.toUpperCase();
  if (upper === 'USD') return Math.round(amount * 100) / 100;
  const rate = rates[upper];
  if (!rate) return null;
  return Math.round((amount / rate) * 100) / 100;
}
