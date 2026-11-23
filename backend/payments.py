"""Razorpay helpers for one-time purchases (Streak Freeze, Pro plans). Inert until RAZORPAY_KEY_ID and
RAZORPAY_KEY_SECRET are set; the webhook additionally needs RAZORPAY_WEBHOOK_SECRET."""

import hashlib
import hmac
import os
import uuid

import razorpay
from starlette.concurrency import run_in_threadpool

# Prices are fixed here on the server, in paise. The app never sends an amount.
PRODUCTS = {
    "streak_freeze": {"amount": 4900, "description": "Streak Freeze"},
    "pro_plans": {"amount": 19900, "description": "Pro training plans"},
}
FREEZE_PRICE_PAISE = PRODUCTS["streak_freeze"]["amount"]
PRO_PLANS_PRICE_PAISE = PRODUCTS["pro_plans"]["amount"]
CURRENCY = "INR"


def key_id() -> str:
    return os.environ.get("RAZORPAY_KEY_ID", "")


def _key_secret() -> str:
    return os.environ.get("RAZORPAY_KEY_SECRET", "")


def _webhook_secret() -> str:
    return os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")


def enabled() -> bool:
    return bool(key_id() and _key_secret())


def webhook_enabled() -> bool:
    return bool(_webhook_secret())


def _client() -> razorpay.Client:
    return razorpay.Client(auth=(key_id(), _key_secret()))


async def create_order(user_id: str, product: str) -> dict:
    return await run_in_threadpool(_client().order.create, {
        "amount": PRODUCTS[product]["amount"],
        "currency": CURRENCY,
        "receipt": "gp_" + uuid.uuid4().hex[:30],
        "notes": {"product": product, "user_id": user_id},
    })


async def fetch_payment(payment_id: str) -> dict:
    return await run_in_threadpool(_client().payment.fetch, payment_id)


async def order_payments(order_id: str) -> list[dict]:
    res = await run_in_threadpool(_client().order.payments, order_id)
    return res.get("items", [])


def _matches(secret: str, message: bytes, signature: str) -> bool:
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def valid_checkout_signature(order_id: str, payment_id: str, signature: str) -> bool:
    return _matches(_key_secret(), f"{order_id}|{payment_id}".encode(), signature)


def valid_webhook_signature(raw_body: bytes, signature: str) -> bool:
    return _matches(_webhook_secret(), raw_body, signature)


def is_paid(payment: dict, order_id: str, amount: int) -> bool:
    """A captured payment for exactly this order and its fixed price."""
    return (payment.get("status") == "captured" and payment.get("order_id") == order_id
            and payment.get("amount") == amount and payment.get("currency") == CURRENCY)
