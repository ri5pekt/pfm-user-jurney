import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY = r"C:\Users\denis\.ssh\id_ed25519"

# Step 1: grab IP_API_KEY from surveys server
print("=== Fetch IP_API_KEY from surveys server ===")
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("2.24.70.59", username="root", key_filename=KEY, timeout=15)
_, out, _ = s.exec_command("grep IP_API_KEY /var/www/pfm-surveys.cloud/.env", timeout=15)
result = out.read().decode("utf-8", errors="replace").strip()
print(f"  raw: {result}")
s.close()

# Parse the key value
api_key = None
for line in result.splitlines():
    if "IP_API_KEY" in line and "=" in line:
        api_key = line.split("=", 1)[1].strip()
        break

if not api_key:
    print("ERROR: could not find IP_API_KEY")
    sys.exit(1)

print(f"  found key: {api_key[:6]}...{api_key[-4:]}")

# Step 2: add/update IP_API_KEY in pfm-uj .env on target server
print("\n=== Update .env on pfm-uj server ===")
t = paramiko.SSHClient()
t.set_missing_host_key_policy(paramiko.AutoAddPolicy())
t.connect("72.62.148.226", username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=15):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = t.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines()[-4:]: print(f"     {l}")

# Check if key already in .env
_, chk, _ = t.exec_command("grep -c IP_API_KEY /var/www/pfm-uj/app/.env 2>/dev/null || echo 0", timeout=10)
count = chk.read().decode().strip()

if count == "0":
    run(f"echo 'IP_API_KEY={api_key}' >> /var/www/pfm-uj/app/.env", "append IP_API_KEY")
else:
    run(f"sed -i 's|^IP_API_KEY=.*|IP_API_KEY={api_key}|' /var/www/pfm-uj/app/.env", "update IP_API_KEY")

run("grep IP_API_KEY /var/www/pfm-uj/app/.env | sed 's/=.*/=***/'", "verify (masked)")

print("\n=== Restart worker to pick up new env var ===")
run("cd /var/www/pfm-uj/app && docker compose restart worker", "restart worker", 30)

_, ps, _ = t.exec_command("docker ps --format '{{.Names}}  {{.Status}}' | grep app-worker", timeout=10)
print(f"  {ps.read().decode().strip()}")

t.close()
print("\nDone.")
