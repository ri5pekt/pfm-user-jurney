"""
Investigate Facebook sessions with empty utm_campaign.
"""
import paramiko, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY     = r"C:\Users\denis\.ssh\id_ed25519"
HOST    = "72.62.148.226"
PG_USER = "pfm_user"
PG_DB   = "pfm_journeys"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def q(sql, label=""):
    cmd = f"docker exec app-postgres-1 psql -U {PG_USER} -d {PG_DB} -t -A -F'|' -c \"{sql}\""
    _, o, e = c.exec_command(cmd, timeout=60)
    rows = o.read().decode("utf-8", errors="replace").strip().splitlines()
    err  = e.read().decode("utf-8", errors="replace").strip()
    if err and "error" in err.lower():
        print("[SQL ERR]", err[:300])
    if label:
        print(f"\n{'='*60}")
        print(label)
        print('='*60)
    return [r.split("|") for r in rows if r]

# 1. What params are present in the entry URLs?
rows = q("""
  SELECT
    CASE
      WHEN entry_url ILIKE '%fbclid=%'      THEN 'fbclid'
      WHEN entry_url ILIKE '%nbt=fb%'       THEN 'nbt=fb'
      WHEN entry_url ILIKE '%brid=%'        THEN 'brid'
      WHEN entry_url ILIKE '%utm_source=%'  THEN 'utm_source only'
      ELSE 'no meta param'
    END AS param_type,
    COUNT(*) cnt
  FROM   sessions
  WHERE  source = 'Facebook'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY 1
  ORDER  BY cnt DESC
""", "1. What tracking param is present for Facebook (not set)?")
for r in rows:
    if len(r) >= 2:
        print(f"  {r[0]:<30} {r[1]:>7}")

# 2. Sample entry URLs
rows = q("""
  SELECT entry_url
  FROM   sessions
  WHERE  source = 'Facebook'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  first_seen >= NOW() - INTERVAL '30 days'
  ORDER  BY first_seen DESC
  LIMIT  15
""", "2. Sample entry URLs (Facebook, no campaign)")
for r in rows:
    if r: print(" ", r[0][:160])

# 3. nbt=fb URLs specifically — check what nb_campaign or utm_campaign they carry
rows = q("""
  SELECT entry_url
  FROM   sessions
  WHERE  source = 'Facebook'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  entry_url ILIKE '%nbt=fb%'
    AND  first_seen >= NOW() - INTERVAL '30 days'
  LIMIT  10
""", "3. nbt=fb URLs with no campaign")
for r in rows:
    if r: print(" ", r[0][:160])

# 4. fbclid URLs with no campaign
rows = q("""
  SELECT entry_url
  FROM   sessions
  WHERE  source = 'Facebook'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  entry_url ILIKE '%fbclid=%'
    AND  first_seen >= NOW() - INTERVAL '30 days'
  LIMIT  10
""", "4. fbclid URLs with no campaign")
for r in rows:
    if r: print(" ", r[0][:160])

# 5. Check if placement column has data for these sessions
rows = q("""
  SELECT placement, COUNT(*) cnt
  FROM   sessions
  WHERE  source = 'Facebook'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY placement
  ORDER  BY cnt DESC
  LIMIT  15
""", "5. Placement breakdown for Facebook (not set)")
for r in rows:
    if len(r) >= 2:
        print(f"  '{r[0]}'  →  {r[1]}")

c.close()
