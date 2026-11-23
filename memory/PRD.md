# GymProof — PRD

## Original problem
A gym accountability app built on proof of workout. Welcome screen with Get Started → Clerk login → onboarding (name, age, height, gender, goal) → main app with bottom tabs (styled like the reference "STATISTICS" screenshot). Proving a workout opens the in-app camera only (no gallery). AI checks for a hand gripping gym equipment and marks the day complete. Weekly streaks, XP gamification, local (city) competition, a widget-style streak card, milestones and achievements.

## User choices
- Gemini 3 Flash vision (Emergent LLM key)
- Emergent Managed Clerk, phone OTP only (the playbook supports phone only)
- Proof = hand gripping any gym equipment
- Private streak + city XP leaderboard
- Core features only (real home-screen widgets need native builds; deferred)

## Architecture
- Backend: FastAPI + MongoDB (`users`, `challenges`, `proofs`), plus `clerk_auth.py` (require_user)
- Proof pipeline: one-use challenge (expires after 120s) → capture timestamp checked against the challenge window → dHash duplicate check (exact match across all accounts, near-match within the user's own history) → Gemini JSON verdict → accepted / rejected / suspicious
- Daily limit enforced by a unique partial index on (user_id, local_date, counted=true)
- XP: +100 per counted day, +250 when the weekly target is reached. Level = every 500 XP
- Streak = consecutive Monday-based weeks meeting the weekly target (2–5, user-selectable)
- Frontend: Expo Router. Screens: welcome, sign-in, start, onboarding, prove (fullscreen modal), (tabs) home/board/stats/me. NativeTabs on iOS 26+, otherwise JS Tabs
- Photos are NOT stored (only the hash), for privacy

## Implemented (2026-11-22)
- Full flow from welcome to onboarding to tabs; 3-state streak widget; week row; level card
- Camera proof with permission handling (allow / Open Settings); AI verification; result screen
- City and everyone leaderboard with podium; Stats (weekly goal ring, records, monthly, milestones, achievements); Me (profile, weekly target, recent proofs, sign out)
- Tests: backend/tests (23 passing)

## Streak Freeze + Razorpay (2026-11-22)
- Rs 49 one-time purchase (`backend/payments.py`, routes `/api/freeze`, `/api/freeze/order`, `/api/freeze/verify`, `/api/razorpay/webhook`)
- A freeze saves only last week, and only if it broke a live streak. Owned freeze is used automatically (inside `compute_stats`); with none owned, the user can buy until the end of the current week and it is applied at once ("repair"). Frozen weeks keep the streak alive but don't add to it. `users.freezes`, `freeze_weeks`, `payments`, `webhook_events`
- A freeze is granted once per order, only after a valid Razorpay signature AND a server-side check that the payment is captured for Rs 49. Webhook and a reconcile-on-open cover closed-app cases
- Checkout: checkout.js on web, the same checkout in a WebView on phones (works in Expo Go and builds; `react-native-razorpay` was skipped because it risks forcing the old architecture)
- Razorpay test keys set (2026-11-23); RAZORPAY_WEBHOOK_SECRET still not set
- Webhook URL to add in Razorpay dashboard: `<app url>/api/razorpay/webhook`, events `payment.captured`, `payment.failed`

## Training plans + exercise demos (2026-11-22)
- New Plans tab: 6 men's plans (Lean Machine, Mass Monster, Shred Mode, Prime After 30, Apex Athlete*, Greek God*) and 6 women's (Peach Protocol, Burn & Sculpt, Strong Not Skinny, Glow After 30, Hourglass Code*, Femme Athlete*). 4 or 5 days a week each. * = PRO
- Plans and day templates live in `backend/plans_data.py`; exercise details in `backend/data/exercises.json` (built by `backend/scripts/build_exercises.py`)
- Demos: 24 exercises have real looping videos (namnq/workout-free-videos, CC0), the other 81 loop two start/finish photos (yuhonas/free-exercise-db, public domain). Media is hot-linked from jsDelivr at pinned versions. No free 3D animation library exists; user was told and chose this
- User choices: browse and pick any plan (opens on profile gender, switch to see the other); plan does NOT change the weekly streak target; some plans paid
- PRO: one Rs 199 Razorpay payment unlocks all 4 PRO plans (`users.plans_unlocked`). Price was my assumption, set in `payments.PRODUCTS`. Locked plans return day titles and exercise counts only (enforced on the server)
- Routes: `/api/plans`, `/api/plans/{id}`, `/api/plans/{id}/start`, `/api/plans/active/stop`, `/api/plans/pro/order`, `/api/exercises/{id}`, shared `/api/payments/verify`
- Screens: `app/(tabs)/plans.tsx`, `app/plan/[id].tsx`, `app/exercise/[id].tsx`, `src/components/ExerciseDemo.tsx`, `HomePlanCard.tsx`, `src/payments/usePurchase.ts`

## WorkoutX library, demos, alternatives and swaps (2026-11-23)
- Plan: /app/plan/plan.md. User added RAZORPAY_KEY_ID/SECRET (test keys; orders verified) and WORKOUTX_API_KEY (Free plan: 500 requests total, 10 exercises per request, 360p watermarked)
- Whole WorkoutX v2 catalogue loaded once (277 requests; ~220 left): 2,764 clips = 1,904 movements (male id is canonical, female via counterpartId). `backend/scripts/fetch_workoutx.py` -> `data/workoutx.json` + `data/workoutx_media_seed.json`; pages cached in `data/workoutx_pages/` so reruns cost nothing
- `backend/library.py`: library, filters, alternatives (same target muscle, movement words, force/mechanic, plan level, gear mix), media cache (`wx_media`, reused until expiry, then 1 request per opened exercise; pauses 10 min if WorkoutX refuses)
- Plan moves -> WorkoutX via `scripts/match_plans.py` (manual overrides) -> `data/plan_matches.json`; 99 of 105 matched, the other 6 keep free-exercise-db photos with "Similar movement"
- Swaps: `plan_swaps` (user, plan, day, index -> exercise_id). Routes: GET /api/library, GET /api/exercises/{id}?model=, GET /api/exercises/{id}/alternatives?plan_id=, PUT/DELETE /api/plans/{plan}/days/{day}/exercises/{index}
- UI: Plans | Library switch, Library (FlashList, search, muscle/level/gear chips), AlternativesSheet, LevelChip, ExerciseDemo (muted looping video, plays only when focused, falls back to photos)
- IMPORTANT: WorkoutX pauses media (~1h, HTTP 429) after bulk poster/video loads. Library rows therefore show NO WorkoutX posters (photo or icon only); posters only on plan rows, alternatives and the exercise screen. Do not bulk-load media in tests
- All seed links expire ~2026-11-24 07:00 UTC; after that videos refresh one exercise at a time on open

## Backlog
- P2: Razorpay webhook secret (RAZORPAY_WEBHOOK_SECRET) + dashboard webhook
- P1: Email (email + password, custom JWT) and Google (Emergent Google Auth) sign-in as separate accounts. Managed Clerk instance has email/Google disabled (checked). Playbooks already fetched; needs a unified `require_user`
- P1: Monthly recap screen with shareable card (visits, XP earned, consistency)
- P1: Native home-screen widgets, Android + iPhone (`expo-widgets` is the SDK 58 route; needs a native build)
- P2: Friends' weekly progress, monthly recap push, gym-level leaderboard
- P2: Optional proof photo storage (object storage) for audit
