import React from "react";
import { Text, View } from "react-native";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import type { WeekDay } from "@/src/api";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

export default function WeekRow({ days }: { days: WeekDay[] }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <View style={styles.row} testID="week-row">
      {days.map((d) => (
        <View key={d.date} testID={`week-day-${d.label.toLowerCase()}`} style={[styles.day, d.done && styles.dayDone, d.is_today && !d.done && styles.today]}>
          <Text style={[styles.label, d.done && { color: colors.onBrandSecondary }]}>{d.label}</Text>
          <Ionicons name="flame" size={26} color={d.done ? colors.brandPrimary : colors.surfaceTertiary} />
        </View>
      ))}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  row: { flexDirection: "row", gap: 6 },
  day: { flex: 1, alignItems: "center", gap: spacing.sm, paddingVertical: spacing.md, borderRadius: radius.md, backgroundColor: c.surfaceSecondary, borderWidth: 2, borderColor: c.surfaceSecondary },
  dayDone: { backgroundColor: c.brandTertiary, borderColor: c.brandSecondary },
  today: { borderColor: c.onSurface },
  label: { fontSize: 12, fontWeight: "800", color: c.muted },
}));
