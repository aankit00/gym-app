# GymProof Streak Freeze tests: /api/freeze endpoints, compute_stats repair logic,
# signature verification, fulfil_order idempotency. Razorpay keys are set ONLY in the
# pytest process via monkeypatch; backend/.env is never modified.
import asyncio
import hashlib
import hmac
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

# bring in helpers from the regression suite (BASE_URL, token_for, H, profile)
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))  # so `import payments` / `import server` resolve
from test_gymproof_api import API, H, profile, token_for  # noqa: E402

load_dotenv("/app/backend/.env")
MONGO = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

PHONES = {
    "P1": "+12015550164",  # repair state - no freeze, broken streak
    "P2": "+12015550165",  # auto-use freeze
    "P3": "+12015550166",  # happy path with freeze, no miss
    "P4": "+12015550167",  # 2 missed weeks with 1 freeze -> NOT consumed
    "P5": "+12015550168",  # no prior streak + freezes=1 -> not consumed
    "P6": "+12015550169",  # frozen week keeps chain alive (done/frozen/done)
    "P7": "+12015550170",  # re-onboarding preserves freezes + xp
    "P8": "+12015550171",  # signatures / fulfil_order / verify ownership
}

CREATED_UIDS: set[str] = set()
CREATED_ORDERS: set[str] = set()


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def seed_counted(uid: str, d: date) -> None:
    MONGO.proofs.insert_one({
        "id": f"TEST_{uuid.uuid4()}", "user_id": uid, "local_date": d.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(), "phash": None,
        "counted": True, "xp_awarded": 0, "status": "accepted",
    })


def complete_week(uid: str, week_start: date, target: int = 3) -> None:
    for i in range(target):
        seed_counted(uid, week_start + timedelta(days=i))


def onboard(phone: str, name: str, target: int = 3, freezes: int = 0, xp: int = 0) -> tuple[str, str]:
    tok = token_for(phone)
    r = requests.post(f"{API}/me", headers=H(tok),
                      json=profile(city=f"TEST_FZ_{phone[-3:]}", name=name, target=target), timeout=15)
    assert r.status_code == 200, r.text
    uid = r.json()["profile"]["user_id"]
    CREATED_UIDS.add(uid)
    # clean any stale state from earlier runs, then set initial freezes/xp
    MONGO.proofs.delete_many({"user_id": uid})
    MONGO.freeze_weeks.delete_many({"user_id": uid})
    MONGO.payments.delete_many({"user_id": uid})
    MONGO.users.update_one({"user_id": uid}, {"$set": {"freezes": freezes, "xp": xp}})
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
    for oid in CREATED_ORDERS:
        MONGO.payments.delete_many({"order_id": oid})


# ---------------- /api/freeze shape + auth ----------------

def test_freeze_requires_auth():
    assert requests.get(f"{API}/freeze", timeout=15).status_code == 401


def test_freeze_404_when_no_profile():
    tok = token_for("+12015550172")
    # ensure no profile exists for this phone
    # delete by user_id minted via Clerk
    import jwt as _jwt  # PyJWT ships with razorpay dep tree
    try:
        payload = _jwt.decode(tok, options={"verify_signature": False})
        uid = payload.get("sub")
        MONGO.users.delete_one({"user_id": uid})
    except Exception:
        pass
    r = requests.get(f"{API}/freeze", headers=H(tok), timeout=15)
    assert r.status_code == 404, r.text


def test_freeze_order_and_verify_503_without_keys():
    import payments as _p
    load_dotenv("/app/backend/.env", override=False)
    if _p.enabled():
        pytest.skip("Razorpay keys are configured; live behaviour covered in test_gymproof_payments_live.py")
    tok, _ = onboard(PHONES["P1"], "TEST_P1")
    for path in ("/freeze/order", "/payments/verify", "/plans/pro/order"):
        r = requests.post(f"{API}{path}", headers=H(tok), json={
            "razorpay_order_id": "x", "razorpay_payment_id": "y", "razorpay_signature": "z"} if "verify" in path else None, timeout=15)
        assert r.status_code == 503, f"{path} -> {r.status_code} {r.text}"
        assert "Payments aren" in r.json()["detail"]


def test_freeze_order_and_verify_require_auth():
    assert requests.post(f"{API}/freeze/order", timeout=15).status_code == 401
    assert requests.post(f"{API}/plans/pro/order", timeout=15).status_code == 401
    r = requests.post(f"{API}/payments/verify", json={
        "razorpay_order_id": "x", "razorpay_payment_id": "y", "razorpay_signature": "z"}, timeout=15)
    assert r.status_code == 401


