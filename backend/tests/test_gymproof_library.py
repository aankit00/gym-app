# GymProof WorkoutX library tests: /api/library, /api/exercises/{id}, /api/exercises/{id}/alternatives,
# per-user plan swaps PUT/DELETE /api/plans/{plan}/days/{day}/exercises/{index}.
# NOTE: only reads cached WorkoutX media (no forced refreshes) - every detail call here is served from wx_media.
import os
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from test_gymproof_api import API, H, profile, token_for  # noqa: E402

load_dotenv("/app/backend/.env")
MONGO = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

PHONE_A, PHONE_B = "+12015550185", "+12015550186"
UIDS: list[str] = []
PLAN = "lean-machine"


def onboard(phone, gender):
    tok = token_for(phone)
    body = profile(city=f"TEST_LIB_{phone[-3:]}", name=f"TEST_LIB_{phone[-3:]}")
    body["gender"] = gender
    r = requests.post(f"{API}/me", headers=H(tok), json=body, timeout=15)
    assert r.status_code == 200, r.text
    uid = r.json()["profile"]["user_id"]
    UIDS.append(uid)
    MONGO.users.update_one({"user_id": uid}, {"$set": {"plans_unlocked": False}})
    return tok, uid


@pytest.fixture(scope="module")
def users():
    a = onboard(PHONE_A, "male")
    b = onboard(PHONE_B, "female")
    yield a, b
    for uid in UIDS:
        MONGO.plan_swaps.delete_many({"user_id": uid})
        MONGO.users.delete_one({"user_id": uid})


@pytest.fixture(scope="module")
def ta(users):
    return users[0][0]


@pytest.fixture(scope="module")
def tb(users):
    return users[1][0]


