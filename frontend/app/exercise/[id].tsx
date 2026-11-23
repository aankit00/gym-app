import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { Exercise, useApi } from "@/src/api";
import AlternativesSheet, { PlanSlot } from "@/src/components/AlternativesSheet";
import ExerciseDemo from "@/src/components/ExerciseDemo";
import { LevelChip } from "@/src/components/LevelChip";
import { Card, PrimaryButton, Segmented } from "@/src/components/ui";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

type Params = { id: string; sets?: string; reps?: string; rest?: string; planId?: string; day?: string; index?: string; mode?: "current" | "swapped" | "candidate" };

export default function ExerciseScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { id, sets, reps, rest, planId, day, index, mode } = useLocalSearchParams<Params>();
  const { call } = useApi();
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [model, setModel] = useState<string>("");
  const [error, setError] = useState("");
  const [altOpen, setAltOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");

  const slot: PlanSlot | undefined = planId && day && index
    ? { planId, day: Number(day), index: Number(index), sets: Number(sets) || undefined, reps, rest: Number(rest) || undefined } : undefined;

  const load = useCallback(async () => {
    try {
      setError("");
      const q = model ? `?model=${model}` : "";
      setExercise(await call<Exercise>(`/exercises/${encodeURIComponent(id)}${q}`));
    } catch (e: any) {
      setError(e.message);
    }
  }, [call, id, model]);

  useEffect(() => { load(); }, [load]);

  const planAction = async (method: "PUT" | "DELETE") => {
    if (!slot) return;
    setBusy(true);
    setActionError("");
    try {
      await call(`/plans/${slot.planId}/days/${slot.day}/exercises/${slot.index}`,
        method === "PUT" ? { method, body: { exercise_id: exercise!.canonical_id } } : { method });
      backToPlan();
    } catch (e: any) {
      setActionError(e.message);
    } finally {
      setBusy(false);
    }
  };

  // the plan screen reloads on focus; anything stacked above it (old exercise screens) is now out of date
  const backToPlan = () => router.dismissTo({ pathname: "/plan/[id]", params: { id: planId! } });

  const bothModels = !!(exercise?.models.male && exercise?.models.female);

  return (
    <View style={[styles.root, { paddingTop: insets.top + spacing.sm }]} testID="exercise-screen">
      <Pressable testID="exercise-back-button" onPress={() => router.back()} style={styles.back} hitSlop={8}>
        <Ionicons name="chevron-back" size={26} color={colors.onSurface} />
      </Pressable>
      {!exercise ? (
        <View style={styles.center}>
          {error ? <><Text style={styles.err} testID="exercise-error">{error}</Text><PrimaryButton testID="exercise-retry-button" label="Retry" onPress={load} /></>
            : <ActivityIndicator color={colors.brandPrimary} size="large" />}
        </View>
      ) : (
        <ScrollView contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + spacing["2xl"] }]}>
          <ExerciseDemo video={exercise.video} poster={exercise.poster} images={exercise.images} />
          {bothModels && (
            <Segmented testIDPrefix="exercise-model" value={exercise.model ?? "male"} onChange={setModel}
              options={[{ key: "male", label: "Male" }, { key: "female", label: "Female" }]} />
          )}
          <Text style={styles.title} testID="exercise-title">{exercise.name}</Text>
          <View style={styles.chips}>
            <LevelChip level={exercise.level} testID="exercise-level" />
            {[exercise.target, exercise.equipment].filter(Boolean).map((t) => <Text key={t} style={styles.chip}>{t}</Text>)}
            {exercise.similar && <Text style={styles.chip}>Similar movement</Text>}
          </View>

          {sets ? (
            <View style={styles.dose} testID="exercise-dose">
              <Dose label="Sets" value={sets} />
              <Dose label="Reps" value={reps || "-"} />
              <Dose label="Rest" value={rest && rest !== "0" ? `${rest}s` : "-"} />
            </View>
          ) : exercise.sets ? (
            <Text style={styles.suggest} testID="exercise-suggested">Suggested: {exercise.sets} sets × {exercise.reps} reps</Text>
          ) : null}

          {mode === "candidate" && slot ? (
            <PrimaryButton testID="exercise-use-button" variant="brand" loading={busy} label="Use this in my plan" onPress={() => planAction("PUT")} />
          ) : (
            <PrimaryButton testID="exercise-alternatives-button" variant="light" label="Alternatives"
              icon={<Ionicons name="swap-horizontal" size={18} color={colors.onSurface} />} onPress={() => setAltOpen(true)} />
          )}
          {mode === "swapped" && slot && (
            <PrimaryButton testID="exercise-reset-button" variant="light" loading={busy} label="Reset to original" onPress={() => planAction("DELETE")} />
          )}
          {!!actionError && <Text style={styles.err}>{actionError}</Text>}

          {exercise.tips.length > 0 && (
            <Card style={styles.block}>
              <Text style={styles.blockTitle}>Tips</Text>
              {exercise.tips.map((c) => (
                <View key={c} style={styles.cue}>
                  <Ionicons name="checkmark-circle" size={18} color={colors.success} />
                  <Text style={styles.stepText}>{c}</Text>
                </View>
              ))}
            </Card>
          )}

          <Card style={styles.block}>
            <Text style={styles.blockTitle}>How to do it</Text>
            {exercise.instructions.map((step, i) => (
              <View key={i} style={styles.step}>
                <View style={styles.num}><Text style={styles.numText}>{i + 1}</Text></View>
                <Text style={styles.stepText}>{step}</Text>
              </View>
            ))}
          </Card>

          {exercise.primary_muscles.length > 0 && <Text style={styles.also}>Main muscles: {exercise.primary_muscles.join(", ")}</Text>}
          {exercise.secondary_muscles.length > 0 && <Text style={styles.also}>Also works: {exercise.secondary_muscles.join(", ")}</Text>}
          <Text style={styles.credit} testID="exercise-credit">
            {exercise.source === "workoutx" ? "Demos by WorkoutX" : "Photos: free-exercise-db (public domain)"}
          </Text>
        </ScrollView>
      )}
      <AlternativesSheet exerciseId={altOpen && exercise ? exercise.canonical_id : null} exerciseName={exercise?.name}
        slot={mode === "candidate" ? undefined : slot} onClose={() => setAltOpen(false)} onSwapped={backToPlan} />
    </View>
  );
}

