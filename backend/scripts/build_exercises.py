"""Builds data/exercises.json: the whole exercise library used by plans, the Library tab and Alternatives.

Source: yuhonas/free-exercise-db (public domain): names, muscles, instructions and two photos
(start and finish) per exercise, which the app loops as an animation.
Form cues for a few common lifts come from namnq/workout-free-videos (CC0).
Run: python scripts/build_exercises.py
"""

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from plans_data import USED_EXERCISE_IDS  # noqa: E402

PHOTO_COMMIT = "f00c92c7dcf1216a928a52c3706c7ce8e2f71ed5"
PHOTO_BASE = f"https://cdn.jsdelivr.net/gh/yuhonas/free-exercise-db@{PHOTO_COMMIT}"
CUES_BASE = "https://cdn.jsdelivr.net/gh/namnq/workout-free-videos@v2.0.0"

# free-exercise-db id -> workout-free-videos slug with form cues for the same movement
CUE_SOURCES = {
    "Dumbbell_Bench_Press": "dumbbell-bench-press",
    "Barbell_Incline_Bench_Press_-_Medium_Grip": "incline-bench-press",
    "Dips_-_Chest_Version": "chest-dip",
    "Standing_Military_Press": "military-press",
    "Side_Lateral_Raise": "dumbbell-lateral-raise",
    "Close-Grip_Barbell_Bench_Press": "close-grip-bench-press",
    "EZ-Bar_Skullcrusher": "ez-bar-skullcrusher",
    "Barbell_Curl": "standing-barbell-curl",
    "Incline_Dumbbell_Curl": "incline-dumbbell-curl",
    "Barbell_Shrug": "barbell-shrug",
    "Upright_Barbell_Row": "barbell-upright-row",
    "Seated_Cable_Rows": "seated-cable-row",
    "Bent_Over_Barbell_Row": "bent-over-row",
    "Wide-Grip_Lat_Pulldown": "lat-pull-down",
    "Pullups": "wide-grip-pull-up",
    "Straight-Arm_Pulldown": "straight-arm-lat-pull-down",
    "Barbell_Hip_Thrust": "barbell-hip-thrust",
    "Hyperextensions_Back_Extensions": "hyperextension",
    "Barbell_Squat": "barbell-back-squat",
    "Leg_Press": "leg-press",
    "Seated_Leg_Curl": "seated-leg-curl",
    "Standing_Calf_Raises": "standing-machine-calf-raise",
    "Seated_Calf_Raise": "seated-calf-raise",
    "Thigh_Adductor": "hip-adduction-machine",
}

MUSCLE_GROUP = {
    "chest": "Chest",
    "lats": "Back", "middle back": "Back", "lower back": "Back", "traps": "Back",
    "shoulders": "Shoulders", "neck": "Shoulders",
    "biceps": "Arms", "triceps": "Arms", "forearms": "Arms",
    "quadriceps": "Legs", "hamstrings": "Legs", "calves": "Legs", "adductors": "Legs", "abductors": "Legs",
    "glutes": "Glutes",
    "abdominals": "Core",
}
CATEGORY_GROUP = {"stretching": "Mobility", "cardio": "Cardio"}
LEVELS = {"beginner": "beginner", "intermediate": "intermediate", "expert": "pro"}

source = requests.get(f"{PHOTO_BASE}/dist/exercises.json", timeout=60).json()
cues = {e["slug"]: e["cues"] for e in requests.get(f"{CUES_BASE}/data/exercises.json", timeout=60).json()}

out = {}
for e in source:
    if not e["images"] or not e["primaryMuscles"]:
        continue
    muscle = e["primaryMuscles"][0]
    slug = CUE_SOURCES.get(e["id"])
    out[e["id"]] = {
        "id": e["id"], "name": e["name"], "level": LEVELS[e["level"]], "gender": "both",
        "group": CATEGORY_GROUP.get(e["category"], MUSCLE_GROUP[muscle]),
        "category": e["category"], "force": e["force"], "mechanic": e["mechanic"],
        "equipment": e["equipment"] or "body only",
        "primary_muscles": e["primaryMuscles"], "secondary_muscles": e["secondaryMuscles"],
        "instructions": e["instructions"], "cues": cues.get(slug, []) if slug else [],
        "images": [f"{PHOTO_BASE}/exercises/{p}" for p in e["images"]],
    }

missing = [i for i in USED_EXERCISE_IDS if i not in out]
if missing:
    sys.exit(f"Plan exercises missing from the library: {missing}")

(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data" / "exercises.json").write_text(json.dumps(out, separators=(",", ":")))
print(f"{len(out)} exercises")
