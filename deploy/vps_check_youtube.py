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

# 1. Any sessions attributed to YouTube already?
q("Sessions with source=YouTube", """
SELECT channel, source, COUNT(*) n FROM sessions
WHERE source ILIKE '%youtube%'
GROUP BY 1,2 ORDER BY n DESC
""")

# 2. Events where referrer contains youtube
q("Events with youtube referrer", """
SELECT COUNT(*) as total_events,
       COUNT(DISTINCT session_id) as unique_sessions
FROM events
WHERE referrer ILIKE '%youtube%'
""")

# 3. Sample youtube referrers
q("Sample youtube referrer values", """
SELECT referrer, COUNT(*) n FROM events
WHERE referrer ILIKE '%youtube%'
GROUP BY referrer ORDER BY n DESC LIMIT 10
""")

# 4. Events where page_url has youtube utm
q("Events with utm_source=youtube in URL", """
SELECT COUNT(*) as events, COUNT(DISTINCT session_id) as sessions
FROM events
WHERE page_url ILIKE '%utm_source=youtube%'
   OR page_url ILIKE '%utm_source=YouTube%'
""")

# 5. Sample youtube UTM URLs
q("Sample youtube UTM URLs", """
SELECT page_url, COUNT(*) n FROM events
WHERE page_url ILIKE '%utm_source=youtube%'
   OR page_url ILIKE '%utm_source=YouTube%'
GROUP BY page_url ORDER BY n DESC LIMIT 5
""")

# 6. What do sessions look like when entry_url has youtube params?
q("Sessions where entry_url contains youtube", """
SELECT source, medium, channel, entry_url, COUNT(*) n FROM sessions
WHERE entry_url ILIKE '%youtube%'
GROUP BY 1,2,3,4 ORDER BY n DESC LIMIT 10
""")

# 7. Check for YouTube click ID (yclid) param
q("Events with yclid (YouTube click ID)", """
SELECT COUNT(*) as events FROM events
WHERE page_url ILIKE '%yclid=%'
""")

# 8. Check for YouTube-related nbt network values
q("Events with nbt containing youtube/yt", """
SELECT page_url, COUNT(*) n FROM events
WHERE page_url ILIKE '%nbt=%'
  AND (page_url ILIKE '%:yt:%' OR page_url ILIKE '%youtube%')
GROUP BY page_url ORDER BY n DESC LIMIT 5
""")

c.close()
