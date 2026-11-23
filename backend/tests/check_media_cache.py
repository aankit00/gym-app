# Helper: print the WorkoutX match for a plan id and whether its cached media is still fresh (no API calls).
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
import library  # noqa: E402
from pymongo import MongoClient  # noqa: E402

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
for pid in sys.argv[1:]:
    m = library.PLAN_MATCH.get(pid)
    print(pid, "->", m)
    for doc in db.wx_media.find({"$or": [{"id": m}, {"_id": m}, {"exercise_id": m}]}, {"_id": 0}).limit(3):
        exp = doc.get("expires_at")
        print("  keys:", list(doc.keys()), "expires_at:", exp, "now:", datetime.now(timezone.utc))
