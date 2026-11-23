"""Training plans. Edit plans here; after adding an exercise id that isn't in data/exercises.json yet,
run `python scripts/build_exercises.py` to pull its details and demo media.

Exercise ids come from the public-domain free-exercise-db. A line is "id | sets | reps | rest seconds".
"""

import json
from pathlib import Path


def _day(title: str, focus: str, lines: str) -> dict:
    exercises = []
    for line in lines.strip().splitlines():
        ex_id, sets, reps, rest = (p.strip() for p in line.split("|"))
        exercises.append({"id": ex_id, "sets": int(sets), "reps": reps, "rest_sec": int(rest)})
    return {"title": title, "focus": focus, "exercises": exercises}


BENCH = "Barbell_Bench_Press_-_Medium_Grip"

D = {
    # ----- general strength / size -----
    "upper_strength": _day("Upper Strength", "Chest, back, shoulders", f"""
        {BENCH} | 4 | 6-8 | 120
        Bent_Over_Barbell_Row | 4 | 6-8 | 120
        Standing_Military_Press | 3 | 8-10 | 90
        Wide-Grip_Lat_Pulldown | 3 | 10-12 | 75
        Barbell_Curl | 3 | 10-12 | 60
        Triceps_Pushdown | 3 | 10-12 | 60"""),
    "lower_strength": _day("Lower Strength", "Quads, hamstrings, calves", """
        Barbell_Squat | 4 | 6-8 | 150
        Romanian_Deadlift | 3 | 8-10 | 120
        Leg_Press | 3 | 10-12 | 90
        Seated_Leg_Curl | 3 | 12 | 60
        Standing_Calf_Raises | 4 | 12-15 | 45
        Plank | 3 | 45 sec | 45"""),
    "upper_volume": _day("Upper Volume", "Muscle-building pump", """
        Incline_Dumbbell_Press | 4 | 8-10 | 90
        Seated_Cable_Rows | 4 | 10 | 75
        Dumbbell_Shoulder_Press | 3 | 10 | 75
        Pullups | 3 | Max reps | 90
        Side_Lateral_Raise | 3 | 12-15 | 45
        Hammer_Curls | 3 | 12 | 45
        EZ-Bar_Skullcrusher | 3 | 12 | 45"""),
    "lower_volume": _day("Lower Volume", "Posterior chain and legs", """
        Barbell_Deadlift | 3 | 5 | 180
        Front_Barbell_Squat | 3 | 8 | 120
        Dumbbell_Lunges | 3 | 10 each leg | 75
        Leg_Extensions | 3 | 12-15 | 60
        Seated_Calf_Raise | 4 | 15 | 45
        Hanging_Leg_Raise | 3 | 12 | 45"""),
    "chest": _day("Chest", "Heavy press, then stretch and squeeze", f"""
        {BENCH} | 4 | 6-8 | 150
        Incline_Dumbbell_Press | 4 | 8-10 | 90
        Dips_-_Chest_Version | 3 | 10 | 90
        Cable_Crossover | 3 | 12-15 | 60
        Dumbbell_Flyes | 3 | 12 | 60
        Pushups | 2 | Max reps | 60"""),
    "back": _day("Back", "Thickness and width", """
        Barbell_Deadlift | 4 | 5 | 180
        Pullups | 4 | 8 | 90
        Bent_Over_Barbell_Row | 4 | 8 | 90
        Wide-Grip_Lat_Pulldown | 3 | 10-12 | 75
        Seated_Cable_Rows | 3 | 12 | 60
        Straight-Arm_Pulldown | 3 | 15 | 45"""),
    "shoulders": _day("Shoulders", "Boulder delts and traps", """
        Standing_Military_Press | 4 | 6-8 | 120
        Arnold_Dumbbell_Press | 3 | 10 | 75
        Side_Lateral_Raise | 4 | 12-15 | 45
        Face_Pull | 3 | 15 | 45
        Reverse_Flyes | 3 | 15 | 45
        Barbell_Shrug | 4 | 12 | 60"""),
    "legs": _day("Legs", "Full leg day", """
        Barbell_Squat | 4 | 6-8 | 150
        Leg_Press | 4 | 10-12 | 90
        Romanian_Deadlift | 4 | 8-10 | 120
        Leg_Extensions | 3 | 15 | 60
        Lying_Leg_Curls | 3 | 12 | 60
        Standing_Calf_Raises | 5 | 12 | 45"""),
    "arms": _day("Arms & Abs", "Biceps, triceps, core", """
        Close-Grip_Barbell_Bench_Press | 4 | 8 | 90
        Barbell_Curl | 4 | 8-10 | 75
        EZ-Bar_Skullcrusher | 3 | 10-12 | 60
        Incline_Dumbbell_Curl | 3 | 12 | 60
        Triceps_Pushdown_-_Rope_Attachment | 3 | 12-15 | 45
        Hammer_Curls | 3 | 12 | 45
        Cable_Crunch | 3 | 15 | 45"""),
    # ----- fat loss -----
    "shred_push": _day("Push Burn", "Chest, shoulders, triceps with short rests", """
        Dumbbell_Bench_Press | 3 | 12 | 45
        Dumbbell_Shoulder_Press | 3 | 12 | 45
        Pushups | 3 | Max reps | 45
        Triceps_Pushdown | 3 | 15 | 30
        Side_Lateral_Raise | 3 | 15 | 30
        Rope_Jumping | 5 | 60 sec | 30"""),
    "shred_pull": _day("Pull Burn", "Back, biceps, core", """
        Wide-Grip_Lat_Pulldown | 3 | 12 | 45
        One-Arm_Dumbbell_Row | 3 | 12 each side | 45
        Face_Pull | 3 | 15 | 30
        Dumbbell_Bicep_Curl | 3 | 15 | 30
        Hanging_Leg_Raise | 3 | 12 | 45
        Rowing_Stationary | 1 | 10 min steady | 0"""),
    "shred_legs": _day("Leg Burn", "High-rep legs", """
        Dumbbell_Squat | 4 | 12 | 60
        Barbell_Walking_Lunge | 3 | 20 steps | 60
        Romanian_Deadlift | 3 | 12 | 60
        Leg_Extensions | 3 | 15 | 45
        Freehand_Jump_Squat | 3 | 15 | 45
        Stairmaster | 1 | 10 min | 0"""),
    "hiit": _day("HIIT & Core", "Sweat session", """
        Battling_Ropes | 6 | 30 sec | 30
        Box_Jump_Multiple_Response | 4 | 8 | 45
        Rope_Jumping | 5 | 60 sec | 30
        Air_Bike | 3 | 20 | 30
        Russian_Twist | 3 | 20 | 30
        Plank | 3 | 60 sec | 30"""),
    "shred_full": _day("Full Body Finisher", "Big moves, heart rate up", """
        Clean_and_Press | 4 | 8 | 75
        Chin-Up | 3 | Max reps | 75
        Dumbbell_Step_Ups | 3 | 12 each leg | 45
        Pushups | 3 | Max reps | 45
        Reverse_Crunch | 3 | 15 | 30
        Running_Treadmill | 1 | 15 min intervals | 0"""),
    # ----- 30+ joint friendly -----
    "prime_upper_a": _day("Upper Body A", "Joint-friendly push and pull", """
        Machine_Bench_Press | 3 | 10-12 | 75
        Seated_Cable_Rows | 3 | 10-12 | 75
        Machine_Shoulder_Military_Press | 3 | 10 | 75
        Wide-Grip_Lat_Pulldown | 3 | 12 | 60
        Face_Pull | 3 | 15 | 45
        External_Rotation_with_Cable | 2 | 15 each side | 30"""),
    "prime_lower_a": _day("Lower Body A", "Strong legs, happy knees", """
        Leg_Press | 4 | 10-12 | 90
        Romanian_Deadlift | 3 | 10 | 90
        Seated_Leg_Curl | 3 | 12 | 60
        Leg_Extensions | 3 | 12 | 60
        Standing_Calf_Raises | 3 | 15 | 45
        Dead_Bug | 3 | 10 each side | 30"""),
    "prime_upper_b": _day("Upper Body B", "Dumbbells and cables", """
        Incline_Dumbbell_Press | 3 | 10 | 75
        One-Arm_Dumbbell_Row | 3 | 10 each side | 60
        Side_Lateral_Raise | 3 | 15 | 45
        Dumbbell_Bicep_Curl | 3 | 12 | 45
        Triceps_Pushdown_-_Rope_Attachment | 3 | 12 | 45
        Pallof_Press | 3 | 10 each side | 30"""),
    "prime_lower_b": _day("Lower Body B", "Hips, back and core", """
        Trap_Bar_Deadlift | 3 | 6-8 | 120
        Dumbbell_Step_Ups | 3 | 10 each leg | 60
        Barbell_Glute_Bridge | 3 | 12 | 60
        Hyperextensions_Back_Extensions | 3 | 12 | 45
        Plank | 3 | 45 sec | 30
        Walking_Treadmill | 1 | 15 min incline walk | 0"""),
    # ----- athlete -----
    "ath_power_lower": _day("Lower Power", "Explosive legs", """
        Power_Clean | 5 | 3 | 150
        Front_Barbell_Squat | 4 | 5 | 150
        Box_Jump_Multiple_Response | 4 | 5 | 60
        Romanian_Deadlift | 3 | 8 | 90
        Glute_Ham_Raise | 3 | 8 | 75
        Hanging_Leg_Raise | 3 | 12 | 45"""),
    "ath_power_upper": _day("Upper Power", "Press, pull, rotate", f"""
        {BENCH} | 4 | 5 | 150
        Weighted_Pull_Ups | 4 | 5 | 120
        Clean_and_Press | 4 | 5 | 120
        Plyo_Push-up | 3 | 8 | 60
        Bent_Over_Barbell_Row | 3 | 8 | 90
        Landmine_180s | 3 | 10 each side | 45"""),
    "ath_speed": _day("Speed & Agility", "Sprint, jump, change direction", """
        Wind_Sprints | 8 | 40 m | 60
        Lateral_Bound | 4 | 6 each side | 45
        Standing_Long_Jump | 4 | 5 | 60
        Prowler_Sprint | 6 | 20 m | 75
        Side_to_Side_Box_Shuffle | 3 | 30 sec | 45
        Pallof_Press_With_Rotation | 3 | 10 each side | 30"""),
    "ath_strength": _day("Total Strength", "Heavy pull and single-leg work", """
        Barbell_Deadlift | 4 | 4 | 180
        Barbell_Walking_Lunge | 3 | 16 steps | 90
        Single_Leg_Glute_Bridge | 3 | 12 each leg | 45
        Knee_Tuck_Jump | 3 | 8 | 60
        Standing_Calf_Raises | 3 | 15 | 45
        Standing_Cable_Wood_Chop | 3 | 12 each side | 30"""),
    "ath_engine": _day("Engine Builder", "Conditioning that carries over", """
        Rowing_Stationary | 5 | 500 m | 90
        Battling_Ropes | 6 | 30 sec | 30
        Weighted_Jump_Squat | 4 | 8 | 60
        Chin-Up | 3 | Max reps | 75
        Dips_-_Chest_Version | 3 | 10 | 60
        Plank | 3 | 60 sec | 30"""),
    # ----- V-taper -----
    "taper_width": _day("Back Width", "Wide lats, capped delts", """
        Weighted_Pull_Ups | 4 | 6-8 | 120
        Wide-Grip_Lat_Pulldown | 4 | 10 | 75
        One-Arm_Dumbbell_Row | 3 | 10 each side | 75
        Straight-Arm_Pulldown | 3 | 15 | 45
        Side_Lateral_Raise | 5 | 15 | 45
        Face_Pull | 3 | 15 | 45"""),
    "taper_chest": _day("Upper Chest & Delts", "The armour plate", """
        Barbell_Incline_Bench_Press_-_Medium_Grip | 4 | 6-8 | 120
        Dumbbell_Bench_Press | 3 | 10 | 90
        Low_Cable_Crossover | 3 | 15 | 45
        Dumbbell_Shoulder_Press | 3 | 10 | 75
        Cable_Seated_Lateral_Raise | 4 | 15 | 45
        Dips_-_Triceps_Version | 3 | 10 | 75"""),
    "taper_core": _day("Delts, Traps & Abs", "Small waist, big frame", """
        Arnold_Dumbbell_Press | 4 | 10 | 75
        Upright_Barbell_Row | 3 | 12 | 60
        Reverse_Flyes | 3 | 15 | 45
        Barbell_Shrug | 3 | 12 | 60
        Hanging_Leg_Raise | 4 | 12 | 45
        Cable_Crunch | 3 | 15 | 45
        Ab_Roller | 3 | 10 | 45"""),
    # ----- women: glutes / shape -----
    "glute_heavy": _day("Glute Power", "Heavy hip thrusts and hinges", """
        Barbell_Hip_Thrust | 4 | 8-10 | 120
        Romanian_Deadlift | 4 | 10 | 90
        Barbell_Squat | 3 | 10 | 120
        One-Legged_Cable_Kickback | 3 | 15 each leg | 45
        Thigh_Abductor | 3 | 20 | 45
        Barbell_Glute_Bridge | 3 | 15 | 60"""),
    "glute_quad": _day("Legs & Glutes", "Quads, glutes, calves", """
        Barbell_Squat | 4 | 8-10 | 120
        Split_Squat_with_Dumbbells | 3 | 10 each leg | 75
        Leg_Press | 3 | 12 | 90
        Dumbbell_Step_Ups | 3 | 12 each leg | 60
        Leg_Extensions | 3 | 15 | 45
        Standing_Calf_Raises | 3 | 15 | 45"""),
    "glute_ham": _day("Glutes & Hamstrings", "Back-of-leg sculpt", """
        Sumo_Deadlift | 4 | 8 | 120
        Barbell_Hip_Thrust | 3 | 12 | 90
        Dumbbell_Rear_Lunge | 3 | 12 each leg | 60
        Lying_Leg_Curls | 3 | 12 | 60
        Pull_Through | 3 | 15 | 45
        Glute_Kickback | 3 | 15 each leg | 30"""),
    "w_upper": _day("Upper Body Tone", "Back, shoulders, arms", """
        Wide-Grip_Lat_Pulldown | 3 | 12 | 60
        Dumbbell_Shoulder_Press | 3 | 12 | 60
        Seated_Cable_Rows | 3 | 12 | 60
        Incline_Dumbbell_Press | 3 | 12 | 60
        Side_Lateral_Raise | 3 | 15 | 45
        Tricep_Dumbbell_Kickback | 3 | 15 | 30
        Dumbbell_Bicep_Curl | 3 | 12 | 30"""),
    "hg_shoulder_back": _day("Shoulders & Back", "Build the top of the hourglass", """
        Seated_Dumbbell_Press | 4 | 10 | 75
        Side_Lateral_Raise | 4 | 15 | 45
        Wide-Grip_Lat_Pulldown | 4 | 12 | 60
        Seated_Cable_Rows | 3 | 12 | 60
        Reverse_Flyes | 3 | 15 | 45
        Face_Pull | 3 | 15 | 45"""),
    "hg_waist": _day("Waist & Core", "Tight core without thickening the waist", """
        Plank | 3 | 60 sec | 30
        Dead_Bug | 3 | 12 each side | 30
        Pallof_Press | 3 | 12 each side | 30
        Hanging_Leg_Raise | 3 | 10 | 45
        Reverse_Crunch | 3 | 15 | 30
        Stairmaster | 1 | 15 min | 0"""),
    "hg_combo": _day("Curves Combo", "Glutes plus shoulders", """
        Barbell_Hip_Thrust | 4 | 12 | 90
        Arnold_Dumbbell_Press | 3 | 12 | 60
        One-Arm_Dumbbell_Row | 3 | 12 each side | 60
        Thigh_Abductor | 3 | 20 | 45
        Cable_Seated_Lateral_Raise | 3 | 15 | 45
        Glute_Kickback | 3 | 15 each leg | 30"""),
    # ----- women: fat loss -----
    "burn_lower": _day("Lower Body Burn", "Legs and glutes, short rests", """
        Dumbbell_Squat | 4 | 15 | 45
        Dumbbell_Lunges | 3 | 12 each leg | 45
        Barbell_Glute_Bridge | 3 | 15 | 45
        Freehand_Jump_Squat | 3 | 12 | 45
        Step-up_with_Knee_Raise | 3 | 12 each leg | 30
        Stairmaster | 1 | 12 min | 0"""),
    "burn_upper": _day("Upper Body Burn", "Tone and sweat", """
        Wide-Grip_Lat_Pulldown | 3 | 15 | 45
        Incline_Push-Up | 3 | 12 | 45
        Dumbbell_Shoulder_Press | 3 | 15 | 45
        One-Arm_Dumbbell_Row | 3 | 12 each side | 45
        Battling_Ropes | 5 | 30 sec | 30
        Rope_Jumping | 5 | 60 sec | 30"""),
    "burn_full": _day("Full Body Sculpt", "Everything in one session", """
        Plie_Dumbbell_Squat | 3 | 15 | 45
        Stiff-Legged_Dumbbell_Deadlift | 3 | 12 | 60
        Incline_Push-Up | 3 | 12 | 45
        Bent_Over_Two-Dumbbell_Row | 3 | 12 | 45
        Air_Bike | 3 | 20 | 30
        Rowing_Stationary | 1 | 10 min | 0"""),
    # ----- women: strength -----
    "w_strength_lower": _day("Heavy Lower", "Squat and deadlift", """
        Barbell_Squat | 4 | 5 | 150
        Barbell_Deadlift | 3 | 5 | 180
        Barbell_Hip_Thrust | 3 | 8 | 120
        Barbell_Lunge | 3 | 8 each leg | 90
        Hanging_Leg_Raise | 3 | 10 | 45"""),
    "w_strength_upper": _day("Heavy Upper", "Bench, row, press", f"""
        {BENCH} | 4 | 5 | 150
        Bent_Over_Barbell_Row | 4 | 6 | 120
        Standing_Military_Press | 3 | 6 | 120
        Band_Assisted_Pull-Up | 3 | Max reps | 90
        Triceps_Pushdown | 3 | 12 | 45
        Hammer_Curls | 3 | 12 | 45"""),
    "glow_glute": _day("Hips & Glutes", "Machines and controlled moves", """
        Barbell_Glute_Bridge | 3 | 12 | 60
        Dumbbell_Step_Ups | 3 | 10 each leg | 60
        Thigh_Abductor | 3 | 15 | 45
        Thigh_Adductor | 3 | 15 | 45
        Seated_Leg_Curl | 3 | 12 | 60
        Dead_Bug | 3 | 10 each side | 30"""),
}


