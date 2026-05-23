import paramiko, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY   = r"C:\Users\denis\.ssh\id_ed25519"
HOST  = "72.62.148.226"
LOCAL = r"C:\Users\denis\Desktop\docker-projects\pfm-user-jurney\frontend\dist"
REMOTE = "/var/www/pfm-uj/frontend"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

sftp = c.open_sftp()

def upload_dir(local_dir, remote_dir):
    try: sftp.mkdir(remote_dir)
    except OSError: pass
    for item in os.listdir(local_dir):
        lp = os.path.join(local_dir, item)
        rp = remote_dir + "/" + item
        if os.path.isdir(lp): upload_dir(lp, rp)
        else:
            sftp.put(lp, rp)

print("Uploading frontend dist...")
upload_dir(LOCAL, REMOTE)
sftp.close()
c.close()
print("Done.")
