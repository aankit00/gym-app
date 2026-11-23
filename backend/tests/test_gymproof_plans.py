# GymProof Training Plans tests: /api/plans, /api/plans/{id}, /api/plans/{id}/start,
# /api/plans/active/stop, /api/exercises/{id}, payments gates, media URLs.
import os
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from test_gymproof_api import API, H, profile, token_for  # noqa: E402

load_dotenv("/app/backend/.env")
MONGO = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

PHONES = {
    "MALE": "+12015550175",
    "FEMALE": "+12015550176",
    "PRO": "+12015550177",
    "ACTIVE": "+12015550178",
    "REONBOARD": "+12015550179",
    "OTHER": "+12015550180",
}

CREATED_UIDS: set[str] = set()

FREE_PLANS = {"lean-machine", "mass-monster", "shred-mode", "prime-after-30",
              "peach-protocol", "burn-and-sculpt", "strong-not-skinny", "glow-after-30"}
PRO_PLANS = {"apex-athlete", "greek-god", "hourglass-code", "femme-athlete"}
ALL_PLANS = FREE_PLANS | PRO_PLANS


def onboard(phone: str, gender: str = "male") -> tuple[str, str]:
    tok = token_for(phone)
    body = profile(city=f"TEST_PLAN_{phone[-3:]}", name=f"TEST_{phone[-3:]}", target=3)
    body["gender"] = gender
    r = requests.post(f"{API}/me", headers=H(tok), json=body, timeout=15)
    assert r.status_code == 200, r.text
    uid = r.json()["profile"]["user_id"]
    CREATED_UIDS.add(uid)
    MONGO.users.update_one({"user_id": uid}, {"$set": {"plans_unlocked": False, "active_plan_id": None}})
    return tok, uid


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for uid in CREATED_UIDS:
        MONGO.users.delete_one({"user_id": uid})
        MONGO.proofs.delete_many({"user_id": uid})
        MONGO.freeze_weeks.delete_many({"user_id": uid})
        MONGO.payments.delete_many({"user_id": uid})
        MONGO.challenges.delete_many({"user_id": uid})


# ---------------- auth ----------------
def test_plans_require_auth():
    assert requests.get(f"{API}/plans", timeout=15).status_code == 401
    assert requests.get(f"{API}/plans/lean-machine", timeout=15).status_code == 401
    assert requests.post(f"{API}/plans/lean-machine/start", timeout=15).status_code == 401
    assert requests.post(f"{API}/plans/active/stop", timeout=15).status_code == 401
    assert requests.get(f"{API}/exercises/Barbell_Squat", timeout=15).status_code == 401


