import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
CONF = "/etc/nginx/sites-available/uj-pfm-qa"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=15):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines(): print(f"     {l}")

# Insert a /flags/ location block before the closing server brace
# Use Python to write the sed command safely
insert = (
    "    # Flag images served from frontend dist\\n"
    "    location /flags/ {\\n"
    "        alias /var/www/pfm-uj/frontend/flags/;\\n"
    "        expires 30d;\\n"
    "        add_header Cache-Control \\\"public, immutable\\\";\\n"
    "    }\\n"
)

# Only add if not already there
_, chk, _ = c.exec_command(f"grep -c 'location /flags/' {CONF} 2>/dev/null || echo 0", timeout=10)
count = chk.read().decode().strip()

if count != "0":
    print("  /flags/ block already exists — skipping insert")
else:
    # Insert before the first 'location / {'
    cmd = f"sed -i 's|# ── Test / root|{insert}\\n    # ── Test / root|' {CONF}"
    _, _, err = c.exec_command(cmd, timeout=10)
    err.read()
    print("  inserted /flags/ location block")

run(f"nginx -t && systemctl reload nginx", "nginx test + reload")
run(f"curl -sI https://uj.pfm-qa.com/flags/US.png | head -3", "HTTP check after fix")

c.close()
print("\nDone.")
