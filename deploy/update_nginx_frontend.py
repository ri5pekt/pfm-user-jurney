"""
update_nginx_frontend.py
Switch the /admin/ nginx location from static alias to proxy_pass → frontend container.
Run once, then use deploy.py for all future deploys.
"""

import paramiko, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY    = r"C:\Users\denis\.ssh\id_ed25519"
HOST   = "72.62.148.226"
NGINX_CONF = "/etc/nginx/sites-available/uj-pfm-qa"

NEW_ADMIN_BLOCK = """
    # ── Frontend — /admin/ (proxied to frontend Docker container) ─────────────
    location /admin/ {
        proxy_pass         http://127.0.0.1:3103/;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
"""

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=30):
    label = label or cmd[:80]
    print(f"  [{label}]")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for line in out.splitlines():
        print(f"    {line}")
    return out

# 1. Read current config
print("=== Reading current nginx config ===")
sftp = c.open_sftp()
with sftp.open(NGINX_CONF, "r") as f:
    current = f.read().decode("utf-8")

# 2. Replace the old static /admin/ block with proxy_pass
import re

old_block_pattern = re.compile(
    r"# ── Frontend.*?location /admin/ \{.*?\}",
    re.DOTALL
)

# Find the existing /admin/ location block (everything until the next top-level location or })
# We'll do a targeted replacement
old_pattern = re.compile(
    r"#[^\n]*[Ff]rontend[^\n]*\n\s*location /admin/ \{[^}]+(?:\{[^}]*\}[^}]*)*\}",
    re.DOTALL
)

match = old_pattern.search(current)
if match:
    print(f"\nFound old block:\n{match.group()}\n")
    new_config = current[:match.start()] + NEW_ADMIN_BLOCK + current[match.end():]
else:
    print("Could not find old /admin/ block — manual edit needed")
    sftp.close()
    c.close()
    sys.exit(1)

# 3. Write new config
with sftp.open(NGINX_CONF, "w") as f:
    f.write(new_config)
sftp.close()
print("=== Wrote new nginx config ===")

# 4. Test + reload
run("nginx -t", "nginx -t")
run("systemctl reload nginx", "reload nginx")

print("\n=== Done. /admin/ now proxies to frontend container on port 3103 ===")
c.close()
