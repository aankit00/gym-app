#!/usr/bin/env python
"""Helper used by the UI test to seed/clean freeze test state in MongoDB.
Usage:
  seed_freeze_helper.py set_freezes <uid> <count>
  seed_freeze_helper.py clear <uid>
  seed_freeze_helper.py seed_broken_streak <uid> <weeks_back_list,comma>  # days to seed per listed week start offset
  seed_freeze_helper.py cleanup <uid>
"""
import os, sys, uuid
from datetime import date, datetime, timedelta, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
cmd, uid, *rest = sys.argv[1:]

if cmd == "set_freezes":
    db.users.update_one({"user_id": uid}, {"$set": {"freezes": int(rest[0])}})
elif cmd == "clear":
    db.proofs.delete_many({"user_id": uid})
    db.freeze_weeks.delete_many({"user_id": uid})
    db.users.update_one({"user_id": uid}, {"$set": {"freezes": 0, "xp": 0}})
elif cmd == "seed_broken_streak":
    # Seed `n_back` prior consecutive completed weeks starting (n_back+1) weeks ago,
    # leaving LAST week missed. Target assumed 3 days/week.
    n_back = int(rest[0])
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    db.proofs.delete_many({"user_id": uid})
    db.freeze_weeks.delete_many({"user_id": uid})
    for w in range(2, 2 + n_back):  # weeks: last-2, last-3, ...
        wstart = monday - timedelta(days=7 * w)
        for i in range(3):
            d = wstart + timedelta(days=i)
            db.proofs.insert_one({"id": f"TEST_{uuid.uuid4()}", "user_id": uid, "local_date": d.isoformat(),
                                  "created_at": datetime.now(timezone.utc).isoformat(), "phash": None,
                                  "counted": True, "xp_awarded": 0, "status": "accepted"})
elif cmd == "cleanup":
    db.proofs.delete_many({"user_id": uid})
    db.freeze_weeks.delete_many({"user_id": uid})
    db.payments.delete_many({"user_id": uid})
    db.challenges.delete_many({"user_id": uid})
    db.users.delete_one({"user_id": uid})
print("ok")
