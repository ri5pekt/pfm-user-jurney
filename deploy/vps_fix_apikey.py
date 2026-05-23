import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
ENV  = "/var/www/pfm-uj/app/.env"

# Step 1: grab the key fresh from surveys server
print("=== Fetch IP_API_KEY from surveys server ===")
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("2.24.70.59", username="root", key_filename=KEY, timeout=15)
_, out, _ = s.exec_command("grep '^IP_API_KEY=' /var/www/pfm-surveys.cloud/.env", timeout=10)
line = out.read().decode("utf-8", errors="replace").strip()
s.close()

if not line or "=" not in line:
    print(f"ERROR: could not read key, got: {repr(line)}")
    sys.exit(1)

api_key = line.split("=", 1)[1].strip()
print(f"  key: {api_key[:6]}...{api_key[-4:]}")

# Step 2: write it into pfm-uj .env
print("\n=== Update .env on pfm-uj server ===")
t = paramiko.SSHClient()
t.set_missing_host_key_policy(paramiko.AutoAddPolicy())
t.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=30):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = t.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines(): print(f"     {l}")

# Show current .env state for the key
_, chk, _ = t.exec_command(f"grep 'IP_API_KEY' {ENV}", timeout=10)
current = chk.read().decode().strip()
print(f"  current in .env: {repr(current)}")

# Remove any existing IP_API_KEY lines and append a clean one
_, ex, _ = t.exec_command(
    f"sed -i '/^IP_API_KEY/d' {ENV} && echo 'IP_API_KEY={api_key}' >> {ENV}",
    timeout=10)
ex.read()

# Verify
_, chk2, _ = t.exec_command(f"grep 'IP_API_KEY' {ENV} | sed 's/=.*/=***/'", timeout=10)
print(f"  after:  {chk2.read().decode().strip()}")

print("\n=== Restart worker ===")
run("cd /var/www/pfm-uj/app && docker compose up -d --force-recreate worker", "force-recreate worker", 30)

print("\n=== Verify env var inside container ===")
run("docker exec app-worker-1 sh -c 'echo KEY=${IP_API_KEY:0:6}...'", "key in container")

t.close()
print("\nDone.")
