import React from "react";
import { Text, View } from "react-native";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import type { Freeze } from "@/src/api";
import { PressScale } from "@/src/components/ui";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

export default function FreezeCard({ freeze, onPress }: { freeze: Freeze; onPress: () => void }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const urgent = !!freeze.repair;
  const title = urgent ? `Repair your ${freeze.repair!.streak_at_risk}-week streak`
    : freeze.owned > 0 ? "Streak Freeze ready"
    : freeze.last_week_frozen ? "A freeze saved your streak" : "Streak Freeze";
  const sub = urgent ? `You missed last week. Fix it for ₹${freeze.price_inr} before this week ends.`
    : freeze.owned > 0 ? "It's used automatically if you miss a week."
    : `Protect your streak from one missed week · ₹${freeze.price_inr}`;
  return (
    <PressScale testID="freeze-card" onPress={onPress} style={[styles.card, urgent && styles.urgent]}>
      <View style={[styles.icon, { backgroundColor: urgent ? colors.error : colors.info }]}>
        <Ionicons name={urgent ? "bandage" : "snow"} size={22} color={urgent ? colors.onError : colors.onInfo} />
      </View>
      <View style={styles.text}>
        <Text style={styles.title} testID="freeze-card-title">{title}</Text>
        <Text style={styles.sub}>{sub}</Text>
      </View>
      <Ionicons name="chevron-forward" size={20} color={colors.muted} />
    </PressScale>
  );
}

const useStyles = makeStyles((c) => ({
  card: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, marginTop: spacing.md, borderWidth: 2, borderColor: c.surfaceSecondary, minHeight: 72 },
  urgent: { borderColor: c.error },
  icon: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center" },
  text: { flex: 1 },
  title: { fontSize: 16, fontWeight: "800", color: c.onSurface },
  sub: { fontSize: 13, fontWeight: "600", color: c.muted, marginTop: 2 },
}));
