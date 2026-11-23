"""Exercise library backed by the WorkoutX catalogue (data/workoutx.json, loaded once by scripts/fetch_workoutx.py).

- Search, filters and Alternatives are computed here from the stored catalogue: no WorkoutX requests.
- Video links are signed and expire after ~24h. They are cached in Mongo (wx_media) and shared by all members
  until they expire, then refreshed one exercise at a time when someone opens it. Files are never downloaded.
- Plan moves that have no good WorkoutX match keep their free-exercise-db photos (data/exercises.json).
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)
DATA = Path(__file__).parent / "data"
WX_API = "https://api.workoutxapp.com/v2"

GROUP_BY_TARGET = {
    "Pectorals": "Chest",
    "Lats": "Back", "Upper Back": "Back", "Traps": "Back", "Spine": "Back",
    "Delts": "Shoulders", "Levator Scapulae": "Shoulders",
    "Biceps": "Arms", "Triceps": "Arms", "Forearms": "Arms",
    "Quads": "Legs", "Hamstrings": "Legs", "Calves": "Legs", "Adductors": "Legs", "Abductors": "Legs",
    "Glutes": "Glutes",
    "Abs": "Core",
    "Cardiovascular System": "Cardio",
}
MOBILITY = {"flexibility", "yoga", "balance"}
GROUPS = ["Chest", "Back", "Shoulders", "Arms", "Legs", "Glutes", "Core", "Cardio", "Mobility"]
LEVEL = {"beginner": "beginner", "intermediate": "intermediate", "advanced": "pro"}
LEVEL_RANK = {"beginner": 0, "intermediate": 1, "pro": 2}


def _load(name: str) -> dict:
    path = DATA / name
    return json.loads(path.read_text()) if path.exists() else {}


RAW: dict[str, dict] = _load("workoutx.json")
PHOTOS: dict[str, dict] = _load("exercises.json")  # free-exercise-db, keyed by its own ids
# plan move (free-exercise-db id) -> closest WorkoutX canonical id, or null to keep the photos (scripts/match_plans.py)
PLAN_MATCH: dict[str, str | None] = _load("plan_matches.json")
PHOTO_OF = {wx: fe for fe, wx in PLAN_MATCH.items() if wx}  # WorkoutX id -> photos to show if its video is unavailable
FE_TARGET = {
    "chest": "Pectorals", "lats": "Lats", "middle back": "Upper Back", "lower back": "Spine", "traps": "Traps",
    "shoulders": "Delts", "neck": "Levator Scapulae", "biceps": "Biceps", "triceps": "Triceps", "forearms": "Forearms",
    "quadriceps": "Quads", "hamstrings": "Hamstrings", "calves": "Calves", "adductors": "Adductors",
    "abductors": "Abductors", "glutes": "Glutes", "abdominals": "Abs",
}


def _kind(e: dict) -> str:
    return "mobility" if e["category"] in MOBILITY else "cardio" if e["category"] == "cardio" else "strength"


def _normalize(e: dict) -> dict:
    primary = [m["group"] for m in e.get("primaryMuscles") or []]
    secondary = [m["group"] for m in e.get("secondaryMuscles") or []]
    return {
        "id": e["id"], "name": e["name"], "model": e.get("model"), "counterpart_id": e.get("counterpartId"),
        "level": LEVEL.get(e.get("difficulty"), "intermediate"),
        "group": "Mobility" if e["category"] in MOBILITY else GROUP_BY_TARGET.get(e.get("target"), "Core"),
        "target": e.get("target") or "", "equipment": (e.get("equipment") or "Body Weight"),
        "kind": _kind(e), "force": e.get("force"), "mechanic": e.get("mechanic"),
        "primary_muscles": primary, "secondary_muscles": secondary,
        "instructions": e.get("instructions") or [], "tips": e.get("tips") or [],
        "sets": e.get("recommendedSets"), "reps": e.get("recommendedReps"),
    }


EX: dict[str, dict] = {i: _normalize(e) for i, e in RAW.items()}


def canonical_id(ex_id: str) -> str:
    """Male and female versions of one movement share the male id; female-only moves keep their own."""
    e = EX[ex_id]
    cp = e["counterpart_id"]
    return cp if e["model"] == "female" and cp in EX else ex_id


CANONICAL = sorted({canonical_id(i) for i in EX}, key=lambda i: EX[i]["name"].lower())


def variant(ex_id: str, model: str | None) -> str:
    """The id of the requested model's version of this movement (itself if there is no such version)."""
    e = EX[ex_id]
    if model and e["model"] != model and e["counterpart_id"] in EX:
        return e["counterpart_id"]
    return ex_id


def models_of(ex_id: str) -> dict:
    e = EX[ex_id]
    out = {e["model"]: ex_id}
    if e["counterpart_id"] in EX:
        out[EX[e["counterpart_id"]]["model"]] = e["counterpart_id"]
    return out


