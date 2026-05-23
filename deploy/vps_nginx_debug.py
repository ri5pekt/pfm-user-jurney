import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def run(cmd, timeout=10):
    _, out, _ = c.exec_command(cmd, timeout=timeout, get_pty=True)
    return out.read().decode("utf-8", errors="replace").strip()

# show the flags block in context
print("=== nginx config around /flags/ ===")
print(run("grep -n 'flags' /etc/nginx/sites-available/uj-pfm-qa"))

# check if the file actually exists where alias points
print("\n=== files at alias path ===")
print(run("ls /var/www/pfm-uj/frontend/flags/ | head -5"))

# check nginx error log for the 404
print("\n=== nginx error log (last 10) ===")
print(run("tail -10 /var/log/nginx/error.log"))

# test with full path
print("\n=== direct file access test ===")
print(run("ls -la /var/www/pfm-uj/frontend/flags/US.png"))

c.close()
