import paramiko, sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("72.62.148.226", username="root", key_filename=r"C:\Users\denis\.ssh\id_ed25519", timeout=15)

def run(cmd):
    _, out, _ = c.exec_command(cmd, timeout=20, get_pty=True)
    return out.read().decode("utf-8", errors="replace").strip()

# Read password from local secrets file (never commit this file)
PW = open(os.path.join(os.path.dirname(__file__), ".secrets")).read().strip().split("ADMIN_PASSWORD=")[-1].splitlines()[0]

# Get token
login = run(
    f'curl -s -X POST http://127.0.0.1:3102/auth/login '
    f'-H "Content-Type: application/json" '
    f'-d \'{{"email":"denis@particleformen.com","password":"{PW}"}}\''
)
token = json.loads(login)["token"]

stats = run(f'curl -s http://127.0.0.1:3102/sessions/stats -H "Authorization: Bearer {token}"')
print("sessions/stats:", stats[:600])

sessions = run(f'curl -s "http://127.0.0.1:3102/sessions?limit=3" -H "Authorization: Bearer {token}"')
print("\nsessions sample:", sessions[:600])
c.close()
