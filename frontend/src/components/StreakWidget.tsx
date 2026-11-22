import React from "react";
import { Text, View } from "react-native";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import Animated, { FadeInDown } from "react-native-reanimated";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";
import type { Dashboard } from "@/src/api";

export default function StreakWidget({ d }: { d: Dashboard }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const state = d.widget_state;
  const bg = state === "week_completed" ? colors.surfaceInverse : state === "completed" ? colors.brandPrimary : colors.surfaceSecondary;
  const fg = state === "pending" ? colors.onSurface : state === "week_completed" ? colors.onSurfaceInverse : colors.onBrandPrimary;
  const sub = state === "pending" ? colors.muted : fg;

  return (
    <Animated.View entering={FadeInDown.duration(400)} testID="streak-widget" style={[styles.wrap, { backgroundColor: bg }]}>
      <View style={styles.topRow}>
        <Text style={[styles.kicker, { color: sub }]}>{state === "week_completed" ? "WEEK COMPLETED!" : "GYM STREAK"}</Text>
        <Ionicons name={state === "week_completed" ? "trophy" : "flame"} size={28}
          color={state === "pending" ? colors.borderStrong : state === "week_completed" ? colors.brandSecondary : colors.brandSecondary} />
      </View>

      {state === "week_completed" ? (
        <>
          <Text testID="streak-widget-headline" style={[styles.big, { color: fg }]}>{d.week_count}/{d.weekly_target} workouts</Text>
          <Text style={[styles.msg, { color: sub }]}>You showed up. That's what matters.</Text>
        </>
      ) : state === "completed" ? (
        <>
          <Text testID="streak-widget-headline" style={[styles.big, { color: fg }]}>{d.streak_weeks} {d.streak_weeks === 1 ? "week" : "weeks"}</Text>
          <Text style={[styles.msg, { color: sub }]}>You've earned today's proof.</Text>
        </>
      ) : (
        <>
          <Text testID="streak-widget-headline" style={[styles.mid, { color: fg }]}>Don't break your rhythm.</Text>
          <Text style={[styles.msg, { color: sub }]}>
            {d.streak_weeks > 0 ? `${d.streak_weeks}-week streak on the line. ` : ""}
            {d.remaining} more {d.remaining === 1 ? "workout" : "workouts"} to reach your weekly goal.
          </Text>
        </>
      )}

      <View style={styles.dots}>
        {Array.from({ length: d.weekly_target }).map((_, i) => (
          <View key={i} style={[styles.dot, {
            backgroundColor: i < d.week_count ? (state === "pending" ? colors.brandPrimary : colors.brandSecondary) : state === "pending" ? colors.surfaceTertiary : colors.scrim,
          }]} />
        ))}
        <Text testID="streak-widget-count" style={[styles.count, { color: sub }]}>{d.week_count}/{d.weekly_target} this week</Text>
      </View>
    </Animated.View>
  );
}

const useStyles = makeStyles((c) => ({
  wrap: { borderRadius: radius.lg, padding: spacing.xl, gap: spacing.sm, borderWidth: 1, borderColor: c.border },
  topRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  kicker: { fontSize: 13, fontWeight: "900", letterSpacing: 1.5 },
  big: { fontSize: 40, fontWeight: "900" },
  mid: { fontSize: 26, fontWeight: "900" },
  msg: { fontSize: 15, fontWeight: "600" },
  dots: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.sm },
  dot: { width: 28, height: 8, borderRadius: 4 },
  count: { fontSize: 13, fontWeight: "700", marginLeft: spacing.xs },
}));
