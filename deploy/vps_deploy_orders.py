"""
Deploy order_id / revenue_usd session enrichment.

Steps:
  1. Pull latest code on VPS
  2. Apply migrate_session_orders.sql
  3. Set FX_API_KEY in .env (if provided)
  4. Rebuild + restart worker and admin-api
  5. Rebuild + upload frontend
"""

import io
import os
import subprocess
import sys
import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

VPS_HOST   = "72.62.148.226"
VPS_USER   = "root"
SSH_KEY    = r"C:\Users\denis\.ssh\id_ed25519"
APP_DIR    = "/var/www/pfm-uj/app"
FRONTEND   = "c:\\Users\\denis\\Desktop\\docker-projects\\pfm-user-jurney\\frontend"
REMOTE_FE  = "/var/www/pfm-uj/frontend"
PG_USER    = "pfm_user"
PG_DB      = "pfm_journeys"

# ── Read FX_API_KEY from local .env (or set it manually here) ──────────────────
LOCAL_ENV  = os.path.join(os.path.dirname(__file__), "..", ".env")
FX_API_KEY = ""
if os.path.exists(LOCAL_ENV):
    for line in open(LOCAL_ENV):
        if line.startswith("FX_API_KEY="):
            FX_API_KEY = line.split("=", 1)[1].strip()

def ssh_exec(client: paramiko.SSHClient, cmd: str) -> str:
    print(f"  $ {cmd}")
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(out)
    if err: print("[stderr]", err)
    return out

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS_HOST, username=VPS_USER, key_filename=SSH_KEY, timeout=15)

print("=== 1. Pull latest code ===")
ssh_exec(client, f"cd {APP_DIR} && git pull origin master")

print("=== 2. Apply migration ===")
ssh_exec(client,
    f"cat {APP_DIR}/scripts/migrate_session_orders.sql | "
    f"docker exec -i app-postgres-1 psql -U {PG_USER} -d {PG_DB}")

if FX_API_KEY:
    print("=== 3. Set FX_API_KEY in .env ===")
    ssh_exec(client, f"sed -i '/^FX_API_KEY=/d' {APP_DIR}/.env")
    ssh_exec(client, f"echo 'FX_API_KEY={FX_API_KEY}' >> {APP_DIR}/.env")
else:
    print("=== 3. FX_API_KEY not found locally — skipping (set it manually on VPS) ===")

print("=== 4. Rebuild + restart worker and admin-api ===")
ssh_exec(client, f"cd {APP_DIR} && docker compose build worker admin-api")
ssh_exec(client, f"cd {APP_DIR} && docker compose up -d --force-recreate worker admin-api")

print("=== 5. Build frontend locally ===")
result = subprocess.run(
    ["cmd", "/c", "npm run build"],
    cwd=FRONTEND, capture_output=True, text=True
)
print(result.stdout[-3000:] if result.stdout else "")
if result.returncode != 0:
    print("FRONTEND BUILD FAILED:", result.stderr[-2000:])
    client.close()
    raise SystemExit(1)

print("=== 5b. Upload frontend ===")
sftp = client.open_sftp()
dist = os.path.join(FRONTEND, "dist")
for root, dirs, files in os.walk(dist):
    rel = os.path.relpath(root, dist)
    remote_dir = REMOTE_FE if rel == "." else f"{REMOTE_FE}/{rel.replace(os.sep, '/')}"
    try: sftp.mkdir(remote_dir)
    except: pass
    for f in files:
        local_path  = os.path.join(root, f)
        remote_path = f"{remote_dir}/{f}"
        sftp.put(local_path, remote_path)
sftp.close()

print("=== 6. Verify ===")
ssh_exec(client, f"cd {APP_DIR} && docker compose logs worker --tail=10")

client.close()
print("\nDone. FX_API_KEY note: if not set, revenue_usd will be stored as NULL.")
print("Add it to .env on VPS: echo 'FX_API_KEY=your_key' >> /root/pfm-user-jurney/.env")
print("Then restart worker: docker compose up -d --force-recreate worker")
