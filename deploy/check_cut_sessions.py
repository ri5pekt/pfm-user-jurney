import paramiko, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def pg(sql):
    _, out, err = c.exec_command(
        f"docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -c \"{sql}\"")
    print(out.read().decode("utf-8", errors="replace"))
    e = err.read().decode("utf-8", errors="replace")
    if e.strip(): print("[err]", e)

print("=== Events for the two sessions ===")
pg("""
SELECT s.session_id, s.page_count, s.source, s.referrer,
       e.page_url, e.event_type, e.timestamp::time
FROM   sessions s
JOIN   events e ON s.session_id = e.session_id
WHERE  s.session_id IN (
    '2206be0a-a562-4532-b8bf-d7156544c445',
    'b8c94610-8faf-4f4e-ab9a-84b0ec9ded9d'
)
ORDER BY e.timestamp
""")

print("=== Sessions with 1 page and thank-you entry ===")
pg("""
SELECT session_id, page_count, source, referrer, entry_url, first_seen
FROM   sessions
WHERE  page_count = 1
  AND  entry_url LIKE '%thank-you-order%'
ORDER  BY first_seen DESC
LIMIT  10
""")

c.close()
