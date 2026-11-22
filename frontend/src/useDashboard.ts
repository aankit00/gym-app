import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { Dashboard, tzOffsetMin, useApi } from "@/src/api";

export function useDashboard() {
  const { call } = useApi();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      setError("");
      setData(await call<Dashboard>(`/dashboard?tz_offset_min=${tzOffsetMin()}`));
    } catch (e: any) {
      setError(e.message);
    }
  }, [call]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  return { data, error, refreshing, refresh, reload: load };
}
