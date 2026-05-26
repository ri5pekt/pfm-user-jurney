-- Fingerprint stitching + attribution method — run manually after migrate_sessions.sql
-- psql -U $POSTGRES_USER -d $POSTGRES_DB -f migrate_fingerprint.sql

-- Add attribution tracking columns to sessions
ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS attribution_method   TEXT    NOT NULL DEFAULT 'direct';
ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS fingerprint_stitched BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_sessions_attr_method ON sessions (attribution_method);
-- Partial index — only index rows where stitching occurred (keeps index small)
CREATE INDEX IF NOT EXISTS idx_sessions_fp_stitched ON sessions (fingerprint_stitched)
  WHERE fingerprint_stitched = true;

-- Fingerprint → session mapping table
-- Stores the richest known attribution for each browser fingerprint within the stitch window.
-- One row per fingerprint; updated on every new session that carries that fingerprint.
CREATE TABLE IF NOT EXISTS fp_sessions (
  fingerprint        TEXT        PRIMARY KEY,
  session_id         TEXT        NOT NULL,
  source             TEXT        NOT NULL DEFAULT '',
  medium             TEXT        NOT NULL DEFAULT '',
  channel            TEXT        NOT NULL DEFAULT '',
  placement          TEXT        NOT NULL DEFAULT '',
  campaign_id        TEXT        NOT NULL DEFAULT '',
  utm_source         TEXT        NOT NULL DEFAULT '',
  utm_medium         TEXT        NOT NULL DEFAULT '',
  utm_campaign       TEXT        NOT NULL DEFAULT '',
  attribution_method TEXT        NOT NULL DEFAULT 'direct',
  first_seen         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  session_count      INT         NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_fp_sessions_session_id ON fp_sessions (session_id);
CREATE INDEX IF NOT EXISTS idx_fp_sessions_channel    ON fp_sessions (channel);
CREATE INDEX IF NOT EXISTS idx_fp_sessions_last_seen  ON fp_sessions (last_seen DESC);