# ---------- media cache ----------
_db = None
_media: dict[str, dict] = {}  # in-memory copy of wx_media: id -> {mp4, poster, expires_at}
_locks: dict[str, asyncio.Lock] = {}
_paused_until = 0.0  # set when WorkoutX refuses (quota used up, down) so we stop asking for a while


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _fresh(m: dict | None, margin_min: int = 10) -> bool:
    return bool(m) and m["expires_at"] > datetime.now(timezone.utc) + timedelta(minutes=margin_min)


async def init(db) -> None:
    """Load cached links into memory and add any newer ones from the catalogue load."""
    global _db
    _db = db
    seed = _load("workoutx_media_seed.json")
    async for doc in db.wx_media.find({}, {"_id": 0}):
        _media[doc["id"]] = {**doc, "expires_at": doc["expires_at"].replace(tzinfo=timezone.utc)}
    for ex_id, m in seed.items():
        item = {"id": ex_id, "mp4": m["mp4"], "poster": m["poster"], "expires_at": _parse(m["expiresAt"])}
        if _fresh(item, 0) and (ex_id not in _media or _media[ex_id]["expires_at"] < item["expires_at"]):
            _media[ex_id] = item
            await db.wx_media.update_one({"id": ex_id}, {"$set": item}, upsert=True)
    logger.info("library: %d exercises, %d cached media links", len(EX), sum(1 for m in _media.values() if _fresh(m, 0)))


def cached_poster(ex_id: str) -> str | None:
    m = _media.get(ex_id)
    return m["poster"] if _fresh(m) else None


async def media(ex_id: str) -> dict | None:
    """Valid video + poster links for one exercise, refreshing from WorkoutX (1 request) only when expired."""
    global _paused_until
    if _fresh(_media.get(ex_id)):
        return _media[ex_id]
    key = os.environ.get("WORKOUTX_API_KEY", "")
    if not key or time.time() < _paused_until:
        return None
    async with _locks.setdefault(ex_id, asyncio.Lock()):
        if _fresh(_media.get(ex_id)):
            return _media[ex_id]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{WX_API}/exercises/{ex_id}/media", headers={"X-WorkoutX-Key": key})
            if r.status_code in (401, 402, 403, 429) or r.status_code >= 500:
                _paused_until = time.time() + 600
                logger.warning("WorkoutX media %s refused (%s); using photos for 10 min", ex_id, r.status_code)
                return None
            r.raise_for_status()
            m = r.json().get("media") or r.json()
            if not m.get("mp4"):
                return None
            item = {"id": ex_id, "mp4": m["mp4"], "poster": m.get("poster"), "expires_at": _parse(m["expiresAt"])}
        except Exception as exc:
            logger.warning("WorkoutX media %s failed: %s", ex_id, exc)
            return None
        _media[ex_id] = item
        if _db is not None:
            await _db.wx_media.update_one({"id": ex_id}, {"$set": item}, upsert=True)
        return item


# ---------- library views ----------
def card(ex_id: str, model: str | None = None, poster: bool = True) -> dict:
    """Compact row for lists. `ex_id` is canonical; the thumbnail follows the member's demo model when cached.
    poster=False skips WorkoutX posters: loading hundreds of them while scrolling gets the account paused."""
    e = EX[ex_id]
    shown = variant(ex_id, model)
    photos = photos_for(ex_id)
    thumb = (cached_poster(shown) or cached_poster(ex_id)) if poster else None
    return {"id": ex_id, "name": e["name"], "level": e["level"], "group": e["group"], "target": e["target"],
            "equipment": e["equipment"], "thumb": thumb or (photos[0] if photos else None)}


def library(model: str | None) -> dict:
    items = [card(i, model, poster=False) for i in CANONICAL]
    return {"items": items, "groups": [g for g in GROUPS if any(i["group"] == g for i in items)],
            "equipment": sorted({i["equipment"] for i in items})}


def photo_exercise(fe_id: str) -> dict:
    """A plan move with no WorkoutX match, shown with free-exercise-db photos."""
    p = PHOTOS[fe_id]
    return {"id": fe_id, "canonical_id": fe_id, "name": p["name"], "model": None, "models": {},
            "level": p["level"], "group": p["group"], "target": p["primary_muscles"][0], "equipment": p["equipment"],
            "primary_muscles": p["primary_muscles"], "secondary_muscles": p["secondary_muscles"],
            "instructions": p["instructions"], "tips": p.get("cues") or [], "sets": None, "reps": None,
            "video": None, "poster": None, "images": p["images"], "similar": True, "source": "free-exercise-db"}


