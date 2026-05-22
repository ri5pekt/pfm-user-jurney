import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def pg(sql):
    cmd = f"docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -c \"{sql}\""
    _, out, _ = c.exec_command(cmd, timeout=15)
    print(out.read().decode("utf-8", errors="replace"))

pg("SELECT TO_CHAR(timestamp,'HH24:MI:SS.MS') AS time, user_agent, page_url FROM events WHERE session_id = '189ce78f-1ebc-4611-abb8-7aa3e1619270' ORDER BY timestamp ASC;")

# Also check how many sessions have 2+ events on same path within 5s
pg(r"""
SELECT COUNT(*) AS suspect_sessions FROM (
  SELECT DISTINCT e1.session_id
  FROM events e1
  JOIN events e2
    ON e1.session_id = e2.session_id
   AND e1.id <> e2.id
   AND REGEXP_REPLACE(e1.page_url, '\?.*$', '') = REGEXP_REPLACE(e2.page_url, '\?.*$', '')
   AND ABS(EXTRACT(EPOCH FROM (e1.timestamp - e2.timestamp))) < 10
) t;
""")

c.close()
