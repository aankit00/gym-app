# Helper: inspect library thumbnails (first N) and check whether the URLs load (HEAD/GET status).
import subprocess
import sys

import requests

URL = [l.split("=", 1)[1].strip().strip('"') for l in open("/app/frontend/.env") if l.startswith("EXPO_PUBLIC_BACKEND_URL")][0].rstrip("/")
tok = subprocess.check_output(["python", "/app/backend/tests/clerk_token.py", "+12015550100"], text=True).strip().splitlines()[-1]
H = {"Authorization": f"Bearer {tok}"}
d = requests.get(f"{URL}/api/library", headers=H, timeout=30).json()
names = sys.argv[1:] or None
items = [i for i in d["items"] if not names or any(n.lower() in i["name"].lower() for n in names)][:6]
for i in items:
    t = i["thumb"]
    st = None
    if t:
        try:
            r = requests.get(t if t.startswith("http") else URL + t, timeout=15, stream=True)
            st = (r.status_code, r.headers.get("content-type"), r.headers.get("access-control-allow-origin"))
        except Exception as e:  # noqa: BLE001
            st = str(e)[:80]
    print(i["id"], i["name"][:30], "| thumb:", len(t or ""), "|", st)
