-- Add event_type to events table
-- Run manually: psql -U $POSTGRES_USER -d $POSTGRES_DB -f migrate_event_type.sql

ALTER TABLE events
  ADD COLUMN IF NOT EXISTS event_type VARCHAR(64) NOT NULL DEFAULT 'page_view';

CREATE INDEX IF NOT EXISTS idx_events_event_type ON events (event_type);
