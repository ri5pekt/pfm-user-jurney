import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=30):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines()[-6:]: print(f"     {l}")

print("=== Fix frontend permissions ===")
run("chmod -R 755 /var/www/pfm-uj/frontend", "chmod")
run("nginx -t && systemctl reload nginx", "nginx reload")
run("docker ps --format '{{.Names}}  {{.Status}}'", "container status")
c.close()
print("\nDone.")
