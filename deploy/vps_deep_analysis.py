import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("72.62.148.226", username="root", key_filename=r"C:\Users\denis\.ssh\id_ed25519", timeout=15)

def pg(sql):
    cmd = f"docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -c \"{sql}\""
    _, out, _ = c.exec_command(cmd, timeout=20)
    return out.read().decode("utf-8", errors="replace").strip()

# 1. All distinct page_url path prefixes (first 2 segments) — find noise patterns
print("=== Page path patterns (top 60 by frequency) ===")
rows = pg("""
  SELECT COUNT(*) as n,
         REGEXP_REPLACE(
           REGEXP_REPLACE(page_url, 'https?://[^/]+', ''),
           '(^/[^/]*/[^/]*).*', '\\1'
         ) as path_prefix
  FROM events
  GROUP BY path_prefix
  ORDER BY n DESC
  LIMIT 60
""")
for r in rows.splitlines(): print(r)

# 2. Noise: invalid/junk paths
print("\n=== Suspected noise page_urls ===")
rows = pg("""
  SELECT page_url, COUNT(*) as n FROM events
  WHERE page_url ~ '/null'
     OR page_url ~ '/undefined'
     OR page_url !~ 'particleformen\.com'
     OR page_url ~ '^https?://$'
  GROUP BY page_url ORDER BY n DESC LIMIT 20
""")
for r in rows.splitlines(): print(r)

# 3. All distinct query param keys across all URLs
print("\n=== All URL param keys seen (sorted) ===")
rows = pg(r"""
  SELECT DISTINCT param_key
  FROM events,
    REGEXP_SPLIT_TO_TABLE(
      REGEXP_REPLACE(page_url, '^[^?]*\??', ''), '&'
    ) AS param,
    LATERAL (SELECT SPLIT_PART(param, '=', 1) AS param_key) AS k
  WHERE param_key <> '' AND LENGTH(param_key) < 40
  ORDER BY param_key
""")
for r in rows.splitlines(): print(r)

# 4. UTM sources seen in entry URLs
print("\n=== utm_source values in entry_urls ===")
rows = pg(r"""
  SELECT COUNT(*) as n,
    (REGEXP_MATCHES(entry_url, '[?&]utm_source=([^&]+)'))[1] AS utm_src
  FROM sessions
  WHERE entry_url ~ 'utm_source'
  GROUP BY utm_src ORDER BY n DESC
""")
for r in rows.splitlines(): print(r)

# 5. Sessions currently unattributed (empty source)
print("\n=== Unattributed sessions (source='') ===")
rows = pg("""
  SELECT entry_url FROM sessions WHERE source = '' OR source IS NULL LIMIT 10
""")
for r in rows.splitlines(): print(r if r else "(none)")

# 6. Referrer domains seen in events
print("\n=== Referrer domains (top 30) ===")
rows = pg(r"""
  SELECT COUNT(*) as n,
    REGEXP_REPLACE(
      REGEXP_REPLACE(referrer, 'https?://(www\.)?', ''),
      '/.*', ''
    ) AS domain
  FROM events
  WHERE referrer <> ''
  GROUP BY domain ORDER BY n DESC LIMIT 30
""")
for r in rows.splitlines(): print(r)

# 7. Current session channel distribution
print("\n=== Session channel breakdown ===")
rows = pg("SELECT channel, source, COUNT(*) as n FROM sessions GROUP BY channel, source ORDER BY n DESC")
for r in rows.splitlines(): print(r)

c.close()
