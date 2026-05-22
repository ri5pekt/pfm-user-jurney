import { Pool } from 'pg';

export const pgPool = new Pool({
  host: process.env.POSTGRES_HOST || 'postgres',
  port: 5432,
  database: process.env.POSTGRES_DB || 'pfm_journeys',
  user: process.env.POSTGRES_USER || 'pfm_user',
  password: process.env.POSTGRES_PASSWORD || '',
  max: 5,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});
