import React, { useCallback, useState } from "react";
import { ActivityIndicator, FlatList, RefreshControl, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Animated, { FadeInDown } from "react-native-reanimated";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useApi } from "@/src/api";
import { BigTitle, PrimaryButton, Segmented } from "@/src/components/ui";
import { usesNativeTabs } from "@/src/navigation";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

type Entry = { rank: number; name: string; xp: number; city: string; is_me: boolean };
type Board = { scope: string; city: string; entries: Entry[]; my_rank: number; my_xp: number; total: number };

export default function BoardScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { call } = useApi();
  const [scope, setScope] = useState<"city" | "all">("city");
  const [data, setData] = useState<Board | null>(null);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;

  const load = useCallback(async (s = scope) => {
    try {
      setError("");
      setData(await call<Board>(`/leaderboard?scope=${s}`));
    } catch (e: any) {
      setError(e.message);
    }
  }, [call, scope]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const top3 = data?.entries.slice(0, 3) ?? [];
  const rest = data?.entries.slice(3) ?? [];
  const medal = [colors.brandSecondary, colors.borderStrong, colors.brandPrimary];

  const Podium = () => (
    <View style={styles.podium}>
      {[1, 0, 2].map((i) => {
        const e = top3[i];
        if (!e) return <View key={i} style={{ flex: 1 }} />;
        return (
          <Animated.View entering={FadeInDown.delay(i * 100)} key={i} style={[styles.podCol, { marginTop: i === 0 ? 0 : spacing.xl }]} testID={`podium-${i + 1}`}>
            {i === 0 && <Ionicons name="trophy" size={22} color={colors.brandPrimary} />}
            <View style={[styles.avatar, { width: i === 0 ? 72 : 60, height: i === 0 ? 72 : 60, borderColor: medal[i] }, e.is_me && { backgroundColor: colors.brandTertiary }]}>
              <Text style={styles.avatarText}>{e.name.slice(0, 1).toUpperCase()}</Text>
            </View>
            <Text numberOfLines={1} style={styles.podName}>{e.is_me ? "You" : e.name}</Text>
            <Text style={styles.podXp}>{e.xp} XP</Text>
            <View style={[styles.rankBadge, { backgroundColor: medal[i] }]}><Text style={styles.rankBadgeText}>{i + 1}</Text></View>
          </Animated.View>
        );
      })}
    </View>
  );

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <BigTitle text="Leaderboard" testID="board-title" />
        <Segmented testIDPrefix="board-scope" value={scope} onChange={(k) => { setScope(k as any); setData(null); load(k as any); }}
          options={[{ key: "city", label: data?.city || "My City" }, { key: "all", label: "Everyone" }]} />
        {data && (
          <View style={styles.meBar} testID="board-my-rank">
            <Text style={styles.meText}>Your rank</Text>
            <Text style={styles.meRank}>#{data.my_rank} <Text style={styles.meOf}>of {data.total}</Text></Text>
            <Text style={styles.meText}>{data.my_xp} XP</Text>
          </View>
        )}
      </View>
      {!data ? (
        <View style={styles.center}>
          {error ? <><Text style={styles.err}>{error}</Text><PrimaryButton testID="board-retry-button" label="Retry" onPress={() => load()} /></>
            : <ActivityIndicator color={colors.brandPrimary} size="large" />}
        </View>
      ) : (
        <FlatList
          data={rest}
          keyExtractor={(e) => `${e.rank}-${e.name}`}
          contentContainerStyle={[styles.list, { paddingBottom: bottomChrome + spacing.xl }]}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}
          ListHeaderComponent={<Podium />}
          ListEmptyComponent={data.entries.length <= 1 ? (
            <Text style={styles.empty} testID="board-empty">You&apos;re the first in {data.city}. Invite your gym buddies to compete!</Text>
          ) : null}
          renderItem={({ item }) => (
            <View style={[styles.row, item.is_me && styles.rowMe]} testID={`board-row-${item.rank}`}>
              <Text style={styles.rank}>{item.rank}</Text>
              <View style={styles.smallAvatar}><Text style={styles.avatarText}>{item.name.slice(0, 1).toUpperCase()}</Text></View>
              <Text style={styles.rowName} numberOfLines={1}>{item.is_me ? `${item.name} (You)` : item.name}</Text>
              <Text style={styles.rowXp}>{item.xp} XP</Text>
            </View>
          )}
        />
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  header: { paddingHorizontal: spacing.xl, paddingBottom: spacing.md, gap: spacing.md, backgroundColor: c.surface },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.lg, padding: spacing.xl },
  err: { color: c.error, fontWeight: "600", textAlign: "center" },
  meBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", backgroundColor: c.surfaceInverse, borderRadius: radius.pill, paddingHorizontal: spacing.lg, height: 48 },
  meText: { color: c.onSurfaceInverse, fontWeight: "700" },
  meRank: { color: c.brandSecondary, fontWeight: "900", fontSize: 18 },
  meOf: { color: c.muted, fontSize: 13, fontWeight: "700" },
  list: { paddingHorizontal: spacing.xl, gap: spacing.sm },
  podium: { flexDirection: "row", alignItems: "flex-start", marginVertical: spacing.lg },
  podCol: { flex: 1, alignItems: "center", gap: 4 },
  avatar: { borderRadius: 999, borderWidth: 4, backgroundColor: c.surfaceSecondary, alignItems: "center", justifyContent: "center" },
  avatarText: { fontSize: 20, fontWeight: "900", color: c.onSurface },
  podName: { fontWeight: "800", color: c.onSurface, maxWidth: 100 },
  podXp: { fontWeight: "700", color: c.muted, fontSize: 13 },
  rankBadge: { width: 28, height: 28, borderRadius: 14, alignItems: "center", justifyContent: "center" },
  rankBadgeText: { fontWeight: "900", color: c.onSurface },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.md, minHeight: 60 },
  rowMe: { borderWidth: 2, borderColor: c.brandPrimary },
  rank: { width: 28, fontWeight: "900", color: c.muted, fontSize: 16, textAlign: "center" },
  smallAvatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: c.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  rowName: { flex: 1, fontWeight: "800", color: c.onSurface, fontSize: 15 },
  rowXp: { fontWeight: "900", color: c.onSurface },
  empty: { textAlign: "center", color: c.muted, fontWeight: "600", marginTop: spacing.lg },
}));
