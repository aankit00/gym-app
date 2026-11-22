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
export type Dashboard = {
  name: string; city: string; streak_weeks: number; best_streak: number; weekly_target: number; week_count: number;
  remaining: number; today_done: boolean; widget_state: "completed" | "pending" | "week_completed";
  week_days: WeekDay[]; total_visits: number; month_visits: number; month: string; completed_weeks: number;
  xp: number; level: number; level_progress: number;
  milestones: { weeks: number; unlocked: boolean }[];
  achievements: { id: string; title: string; desc: string; unlocked: boolean }[];
};
