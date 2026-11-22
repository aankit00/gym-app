# GymProof backend: weekly bonus (+250 XP), week_completed widget state and weekly streak math
import os
import uuid
from datetime import datetime, timedelta, timezone, date

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

from test_gymproof_api import API, FIX, H, profile, submit, token_for

PHONE = "+12015550163"


@pytest.fixture(scope="module")
def ctx():
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    tok = token_for(PHONE)
    r = requests.post(f"{API}/me", headers=H(tok), json=profile(city="TEST_Bonus", name="TEST_Bonus", target=3), timeout=15)
    assert r.status_code == 200
    uid = r.json()["profile"]["user_id"]
    yield {"db": db, "tok": tok, "uid": uid}
    db.users.delete_one({"user_id": uid}); db.proofs.delete_many({"user_id": uid}); db.challenges.delete_many({"user_id": uid})


def seed_counted(db, uid, d: date):
    db.proofs.insert_one({"id": f"TEST_{uuid.uuid4()}", "user_id": uid, "local_date": d.isoformat(),
                          "created_at": datetime.now(timezone.utc).isoformat(), "phash": None, "counted": True,
                          "xp_awarded": 0, "status": "accepted"})


def test_week_bonus_and_streak(ctx):
    db, uid, tok = ctx["db"], ctx["uid"], ctx["tok"]
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    others = [monday + timedelta(days=i) for i in range(7) if monday + timedelta(days=i) != today][:2]
    for d in others:
        seed_counted(db, uid, d)
    # previous week fully completed -> streak should become 2 after this week completes
    for i in range(3):
        seed_counted(db, uid, monday - timedelta(days=7 - i))
    d0 = requests.get(f"{API}/dashboard", headers=H(tok), params={"tz_offset_min": 0}, timeout=15).json()
    assert d0["streak_weeks"] == 1 and d0["week_count"] == 2 and d0["widget_state"] == "pending", d0
    r, _ = submit(tok, FIX / "dumbbell_crop.jpg")
    j = r.json()
    assert j["status"] == "accepted", j
    assert j["xp_awarded"] == 350 and j.get("week_completed_now") is True, j
    d = requests.get(f"{API}/dashboard", headers=H(tok), timeout=15).json()
    assert d["widget_state"] == "week_completed" and d["streak_weeks"] == 2 and d["best_streak"] == 2, d
    assert d["xp"] == 350 and d["remaining"] == 0
    ach = {a["id"]: a["unlocked"] for a in d["achievements"]}
    assert ach["first_proof"] and ach["first_week"] and not ach["first_month"]
