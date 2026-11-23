# Helper: show demo user's profile basics, plans and current swaps on a plan via the public API.
import json
import subprocess
import sys

import requests

URL = [l.split("=", 1)[1].strip().strip('"') for l in open("/app/frontend/.env") if l.startswith("EXPO_PUBLIC_BACKEND_URL")][0].rstrip("/")
phone = sys.argv[1] if len(sys.argv) > 1 else "+12015550100"
tok = subprocess.check_output(["python", "/app/backend/tests/clerk_token.py", phone], text=True).strip().splitlines()[-1]
H = {"Authorization": f"Bearer {tok}"}
me = requests.get(f"{URL}/api/me", headers=H, timeout=15)
print("me", me.status_code, json.dumps(me.json())[:400])
pl = requests.get(f"{URL}/api/plans", headers=H, timeout=15)
print("plans", pl.status_code, json.dumps(pl.json())[:600])
for pid in sys.argv[2:]:
    p = requests.get(f"{URL}/api/plans/{pid}", headers=H, timeout=15).json()
    for d in p.get("days", []):
        sw = [(i, e.get("id"), e.get("name"), e.get("swapped")) for i, e in enumerate(d.get("exercises", []))]
        print("day", d.get("day"), d.get("locked"), sw[:8])
