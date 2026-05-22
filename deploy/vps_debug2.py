import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("72.62.148.226", username="root", key_filename=r"C:\Users\denis\.ssh\id_ed25519", timeout=15)

def pg(sql):
    cmd = f"docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -c \"{sql}\""
    _, out, _ = c.exec_command(cmd, timeout=15)
    return out.read().decode("utf-8", errors="replace").strip()

# Check events table for any regional paths
print("=== Events with /gb/ /es/ etc in page_url ===")
rows = pg("SELECT COUNT(*), SUBSTRING(page_url FROM 'particleformen\.com(/[^/?]+)') as path_start FROM events WHERE page_url ~ 'particleformen\.com/(gb|es|fr|de|ca|au|it)[/?]' GROUP BY path_start")
for r in rows.splitlines(): print(r)

print("\n=== Events with /gb without slash (edge case) ===")
rows = pg("SELECT page_url FROM events WHERE page_url ~ 'particleformen\.com/(gb|es|fr|de|ca|au|it)$' LIMIT 10")
for r in rows.splitlines(): print(r if r else "(none)")

print("\n=== Current sessions table size ===")
print(pg("SELECT COUNT(*) FROM sessions"))

print("\n=== Current sessions - show ones that look like regional ===")
rows = pg("SELECT source, channel, entry_url FROM sessions WHERE entry_url ~ '/(gb|es|fr|de|ca|au|it)[/?]|/(gb|es|fr|de|ca|au|it)$' LIMIT 10")
for r in rows.splitlines(): print(r if r else "(none found)")

print("\n=== Sessions with faq/support ===")
rows = pg("SELECT source, entry_url FROM sessions WHERE entry_url ILIKE '%faq%' OR entry_url ILIKE '%support%' LIMIT 5")
for r in rows.splitlines(): print(r if r else "(none found)")

c.close()
