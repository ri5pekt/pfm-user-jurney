"""
fix_and_complete_migration.py
Fixes the broken nginx config, resets VPS git state, builds + starts the
frontend container. Run once to complete the migration.
"""
import paramiko, sys, io, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY        = r"C:\Users\denis\.ssh\id_ed25519"
HOST       = "72.62.148.226"
APP_DIR    = "/var/www/pfm-uj/app"
NGINX_CONF = "/etc/nginx/sites-available/uj-pfm-qa"

# The correct, complete nginx config
NGINX_CONFIG = """\
# Host nginx config for uj.pfm-qa.com
server {
    server_name uj.pfm-qa.com;

    # ── Collector — POST /p ──────────────────────────────────────────────────
    location = /p {
        proxy_pass         http://127.0.0.1:3101;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout    10s;
    }

    # ── Admin API — /api/* ───────────────────────────────────────────────────
    location /api/ {
        proxy_pass         http://127.0.0.1:3102/;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout    300s;
        proxy_connect_timeout  75s;
    }

    # ── Frontend — /admin/ (frontend Docker container on port 3103) ──────────
    location /admin/ {
        proxy_pass         http://127.0.0.1:3103/;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    # ── Root ─────────────────────────────────────────────────────────────────
    location / {
        root  /var/www/pfm-uj;
        index index.html;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/uj.pfm-qa.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/uj.pfm-qa.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    if ($host = uj.pfm-qa.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name uj.pfm-qa.com;
    return 404; # managed by Certbot
}
"""

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

# ── 1. Write correct nginx config ────────────────────────────────────────────
print("=== 1. Write correct nginx config ===")
sftp = c.open_sftp()
with sftp.open(NGINX_CONF, "w") as f:
    f.write(NGINX_CONFIG)
sftp.close()
print("  Written.")

run("nginx -t",               "nginx -t")
run("systemctl reload nginx", "reload nginx")

# ── 2. Reset VPS git to match origin (SCP'd files are already in git) ────────
print("\n=== 2. Reset VPS git state ===")
run(f"cd {APP_DIR} && git fetch origin master",          "git fetch")
run(f"cd {APP_DIR} && git reset --hard origin/master",   "git reset --hard")

# ── 3. Build + start frontend container ──────────────────────────────────────
print("\n=== 3. Build frontend container ===")
run(f"cd {APP_DIR} && docker compose build frontend", "docker compose build frontend", timeout=600)

print("\n=== 4. Start frontend container ===")
run(f"cd {APP_DIR} && docker compose up -d frontend", "docker compose up -d frontend")
time.sleep(4)

# ── 5. Smoke test ────────────────────────────────────────────────────────────
print("\n=== 5. Smoke test ===")
run("curl -sI https://uj.pfm-qa.com/admin/ | head -6", "curl /admin/")
run(f"cd {APP_DIR} && docker compose ps",               "container status")

print("\n=== Migration complete. Use: python deploy/deploy.py ===")
c.close()