def _plan(pid, gender, name, tagline, goal, level, weeks, premium, icon, description, days) -> dict:
    return {"id": pid, "gender": gender, "name": name, "tagline": tagline, "goal": goal, "level": level,
            "duration_weeks": weeks, "premium": premium, "icon": icon, "description": description,
            "days_per_week": len(days), "days": [{"day": i + 1, **D[k]} for i, k in enumerate(days)]}


PLANS = [
    # ---------- Men ----------
    _plan("lean-machine", "male", "Lean Machine", "Lean muscle gain", "Lean muscle", "Beginner to intermediate", 8, False, "body",
          "Add muscle without the fluff. Two strength days and two volume days hit every muscle twice a week.",
          ["upper_strength", "lower_strength", "upper_volume", "lower_volume"]),
    _plan("mass-monster", "male", "Mass Monster", "The ultimate bulk", "Bulk", "Intermediate", 10, False, "barbell",
          "A classic five-day split. One muscle group a day, heavy compound lifts first, then volume. Eat big.",
          ["chest", "back", "shoulders", "legs", "arms"]),
    _plan("shred-mode", "male", "Shred Mode", "Strip fat, keep muscle", "Fat loss", "All levels", 8, False, "flame",
          "Short rests, high reps and conditioning finishers five days a week to burn fat while holding on to muscle.",
          ["shred_push", "shred_pull", "shred_legs", "hiit", "shred_full"]),
    _plan("prime-after-30", "male", "Prime After 30", "Fit, strong and pain-free", "Stay fit", "All levels", 8, False, "shield-checkmark",
          "Built for busy bodies over 30. Joint-friendly machines and dumbbells, sensible volume, core and shoulder care.",
          ["prime_upper_a", "prime_lower_a", "prime_upper_b", "prime_lower_b"]),
    _plan("apex-athlete", "male", "Apex Athlete", "Train like a pro athlete", "Athletic body", "Advanced", 10, True, "flash",
          "Power, speed, strength and engine. Olympic lifts, jumps and sprints for a body that performs as good as it looks.",
          ["ath_power_lower", "ath_power_upper", "ath_speed", "ath_strength", "ath_engine"]),
    _plan("greek-god", "male", "Greek God", "V-taper aesthetics", "Aesthetics", "Intermediate", 12, True, "trophy",
          "Wide back, capped shoulders, upper chest and a tight waist. Five days aimed squarely at the classic V shape.",
          ["taper_width", "taper_chest", "legs", "taper_core", "arms"]),
    # ---------- Women ----------
    _plan("peach-protocol", "female", "Peach Protocol", "Booty builder", "Glutes", "Beginner to intermediate", 8, False, "heart",
          "Three glute-focused lower days and one upper day. Hip thrusts, hinges and kickbacks to build and lift.",
          ["glute_heavy", "w_upper", "glute_quad", "glute_ham"]),
    _plan("burn-and-sculpt", "female", "Burn & Sculpt", "Fat loss and tone", "Fat loss", "All levels", 8, False, "flame",
          "Lifting circuits with cardio finishers. Burns calories in the gym and builds the shape underneath.",
          ["burn_lower", "burn_upper", "burn_full", "hiit"]),
    _plan("strong-not-skinny", "female", "Strong Not Skinny", "Lift heavy, feel powerful", "Strength", "Intermediate", 10, False, "barbell",
          "Squat, bench, deadlift and press, backed by glute and upper-body work. Strength first, shape follows.",
          ["w_strength_lower", "w_strength_upper", "glute_ham", "w_upper"]),
    _plan("glow-after-30", "female", "Glow After 30", "Strong, lean and energised", "Stay fit", "All levels", 8, False, "sunny",
          "Joint-friendly strength training that protects bones, lifts the glutes and keeps energy high.",
          ["prime_lower_a", "prime_upper_a", "glow_glute", "prime_upper_b"]),
    _plan("hourglass-code", "female", "Hourglass Code", "Curves up top and below", "Hourglass", "Intermediate", 12, True, "hourglass",
          "Build shoulders, back and glutes while keeping the waist tight. Five days designed around the hourglass shape.",
          ["glute_heavy", "hg_shoulder_back", "glute_quad", "hg_waist", "hg_combo"]),
    _plan("femme-athlete", "female", "Femme Athlete", "Athletic and powerful", "Athletic body", "Advanced", 10, True, "flash",
          "Jump higher, sprint faster, lift heavier. Power and speed work blended with glute and upper-body strength.",
          ["ath_power_lower", "w_strength_upper", "ath_speed", "glute_ham", "ath_engine"]),
]

PLANS_BY_ID = {p["id"]: p for p in PLANS}
USED_EXERCISE_IDS = sorted({e["id"] for d in D.values() for e in d["exercises"]})

_catalogue = Path(__file__).parent / "data" / "exercises.json"
EXERCISES: dict[str, dict] = json.loads(_catalogue.read_text()) if _catalogue.exists() else {}
