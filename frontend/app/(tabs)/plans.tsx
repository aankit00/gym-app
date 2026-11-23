import React, { useCallback, useState } from "react";
import { ActivityIndicator, RefreshControl, ScrollView, Text, View } from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { PlanCard, ProStatus, useApi } from "@/src/api";
import { BigTitle, PressScale, PrimaryButton, Segmented } from "@/src/components/ui";
import ExerciseLibrary from "@/src/components/ExerciseLibrary";
import { usesNativeTabs } from "@/src/navigation";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

type PlansResponse = { plans: PlanCard[]; pro: ProStatus; default_gender: "male" | "female" };

export default function Plans() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { call } = useApi();
  const [data, setData] = useState<PlansResponse | null>(null);
  const [gender, setGender] = useState<string>("");
  const [view, setView] = useState("plans");
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      setError("");
      const res = await call<PlansResponse>("/plans");
      setData(res);
      setGender((g) => g || res.default_gender);
    } catch (e: any) {
      setError(e.message);
    }
  }, [call]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const open = (id: string) => router.push({ pathname: "/plan/[id]", params: { id } });
  const shown = data?.plans.filter((p) => p.gender === gender) ?? [];

  return (
    <View style={styles.root} testID="plans-screen">
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <BigTitle text="Plans" testID="plans-title" />
        <Segmented testIDPrefix="plans-view" value={view} onChange={setView}
          options={[{ key: "plans", label: "Plans" }, { key: "library", label: "Library" }]} />
      </View>
      {view === "library" ? <ExerciseLibrary /> : !data ? (
        <View style={styles.center}>
          {error ? <><Text style={styles.err} testID="plans-error">{error}</Text><PrimaryButton testID="plans-retry-button" label="Retry" onPress={load} /></>
            : <ActivityIndicator color={colors.brandPrimary} size="large" />}
        </View>
      ) : (
        <ScrollView contentContainerStyle={[styles.scroll, { paddingBottom: (usesNativeTabs ? insets.bottom : 0) + spacing["2xl"] }]}
          refreshControl={<RefreshControl refreshing={refreshing} tintColor={colors.brandPrimary}
            onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}>
          <Text style={styles.intro}>Pick the body you&apos;re training for. Every workout comes with exercise demos.</Text>
          <Segmented testIDPrefix="plans-gender" value={gender} onChange={setGender}
            options={[{ key: "male", label: "Men" }, { key: "female", label: "Women" }]} />
          {shown.map((p) => (
            <PressScale key={p.id} testID={`plan-card-${p.id}`} onPress={() => open(p.id)} style={[styles.card, p.active && styles.cardActive]}>
              <View style={styles.cardTop}>
                <View style={[styles.icon, p.premium && styles.iconPro]}>
                  <Ionicons name={p.icon as any} size={24} color={p.premium ? colors.onSurfaceInverse : colors.onBrandSecondary} />
                </View>
                <View style={styles.cardText}>
                  <Text style={styles.name}>{p.name}</Text>
                  <Text style={styles.tagline}>{p.tagline}</Text>
                </View>
                {p.active ? <View style={[styles.tag, styles.tagActive]}><Text style={styles.tagActiveText}>ACTIVE</Text></View>
                  : p.premium ? (
                    <View style={[styles.tag, styles.tagPro]} testID={`plan-pro-tag-${p.id}`}>
                      {p.locked && <Ionicons name="lock-closed" size={11} color={colors.onSurfaceInverse} />}
                      <Text style={styles.tagProText}>PRO</Text>
                    </View>
                  ) : null}
              </View>
              <View style={styles.chips}>
                <Text style={styles.chip}>{p.days_per_week} days / week</Text>
                <Text style={styles.chip}>{p.duration_weeks} weeks</Text>
                <Text style={styles.chip}>{p.level}</Text>
              </View>
            </PressScale>
          ))}
          {!data.pro.unlocked && (
            <Text style={styles.proNote} testID="plans-pro-note">
              PRO plans unlock together with one payment of ₹{data.pro.price_inr}. Open any PRO plan to see what&apos;s inside.
            </Text>
          )}
        </ScrollView>
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  header: { paddingHorizontal: spacing.xl, paddingBottom: spacing.md, gap: spacing.sm },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.lg, padding: spacing.xl },
  err: { color: c.error, fontWeight: "600", textAlign: "center" },
  scroll: { paddingHorizontal: spacing.xl, paddingTop: spacing.sm, gap: spacing.md },
  intro: { fontSize: 16, fontWeight: "600", color: c.muted, marginBottom: spacing.xs },
  card: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.md, borderWidth: 2, borderColor: c.surfaceSecondary },
  cardActive: { borderColor: c.brandPrimary },
  cardTop: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  icon: { width: 48, height: 48, borderRadius: 24, backgroundColor: c.brandSecondary, alignItems: "center", justifyContent: "center" },
  iconPro: { backgroundColor: c.surfaceInverse },
  cardText: { flex: 1 },
  name: { fontSize: 20, fontWeight: "900", color: c.onSurface },
  tagline: { fontSize: 14, fontWeight: "600", color: c.muted, marginTop: 2 },
  tag: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: spacing.sm, height: 24, borderRadius: radius.sm },
  tagPro: { backgroundColor: c.surfaceInverse },
  tagProText: { color: c.onSurfaceInverse, fontSize: 11, fontWeight: "900", letterSpacing: 1 },
  tagActive: { backgroundColor: c.brandPrimary },
  tagActiveText: { color: c.onBrandPrimary, fontSize: 11, fontWeight: "900", letterSpacing: 1 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: { fontSize: 12, fontWeight: "800", color: c.onSurfaceTertiary, backgroundColor: c.surface, paddingHorizontal: spacing.md, paddingVertical: 6, borderRadius: radius.pill, overflow: "hidden" },
  proNote: { fontSize: 13, fontWeight: "600", color: c.muted, textAlign: "center", marginTop: spacing.sm },
}));
