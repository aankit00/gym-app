import React from "react";
import { ActivityIndicator, RefreshControl, ScrollView, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { BlurView } from "expo-blur";
import Animated, { FadeInDown } from "react-native-reanimated";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useDashboard } from "@/src/useDashboard";
import StreakWidget from "@/src/components/StreakWidget";
import WeekRow from "@/src/components/WeekRow";
import { BigTitle, Card, PrimaryButton, SectionTitle } from "@/src/components/ui";
import { usesNativeTabs } from "@/src/navigation";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

export default function Home() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data, error, refreshing, refresh, reload } = useDashboard();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <BigTitle text="Gym Streak" testID="home-title" right={
          data ? <View style={styles.xpChip} testID="home-xp-chip"><Ionicons name="flash" size={16} color={colors.onBrandSecondary} /><Text style={styles.xpChipText}>{data.xp} XP</Text></View> : null
        } />
      </View>
      {!data ? (
        <View style={styles.center}>
          {error ? (
            <>
              <Text style={styles.err} testID="home-error">{error}</Text>
              <PrimaryButton testID="home-retry-button" label="Retry" onPress={reload} />
            </>
          ) : <ActivityIndicator color={colors.brandPrimary} size="large" />}
        </View>
      ) : (
        <ScrollView contentContainerStyle={[styles.scroll, { paddingBottom: bottomChrome + 110 }]}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.brandPrimary} />}>
          <Text style={styles.hello} testID="home-greeting">Hey {data.name.split(" ")[0]}, keep showing up.</Text>
          <StreakWidget d={data} />

          <SectionTitle text="This Week" />
          <WeekRow days={data.week_days} />

          <SectionTitle text="Level" />
          <Animated.View entering={FadeInDown.delay(150)}>
            <Card testID="level-card">
              <View style={styles.levelRow}>
                <Text style={styles.levelBig}>LV {data.level}</Text>
                <Text style={styles.levelMeta}>{Math.round(data.level_progress * 500)}/500 XP to next</Text>
              </View>
              <View style={styles.bar}><View style={[styles.barFill, { width: `${Math.max(4, data.level_progress * 100)}%` }]} /></View>
              <View style={styles.statRow}>
                <Stat label="Streak" value={`${data.streak_weeks}w`} testID="home-stat-streak" />
                <Stat label="Best" value={`${data.best_streak}w`} testID="home-stat-best" />
                <Stat label="Visits" value={String(data.total_visits)} testID="home-stat-visits" />
              </View>
            </Card>
          </Animated.View>

          <SectionTitle text="How Proof Works" />
          <Card>
            {[
              ["camera", "Open the live camera in the gym"],
              ["hand-left", "Show your hand gripping equipment"],
              ["sparkles", "AI checks it — accepted proof = +100 XP"],
              ["calendar", `Hit ${data.weekly_target} days a week to grow your streak`],
            ].map(([i, t]) => (
              <View key={t} style={styles.howRow}>
                <View style={styles.howIcon}><Ionicons name={i as any} size={18} color={colors.onSurface} /></View>
                <Text style={styles.howText}>{t}</Text>
              </View>
            ))}
          </Card>
        </ScrollView>
      )}
      {data && (
        <BlurView intensity={40} tint="light" style={[styles.cta, { bottom: bottomChrome + spacing.lg }]}>
          <PrimaryButton testID="prove-workout-button" variant={data.today_done ? "light" : "dark"}
            label={data.today_done ? "Today's proof earned ✓  Prove again" : "Prove Your Workout"}
            icon={<Ionicons name="camera" size={20} color={data.today_done ? colors.onSurface : colors.onSurfaceInverse} />}
            onPress={() => router.push("/prove")} />
        </BlurView>
      )}
    </View>
  );
}

function Stat({ label, value, testID }: { label: string; value: string; testID: string }) {
  const styles = useStyles();
  return (
    <View style={styles.stat}>
      <Text style={styles.statVal} testID={testID}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  header: { paddingHorizontal: spacing.xl, paddingBottom: spacing.sm, backgroundColor: c.surface },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.lg, padding: spacing.xl },
  err: { color: c.error, fontWeight: "600", textAlign: "center" },
  scroll: { paddingHorizontal: spacing.xl, paddingTop: spacing.sm },
  hello: { fontSize: 16, fontWeight: "600", color: c.muted, marginBottom: spacing.lg },
  xpChip: { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: c.brandSecondary, paddingHorizontal: spacing.md, height: 32, borderRadius: radius.pill },
  xpChipText: { fontWeight: "900", color: c.onBrandSecondary },
  levelRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end" },
  levelBig: { fontSize: 28, fontWeight: "900", color: c.onSurface },
  levelMeta: { fontSize: 13, fontWeight: "700", color: c.muted },
  bar: { height: 10, borderRadius: 5, backgroundColor: c.surfaceTertiary, marginTop: spacing.md, overflow: "hidden" },
  barFill: { height: 10, borderRadius: 5, backgroundColor: c.brandPrimary },
  statRow: { flexDirection: "row", marginTop: spacing.lg },
  stat: { flex: 1, alignItems: "center" },
  statVal: { fontSize: 26, fontWeight: "900", color: c.onSurface },
  statLabel: { fontSize: 13, fontWeight: "700", color: c.muted, marginTop: 2 },
  howRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingVertical: spacing.sm },
  howIcon: { width: 36, height: 36, borderRadius: 18, backgroundColor: c.brandTertiary, alignItems: "center", justifyContent: "center" },
  howText: { flex: 1, fontSize: 15, fontWeight: "600", color: c.onSurface },
  cta: { position: "absolute", left: spacing.lg, right: spacing.lg, borderRadius: radius.pill, overflow: "hidden", padding: 6 },
}));
