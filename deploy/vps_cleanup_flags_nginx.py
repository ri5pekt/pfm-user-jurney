import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
CONF = "/etc/nginx/sites-available/uj-pfm-qa"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

sftp = c.open_sftp()
with sftp.open(CONF, "r") as f:
    config = f.read().decode("utf-8")

# Remove the /flags/ block we added earlier
import re
cleaned = re.sub(
    r"\n\s*# Flag images served from frontend dist\n\s*location /flags/ \{[^}]+\}\n",
    "\n",
    config,
)

if cleaned == config:
    print("  /flags/ block not found — nothing to remove")
else:
    with sftp.open(CONF, "w") as f:
        f.write(cleaned.encode("utf-8"))
    print("  /flags/ block removed")

sftp.close()

def run(cmd, timeout=15):
    _, out, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    return out.read().decode("utf-8", errors="replace").strip()

print(f"  nginx test: {run('nginx -t 2>&1 | tail -2')}")
print(f"  reload:     {run('systemctl reload nginx && echo OK')}")
print(f"  chmod:      {run('chmod -R 755 /var/www/pfm-uj/frontend && echo OK')}")

c.close()
print("\nDone.")
