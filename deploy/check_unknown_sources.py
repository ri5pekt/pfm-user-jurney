import paramiko, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
PG_USER = "pfm_user"
PG_DB   = "pfm_journeys"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def q(sql):
    cmd = f"docker exec app-postgres-1 psql -U {PG_USER} -d {PG_DB} -t -A -F'|' -c \"{sql}\""
    _, o, e = c.exec_command(cmd, timeout=60)
    rows = o.read().decode("utf-8", errors="replace").strip().splitlines()
    err  = e.read().decode("utf-8", errors="replace").strip()
    if err and "error" in err.lower():
        print("[SQL ERR]", err[:300])
    return [r.split("|") for r in rows if r]

# Check medium/channel/campaign for small unrecognized sources
rows = q("""
  SELECT source, medium, channel, utm_campaign, COUNT(*) cnt,
         LEFT(MIN(entry_url),120) sample_url
  FROM   sessions
  WHERE  source IN ('patriot','echo','tv','1440','mobilize','interesting',
                    'golfgenius','history','christian','pourover','best30','memorial25')
  GROUP  BY source, medium, channel, utm_campaign
  ORDER  BY source, cnt DESC
  LIMIT  60
""")

print(f"{'SOURCE':<15} {'MEDIUM':<12} {'CHANNEL':<14} {'CNT':>5}  CAMPAIGN / SAMPLE URL")
print("-" * 100)
for r in rows:
    if len(r) >= 6:
        src, med, ch, camp, cnt, url = r[0], r[1], r[2], r[3], r[4], r[5]
        info = camp if camp else url[:80]
        print(f"{src:<15} {med:<12} {ch:<14} {cnt:>5}  {info}")

c.close()
