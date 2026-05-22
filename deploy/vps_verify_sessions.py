import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("72.62.148.226", username="root", key_filename=r"C:\Users\denis\.ssh\id_ed25519", timeout=15)

def run(cmd, label=""):
    _, out, _ = c.exec_command(cmd, timeout=20, get_pty=True)
    text = out.read().decode("utf-8", errors="replace").strip()
    print(f"[{label}]\n{text[:400]}\n")

run("docker logs app-worker-1 --tail 10", "worker logs")
run(
    "curl -s http://127.0.0.1:3102/sessions/stats "
    "-H 'Authorization: Bearer $(curl -s -X POST http://127.0.0.1:3102/auth/login "
    "-H \"Content-Type: application/json\" "
    "-d \\'{ \"email\": \"denis@particleformen.com\", \"password\": \"REDACTED\" }\\' "
    "| grep -o '\"token\":\"[^\"]*\"' | cut -d'\"' -f4)'",
    "sessions/stats"
)
c.close()
