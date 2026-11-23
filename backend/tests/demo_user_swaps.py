# Helper: list plan swaps for the demo user (+12015550100) so the test only cleans up swaps it created.
import os
import sys

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
u = db.users.find_one({"phone": {"$in": ["+12015550100", "12015550100"]}}, {"_id": 0, "user_id": 1, "plans_unlocked": 1, "gender": 1, "active_plan": 1})
if not u:
    u = db.users.find_one({"name": {"$regex": "."}, "phone": {"$regex": "2015550100"}}, {"_id": 0})
print("user:", u)
if u:
    for s in db.plan_swaps.find({"user_id": u["user_id"]}, {"_id": 0}):
        print("swap:", s)
    if len(sys.argv) > 1 and sys.argv[1] == "--keys":
        print(list(db.users.find_one({"user_id": u["user_id"]}).keys()))
