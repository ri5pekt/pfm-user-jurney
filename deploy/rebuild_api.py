import paramiko, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
APP_DIR = "/var/www/pfm-uj/app"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd):
    print(f"$ {cmd[:80]}")
    _, o, e = c.exec_command(cmd, timeout=300)
    out = o.read().decode("utf-8", errors="replace").strip()
    err = e.read().decode("utf-8", errors="replace").strip()
    if out: print(out[-2000:])
    if err: print("[err]", err[-500:])

run(f"cd {APP_DIR} && git pull origin master")
run(f"cd {APP_DIR} && docker compose build admin-api")
run(f"cd {APP_DIR} && docker compose up -d --force-recreate admin-api")
print("=== Done ===")
c.close()
