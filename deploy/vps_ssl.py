import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
DOMAIN = "uj.pfm-qa.com"
EMAIL  = "denis@particleformen.com"


def connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username="root", key_filename=KEY, timeout=15)
    return c


def run(c, cmd, label="", timeout=60):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    for line in out.splitlines():
        print(f"     {line}")
    return out, code


client = connect()

print("\n=== Check / install certbot ===")
run(client, "which certbot || apt-get install -y certbot python3-certbot-nginx", "ensure certbot installed", timeout=120)

print("\n=== Request SSL certificate ===")
out, code = run(
    client,
    f"certbot --nginx -d {DOMAIN} --non-interactive --agree-tos --email {EMAIL} --redirect 2>&1",
    f"certbot --nginx -d {DOMAIN}",
    timeout=120,
)

if code != 0:
    print(f"\n[ERROR] certbot failed (exit {code}). See output above.")
    client.close()
    sys.exit(1)

print("\n=== Reload nginx ===")
run(client, "systemctl reload nginx", "reload nginx")

print("\n=== Verify HTTPS ===")
run(client, f"curl -s -o /dev/null -w '%{{http_code}}' https://{DOMAIN}/", f"curl https://{DOMAIN}/")

print("\n=== Done ===")
print(f"  Site is now: https://{DOMAIN}/")
client.close()
