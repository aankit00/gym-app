"""Matches every plan move (free-exercise-db id) to the closest WorkoutX movement -> data/plan_matches.json.

Automatic name matching, then MANUAL overrides below (None = no good match, keep the photos).
Run after scripts/fetch_workoutx.py: python scripts/match_plans.py
"""

import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import library  # noqa: E402
from plans_data import USED_EXERCISE_IDS  # noqa: E402

MANUAL: dict[str, str | None] = {
    "Wind_Sprints": None, "Standing_Long_Jump": None, "Landmine_180s": None, "Knee_Tuck_Jump": None,
    "Pallof_Press_With_Rotation": None, "Side_to_Side_Box_Shuffle": None, "Weighted_Pull_Ups": "ex_UPWQ2O",
    "Stairmaster": "ex_S7P5NA", "Ab_Roller": "ex_EHLMJ7", "Box_Jump_Multiple_Response": "ex_3BVVUH",
    "Weighted_Jump_Squat": "ex_UXDJRO", "Prowler_Sprint": "ex_2ZPRBJ", "Thigh_Adductor": "ex_74BEI3",
    "Battling_Ropes": "ex_FZAE32", "Glute_Ham_Raise": "ex_3A2EJR", "Dips_-_Chest_Version": "ex_PP6TEI",
    "Glute_Kickback": "ex_AXQ7WG", "Plank": "ex_6JOB6L", "Pullups": "ex_UPWQ2O", "Pushups": "ex_PKMXFR",
    "Triceps_Pushdown": "ex_LLJJAG", "Triceps_Pushdown_-_Rope_Attachment": "ex_IE5GEE", "Rowing_Stationary": "ex_AORJKI",
    "Face_Pull": "ex_RGMFJU", "Freehand_Jump_Squat": "ex_XUVB7Y", "One-Legged_Cable_Kickback": "ex_IZFMME",
    "Rope_Jumping": "ex_BXNAXW", "Low_Cable_Crossover": "ex_XTBV3C", "Cable_Crunch": "ex_REWQH2",
    "Side_Lateral_Raise": "ex_UDDGLG", "Hyperextensions_Back_Extensions": "ex_LVM2OL", "Lateral_Bound": "ex_OQ6IAA",
    "Reverse_Flyes": "ex_WCTNRV", "Standing_Cable_Wood_Chop": "ex_W4UFSB", "Cable_Crossover": "ex_C455QP",
    "Clean_and_Press": "ex_FWPJZV", "Dips_-_Triceps_Version": "ex_7VYPL6", "Leg_Press": "ex_WOTCCC",
    "Single_Leg_Glute_Bridge": "ex_73JV5H", "Dumbbell_Flyes": "ex_VAUXSK", "External_Rotation_with_Cable": "ex_GDBY34",
    "One-Arm_Dumbbell_Row": "ex_U7I2E7", "Dumbbell_Bicep_Curl": "ex_B5ZYR5", "EZ-Bar_Skullcrusher": "ex_MWBUIJ",
    "Plyo_Push-up": "ex_O4MO37", "Tricep_Dumbbell_Kickback": "ex_QYTMLO", "Band_Assisted_Pull-Up": "ex_UGBP7X",
    "Dumbbell_Lunges": "ex_52QG4I", "Barbell_Squat": "ex_NEMYLA", "Incline_Push-Up": "ex_BYAIRV",
    "Seated_Dumbbell_Press": "ex_4EQJV2", "Hammer_Curls": "ex_5NDQ64", "Wide-Grip_Lat_Pulldown": "ex_STL56E",
    "Power_Clean": "ex_XXQ7CX", "Machine_Shoulder_Military_Press": "ex_SZFB65", "Thigh_Abductor": "ex_7QVWV6", "Cable_Seated_Lateral_Raise": "ex_CVVYVO", "Plie_Dumbbell_Squat": "ex_55EGD4",
}

STOP = {"the", "a", "with", "version", "medium", "grip", "-", "and"}


def norm(name: str) -> str:
    name = name.lower().replace("dumbbells", "dumbbell").replace("ups", "up").replace("raises", "raise")
    words = [w for w in re.split(r"[^a-z0-9]+", name) if w and w not in STOP]
    return " ".join(sorted(words))


wx = {i: norm(library.EX[i]["name"]) for i in library.CANONICAL if library.EX[i]["kind"] != "mobility"}
out, report = {}, []
for fe in USED_EXERCISE_IDS:
    if fe in MANUAL:
        out[fe] = MANUAL[fe]
        continue
    target = norm(library.PHOTOS[fe]["name"])
    best = max(wx, key=lambda i: difflib.SequenceMatcher(None, target, wx[i]).ratio())
    score = difflib.SequenceMatcher(None, target, wx[best]).ratio()
    out[fe] = best if score >= 0.75 else None
    report.append(f"{score:.2f}  {library.PHOTOS[fe]['name']!r:45} -> {library.EX[best]['name']!r} ({best})")

(ROOT / "data" / "plan_matches.json").write_text(json.dumps(out, indent=1))
print("\n".join(sorted(report)))
print(f"{sum(1 for v in out.values() if v)} of {len(out)} plan moves matched")
