import asyncio
import base64
import io
import json
import logging
import os
import re
import uuid
from contextlib import suppress
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from motor.motor_asyncio import AsyncIOMotorClient
from PIL import Image
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import DuplicateKeyError
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

try:  # launched as `backend.server` (the default)
    from backend.clerk_auth import clerk_router, require_user
except ModuleNotFoundError:  # launched from inside backend/ as `server`
    from clerk_auth import clerk_router, require_user

try:
    from backend import library, payments, plans_data
except ModuleNotFoundError:
    import library
    import payments
    import plans_data

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INDEXES: dict[str, list[IndexModel]] = {
    "users": [
        IndexModel([("user_id", ASCENDING)], name="user_id", unique=True),
        IndexModel([("city_key", ASCENDING), ("xp", DESCENDING)], name="city_xp"),
    ],
    "challenges": [IndexModel([("id", ASCENDING)], name="id", unique=True)],
    "proofs": [
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="user_created"),
        IndexModel([("user_id", ASCENDING), ("local_date", ASCENDING)], name="user_date_counted_unique",
                   unique=True, partialFilterExpression={"counted": True}),
        IndexModel([("phash", ASCENDING)], name="phash"),
    ],
    "freeze_weeks": [IndexModel([("user_id", ASCENDING), ("week_start", ASCENDING)], name="user_week", unique=True)],
    "payments": [
        IndexModel([("order_id", ASCENDING)], name="order_id", unique=True),
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="user_created"),
    ],
    "webhook_events": [IndexModel([("event_id", ASCENDING)], name="event_id", unique=True)],
    "plan_swaps": [IndexModel([("user_id", ASCENDING), ("plan_id", ASCENDING), ("day", ASCENDING), ("index", ASCENDING)],
                              name="user_plan_slot", unique=True)],
    "wx_media": [IndexModel([("id", ASCENDING)], name="id", unique=True)],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)


app = FastAPI()


@app.get("/health", include_in_schema=False)
@app.head("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


api_router = APIRouter(prefix="/api")

XP_PER_PROOF = 100
XP_WEEK_BONUS = 250
CHALLENGE_TTL_SEC = 120
MILESTONES = [4, 8, 12, 26]
LEVEL_XP = 500


# ---------- Models ----------
class Profile(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    age: int = Field(ge=13, le=100)
    height_cm: int = Field(ge=100, le=250)
    gender: Literal["male", "female", "other"]
    goal: Literal["lean_muscle", "fat_loss", "strength", "stay_fit"]
    weekly_target: int = Field(ge=2, le=5)
    city: str = Field(min_length=1, max_length=60)
    tz_offset_min: int = 0  # minutes to add to UTC to get local time


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    weekly_target: Optional[int] = Field(default=None, ge=2, le=5)
    city: Optional[str] = Field(default=None, min_length=1, max_length=60)
    goal: Optional[Literal["lean_muscle", "fat_loss", "strength", "stay_fit"]] = None
    tz_offset_min: Optional[int] = None


class UserDoc(BaseModel):
    user_id: str
    name: str
    age: int
    height_cm: int
    gender: str
    goal: str
    weekly_target: int
    city: str
    city_key: str
    tz_offset_min: int = 0
    xp: int = 0
    freezes: int = 0  # Streak Freezes bought and not yet used
    plans_unlocked: bool = False  # paid once to open the Pro training plans
    active_plan_id: Optional[str] = None
    created_at: str

    @classmethod
    def from_mongo(cls, doc: dict) -> "UserDoc":
        return cls(**{k: v for k, v in doc.items() if k != "_id"})

    def to_mongo(self) -> dict:
        return self.model_dump()


# ---------- Helpers ----------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def local_today(tz_offset_min: int) -> date:
    return (now_utc() + timedelta(minutes=tz_offset_min)).date()


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())  # Monday


def city_key(city: str) -> str:
    return re.sub(r"\s+", " ", city.strip().lower())


def dhash(img: Image.Image, size: int = 8) -> str:
    g = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(g.getdata())
    bits = 0
    for r in range(size):
        for c in range(size):
            bits = (bits << 1) | (1 if px[r * (size + 1) + c] > px[r * (size + 1) + c + 1] else 0)
    return f"{bits:016x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


async def get_user_or_404(user_id: str) -> UserDoc:
    doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    return UserDoc.from_mongo(doc)


VERIFY_PROMPT = """You are GymProof, a strict photo checker for a gym accountability app.
Look at the photo and answer ONLY with a JSON object, no markdown:
{"hand_present": bool, "hand_gripping_object": bool, "gym_equipment": bool,
 "equipment_type": string, "is_photo_of_screen_or_print": bool, "confidence": number 0-1,
 "reason": string (max 20 words, friendly, addressed to the user)}
Rules:
- hand_gripping_object = a human hand is visibly wrapped around / holding the object.
- gym_equipment = dumbbell, barbell, kettlebell, weight plate, cable handle, machine handle, pull-up bar, resistance band, etc.
- is_photo_of_screen_or_print = the image looks like a picture of a phone/monitor screen or printed photo (moire, bezels, glare, pixel grid)."""


async def ai_verify(jpeg_bytes: bytes) -> dict:
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"proof-{uuid.uuid4()}",
                   system_message="You analyse gym photos and reply with strict JSON.").with_model("gemini", "gemini-3-flash-preview")
    msg = UserMessage(text=VERIFY_PROMPT, file_contents=[ImageContent(image_base64=base64.b64encode(jpeg_bytes).decode())])
    raw = await chat.send_message(msg)
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError(f"No JSON in model output: {raw[:200]}")
    return json.loads(m.group(0))


