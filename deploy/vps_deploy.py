import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
REPO = "https://github.com/ri5pekt/pfm-user-jurney.git"
APP_DIR = "/var/www/pfm-uj/app"

# Production .env — set real secrets here
# NOTE: never hardcode real passwords here. Set them directly on the VPS .env file.
PROD_ENV = """POSTGRES_DB=pfm_journeys
POSTGRES_USER=pfm_user
POSTGRES_PASSWORD=CHANGE_ME

REDIS_URL=redis://redis:6379
REDIS_QUEUE_KEY=events_queue

PORT_COLLECTOR=3001
ALLOWED_ORIGINS=https://particleformen.com

PORT_ADMIN=3002
JWT_SECRET=CHANGE_ME_use_a_long_random_string
ADMIN_USERNAME=admin
ADMIN_PASSWORD=CHANGE_ME

WORKER_BATCH_SIZE=100
WORKER_INTERVAL_MS=3000
"""


def connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username="root", key_filename=KEY, timeout=15)
    return c


def run(c, cmd, label="", timeout=120):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    for line in out.splitlines():
        print(f"     {line}")
    return out, code


client = connect()

# 1. Install Docker if not present
print("\n=== Check Docker ===")
out, _ = run(client, "docker --version 2>/dev/null || echo MISSING")
if "MISSING" in out:
    print("  -> Installing Docker...")
    run(client, "curl -fsSL https://get.docker.com | sh", "install Docker", timeout=300)

# 2. Clone or pull
print("\n=== Clone / pull repo ===")
out, _ = run(client, f"test -d {APP_DIR}/.git && echo EXISTS || echo MISSING")
if "MISSING" in out:
    run(client, f"mkdir -p {APP_DIR}")
    run(client, f"git clone {REPO} {APP_DIR}", "git clone", timeout=60)
else:
    run(client, f"cd {APP_DIR} && git pull origin master", "git pull")

# 3. Write .env (only if it doesn't exist — never overwrite production secrets)
print("\n=== .env ===")
out, _ = run(client, f"test -f {APP_DIR}/.env && echo EXISTS || echo MISSING")
if "MISSING" in out:
    sftp = client.open_sftp()
    with sftp.open(f"{APP_DIR}/.env", "w") as f:
        f.write(PROD_ENV)
    sftp.close()
    print("  -> .env created")
else:
    print("  -> .env already exists, skipping (preserving secrets)")

# 4. Build and start
print("\n=== docker compose build + up ===")
run(client,
    f"cd {APP_DIR} && docker compose -f docker-compose.yml build",
    "docker compose build", timeout=600)
run(client,
    f"cd {APP_DIR} && docker compose -f docker-compose.yml up -d --remove-orphans",
    "docker compose up -d", timeout=60)

# 5. Status
print("\n=== Container status ===")
run(client, f"cd {APP_DIR} && docker compose -f docker-compose.yml ps", timeout=15)

# 6. Smoke test collector
print("\n=== Smoke test ===")
run(client,
    "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3101/health",
    "collector health (127.0.0.1:3101)")

print("\n=== Done ===")
print("  https://uj.pfm-qa.com is live with the full stack.")
client.close()
