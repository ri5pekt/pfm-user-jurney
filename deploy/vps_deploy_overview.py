import io, os, subprocess, sys, paramiko
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY      = r"C:\Users\denis\.ssh\id_ed25519"
HOST     = "72.62.148.226"
APP_DIR  = "/var/www/pfm-uj/app"
FRONTEND = r"c:\Users\denis\Desktop\docker-projects\pfm-user-jurney\frontend"
REMOTE_FE = "/var/www/pfm-uj/frontend"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd):
    print(f"  $ {cmd[:100]}")
    _, out, err = c.exec_command(cmd, timeout=180)
    o = out.read().decode("utf-8", errors="replace").strip()
    e = err.read().decode("utf-8", errors="replace").strip()
    if o: print(o[-2000:])
    if e: print("[err]", e[-500:])

print("=== 1. Pull ===")
run(f"cd {APP_DIR} && git pull origin master")

print("=== 2. Rebuild admin-api ===")
run(f"cd {APP_DIR} && docker compose build admin-api")
run(f"cd {APP_DIR} && docker compose up -d --force-recreate admin-api")

print("=== 3. Build frontend locally ===")
r = subprocess.run(["cmd", "/c", "npm run build"], cwd=FRONTEND, capture_output=True, text=True)
print(r.stdout[-2000:] if r.stdout else "")
if r.returncode != 0:
    print("FAILED:", r.stderr[-1000:]); c.close(); raise SystemExit(1)

print("=== 4. Upload frontend ===")
sftp = c.open_sftp()
dist = os.path.join(FRONTEND, "dist")
for root, dirs, files in os.walk(dist):
    rel = os.path.relpath(root, dist)
    rdir = REMOTE_FE if rel == "." else f"{REMOTE_FE}/{rel.replace(os.sep, '/')}"
    try: sftp.mkdir(rdir)
    except: pass
    for f in files:
        sftp.put(os.path.join(root, f), f"{rdir}/{f}")
sftp.close()
print("Done.")
c.close()
