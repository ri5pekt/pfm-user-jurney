import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
APP_DIR = "/var/www/pfm-uj/app"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=300):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines()[-6:]: print(f"     {l}")

def pg(sql):
    cmd = f'docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -c "{sql}"'
    _, out, _ = c.exec_command(cmd, timeout=15)
    return out.read().decode("utf-8", errors="replace").strip()

print("=== git pull ===")
run(f"cd {APP_DIR} && git pull origin master", "git pull", 30)

print("\n=== Rebuild worker ===")
run(f"cd {APP_DIR} && docker compose build worker", "build", 300)
run(f"cd {APP_DIR} && docker compose up -d worker", "up -d", 30)

print("\n=== Truncate sessions ===")
pg("TRUNCATE TABLE sessions;")
print("  -> sessions truncated")

print("\n=== Run backfill ===")
run(f"cd {APP_DIR} && docker compose exec -T worker node dist/backfill.js", "backfill", 120)

n = pg("SELECT COUNT(*) FROM sessions;")
print(f"\n  -> sessions rebuilt: {n}")

c.close()
print("\nDone.")