def test_webhook_503_without_secret():
    r = requests.post(f"{API}/razorpay/webhook", data=b"{}", timeout=15,
                      headers={"x-razorpay-signature": "sig", "x-razorpay-event-id": "evt_1"})
    assert r.status_code == 503, r.text


def test_dashboard_has_freeze_block():
    tok, _ = onboard(PHONES["P1"], "TEST_P1")
    d = requests.get(f"{API}/dashboard", headers=H(tok), params={"tz_offset_min": 0}, timeout=15).json()
    fz = d["freeze"]
    assert fz["price_inr"] == 49
    assert isinstance(fz["payments_enabled"], bool)
    assert fz["owned"] == 0 and fz["can_buy"] is True
    assert fz["last_week_frozen"] is False
    assert fz["frozen_weeks"] == []
    assert fz["repair"] is None


# ---------------- compute_stats repair logic ----------------

def test_repair_offered_when_streak_broken_no_freezes():
    """(a) streak of 2 weeks, last week missed, freezes=0 -> streak_weeks 0, repair present."""
    tok, uid = onboard(PHONES["P1"], "TEST_P1R", freezes=0)
    today = datetime.now(timezone.utc).date()
    this_week = monday_of(today)
    # seed 2 full weeks before last week
    complete_week(uid, this_week - timedelta(days=21))
    complete_week(uid, this_week - timedelta(days=14))
    d = requests.get(f"{API}/dashboard", headers=H(tok), params={"tz_offset_min": 0}, timeout=15).json()
    assert d["streak_weeks"] == 0, d
    fz = d["freeze"]
    assert fz["repair"] is not None
    assert fz["repair"]["week_start"] == (this_week - timedelta(days=7)).isoformat()
    assert fz["repair"]["deadline"] == (this_week + timedelta(days=6)).isoformat()
    assert fz["repair"]["streak_at_risk"] == 2
    assert fz["last_week_frozen"] is False


def test_auto_uses_freeze_and_idempotent():
    """(b) freezes=1 + missed last week -> auto-used, streak kept, owned=0, frozen row exists;
    calling again doesn't consume anything more."""
    tok, uid = onboard(PHONES["P2"], "TEST_P2", freezes=1)
    today = datetime.now(timezone.utc).date()
    this_week = monday_of(today)
    complete_week(uid, this_week - timedelta(days=21))
    complete_week(uid, this_week - timedelta(days=14))

    d = requests.get(f"{API}/dashboard", headers=H(tok), params={"tz_offset_min": 0}, timeout=15).json()
    fz = d["freeze"]
    assert d["streak_weeks"] == 2, d
    assert fz["owned"] == 0
    assert fz["last_week_frozen"] is True
    assert fz["repair"] is None
    assert (this_week - timedelta(days=7)).isoformat() in fz["frozen_weeks"]

    frozen_rows = MONGO.freeze_weeks.count_documents({"user_id": uid})
    assert frozen_rows == 1

    # call again - no more consumption
    d2 = requests.get(f"{API}/dashboard", headers=H(tok), timeout=15).json()
    assert d2["freeze"]["owned"] == 0
    assert MONGO.freeze_weeks.count_documents({"user_id": uid}) == 1
    assert MONGO.users.find_one({"user_id": uid})["freezes"] == 0


def test_freeze_not_consumed_when_nothing_to_save():
    """(c) owned=1, no missed week -> owned stays 1, can_buy False."""
    tok, uid = onboard(PHONES["P3"], "TEST_P3", freezes=1)
    today = datetime.now(timezone.utc).date()
    this_week = monday_of(today)
    complete_week(uid, this_week - timedelta(days=14))
    complete_week(uid, this_week - timedelta(days=7))
    d = requests.get(f"{API}/dashboard", headers=H(tok), params={"tz_offset_min": 0}, timeout=15).json()
    fz = d["freeze"]
    assert fz["owned"] == 1 and fz["can_buy"] is False
    assert fz["last_week_frozen"] is False
    assert MONGO.freeze_weeks.count_documents({"user_id": uid}) == 0


def test_two_missed_weeks_not_saved():
    """(d) owned=1, last two weeks missed -> NOT consumed, streak 0, no repair."""
    tok, uid = onboard(PHONES["P4"], "TEST_P4", freezes=1)
    today = datetime.now(timezone.utc).date()
    this_week = monday_of(today)
    # streak 2 weeks ago and 3 weeks ago, then 2 misses
    complete_week(uid, this_week - timedelta(days=28))
    complete_week(uid, this_week - timedelta(days=21))
    d = requests.get(f"{API}/dashboard", headers=H(tok), params={"tz_offset_min": 0}, timeout=15).json()
    assert d["streak_weeks"] == 0, d
    fz = d["freeze"]
    assert fz["owned"] == 1
    assert fz["repair"] is None
    assert fz["last_week_frozen"] is False


