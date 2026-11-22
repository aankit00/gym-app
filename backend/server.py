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
from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
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

    # Current streak: current week counts if already completed; otherwise start from last week.
    streak = 0
    w = this_week if done(this_week) else this_week - timedelta(days=7)
    while done(w):
        streak += 1
        w -= timedelta(days=7)

    # Best streak
    best, run, prev = 0, 0, None
    for wk in sorted(k for k in per_week if done(k)):
        run = run + 1 if prev and wk - prev == timedelta(days=7) else 1
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
    }


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
    existing = await db.users.find_one({"user_id": auth["user_id"]}, {"_id": 0, "xp": 1, "created_at": 1})
    user = UserDoc(user_id=auth["user_id"], **body.model_dump(), city_key=city_key(body.city),
                   xp=(existing or {}).get("xp", 0),
                   created_at=(existing or {}).get("created_at", now_utc().isoformat()))
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
    return {"name": user.name, "city": user.city, **stats}


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


@app.on_event("shutdown")
async def shutdown_db_client():
    app.state.index_task.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.index_task
    client.close()
