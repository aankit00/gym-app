import React, { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Platform, Pressable, ScrollView, Share, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { captureRef } from "react-native-view-shot";
import * as Sharing from "expo-sharing";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useApi } from "@/src/api";
import { Hexagon, PrimaryButton } from "@/src/components/ui";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

type Recap = {
  month: string; label: string; name: string; city: string; visits: number; xp: number; weeks_hit: number; weeks_total: number;
  weekly_target: number; consistency: number; streak_weeks: number; level: number; active_days: string[]; days_in_month: number;
  first_weekday: number; busiest_day: string | null; in_progress: boolean;
};

const shift = (month: string, by: number) => {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + by, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
};

function RecapCard({ r }: { r: Recap }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const active = new Set(r.active_days.map((d) => Number(d.slice(8, 10))));
  const cells = [...Array(r.first_weekday).fill(0), ...Array.from({ length: r.days_in_month }, (_, i) => i + 1)];
  return (
    <View style={styles.card} testID="recap-card">
      <View style={styles.brandRow}>
        <Hexagon size={22} color={colors.brandSecondary} />
        <Text style={styles.brand}>GYMPROOF</Text>
        <Text style={styles.month}>{r.label.toUpperCase()}</Text>
      </View>
      <Text style={styles.hello}>{r.name}&apos;s month{r.in_progress ? " so far" : ""}</Text>
      <View style={styles.big}>
        <Stat value={String(r.visits)} label="verified visits" testID="recap-visits" />
        <Stat value={`+${r.xp}`} label="XP earned" testID="recap-xp" />
        <Stat value={`${r.consistency}%`} label="consistency" testID="recap-consistency" />
      </View>
      <View style={styles.grid}>
        {cells.map((d, i) => (
          <View key={i} style={[styles.cell, d === 0 && styles.cellBlank, active.has(d) && styles.cellOn]}>
            {d > 0 && <Text style={[styles.cellText, active.has(d) && styles.cellTextOn]}>{d}</Text>}
          </View>
        ))}
      </View>
      <Text style={styles.foot}>
        {r.weeks_hit}/{r.weeks_total} weeks hit the {r.weekly_target}-day goal · {r.streak_weeks}-week streak
        {r.busiest_day ? ` · loves ${r.busiest_day}` : ""}
      </Text>
      <Text style={styles.tag}>Every visit verified by live photo · {r.city}</Text>
    </View>
  );
}