async def compute_stats(user: UserDoc) -> dict:
    proofs = await db.proofs.find({"user_id": user.user_id, "counted": True}, {"_id": 0, "local_date": 1}).to_list(5000)
    days = sorted({date.fromisoformat(p["local_date"]) for p in proofs})
    target = user.weekly_target
    today = local_today(user.tz_offset_min)
    this_week = week_start(today)

    per_week: dict[date, int] = {}
    for d in days:
        per_week[week_start(d)] = per_week.get(week_start(d), 0) + 1

    def done(w: date) -> bool:
        return per_week.get(w, 0) >= target

    one_week = timedelta(days=7)
    frozen = {date.fromisoformat(f["week_start"]) for f in
              await db.freeze_weeks.find({"user_id": user.user_id}, {"_id": 0, "week_start": 1}).to_list(1000)}

    def chain(w: date) -> int:
        """Verified weeks in the unbroken run ending at w. A frozen week keeps the run alive without adding to it."""
        n = 0
        while done(w) or w in frozen:
            n += 1 if done(w) else 0
            w -= one_week
        return n

    # Streak Freeze: only last week can be saved, and only if it broke a live streak.
    # An owned freeze is used automatically; otherwise the user can buy one until this week ends.
    last_week = this_week - one_week
    repair = None
    if not done(last_week) and last_week not in frozen:
        at_risk = chain(last_week - one_week)
        if at_risk > 0:
            if await use_freeze(user, last_week):
                frozen.add(last_week)
            else:
                repair = {"week_start": last_week.isoformat(), "deadline": (this_week + timedelta(days=6)).isoformat(),
                          "streak_at_risk": at_risk}

    # Current streak: current week counts if already completed; otherwise start from last week.
    streak = chain(this_week if done(this_week) else last_week)

    # Best streak
    best, run, prev = 0, 0, None
    for wk in sorted({k for k in per_week if done(k)} | frozen):
        if not (prev and wk - prev == one_week):
            run = 0
        run += 1 if done(wk) else 0
        best = max(best, run)
        prev = wk

    week_days = []
    for i in range(7):
        d = this_week + timedelta(days=i)
        week_days.append({"date": d.isoformat(), "label": d.strftime("%a"), "done": d in set(days),
                          "is_today": d == today, "is_future": d > today})
    week_count = per_week.get(this_week, 0)
    today_done = today in set(days)
    if week_count >= target:
        widget_state = "week_completed"
    elif today_done:
        widget_state = "completed"
    else:
        widget_state = "pending"

    month_prefix = today.strftime("%Y-%m")
    month_visits = sum(1 for d in days if d.isoformat().startswith(month_prefix))
    total = len(days)
    completed_weeks = sum(1 for k in per_week if done(k))

    milestones = [{"weeks": m, "unlocked": best >= m} for m in MILESTONES]
    achievements = [
        {"id": "first_proof", "title": "First Proof", "desc": "Your first verified gym visit", "unlocked": total >= 1},
        {"id": "first_week", "title": "First Week", "desc": "Hit your weekly target once", "unlocked": completed_weeks >= 1},
        {"id": "first_month", "title": "First Month", "desc": "4-week streak", "unlocked": best >= 4},
        {"id": "ten_visits", "title": "Regular", "desc": "10 verified visits", "unlocked": total >= 10},
        {"id": "fifty_visits", "title": "Iron Habit", "desc": "50 verified visits", "unlocked": total >= 50},
    ]
    return {
        "streak_weeks": streak, "best_streak": best, "weekly_target": target, "week_count": week_count,
        "remaining": max(0, target - week_count), "today_done": today_done, "widget_state": widget_state,
        "week_days": week_days, "total_visits": total, "month_visits": month_visits, "month": month_prefix,
        "completed_weeks": completed_weeks, "xp": user.xp, "level": user.xp // LEVEL_XP + 1,
        "level_progress": (user.xp % LEVEL_XP) / LEVEL_XP, "milestones": milestones, "achievements": achievements,
        "freeze": {"owned": user.freezes, "price_inr": payments.FREEZE_PRICE_PAISE // 100,
                   "payments_enabled": payments.enabled(), "can_buy": user.freezes == 0, "repair": repair,
                   "last_week_frozen": last_week in frozen, "frozen_weeks": sorted(w.isoformat() for w in frozen)},
    }