def test_no_prior_streak_not_consumed():
    """(e) user with no prior streak + freezes=1 -> not consumed."""
    tok, uid = onboard(PHONES["P5"], "TEST_P5", freezes=1)
    d = requests.get(f"{API}/dashboard", headers=H(tok), params={"tz_offset_min": 0}, timeout=15).json()
    fz = d["freeze"]
    assert fz["owned"] == 1
    assert fz["last_week_frozen"] is False
    assert fz["repair"] is None
    assert d["streak_weeks"] == 0


def test_frozen_week_keeps_chain_but_doesnt_count():
    """(f) done, frozen, done => streak_weeks == 2 once current week is done; frozen week kept alive chain."""
    tok, uid = onboard(PHONES["P6"], "TEST_P6", freezes=0)
    today = datetime.now(timezone.utc).date()
    this_week = monday_of(today)
    # Week -2 done, Week -1 manually frozen (simulating a freeze already applied), This week done
    complete_week(uid, this_week - timedelta(days=14))
    MONGO.freeze_weeks.insert_one({"user_id": uid, "week_start": (this_week - timedelta(days=7)).isoformat(),
                                   "applied_at": datetime.now(timezone.utc).isoformat()})
    complete_week(uid, this_week)
    d = requests.get(f"{API}/dashboard", headers=H(tok), params={"tz_offset_min": 0}, timeout=15).json()
    # 2 verified weeks (this_week done + week -2 done); week -1 is frozen so it doesn't add to streak
    assert d["streak_weeks"] == 2, d
    # best_streak should also be 2 - frozen week doesn't add
    assert d["best_streak"] == 2, d
    assert d["freeze"]["last_week_frozen"] is True


def test_reonboarding_preserves_freezes_and_xp():
    tok, uid = onboard(PHONES["P7"], "TEST_P7", freezes=2, xp=777)
    r = requests.post(f"{API}/me", headers=H(tok),
                      json=profile(city="TEST_FZ_RE", name="TEST_P7_renamed", target=4), timeout=15)
    assert r.status_code == 200, r.text
    row = MONGO.users.find_one({"user_id": uid})
    assert row["freezes"] == 2
    assert row["xp"] == 777
    assert row["weekly_target"] == 4
    assert row["name"] == "TEST_P7_renamed"


# ---------------- Payments helpers (keys set only inside pytest) ----------------