def plan(tok, pid=PLAN):
    r = requests.get(f"{API}/plans/{pid}", headers=H(tok), timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- auth ----------
def test_library_requires_auth():
    assert requests.get(f"{API}/library", timeout=15).status_code == 401
    assert requests.get(f"{API}/exercises/ex_SAWOOH/alternatives", timeout=15).status_code == 401
    assert requests.put(f"{API}/plans/{PLAN}/days/1/exercises/0", json={"exercise_id": "ex_SAWOOH"}, timeout=15).status_code == 401


# ---------- library ----------
def test_library_shape(ta):
    r = requests.get(f"{API}/library", headers=H(ta), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert 1850 <= len(d["items"]) <= 1950, len(d["items"])
    keys = {"id", "name", "level", "group", "target", "equipment", "thumb"}
    assert all(keys <= set(i) for i in d["items"])
    assert {i["level"] for i in d["items"]} <= {"beginner", "intermediate", "pro"}
    assert len({i["id"] for i in d["items"]}) == len(d["items"])
    assert set(d["groups"]) >= {"Chest", "Back", "Legs", "Core"}
    assert len(d["equipment"]) > 3
    no_thumb = sum(1 for i in d["items"] if not i["thumb"])
    assert no_thumb < 50, f"{no_thumb} items without thumb"


# ---------- exercise detail ----------
def test_detail_workoutx_male_female(ta):
    m = requests.get(f"{API}/exercises/ex_SAWOOH?model=male", headers=H(ta), timeout=20).json()
    assert m["id"] == "ex_SAWOOH" and m["canonical_id"] == "ex_SAWOOH" and m["model"] == "male"
    assert m["video"] and m["poster"] and m["source"] == "workoutx" and m["similar"] is False
    assert set(m["models"]) == {"male", "female"}
    f = requests.get(f"{API}/exercises/ex_SAWOOH?model=female", headers=H(ta), timeout=20).json()
    assert f["model"] == "female" and f["id"] == m["models"]["female"] and f["canonical_id"] == "ex_SAWOOH"
    assert f["video"] and f["video"] != m["video"]


def test_detail_female_id_canonicalises(ta):
    r = requests.get(f"{API}/exercises/ex_HYOSAB", headers=H(ta), timeout=20).json()  # male user, no model
    assert r["canonical_id"] == "ex_SAWOOH"


def test_detail_bad_model_422(ta):
    assert requests.get(f"{API}/exercises/ex_SAWOOH?model=robot", headers=H(ta), timeout=15).status_code == 422


def test_detail_photo_only(ta):
    r = requests.get(f"{API}/exercises/Wind_Sprints", headers=H(ta), timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert d["similar"] is True and d["video"] is None and len(d["images"]) >= 1 and d["models"] == {}


# iteration_4: free-exercise-db plan ids resolve through PLAN_MATCH to the WorkoutX version (cached media)
def test_detail_plan_id_resolves_to_workoutx(ta):
    r = requests.get(f"{API}/exercises/Barbell_Squat", headers=H(ta), timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["source"] == "workoutx" and d["video"] and d["poster"]
    assert d["canonical_id"].startswith("ex_") and d["similar"] is False


def test_detail_unknown_404(ta):
    assert requests.get(f"{API}/exercises/ex_NOPE_123", headers=H(ta), timeout=15).status_code == 404


# ---------- alternatives ----------
@pytest.mark.parametrize("ex_id", ["ex_SAWOOH", "Wind_Sprints", "Landmine_180s"])
def test_alternatives(ta, ex_id):
    r = requests.get(f"{API}/exercises/{ex_id}/alternatives?plan_id={PLAN}", headers=H(ta), timeout=20)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert 5 <= len(items) <= 6, len(items)
    ids = [i["id"] for i in items]
    assert ex_id not in ids and len(set(ids)) == len(ids)
    if ex_id == "ex_SAWOOH":
        assert "ex_HYOSAB" not in ids


def test_alternatives_unknown(ta):
    assert requests.get(f"{API}/exercises/nope/alternatives", headers=H(ta), timeout=15).status_code == 404
    assert requests.get(f"{API}/exercises/ex_SAWOOH/alternatives?plan_id=nope", headers=H(ta), timeout=15).status_code == 404


def test_every_plan_move_has_alternatives(ta):
    p = plan(ta)
    for d in p["days"]:
        for e in d["exercises"]:
            items = requests.get(f"{API}/exercises/{e['id']}/alternatives?plan_id={PLAN}", headers=H(ta), timeout=20).json()["items"]
            assert 5 <= len(items) <= 6 and e["id"] not in [i["id"] for i in items], e["id"]


# ---------- swaps ----------
def test_swap_flow_and_per_user(ta, tb):
    p = plan(ta)
    day = p["days"][0]["day"]
    row = p["days"][0]["exercises"][0]
    assert row["swapped"] is False and row["id"] == row["original_id"] and row["level"] in ("beginner", "intermediate", "pro")
    alt = requests.get(f"{API}/exercises/{row['id']}/alternatives?plan_id={PLAN}", headers=H(ta), timeout=20).json()["items"][0]
    url = f"{API}/plans/{PLAN}/days/{day}/exercises/0"
    r = requests.put(url, headers=H(ta), json={"exercise_id": alt["id"]}, timeout=15)
    assert r.status_code == 200 and r.json() == {"exercise_id": alt["id"], "swapped": True}
    row2 = plan(ta)["days"][0]["exercises"][0]
    assert row2["swapped"] is True and row2["id"] == alt["id"] and row2["original_id"] == row["original_id"]
    assert row2["name"] == alt["name"] and row2["sets"] == row["sets"]
    # other user doesn't see it
    other = plan(tb)["days"][0]["exercises"][0]
    assert other["swapped"] is False and other["id"] == row["original_id"]
    # DELETE resets
    r = requests.delete(url, headers=H(ta), timeout=15)
    assert r.status_code == 200 and r.json()["swapped"] is False and r.json()["exercise_id"] == row["original_id"]
    row3 = plan(ta)["days"][0]["exercises"][0]
    assert row3["swapped"] is False and row3["id"] == row["original_id"]


def test_swap_female_variant_stored_canonical(ta):
    p = plan(ta)
    day = p["days"][0]["day"]
    url = f"{API}/plans/{PLAN}/days/{day}/exercises/1"
    r = requests.put(url, headers=H(ta), json={"exercise_id": "ex_HYOSAB"}, timeout=15)
    assert r.status_code == 200 and r.json()["exercise_id"] == "ex_SAWOOH"
    requests.delete(url, headers=H(ta), timeout=15)


def test_swap_with_original_removes_swap(ta):
    p = plan(ta)
    day = p["days"][1]["day"]
    row = p["days"][1]["exercises"][0]
    url = f"{API}/plans/{PLAN}/days/{day}/exercises/0"
    alt = requests.get(f"{API}/exercises/{row['id']}/alternatives?plan_id={PLAN}", headers=H(ta), timeout=20).json()["items"][1]
    assert requests.put(url, headers=H(ta), json={"exercise_id": alt["id"]}, timeout=15).json()["swapped"] is True
    r = requests.put(url, headers=H(ta), json={"exercise_id": row["original_id"]}, timeout=15)
    assert r.status_code == 200 and r.json()["swapped"] is False
    assert plan(ta)["days"][1]["exercises"][0]["swapped"] is False
    assert MONGO.plan_swaps.count_documents({"user_id": UIDS[0], "plan_id": PLAN, "day": day, "index": 0}) == 0


def test_swap_photo_exercise_allowed(ta):
    p = plan(ta)
    day = p["days"][0]["day"]
    url = f"{API}/plans/{PLAN}/days/{day}/exercises/2"
    r = requests.put(url, headers=H(ta), json={"exercise_id": "Wind_Sprints"}, timeout=15)
    assert r.status_code == 200 and r.json()["swapped"] is True
    row = plan(ta)["days"][0]["exercises"][2]
    assert row["similar"] is True and row["id"] == "Wind_Sprints"
    requests.delete(url, headers=H(ta), timeout=15)


def test_swap_errors(ta):
    day = plan(ta)["days"][0]["day"]
    base = f"{API}/plans/{PLAN}/days/{day}/exercises"
    assert requests.put(f"{base}/99", headers=H(ta), json={"exercise_id": "ex_SAWOOH"}, timeout=15).status_code == 404
    assert requests.put(f"{base}/-1", headers=H(ta), json={"exercise_id": "ex_SAWOOH"}, timeout=15).status_code == 404
    assert requests.put(f"{API}/plans/{PLAN}/days/99/exercises/0", headers=H(ta), json={"exercise_id": "ex_SAWOOH"}, timeout=15).status_code == 404
    assert requests.put(f"{base}/0", headers=H(ta), json={"exercise_id": "nope"}, timeout=15).status_code == 404
    assert requests.put(f"{base}/0", headers=H(ta), json={}, timeout=15).status_code == 422
    assert requests.put(f"{API}/plans/nope/days/1/exercises/0", headers=H(ta), json={"exercise_id": "ex_SAWOOH"}, timeout=15).status_code == 404
    assert requests.delete(f"{base}/99", headers=H(ta), timeout=15).status_code == 404


def test_swap_locked_pro_403(ta):
    p = plan(ta, "apex-athlete")
    assert p["locked"] is True and all(d["exercises"] == [] for d in p["days"])
    day = p["days"][0]["day"]
    url = f"{API}/plans/apex-athlete/days/{day}/exercises/0"
    assert requests.put(url, headers=H(ta), json={"exercise_id": "ex_SAWOOH"}, timeout=15).status_code == 403
    assert requests.delete(url, headers=H(ta), timeout=15).status_code == 403


def test_no_leftover_swaps(users):
    assert MONGO.plan_swaps.count_documents({"user_id": {"$in": UIDS}}) == 0
