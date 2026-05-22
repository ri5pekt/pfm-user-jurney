import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)
_, out, _ = c.exec_command("find / -name 'docker-compose.prod.yml' 2>/dev/null | grep -v proc | head -5")
print(out.read().decode())
_, out, _ = c.exec_command("ls /root/")
print("root:", out.read().decode())
c.close()
