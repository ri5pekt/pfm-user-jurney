import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=15):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    print(out or "  (no output)")

run("ls /var/www/pfm-uj/frontend/flags/ 2>/dev/null | head -5 || echo 'flags/ folder NOT FOUND'", "flags folder on server")
run("ls /var/www/pfm-uj/frontend/flags/ 2>/dev/null | wc -l", "flag count")
run("curl -sI http://localhost/flags/US.png 2>/dev/null | head -5 || echo 'curl failed'", "HTTP check US.png")

c.close()
