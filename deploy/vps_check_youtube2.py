import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def q(label, sql):
    print(f"\n=== {label} ===")
    _, out, _ = c.exec_command(f'docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -F "\\t" -c "{sql}"', timeout=20)
    print(out.read().decode("utf-8", errors="replace").strip())

# Are youtube.com referrer events the FIRST event of their session?
q("YouTube referrer - first vs mid-session", """
SELECT
  CASE WHEN e.timestamp = mins.first_ts THEN 'first_event' ELSE 'mid_session' END as position,
  COUNT(*) as events,
  COUNT(DISTINCT e.session_id) as sessions
FROM events e
JOIN (SELECT session_id, MIN(timestamp) as first_ts FROM events GROUP BY session_id) mins
  ON e.session_id = mins.session_id
WHERE e.referrer LIKE '%youtube.com%'
  AND e.referrer NOT LIKE '%particleformen%'
GROUP BY 1
""")

# What are those sessions attributed as RIGHT NOW?
q("First-event youtube referrer - current session attribution", """
SELECT s.source, s.channel, COUNT(*) n
FROM events e
JOIN (SELECT session_id, MIN(timestamp) as first_ts FROM events GROUP BY session_id) mins
  ON e.session_id = mins.session_id AND e.timestamp = mins.first_ts
JOIN sessions s ON e.session_id = s.session_id
WHERE e.referrer LIKE '%youtube.com%'
  AND e.referrer NOT LIKE '%particleformen%'
GROUP BY 1,2 ORDER BY n DESC
""")

# YouTube Ads via gad_source=2 (Demand Gen / YouTube Discovery) - how many?
q("Sessions with gad_source=2 in entry URL (YouTube Demand Gen)", """
SELECT source, channel, COUNT(*) n FROM sessions
WHERE entry_url LIKE '%gad_source=2%'
GROUP BY 1,2 ORDER BY n DESC
""")

# Sessions with gbraid in entry URL
q("Sessions with gbraid in entry URL", """
SELECT source, channel, COUNT(*) n FROM sessions
WHERE entry_url LIKE '%gbraid=%'
GROUP BY 1,2 ORDER BY n DESC
""")

# nbt with ytv platform
q("Sessions with nbt:adwords:ytv (YouTube Video ad)", """
SELECT source, channel, COUNT(*) n FROM sessions
WHERE entry_url LIKE '%nbt=%adwords%ytv%'
   OR entry_url LIKE '%nbt=nb:adwords:ytv%'
   OR entry_url LIKE '%nbt%3Aadwords%3Aytv%'
GROUP BY 1,2 ORDER BY n DESC
""")

# How many sessions have utm_campaign containing YouTube?
q("Sessions with YouTube in utm_campaign", """
SELECT source, channel, COUNT(*) n FROM sessions
WHERE entry_url ILIKE '%utm_campaign%youtube%'
   OR entry_url ILIKE '%utm_campaign%_yt_%'
GROUP BY 1,2 ORDER BY n DESC
""")

c.close()
