import React, { useEffect, useState } from "react";
import { ActivityIndicator, Modal, Pressable, ScrollView, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { LibraryItem, useApi } from "@/src/api";
import { ExerciseThumb, LevelChip } from "@/src/components/LevelChip";
import { PrimaryButton } from "@/src/components/ui";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

export type PlanSlot = { planId: string; day: number; index: number; sets?: number; reps?: string; rest?: number };

// Bottom sheet with 5–6 swaps for the same muscle. With a plan slot, "Use this" puts the pick into that plan day.
export default function AlternativesSheet({ exerciseId, exerciseName, slot, onClose, onSwapped }: {
  exerciseId: string | null; exerciseName?: string; slot?: PlanSlot; onClose: () => void; onSwapped?: () => void;
}) {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { call } = useApi();
  const [items, setItems] = useState<LibraryItem[] | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    if (!exerciseId) return;
    setItems(null);
    setError("");
    const q = slot ? `?plan_id=${encodeURIComponent(slot.planId)}` : "";
    call<{ items: LibraryItem[] }>(`/exercises/${encodeURIComponent(exerciseId)}/alternatives${q}`)
      .then((r) => setItems(r.items))
      .catch((e) => setError(e.message));
  }, [exerciseId, slot, call]);

  const use = async (item: LibraryItem) => {
    if (!slot) return;
    setSaving(item.id);
    setError("");
    try {
      await call(`/plans/${slot.planId}/days/${slot.day}/exercises/${slot.index}`, { method: "PUT", body: { exercise_id: item.id } });
      onSwapped?.();
      onClose();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(null);
    }
  };

  const preview = (item: LibraryItem) => {
    onClose();
    router.push({
      pathname: "/exercise/[id]",
      params: {
        id: item.id,
        ...(slot ? { planId: slot.planId, day: String(slot.day), index: String(slot.index), sets: String(slot.sets ?? ""), reps: slot.reps ?? "", rest: String(slot.rest ?? ""), mode: "candidate" } : {}),
      },
    });
  };

  return (
    <Modal visible={!!exerciseId} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.scrim} onPress={onClose} testID="alternatives-scrim" />
      <View style={[styles.sheet, { paddingBottom: insets.bottom + spacing.lg }]} testID="alternatives-sheet">
        <View style={styles.grabber} />
        <View style={styles.head}>
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>Alternatives</Text>
            {!!exerciseName && <Text style={styles.sub} numberOfLines={1}>Same muscles as {exerciseName}</Text>}
          </View>
          <Pressable testID="alternatives-close-button" onPress={onClose} hitSlop={8} style={styles.close}>
            <Ionicons name="close" size={22} color={colors.onSurface} />
          </Pressable>
        </View>
        {!items ? (
          <View style={styles.center}>
            {error ? <Text style={styles.err}>{error}</Text> : <ActivityIndicator color={colors.brandPrimary} />}
          </View>
        ) : (
          <ScrollView contentContainerStyle={styles.list}>
            {items.length === 0 && <Text style={styles.sub}>No close swaps found for this move.</Text>}
            {items.map((it, i) => (
              <View key={it.id} style={styles.row}>
                <Pressable testID={`alternative-${i}`} onPress={() => preview(it)} style={styles.rowMain}>
                  <ExerciseThumb uri={it.thumb} size={60} />
                  <View style={{ flex: 1, gap: 4 }}>
                    <Text style={styles.name} numberOfLines={2}>{it.name}</Text>
                    <View style={styles.metaRow}>
                      <LevelChip level={it.level} />
                      <Text style={styles.meta} numberOfLines={1}>{it.equipment}</Text>
                    </View>
                  </View>
                </Pressable>
                {slot && (
                  <View style={styles.useBtn}>
                    <PrimaryButton testID={`alternative-use-${i}`} label="Use" variant="dark" loading={saving === it.id}
                      disabled={!!saving} onPress={() => use(it)} />
                  </View>
                )}
              </View>
            ))}
            {!!error && <Text style={styles.err}>{error}</Text>}
          </ScrollView>
        )}
      </View>
    </Modal>
  );
}

const useStyles = makeStyles((c) => ({
  scrim: { flex: 1, backgroundColor: c.scrim },
  sheet: { backgroundColor: c.surface, borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg, maxHeight: "80%", paddingTop: spacing.sm },
  grabber: { alignSelf: "center", width: 40, height: 5, borderRadius: 3, backgroundColor: c.borderStrong, marginBottom: spacing.sm },
  head: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.xl, paddingBottom: spacing.md },
  title: { fontSize: 22, fontWeight: "900", color: c.onSurface },
  sub: { fontSize: 14, fontWeight: "600", color: c.muted, marginTop: 2 },
  close: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  center: { padding: spacing["2xl"], alignItems: "center" },
  list: { paddingHorizontal: spacing.xl, gap: spacing.sm, paddingBottom: spacing.md },
  row: { flexDirection: "row", alignItems: "center", backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.sm, gap: spacing.sm },
  rowMain: { flex: 1, flexDirection: "row", alignItems: "center", gap: spacing.md, minHeight: 60 },
  name: { fontSize: 15, fontWeight: "800", color: c.onSurface },
  metaRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  meta: { flex: 1, fontSize: 12, fontWeight: "700", color: c.muted, textTransform: "capitalize" },
  useBtn: { width: 84 },
  err: { color: c.error, fontWeight: "600", textAlign: "center", marginTop: spacing.sm },
}));
