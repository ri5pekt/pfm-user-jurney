import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
APP_DIR = "/var/www/pfm-uj/app"
DIST    = r"C:\Users\denis\Desktop\docker-projects\pfm-user-jurney\frontend\dist"
REMOTE_FRONTEND = "/var/www/pfm-uj/frontend"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=300):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines()[-6:]:
        print(f"     {l}")
    return out

import os
def upload_dir(sftp, local_dir, remote_dir):
    try: sftp.mkdir(remote_dir)
    except OSError: pass
    for item in os.listdir(local_dir):
        lp = os.path.join(local_dir, item)
        rp = remote_dir + "/" + item
        if os.path.isdir(lp): upload_dir(sftp, lp, rp)
        else: sftp.put(lp, rp)

# 1. git pull
print("=== git pull ===")
run(f"cd {APP_DIR} && git pull origin master", "git pull", 30)

# 2. Run sessions migration
print("\n=== Run sessions migration ===")
run(
    f"docker exec app-postgres-1 psql -U ${{POSTGRES_USER:-tracker}} -d ${{POSTGRES_DB:-tracker}} "
    f"-f /dev/stdin < {APP_DIR}/scripts/migrate_sessions.sql 2>&1 || "
    f"docker exec -i app-postgres-1 psql -U tracker -d tracker < {APP_DIR}/scripts/migrate_sessions.sql",
    "migrate sessions table"
)
# More reliable approach — copy file into container and run
run(
    f"docker cp {APP_DIR}/scripts/migrate_sessions.sql app-postgres-1:/tmp/migrate_sessions.sql && "
    f"docker exec app-postgres-1 psql -U tracker -d tracker -f /tmp/migrate_sessions.sql",
    "migrate (copy+exec)"
)

# 3. Rebuild worker + admin-api
print("\n=== Rebuild worker ===")
run(f"cd {APP_DIR} && docker compose build worker", "build worker", 300)
run(f"cd {APP_DIR} && docker compose up -d worker", "restart worker", 30)

print("\n=== Rebuild admin-api ===")
run(f"cd {APP_DIR} && docker compose build admin-api", "build admin-api", 300)
run(f"cd {APP_DIR} && docker compose up -d admin-api", "restart admin-api", 30)

# 4. Upload frontend
print("\n=== Upload frontend ===")
run(f"rm -rf {REMOTE_FRONTEND} && mkdir -p {REMOTE_FRONTEND}")
sftp = c.open_sftp()
print(f"  -> uploading dist -> {REMOTE_FRONTEND}")
upload_dir(sftp, DIST, REMOTE_FRONTEND)
sftp.close()
run(f"chmod -R 755 {REMOTE_FRONTEND}", "chmod")

time.sleep(4)

# 5. Verify
print("\n=== Verify ===")
run('curl -s http://127.0.0.1:3102/health', "admin-api health")
run('curl -s http://127.0.0.1:3102/sessions/stats | head -c 120', "sessions/stats")
run(f"docker logs app-worker-1 --tail 5", "worker logs")

print("\nDone.")
c.close()
