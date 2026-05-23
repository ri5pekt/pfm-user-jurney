import paramiko, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
OUT  = r"C:\Users\denis\Desktop\docker-projects\pfm-user-jurney\deploy\analysis"
os.makedirs(OUT, exist_ok=True)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def q(sql, fname):
    cmd = f"docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -F $'\\t' -c \"{sql}\""
    _, out, _ = c.exec_command(cmd, timeout=30)
    data = out.read().decode("utf-8", errors="replace")
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        f.write(data)
    rows = len([l for l in data.strip().splitlines() if l])
    print(f"  {fname}: {rows} rows")

print("=== Pulling data from VPS ===")

q("""SELECT channel, source, medium, COUNT(*) n
   FROM sessions GROUP BY 1,2,3 ORDER BY n DESC""",
  "channel_source.tsv")

q("""SELECT REGEXP_REPLACE(entry_url,'^https://[^/]+','') entry,
          channel, source, COUNT(*) n
   FROM sessions GROUP BY 1,2,3 ORDER BY n DESC LIMIT 60""",
  "entry_pages.tsv")

q("""SELECT TO_CHAR(first_seen,'YYYY-MM-DD HH24:MI:SS') ts,
          session_id, channel, source, page_count,
          REGEXP_REPLACE(entry_url,'^https://[^/]+','') entry,
          referrer
   FROM sessions ORDER BY first_seen DESC LIMIT 100""",
  "sessions_latest.tsv")

q("""SELECT TO_CHAR(timestamp,'YYYY-MM-DD HH24:MI:SS') ts,
          REGEXP_REPLACE(page_url,'^https://[^/]+','') url,
          REGEXP_REPLACE(referrer,'^https://[^/]+','') ref
   FROM events ORDER BY timestamp DESC LIMIT 200""",
  "events_latest.tsv")

q("""SELECT channel, source, medium, placement,
          REGEXP_REPLACE(entry_url,'^https://[^/]+','') entry,
          referrer, session_id
   FROM sessions
   WHERE channel = 'direct' OR channel IS NULL OR channel = ''
   ORDER BY first_seen DESC LIMIT 60""",
  "direct_sessions.tsv")

q("""SELECT utm_source, utm_medium, utm_campaign, channel, source, COUNT(*) n
   FROM sessions WHERE utm_source IS NOT NULL AND utm_source != ''
   GROUP BY 1,2,3,4,5 ORDER BY n DESC LIMIT 40""",
  "utm_breakdown.tsv")

q("""SELECT REGEXP_REPLACE(entry_url,'^https://[^/]+','') entry,
          referrer, channel, source, session_id
   FROM sessions
   WHERE channel NOT IN ('direct','email','sms','paid_search','paid_social',
                         'paid_shopping','paid_other','organic_search',
                         'organic_social','organic_shopping','referral')
      OR channel IS NULL
   ORDER BY first_seen DESC LIMIT 40""",
  "unknown_channel.tsv")

c.close()
print("Done.")
