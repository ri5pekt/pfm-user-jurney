-- Add order tracking columns to sessions
-- Run manually: psql -U $POSTGRES_USER -d $POSTGRES_DB -f migrate_session_orders.sql

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS order_id    VARCHAR(100);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS revenue_usd NUMERIC(10,2);

CREATE INDEX IF NOT EXISTS idx_sessions_order_id  ON sessions (order_id)    WHERE order_id    IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_revenue   ON sessions (revenue_usd) WHERE revenue_usd IS NOT NULL;
