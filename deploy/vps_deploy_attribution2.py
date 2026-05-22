import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label=""):
    _, out, err = c.exec_command(cmd, timeout=120)
    stdout = out.read().decode("utf-8", errors="replace").strip()
    stderr = err.read().decode("utf-8", errors="replace").strip()
    if label:
        print(f"\n--- {label} ---")
    if stdout: print(stdout[-2000:])
    if stderr and "error" in stderr.lower(): print("STDERR:", stderr[-500:])
    return stdout

print("=== Deploying attribution fixes ===\n")

run("cd /root/pfm-user-jurney && git pull", "git pull")

# Rebuild collector (regional filter fix)
run("cd /root/pfm-user-jurney && docker compose -f docker-compose.prod.yml build --no-cache collector 2>&1 | tail -5", "build collector")
run("docker compose -f /root/pfm-user-jurney/docker-compose.prod.yml up -d collector", "restart collector")

# Rebuild worker (attribution fixes)
run("cd /root/pfm-user-jurney && docker compose -f docker-compose.prod.yml build --no-cache worker 2>&1 | tail -5", "build worker")
run("docker compose -f /root/pfm-user-jurney/docker-compose.prod.yml up -d worker", "restart worker")

# Upload new frontend build
import os
sftp = c.open_sftp()
local_dist = r"C:\Users\denis\Desktop\docker-projects\pfm-user-jurney\frontend\dist"
remote_dist = "/root/pfm-user-jurney/frontend/dist"
run(f"rm -rf {remote_dist} && mkdir -p {remote_dist}")

for root, dirs, files in os.walk(local_dist):
    rel = os.path.relpath(root, local_dist).replace("\\", "/")
    remote_dir = remote_dist if rel == "." else f"{remote_dist}/{rel}"
    try: sftp.mkdir(remote_dir)
    except: pass
    for fname in files:
        sftp.put(os.path.join(root, fname), f"{remote_dir}/{fname}")

print("  frontend uploaded")
sftp.close()

# Truncate sessions for re-attribution
run('docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -c "TRUNCATE TABLE sessions;"', "truncate sessions")

# Verify
print("\n=== Verification ===")
run('docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -c "SELECT COUNT(*) FROM sessions;"', "session count (should be 0 now)")
run('docker ps --format "{{.Names}} {{.Status}}" | grep -E "collector|worker|admin|nginx"', "service status")

c.close()
print("\nDone.")
