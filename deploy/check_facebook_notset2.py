"""Check all URL params present on Facebook fbclid/brid (not set) sessions."""
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
    return [r.split("|") for r in rows if r]

# Get all distinct param names from fbclid/brid FB sessions with no campaign
rows = q("""
  SELECT DISTINCT entry_url
  FROM   sessions
  WHERE  source = 'Facebook'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  (entry_url ILIKE '%fbclid=%' OR entry_url ILIKE '%brid=%')
    AND  first_seen >= NOW() - INTERVAL '30 days'
  LIMIT  30
""")

from urllib.parse import urlparse, parse_qs, unquote

param_names = {}
for r in rows:
    if not r: continue
    url = r[0]
    try:
        parsed = urlparse(url)
        # merge query + hash params
        combined = parsed.query
        if parsed.fragment and '=' in parsed.fragment:
            combined += ('&' if combined else '') + parsed.fragment
        params = parse_qs(combined)
        for k in params:
            param_names[k] = param_names.get(k, 0) + 1
    except Exception:
        pass

print("Param names seen across Facebook (not set) fbclid/brid sessions:")
for k, cnt in sorted(param_names.items(), key=lambda x: -x[1]):
    print(f"  {cnt:>4}  {k}")

# Check specifically for nb_adname / nb_campaign / ad_name etc.
print("\nFull URL sample with most params:")
all_rows = q("""
  SELECT entry_url
  FROM   sessions
  WHERE  source = 'Facebook'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  (entry_url ILIKE '%fbclid=%' OR entry_url ILIKE '%brid=%')
    AND  LENGTH(entry_url) = (
      SELECT MAX(LENGTH(entry_url))
      FROM sessions
      WHERE source='Facebook'
        AND (utm_campaign IS NULL OR utm_campaign = '')
        AND (entry_url ILIKE '%fbclid=%' OR entry_url ILIKE '%brid=%')
        AND first_seen >= NOW() - INTERVAL '30 days'
    )
  LIMIT 3
""")
for r in all_rows:
    if r: print(" ", r[0])

c.close()
