# Repro: per-IP login lockout keys on the ingress pod IP, so 5 bad logins by anyone lock out everyone
import os, uuid, requests
from dotenv import load_dotenv
from pymongo import MongoClient
load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
API = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
run = uuid.uuid4().hex[:8]
attacker = [f"test_atk{i}_{run}@example.com" for i in range(6)]
victim = f"test_victim_{run}@example.com"
r = requests.post(f"{API}/auth/register", json={"email": victim, "password": "TEST_pass_1234"}); vid = r.json()["account"]["user_id"]
try:
    # 6 different emails, one wrong attempt each (no single email reaches 5)
    print("attacker codes", [requests.post(f"{API}/auth/login", json={"email": e, "password": "WRONG_pass_99"}).status_code for e in attacker])
    print("ip keys", list(db.auth_attempts.find({"_id": {"$regex": "^ip:"}})))
    print("victim correct login codes", [requests.post(f"{API}/auth/login", json={"email": victim, "password": "TEST_pass_1234"}).status_code for _ in range(4)])
finally:
    db.auth_attempts.delete_many({"_id": {"$in": [f"email:{e}" for e in attacker + [victim]]}})
    db.auth_attempts.delete_many({"_id": {"$regex": "^ip:10\\."}})
    db.auth_accounts.delete_one({"user_id": vid})
