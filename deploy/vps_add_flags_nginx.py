import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
CONF = "/etc/nginx/sites-available/uj-pfm-qa"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

# Read current config
sftp = c.open_sftp()
with sftp.open(CONF, "r") as f:
    original = f.read().decode("utf-8")

if "location /flags/" in original:
    print("  /flags/ block already present — nothing to do")
else:
    flags_block = """
    # Flag images served from frontend dist
    location /flags/ {
        alias /var/www/pfm-uj/frontend/flags/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
"""
    # Insert before the "# ── Test / root" comment
    marker = "    # ── Test / root"
    if marker in original:
        updated = original.replace(marker, flags_block + marker, 1)
    else:
        # Fallback: insert before the last closing brace of the first server block
        updated = original.replace("    location / {", flags_block + "    location / {", 1)

    with sftp.open(CONF, "w") as f:
        f.write(updated.encode("utf-8"))
    print("  /flags/ block inserted")

sftp.close()

def run(cmd, timeout=15):
    _, out, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    return out.read().decode("utf-8", errors="replace").strip()

# Verify insertion
print(f"  grep result: {run('grep -A4 location /flags/ ' + CONF)}")
print(f"  nginx test:  {run('nginx -t 2>&1 | tail -2')}")
print(f"  reload:      {run('systemctl reload nginx && echo OK')}")
print(f"  HTTP check:  {run('curl -sI https://uj.pfm-qa.com/flags/US.png | head -2')}")

c.close()
print("\nDone.")
