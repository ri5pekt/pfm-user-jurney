import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def pg(sql, label=""):
    cmd = f"docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -c \"{sql}\""
    _, out, _ = c.exec_command(cmd, timeout=30)
    r = out.read().decode("utf-8", errors="replace").strip()
    if label: print(f"  {label}: {r}")
    return r

before = pg("SELECT COUNT(*) FROM events", "events before")

# Delete duplicate events: keep the LATEST event when same session + same url + within 5 seconds.
# Uses a CTE to find IDs to delete: for each group of duplicates, keep the MAX id.
pg(r"""
DELETE FROM events
WHERE id IN (
  SELECT e.id
  FROM events e
  WHERE EXISTS (
    SELECT 1 FROM events e2
    WHERE  e2.session_id = e.session_id
      AND  REGEXP_REPLACE(e2.page_url, '\?.*$', '') = REGEXP_REPLACE(e.page_url, '\?.*$', '')
      AND  e2.id <> e.id
      AND  ABS(EXTRACT(EPOCH FROM (e2.timestamp - e.timestamp))) < 5
      AND  e2.timestamp >= e.timestamp
  )
)
""", "deleted")

after = pg("SELECT COUNT(*) FROM events", "events after")
print(f"\n  Removed {int(before) - int(after)} duplicate events")

# Recount suspect sessions
pg(r"""
SELECT COUNT(*) FROM (
  SELECT DISTINCT e1.session_id
  FROM events e1
  JOIN events e2
    ON e1.session_id = e2.session_id
   AND e1.id <> e2.id
   AND REGEXP_REPLACE(e1.page_url, '\?.*$', '') = REGEXP_REPLACE(e2.page_url, '\?.*$', '')
   AND ABS(EXTRACT(EPOCH FROM (e1.timestamp - e2.timestamp))) < 10
) t
""", "suspect sessions remaining")

c.close()
print("\nDone.")
