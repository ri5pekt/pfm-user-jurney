import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("72.62.148.226", username="root", key_filename=r"C:\Users\denis\.ssh\id_ed25519", timeout=15)

def run(cmd, label="", timeout=120):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines(): print(f"     {l}")
    return out

run("cd /var/www/pfm-uj/app && git pull origin master", "git pull", timeout=30)
run("cd /var/www/pfm-uj/app && docker compose build collector", "build", timeout=300)
run("cd /var/www/pfm-uj/app && docker compose up -d collector", "up -d", timeout=30)
time.sleep(3)

print("\n=== OPTIONS preflight ===")
run(
    'curl -si -X OPTIONS https://uj.pfm-qa.com/p '
    '-H "Origin: https://www.particleformen.com" '
    '-H "Access-Control-Request-Method: POST" '
    '-H "Access-Control-Request-Headers: content-type" '
    '| head -10',
    "preflight check"
)

print("\n=== POST with browser UA ===")
run(
    'curl -s -o /dev/null -w "%{http_code}" -X POST https://uj.pfm-qa.com/p '
    '-H "Origin: https://www.particleformen.com" '
    '-H "Content-Type: application/json" '
    '-H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0" '
    '-d \'{"session_id":"cors-test-001","page_url":"https://www.particleformen.com/"}\'',
    "POST test"
)
c.close()
