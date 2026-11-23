import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Animated, { ZoomIn } from "react-native-reanimated";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { Freeze, useApi } from "@/src/api";
import RazorpayCheckout from "@/src/payments/RazorpayCheckout";
import { usePurchase } from "@/src/payments/usePurchase";
import { Card, PrimaryButton } from "@/src/components/ui";
import { makeStyles, spacing, useTheme } from "@/src/theme";

type FreezeStatus = Freeze & { streak_weeks: number };
const HOW = [
  ["snow", "One freeze covers one missed week, so your streak doesn't reset."],
  ["flash", "If you own a freeze it's used automatically. Nothing to remember."],
  ["bandage", "No freeze? You have until the end of the next week to buy one and repair the streak."],
  ["pause", "A frozen week keeps your streak alive but doesn't add to it."],
] as const;

export default function FreezeScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { call } = useApi();
  const [status, setStatus] = useState<FreezeStatus | null>(null);
  const [loadError, setLoadError] = useState("");
  const [justBought, setJustBought] = useState(false);

  const load = useCallback(async () => {
    try {
      setStatus(await call<FreezeStatus>("/freeze"));
    } catch (e: any) {
      setLoadError(e.message);
    }
  }, [call]);

  useEffect(() => { load(); }, [load]);

  const { buy, busy, error, notice, checkout } = usePurchase("/freeze/order", async (fulfilled) => {
    if (fulfilled) setJustBought(true);
    await load();
  });
  const repair = status?.repair;
  const deadline = repair ? new Date(`${repair.deadline}T12:00:00`).toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short" }) : "";

  return (
    <View style={[styles.root, { paddingTop: insets.top + spacing.sm }]} testID="freeze-screen">
      <Pressable testID="freeze-close-button" onPress={() => router.back()} style={styles.close} hitSlop={8}>
        <Ionicons name="close" size={26} color={colors.onSurface} />
      </Pressable>
      {!status ? (
        <View style={styles.center}>
          {loadError ? <><Text style={styles.err}>{loadError}</Text><PrimaryButton testID="freeze-retry-button" label="Retry" onPress={() => { setLoadError(""); load(); }} /></>
            : <ActivityIndicator color={colors.brandPrimary} size="large" />}
        </View>
      ) : (
        <>
          <ScrollView contentContainerStyle={styles.scroll}>
            <Animated.View entering={ZoomIn.springify()} style={styles.hero}>
              <Ionicons name="snow" size={56} color={colors.onInfo} />
            </Animated.View>
            <Text style={styles.title} testID="freeze-title">
              {justBought ? (status.last_week_frozen ? "STREAK REPAIRED" : "FREEZE READY")
                : repair ? "REPAIR YOUR STREAK" : status.owned > 0 ? "FREEZE READY" : "STREAK FREEZE"}
            </Text>
            <Text style={styles.body} testID="freeze-body">
              {repair
                ? `You missed last week and your ${repair.streak_at_risk}-week streak is broken. Buy a freeze by ${deadline} to bring it back.`
                : status.owned > 0
                  ? "You have a Streak Freeze. It kicks in by itself the next time you miss a week."
                  : status.last_week_frozen
                    ? `A freeze covered last week, so your ${status.streak_weeks}-week streak is safe. Get another to stay protected.`
                    : "Life happens. A Streak Freeze saves your streak when you miss one week."}
            </Text>
            <Card style={styles.how}>
              {HOW.map(([icon, text]) => (
                <View key={text} style={styles.howRow}>
                  <View style={styles.howIcon}><Ionicons name={icon} size={18} color={colors.onSurface} /></View>
                  <Text style={styles.howText}>{text}</Text>
                </View>
              ))}
            </Card>
            {!!notice && <Text style={styles.notice} testID="freeze-notice">{notice}</Text>}
            {!!error && <Text style={styles.err} testID="freeze-error">{error}</Text>}
          </ScrollView>
          <View style={[styles.footer, { paddingBottom: insets.bottom + spacing.lg }]}>
            {status.owned > 0 ? (
              <PrimaryButton testID="freeze-done-button" label="Done" variant="brand" onPress={() => router.back()} />
            ) : (
              <>
                <PrimaryButton testID="freeze-buy-button" variant="brand" loading={busy} disabled={!status.payments_enabled}
                  label={`${repair ? "Repair streak" : "Get Streak Freeze"} · ₹${status.price_inr}`} onPress={buy} />
                <Text style={styles.small} testID="freeze-pay-note">
                  {status.payments_enabled ? "One-time payment via Razorpay. UPI, cards and netbanking." : "Payments aren't switched on yet. Check back soon."}
                </Text>
              </>
            )}
          </View>
        </>
      )}
      <RazorpayCheckout {...checkout} />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  close: { width: 44, height: 44, justifyContent: "center", marginLeft: spacing.lg },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.lg, padding: spacing.xl },
  scroll: { paddingHorizontal: spacing.xl, paddingBottom: spacing.xl, alignItems: "center", gap: spacing.lg },
  hero: { width: 112, height: 112, borderRadius: 56, backgroundColor: c.info, alignItems: "center", justifyContent: "center", marginTop: spacing.lg },
  title: { fontSize: 28, fontWeight: "900", color: c.onSurface, textAlign: "center" },
  body: { fontSize: 16, lineHeight: 22, fontWeight: "500", color: c.onSurfaceTertiary, textAlign: "center" },
  how: { alignSelf: "stretch" },
  howRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingVertical: spacing.sm },
  howIcon: { width: 36, height: 36, borderRadius: 18, backgroundColor: c.brandTertiary, alignItems: "center", justifyContent: "center" },
  howText: { flex: 1, fontSize: 15, fontWeight: "600", color: c.onSurface },
  footer: { paddingHorizontal: spacing.xl, paddingTop: spacing.md, gap: spacing.sm },
  small: { fontSize: 13, fontWeight: "600", color: c.muted, textAlign: "center" },
  notice: { color: c.onSurfaceTertiary, fontWeight: "600", textAlign: "center" },
  err: { color: c.error, fontWeight: "600", textAlign: "center" },
}));
