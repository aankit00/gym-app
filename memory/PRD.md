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

## Backlog
- P1: Native home-screen widgets (Android Glance / iOS WidgetKit; needs a dev build)
- P1: Streak Freeze (earned at milestones / subscription perk via Razorpay)
- P1: Email / Google sign-in alongside phone
- P2: Friends' weekly progress, monthly recap push, gym-level leaderboard
- P2: Optional proof photo storage (object storage) for audit
