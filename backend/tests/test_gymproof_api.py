# GymProof backend regression tests: profile, dashboard, proof anti-cheat + AI, proofs list, leaderboard
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api"
HERE = Path(__file__).parent
FIX = HERE / "fixtures"

PHONE_A = "+12015550160"
PHONE_B = "+12015550161"
PHONE_C = "+12015550162"
STATE: dict = {}


def token_for(phone: str) -> str:
    out = subprocess.run([sys.executable, str(HERE / "clerk_token.py"), phone], capture_output=True, text=True, timeout=60)
    tok = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    if not tok:
        pytest.skip(f"could not mint Clerk token: {out.stderr[-300:]}")
    return tok


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def profile(city="TEST_Pune", name="TEST_Alice", target=3):
    return {"name": name, "age": 28, "height_cm": 170, "gender": "female", "goal": "strength",
            "weekly_target": target, "city": city, "tz_offset_min": 0}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def submit(tok, img_path, challenge_id=None, captured_at=None):
    if challenge_id is None:
        r = requests.post(f"{API}/proof/challenge", headers=H(tok), timeout=30)
        assert r.status_code == 200, r.text
        challenge_id = r.json()["challenge_id"]
    with open(img_path, "rb") as f:
        return requests.post(f"{API}/proof/submit", headers=H(tok),
                             data={"challenge_id": challenge_id, "captured_at": captured_at or now_iso()},
                             files={"image": ("p.jpg", f, "image/jpeg")}, timeout=120), challenge_id


@pytest.fixture(scope="module")
def toks():
    t = {"A": token_for(PHONE_A), "B": token_for(PHONE_B), "C": token_for(PHONE_C)}
    yield t
    # cleanup only our TEST users' data by user_id
    from pymongo import MongoClient
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    for uid in STATE.get("uids", []):
        db.users.delete_one({"user_id": uid})
        db.proofs.delete_many({"user_id": uid})
        db.challenges.delete_many({"user_id": uid})


# --- Auth / profile ---
def test_me_requires_auth():
    assert requests.get(f"{API}/me", timeout=15).status_code == 401
    assert requests.get(f"{API}/me", headers={"Authorization": "Bearer garbage"}, timeout=15).status_code == 401


def test_me_not_onboarded_then_onboarded(toks):
    r = requests.get(f"{API}/me", headers=H(toks["A"]), timeout=15)
    assert r.status_code == 200
    assert r.json() == {"onboarded": False, "profile": None}, r.json()
    STATE["uids"] = []
    for k, city, name in [("A", "TEST_Pune", "TEST_Alice"), ("B", "test_pune ", "TEST_Bob"), ("C", "TEST_Delhi", "TEST_Carl")]:
        r = requests.post(f"{API}/me", headers=H(toks[k]), json=profile(city=city, name=name), timeout=15)
        assert r.status_code == 200, r.text
        STATE["uids"].append(r.json()["profile"]["user_id"])
    r = requests.get(f"{API}/me", headers=H(toks["A"]), timeout=15).json()
    assert r["onboarded"] is True and r["profile"]["name"] == "TEST_Alice" and r["profile"]["xp"] == 0
    assert "_id" not in r["profile"]


@pytest.mark.parametrize("field,val", [("age", 12), ("age", 101), ("height_cm", 99), ("height_cm", 251),
                                       ("weekly_target", 1), ("weekly_target", 6), ("gender", "robot"), ("goal", "bulk")])
def test_me_validation(toks, field, val):
    body = profile(); body[field] = val
    assert requests.post(f"{API}/me", headers=H(toks["A"]), json=body, timeout=15).status_code == 422


def test_patch_weekly_target(toks):
    r = requests.patch(f"{API}/me", headers=H(toks["A"]), json={"weekly_target": 2}, timeout=15)
    assert r.status_code == 200 and r.json()["profile"]["weekly_target"] == 2
    assert requests.patch(f"{API}/me", headers=H(toks["A"]), json={"weekly_target": 7}, timeout=15).status_code == 422
    assert requests.get(f"{API}/me", headers=H(toks["A"]), timeout=15).json()["profile"]["weekly_target"] == 2


