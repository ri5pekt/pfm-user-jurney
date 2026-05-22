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
