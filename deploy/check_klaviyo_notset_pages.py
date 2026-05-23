"""
For Klaviyo (not set) sessions:
- Look at ALL page URLs visited in each session
- Check if ANY page URL has utm_campaign or other useful params
- This tells us if multi-step attribution could recover the campaign name
"""
import paramiko, io, sys
from urllib.parse import urlparse, parse_qs, unquote
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

# Get Klaviyo (not set) session IDs (sample of 200)
print("Loading Klaviyo (not set) session IDs...")
rows = q("""
  SELECT session_id, entry_url
  FROM   sessions
  WHERE  source = 'Klaviyo'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  first_seen >= NOW() - INTERVAL '30 days'
  LIMIT  500
""")
session_ids = [r[0] for r in rows if r]
entry_urls  = {r[0]: r[1] for r in rows if r}
print(f"  Found {len(session_ids)} sessions\n")

if not session_ids:
    c.close()
    sys.exit()

# Get ALL page_url values for these sessions from events table
ids_sql = "','".join(session_ids[:200])
event_rows = q(f"""
  SELECT session_id, page_url, event_type
  FROM   events
  WHERE  session_id IN ('{ids_sql}')
  ORDER  BY session_id, timestamp
""")

# Group by session
from collections import defaultdict
session_pages = defaultdict(list)
for r in event_rows:
    if len(r) >= 2:
        session_pages[r[0]].append(r[1])

# Check each session: does ANY page URL have utm_campaign?
def extract_params(url):
    try:
        parsed = urlparse(url)
        combined = parsed.query
        if parsed.fragment and '=' in parsed.fragment:
            combined += ('&' if combined else '') + parsed.fragment
        return parse_qs(combined)
    except Exception:
        return {}

recovered   = 0
not_in_events = 0
campaigns_found = defaultdict(int)
sample_recoverable = []

for sid in session_ids[:200]:
    pages = session_pages.get(sid, [])
    if not pages:
        not_in_events += 1
        continue

    found_campaign = None
    for page_url in pages:
        params = extract_params(page_url)
        camp = params.get('utm_campaign', [''])[0]
        if camp:
            found_campaign = camp
            break  # use first occurrence

    if found_campaign:
        recovered += 1
        campaigns_found[found_campaign] += 1
        if len(sample_recoverable) < 5:
            sample_recoverable.append({
                'entry': entry_urls.get(sid, ''),
                'found_on': next(p for p in pages if 'utm_campaign' in p),
                'campaign': found_campaign,
            })

print(f"Sessions analyzed: {min(200, len(session_ids))}")
print(f"  Sessions with NO events in DB: {not_in_events}")
print(f"  Sessions where utm_campaign found in a later page: {recovered}")
print(f"  Sessions still unrecoverable: {min(200, len(session_ids)) - not_in_events - recovered}")

if campaigns_found:
    print(f"\nRecoverable campaign names (top 20):")
    for camp, cnt in sorted(campaigns_found.items(), key=lambda x: -x[1])[:20]:
        print(f"  {cnt:>4}  {camp}")

if sample_recoverable:
    print(f"\nSample recoverable sessions:")
    for s in sample_recoverable:
        print(f"  Entry URL:  {s['entry'][:100]}")
        print(f"  Campaign found on: {s['found_on'][:100]}")
        print(f"  Campaign: {s['campaign']}")
        print()

# Also check: what's the distribution of page counts for these sessions?
print("\nPage count distribution for Klaviyo (not set) sessions:")
rows2 = q("""
  SELECT page_count, COUNT(*) cnt
  FROM   sessions
  WHERE  source = 'Klaviyo'
    AND  (utm_campaign IS NULL OR utm_campaign = '')
    AND  first_seen >= NOW() - INTERVAL '30 days'
  GROUP  BY page_count
  ORDER  BY page_count
  LIMIT  20
""")
for r in rows2:
    if len(r) >= 2:
        bar = '█' * min(int(r[1])//5, 40)
        print(f"  pages={r[0]:>3}  n={r[1]:>5}  {bar}")

c.close()
