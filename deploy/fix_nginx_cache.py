import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
CONF = "/etc/nginx/sites-available/uj-pfm-qa"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

sftp = c.open_sftp()
with sftp.open(CONF, "r") as f:
    content = f.read().decode()

old = '        location ~* \\.(js|css|png|jpg|svg|ico|woff2?)$ {\n            expires 30d;\n            add_header Cache-Control "public, immutable";\n        }'
new = ('        location ~* \\.html$ {\n'
       '            add_header Cache-Control "no-cache, no-store, must-revalidate";\n'
       '            expires 0;\n'
       '        }\n\n'
       '        location ~* \\.(js|css|png|jpg|svg|ico|woff2?)$ {\n'
       '            expires 30d;\n'
       '            add_header Cache-Control "public, immutable";\n'
       '        }')

if old in content:
    content = content.replace(old, new)
    with sftp.open(CONF, "w") as f:
        f.write(content)
    print("Config updated.")
else:
    print("Pattern not found. Showing relevant section:")
    idx = content.find("location ~*")
    print(repr(content[idx:idx+300]))

sftp.close()

_, out, err = c.exec_command("nginx -t && systemctl reload nginx")
print(out.read().decode())
print(err.read().decode())
c.close()