async def use_freeze(user: UserDoc, week: date) -> bool:
    """Spend one owned freeze on `week`. Atomic: the count can't go below zero and a week is frozen once."""
    if not await db.users.find_one_and_update({"user_id": user.user_id, "freezes": {"$gt": 0}}, {"$inc": {"freezes": -1}}):
        return False
    try:
        await db.freeze_weeks.insert_one({"user_id": user.user_id, "week_start": week.isoformat(),
                                          "applied_at": now_utc().isoformat()})
        user.freezes -= 1
    except DuplicateKeyError:  # a concurrent request froze this week already; give the freeze back
        await db.users.update_one({"user_id": user.user_id}, {"$inc": {"freezes": 1}})
    return True


async def fulfil_order(order_id: str, payment_id: str) -> None:
    """Deliver a paid order exactly once, however many times verify/webhook/reconcile report it."""
    row = await db.payments.find_one_and_update(
        {"order_id": order_id, "status": {"$ne": "fulfilled"}},
        {"$set": {"status": "fulfilled", "payment_id": payment_id, "fulfilled_at": now_utc().isoformat()}})
    if not row:
        return
    grant = {"$set": {"plans_unlocked": True}} if row["product"] == "pro_plans" else {"$inc": {"freezes": 1}}
    await db.users.update_one({"user_id": row["user_id"]}, grant)
    logger.info("Order fulfilled: %s order=%s user=%s", row["product"], order_id, row["user_id"])


async def settle(row: dict, payment: dict) -> bool:
    """Fulfil the order if this payment is captured for the order's own amount."""
    if not payments.is_paid(payment, row["order_id"], row["amount"]):
        return False
    await fulfil_order(row["order_id"], payment["id"])
    return True


_last_reconcile: dict[str, datetime] = {}


async def reconcile_orders(user_id: str) -> None:
    """Pick up payments that were captured but never reported back by the app (closed mid-checkout).
    Checks Razorpay at most once a minute per user."""
    last = _last_reconcile.get(user_id)
    if last and (now_utc() - last).total_seconds() < 60:
        return
    _last_reconcile[user_id] = now_utc()
    since = (now_utc() - timedelta(days=1)).isoformat()
    open_orders = await db.payments.find({"user_id": user_id, "status": "created", "created_at": {"$gte": since}},
                                         {"_id": 0}).sort("created_at", -1).to_list(4)
    for o in open_orders:
        try:
            for p in await payments.order_payments(o["order_id"]):
                await settle(o, p)
        except Exception as exc:
            logger.warning("reconcile %s failed: %s", o["order_id"], exc)


