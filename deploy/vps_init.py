import paramiko
import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"

ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_PAGE    = os.path.join(ROOT, "scripts", "test-page", "index.html")
NGINX_CONF   = os.path.join(ROOT, "nginx", "vps-site.conf")
DEPLOY_DIR   = "/var/www/pfm-uj"
SITE_NAME    = "uj-pfm-qa"
NGINX_AVAIL  = f"/etc/nginx/sites-available/{SITE_NAME}"
NGINX_ENABLED = f"/etc/nginx/sites-enabled/{SITE_NAME}"


def connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username="root", key_filename=KEY, timeout=15)
    return c


def run(c, cmd, label=""):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=30, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    for line in out.splitlines():
        print(f"     {line}")
    return out, code


def upload(c, local, remote):
    print(f"  -> upload {os.path.basename(local)} -> {remote}")
    sftp = c.open_sftp()
    sftp.put(local, remote)
    sftp.close()


client = connect()
print("\n=== Safety check ===")
run(client, "ss -tlnp | grep -E ':80|:443|:310' || echo none", "ports 80/443/310x")
run(client, "ls /etc/nginx/sites-enabled/", "existing nginx sites")
run(client, "docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null || echo no-docker", "running containers")

print("\n=== Create deploy dir ===")
run(client, f"mkdir -p {DEPLOY_DIR} && chmod 755 {DEPLOY_DIR}", f"mkdir {DEPLOY_DIR}")

print("\n=== Upload test page ===")
upload(client, TEST_PAGE, f"{DEPLOY_DIR}/index.html")
run(client, f"chmod 644 {DEPLOY_DIR}/index.html")

print("\n=== Install nginx site config ===")
upload(client, NGINX_CONF, NGINX_AVAIL)
run(client, f"chmod 644 {NGINX_AVAIL}")
run(client, f"ln -sf {NGINX_AVAIL} {NGINX_ENABLED}", "enable site")

print("\n=== nginx -t ===")
out, code = run(client, "nginx -t 2>&1", "nginx -t")
if code != 0 or "failed" in out.lower():
    print("\n[ABORT] nginx config test failed. Nothing reloaded. Existing sites unchanged.")
    client.close()
    sys.exit(1)

run(client, "systemctl reload nginx", "reload nginx")

print("\n=== Verify ===")
run(client, "curl -s -o /dev/null -w '%{http_code}' http://uj.pfm-qa.com/", "curl http://uj.pfm-qa.com/")
run(client, f"curl -s -o /dev/null -w '%{{http_code}}' http://{HOST}/", f"curl http://{HOST}/")

print("\n=== Done ===")
print("  Open: http://uj.pfm-qa.com/")
client.close()
