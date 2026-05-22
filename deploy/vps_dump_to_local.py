"""
Download a full data dump from VPS and restore it to the local dev Docker container.
Run from the project root.
"""
import paramiko, sys, io, os, subprocess, tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEY       = r"C:\Users\denis\.ssh\id_ed25519"
HOST      = "72.62.148.226"
DUMP_FILE = os.path.join(tempfile.gettempdir(), "pfm_journeys_dump.sql")
LOCAL_CONTAINER = "pfm-user-jurney-postgres-1"
LOCAL_DB        = "pfm_journeys"
LOCAL_USER      = "pfm_user"

# ── 1. Dump from VPS ────────────────────────────────────────────────
print("=== Step 1: Dump from VPS ===")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)

def vps(cmd, timeout=60):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    stdout = out.read().decode("utf-8", errors="replace")
    stderr = err.read().decode("utf-8", errors="replace").strip()
    if stderr and "error" in stderr.lower():
        print("  STDERR:", stderr[:200])
    return stdout

# Dump data-only for events + sessions (schema is managed by migration files)
print("  Running pg_dump on VPS (data only)…")
vps("docker exec app-postgres-1 pg_dump -U pfm_user pfm_journeys --data-only "
    "-t events -t sessions --no-acl --no-owner "
    "> /tmp/pfm_dump.sql 2>/tmp/pfm_dump.err")

err = vps("cat /tmp/pfm_dump.err").strip()
if err:
    print("  pg_dump errors:", err[:400])

# Check dump size
size = vps("wc -c < /tmp/pfm_dump.sql").strip()
print(f"  Dump size: {int(size or 0) // 1024} KB")

# ── 2. Download dump ────────────────────────────────────────────────
print(f"\n=== Step 2: Download to {DUMP_FILE} ===")
sftp = c.open_sftp()
sftp.get("/tmp/pfm_dump.sql", DUMP_FILE)
sftp.close()
c.close()
local_size = os.path.getsize(DUMP_FILE)
print(f"  Downloaded: {local_size // 1024} KB")

# ── 3. Ensure sessions table exists locally ─────────────────────────
print("\n=== Step 3: Ensure local schema is up to date ===")
migrations_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
sessions_sql   = os.path.join(migrations_dir, "migrate_sessions.sql")

with open(sessions_sql, "r") as f:
    sessions_ddl = f.read()

proc = subprocess.run(
    ["docker", "exec", "-i", LOCAL_CONTAINER,
     "psql", "-U", LOCAL_USER, "-d", LOCAL_DB],
    input=sessions_ddl.encode("utf-8"),
    capture_output=True,
)
out = proc.stdout.decode("utf-8", errors="replace").strip()
err = proc.stderr.decode("utf-8", errors="replace").strip()
if out: print("  ", out[-200:])
if err and "error" in err.lower(): print("  SCHEMA ERR:", err[-300:])
else: print("  Sessions table OK")

# ── 4. Truncate local tables ─────────────────────────────────────────
print("\n=== Step 4: Truncate local tables ===")
proc = subprocess.run(
    ["docker", "exec", "-i", LOCAL_CONTAINER,
     "psql", "-U", LOCAL_USER, "-d", LOCAL_DB,
     "-c", "TRUNCATE TABLE events, sessions RESTART IDENTITY CASCADE;"],
    capture_output=True,
)
print(" ", proc.stdout.decode("utf-8", errors="replace").strip())

# ── 5. Restore dump ──────────────────────────────────────────────────
print("\n=== Step 5: Restore dump to local container ===")
with open(DUMP_FILE, "rb") as f:
    proc = subprocess.run(
        ["docker", "exec", "-i", LOCAL_CONTAINER,
         "psql", "-U", LOCAL_USER, "-d", LOCAL_DB, "-q"],
        stdin=f,
        capture_output=True,
        timeout=120,
    )
stderr = proc.stderr.decode("utf-8", errors="replace").strip()
if stderr and "error" in stderr.lower():
    print("  RESTORE ERR:", stderr[:400])
else:
    print("  Restore complete")

# ── 6. Verify ────────────────────────────────────────────────────────
print("\n=== Step 6: Verify ===")
proc = subprocess.run(
    ["docker", "exec", LOCAL_CONTAINER,
     "psql", "-U", LOCAL_USER, "-d", LOCAL_DB, "-t", "-A",
     "-c", "SELECT 'events: ' || COUNT(*) FROM events UNION ALL SELECT 'sessions: ' || COUNT(*) FROM sessions;"],
    capture_output=True,
)
print(proc.stdout.decode("utf-8", errors="replace").strip())
print("\nDone. Local DB is ready for development.")
