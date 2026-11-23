import { useCallback } from "react";
import { useAuth } from "@clerk/expo";

export const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
export const tzOffsetMin = () => -new Date().getTimezoneOffset();

export function useApi() {
  const { getToken } = useAuth();
  const authHeader = useCallback(async () => ({ Authorization: `Bearer ${await getToken()}` }), [getToken]);
  const call = useCallback(
    async <T = any>(path: string, init: { method?: string; body?: any } = {}): Promise<T> => {
      const headers: Record<string, string> = await authHeader();
      if (init.body !== undefined) headers["Content-Type"] = "application/json";
      const res = await fetch(`${BACKEND_URL}/api${path}`, {
        method: init.method ?? "GET",
        headers,
        body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
      return data as T;
    },
    [authHeader],
  );
  return { call, authHeader };
}

export type WeekDay = { date: string; label: string; done: boolean; is_today: boolean; is_future: boolean };
export type Freeze = {
  owned: number; price_inr: number; payments_enabled: boolean; can_buy: boolean; last_week_frozen: boolean;
  frozen_weeks: string[]; repair: { week_start: string; deadline: string; streak_at_risk: number } | null;
};
export type ProStatus = { unlocked: boolean; price_inr: number; payments_enabled: boolean; plan_count: number };
export type PlanCard = {
  id: string; gender: "male" | "female"; name: string; tagline: string; goal: string; level: string; duration_weeks: number;
  premium: boolean; icon: string; days_per_week: number; locked: boolean; active: boolean;
};
export type Level = "beginner" | "intermediate" | "pro";
export type PlanExercise = {
  index: number; id: string; original_id: string; swapped: boolean; similar: boolean;
  name: string; sets: number; reps: string; rest_sec: number; muscle: string; equipment: string; level: Level; image: string | null;
};
export type LibraryItem = {
  id: string; name: string; level: Level; group: string; target: string; equipment: string; thumb: string | null;
};
export type Library = { items: LibraryItem[]; groups: string[]; equipment: string[] };
export type PlanDetail = PlanCard & {
  description: string; pro: ProStatus;
  days: { day: number; title: string; focus: string; exercise_count: number; exercises: PlanExercise[] }[];
};
export type Exercise = {
  id: string; canonical_id: string; name: string; model: "male" | "female" | null; models: { male?: string; female?: string };
  level: Level; group: string; target: string; equipment: string; primary_muscles: string[]; secondary_muscles: string[];
  instructions: string[]; tips: string[]; sets: string | null; reps: string | null;
  video: string | null; poster: string | null; images: string[]; similar: boolean; source: "workoutx" | "free-exercise-db";
};
export type Dashboard = {
  freeze: Freeze;
  active_plan: { id: string; name: string; days_per_week: number } | null;
  name: string; city: string; streak_weeks: number; best_streak: number; weekly_target: number; week_count: number;
  remaining: number; today_done: boolean; widget_state: "completed" | "pending" | "week_completed";
  week_days: WeekDay[]; total_visits: number; month_visits: number; month: string; completed_weeks: number;
  xp: number; level: number; level_progress: number;
  milestones: { weeks: number; unlocked: boolean }[];
  achievements: { id: string; title: string; desc: string; unlocked: boolean }[];
};
