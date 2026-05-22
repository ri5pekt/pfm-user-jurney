import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
APP_DIR = "/var/www/pfm-uj/app"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=180):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines()[-8:]:
        print(f"     {l}")
    return out

run(f"cd {APP_DIR} && git pull origin master", "git pull", 30)
run(f"cd {APP_DIR} && docker compose build collector", "build collector", 180)
run(f"cd {APP_DIR} && docker compose up -d collector", "restart collector", 30)
time.sleep(3)
run(f"docker logs app-collector-1 --tail 10", "collector logs")
print("\nDone — referrers will now be captured from the request body.")
c.close()
