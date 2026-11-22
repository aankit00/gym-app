import os, json, urllib.request, sys
from dotenv import load_dotenv; load_dotenv("/app/backend/.env")
SK = os.environ["CLERK_SECRET_KEY"]
def bapi(path, body=None, method="POST"):
    req = urllib.request.Request("https://api.clerk.com/v1" + path, data=json.dumps(body).encode() if body is not None else None, method=method,
        headers={"Authorization": "Bearer " + SK, "Content-Type": "application/json", "User-Agent": "emergent-test"})
    return json.load(urllib.request.urlopen(req))
phone = sys.argv[1]
users = bapi(f"/users?phone_number=%2B{phone.lstrip('+')}", method="GET")
user = users[0] if users else bapi("/users", {"phone_number": [phone]})
s = bapi("/sessions", {"user_id": user["id"]})
print(bapi(f"/sessions/{s['id']}/tokens", {"expires_in_seconds": 600})["jwt"])
