# GymProof: WorkoutX Exercise Library, Video Demos and Alternatives

GymProof's exercise library switches to WorkoutX, which has about 840 exercises with looping video demos and male and female models.
Every exercise gets a level and an **Alternatives** button with 5–6 swaps for the same muscles. A picked swap goes into the member's plan and stays there.

## Who it's for
- GymProof members on a workout plan who want to see a move done by someone like them, or need a swap because a machine is taken, they're sore, or the gear isn't there.
- Members who want to browse and learn moves by muscle and level, outside a plan.

## Core features and experience
- **One WorkoutX library for the whole app.** Plans, the exercise screen and the Library all use the same WorkoutX exercises and demos.
- **Looping video demos** play muted and on repeat, like a short animation.
- **Male and female demo models.** Each member sees the model that matches the gender in their profile. A small "Male / Female" switch on the exercise screen shows the other version when WorkoutX has one.
- **Exercise details:** main and secondary muscles, equipment, step-by-step instructions, tips, and WorkoutX's suggested sets and reps.
- **Level on every exercise:** Beginner, Intermediate or Pro, shown as a coloured chip.
- **Alternatives button** next to each move in a plan day and on the exercise screen. It opens a sheet of 5–6 options that train the same muscle. Each option shows its demo, level and equipment, and the options mix equipment (barbell, dumbbell, cable, machine, bodyweight, band) where the library has them.
- **Swap into plan.** Picking an alternative replaces that move in that plan day for that member only. The swap is remembered on every device. A swapped move shows a "Swapped" tag, and "Reset to original" puts it back.
- **Searchable Library inside the Plans tab:** a "Plans | Library" switch at the top, with search by name and filters for muscle group, level and equipment.
- **Plans keep working.** The 12 existing plans keep their days, sets and reps. Each move is matched to the closest WorkoutX exercise. If there is no good match, the move keeps its current photos, with a small "Similar movement" label.
- **Fallback demos.** If WorkoutX can't supply a video, the app shows the still start-and-finish photos it uses today. This happens when WorkoutX is down, an exercise has no video, or the plan's request allowance runs out. Nothing breaks.

## User flow
1. Plans tab → open a plan → pick a day → each move shows a demo thumbnail, sets and reps, and an **Alternatives** button.
2. Tap **Alternatives** → sheet with 5–6 swaps → preview one or tap **Use this** → the plan day updates and shows "Swapped".
3. Tap any move → exercise screen with the looping video, the Male/Female switch, level, muscles, steps and tips, plus Alternatives.
4. Plans tab → switch to **Library** → search or filter (e.g. Glutes · Beginner) → open an exercise. Alternatives works here too, but only to look; there is no plan to swap into.
5. Pro plans stay locked until paid. Locked plans don't show their moves or alternatives.

## UI/UX feel
- Same bold GymProof look as today.
- Videos loop quietly with no sound or controls. Only the one on screen plays, to save battery and data. List thumbnails are still images, and the video plays when the move is opened.
- Alternatives open in a bottom sheet so the plan day stays visible behind it.
- Level chip colours: Beginner green, Intermediate amber, Pro dark.
- The library list scrolls smoothly through all exercises, with filter chips pinned at the top.

## Implementation phases
**Phase 1 (MVP, built now)**
- Connect WorkoutX with your API key, kept only on the server.
- Load the WorkoutX library into the app, then search and filter it without extra WorkoutX requests.
- Video demos with the male/female model and the photo fallback.
- Alternatives (5–6 per exercise) on plan days and the exercise screen.
- Swaps saved per member, with "Reset to original".
- Library in the Plans tab with search and filters.
- Existing plans matched to WorkoutX exercises.

**Phase 2**
- Email & Google login, as accounts separate from phone login.
- Monthly Recap shareable card (verified visits, XP, consistency).

**Phase 3**
- Wider Milestones and Achievements.
- Home screen widget for Android and iPhone. This only works in an installed build, not in Expo Go.
- Razorpay webhook, so a payment is still credited if the member closes the app before returning to it.

## Assumptions
- **WorkoutX Free plan limits.** The plan you chose has 500 requests in total, not per month, and 10 exercises per request. Its videos are small (360p) and carry a WorkoutX watermark. Loading the library uses part of those 500 requests, and each refresh of demo links uses more. Once the 500 are gone, demos fall back to still photos until you upgrade. Moving to Starter or Growth later needs only a new key, no rebuild.
- **Video links are reused for up to a day.** WorkoutX video links expire after about 24 hours. The app uses one link for all members until it expires, then fetches a new one when someone opens that move. Video files are never downloaded or re-hosted, which WorkoutX's licence forbids.
- **Alternatives are worked out inside the app.** They are chosen from the stored library by main muscle and movement type, so they don't use WorkoutX requests. WorkoutX's own "alternatives" service is not used on the Free plan. Picks lean toward the plan's level, and Pro moves are only offered on Beginner plans when nothing else fits.
- **Demo model:** each member sees the model matching their profile gender. Other members see the male model, with the switch available to everyone.
- **Fallback:** when no video is available, the still start-and-finish photos from the current free library are shown.
- **Levels** come from WorkoutX where it gives them. Where it doesn't, they are set by how hard and technical the move is.
- **Swaps** change only the member's own copy of a plan, never anyone else's.
- **Credit:** a "Demos by WorkoutX" credit appears on the exercise screen.
- **Your WorkoutX API key** is collected through the secure key card when building starts. It is never shown in the app.