async def start_order(user_id: str, product: str) -> dict:
    """Razorpay order for `product`. Reuses a just-created unpaid one so a double tap can't lead to paying twice."""
    item = payments.PRODUCTS[product]
    recent = await db.payments.find_one(
        {"user_id": user_id, "product": product, "status": "created",
         "created_at": {"$gte": (now_utc() - timedelta(minutes=10)).isoformat()}},
        {"_id": 0, "order_id": 1}, sort=[("created_at", -1)])
    if recent:
        order_id = recent["order_id"]
    else:
        try:
            order = await payments.create_order(user_id, product)
        except Exception as exc:
            logger.exception("Razorpay order failed: %s", exc)
            raise HTTPException(status_code=502, detail="Couldn't start the payment. Try again.")
        order_id = order["id"]
        await db.payments.insert_one({"order_id": order_id, "user_id": user_id, "product": product,
                                      "amount": item["amount"], "currency": payments.CURRENCY,
                                      "status": "created", "created_at": now_utc().isoformat()})
    return {"key_id": payments.key_id(), "order_id": order_id, "amount": item["amount"],
            "currency": payments.CURRENCY, "name": "GymProof", "description": item["description"]}


def require_payments() -> None:
    if not payments.enabled():
        raise HTTPException(status_code=503, detail="Payments aren't switched on yet.")


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"message": "GymProof API"}


@api_router.get("/me")
async def get_me(auth: dict = Depends(require_user)):
    doc = await db.users.find_one({"user_id": auth["user_id"]}, {"_id": 0})
    if not doc:
        return {"onboarded": False, "profile": None}
    return {"onboarded": True, "profile": UserDoc.from_mongo(doc).model_dump()}


@api_router.post("/me")
async def create_me(body: Profile, auth: dict = Depends(require_user)):
    keep = ("xp", "freezes", "plans_unlocked", "active_plan_id", "created_at")
    existing = await db.users.find_one({"user_id": auth["user_id"]}, {"_id": 0, **{k: 1 for k in keep}}) or {}
    user = UserDoc(**{"created_at": now_utc().isoformat(), **existing}, user_id=auth["user_id"], **body.model_dump(),
                   city_key=city_key(body.city))
    await db.users.update_one({"user_id": user.user_id}, {"$set": user.to_mongo()}, upsert=True)
    return {"onboarded": True, "profile": user.model_dump()}


@api_router.patch("/me")
async def update_me(body: ProfileUpdate, auth: dict = Depends(require_user)):
    await get_user_or_404(auth["user_id"])
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "city" in updates:
        updates["city_key"] = city_key(updates["city"])
    if updates:
        await db.users.update_one({"user_id": auth["user_id"]}, {"$set": updates})
    return {"onboarded": True, "profile": (await get_user_or_404(auth["user_id"])).model_dump()}


@api_router.get("/dashboard")
async def dashboard(tz_offset_min: Optional[int] = None, auth: dict = Depends(require_user)):
    user = await get_user_or_404(auth["user_id"])
    if tz_offset_min is not None and tz_offset_min != user.tz_offset_min:
        await db.users.update_one({"user_id": user.user_id}, {"$set": {"tz_offset_min": tz_offset_min}})
        user.tz_offset_min = tz_offset_min
    stats = await compute_stats(user)
    plan = plans_data.PLANS_BY_ID.get(user.active_plan_id or "")
    return {"name": user.name, "city": user.city, **stats,
            "active_plan": plan and {"id": plan["id"], "name": plan["name"], "days_per_week": plan["days_per_week"]}}


@api_router.post("/proof/challenge")
async def proof_challenge(auth: dict = Depends(require_user)):
    await get_user_or_404(auth["user_id"])
    ch = {"id": str(uuid.uuid4()), "user_id": auth["user_id"], "issued_at": now_utc().isoformat(),
          "expires_at": (now_utc() + timedelta(seconds=CHALLENGE_TTL_SEC)).isoformat(), "used": False}
    await db.challenges.insert_one(dict(ch))
    return {"challenge_id": ch["id"], "expires_at": ch["expires_at"], "ttl_sec": CHALLENGE_TTL_SEC}


