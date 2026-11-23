import React from "react";
import { Text, View } from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import type { Dashboard } from "@/src/api";
import { PressScale } from "@/src/components/ui";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

export default function HomePlanCard({ plan }: { plan: Dashboard["active_plan"] }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  return (
    <PressScale testID="home-plan-card" style={styles.card}
      onPress={() => (plan ? router.push({ pathname: "/plan/[id]", params: { id: plan.id } }) : router.push("/plans"))}>
      <View style={styles.icon}><Ionicons name="barbell" size={22} color={colors.onBrandSecondary} /></View>
      <View style={styles.text}>
        <Text style={styles.title} testID="home-plan-title">{plan ? plan.name : "Pick a training plan"}</Text>
        <Text style={styles.sub}>{plan ? `Your plan · ${plan.days_per_week} days a week` : "Workouts for your goal, with exercise demos"}</Text>
      </View>
      <Ionicons name="chevron-forward" size={20} color={colors.muted} />
    </PressScale>
  );
}

const useStyles = makeStyles((c) => ({
  card: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, marginTop: spacing.md, minHeight: 72 },
  icon: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center", backgroundColor: c.brandSecondary },
  text: { flex: 1 },
  title: { fontSize: 16, fontWeight: "800", color: c.onSurface },
  sub: { fontSize: 13, fontWeight: "600", color: c.muted, marginTop: 2 },
}));
