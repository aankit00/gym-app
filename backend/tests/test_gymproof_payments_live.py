# GymProof live Razorpay (TEST keys) tests: real order creation for Streak Freeze & Pro plans,
# server-fixed amounts, double-tap order reuse, bad-signature rejection, cross-user order rejection,
# pro plan start blocked before purchase, webhook signature gate. Keys are read from the live server only.
import os
import sys
import uuid
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

PHONE_A = "+12015550181"
PHONE_B = "+12015550182"
CREATED_UIDS: set[str] = set()


def onboard(phone: str) -> tuple[str, str]:
    tok = token_for(phone)
    body = profile(city=f"TEST_PAY_{phone[-3:]}", name=f"TEST_PAY_{phone[-3:]}", target=3)
    r = requests.post(f"{API}/me", headers=H(tok), json=body, timeout=15)
    assert r.status_code == 200, r.text
    uid = r.json()["profile"]["user_id"]
    CREATED_UIDS.add(uid)
    MONGO.payments.delete_many({"user_id": uid})
    MONGO.users.update_one({"user_id": uid}, {"$set": {"freezes": 0, "plans_unlocked": False, "active_plan_id": None}})
    return tok, uid


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for uid in CREATED_UIDS:
        MONGO.users.delete_one({"user_id": uid})
        MONGO.payments.delete_many({"user_id": uid})
        MONGO.freeze_weeks.delete_many({"user_id": uid})
        MONGO.proofs.delete_many({"user_id": uid})


@pytest.fixture(scope="module")
def user_a():
    return onboard(PHONE_A)


@pytest.fixture(scope="module")
def user_b():
    return onboard(PHONE_B)


def _require_enabled(tok):
    r = requests.get(f"{API}/freeze", headers=H(tok), timeout=15)
    assert r.status_code == 200, r.text
    if not r.json()["payments_enabled"]:
        pytest.skip("payments not enabled on live server")
    return r.json()


# Freeze status endpoint
def test_freeze_status_shape(user_a):
    tok, _ = user_a
    d = _require_enabled(tok)
    assert d["price_inr"] == 49 and d["owned"] == 0 and d["can_buy"] is True
    assert "streak_weeks" in d and isinstance(d["frozen_weeks"], list)


# Real Razorpay order creation (freeze), server-fixed amount, reuse on double-tap
def test_freeze_order_real_and_reused(user_a):
    tok, uid = user_a
    _require_enabled(tok)
    r = requests.post(f"{API}/freeze/order", headers=H(tok), json={"amount": 1}, timeout=30)
    assert r.status_code == 200, r.text
    o = r.json()
    assert o["order_id"].startswith("order_")
    assert o["amount"] == 4900 and o["currency"] == "INR"
    assert o["key_id"].startswith("rzp_test_")
    row = MONGO.payments.find_one({"order_id": o["order_id"]})
    assert row and row["user_id"] == uid and row["amount"] == 4900 and row["status"] == "created"
    r2 = requests.post(f"{API}/freeze/order", headers=H(tok), timeout=30)
    assert r2.status_code == 200 and r2.json()["order_id"] == o["order_id"]


# Real Razorpay order creation (pro plans)
def test_pro_order_real(user_a):
    tok, uid = user_a
    _require_enabled(tok)
    r = requests.post(f"{API}/plans/pro/order", headers=H(tok), json={"amount": 100}, timeout=30)
    assert r.status_code == 200, r.text
    o = r.json()
    assert o["order_id"].startswith("order_") and o["amount"] == 19900 and o["currency"] == "INR"
    assert MONGO.payments.find_one({"order_id": o["order_id"]})["product"] == "pro_plans"


# Bad signature rejected; plans stay locked
def test_verify_bad_signature_rejected(user_a):
    tok, uid = user_a
    _require_enabled(tok)
    oid = requests.post(f"{API}/plans/pro/order", headers=H(tok), timeout=30).json()["order_id"]
    r = requests.post(f"{API}/payments/verify", headers=H(tok), timeout=15, json={
        "razorpay_order_id": oid, "razorpay_payment_id": "pay_FAKE123", "razorpay_signature": "0" * 64})
    assert r.status_code == 400 and "verified" in r.json()["detail"].lower()
    u = MONGO.users.find_one({"user_id": uid})
    assert u["plans_unlocked"] is False and u["freezes"] == 0
    assert MONGO.payments.find_one({"order_id": oid})["status"] == "created"


# Other user's order cannot be verified
def test_verify_cross_user_rejected(user_a, user_b):
    tok_a, _ = user_a
    tok_b, _ = user_b
    _require_enabled(tok_a)
    oid = requests.post(f"{API}/freeze/order", headers=H(tok_a), timeout=30).json()["order_id"]
    r = requests.post(f"{API}/payments/verify", headers=H(tok_b), timeout=15, json={
        "razorpay_order_id": oid, "razorpay_payment_id": "pay_X", "razorpay_signature": "a" * 64})
    assert r.status_code == 400 and r.json()["detail"] == "Unknown order"


# Validation of verify body
def test_verify_body_validation(user_a):
    tok, _ = user_a
    r = requests.post(f"{API}/payments/verify", headers=H(tok), timeout=15, json={"razorpay_order_id": "x"})
    assert r.status_code == 422


# Pro plan cannot be started before purchase
def test_pro_plan_start_blocked(user_a):
    tok, uid = user_a
    r = requests.post(f"{API}/plans/greek-god/start", headers=H(tok), timeout=15)
    assert r.status_code == 403
    assert MONGO.users.find_one({"user_id": uid}).get("active_plan_id") is None
    d = requests.get(f"{API}/plans/greek-god", headers=H(tok), timeout=15).json()
    assert d["locked"] is True and all(day["exercises"] == [] for day in d["days"])


# Webhook rejects missing/invalid signature
def test_webhook_rejects_bad_signature():
    r = requests.post(f"{API}/razorpay/webhook", data=b'{"event":"payment.captured"}', timeout=15,
                      headers={"x-razorpay-signature": "bad", "x-razorpay-event-id": f"evt_{uuid.uuid4().hex}"})
    assert r.status_code in (400, 503), r.text
    r2 = requests.post(f"{API}/razorpay/webhook", data=b"{}", timeout=15)
    assert r2.status_code in (400, 503)


# 409 when a freeze is already owned
def test_freeze_order_409_when_owned(user_b):
    tok, uid = user_b
    _require_enabled(tok)
    MONGO.users.update_one({"user_id": uid}, {"$set": {"freezes": 1}})
    r = requests.post(f"{API}/freeze/order", headers=H(tok), timeout=30)
    assert r.status_code == 409
    MONGO.users.update_one({"user_id": uid}, {"$set": {"freezes": 0}})
