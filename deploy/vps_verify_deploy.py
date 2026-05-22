import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label=""):
    _, out, err = c.exec_command(cmd, timeout=180)
    stdout = out.read().decode("utf-8", errors="replace").strip()
    stderr = err.read().decode("utf-8", errors="replace").strip()
    if label: print(f"\n--- {label} ---")
    if stdout: print(stdout[-3000:])
    if stderr: print("STDERR:", stderr[-1000:])
    return stdout

print("=== Check + Force Rebuild ===")
run("cd /root/pfm-user-jurney && git log --oneline -3", "git log")
run("cd /root/pfm-user-jurney && git pull 2>&1", "git pull")
run("cd /root/pfm-user-jurney && git log --oneline -3", "git log after pull")

# Force rebuild with explicit error output
print("\nBuilding collector...")
run("cd /root/pfm-user-jurney && docker compose -f docker-compose.prod.yml build collector 2>&1 | tail -10", "build collector")
run("cd /root/pfm-user-jurney && docker compose -f docker-compose.prod.yml up -d --no-deps collector 2>&1", "restart collector")

print("\nBuilding worker...")
run("cd /root/pfm-user-jurney && docker compose -f docker-compose.prod.yml build worker 2>&1 | tail -10", "build worker")
run("cd /root/pfm-user-jurney && docker compose -f docker-compose.prod.yml up -d --no-deps worker 2>&1", "restart worker")

run('docker ps --format "{{.Names}} {{.Status}}" | grep -E "collector|worker|admin"', "service status")
run('docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -c "SELECT channel, source, COUNT(*) FROM sessions GROUP BY channel, source ORDER BY COUNT(*) DESC LIMIT 10;"', "sessions preview")
c.close()
print("\nDone.")