@api_router.post("/proof/submit")
async def proof_submit(challenge_id: str = Form(...), captured_at: str = Form(...),
                       image: UploadFile = File(...), auth: dict = Depends(require_user)):
    user = await get_user_or_404(auth["user_id"])
    # 1. Challenge: one-use, short-lived, owned by this user
    ch = await db.challenges.find_one_and_update(
        {"id": challenge_id, "user_id": user.user_id, "used": False}, {"$set": {"used": True}})
    if not ch:
        raise HTTPException(status_code=400, detail="Proof session expired. Open the camera again.")
    now = now_utc()
    if datetime.fromisoformat(ch["expires_at"]) < now:
        raise HTTPException(status_code=400, detail="Proof session expired. Open the camera again.")
    # 2. Capture timestamp must be inside the challenge window
    try:
        cap = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid capture time")
    issued = datetime.fromisoformat(ch["issued_at"])
    if not (issued - timedelta(seconds=5) <= cap <= now + timedelta(seconds=5)):
        raise HTTPException(status_code=400, detail="Capture time doesn't match this proof session.")

    data = await image.read()
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read the photo")
    img = img.convert("RGB")
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    phash = dhash(img)

    today = local_today(user.tz_offset_min)
    proof = {"id": str(uuid.uuid4()), "user_id": user.user_id, "local_date": today.isoformat(),
             "created_at": now.isoformat(), "phash": phash, "counted": False, "xp_awarded": 0}

    # 3. Duplicate detection against earlier submissions
    # exact match across all accounts, near-match against this user's own history
    cross = await db.proofs.find_one({"phash": phash}, {"_id": 1})
    prev = await db.proofs.find({"user_id": user.user_id}, {"_id": 0, "phash": 1}).sort("created_at", -1).to_list(500)
    if cross or any(p.get("phash") and hamming(p["phash"], phash) <= 4 for p in prev):
        proof.update(status="suspicious", reason="This looks like a photo you've already submitted. Take a fresh one.")
        await db.proofs.insert_one(dict(proof))
        return {k: v for k, v in proof.items() if k not in ("phash", "user_id")}

    # 4. AI check
    try:
        v = await ai_verify(buf.getvalue())
    except Exception as exc:
        logger.exception("AI verify failed: %s", exc)
        raise HTTPException(status_code=502, detail="AI couldn't check the photo right now. Try again.")

    if v.get("is_photo_of_screen_or_print"):
        status, reason = "suspicious", "Looks like a photo of a screen or print. Snap the real thing."
    elif v.get("hand_present") and v.get("hand_gripping_object") and v.get("gym_equipment"):
        status, reason = "accepted", v.get("reason") or "Hand on the iron. Gym Proof accepted!"
    else:
        status = "rejected"
        if not v.get("hand_present") or not v.get("hand_gripping_object"):
            reason = "We need to see your hand gripping the equipment."
        else:
            reason = "We couldn't spot gym equipment in your grip."
    proof.update(status=status, reason=reason, equipment=v.get("equipment_type", ""),
                 confidence=v.get("confidence"))

    if status == "accepted":
        already = await db.proofs.find_one({"user_id": user.user_id, "local_date": proof["local_date"], "counted": True})
        if already:
            proof["already_counted_today"] = True
        else:
            before = await compute_stats(user)
            proof["counted"] = True
            xp = XP_PER_PROOF
            if before["week_count"] + 1 == user.weekly_target:
                xp += XP_WEEK_BONUS
                proof["week_completed_now"] = True
            proof["xp_awarded"] = xp
    try:
        await db.proofs.insert_one(dict(proof))
    except DuplicateKeyError:  # concurrent accepted proof for the same day already counted
        proof.update(counted=False, xp_awarded=0, already_counted_today=True)
        proof.pop("week_completed_now", None)
        await db.proofs.insert_one(dict(proof))
    if proof["counted"]:
        await db.users.update_one({"user_id": user.user_id}, {"$inc": {"xp": proof["xp_awarded"]}})
    return {k: v for k, v in proof.items() if k not in ("phash", "user_id")}


@api_router.get("/proofs")
async def list_proofs(limit: int = Query(30, ge=1, le=100), auth: dict = Depends(require_user)):
    return await db.proofs.find({"user_id": auth["user_id"]}, {"_id": 0, "phash": 0, "user_id": 0}) \
        .sort("created_at", -1).limit(limit).to_list(limit)


class VerifyPayment(BaseModel):
    razorpay_order_id: str = Field(max_length=64)
    razorpay_payment_id: str = Field(max_length=64)
    razorpay_signature: str = Field(max_length=128)