async def detail(ex_id: str, model: str | None, fallback_photos: list[str]) -> dict:
    canon = canonical_id(ex_id)
    shown = variant(canon, model) if model else ex_id
    e = EX[shown]
    m = await media(shown)
    return {"id": shown, "canonical_id": canon, "name": e["name"], "model": e["model"], "models": models_of(canon),
            "level": e["level"], "group": e["group"], "target": e["target"], "equipment": e["equipment"],
            "primary_muscles": e["primary_muscles"], "secondary_muscles": e["secondary_muscles"],
            "instructions": e["instructions"], "tips": e["tips"], "sets": e["sets"], "reps": e["reps"],
            "video": m["mp4"] if m else None, "poster": m["poster"] if m else None,
            "images": fallback_photos, "similar": False, "source": "workoutx"}


GEAR_WORDS = {"barbell", "dumbbell", "dumbbells", "band", "resistance", "cable", "kettlebell", "machine", "smith", "lever",
              "ez", "weighted", "assisted", "bodyweight", "plate", "with", "on", "the", "and", "of", "to", "in"}


def _move_words(name: str) -> set[str]:
    return {w for w in name.lower().replace("-", " ").replace("(", " ").replace(")", " ").split() if w not in GEAR_WORDS}


def _score(x: dict, y: dict, target_level: str) -> float:
    s = 0.0
    if y["force"] == x["force"]:
        s += 3
    if y["mechanic"] == x["mechanic"]:
        s += 2
    s += 2 * len(set(x["primary_muscles"]) & set(y["primary_muscles"]))
    s += 0.5 * len(set(x["secondary_muscles"]) & set(y["secondary_muscles"]))
    gap = LEVEL_RANK[y["level"]] - LEVEL_RANK[target_level]
    s -= 1.5 * gap if gap > 0 else 0.5 * -gap  # harder than the plan costs more than easier
    s += 1.5 * len(_move_words(x["name"]) & _move_words(y["name"]))  # same movement, other gear
    if target_level == "beginner" and y["level"] == "pro":
        s -= 20  # only when nothing else fits
    if y["equipment"] == x["equipment"]:
        s -= 0.5  # nudge towards different gear
    s -= 0.4 * max(0, len(y["name"].split()) - 3)  # prefer plain, well-known moves over niche variations
    if "(" in y["name"]:
        s -= 1  # camera-angle duplicates like "(Side View)"
    return s


def resolve_plan_move(fe_id: str) -> str:
    """The id a plan move shows: its WorkoutX match, or the original photo exercise."""
    return PLAN_MATCH.get(fe_id) or fe_id


def photos_for(ex_id: str) -> list[str]:
    fe = PHOTO_OF.get(ex_id) or PHOTO_OF.get(canonical_id(ex_id)) if ex_id in EX else ex_id
    return PHOTOS[fe]["images"] if fe in PHOTOS else []


def _as_query(ex_id: str) -> dict:
    """Library entry or photo exercise, in the shape the Alternatives scorer reads."""
    if ex_id in EX:
        return EX[canonical_id(ex_id)]
    p = PHOTOS[ex_id]
    return {"id": ex_id, "name": p["name"], "level": p["level"], "equipment": "", "force": p.get("force"),
            "mechanic": p.get("mechanic"), "primary_muscles": [], "secondary_muscles": [],
            "target": FE_TARGET.get(p["primary_muscles"][0], ""), "group": p["group"],
            "kind": "mobility" if p.get("category") == "stretching" else "cardio" if p.get("category") == "cardio" else "strength"}


def alternatives(ex_id: str, target_level: str | None, n: int = 6) -> list[str]:
    """5–6 canonical ids training the same muscle, mixing equipment where the library allows."""
    x = _as_query(ex_id)
    canon = x["id"]
    level = target_level or x["level"]
    pool = [EX[i] for i in CANONICAL if i != canon and EX[i]["kind"] == x["kind"] and EX[i]["target"] == x["target"]]
    if len(pool) < n:
        pool += [EX[i] for i in CANONICAL if i != canon and EX[i]["kind"] == x["kind"]
                 and EX[i]["group"] == x["group"] and EX[i]["target"] != x["target"]]
    ranked = sorted(pool, key=lambda y: (-_score(x, y, level), y["name"]))
    picked, gear, names = [], set(), {x["name"].lower()}
    top = _score(x, ranked[0], level) if ranked else 0
    for only_new_gear in (True, False):
        for y in ranked:
            if len(picked) >= n:
                break
            if y["id"] in picked or y["name"].lower() in names or (only_new_gear and y["equipment"] in gear):
                continue
            if only_new_gear and _score(x, y, level) < top - 2.5:
                continue
            picked.append(y["id"])
            gear.add(y["equipment"])
            names.add(y["name"].lower())
    return picked


def level_of_plan(plan_level: str) -> str | None:
    lv = plan_level.lower()
    if lv.startswith("beginner"):
        return "beginner"
    if lv.startswith("intermediate"):
        return "intermediate"
    if lv.startswith("advanced"):
        return "pro"
    return None
