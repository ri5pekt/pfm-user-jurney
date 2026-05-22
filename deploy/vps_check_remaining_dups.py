import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
KEY  = r"C:\Users\denis\.ssh\id_ed25519"
HOST = "72.62.148.226"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", key_filename=KEY, timeout=15)
_, out, _ = c.exec_command(r"""
docker exec app-postgres-1 psql -U pfm_user -d pfm_journeys -c "
SELECT e1.session_id,
       TO_CHAR(e1.timestamp,'HH24:MI:SS') t1,
       TO_CHAR(e2.timestamp,'HH24:MI:SS') t2,
       ROUND(ABS(EXTRACT(EPOCH FROM (e2.timestamp - e1.timestamp)))) gap_s,
       REGEXP_REPLACE(e1.page_url,'\?.*$','') path
FROM events e1
JOIN events e2
  ON e1.session_id = e2.session_id
 AND e1.id < e2.id
 AND REGEXP_REPLACE(e1.page_url,'\?.*$','') = REGEXP_REPLACE(e2.page_url,'\?.*$','')
 AND ABS(EXTRACT(EPOCH FROM (e2.timestamp - e1.timestamp))) BETWEEN 5 AND 10
LIMIT 20;"
""", timeout=20)
print(out.read().decode("utf-8", errors="replace"))
c.close()
