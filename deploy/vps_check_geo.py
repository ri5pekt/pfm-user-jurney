import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=30):
    print(f"\n=== {label or cmd[:80]} ===")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    print(out or "(no output)")

def pg(sql):
    _, out, _ = c.exec_command(
        f'docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -c "{sql}"', timeout=15)
    return out.read().decode("utf-8", errors="replace").strip()

# Worker logs
run("docker logs app-worker-1 --tail 40 2>&1", "worker logs (last 40 lines)")

# IP_API_KEY present in worker env?
run("docker exec app-worker-1 sh -c 'echo IP_API_KEY=${IP_API_KEY}'", "IP_API_KEY in worker container")

# Any rows in geo cache?
print(f"\n=== ip_geolocation_cache row count ===")
print(pg("SELECT COUNT(*) FROM ip_geolocation_cache"))

# Recent sessions — do any have country set?
print(f"\n=== sessions with country (last 5) ===")
print(pg("SELECT session_id, country, city, ip FROM sessions WHERE country IS NOT NULL ORDER BY first_seen DESC LIMIT 5"))

# Recent sessions without country
print(f"\n=== recent sessions missing country (last 5) ===")
print(pg("SELECT session_id, ip, first_seen FROM sessions WHERE country IS NULL ORDER BY first_seen DESC LIMIT 5"))

c.close()
