import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def q(label, sql):
    print(f"\n=== {label} ===")
    _, out, _ = c.exec_command(f'docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -F "\\t" -c "{sql}"', timeout=20)
    print(out.read().decode("utf-8", errors="replace").strip())

q("Top sources after fix", """
SELECT channel, source, COUNT(*) n FROM sessions
GROUP BY 1,2 ORDER BY n DESC LIMIT 20
""")

q("YouTube Ads sessions", """
SELECT channel, source, COUNT(*) n FROM sessions
WHERE source ILIKE '%youtube%'
GROUP BY 1,2 ORDER BY n DESC
""")

q("Google Ads sessions (should no longer include YouTube)", """
SELECT channel, source, COUNT(*) n FROM sessions
WHERE source = 'Google Ads'
GROUP BY 1,2 ORDER BY n DESC
""")

c.close()
