import React from "react";
import { Text, View } from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Animated, { FadeInDown } from "react-native-reanimated";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useAppSession } from "@/src/auth/AppSession";
import { PrimaryButton, Hexagon } from "@/src/components/ui";
import { makeStyles, spacing, useTheme } from "@/src/theme";

const BG = "https://images.pexels.com/photos/4753994/pexels-photo-4753994.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=1200&w=800";

export default function Welcome() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { googleSignIn, googleBusy, googleError } = useAppSession();
  return (
    <View style={styles.root} testID="welcome-screen">
      <Image source={{ uri: BG }} style={styles.bg} contentFit="cover" transition={300} />
      <LinearGradient colors={["rgba(0,0,0,0.1)", "rgba(0,0,0,0.55)", "rgba(0,0,0,0.95)"]} style={styles.bg} />
      <View style={[styles.content, { paddingTop: insets.top + spacing.lg, paddingBottom: insets.bottom + spacing.xl }]}>
        <View style={styles.brandRow}>
          <Hexagon size={30} color={colors.brandSecondary} />
          <Text style={styles.brand}>GYMPROOF</Text>
        </View>
        <View style={{ flex: 1 }} />
        <Animated.View entering={FadeInDown.delay(100).duration(500)}>
          <Text style={styles.kicker}>PROOF OF WORKOUT</Text>
          <Text style={styles.title}>SHOW UP.{"\n"}PROVE IT.{"\n"}KEEP THE STREAK.</Text>
        </Animated.View>
        <Animated.View entering={FadeInDown.delay(250).duration(500)} style={styles.points}>
          {[
            ["camera", "Live camera proof — no gallery, no old photos"],
            ["flame", "Weekly streaks that feel earned"],
            ["trophy", "Earn XP and climb your city's board"],
          ].map(([icon, t]) => (
            <View key={t} style={styles.point}>
              <Ionicons name={icon as any} size={18} color={colors.brandSecondary} />
              <Text style={styles.pointText}>{t}</Text>
            </View>
          ))}
        </Animated.View>
        <Animated.View entering={FadeInDown.delay(400).duration(500)} style={styles.buttons}>
          <PrimaryButton testID="get-started-button" label="Continue with phone" variant="brand" onPress={() => router.push("/sign-in")}
            icon={<Ionicons name="call" size={18} color={colors.onBrandPrimary} />} />
          <PrimaryButton testID="google-sign-in-button" label="Continue with Google" variant="light" loading={googleBusy} onPress={googleSignIn}
            icon={<Ionicons name="logo-google" size={18} color={colors.onSurface} />} />
          <PrimaryButton testID="email-sign-in-button" label="Continue with email" variant="light" onPress={() => router.push("/email-sign-in")}
            icon={<Ionicons name="mail" size={18} color={colors.onSurface} />} />
          {!!googleError && <Text style={styles.err} testID="google-sign-in-error">{googleError}</Text>}
          <Text style={styles.note}>Phone, Google and email are separate accounts.</Text>
        </Animated.View>
      </View>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surfaceInverse },
  bg: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
  content: { flex: 1, paddingHorizontal: spacing.xl },
  brandRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  brand: { color: c.onSurfaceInverse, fontSize: 18, fontWeight: "900", letterSpacing: 2 },
  kicker: { color: c.brandSecondary, fontWeight: "900", letterSpacing: 2, fontSize: 13, marginBottom: spacing.sm },
  title: { color: c.onSurfaceInverse, fontSize: 40, lineHeight: 44, fontWeight: "900" },
  points: { gap: spacing.md, marginVertical: spacing.xl },
  buttons: { gap: spacing.sm },
  err: { color: c.brandSecondary, fontWeight: "700", textAlign: "center" },
  note: { color: c.onSurfaceInverse, opacity: 0.7, fontSize: 12, fontWeight: "600", textAlign: "center", marginTop: spacing.xs },
  point: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  pointText: { color: c.onSurfaceInverse, fontSize: 15, fontWeight: "600", flex: 1 },
}));
