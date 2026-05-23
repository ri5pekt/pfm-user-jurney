"""
Re-attribute sessions whose source is known to be wrong.
Only touches sessions where we can be confident about the correct source.
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

def sql(query, label=""):
    cmd = f'docker exec app-postgres-1 psql -U {PG_USER} -d {PG_DB} -t -A -c "{query}"'
    _, o, e = c.exec_command(cmd, timeout=60)
    out = o.read().decode("utf-8", errors="replace").strip()
    err = e.read().decode("utf-8", errors="replace").strip()
    if label: print(f"  {label}: {out}")
    if err and "error" in err.lower(): print("  [ERR]", err[:300])
    return out

print("=== Attribution backfill ===\n")

# ── 1. utm_clickid → Atwave
print("1. utm_clickid → Atwave")
sql("""
  UPDATE sessions
  SET    source='Atwave', medium='paid', channel='paid_other'
  WHERE  entry_url ILIKE '%utm_clickid=%'
    AND  source = 'direct'
""", "rows updated")

# ── 2. Flyover variants → 'Flyover'
print("2. flyover_* sources → 'Flyover'")
sql("""
  UPDATE sessions
  SET    source='Flyover'
  WHERE  source ILIKE 'flyover_%'
""", "rows updated")

# ── 3. gentlemantoday_* → 'Gentleman Today'  (UTM source variants)
print("3. gentlemantoday_* → 'Gentleman Today'")
sql("""
  UPDATE sessions
  SET    source='Gentleman Today'
  WHERE  source ILIKE 'gentlemantoday%'
    AND  source <> 'Gentleman Today'
""", "rows updated")

# ── 4. Narvar flow names (e.g. "Narvar - In Transit (2025)") → 'Narvar'
print("4. Narvar flow names → 'Narvar'")
sql("""
  UPDATE sessions
  SET    source='Narvar', medium='email', channel='email'
  WHERE  utm_source ILIKE '%narvar%'
    AND  source = 'Klaviyo'
""", "rows updated")

# ── 5. Yotpo flow names → 'Yotpo'
print("5. Yotpo flow names → 'Yotpo'")
sql("""
  UPDATE sessions
  SET    source='Yotpo', medium='email', channel='email'
  WHERE  (utm_source ILIKE '%yotpo%'
       OR utm_source ILIKE '%loyalty%'
       OR utm_source ILIKE '%rewards%')
    AND  source = 'Klaviyo'
    AND  utm_source NOT ILIKE '%klaviyo%'
""", "rows updated")

# ── 6. Wunderkind flow names → 'Wunderkind'
print("6. Wunderkind flow names → 'Wunderkind'")
sql("""
  UPDATE sessions
  SET    source='Wunderkind', medium='email', channel='email'
  WHERE  utm_source ILIKE '%wunderkind%'
    AND  source = 'Klaviyo'
""", "rows updated")

# ── 7. sref_id + utm_medium=sms → Klaviyo SMS
print("7. sref_id SMS links → Klaviyo SMS")
sql("""
  UPDATE sessions
  SET    source='Klaviyo', medium='sms', channel='sms'
  WHERE  entry_url ILIKE '%sref_id=%'
    AND  utm_medium = 'sms'
    AND  source = 'direct'
""", "rows updated")

# ── 8. utm_id WITHOUT utm_source → revert to direct
# utm_id is a generic GA4 Campaign ID — NOT Facebook-specific.
# Any platform (Meta, Atwave, Google) can use it.
# We previously wrongly attributed these to Facebook; now reverting.
print("8. Reverting utm_id-only sessions back to direct")
sql("""
  UPDATE sessions
  SET    source='direct', medium='none', channel='direct'
  WHERE  utm_source = ''
    AND  entry_url ~ 'utm_id='
    AND  source = 'Facebook'
    AND  NOT (entry_url ILIKE '%fbclid=%'
           OR entry_url ILIKE '%nbt=fb%'
           OR entry_url ILIKE '%brid=%')
""", "rows updated")

# ── 9. TikTok (ttclid) → TikTok
print("9. ttclid → TikTok")
sql("""
  UPDATE sessions
  SET    source='TikTok', medium='paid_social', channel='paid_social'
  WHERE  entry_url ILIKE '%ttclid=%'
    AND  source NOT IN ('TikTok')
""", "rows updated")

# ── 10. utm_source=tiktok → TikTok (normalize casing)
print("10. utm_source=tiktok → TikTok")
sql("""
  UPDATE sessions
  SET    source='TikTok', medium='paid_social', channel='paid_social'
  WHERE  LOWER(utm_source) = 'tiktok'
    AND  source <> 'TikTok'
""", "rows updated")

# ── 11. liveintent → LiveIntent
print("11. liveintent → LiveIntent")
sql("""
  UPDATE sessions
  SET    source='LiveIntent', medium='email', channel='email'
  WHERE  LOWER(utm_source) = 'liveintent'
    AND  source <> 'LiveIntent'
""", "rows updated")

# ── 12. Normalize 'atwave' → 'Atwave' (case inconsistency from old sessions)
print("12. atwave → Atwave (case normalization)")
sql("""
  UPDATE sessions
  SET    source='Atwave'
  WHERE  source = 'atwave'
""", "rows updated")

# ── 13. Klaviyo mtke (transactional email) → label utm_campaign = 'Transactional'
print("13. Klaviyo mtke → utm_campaign = 'Transactional'")
sql("""
  UPDATE sessions
  SET    utm_campaign = 'Transactional'
  WHERE  source = 'Klaviyo'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  entry_url ILIKE '%mtke=%'
""", "rows updated")

# ── 14. Normalize Facebook placement variants
print("14. Facebook placement normalization")
sql("""
  UPDATE sessions SET placement = 'Facebook Reels'
  WHERE source IN ('Facebook','Instagram','Audience Network')
    AND placement IN ('Facebook_Reels')
""", "Facebook_Reels rows")
sql("""
  UPDATE sessions SET placement = 'Facebook Stories'
  WHERE source IN ('Facebook','Instagram','Audience Network')
    AND placement IN ('Facebook_Stories','Facebook_Mobile_Stories','Facebook_Desktop_Stories')
""", "Facebook_Stories rows")
sql("""
  UPDATE sessions SET placement = 'Facebook Video'
  WHERE source IN ('Facebook','Instagram','Audience Network')
    AND placement = 'Facebook_Mobile_Instream'
""", "Facebook_Mobile_Instream rows")
sql("""
  UPDATE sessions SET placement = ''
  WHERE source IN ('Facebook','Instagram','Audience Network')
    AND placement IN ('placement','{{placement}}')
""", "Unresolved macro rows")

# ── Verify final source distribution
print("\n=== Top sources after backfill ===")
rows_raw = sql("""
  SELECT source, COUNT(*) AS cnt
  FROM   sessions
  WHERE  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY source
  ORDER  BY cnt DESC
  LIMIT  40
""")
for line in rows_raw.splitlines():
    parts = line.split("|")
    if len(parts) == 2:
        print(f"  {parts[1]:>7}  {parts[0]}")

c.close()
print("\n=== Backfill complete ===")
