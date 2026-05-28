-- User Journey Tracker — PostgreSQL Schema
-- Runs automatically on first container start via docker-entrypoint-initdb.d

CREATE TABLE IF NOT EXISTS events (
    id          BIGSERIAL PRIMARY KEY,
    session_id  VARCHAR(64)     NOT NULL,
    page_url    TEXT            NOT NULL,
    referrer    TEXT            NOT NULL DEFAULT '',
    user_agent  TEXT            NOT NULL DEFAULT '',
    timestamp   TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Core query indexes
CREATE INDEX IF NOT EXISTS idx_events_session_id  ON events (session_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp   ON events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_session_ts  ON events (session_id, timestamp ASC);

CREATE TABLE IF NOT EXISTS saved_funnels (
  id          SERIAL       PRIMARY KEY,
  name        VARCHAR(120) NOT NULL,
  config      JSONB        NOT NULL,
  created_by  VARCHAR(120),
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
