"""
migrate_to_docker_frontend.py  (run once)

Switches the frontend from "build locally + SCP dist/" to a Dockerized
service that builds from source on the VPS after every git pull.

Steps:
  1. git pull  (gets docker-compose.yml with frontend service + frontend/Dockerfile)
  2. docker compose build frontend
  3. docker compose up -d frontend
  4. Patch host nginx: /admin/ -> proxy_pass 127.0.0.1:3103  (was: alias)
  5. nginx -t && systemctl reload nginx
  6. Smoke test
"""
import paramiko, sys, io, re, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY        = r"C:\Users\denis\.ssh\id_ed25519"
HOST       = "72.62.148.226"
APP_DIR    = "/var/www/pfm-uj/app"
NGINX_CONF = "/etc/nginx/sites-available/uj-pfm-qa"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=600):
    label = label or cmd[:80]
    print(f"\n  [{label}]")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for line in out.splitlines():
        print(f"    {line}")
    return out

# ── 1. git pull ──────────────────────────────────────────────────────────────
print("=== 1. git pull ===")
run(f"cd {APP_DIR} && git pull origin master", "git pull", timeout=30)

# ── 2. Build frontend container ──────────────────────────────────────────────
print("\n=== 2. docker compose build frontend ===")
run(f"cd {APP_DIR} && docker compose build frontend", "build frontend", timeout=600)

# ── 3. Start frontend container ──────────────────────────────────────────────
print("\n=== 3. docker compose up -d frontend ===")
run(f"cd {APP_DIR} && docker compose up -d frontend", "up frontend", timeout=60)
time.sleep(3)

# ── 4. Patch nginx ───────────────────────────────────────────────────────────
print("\n=== 4. Patch nginx /admin/ location ===")

sftp = c.open_sftp()
with sftp.open(NGINX_CONF, "r") as f:
    config = f.read().decode("utf-8")

NEW_BLOCK = """\
    # ── Frontend — /admin/ (proxied to frontend Docker container) ────────────
    location /admin/ {
        proxy_pass         http://127.0.0.1:3103/;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }"""

# Match the existing /admin/ block (comment line + location block, possibly nested)
pattern = re.compile(
    r"[ \t]*#[^\n]*[Ff]rontend[^\n]*(static[^\n]*)?\n"   # comment
    r"[ \t]*location /admin/ \{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",
    re.DOTALL,
)

m = pattern.search(config)
if m:
    print(f"  Found old block, replacing...")
    config = config[:m.start()] + NEW_BLOCK + config[m.end():]
    with sftp.open(NGINX_CONF, "w") as f:
        f.write(config)
    print("  Wrote updated nginx config.")
else:
    print("  WARNING: could not find /admin/ block. Check nginx config manually.")

sftp.close()

# ── 5. Test + reload nginx ───────────────────────────────────────────────────
print("\n=== 5. nginx -t && reload ===")
run("nginx -t",                 "nginx -t")
run("systemctl reload nginx",   "reload nginx")

# ── 6. Smoke test ────────────────────────────────────────────────────────────
print("\n=== 6. Smoke test ===")
run("curl -sI https://uj.pfm-qa.com/admin/ | head -5",  "curl /admin/")
run(f"cd {APP_DIR} && docker compose ps", "container status")

print("\n=== Done. Future deploys: python deploy/deploy.py ===")
c.close()