function Stat({ value, label, testID }: { value: string; label: string; testID: string }) {
  const styles = useStyles();
  return (
    <View style={styles.stat}>
      <Text style={styles.statVal} testID={testID}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

export default function RecapScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { call } = useApi();
  const cardRef = useRef<any>(null);
  const [month, setMonth] = useState<string | null>(null);
  const [current, setCurrent] = useState<string | null>(null);
  const [recap, setRecap] = useState<Recap | null>(null);
  const [error, setError] = useState("");
  const [sharing, setSharing] = useState(false);

  const load = useCallback(async () => {
    try {
      setError("");
      setRecap(null);
      const r = await call<Recap>(`/recap${month ? `?month=${month}` : ""}`);
      setRecap(r);
      setCurrent((c) => c ?? r.month);
    } catch (e: any) {
      setError(e.message);
    }
  }, [call, month]);
  useEffect(() => { load(); }, [load]);

  const share = async () => {
    if (!recap) return;
    setSharing(true);
    setError("");
    const text = `My ${recap.label} on GymProof: ${recap.visits} verified gym visits, +${recap.xp} XP, ${recap.consistency}% consistency.`;
    try {
      if (Platform.OS === "web") {
        await Share.share({ message: text }); // browsers can't hand an image to other apps here
      } else {
        const uri = await captureRef(cardRef, { format: "png", quality: 1, result: "tmpfile" });
        if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(uri, { mimeType: "image/png", dialogTitle: "Share your recap" });
        else await Share.share({ message: text, url: uri });
      }
    } catch (e: any) {
      if (!/cancel/i.test(String(e?.message))) setError("Couldn't share right now. Try again.");
    } finally {
      setSharing(false);
    }
  };

  const shown = recap?.month ?? month;
  return (
    <View style={[styles.root, { paddingTop: insets.top + spacing.sm }]} testID="recap-screen">
      <View style={styles.top}>
        <Pressable testID="recap-close-button" onPress={() => router.back()} style={styles.iconBtn} hitSlop={8}>
          <Ionicons name="close" size={26} color={colors.onSurface} />
        </Pressable>
        <Text style={styles.title}>Monthly Recap</Text>
        <View style={styles.iconBtn} />
      </View>
      <View style={styles.monthRow}>
        <Pressable testID="recap-prev-month" disabled={!shown} onPress={() => shown && setMonth(shift(shown, -1))} style={styles.iconBtn} hitSlop={8}>
          <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={styles.monthLabel} testID="recap-month-label">{recap?.label ?? " "}</Text>
        <Pressable testID="recap-next-month" disabled={!shown || shown === current} onPress={() => shown && setMonth(shift(shown, 1))}
          style={[styles.iconBtn, (!shown || shown === current) && { opacity: 0.3 }]} hitSlop={8}>
          <Ionicons name="chevron-forward" size={24} color={colors.onSurface} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + spacing.xl }]}>
        {!recap ? (
          <View style={styles.center}>
            {error ? <><Text style={styles.err}>{error}</Text><PrimaryButton testID="recap-retry-button" label="Retry" onPress={load} /></>
              : <ActivityIndicator color={colors.brandPrimary} size="large" />}
          </View>
        ) : (
          <>
            <View ref={cardRef} collapsable={false}><RecapCard r={recap} /></View>
            <PrimaryButton testID="recap-share-button" variant="brand" loading={sharing} label="Share recap" onPress={share}
              icon={<Ionicons name="share-social" size={18} color={colors.onBrandPrimary} />} />
            {recap.visits === 0 && <Text style={styles.hint}>No verified visits this month yet. Snap a proof to fill your card.</Text>}
            {!!error && <Text style={styles.err}>{error}</Text>}
          </>
        )}
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  top: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.md },
  iconBtn: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  title: { fontSize: 18, fontWeight: "900", color: c.onSurface },
  monthRow: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.md },
  monthLabel: { fontSize: 16, fontWeight: "800", color: c.onSurface, minWidth: 140, textAlign: "center" },
  scroll: { padding: spacing.xl, gap: spacing.lg },
  center: { alignItems: "center", gap: spacing.lg, padding: spacing.xl },
  err: { color: c.error, fontWeight: "600", textAlign: "center" },
  hint: { color: c.muted, fontWeight: "600", textAlign: "center" },
  card: { backgroundColor: c.surfaceInverse, borderRadius: radius.lg, padding: spacing.xl, gap: spacing.lg },
  brandRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  brand: { color: c.onSurfaceInverse, fontWeight: "900", letterSpacing: 2, fontSize: 14, flex: 1 },
  month: { color: c.brandSecondary, fontWeight: "900", letterSpacing: 1, fontSize: 12 },
  hello: { color: c.onSurfaceInverse, fontSize: 26, fontWeight: "900" },
  big: { flexDirection: "row", gap: spacing.sm },
  stat: { flex: 1, backgroundColor: c.brandSecondary, borderRadius: radius.md, paddingVertical: spacing.md, alignItems: "center" },
  statVal: { fontSize: 26, fontWeight: "900", color: c.onBrandSecondary },
  statLabel: { fontSize: 11, fontWeight: "800", color: c.onBrandSecondary, textAlign: "center" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 4 },
  cell: { width: "13%", aspectRatio: 1, borderRadius: 6, backgroundColor: c.onSurfaceTertiary, alignItems: "center", justifyContent: "center" },
  cellBlank: { backgroundColor: "transparent" },
  cellOn: { backgroundColor: c.brandPrimary },
  cellText: { fontSize: 11, fontWeight: "800", color: c.muted },
  cellTextOn: { color: c.onBrandPrimary },
  foot: { color: c.onSurfaceInverse, fontWeight: "700", fontSize: 13, lineHeight: 19 },
  tag: { color: c.muted, fontWeight: "700", fontSize: 11 },
}));
