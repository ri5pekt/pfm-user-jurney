import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("72.62.148.226", username="root", key_filename=r"C:\Users\denis\.ssh\id_ed25519", timeout=15)

def run(cmd, label=""):
    _, out, _ = c.exec_command(cmd, timeout=20, get_pty=True)
    text = out.read().decode("utf-8", errors="replace").strip()
    print(f"[{label}] {text[:120]}")

# Read password from local secrets file (never commit this file)
import os
PW = open(os.path.join(os.path.dirname(__file__), ".secrets")).read().strip().split("ADMIN_PASSWORD=")[-1].splitlines()[0]

run('curl -s -o /dev/null -w "%{http_code}" https://uj.pfm-qa.com/admin/', "HTTPS /admin/ status")
run(
    f'curl -s -X POST https://uj.pfm-qa.com/api/auth/login '
    f'-H "Content-Type: application/json" '
    f'-d \'{{"email":"denis@particleformen.com","password":"{PW}"}}\'',
    "POST /api/auth/login"
)
c.close()
