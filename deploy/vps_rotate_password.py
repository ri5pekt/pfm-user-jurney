import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
APP_DIR = "/var/www/pfm-uj/app"
PW      = "23ltybc69"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, timeout=30):
    _, out, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    print(" ", out.read().decode("utf-8", errors="replace").strip()[-200:])

run(f"sed -i 's|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD={PW}|' {APP_DIR}/.env")
run(f"grep ADMIN_PASSWORD {APP_DIR}/.env")
run(f"cd {APP_DIR} && docker compose up -d admin-api")
time.sleep(4)
run(f"curl -s -o /dev/null -w '%{{http_code}}' -X POST https://uj.pfm-qa.com/api/auth/login -H 'Content-Type: application/json' -d '{{\"email\":\"denis@particleformen.com\",\"password\":\"{PW}\"}}'")
c.close()
print("Done.")
