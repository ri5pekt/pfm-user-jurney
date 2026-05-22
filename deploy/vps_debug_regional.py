import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("72.62.148.226", username="root", key_filename=r"C:\Users\denis\.ssh\id_ed25519", timeout=15)

def pg(sql):
    cmd = f"docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -c \"{sql}\""
    _, out, _ = c.exec_command(cmd, timeout=15)
    return out.read().decode("utf-8", errors="replace").strip()

# Find sessions with /gb in entry_url or page_url
print("=== Sessions with regional paths that slipped through ===")
rows = pg(r"SELECT session_id, channel, source, entry_url FROM sessions WHERE entry_url ~ '/[a-z]{2}(/|$)' AND entry_url ~ 'particleformen' LIMIT 20")
for r in rows.splitlines(): print(r)

# Find the faq session
print("\n=== Sessions with faq or support entry ===")
rows = pg("SELECT session_id, source, channel, entry_url, referrer FROM sessions WHERE entry_url LIKE '%faq%' OR entry_url LIKE '%support%' LIMIT 10")
for r in rows.splitlines(): print(r)

# See what regional paths are actually making it into events
print("\n=== Events with regional paths ===")
rows = pg(r"SELECT page_url FROM events WHERE page_url ~ 'particleformen\.com/(gb|es|fr|de|ca|au|it)/' LIMIT 10")
for r in rows.splitlines(): print(r)

# Show all distinct entry_url path prefixes that look regional
print("\n=== All session entry paths that look regional ===")
rows = pg("SELECT entry_url FROM sessions WHERE entry_url ~ '/[a-z]{2}[/?#]' OR entry_url ~ '/[a-z]{2}$' LIMIT 20")
for r in rows.splitlines(): print(r)

c.close()