@api_router.get("/freeze")
async def freeze_status(auth: dict = Depends(require_user)):
    await get_user_or_404(auth["user_id"])
    if payments.enabled():
        await reconcile_orders(auth["user_id"])
    stats = await compute_stats(await get_user_or_404(auth["user_id"]))
    return {**stats["freeze"], "streak_weeks": stats["streak_weeks"]}


@api_router.post("/freeze/order")
async def freeze_order(auth: dict = Depends(require_user)):
    user = await get_user_or_404(auth["user_id"])
    require_payments()
    await reconcile_orders(user.user_id)
    user = await get_user_or_404(user.user_id)
    await compute_stats(user)  # uses an owned freeze first if last week needs one
    if user.freezes > 0:
        raise HTTPException(status_code=409, detail="You already have a Streak Freeze ready.")
    return await start_order(user.user_id, "streak_freeze")


@api_router.post("/payments/verify")
async def payment_verify(body: VerifyPayment, auth: dict = Depends(require_user)):
    require_payments()
    row = await db.payments.find_one({"order_id": body.razorpay_order_id, "user_id": auth["user_id"]}, {"_id": 0})
    if not row:
        raise HTTPException(status_code=400, detail="Unknown order")
    if row["status"] == "fulfilled":
        return {"status": "fulfilled"}
    if not payments.valid_checkout_signature(row["order_id"], body.razorpay_payment_id, body.razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment could not be verified.")
    try:
        payment = await payments.fetch_payment(body.razorpay_payment_id)
    except Exception as exc:
        logger.exception("Razorpay payment fetch failed: %s", exc)
        raise HTTPException(status_code=502, detail="Couldn't confirm the payment yet. Try again.")
    if payment.get("order_id") != row["order_id"]:
        raise HTTPException(status_code=400, detail="Payment could not be verified.")
    # "pending" = authorised but not captured yet; the webhook or the next check completes it
    return {"status": "fulfilled" if await settle(row, payment) else "pending"}


@api_router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    if not payments.webhook_enabled():
        raise HTTPException(status_code=503, detail="Webhook is not configured")
    raw = await request.body()  # signature is over the untouched bytes
    if not payments.valid_webhook_signature(raw, request.headers.get("x-razorpay-signature", "")):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    event_id = request.headers.get("x-razorpay-event-id")
    if not event_id:
        raise HTTPException(status_code=400, detail="Missing event id")
    event = json.loads(raw)
    kind = event.get("event")
    payment = event.get("payload", {}).get("payment", {}).get("entity", {})
    row = await db.payments.find_one({"order_id": payment.get("order_id") or ""}, {"_id": 0})
    if row and kind == "payment.captured":
        await settle(row, payment)
    elif row and kind == "payment.failed":
        await db.payments.update_one({"order_id": row["order_id"], "status": "created"},
                                     {"$set": {"last_failure_at": now_utc().isoformat()}})
    with suppress(DuplicateKeyError):  # recorded after handling, so a retried delivery is processed until it succeeds
        await db.webhook_events.insert_one({"event_id": event_id, "event": kind, "received_at": now_utc().isoformat()})
    return {"ok": True}


# ---------- Training plans ----------
PLAN_CARD_KEYS = ("id", "gender", "name", "tagline", "goal", "level", "duration_weeks", "premium", "icon", "days_per_week")


def plan_card(plan: dict, user: UserDoc) -> dict:
    return {**{k: plan[k] for k in PLAN_CARD_KEYS}, "locked": plan["premium"] and not user.plans_unlocked,
            "active": plan["id"] == user.active_plan_id}


def pro_status(user: UserDoc) -> dict:
    return {"unlocked": user.plans_unlocked, "price_inr": payments.PRO_PLANS_PRICE_PAISE // 100,
            "payments_enabled": payments.enabled(), "plan_count": sum(1 for p in plans_data.PLANS if p["premium"])}


def get_plan_or_404(plan_id: str) -> dict:
    plan = plans_data.PLANS_BY_ID.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


async def user_with_purchases(user_id: str) -> UserDoc:
    user = await get_user_or_404(user_id)
    if payments.enabled() and not user.plans_unlocked:
        await reconcile_orders(user_id)
        user = await get_user_or_404(user_id)
    return user


@api_router.get("/plans")
async def list_plans(auth: dict = Depends(require_user)):
    user = await user_with_purchases(auth["user_id"])
    return {"plans": [plan_card(p, user) for p in plans_data.PLANS], "pro": pro_status(user),
            "default_gender": "female" if user.gender == "female" else "male"}


@api_router.post("/plans/pro/order")
async def pro_plans_order(auth: dict = Depends(require_user)):
    require_payments()
    user = await user_with_purchases(auth["user_id"])
    if user.plans_unlocked:
        raise HTTPException(status_code=409, detail="Pro plans are already unlocked.")
    return await start_order(user.user_id, "pro_plans")


@api_router.post("/plans/active/stop")
async def stop_plan(auth: dict = Depends(require_user)):
    await get_user_or_404(auth["user_id"])
    await db.users.update_one({"user_id": auth["user_id"]}, {"$set": {"active_plan_id": None}})
    return {"active_plan_id": None}


def demo_model(user: UserDoc) -> str:
    return "female" if user.gender == "female" else "male"


def plan_row(index: int, move: dict, current: str, swapped: bool, model: str) -> dict:
    """One move of a plan day as the app lists it: the plan's sets and reps with the current exercise."""
    if current in library.EX:
        c = library.card(current, model)
        photos = library.photos_for(current)
        ex = {"name": c["name"], "muscle": c["target"], "equipment": c["equipment"], "level": c["level"],
              "image": c["thumb"] or (photos[0] if photos else None), "similar": False}
    else:
        p = library.PHOTOS[current]
        ex = {"name": p["name"], "muscle": p["primary_muscles"][0], "equipment": p["equipment"], "level": p["level"],
              "image": p["images"][0], "similar": True}
    return {**ex, "index": index, "id": current, "original_id": library.resolve_plan_move(move["id"]), "swapped": swapped,
            "sets": move["sets"], "reps": move["reps"], "rest_sec": move["rest_sec"]}


@api_router.get("/plans/{plan_id}")
async def plan_detail(plan_id: str, auth: dict = Depends(require_user)):
    plan = get_plan_or_404(plan_id)
    user = await user_with_purchases(auth["user_id"])
    card = plan_card(plan, user)
    swaps = {} if card["locked"] else {
        (s["day"], s["index"]): s["exercise_id"]
        async for s in db.plan_swaps.find({"user_id": user.user_id, "plan_id": plan_id}, {"_id": 0})}
    model = demo_model(user)
    days = []
    for d in plan["days"]:
        exercises = [] if card["locked"] else [
            plan_row(i, e, swaps.get((d["day"], i), library.resolve_plan_move(e["id"])), (d["day"], i) in swaps, model)
            for i, e in enumerate(d["exercises"])]
        days.append({"day": d["day"], "title": d["title"], "focus": d["focus"],
                     "exercise_count": len(d["exercises"]), "exercises": exercises})
    return {**card, "description": plan["description"], "days": days, "pro": pro_status(user)}


class SwapBody(BaseModel):
    exercise_id: str = Field(max_length=80)


async def plan_slot(plan_id: str, day: int, index: int, user_id: str) -> tuple[dict, UserDoc]:
    plan = get_plan_or_404(plan_id)
    user = await user_with_purchases(user_id)
    if plan["premium"] and not user.plans_unlocked:
        raise HTTPException(status_code=403, detail="Unlock Pro plans to change this one.")
    d = next((x for x in plan["days"] if x["day"] == day), None)
    if not d or not 0 <= index < len(d["exercises"]):
        raise HTTPException(status_code=404, detail="That move isn't in this plan.")
    return d["exercises"][index], user


@api_router.put("/plans/{plan_id}/days/{day}/exercises/{index}")
async def swap_move(plan_id: str, day: int, index: int, body: SwapBody, auth: dict = Depends(require_user)):
    move, user = await plan_slot(plan_id, day, index, auth["user_id"])
    if body.exercise_id in library.EX:
        new_id = library.canonical_id(body.exercise_id)
    elif body.exercise_id in library.PHOTOS:
        new_id = body.exercise_id
    else:
        raise HTTPException(status_code=404, detail="Exercise not found")
    slot = {"user_id": user.user_id, "plan_id": plan_id, "day": day, "index": index}
    if new_id == library.resolve_plan_move(move["id"]):
        await db.plan_swaps.delete_one(slot)
        return {"exercise_id": new_id, "swapped": False}
    await db.plan_swaps.update_one(slot, {"$set": {**slot, "exercise_id": new_id, "updated_at": now_utc().isoformat()}}, upsert=True)
    return {"exercise_id": new_id, "swapped": True}


@api_router.delete("/plans/{plan_id}/days/{day}/exercises/{index}")
async def reset_move(plan_id: str, day: int, index: int, auth: dict = Depends(require_user)):
    move, user = await plan_slot(plan_id, day, index, auth["user_id"])
    await db.plan_swaps.delete_one({"user_id": user.user_id, "plan_id": plan_id, "day": day, "index": index})
    return {"exercise_id": library.resolve_plan_move(move["id"]), "swapped": False}


@api_router.post("/plans/{plan_id}/start")
async def start_plan(plan_id: str, auth: dict = Depends(require_user)):
    plan = get_plan_or_404(plan_id)
    user = await user_with_purchases(auth["user_id"])
    if plan["premium"] and not user.plans_unlocked:
        raise HTTPException(status_code=403, detail="Unlock Pro plans to start this one.")
    await db.users.update_one({"user_id": user.user_id}, {"$set": {"active_plan_id": plan_id}})
    return {"active_plan_id": plan_id}


@api_router.get("/library")
async def exercise_library(auth: dict = Depends(require_user)):
    return library.library(demo_model(await get_user_or_404(auth["user_id"])))


@api_router.get("/exercises/{exercise_id}")
async def exercise_detail(exercise_id: str, model: Optional[Literal["male", "female"]] = None,
                          auth: dict = Depends(require_user)):
    user = await get_user_or_404(auth["user_id"])
    if exercise_id in library.EX:
        return await library.detail(exercise_id, model or demo_model(user), library.photos_for(exercise_id))
    if exercise_id in library.PHOTOS:
        match = library.PLAN_MATCH.get(exercise_id)
        if match:  # an old plan id that now has a WorkoutX version
            return await library.detail(match, model or demo_model(user), library.photos_for(match))
        return library.photo_exercise(exercise_id)
    raise HTTPException(status_code=404, detail="Exercise not found")


@api_router.get("/exercises/{exercise_id}/alternatives")
async def exercise_alternatives(exercise_id: str, plan_id: Optional[str] = None, auth: dict = Depends(require_user)):
    user = await get_user_or_404(auth["user_id"])
    if exercise_id not in library.EX and exercise_id not in library.PHOTOS:
        raise HTTPException(status_code=404, detail="Exercise not found")
    level = library.level_of_plan(get_plan_or_404(plan_id)["level"]) if plan_id else None
    model = demo_model(user)
    return {"items": [library.card(i, model) for i in library.alternatives(exercise_id, level)]}


@api_router.get("/leaderboard")
async def leaderboard(scope: Literal["city", "all"] = "city", auth: dict = Depends(require_user)):
    me = await get_user_or_404(auth["user_id"])
    q = {"city_key": me.city_key} if scope == "city" else {}
    proj = {"_id": 0, "user_id": 1, "name": 1, "xp": 1, "city": 1}
    top = await db.users.find(q, proj).sort([("xp", -1), ("created_at", 1)]).limit(50).to_list(50)
    my_rank = await db.users.count_documents(
        {**q, "$or": [{"xp": {"$gt": me.xp}}, {"xp": me.xp, "created_at": {"$lt": me.created_at}}]}) + 1
    entries = [{"rank": i + 1, "name": u["name"], "xp": u["xp"], "city": u["city"],
                "is_me": u["user_id"] == me.user_id} for i, u in enumerate(top)]
    return {"scope": scope, "city": me.city, "entries": entries, "my_rank": my_rank, "my_xp": me.xp,
            "total": await db.users.count_documents(q)}


app.include_router(api_router)
app.include_router(clerk_router)

app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def start_index_build():
    app.state.index_task = asyncio.create_task(ensure_indexes())
    await library.init(db)


@app.on_event("shutdown")
async def shutdown_db_client():
    app.state.index_task.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.index_task
    client.close()
