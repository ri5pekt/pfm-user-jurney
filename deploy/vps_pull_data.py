import paramiko, sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
OUT_DIR = r"C:\Users\denis\Desktop\docker-projects\pfm-user-jurney\deploy\analysis"

os.makedirs(OUT_DIR, exist_ok=True)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def pg(sql, label=""):
    cmd = f"docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -c \"{sql}\""
    _, out, _ = c.exec_command(cmd, timeout=30)
    rows = [r for r in out.read().decode("utf-8", errors="replace").strip().splitlines() if r]
    if label:
        print(f"  [{label}] {len(rows)} rows")
    return rows

def save(filename, rows, header=""):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        if header:
            f.write(header + "\n")
        f.write("\n".join(rows))
    print(f"  -> saved {filename} ({len(rows)} rows)")
    return path

print("=== Pulling data from VPS ===\n")

# 1. All sessions with full attribution
rows = pg("""
  SELECT session_id, TO_CHAR(first_seen,'YYYY-MM-DD HH24:MI'), TO_CHAR(last_seen,'HH24:MI'),
         page_count, source, medium, channel, placement, campaign_id,
         utm_source, utm_medium, utm_campaign,
         REGEXP_REPLACE(entry_url, 'https?://[^/]+', '') AS entry_path,
         referrer
  FROM sessions ORDER BY first_seen DESC
""", "sessions")
save("sessions.tsv", rows, "session_id\tfirst_seen\tlast_seen\tpages\tsource\tmedium\tchannel\tplacement\tcampaign_id\tutm_source\tutm_medium\tutm_campaign\tentry_path\treferrer")

# 2. Channel breakdown
rows = pg("""
  SELECT channel, source, COUNT(*) AS n,
         ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER(),1) AS pct
  FROM sessions GROUP BY channel, source ORDER BY n DESC
""", "channel breakdown")
save("channel_breakdown.tsv", rows, "channel\tsource\tcount\tpct")

# 3. Entry paths by frequency
rows = pg(r"""
  SELECT COUNT(*) as n,
         REGEXP_REPLACE(REGEXP_REPLACE(entry_url,'https?://[^/]+',''),'\?.*','') AS path
  FROM sessions GROUP BY path ORDER BY n DESC LIMIT 80
""", "entry paths")
save("entry_paths.tsv", rows, "count\tpath")

# 4. Unattributed / anomalous sessions
rows = pg("""
  SELECT source, channel, entry_url, referrer
  FROM sessions
  WHERE source = '' OR source = 'direct' AND entry_url ~ '[?&](utm_|nbt|nb_|fbclid|gclid|msclkid|aleid|ScCid)'
  LIMIT 30
""", "anomalous sessions")
save("anomalous_sessions.tsv", rows, "source\tchannel\tentry_url\treferrer")

# 5. All distinct utm_source values with counts
rows = pg(r"""
  SELECT COUNT(*) as n,
         (REGEXP_MATCHES(entry_url, '[?&]utm_source=([^&]+)'))[1] AS utm_src
  FROM sessions WHERE entry_url ~ 'utm_source'
  GROUP BY utm_src ORDER BY n DESC
""", "utm_source values")
save("utm_sources.tsv", rows, "count\tutm_source")

# 6. All distinct referrer domains
rows = pg(r"""
  SELECT COUNT(*) as n,
         REGEXP_REPLACE(REGEXP_REPLACE(referrer,'https?://(www\.)?',''),'/.*','') AS domain
  FROM events WHERE referrer <> ''
  GROUP BY domain ORDER BY n DESC
""", "referrer domains")
save("referrer_domains.tsv", rows, "count\tdomain")

# 7. Recent 500 events with full detail
rows = pg("""
  SELECT TO_CHAR(timestamp,'HH24:MI:SS'), session_id,
         REGEXP_REPLACE(page_url,'https?://[^/]+','') AS url_path,
         referrer
  FROM events ORDER BY timestamp DESC LIMIT 500
""", "recent events")
save("recent_events.tsv", rows, "time\tsession_id\turl_path\treferrer")

# 8. Noise check: page_url patterns that look suspicious
rows = pg(r"""
  SELECT COUNT(*) as n,
         REGEXP_REPLACE(REGEXP_REPLACE(page_url,'https?://[^/]+',''),'\?.*','') AS path
  FROM events
  WHERE page_url ~ '(null|undefined|error|test|debug|404|500)'
     OR LENGTH(REGEXP_REPLACE(page_url,'https?://[^/]+','')) < 3
  GROUP BY path ORDER BY n DESC
""", "suspicious paths")
save("suspicious_paths.tsv", rows, "count\tpath")

# 9. Sessions with source='' (still unmatched)
rows = pg("SELECT entry_url, referrer FROM sessions WHERE source = '' LIMIT 30", "unmatched")
save("unmatched_sessions.tsv", rows, "entry_url\treferrer")

# 10. Referrer domains seen for the first time (not yet handled)
rows = pg(r"""
  SELECT COUNT(*) as n,
         REGEXP_REPLACE(REGEXP_REPLACE(referrer,'https?://(www\.)?',''),'/.*','') AS domain
  FROM events WHERE referrer <> ''
    AND referrer !~ 'particleformen|google|facebook|instagram|bing|yahoo|duckduckgo|snapchat|youtube|threads|pinterest|afterpay|pstmrk|deref-mail|edgepilot|netzero|earthlink|android-app|brave|mail\.google'
  GROUP BY domain ORDER BY n DESC LIMIT 40
""", "unhandled referrers")
save("unhandled_referrers.tsv", rows, "count\tdomain")

print("\n=== Summary ===")
print(f"  Output directory: {OUT_DIR}")
c.close()
