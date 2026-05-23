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
    for l in out.splitlines()[-10:]: print(f"     {l}")

def pg(sql):
    _, out, _ = c.exec_command(
        f"docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -c \"{sql}\"", timeout=15)
    return out.read().decode("utf-8", errors="replace").strip()

print("=== Run migrate_geo.sql ===")
run(
    f"cat {APP_DIR}/scripts/migrate_geo.sql | docker exec -i app-postgres-1 psql -U pfm_user -d pfm_journeys",
    "migrate_geo",
    60,
)

print("\n=== Verify columns ===")
cols = pg("SELECT column_name FROM information_schema.columns WHERE table_name='sessions' AND column_name IN ('country','city','state_name','ip') ORDER BY column_name")
print(f"     sessions geo columns: {cols.replace(chr(10), ', ')}")

cache = pg("SELECT to_regclass('public.ip_geolocation_cache')")
print(f"     ip_geolocation_cache table: {cache}")

print("\n=== Restart worker (pick up new schema) ===")
run(f"cd {APP_DIR} && docker compose restart worker", "restart worker", 30)

c.close()
print("\nDone.")
