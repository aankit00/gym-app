import React, { useState } from "react";
import { ActivityIndicator, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Svg, { Circle } from "react-native-svg";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useRouter } from "expo-router";
import { useDashboard } from "@/src/useDashboard";
import WeekRow from "@/src/components/WeekRow";
import { BigTitle, Card, PrimaryButton, SectionTitle, Segmented } from "@/src/components/ui";
import { usesNativeTabs } from "@/src/navigation";
import { makeStyles, spacing, useTheme } from "@/src/theme";

function Ring({ progress, size = 120 }: { progress: number; size?: number }) {
  const { colors } = useTheme();
  const sw = 16;
  const r = (size - sw) / 2;
  const circ = 2 * Math.PI * r;
  return (
    <Svg width={size} height={size}>
      <Circle cx={size / 2} cy={size / 2} r={r} stroke={colors.brandTertiary} strokeWidth={sw} fill="none" />
      <Circle cx={size / 2} cy={size / 2} r={r} stroke={colors.brandPrimary} strokeWidth={sw} fill="none" strokeLinecap="round"
        strokeDasharray={`${circ} ${circ}`} strokeDashoffset={circ * (1 - Math.min(1, progress))} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
    </Svg>
  );
}

export default function Stats() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { data, error, refreshing, refresh, reload } = useDashboard();
  const [tab, setTab] = useState("stats");
  const router = useRouter();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <BigTitle text="Statistics" testID="stats-title" right={
          <PrimaryButton testID="open-recap-button" label="Recap" variant="brand" onPress={() => router.push("/recap")}
            icon={<Ionicons name="sparkles" size={16} color={colors.onBrandPrimary} />} />
        } />
        <Segmented testIDPrefix="stats-tab" value={tab} onChange={setTab}
          options={[{ key: "stats", label: "Statistics" }, { key: "awards", label: "Achievements" }]} />
      </View>
      {!data ? (
        <View style={styles.center}>
          {error ? <><Text style={styles.err}>{error}</Text><PrimaryButton testID="stats-retry-button" label="Retry" onPress={reload} /></>
            : <ActivityIndicator color={colors.brandPrimary} size="large" />}
        </View>
      ) : (
        <ScrollView contentContainerStyle={[styles.scroll, { paddingBottom: bottomChrome + spacing.xl }]}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}>
          {tab === "stats" ? (
            <>
              <WeekRow days={data.week_days} />
              <SectionTitle text="Weekly Goal" />
              <Card style={styles.goalCard} testID="weekly-goal-card">
                <View style={{ gap: spacing.md, flex: 1 }}>
                  <View>
                    <Text style={[styles.goalLabel, { color: colors.brandPrimary }]}>Verified days</Text>
                    <Text style={styles.goalVal} testID="weekly-goal-value">{data.week_count}<Text style={styles.goalOf}>/{data.weekly_target} days</Text></Text>
                  </View>
                  <View>
                    <Text style={[styles.goalLabel, { color: colors.onBrandTertiary }]}>Streak</Text>
                    <Text style={styles.goalVal}>{data.streak_weeks}<Text style={styles.goalOf}> weeks</Text></Text>
                  </View>
                </View>
                <Ring progress={data.week_count / data.weekly_target} />
              </Card>

              <SectionTitle text="Records" />
              <Card style={styles.records} testID="records-card">
                <Rec v={data.total_visits} l="Visits" id="records-visits" />
                <Rec v={data.completed_weeks} l="Weeks hit" id="records-weeks" />
                <Rec v={data.best_streak} l="Best streak" id="records-best" />
              </Card>

              <SectionTitle text="Monthly" />
              <Card testID="monthly-card">
                <Text style={styles.month}>{new Date(`${data.month}-01T12:00:00`).toLocaleDateString("en-US", { month: "long", year: "numeric" })}</Text>
                <View style={styles.records}>
                  <Rec v={data.month_visits} l="Verified visits" id="monthly-visits" />
                  <Rec v={data.xp} l="Total XP" id="monthly-xp" />
                </View>
              </Card>
            </>
          ) : (
            <>
              <SectionTitle text="Milestones" />
              <View style={styles.grid}>
                {data.milestones.map((m) => (
                  <View key={m.weeks} style={[styles.mile, m.unlocked && styles.mileOn]} testID={`milestone-${m.weeks}`}>
                    <Ionicons name={m.unlocked ? "flame" : "lock-closed"} size={28} color={m.unlocked ? colors.brandPrimary : colors.borderStrong} />
                    <Text style={styles.mileVal}>{m.weeks}</Text>
                    <Text style={styles.mileLabel}>weeks</Text>
                  </View>
                ))}
              </View>
              <SectionTitle text="Achievements" />
              <View style={{ gap: spacing.sm }}>
                {data.achievements.map((a) => (
                  <Card key={a.id} style={[styles.ach, !a.unlocked && { opacity: 0.55 }]} testID={`achievement-${a.id}`}>
                    <View style={[styles.achIcon, a.unlocked && { backgroundColor: colors.brandSecondary }]}>
                      <Ionicons name={a.unlocked ? "ribbon" : "lock-closed"} size={22} color={colors.onSurface} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.achTitle}>{a.title}</Text>
                      <Text style={styles.achDesc}>{a.desc}</Text>
                    </View>
                    {a.unlocked && <Ionicons name="checkmark-circle" size={24} color={colors.success} />}
                  </Card>
                ))}
              </View>
            </>
          )}
        </ScrollView>
      )}
    </View>
  );
}

