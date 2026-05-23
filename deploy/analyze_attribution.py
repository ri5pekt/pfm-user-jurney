import paramiko, io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

PG_USER = "pfm_user"
PG_DB   = "pfm_journeys"

def q(sql):
    cmd = f'docker exec app-postgres-1 psql -U {PG_USER} -d {PG_DB} -t -A -F"|" -c "{sql}"'
    _, o, e = c.exec_command(cmd, timeout=60)
    rows = o.read().decode("utf-8", errors="replace").strip().splitlines()
    err  = e.read().decode("utf-8", errors="replace").strip()
    if err and "error" in err.lower(): print("[SQL ERR]", err[:300])
    return [r.split("|") for r in rows if r]

print("=" * 70)
print("1. ALL DISTINCT SOURCES (last 30 days) — count + sample entry_url")
print("=" * 70)
rows = q("""
  SELECT source, COUNT(*) AS cnt,
         MIN(entry_url) AS sample_url
  FROM   sessions
  WHERE  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY source
  ORDER  BY cnt DESC
  LIMIT  60
""")
for r in rows:
    src, cnt, url = r[0], r[1], r[2] if len(r) > 2 else ''
    url_short = url[:90] if url else ''
    print(f"  {cnt:>6}  {src:<30}  {url_short}")

print()
print("=" * 70)
print("2. SOURCES WITH DIGITS (potential coupon codes)")
print("=" * 70)
rows = q("""
  SELECT source, COUNT(*) AS cnt,
         MIN(entry_url) AS sample_url,
         MIN(utm_source) AS utm_src,
         MIN(utm_medium) AS utm_med
  FROM   sessions
  WHERE  source ~ '[0-9]'
    AND  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY source
  ORDER  BY cnt DESC
""")
for r in rows:
    src, cnt, url, usrc, umed = r[0], r[1], r[2] if len(r) > 2 else '', r[3] if len(r) > 3 else '', r[4] if len(r) > 4 else ''
    print(f"  {cnt:>6}  source={src:<25}  utm_source={usrc}  utm_medium={umed}")
    if url: print(f"         url: {url[:100]}")

print()
print("=" * 70)
print("3. SOURCES WITH LONG NAMES (>20 chars) — possible miscoded domains/UTMs")
print("=" * 70)
rows = q("""
  SELECT source, COUNT(*) AS cnt, MIN(entry_url) AS sample_url
  FROM   sessions
  WHERE  LENGTH(source) > 20
    AND  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY source
  ORDER  BY cnt DESC
  LIMIT  30
""")
for r in rows:
    src, cnt, url = r[0], r[1], r[2] if len(r) > 2 else ''
    print(f"  {cnt:>6}  {src[:50]}")
    if url: print(f"         url: {url[:100]}")

print()
print("=" * 70)
print("4. TOP UTM_SOURCE VALUES NOT MAPPED TO KNOWN SOURCES")
print("=" * 70)
rows = q("""
  SELECT utm_source, source, COUNT(*) AS cnt
  FROM   sessions
  WHERE  utm_source <> ''
    AND  utm_source <> source
    AND  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY utm_source, source
  ORDER  BY cnt DESC
  LIMIT  40
""")
for r in rows:
    usrc, src, cnt = r[0], r[1], r[2]
    print(f"  {cnt:>6}  utm_source={usrc:<30}  → source={src}")

print()
print("=" * 70)
print("5. MEDIUM BREAKDOWN")
print("=" * 70)
rows = q("""
  SELECT medium, COUNT(*) AS cnt
  FROM   sessions
  WHERE  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY medium
  ORDER  BY cnt DESC
""")
for r in rows:
    med, cnt = r[0], r[1]
    print(f"  {cnt:>7}  {med}")

print()
print("=" * 70)
print("6. CHANNEL BREAKDOWN")
print("=" * 70)
rows = q("""
  SELECT channel, COUNT(*) AS cnt
  FROM   sessions
  WHERE  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY channel
  ORDER  BY cnt DESC
""")
for r in rows:
    ch, cnt = r[0], r[1]
    print(f"  {cnt:>7}  {ch}")

print()
print("=" * 70)
print("7. REFERRER DOMAINS NOT RECOGNISED (mapped to 'referral') — top 30")
print("=" * 70)
rows = q("""
  SELECT source, COUNT(*) AS cnt, MIN(referrer) AS sample_ref
  FROM   sessions
  WHERE  channel = 'referral'
    AND  source NOT IN ('direct','Email','Gmail','Narvar','Microsoft Edge','AdsSupply','Wunderkind','Yotpo')
    AND  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY source
  ORDER  BY cnt DESC
  LIMIT  30
""")
for r in rows:
    src, cnt, ref = r[0], r[1], r[2] if len(r) > 2 else ''
    print(f"  {cnt:>6}  {src:<35}  ref: {ref[:60]}")

print()
print("=" * 70)
print("8. SAMPLE ENTRY URLS FOR 'direct' — check for missed UTMs")
print("=" * 70)
rows = q("""
  SELECT entry_url, COUNT(*) AS cnt
  FROM   sessions
  WHERE  source = 'direct'
    AND  entry_url ILIKE '%utm_%'
    AND  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY entry_url
  ORDER  BY cnt DESC
  LIMIT  20
""")
if rows:
    for r in rows:
        url, cnt = r[0], r[1]
        print(f"  {cnt:>6}  {url[:120]}")
else:
    print("  (none — direct sessions have no UTM params, looks good)")

print()
print("=" * 70)
print("9. SUSPICIOUS: sources that look like hostnames (contain dots)")
print("=" * 70)
rows = q("""
  SELECT source, channel, COUNT(*) AS cnt, MIN(referrer) AS sample_ref
  FROM   sessions
  WHERE  source LIKE '%.%'
    AND  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY source, channel
  ORDER  BY cnt DESC
  LIMIT  30
""")
for r in rows:
    src, ch, cnt, ref = r[0], r[1], r[2], r[3] if len(r) > 3 else ''
    print(f"  {cnt:>6}  {src:<40}  channel={ch}")
    if ref: print(f"         ref: {ref[:80]}")

c.close()
print()
print("=== Analysis complete ===")
