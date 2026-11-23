import React, { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { PlanDetail, PlanExercise, useApi } from "@/src/api";
import RazorpayCheckout from "@/src/payments/RazorpayCheckout";
import { usePurchase } from "@/src/payments/usePurchase";
import AlternativesSheet, { PlanSlot } from "@/src/components/AlternativesSheet";
import { ExerciseThumb, LevelChip } from "@/src/components/LevelChip";
import { PressScale, PrimaryButton } from "@/src/components/ui";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

export default function PlanScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { call } = useApi();
  const [plan, setPlan] = useState<PlanDetail | null>(null);
  const [dayIndex, setDayIndex] = useState(0);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [saving, setSaving] = useState(false);
  const [alt, setAlt] = useState<{ exercise: PlanExercise; slot: PlanSlot } | null>(null);
  const [resetting, setResetting] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setLoadError("");
      setPlan(await call<PlanDetail>(`/plans/${id}`));
    } catch (e: any) {
      setLoadError(e.message);
    }
  }, [call, id]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const { buy, busy, error: payError, notice, checkout } = usePurchase("/plans/pro/order", load);

  const setActive = async (start: boolean) => {
    setActionError("");
    setSaving(true);
    try {
      await call(start ? `/plans/${id}/start` : "/plans/active/stop", { method: "POST" });
      await load();
    } catch (e: any) {
      setActionError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const day = plan?.days[dayIndex];
  const slotFor = (e: PlanExercise): PlanSlot => ({ planId: id, day: day!.day, index: e.index, sets: e.sets, reps: e.reps, rest: e.rest_sec });

  const openExercise = (e: PlanExercise) => router.push({
    pathname: "/exercise/[id]",
    params: { id: e.id, sets: String(e.sets), reps: e.reps, rest: String(e.rest_sec), planId: id, day: String(day!.day), index: String(e.index), mode: e.swapped ? "swapped" : "current" },
  });

  const reset = async (e: PlanExercise) => {
    setActionError("");
    setResetting(e.index);
    try {
      await call(`/plans/${id}/days/${day!.day}/exercises/${e.index}`, { method: "DELETE" });
      await load();
    } catch (err: any) {
      setActionError(err.message);
    } finally {
      setResetting(null);
    }
  };
  const error = actionError || payError;

  return (
    <View style={[styles.root, { paddingTop: insets.top + spacing.sm }]} testID="plan-screen">
      <Pressable testID="plan-back-button" onPress={() => (router.canGoBack() ? router.back() : router.replace("/plans"))} style={styles.back} hitSlop={8}>
        <Ionicons name="chevron-back" size={26} color={colors.onSurface} />
      </Pressable>
      {!plan || !day ? (
        <View style={styles.center}>
          {loadError ? <><Text style={styles.err} testID="plan-error">{loadError}</Text><PrimaryButton testID="plan-retry-button" label="Retry" onPress={load} /></>
            : <ActivityIndicator color={colors.brandPrimary} size="large" />}
        </View>
      ) : (
        <>
          <ScrollView contentContainerStyle={styles.scroll}>
            <Text style={styles.kicker}>{plan.goal.toUpperCase()}{plan.premium ? " · PRO" : ""}</Text>
            <Text style={styles.title} testID="plan-title">{plan.name}</Text>
            <Text style={styles.body}>{plan.description}</Text>
            <View style={styles.chips}>
              <Text style={styles.chip}>{plan.days_per_week} days / week</Text>
              <Text style={styles.chip}>{plan.duration_weeks} weeks</Text>
              <Text style={styles.chip}>{plan.level}</Text>
            </View>

            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.dayStrip} contentContainerStyle={styles.dayStripInner}>
              {plan.days.map((d, i) => (
                <Pressable key={d.day} testID={`plan-day-${d.day}`} onPress={() => setDayIndex(i)}
                  style={[styles.dayPill, i === dayIndex && styles.dayPillOn]}>
                  <Text style={[styles.dayPillText, i === dayIndex && styles.dayPillTextOn]}>Day {d.day}</Text>
                </Pressable>
              ))}
            </ScrollView>

            <Text style={styles.dayTitle} testID="plan-day-title">{day.title}</Text>
            <Text style={styles.dayFocus}>{day.focus}</Text>

            {plan.locked ? (
              <View style={styles.locked} testID="plan-locked">
                <Ionicons name="lock-closed" size={28} color={colors.onSurface} />
                <Text style={styles.lockedTitle}>{day.exercise_count} exercises in this workout</Text>
                <Text style={styles.lockedText}>
                  Unlock PRO once for ₹{plan.pro.price_inr} to open all {plan.pro.plan_count} PRO plans, yours to keep.
                </Text>
              </View>
            ) : day.exercises.map((e, i) => (
              <View key={`${day.day}-${e.index}`} style={styles.row}>
                <PressScale testID={`plan-exercise-${i}`} onPress={() => openExercise(e)} style={styles.rowMain}>
                  <ExerciseThumb uri={e.image} />
                  <View style={styles.rowText}>
                    <Text style={styles.rowName} numberOfLines={2}>{e.name}</Text>
                    <Text style={styles.rowMeta}>{e.sets} × {e.reps}{e.rest_sec ? ` · rest ${e.rest_sec}s` : ""}</Text>
                    <View style={styles.tags}>
                      <LevelChip level={e.level} />
                      {e.swapped && <Text style={styles.swapped} testID={`plan-exercise-swapped-${i}`}>SWAPPED</Text>}
                      {e.similar && <Text style={styles.similar}>Similar movement</Text>}
                    </View>
                  </View>
                  <Ionicons name="chevron-forward" size={20} color={colors.muted} />
                </PressScale>
                <View style={styles.rowActions}>
                  <Pressable testID={`plan-exercise-alternatives-${i}`} onPress={() => setAlt({ exercise: e, slot: slotFor(e) })} style={styles.action} hitSlop={4}>
                    <Ionicons name="swap-horizontal" size={16} color={colors.onSurface} />
                    <Text style={styles.actionText}>Alternatives</Text>
                  </Pressable>
                  {e.swapped && (
                    <Pressable testID={`plan-exercise-reset-${i}`} disabled={resetting !== null} onPress={() => reset(e)} style={styles.action} hitSlop={4}>
                      {resetting === e.index ? <ActivityIndicator size="small" color={colors.onSurface} />
                        : <Ionicons name="refresh" size={16} color={colors.onSurface} />}
                      <Text style={styles.actionText}>Reset to original</Text>
                    </Pressable>
                  )}
                </View>
              </View>
            ))}
            {!!notice && <Text style={styles.notice} testID="plan-notice">{notice}</Text>}
            {!!error && <Text style={styles.err} testID="plan-action-error">{error}</Text>}
          </ScrollView>

          <View style={[styles.footer, { paddingBottom: insets.bottom + spacing.lg }]}>
            {plan.locked ? (
              <>
                <PrimaryButton testID="plan-unlock-button" variant="brand" loading={busy} disabled={!plan.pro.payments_enabled}
                  label={`Unlock PRO plans · ₹${plan.pro.price_inr}`} onPress={buy} />
                <Text style={styles.small} testID="plan-pay-note">
                  {plan.pro.payments_enabled ? "One-time payment via Razorpay. UPI, cards and netbanking." : "Payments aren't switched on yet. Check back soon."}
                </Text>
              </>
            ) : plan.active ? (
              <PrimaryButton testID="plan-stop-button" variant="light" loading={saving} label="Stop following this plan" onPress={() => setActive(false)} />
            ) : (
              <PrimaryButton testID="plan-start-button" variant="brand" loading={saving} label="Start this plan" onPress={() => setActive(true)} />
            )}
          </View>
        </>
      )}
      <RazorpayCheckout {...checkout} />
      <AlternativesSheet exerciseId={alt?.exercise.id ?? null} exerciseName={alt?.exercise.name} slot={alt?.slot}
        onClose={() => setAlt(null)} onSwapped={load} />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  back: { width: 44, height: 44, justifyContent: "center", marginLeft: spacing.md },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.lg, padding: spacing.xl },
  scroll: { paddingHorizontal: spacing.xl, paddingBottom: spacing.xl, gap: spacing.sm },
  kicker: { fontSize: 12, fontWeight: "900", letterSpacing: 1.5, color: c.onBrandTertiary },
  title: { fontSize: 32, fontWeight: "900", color: c.onSurface },
  body: { fontSize: 16, lineHeight: 22, fontWeight: "500", color: c.onSurfaceTertiary },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.xs },
  chip: { fontSize: 12, fontWeight: "800", color: c.onSurfaceTertiary, backgroundColor: c.surfaceSecondary, paddingHorizontal: spacing.md, paddingVertical: 6, borderRadius: radius.pill, overflow: "hidden" },
  dayStrip: { marginHorizontal: -spacing.xl, marginTop: spacing.lg, flexGrow: 0 },
  dayStripInner: { paddingHorizontal: spacing.xl, gap: spacing.sm },
  dayPill: { height: 44, paddingHorizontal: spacing.lg, borderRadius: radius.pill, backgroundColor: c.surfaceSecondary, alignItems: "center", justifyContent: "center" },
  dayPillOn: { backgroundColor: c.surfaceInverse },
  dayPillText: { fontSize: 15, fontWeight: "800", color: c.onSurface },
  dayPillTextOn: { color: c.onSurfaceInverse },
  dayTitle: { fontSize: 22, fontWeight: "900", color: c.onSurface, marginTop: spacing.md },
  dayFocus: { fontSize: 14, fontWeight: "600", color: c.muted, marginBottom: spacing.sm },
  row: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.md, gap: spacing.sm },
  rowMain: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  tags: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: spacing.sm, marginTop: 4 },
  swapped: { fontSize: 11, fontWeight: "900", letterSpacing: 0.5, color: c.onBrandSecondary, backgroundColor: c.brandSecondary, paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.sm, overflow: "hidden" },
  similar: { fontSize: 11, fontWeight: "800", color: c.muted },
  rowActions: { flexDirection: "row", gap: spacing.sm, flexWrap: "wrap" },
  action: { flexDirection: "row", alignItems: "center", gap: 6, height: 40, paddingHorizontal: spacing.md, borderRadius: radius.pill, backgroundColor: c.surface },
  actionText: { fontSize: 13, fontWeight: "800", color: c.onSurface },
  rowText: { flex: 1 },
  rowName: { fontSize: 16, fontWeight: "800", color: c.onSurface },
  rowMeta: { fontSize: 14, fontWeight: "700", color: c.onBrandTertiary, marginTop: 2 },
  locked: { alignItems: "center", gap: spacing.sm, backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.xl },
  lockedTitle: { fontSize: 17, fontWeight: "800", color: c.onSurface },
  lockedText: { fontSize: 14, fontWeight: "600", color: c.muted, textAlign: "center", lineHeight: 20 },
  footer: { paddingHorizontal: spacing.xl, paddingTop: spacing.md, gap: spacing.sm },
  small: { fontSize: 13, fontWeight: "600", color: c.muted, textAlign: "center" },
  notice: { color: c.onSurfaceTertiary, fontWeight: "600", textAlign: "center", marginTop: spacing.sm },
  err: { color: c.error, fontWeight: "600", textAlign: "center", marginTop: spacing.sm },
}));
