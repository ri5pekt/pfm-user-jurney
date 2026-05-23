"""
deploy.py — Git-based deploy to VPS.

Usage:
  python deploy/deploy.py                # full deploy (all services)
  python deploy/deploy.py frontend       # rebuild only frontend
  python deploy/deploy.py worker         # rebuild only worker
  python deploy/deploy.py admin-api      # rebuild only admin-api
  python deploy/deploy.py collector      # rebuild only collector

Workflow:
  1. SSH into VPS
  2. git pull origin master
  3. docker compose build [service]  (or all if no service specified)
  4. docker compose up -d [service]  (or all)
  5. docker image prune -f
"""

import paramiko, sys, io, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
APP_DIR = "/var/www/pfm-uj/app"

service = sys.argv[1] if len(sys.argv) > 1 else None

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=600):
    label = label or cmd[:80]
    print(f"\n  [{label}]")
    _, stdout, stderr = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for line in out.splitlines():
        print(f"    {line}")
    return out

print("=" * 55)
print(f"  Deploy: {service or 'ALL services'}")
print("=" * 55)

# 1. Pull latest code
run(f"cd {APP_DIR} && git pull origin master", "git pull", timeout=30)

# 2. Build
if service:
    run(f"cd {APP_DIR} && docker compose build {service}", f"build {service}", timeout=600)
else:
    run(f"cd {APP_DIR} && docker compose build", "build all", timeout=600)

# 3. Restart
if service:
    run(f"cd {APP_DIR} && docker compose up -d {service}", f"up {service}", timeout=60)
else:
    run(f"cd {APP_DIR} && docker compose up -d --remove-orphans", "up -d all", timeout=60)

time.sleep(3)

# 4. Cleanup
run("docker image prune -f", "prune images")

# 5. Status
print()
run(f"cd {APP_DIR} && docker compose ps", "container status")

print("\n=== Deploy complete ===")
c.close()
