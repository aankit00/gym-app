# GymProof iteration 5: email auth (register/login/lockout), Google session, auth isolation, recap,
# photo-check rate limit, tz validation, CORS allowlist
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import jwt
import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")  # only for MONGO_URL/DB_NAME (never printed)
BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api"
HERE = Path(__file__).parent
PHONE = "+12015550163"
RUN = uuid.uuid4().hex[:8]
EMAIL_A = f"test_a_{RUN}@example.com"
EMAIL_LOCK = f"test_lock_{RUN}@example.com"
PW = "TEST_pass_1234"
S: dict = {}


@pytest.fixture(scope="module")
def mdb():
    c = MongoClient(os.environ["MONGO_URL"])
    yield c[os.environ["DB_NAME"]]
    c.close()


@pytest.fixture(scope="module", autouse=True)
def cleanup(mdb):
    yield
    for uid in S.get("uids", []):
        mdb.users.delete_many({"user_id": uid})
        mdb.auth_accounts.delete_many({"user_id": uid})
        mdb.ai_checks.delete_many({"user_id": uid})
        mdb.challenges.delete_many({"user_id": uid})
        mdb.proofs.delete_many({"user_id": uid})
    for e in (EMAIL_A, EMAIL_LOCK):
        mdb.auth_attempts.delete_many({"_id": f"email:{e}"})


def H(t):
    return {"Authorization": f"Bearer {t}"}


def profile(name="TEST_Email", city="TEST_Recapcity"):
    return {"name": name, "age": 30, "height_cm": 175, "gender": "male", "goal": "strength",
            "weekly_target": 3, "city": city, "tz_offset_min": 330}


# ---------- register ----------
def test_register_ok():
    r = requests.post(f"{API}/auth/register", json={"email": EMAIL_A, "password": PW})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["account"]["provider"] == "email" and d["account"]["email"] == EMAIL_A
    assert d["account"]["user_id"].startswith("email_")
    assert "password_hash" not in d["account"]
    assert jwt.get_unverified_header(d["token"])["alg"] == "HS256"
    S["tok"], S["uid"] = d["token"], d["account"]["user_id"]
    S.setdefault("uids", []).append(S["uid"])


def test_register_duplicate_409():
    r = requests.post(f"{API}/auth/register", json={"email": EMAIL_A.upper(), "password": PW})
    assert r.status_code == 409, r.text


@pytest.mark.parametrize("body", [{"email": "notanemail", "password": PW}, {"email": f"x{RUN}@example.com", "password": "short"}])
def test_register_invalid_422(body):
    assert requests.post(f"{API}/auth/register", json=body).status_code == 422


# ---------- login ----------
def test_login_ok_and_wrong_pw():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL_A, "password": PW})
    assert r.status_code == 200 and r.json()["account"]["user_id"] == S["uid"]
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL_A, "password": "WRONG_pass_99"})
    assert r.status_code == 401


def test_login_lockout_after_5(mdb):
    codes = [requests.post(f"{API}/auth/login", json={"email": EMAIL_LOCK, "password": "WRONG_pass_99"}).status_code for _ in range(6)]
    print("lockout codes", codes)
    assert codes[:5] == [401] * 5 and codes[5] == 429
    # Does the per-IP key lock OTHER users? (behind ingress all clients share one IP)
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL_A, "password": PW})
    S["other_user_after_lock"] = r.status_code
    ip_keys = [d["_id"] for d in mdb.auth_attempts.find({"_id": {"$regex": "^ip:"}}, {"_id": 1})]
    print("ip keys:", ip_keys, "other user login status:", r.status_code)
    # clean our ip lock so other testers are not blocked
    mdb.auth_attempts.delete_many({"_id": {"$in": ip_keys}})
    mdb.auth_attempts.delete_many({"_id": f"email:{EMAIL_LOCK}"})
    assert r.status_code == 200, "a different user's correct login was blocked by per-IP lockout (shared ingress IP)"


# ---------- token usage / isolation ----------
def test_email_token_me_not_onboarded():
    r = requests.get(f"{API}/me", headers=H(S["tok"]))
    assert r.status_code == 200
    d = r.json()
    assert d["onboarded"] is False and d["account"]["provider"] == "email" and d["account"]["email"] == EMAIL_A


def test_email_onboard_and_dashboard():
    r = requests.post(f"{API}/me", json=profile(), headers=H(S["tok"]))
    assert r.status_code == 200 and r.json()["profile"]["user_id"] == S["uid"]
    r = requests.get(f"{API}/dashboard", headers=H(S["tok"]))
    assert r.status_code == 200 and r.json()["name"] == "TEST_Email"