function Dose({ label, value }: { label: string; value: string }) {
  const styles = useStyles();
  return (
    <View style={styles.doseItem}>
      <Text style={styles.doseVal}>{value}</Text>
      <Text style={styles.doseLabel}>{label}</Text>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  back: { width: 44, height: 44, justifyContent: "center", marginLeft: spacing.md },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.lg, padding: spacing.xl },
  err: { color: c.error, fontWeight: "600", textAlign: "center" },
  scroll: { paddingHorizontal: spacing.xl, gap: spacing.md },
  title: { fontSize: 28, fontWeight: "900", color: c.onSurface, marginTop: spacing.sm },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, alignItems: "center" },
  chip: { fontSize: 12, fontWeight: "800", color: c.onSurfaceTertiary, backgroundColor: c.surfaceSecondary, paddingHorizontal: spacing.md, paddingVertical: 4, borderRadius: radius.pill, overflow: "hidden", textTransform: "capitalize" },
  dose: { flexDirection: "row", backgroundColor: c.brandSecondary, borderRadius: radius.lg, paddingVertical: spacing.lg },
  doseItem: { flex: 1, alignItems: "center", paddingHorizontal: spacing.xs },
  doseVal: { fontSize: 20, fontWeight: "900", color: c.onBrandSecondary, textAlign: "center" },
  doseLabel: { fontSize: 12, fontWeight: "800", color: c.onBrandSecondary, marginTop: 2 },
  suggest: { fontSize: 15, fontWeight: "800", color: c.onBrandTertiary },
  block: { gap: spacing.md },
  blockTitle: { fontSize: 18, fontWeight: "900", color: c.onSurface },
  cue: { flexDirection: "row", gap: spacing.sm, alignItems: "flex-start" },
  step: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start" },
  num: { width: 26, height: 26, borderRadius: 13, backgroundColor: c.brandTertiary, alignItems: "center", justifyContent: "center" },
  numText: { fontSize: 13, fontWeight: "900", color: c.onBrandTertiary },
  stepText: { flex: 1, fontSize: 15, lineHeight: 21, fontWeight: "500", color: c.onSurface },
  also: { fontSize: 13, fontWeight: "600", color: c.muted, textTransform: "capitalize" },
  credit: { fontSize: 12, fontWeight: "700", color: c.muted, textAlign: "center", marginTop: spacing.md },
}));
