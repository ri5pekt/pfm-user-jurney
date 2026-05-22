import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd):
    _, out, err = c.exec_command(cmd, timeout=30)
    print(out.read().decode("utf-8", errors="replace").strip())

run("ls /root/pfm-user-jurney/")
run("ls /root/pfm-user-jurney/worker/src/lib/")
run("cat /root/pfm-user-jurney/worker/src/lib/attribution.ts | head -20")
run("docker inspect app-worker-1 --format '{{.Config.WorkingDir}} {{.Image}}'")
run("docker inspect app-collector-1 --format '{{.Config.WorkingDir}} {{.Image}}'")
c.close()
