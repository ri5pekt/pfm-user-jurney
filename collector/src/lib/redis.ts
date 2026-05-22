import Redis from 'ioredis';

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

export const redisClient = new Redis(REDIS_URL, {
  maxRetriesPerRequest: 3,
  lazyConnect: false,
});

redisClient.on('connect', () => {
  console.log('[collector] redis connected');
});

redisClient.on('error', (err) => {
  console.error('[collector] redis error:', err.message);
});
