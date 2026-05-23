import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
APP_DIR = "/var/www/pfm-uj/app"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=60):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines()[-6:]: print(f"     {l}")

def pg(sql):
    _, out, _ = c.exec_command(
        f"docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -c \"{sql}\"", timeout=15)
    return out.read().decode("utf-8", errors="replace").strip()

print("=== Run migrate_metadata.sql ===")
run(f"cat {APP_DIR}/scripts/migrate_metadata.sql | docker exec -i app-postgres-1 psql -U pfm_user -d pfm_journeys", "migrate")

print("\n=== Verify ===")
col = pg("SELECT column_name FROM information_schema.columns WHERE table_name='events' AND column_name='metadata'")
print(f"     metadata column: {'OK' if col else 'MISSING'}")

print("\n=== Rebuild + restart worker ===")
run(f"cd {APP_DIR} && docker compose build worker", "build worker", 180)
run(f"cd {APP_DIR} && docker compose up -d worker", "up -d worker", 30)

print("\n=== Rebuild admin-api ===")
run(f"cd {APP_DIR} && docker compose build admin-api", "build admin-api", 180)
run(f"cd {APP_DIR} && docker compose up -d admin-api", "up -d admin-api", 30)

c.close()
print("\nDone.")
