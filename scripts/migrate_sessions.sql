-- Sessions table — one row per session, holds attribution data from the entry event
-- Run manually: psql -U $POSTGRES_USER -d $POSTGRES_DB -f migrate_sessions.sql

CREATE TABLE IF NOT EXISTS sessions (
  session_id   VARCHAR(64)  PRIMARY KEY,
  first_seen   TIMESTAMPTZ  NOT NULL,
  last_seen    TIMESTAMPTZ  NOT NULL,
  entry_url    TEXT         NOT NULL DEFAULT '',
  referrer     TEXT         NOT NULL DEFAULT '',

  -- Parsed attribution
  source       TEXT         NOT NULL DEFAULT '',   -- 'Google Ads', 'Facebook', 'Klaviyo', ...
  medium       TEXT         NOT NULL DEFAULT '',   -- 'cpc', 'paid_social', 'email', 'organic', ...
  channel      TEXT         NOT NULL DEFAULT '',   -- 'paid_search', 'paid_social', 'email', 'organic_search', 'direct', ...
  placement    TEXT         NOT NULL DEFAULT '',   -- 'Instagram Reels', 'Facebook Feed', ...
  campaign_id  TEXT         NOT NULL DEFAULT '',

  -- Standard UTM (if present in entry URL)
  utm_source   TEXT         NOT NULL DEFAULT '',
  utm_medium   TEXT         NOT NULL DEFAULT '',
  utm_campaign TEXT         NOT NULL DEFAULT '',

  page_count   INT          NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_sessions_first_seen ON sessions (first_seen DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_channel    ON sessions (channel);
CREATE INDEX IF NOT EXISTS idx_sessions_source     ON sessions (source);
