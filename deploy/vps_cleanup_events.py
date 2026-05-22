import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def pg(sql, label=""):
    cmd = f"docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -c \"{sql}\""
    _, out, _ = c.exec_command(cmd, timeout=15)
    r = out.read().decode("utf-8", errors="replace").strip()
    if label: print(f"  {label}: {r}")
    return r

# Show what we're about to delete
print("Events matching /producto/ or regional prefixes:")
pg(r"""
  SELECT page_url FROM events
  WHERE page_url ~ '/producto/'
     OR page_url ~ '://www\.particleformen\.com/(es|fr|de|ca|gb|au|it)(/|$|\?)'
  LIMIT 20
""", "to delete")

# Count
before = pg("SELECT COUNT(*) FROM events", "total events before")

# Delete leaked regional + translated events
pg(r"""
  DELETE FROM events
  WHERE page_url ~ '/producto/'
     OR page_url ~ '://www\.particleformen\.com/(es|fr|de|ca|gb|au|it)(/|$|\?)'
""", "deleted")

after = pg("SELECT COUNT(*) FROM events", "total events after")
print(f"\n  Removed {int(before) - int(after)} events")

c.close()
