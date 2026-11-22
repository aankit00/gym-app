import React from "react";
import { ActivityIndicator, Pressable, StyleProp, Text, View, ViewStyle } from "react-native";
import Svg, { Polygon } from "react-native-svg";
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from "react-native-reanimated";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

export function Hexagon({ size = 40, color }: { size?: number; color: string }) {
  const h = size;
  const w = size * 0.92;
  return (
    <Svg width={w} height={h} viewBox="0 0 92 100">
      <Polygon points="46,0 92,25 92,75 46,100 0,75 0,25" fill={color} />
    </Svg>
  );
}

export function BigTitle({ text, right, testID }: { text: string; right?: React.ReactNode; testID?: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <View style={styles.titleRow}>
      <View style={styles.titleWrap}>
        <View style={styles.hex} pointerEvents="none"><Hexagon size={42} color={colors.brandSecondary} /></View>
        <Text testID={testID} style={styles.bigTitle}>{text.toUpperCase()}</Text>
      </View>
      {right}
    </View>
  );
}

export function SectionTitle({ text, right }: { text: string; right?: React.ReactNode }) {
  const styles = useStyles();
  return (
    <View style={styles.sectionRow}>
      <View>
        <View style={styles.underline} />
        <Text style={styles.sectionTitle}>{text}</Text>
      </View>
      {right}
    </View>
  );
}

export function Card({ children, style, testID }: { children: React.ReactNode; style?: StyleProp<ViewStyle>; testID?: string }) {
  const styles = useStyles();
  return <View testID={testID} style={[styles.card, style]}>{children}</View>;
}

export function PressScale({ children, onPress, disabled, style, testID }: {
  children: React.ReactNode; onPress?: () => void; disabled?: boolean; style?: StyleProp<ViewStyle>; testID?: string;
}) {
  const s = useSharedValue(1);
  const a = useAnimatedStyle(() => ({ transform: [{ scale: s.value }] }));
  return (
    <Pressable testID={testID} disabled={disabled} onPress={onPress}
      onPressIn={() => (s.value = withSpring(0.96))} onPressOut={() => (s.value = withSpring(1))}>
      <Animated.View style={[style, a, disabled && { opacity: 0.5 }]}>{children}</Animated.View>
    </Pressable>
  );
}

export function PrimaryButton({ label, onPress, disabled, loading, testID, variant = "dark", icon }: {
  label: string; onPress?: () => void; disabled?: boolean; loading?: boolean; testID?: string;
  variant?: "dark" | "brand" | "light"; icon?: React.ReactNode;
}) {
  const styles = useStyles();
  const { colors } = useTheme();
  const bg = variant === "dark" ? colors.surfaceInverse : variant === "brand" ? colors.brandPrimary : colors.surfaceSecondary;
  const fg = variant === "dark" ? colors.onSurfaceInverse : variant === "brand" ? colors.onBrandPrimary : colors.onSurface;
  return (
    <PressScale testID={testID} onPress={onPress} disabled={disabled || loading} style={[styles.btn, { backgroundColor: bg }]}>
      {loading ? <ActivityIndicator color={fg} /> : (
        <View style={styles.btnInner}>
          {icon}
          <Text style={[styles.btnText, { color: fg }]}>{label}</Text>
        </View>
      )}
    </PressScale>
  );
}

export function Segmented({ options, value, onChange, testIDPrefix }: {
  options: { key: string; label: string }[]; value: string; onChange: (k: string) => void; testIDPrefix: string;
}) {
  const styles = useStyles();
  return (
    <View style={styles.seg}>
      {options.map((o) => (
        <Pressable key={o.key} testID={`${testIDPrefix}-${o.key}`} onPress={() => onChange(o.key)}
          style={[styles.segItem, value === o.key && styles.segActive]}>
          <Text style={[styles.segText, value === o.key && styles.segTextActive]}>{o.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  titleRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: spacing.sm },
  titleWrap: { flexDirection: "row", alignItems: "center" },
  hex: { position: "absolute", left: -8, top: -6 },
  bigTitle: { fontSize: 32, fontWeight: "900", color: c.onSurface, letterSpacing: 0.5 },
  sectionRow: { flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between", marginTop: spacing.xl, marginBottom: spacing.md },
  underline: { position: "absolute", left: 0, bottom: 2, height: 10, width: 48, backgroundColor: c.brandPrimary, borderRadius: 2 },
  sectionTitle: { fontSize: 24, fontWeight: "800", color: c.onSurface },
  card: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, shadowColor: "#000", shadowOpacity: 0.04, shadowRadius: 10, shadowOffset: { width: 0, height: 2 }, elevation: 1 },
  btn: { height: 56, borderRadius: radius.pill, alignItems: "center", justifyContent: "center", paddingHorizontal: spacing.xl },
  btnInner: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  btnText: { fontSize: 17, fontWeight: "800", letterSpacing: 0.3 },
  seg: { flexDirection: "row", backgroundColor: c.surfaceTertiary, borderRadius: radius.pill, padding: 4 },
  segItem: { flex: 1, height: 44, borderRadius: radius.pill, alignItems: "center", justifyContent: "center" },
  segActive: { backgroundColor: c.surfaceSecondary, shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 6, shadowOffset: { width: 0, height: 2 }, elevation: 2 },
  segText: { fontSize: 15, fontWeight: "700", color: c.muted },
  segTextActive: { color: c.onSurface },
}));