@pytest.mark.parametrize("tok", ["garbage", "a.b.c", "TAMPER", "FORGED"])
def test_bad_tokens_401(tok):
    if tok == "TAMPER":
        tok = S["tok"][:-3] + ("aaa" if not S["tok"].endswith("aaa") else "bbb")
    if tok == "FORGED":
        tok = jwt.encode({"sub": S["uid"], "provider": "email", "iss": "gymproof-api", "aud": "gymproof-app",
                          "iat": 1, "exp": 9999999999}, "wrong-secret", algorithm="HS256")
    assert requests.get(f"{API}/me", headers=H(tok)).status_code == 401
    assert requests.get(f"{API}/me").status_code == 401


def test_phone_token_still_works_and_isolated():
    out = subprocess.run([sys.executable, str(HERE / "clerk_token.py"), PHONE], capture_output=True, text=True, timeout=60)
    tok = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    if not tok:
        pytest.skip("no clerk token")
    r = requests.get(f"{API}/me", headers=H(tok))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["account"] is None
    if d["profile"]:
        assert d["profile"]["user_id"] != S["uid"] and d["profile"]["user_id"].startswith("user_")
    # email user sees only own profile
    assert requests.get(f"{API}/me", headers=H(S["tok"])).json()["profile"]["user_id"] == S["uid"]


def test_cookie_fallback_removed():
    out = subprocess.run([sys.executable, str(HERE / "clerk_token.py"), PHONE], capture_output=True, text=True, timeout=60)
    tok = out.stdout.strip().splitlines()[-1]
    assert requests.get(f"{API}/me", cookies={"__session": tok}).status_code == 401


# ---------- google / logout ----------
def test_google_bogus_session_401():
    r = requests.post(f"{API}/auth/session", json={"session_id": "bogus_" + RUN})
    assert r.status_code == 401, r.text


def test_logout_ok():
    r = requests.post(f"{API}/auth/logout", headers=H(S["tok"]))
    assert r.status_code == 200 and r.json() == {"ok": True}


# ---------- recap ----------
def test_recap_current_and_explicit():
    r = requests.get(f"{API}/recap", headers=H(S["tok"]))
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("visits", "xp", "consistency", "weeks_hit", "weeks_total", "active_days", "label", "month"):
        assert k in d
    assert d["visits"] == 0 and d["xp"] == 0 and isinstance(d["active_days"], list)
    S["month"] = d["month"]
    r2 = requests.get(f"{API}/recap", params={"month": "2025-06"}, headers=H(S["tok"]))
    assert r2.status_code == 200 and r2.json()["label"] == "June 2025" and r2.json()["days_in_month"] == 30


def test_recap_future_and_bad():
    assert requests.get(f"{API}/recap", params={"month": "2099-01"}, headers=H(S["tok"])).status_code == 400
    for bad in ("2026-13", "2026-1", "abc"):
        assert requests.get(f"{API}/recap", params={"month": bad}, headers=H(S["tok"])).status_code == 422


# ---------- rate limit ----------
def test_photo_budget_429(mdb):
    r = requests.post(f"{API}/proof/challenge", headers=H(S["tok"]))
    assert r.status_code == 200, r.text
    mdb.ai_checks.insert_many([{"user_id": S["uid"], "at": datetime.now(timezone.utc)} for _ in range(5)])
    r = requests.post(f"{API}/proof/challenge", headers=H(S["tok"]))
    assert r.status_code == 429, r.text


# ---------- tz validation ----------
def test_tz_validation():
    assert requests.get(f"{API}/dashboard", params={"tz_offset_min": 5000}, headers=H(S["tok"])).status_code == 422
    assert requests.patch(f"{API}/me", json={"tz_offset_min": -800}, headers=H(S["tok"])).status_code == 422
    assert requests.patch(f"{API}/me", json={"tz_offset_min": 840}, headers=H(S["tok"])).status_code == 200


# ---------- CORS ----------
def test_cors():
    r = requests.options(f"{API}/me", headers={"Origin": "https://evil.com", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}
    # NOTE: on simple GETs the preview ingress (not the app) adds 'access-control-allow-origin: *';
    # the app's own CORS is checked via preflight, which the ingress forwards to FastAPI.
    r = requests.options(f"{API}/me", headers={"Origin": "https://x.preview.emergentagent.com.evil.com",
                                                "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}
    r = requests.options(f"{API}/me", headers={"Origin": BASE_URL, "Access-Control-Request-Method": "GET",
                                                "Access-Control-Request-Headers": "authorization"})
    assert r.headers.get("access-control-allow-origin") == BASE_URL
    assert r.headers.get("access-control-allow-credentials") is None
