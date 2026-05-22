import { Pool } from 'pg';

export const pgPool = new Pool({
  host: 'postgres',
  port: 5432,
  database: process.env.POSTGRES_DB || 'pfm_journeys',
  user: process.env.POSTGRES_USER || 'pfm_user',
  password: process.env.POSTGRES_PASSWORD || '',
  max: 5,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

pgPool.on('connect', () => {
  console.log('[worker] postgres connected');
});

pgPool.on('error', (err) => {
  console.error('[worker] postgres pool error:', err.message);
});
