import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("72.62.148.226", username="root", key_filename=r"C:\Users\denis\.ssh\id_ed25519", timeout=15)

def run(cmd, label=""):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=15, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines(): print(f"     {l}")

run(
    'cd /var/www/pfm-uj/app && docker compose exec -T postgres '
    'psql -U pfm_user -d pfm_journeys -c '
    '"SELECT id, session_id, page_url, referrer, timestamp FROM events ORDER BY id DESC LIMIT 5;"',
    "last 5 events"
)
c.close()
