-- Add JSONB metadata column to events for custom event data (order_id, total, currency, etc.)
-- Run manually: psql -U $POSTGRES_USER -d $POSTGRES_DB -f migrate_metadata.sql

ALTER TABLE events ADD COLUMN IF NOT EXISTS metadata JSONB;

-- Partial index on order_id for fast order deduplication queries
CREATE INDEX IF NOT EXISTS idx_events_metadata_order_id
  ON events ((metadata->>'order_id'))
  WHERE event_type = 'order_completed';
