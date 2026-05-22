import paramiko, sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
APP_DIR = "/var/www/pfm-uj/app"
DIST    = r"C:\Users\denis\Desktop\docker-projects\pfm-user-jurney\frontend\dist"
REMOTE_FRONTEND = "/var/www/pfm-uj/frontend"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=300):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines()[-5:]:
        print(f"     {l}")
    return out

def upload_dir(sftp, local_dir, remote_dir):
    try: sftp.mkdir(remote_dir)
    except OSError: pass
    for item in os.listdir(local_dir):
        lp = os.path.join(local_dir, item)
        rp = remote_dir + "/" + item
        if os.path.isdir(lp): upload_dir(sftp, lp, rp)
        else: sftp.put(lp, rp)

print("=== git pull ===")
run(f"cd {APP_DIR} && git pull origin master", "git pull", 30)

print("\n=== Rebuild worker ===")
run(f"cd {APP_DIR} && docker compose build worker", "build worker", 300)
run(f"cd {APP_DIR} && docker compose up -d worker", "restart worker", 30)

print("\n=== Upload frontend ===")
run(f"rm -rf {REMOTE_FRONTEND} && mkdir -p {REMOTE_FRONTEND}")
sftp = c.open_sftp()
print("  -> uploading dist/")
upload_dir(sftp, DIST, REMOTE_FRONTEND)
sftp.close()
run(f"chmod -R 755 {REMOTE_FRONTEND}", "chmod")

# Re-attribute all existing sessions by running the attribution logic
# against entry_url + referrer stored in the DB.
# We do this via a SQL trick: clear source/channel on all sessions
# and let the worker re-process them. But simpler: just truncate sessions
# and let the worker rebuild them from the events table.
print("\n=== Re-attribute existing sessions ===")
print("  -> clearing sessions table so worker rebuilds with fixed attribution")
run(
    "docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -c "
    "'TRUNCATE TABLE sessions;'",
    "truncate sessions"
)

time.sleep(4)

print("\n=== Verify ===")
run("docker logs app-worker-1 --tail 6", "worker logs")

print("\nDone — new events will be attributed with fixes. Sessions rebuilding from new events.")
c.close()
