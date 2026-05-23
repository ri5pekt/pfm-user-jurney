import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def q(label, sql):
    print(f"\n=== {label} ===")
    _, out, _ = c.exec_command(f'docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -t -A -F "\t" -c "{sql}"', timeout=15)
    print(out.read().decode("utf-8", errors="replace").strip())

# Verify mtke fix
q("mtke still direct (should be 0)", """
SELECT COUNT(*) FROM sessions WHERE entry_url LIKE '%mtke%' AND channel = 'direct'
""")
q("mtke sessions now attributed", """
SELECT channel, source, COUNT(*) n FROM sessions WHERE entry_url LIKE '%mtke%'
GROUP BY 1,2 ORDER BY n DESC
""")

# Verify brid fix
q("brid still direct", """
SELECT COUNT(*) FROM sessions WHERE entry_url LIKE '%brid=%' AND channel = 'direct'
""")
q("brid sessions now attributed", """
SELECT channel, source, COUNT(*) n FROM sessions WHERE entry_url LIKE '%brid=%'
GROUP BY 1,2 ORDER BY n DESC LIMIT 5
""")

# Updated channel breakdown
q("channel breakdown", """
SELECT channel, source, medium, COUNT(*) n FROM sessions
GROUP BY 1,2,3 ORDER BY n DESC LIMIT 15
""")

c.close()
