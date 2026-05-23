"""
Investigate Klaviyo sessions with empty utm_campaign.
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

# 1. How many Klaviyo sessions have no utm_campaign, and what are their utm_source values?
rows = q("""
  SELECT utm_source, utm_medium, COUNT(*) cnt
  FROM   sessions
  WHERE  source = 'Klaviyo'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY utm_source, utm_medium
  ORDER  BY cnt DESC
  LIMIT  20
""", "1. Klaviyo (not set) — utm_source / utm_medium breakdown")
print(f"{'UTM_SOURCE':<30} {'MEDIUM':<10} {'COUNT':>7}")
print("-"*50)
for r in rows:
    if len(r) >= 3:
        print(f"{r[0]:<30} {r[1]:<10} {r[2]:>7}")

# 2. Sample entry URLs for the biggest group
rows = q("""
  SELECT entry_url
  FROM   sessions
  WHERE  source = 'Klaviyo'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  first_seen >= NOW() - INTERVAL '30 days'
  ORDER  BY first_seen DESC
  LIMIT  20
""", "2. Sample entry URLs (most recent Klaviyo no-campaign sessions)")
for r in rows:
    if r: print(" ", r[0][:140])

# 3. Check if nb_klid / _kx params are in the entry URLs (Klaviyo click ID)
rows = q("""
  SELECT
    CASE
      WHEN entry_url ILIKE '%nb_klid=%' THEN 'has nb_klid'
      WHEN entry_url ILIKE '%_kx=%'     THEN 'has _kx'
      WHEN entry_url ILIKE '%mtke=%'    THEN 'has mtke'
      WHEN entry_url ILIKE '%utm_source%' THEN 'has utm_source only'
      ELSE 'no klaviyo param'
    END AS param_type,
    COUNT(*) cnt
  FROM   sessions
  WHERE  source = 'Klaviyo'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY 1
  ORDER  BY cnt DESC
""", "3. Which Klaviyo click param is present in the entry URL?")
for r in rows:
    if len(r) >= 2:
        print(f"  {r[0]:<30} {r[1]:>7}")

# 4. For nb_klid sessions — what does the full URL look like?
rows = q("""
  SELECT entry_url
  FROM   sessions
  WHERE  source = 'Klaviyo'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  entry_url ILIKE '%nb_klid=%'
    AND  first_seen >= NOW() - INTERVAL '30 days'
  LIMIT  5
""", "4. Sample nb_klid Klaviyo URLs (no campaign)")
for r in rows:
    if r: print(" ", r[0][:160])

# 5. For utm_source-only sessions — sample URLs
rows = q("""
  SELECT entry_url
  FROM   sessions
  WHERE  source = 'Klaviyo'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  entry_url NOT ILIKE '%nb_klid=%'
    AND  entry_url NOT ILIKE '%_kx=%'
    AND  first_seen >= NOW() - INTERVAL '30 days'
  LIMIT  10
""", "5. Sample URLs with no Klaviyo click param")
for r in rows:
    if r: print(" ", r[0][:160])

c.close()
