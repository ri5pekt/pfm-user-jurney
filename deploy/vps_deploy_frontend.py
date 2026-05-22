import paramiko, sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY      = r"C:\Users\denis\.ssh\id_ed25519"
HOST     = "72.62.148.226"
APP_DIR  = "/var/www/pfm-uj/app"
DIST_DIR = r"C:\Users\denis\Desktop\docker-projects\pfm-user-jurney\frontend\dist"
REMOTE_FRONTEND = "/var/www/pfm-uj/frontend"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, label="", timeout=120):
    print(f"  -> {label or cmd[:80]}")
    _, stdout, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    for l in out.splitlines(): print(f"     {l}")
    return out

def upload_dir(sftp, local_dir, remote_dir):
    """Recursively upload a local directory to remote."""
    try:
        sftp.mkdir(remote_dir)
    except OSError:
        pass
    for item in os.listdir(local_dir):
        local_path  = os.path.join(local_dir, item)
        remote_path = remote_dir + "/" + item
        if os.path.isdir(local_path):
            upload_dir(sftp, local_path, remote_path)
        else:
            sftp.put(local_path, remote_path)

# 1. Upload frontend dist/
print("=== Upload frontend dist/ ===")
run(f"rm -rf {REMOTE_FRONTEND} && mkdir -p {REMOTE_FRONTEND}")
sftp = c.open_sftp()
print(f"  -> uploading {DIST_DIR} -> {REMOTE_FRONTEND}")
upload_dir(sftp, DIST_DIR, REMOTE_FRONTEND)
sftp.close()
run(f"chmod -R 755 {REMOTE_FRONTEND}", "chmod 755")
run(f"ls {REMOTE_FRONTEND}", "verify upload")

# 2. git pull + rebuild admin-api
print("\n=== git pull + rebuild admin-api ===")
run(f"cd {APP_DIR} && git pull origin master", "git pull", timeout=30)
run(f"cd {APP_DIR} && docker compose build admin-api", "build admin-api", timeout=300)
run(f"cd {APP_DIR} && docker compose up -d admin-api", "up -d admin-api", timeout=30)

time.sleep(4)

# 4. Verify
print("\n=== Verify ===")
run(f"curl -s http://127.0.0.1:3102/health", "admin-api health")
run(f"ls -la {REMOTE_FRONTEND}", "frontend files")

print("\n=== Done ===")
print("  https://uj.pfm-qa.com/admin/ — admin dashboard")
print("  https://uj.pfm-qa.com/admin/#/login — login page")
c.close()
