import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

_, out, _ = c.exec_command("cat $(ls /etc/nginx/sites-enabled/ | xargs -I{} echo /etc/nginx/sites-enabled/{} | grep -i uj | head -1)", timeout=10)
result = out.read().decode("utf-8", errors="replace").strip()
if not result:
    _, out, _ = c.exec_command("ls /etc/nginx/sites-enabled/", timeout=10)
    print("sites-enabled:", out.read().decode().strip())
    _, out, _ = c.exec_command("cat /etc/nginx/sites-enabled/*uj*", timeout=10)
    result = out.read().decode("utf-8", errors="replace").strip()
print(result)
c.close()