def test_dashboard_shape(toks):
    r = requests.get(f"{API}/dashboard", headers=H(toks["A"]), params={"tz_offset_min": 0}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["streak_weeks"] == 0 and d["widget_state"] == "pending" and d["xp"] == 0 and d["level"] == 1
    assert len(d["week_days"]) == 7 and d["week_days"][0]["label"] == "Mon" and d["week_days"][6]["label"] == "Sun"
    assert sum(1 for w in d["week_days"] if w["is_today"]) == 1
    assert [m["weeks"] for m in d["milestones"]] == [4, 8, 12, 26]
    assert len(d["achievements"]) == 5 and not any(a["unlocked"] for a in d["achievements"])


# --- Proof anti-cheat ---
def test_challenge_requires_profile():
    assert requests.post(f"{API}/proof/challenge", timeout=15).status_code == 401


def test_wrong_user_challenge_rejected(toks):
    ch = requests.post(f"{API}/proof/challenge", headers=H(toks["B"]), timeout=15).json()["challenge_id"]
    r, _ = submit(toks["A"], FIX / "landscape.jpg", challenge_id=ch)
    assert r.status_code == 400, r.text


def test_captured_at_outside_window(toks):
    old = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    r, _ = submit(toks["A"], FIX / "landscape.jpg", captured_at=old)
    assert r.status_code == 400 and "Capture time" in r.json()["detail"]
    future = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    r, _ = submit(toks["A"], FIX / "landscape.jpg", captured_at=future)
    assert r.status_code == 400
    r, _ = submit(toks["A"], FIX / "landscape.jpg", captured_at="not-a-date")
    assert r.status_code == 400


def test_no_hand_rejected_and_challenge_single_use(toks):
    r, ch = submit(toks["A"], FIX / "landscape.jpg")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] == "rejected" and j["counted"] is False and j["xp_awarded"] == 0, j
    r2, _ = submit(toks["A"], FIX / "dumbbell.jpg", challenge_id=ch)
    assert r2.status_code == 400


def test_duplicate_image_suspicious(toks):
    r, _ = submit(toks["A"], FIX / "landscape.jpg")
    assert r.status_code == 200 and r.json()["status"] == "suspicious", r.text


def test_real_dumbbell_accepted_counted(toks):
    r, _ = submit(toks["A"], FIX / "dumbbell.jpg")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] == "accepted" and j["counted"] is True and j["xp_awarded"] == 100, j
    assert "phash" not in j and "user_id" not in j
    d = requests.get(f"{API}/dashboard", headers=H(toks["A"]), timeout=15).json()
    assert d["xp"] == 100 and d["today_done"] is True and d["widget_state"] == "completed" and d["week_count"] == 1


def test_second_accept_same_day_not_counted(toks):
    r, _ = submit(toks["A"], FIX / "dumbbell_mirror.jpg")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] == "accepted", j
    assert j.get("already_counted_today") is True and j["counted"] is False and j["xp_awarded"] == 0
    assert requests.get(f"{API}/dashboard", headers=H(toks["A"]), timeout=15).json()["xp"] == 100


def test_list_proofs(toks):
    r = requests.get(f"{API}/proofs", headers=H(toks["A"]), timeout=15)
    assert r.status_code == 200
    p = r.json()
    assert len(p) >= 4 and all("phash" not in x and "_id" not in x for x in p)
    assert sum(1 for x in p if x["counted"]) == 1
    assert {x["status"] for x in p} >= {"rejected", "suspicious", "accepted"}


# --- Leaderboard ---
def test_leaderboard_city_isolation(toks):
    r = requests.get(f"{API}/leaderboard", headers=H(toks["A"]), params={"scope": "city"}, timeout=15).json()
    names = [e["name"] for e in r["entries"]]
    assert "TEST_Alice" in names and "TEST_Bob" in names and "TEST_Carl" not in names, names
    assert r["my_rank"] == 1 and r["entries"][0]["is_me"] is True and r["total"] == 2
    rb = requests.get(f"{API}/leaderboard", headers=H(toks["B"]), params={"scope": "city"}, timeout=15).json()
    assert rb["my_rank"] == 2 and [e for e in rb["entries"] if e["is_me"]][0]["name"] == "TEST_Bob"
    rc = requests.get(f"{API}/leaderboard", headers=H(toks["C"]), params={"scope": "city"}, timeout=15).json()
    assert [e["name"] for e in rc["entries"]] == ["TEST_Carl"]


def test_leaderboard_all_and_bad_scope(toks):
    r = requests.get(f"{API}/leaderboard", headers=H(toks["C"]), params={"scope": "all"}, timeout=15).json()
    names = [e["name"] for e in r["entries"]]
    assert "TEST_Alice" in names and "TEST_Carl" in names
    assert requests.get(f"{API}/leaderboard", headers=H(toks["C"]), params={"scope": "x"}, timeout=15).status_code == 422