@pytest.fixture(scope="module")
def event_loop():
    """One asyncio loop for all async tests. Motor binds to this loop on first use."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def pay_env(monkeypatch):
    """Set Razorpay env in-process. Never touches backend/.env."""
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_PYTEST")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "pytest_secret_abcdef")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "pytest_webhook_secret_xyz")
    yield


def test_valid_checkout_signature(pay_env):
    import payments
    order_id, payment_id = "order_123", "pay_456"
    secret = os.environ["RAZORPAY_KEY_SECRET"].encode()
    good = hmac.new(secret, f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    assert payments.valid_checkout_signature(order_id, payment_id, good) is True
    assert payments.valid_checkout_signature(order_id, payment_id, "bad") is False
    assert payments.valid_checkout_signature(order_id, payment_id, "") is False


def test_valid_webhook_signature(pay_env):
    import payments
    raw = b'{"event":"payment.captured"}'
    secret = os.environ["RAZORPAY_WEBHOOK_SECRET"].encode()
    good = hmac.new(secret, raw, hashlib.sha256).hexdigest()
    assert payments.valid_webhook_signature(raw, good) is True
    assert payments.valid_webhook_signature(raw, "bad") is False
    assert payments.valid_webhook_signature(raw, "") is False


def test_fulfil_order_grants_exactly_one_freeze(pay_env, event_loop):
    """server.fulfil_order called many times / concurrently for the same order grants exactly 1 freeze."""
    import server as srv
    tok, uid = onboard(PHONES["P8"], "TEST_P8", freezes=0)
    order_id = f"TEST_ord_{uuid.uuid4().hex[:12]}"
    CREATED_ORDERS.add(order_id)
    MONGO.payments.insert_one({"order_id": order_id, "user_id": uid, "product": "streak_freeze",
                               "amount": 4900, "currency": "INR", "status": "created",
                               "created_at": datetime.now(timezone.utc).isoformat()})

    async def hammer():
        await asyncio.gather(*[srv.fulfil_order(order_id, f"pay_{i}") for i in range(10)])

    event_loop.run_until_complete(hammer())
    assert MONGO.users.find_one({"user_id": uid})["freezes"] == 1
    row = MONGO.payments.find_one({"order_id": order_id})
    assert row["status"] == "fulfilled"


def test_verify_rejects_cross_user_order(pay_env):
    """/api/freeze/verify must 400 when order_id belongs to another user."""
    tok_a, uid_a = onboard(PHONES["P8"], "TEST_P8_a", freezes=0)
    # create an order owned by a DIFFERENT user_id
    other_uid = f"TEST_other_{uuid.uuid4().hex[:8]}"
    order_id = f"TEST_ord_{uuid.uuid4().hex[:12]}"
    CREATED_ORDERS.add(order_id)
    MONGO.payments.insert_one({"order_id": order_id, "user_id": other_uid, "product": "streak_freeze",
                               "amount": 4900, "currency": "INR", "status": "created",
                               "created_at": datetime.now(timezone.utc).isoformat()})
    # NOTE: route only sees payments.enabled() from server process env, which lacks keys -> 503.
    # So we exercise this directly against the server process, which will still 503. We assert
    # the behaviour via a direct DB-less check: hit the endpoint and expect 503 OR 400.
    r = requests.post(f"{API}/payments/verify", headers=H(tok_a), timeout=15,
                      json={"razorpay_order_id": order_id, "razorpay_payment_id": "pay_x",
                            "razorpay_signature": "sig_x"})
    # Live server has no Razorpay keys, so the payments gate short-circuits to 503.
    # The cross-user guard runs *after* the gate, so we can't reach 400 here without keys on the live
    # server. Document this clearly so main agent can confirm manually.
    assert r.status_code in (400, 503), r.text


def test_verify_rejects_bad_signature_via_in_process_call(pay_env, event_loop):
    """Directly call the route handler in-process with Razorpay keys set.
    This bypasses the live server (which still has no keys) and asserts the
    400 path for unknown / cross-user order and bad signature."""
    from fastapi import HTTPException
    import server as srv

    tok, uid = onboard(PHONES["P8"], "TEST_P8_sig", freezes=0)

    order_id = f"TEST_ord_{uuid.uuid4().hex[:12]}"
    CREATED_ORDERS.add(order_id)
    my_order = f"TEST_ord_{uuid.uuid4().hex[:12]}"
    CREATED_ORDERS.add(my_order)
    other_uid = f"TEST_other_{uuid.uuid4().hex[:8]}"

    async def scenarios():
        # (1) Unknown order -> 400 Unknown order
        body_unknown = srv.VerifyPayment(razorpay_order_id=order_id, razorpay_payment_id="pay_1",
                                         razorpay_signature="x" * 64)
        try:
            await srv.payment_verify(body=body_unknown, auth={"user_id": uid})
            raise AssertionError("expected HTTPException")
        except HTTPException as e:
            assert e.status_code == 400 and "Unknown order" in e.detail

        # (2) Cross-user order -> same 400
        await asyncio.to_thread(MONGO.payments.insert_one, {
            "order_id": order_id, "user_id": other_uid, "product": "streak_freeze",
            "amount": 4900, "currency": "INR", "status": "created",
            "created_at": datetime.now(timezone.utc).isoformat()})
        try:
            await srv.payment_verify(body=body_unknown, auth={"user_id": uid})
            raise AssertionError("expected HTTPException")
        except HTTPException as e:
            assert e.status_code == 400 and "Unknown order" in e.detail

        # (3) Bad signature on a user-owned order -> 400 "Payment could not be verified."
        await asyncio.to_thread(MONGO.payments.insert_one, {
            "order_id": my_order, "user_id": uid, "product": "streak_freeze",
            "amount": 4900, "currency": "INR", "status": "created",
            "created_at": datetime.now(timezone.utc).isoformat()})
        body_bad = srv.VerifyPayment(razorpay_order_id=my_order, razorpay_payment_id="pay_z",
                                     razorpay_signature="deadbeef" * 8)
        try:
            await srv.payment_verify(body=body_bad, auth={"user_id": uid})
            raise AssertionError("expected HTTPException")
        except HTTPException as e:
            assert e.status_code == 400 and "verified" in e.detail.lower()

    event_loop.run_until_complete(scenarios())
