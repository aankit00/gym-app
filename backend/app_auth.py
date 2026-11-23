"""Email/password and Google sign-in, as accounts separate from Clerk phone sign-in.

- Email: bcrypt-hashed passwords, our own HS256 JWT (30 days), per-email and per-IP lockout after 5 failures.
- Google: Emergent-managed Google auth. The app sends the one-time session_id; we exchange it once and store
  our own 7-day session token in user_sessions.
- require_user accepts any of the three and returns {"user_id", "provider"}. Ids never collide:
  Clerk "user_...", email "email_...", Google "google_...". Accounts are never linked by email.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from pymongo.errors import DuplicateKeyError
from starlette.concurrency import run_in_threadpool

try:
    from backend import clerk_auth
except ModuleNotFoundError:
    import clerk_auth

router = APIRouter(prefix="/api/auth")
ISSUER, AUDIENCE = "gymproof-api", "gymproof-app"
EMAIL_TOKEN_DAYS = 30
GOOGLE_SESSION_DAYS = 7
MAX_FAILURES, LOCK_MINUTES = 5, 15
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
_DUMMY_HASH = bcrypt.hashpw(b"constant dummy password", bcrypt.gensalt()).decode()
_db = None


def init(db) -> None:
    global _db
    _db = db


async def ensure_indexes() -> None:
    await _db.auth_accounts.create_index([("provider", 1), ("email", 1)], unique=True, name="provider_email")
    await _db.auth_accounts.create_index("user_id", unique=True, name="user_id")
    await _db.user_sessions.create_index("session_token", unique=True, name="token")
    await _db.user_sessions.create_index("expires_at", expireAfterSeconds=0, name="ttl")
    await _db.auth_attempts.create_index("expires_at", expireAfterSeconds=0, name="ttl")


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ip(request: Request) -> str:
    # behind the ingress request.client is the ingress pod, shared by everyone; the client is the first XFF hop
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _public(acc: dict) -> dict:
    return {"user_id": acc["user_id"], "email": acc["email"], "name": acc.get("name", ""), "provider": acc["provider"]}


# ---------- email + password ----------
class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


def _check_length(password: str) -> None:
    if len(password.encode()) > 72:  # bcrypt ignores anything past 72 bytes
        raise HTTPException(status_code=422, detail="Password is too long.")


def _email_token(user_id: str) -> str:
    now = _now()
    return jwt.encode({"sub": user_id, "provider": "email", "iss": ISSUER, "aud": AUDIENCE, "iat": now,
                       "exp": now + timedelta(days=EMAIL_TOKEN_DAYS)}, _secret(), algorithm="HS256")


async def _locked(keys: list[str]) -> bool:
    now = _now()
    docs = await _db.auth_attempts.find({"_id": {"$in": keys}}).to_list(len(keys))
    return any(d.get("failures", 0) >= MAX_FAILURES and d["expires_at"].replace(tzinfo=timezone.utc) > now for d in docs)


async def _fail(keys: list[str]) -> None:
    for k in keys:
        await _db.auth_attempts.update_one(
            {"_id": k}, {"$inc": {"failures": 1}, "$set": {"expires_at": _now() + timedelta(minutes=LOCK_MINUTES)}}, upsert=True)


@router.post("/register")
async def register(body: Credentials):
    _check_length(body.password)
    email = body.email.lower().strip()
    acc = {"user_id": f"email_{uuid.uuid4().hex[:16]}", "provider": "email", "email": email, "name": "",
           "password_hash": (await run_in_threadpool(bcrypt.hashpw, body.password.encode(), bcrypt.gensalt(12))).decode(),
           "created_at": _now()}
    try:
        await _db.auth_accounts.insert_one(dict(acc))
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="An account with this email already exists. Sign in instead.")
    return {"token": _email_token(acc["user_id"]), "account": _public(acc)}


@router.post("/login")
async def login(body: Credentials, request: Request):
    _check_length(body.password)
    email = body.email.lower().strip()
    keys = [f"email:{email}", f"ip:{_ip(request)}"]
    if await _locked(keys):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.")
    acc = await _db.auth_accounts.find_one({"provider": "email", "email": email}, {"_id": 0})
    stored = acc["password_hash"] if acc else _DUMMY_HASH  # same work either way: no account enumeration by timing
    ok = await run_in_threadpool(bcrypt.checkpw, body.password.encode(), stored.encode())
    if not (acc and ok):
        await _fail(keys)
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    await _db.auth_attempts.delete_many({"_id": {"$in": keys}})
    return {"token": _email_token(acc["user_id"]), "account": _public(acc)}


# ---------- Google (Emergent-managed) ----------
class GoogleSession(BaseModel):
    session_id: str = Field(min_length=1, max_length=512)


@router.post("/session")
async def google_session(body: GoogleSession):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": body.session_id})
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Google sign-in is unavailable. Try again.")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Google sign-in expired. Try again.")
    data = r.json()
    email = (data.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=401, detail="Google didn't share an email address.")
    acc = await _db.auth_accounts.find_one_and_update(
        {"provider": "google", "email": email},
        {"$set": {"name": data.get("name") or "", "picture": data.get("picture") or ""},
         "$setOnInsert": {"user_id": f"google_{uuid.uuid4().hex[:16]}", "provider": "google", "email": email,
                          "created_at": _now()}},
        upsert=True, return_document=True, projection={"_id": 0})
    token = data.get("session_token") or uuid.uuid4().hex
    await _db.user_sessions.update_one(
        {"session_token": token},
        {"$set": {"session_token": token, "user_id": acc["user_id"], "created_at": _now(),
                  "expires_at": _now() + timedelta(days=GOOGLE_SESSION_DAYS)}}, upsert=True)
    return {"token": token, "account": _public(acc)}


# ---------- shared ----------
def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    return auth[7:].strip() if auth.lower().startswith("bearer ") else ""


async def require_user(request: Request) -> dict:
    """FastAPI dependency for every protected route: Clerk phone, email or Google sign-in."""
    token = _bearer(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not signed in")
    if token.count(".") == 2:
        try:
            alg = jwt.get_unverified_header(token).get("alg")
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        if alg == "HS256":
            try:
                claims = jwt.decode(token, _secret(), algorithms=["HS256"], issuer=ISSUER, audience=AUDIENCE,
                                    options={"require": ["sub", "iss", "aud", "iat", "exp"]})
            except jwt.PyJWTError:
                raise HTTPException(status_code=401, detail="Invalid or expired session")
            if claims.get("provider") != "email" or not str(claims["sub"]).startswith("email_"):
                raise HTTPException(status_code=401, detail="Invalid or expired session")
            if not await _db.auth_accounts.find_one({"user_id": claims["sub"]}, {"_id": 1}):
                raise HTTPException(status_code=401, detail="Account not found")
            return {"user_id": claims["sub"], "provider": "email"}
        user = await run_in_threadpool(clerk_auth.require_user, request)
        return {**user, "provider": "phone"}
    s = await _db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not s or s["expires_at"].replace(tzinfo=timezone.utc) <= _now():
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return {"user_id": s["user_id"], "provider": "google"}


async def account_of(user_id: str) -> dict | None:
    acc = await _db.auth_accounts.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return _public(acc) if acc else None


@router.post("/logout")
async def logout(request: Request):
    token = _bearer(request)
    if token and token.count(".") != 2:
        await _db.user_sessions.delete_one({"session_token": token})
    return {"ok": True}