# ---------------- GET /api/plans ----------------
def test_list_plans_male_default():
    tok, _ = onboard(PHONES["MALE"], gender="male")
    r = requests.get(f"{API}/plans", headers=H(tok), timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    plans = data["plans"]
    assert len(plans) == 12
    assert sum(1 for p in plans if p["gender"] == "male") == 6
    assert sum(1 for p in plans if p["gender"] == "female") == 6
    assert data["default_gender"] == "male"
    assert data["pro"]["unlocked"] is False and data["pro"]["price_inr"] == 199
    assert data["pro"]["plan_count"] == 4 and isinstance(data["pro"]["payments_enabled"], bool)
    locked_ids = {p["id"] for p in plans if p["locked"]}
    assert locked_ids == PRO_PLANS
    all_ids = {p["id"] for p in plans}
    assert all_ids == ALL_PLANS


def test_list_plans_female_default():
    tok, _ = onboard(PHONES["FEMALE"], gender="female")
    r = requests.get(f"{API}/plans", headers=H(tok), timeout=15)
    data = r.json()
    assert data["default_gender"] == "female"


# ---------------- GET /api/plans/{id} ----------------
def test_free_plan_detail_has_exercises():
    tok, _ = onboard(PHONES["MALE"], gender="male")
    r = requests.get(f"{API}/plans/lean-machine", headers=H(tok), timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["id"] == "lean-machine" and d["locked"] is False
    assert len(d["days"]) >= 1
    day = d["days"][0]
    assert day["exercise_count"] == len(day["exercises"]) > 0
    e = day["exercises"][0]
    for k in ("id", "name", "sets", "reps", "rest_sec", "muscle", "equipment", "image", "level", "swapped", "original_id", "similar"):
        assert k in e, f"missing key {k} in exercise"
    assert isinstance(e["swapped"], bool)
    assert e["image"].startswith("http")


def test_pro_plan_locked_hides_exercises():
    tok, _ = onboard(PHONES["PRO"], gender="male")
    r = requests.get(f"{API}/plans/hourglass-code", headers=H(tok), timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["locked"] is True
    for day in d["days"]:
        assert day["exercise_count"] > 0
        assert day["exercises"] == []


def test_unknown_plan_404():
    tok, _ = onboard(PHONES["MALE"])
    r = requests.get(f"{API}/plans/nope-nope", headers=H(tok), timeout=15)
    assert r.status_code == 404


def test_unlocking_pro_in_mongo_reveals_exercises():
    tok, uid = onboard(PHONES["PRO"], gender="male")
    MONGO.users.update_one({"user_id": uid}, {"$set": {"plans_unlocked": True}})
    try:
        r = requests.get(f"{API}/plans/apex-athlete", headers=H(tok), timeout=15)
        d = r.json()
        assert d["locked"] is False
        assert d["days"][0]["exercises"] != []
    finally:
        MONGO.users.update_one({"user_id": uid}, {"$set": {"plans_unlocked": False}})


# ---------------- start / stop ----------------
def test_start_free_plan_updates_dashboard_not_target():
    tok, uid = onboard(PHONES["ACTIVE"], gender="female")
    before = requests.get(f"{API}/dashboard", headers=H(tok), params={"tz_offset_min": 0}, timeout=15).json()
    target_before = before["weekly_target"]
    r = requests.post(f"{API}/plans/peach-protocol/start", headers=H(tok), timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["active_plan_id"] == "peach-protocol"
    d = requests.get(f"{API}/dashboard", headers=H(tok), timeout=15).json()
    assert d["active_plan"] == {"id": "peach-protocol", "name": "Peach Protocol", "days_per_week": 4}
    assert d["weekly_target"] == target_before

    r = requests.post(f"{API}/plans/active/stop", headers=H(tok), timeout=15)
    assert r.status_code == 200 and r.json()["active_plan_id"] is None
    d = requests.get(f"{API}/dashboard", headers=H(tok), timeout=15).json()
    assert d["active_plan"] is None


def test_start_locked_pro_returns_403():
    tok, _ = onboard(PHONES["PRO"], gender="male")
    r = requests.post(f"{API}/plans/apex-athlete/start", headers=H(tok), timeout=15)
    assert r.status_code == 403


def test_reonboarding_preserves_plan_state():
    tok, uid = onboard(PHONES["REONBOARD"], gender="male")
    MONGO.users.update_one({"user_id": uid}, {"$set": {
        "xp": 555, "freezes": 2, "plans_unlocked": True, "active_plan_id": "apex-athlete"}})
    body = profile(city="TEST_PLAN_REO", name="TEST_REO_renamed", target=4)
    body["gender"] = "male"
    r = requests.post(f"{API}/me", headers=H(tok), json=body, timeout=15)
    assert r.status_code == 200
    row = MONGO.users.find_one({"user_id": uid})
    assert row["xp"] == 555
    assert row["freezes"] == 2
    assert row["plans_unlocked"] is True
    assert row["active_plan_id"] == "apex-athlete"
    assert row["weekly_target"] == 4
    assert row["name"] == "TEST_REO_renamed"


# ---------------- /api/exercises/{id} ----------------
def test_exercise_with_video():
    tok, _ = onboard(PHONES["MALE"])
    r = requests.get(f"{API}/exercises/ex_SAWOOH", headers=H(tok), timeout=15)  # WorkoutX id (cached media)
    assert r.status_code == 200
    d = r.json()
    assert d["video"] and d["poster"]
    assert isinstance(d.get("images"), list)


def test_exercise_with_two_photos_no_video():
    tok, _ = onboard(PHONES["MALE"])
    r = requests.get(f"{API}/exercises/Glute_Kickback", headers=H(tok), timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["video"] is None
    assert len(d["images"]) == 2


def test_exercise_unknown_404():
    tok, _ = onboard(PHONES["MALE"])
    r = requests.get(f"{API}/exercises/does_not_exist", headers=H(tok), timeout=15)
    assert r.status_code == 404


def test_every_plan_exercise_resolves():
    # import PLANS from the package
    import plans_data
    tok, _ = onboard(PHONES["MALE"])
    unresolved = []
    checked = set()
    for p in plans_data.PLANS:
        for day in p["days"]:
            for e in day["exercises"]:
                if e["id"] in checked:
                    continue
                checked.add(e["id"])
                r = requests.get(f"{API}/exercises/{e['id']}", headers=H(tok), timeout=15)
                if r.status_code != 200:
                    unresolved.append((p["id"], e["id"], r.status_code))
    assert not unresolved, f"unresolved exercises: {unresolved[:5]} (total {len(unresolved)})"


def test_media_urls_reachable():
    import plans_data
    images, videos = [], []
    for ex in plans_data.EXERCISES.values():
        if ex.get("images"):
            images.append(ex["images"][0])
        if ex.get("video"):
            videos.append(ex["video"])
    # 5 images, 3 videos: spot check only
    sample_imgs = images[:5]
    sample_vids = videos[:3]
    bad = []
    for u in sample_imgs + sample_vids:
        try:
            r = requests.head(u, timeout=15, allow_redirects=True)
            if r.status_code >= 400:
                # some CDNs block HEAD; try GET with Range
                r = requests.get(u, timeout=15, headers={"Range": "bytes=0-1023"}, stream=True)
            if r.status_code >= 400:
                bad.append((u, r.status_code))
        except Exception as exc:
            bad.append((u, str(exc)))
    assert not bad, f"bad media urls: {bad}"
