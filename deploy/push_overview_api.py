import paramiko, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
APP_DIR = "/var/www/pfm-uj/app"

files = [
    (r"c:\Users\denis\Desktop\docker-projects\pfm-user-jurney\admin-api\src\routes\overview.ts",
     f"{APP_DIR}/admin-api/src/routes/overview.ts"),
]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

sftp = c.open_sftp()
for local, remote in files:
    sftp.put(local, remote)
    print(f"Uploaded {os.path.basename(local)} ({os.path.getsize(local)} bytes)")
sftp.close()

def run(cmd):
    print(f"$ {cmd[:80]}")
    _, o, e = c.exec_command(cmd, timeout=300)
    out = o.read().decode("utf-8", errors="replace").strip()
    err = e.read().decode("utf-8", errors="replace").strip()
    if out: print(out[-2000:])
    if err and "error" in err.lower(): print("[err]", err[-400:])

print("=== Rebuild admin-api ===")
run(f"cd {APP_DIR} && docker compose build admin-api")
run(f"cd {APP_DIR} && docker compose up -d --force-recreate admin-api")
print("=== Done ===")
c.close()