function Rec({ v, l, id }: { v: number; l: string; id: string }) {
  const styles = useStyles();
  return (
    <View style={styles.rec}>
      <Text style={styles.recVal} testID={id}>{v}</Text>
      <Text style={styles.recLabel}>{l}</Text>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  header: { paddingHorizontal: spacing.xl, paddingBottom: spacing.md, gap: spacing.md, backgroundColor: c.surface },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.lg, padding: spacing.xl },
  err: { color: c.error, fontWeight: "600", textAlign: "center" },
  scroll: { paddingHorizontal: spacing.xl, paddingTop: spacing.sm },
  goalCard: { flexDirection: "row", alignItems: "center", padding: spacing.xl },
  goalLabel: { fontSize: 16, fontWeight: "800" },
  goalVal: { fontSize: 30, fontWeight: "900", color: c.onSurface },
  goalOf: { fontSize: 18, fontWeight: "700", color: c.onSurfaceTertiary },
  records: { flexDirection: "row", paddingVertical: spacing.xl },
  rec: { flex: 1, alignItems: "center" },
  recVal: { fontSize: 34, fontWeight: "900", color: c.onSurface },
  recLabel: { fontSize: 14, fontWeight: "600", color: c.muted, marginTop: 4 },
  month: { textAlign: "center", fontSize: 20, fontWeight: "800", color: c.onSurfaceTertiary },
  grid: { flexDirection: "row", gap: spacing.sm },
  mile: { flex: 1, alignItems: "center", backgroundColor: c.surfaceSecondary, borderRadius: 20, paddingVertical: spacing.lg, borderWidth: 2, borderColor: c.surfaceSecondary },
  mileOn: { borderColor: c.brandSecondary, backgroundColor: c.brandTertiary },
  mileVal: { fontSize: 24, fontWeight: "900", color: c.onSurface, marginTop: 4 },
  mileLabel: { fontSize: 12, fontWeight: "700", color: c.muted },
  ach: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  achIcon: { width: 44, height: 44, borderRadius: 22, backgroundColor: c.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  achTitle: { fontSize: 16, fontWeight: "800", color: c.onSurface },
  achDesc: { fontSize: 13, fontWeight: "600", color: c.muted, marginTop: 2 },
}));
