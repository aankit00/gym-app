"""One-time load of the whole WorkoutX v2 catalogue (male + female models) into data/workoutx.json.

Free plan: 10 exercises per request and 500 requests in total, so this costs ~277 requests.
Pages are saved under data/workoutx_pages/ so a rerun resumes instead of paying again.
Signed media links that come back with each page go to data/workoutx_media_seed.json; the server
seeds its media cache from it (links expire in ~24h and are never downloaded or re-hosted).
Run: python scripts/fetch_workoutx.py
"""

import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
PAGES = ROOT / "data" / "workoutx_pages"
PAGES.mkdir(parents=True, exist_ok=True)
API = "https://api.workoutxapp.com/v2/exercises"
PAGE = 10

client = httpx.Client(headers={"X-WorkoutX-Key": os.environ["WORKOUTX_API_KEY"]}, timeout=30)


def page(model: str, offset: int) -> dict:
    path = PAGES / f"{model}_{offset}.json"
    if path.exists():
        return json.loads(path.read_text())
    for attempt in range(5):
        r = client.get(API, params={"model": model, "limit": PAGE, "offset": offset, "media": "true"})
        if r.status_code == 429:
            time.sleep(20 * (attempt + 1))
            continue
        r.raise_for_status()
        path.write_text(r.text)
        print(model, offset, "quota left", r.headers.get("x-quota-remaining"), flush=True)
        time.sleep(2.3)  # stay under 30 requests a minute
        return r.json()
    sys.exit(f"gave up at {model} {offset}")


exercises, media = {}, {}
for model in ("male", "female"):
    offset, total = 0, None
    while total is None or offset < total:
        data = page(model, offset)
        total = data["total"]
        for e in data["results"]:
            m = e.pop("media", None)
            if m and m.get("mp4"):
                media[e["id"]] = {k: m.get(k) for k in ("mp4", "poster", "expiresAt")}
            exercises[e["id"]] = e
        offset += PAGE

(ROOT / "data" / "workoutx.json").write_text(json.dumps(exercises, separators=(",", ":")))
(ROOT / "data" / "workoutx_media_seed.json").write_text(json.dumps(media, separators=(",", ":")))
print(f"done: {len(exercises)} exercises, {len(media)} media links")
