-- Geo / IP enrichment — run manually after migrate_sessions.sql
-- psql -U $POSTGRES_USER -d $POSTGRES_DB -f migrate_geo.sql

-- IP geolocation cache (same structure as pfm-surveys)
CREATE TABLE IF NOT EXISTS ip_geolocation_cache (
  ip           VARCHAR(45) PRIMARY KEY,
  country      VARCHAR(2),
  state        VARCHAR(10),
  state_name   VARCHAR(255),
  city         VARCHAR(255),
  lookup_count INTEGER   NOT NULL DEFAULT 1,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ip_geo_last_seen    ON ip_geolocation_cache (last_seen_at);
CREATE INDEX IF NOT EXISTS idx_ip_geo_lookup_count ON ip_geolocation_cache (lookup_count);

-- Add geo columns to sessions
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS ip         VARCHAR(45);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS country    VARCHAR(2);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS state      VARCHAR(10);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS state_name VARCHAR(255);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS city       VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_sessions_country ON sessions (country);
