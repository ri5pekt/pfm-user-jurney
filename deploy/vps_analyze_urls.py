import paramiko, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("72.62.148.226", username="root", key_filename=r"C:\Users\denis\.ssh\id_ed25519", timeout=15)

def pg(sql):
    cmd = f'docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -c "{sql}"'
    _, out, _ = c.exec_command(cmd, timeout=20)
    return out.read().decode("utf-8", errors="replace").strip()

print("=== Sample entry_urls from sessions ===")
rows = pg(r"SELECT source, channel, entry_url FROM sessions ORDER BY first_seen DESC LIMIT 40")
for r in rows.splitlines():
    print(r)

print("\n=== Distinct referrers in events (last 200 events) ===")
rows = pg("SELECT DISTINCT referrer FROM events WHERE referrer <> '' ORDER BY referrer LIMIT 30")
for r in rows.splitlines():
    print(r)

print("\n=== Sessions with source='' or channel='' (unmatched) ===")
rows = pg("SELECT entry_url, referrer FROM sessions WHERE source='' OR channel='' LIMIT 20")
for r in rows.splitlines():
    print(r)

print("\n=== Sessions by source+channel breakdown ===")
rows = pg("SELECT source, channel, COUNT(*) AS n FROM sessions GROUP BY source, channel ORDER BY n DESC")
for r in rows.splitlines():
    print(r)

c.close()
