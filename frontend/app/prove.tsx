import React, { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Linking, Pressable, Text, View } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Animated, { FadeIn, ZoomIn } from "react-native-reanimated";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import * as Haptics from "expo-haptics";
import { BACKEND_URL, useApi } from "@/src/api";
import { uploadForm } from "@/src/utils/upload";
import { PrimaryButton } from "@/src/components/ui";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

type Challenge = { challenge_id: string; expires_at: string };
type Result = { status: "accepted" | "rejected" | "suspicious"; reason: string; counted: boolean; xp_awarded: number;
  already_counted_today?: boolean; week_completed_now?: boolean; equipment?: string };

export default function Prove() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { call, authHeader } = useApi();
  const [permission, requestPermission] = useCameraPermissions();
  const cam = useRef<CameraView>(null);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [ready, setReady] = useState(false);
  const [phase, setPhase] = useState<"camera" | "verifying" | "result">("camera");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [facing, setFacing] = useState<"back" | "front">("back");

  const newChallenge = useCallback(async () => {
    try {
      setChallenge(await call<Challenge>("/proof/challenge", { method: "POST" }));
    } catch (e: any) {
      setError(e.message);
    }
  }, [call]);

  useEffect(() => {
    if (permission?.granted) newChallenge();
  }, [permission?.granted, newChallenge]);

  const snap = async () => {
    if (!cam.current || !challenge) return;
    setError("");
    let ch = challenge;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    try {
      if (new Date(ch.expires_at).getTime() - Date.now() < 5000) {
        ch = await call<Challenge>("/proof/challenge", { method: "POST" });
        setChallenge(ch);
      }
      const photo = await cam.current.takePictureAsync({ quality: 0.6 });
      const capturedAt = new Date().toISOString();
      setPhase("verifying");
      const res = await uploadForm(`${BACKEND_URL}/api/proof/submit`, {
        fields: { challenge_id: ch.challenge_id, captured_at: capturedAt },
        files: { image: { uri: photo.uri, name: "proof.jpg", mimeType: "image/jpeg" } },
        headers: await authHeader(),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Upload failed");
      setResult(data);
      setPhase("result");
      Haptics.notificationAsync(data.status === "accepted" ? Haptics.NotificationFeedbackType.Success : Haptics.NotificationFeedbackType.Error).catch(() => {});
    } catch (e: any) {
      setError(e.message);
      setPhase("camera");
      newChallenge();
    }
  };

  const retake = () => { setResult(null); setPhase("camera"); newChallenge(); };

  // ----- Permission states -----
  if (!permission) {
    return <View style={styles.center}><ActivityIndicator color={colors.brandPrimary} /></View>;
  }
  if (!permission.granted) {
    return (
      <View style={[styles.permRoot, { paddingTop: insets.top + spacing.lg, paddingBottom: insets.bottom + spacing.xl }]} testID="camera-permission-screen">
        <Pressable testID="prove-close-button" onPress={() => router.back()} style={styles.closeDark}><Ionicons name="close" size={26} color={colors.onSurface} /></Pressable>
        <View style={{ flex: 1, justifyContent: "center", gap: spacing.lg }}>
          <View style={styles.permIcon}><Ionicons name="camera" size={40} color={colors.onBrandSecondary} /></View>
          <Text style={styles.permTitle}>Camera needed for Gym Proof</Text>
          <Text style={styles.permText}>
            Proof is captured live in the app — no gallery, no old photos. That&apos;s what makes your streak feel earned.
          </Text>
          {!permission.canAskAgain && (
            <Text testID="camera-permission-blocked" style={styles.permText}>Camera access is turned off. Enable it in Settings to prove your workout.</Text>
          )}
        </View>
        {permission.canAskAgain ? (
          <PrimaryButton testID="allow-camera-button" label="Allow camera" onPress={requestPermission} />
        ) : (
          <PrimaryButton testID="open-settings-button" label="Open Settings" onPress={() => Linking.openSettings()} />
        )}
      </View>
    );
  }

  // ----- Result -----
  if (phase === "result" && result) {
    const ok = result.status === "accepted";
    const sus = result.status === "suspicious";
    const tint = ok ? colors.success : sus ? colors.warning : colors.error;
    const title = ok
      ? result.week_completed_now ? "WEEK COMPLETED!" : result.already_counted_today ? "ALREADY PROVEN TODAY" : "GYM PROOF ACCEPTED"
      : sus ? "SUSPICIOUS PHOTO" : "PROOF REJECTED";
    return (
      <View style={[styles.permRoot, { paddingTop: insets.top + spacing.lg, paddingBottom: insets.bottom + spacing.xl }]} testID="proof-result-screen">
        <View style={{ flex: 1, justifyContent: "center", alignItems: "center", gap: spacing.lg }}>
          <Animated.View entering={ZoomIn.springify()} style={[styles.resultIcon, { backgroundColor: tint }]}>
            <Ionicons name={ok ? (result.week_completed_now ? "trophy" : "checkmark") : sus ? "alert" : "close"} size={56} color={colors.onSuccess} />
          </Animated.View>
          <Text testID="proof-result-title" style={styles.resultTitle}>{title}</Text>
          <Text testID="proof-result-reason" style={styles.permText}>{result.reason}</Text>
          {ok && result.counted && (
            <Animated.View entering={FadeIn.delay(300)} style={styles.xpPill}>
              <Ionicons name="flash" size={18} color={colors.onBrandSecondary} />
              <Text testID="proof-result-xp" style={styles.xpText}>+{result.xp_awarded} XP</Text>
            </Animated.View>
          )}
          {ok && result.already_counted_today && (
            <Text style={styles.small}>One counted proof per day. Extra sessions still show up in your history.</Text>
          )}
        </View>
        {ok ? (
          <PrimaryButton testID="proof-done-button" label="Done" variant="brand" onPress={() => router.back()} />
        ) : (
          <View style={{ gap: spacing.md }}>
            <PrimaryButton testID="proof-retake-button" label="Retake photo" onPress={retake} />
            <PrimaryButton testID="proof-cancel-button" label="Cancel" variant="light" onPress={() => router.back()} />
          </View>
        )}
      </View>
    );
  }

  // ----- Camera -----
  return (
    <View style={styles.camRoot} testID="camera-screen">
      <CameraView ref={cam} style={styles.fill} facing={facing} onCameraReady={() => setReady(true)} />
      <View style={[styles.overlay, { paddingTop: insets.top + spacing.md, paddingBottom: insets.bottom + spacing.xl }]} pointerEvents="box-none">
        <View style={styles.camTop}>
          <Pressable testID="prove-close-button" onPress={() => router.back()} style={styles.roundBtn}><Ionicons name="close" size={26} color={colors.onSurfaceInverse} /></Pressable>
          <View style={styles.livePill}><View style={styles.liveDot} /><Text style={styles.liveText}>LIVE CAPTURE</Text></View>
          <Pressable testID="flip-camera-button" onPress={() => setFacing(facing === "back" ? "front" : "back")} style={styles.roundBtn}>
            <Ionicons name="camera-reverse" size={24} color={colors.onSurfaceInverse} />
          </Pressable>
        </View>
        <View style={styles.guide} pointerEvents="none">
          <View style={styles.guideBox} />
          <Text style={styles.guideText}>Show your hand gripping a dumbbell, barbell or any gym equipment</Text>
        </View>
        {!!error && <Text testID="camera-error" style={styles.camError}>{error}</Text>}
        <View style={styles.shutterRow}>
          <Pressable testID="capture-button" disabled={!ready || !challenge || phase === "verifying"} onPress={snap}
            style={[styles.shutter, (!ready || !challenge) && { opacity: 0.4 }]}>
            <View style={styles.shutterInner} />
          </Pressable>
        </View>
      </View>
      {phase === "verifying" && (
        <Animated.View entering={FadeIn} style={styles.verifying} testID="proof-verifying">
          <ActivityIndicator size="large" color={colors.brandSecondary} />
          <Text style={styles.verifyingText}>Checking your Gym Proof…</Text>
        </Animated.View>
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: c.surface },
  permRoot: { flex: 1, backgroundColor: c.surface, paddingHorizontal: spacing.xl },
  closeDark: { width: 44, height: 44, justifyContent: "center" },
  permIcon: { width: 80, height: 80, borderRadius: 40, backgroundColor: c.brandSecondary, alignItems: "center", justifyContent: "center" },
  permTitle: { fontSize: 28, fontWeight: "900", color: c.onSurface },
  permText: { fontSize: 16, color: c.onSurfaceTertiary, fontWeight: "500", textAlign: "left", lineHeight: 22 },
  small: { fontSize: 13, color: c.muted, textAlign: "center" },
  resultIcon: { width: 112, height: 112, borderRadius: 56, alignItems: "center", justifyContent: "center" },
  resultTitle: { fontSize: 26, fontWeight: "900", color: c.onSurface, textAlign: "center" },
  xpPill: { flexDirection: "row", alignItems: "center", gap: spacing.xs, backgroundColor: c.brandSecondary, paddingHorizontal: spacing.lg, paddingVertical: spacing.sm, borderRadius: radius.pill },
  xpText: { fontSize: 18, fontWeight: "900", color: c.onBrandSecondary },
  camRoot: { flex: 1, backgroundColor: c.surfaceInverse },
  fill: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
  overlay: { flex: 1, paddingHorizontal: spacing.lg, justifyContent: "space-between" },
  camTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  roundBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: c.scrim, alignItems: "center", justifyContent: "center" },
  livePill: { flexDirection: "row", alignItems: "center", gap: spacing.xs, backgroundColor: c.scrim, paddingHorizontal: spacing.md, height: 32, borderRadius: radius.pill },
  liveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: c.error },
  liveText: { color: c.onSurfaceInverse, fontWeight: "900", fontSize: 12, letterSpacing: 1 },
  guide: { alignItems: "center", gap: spacing.md },
  guideBox: { width: "80%", aspectRatio: 1, borderWidth: 3, borderColor: c.brandSecondary, borderRadius: radius.lg, borderStyle: "dashed" },
  guideText: { color: c.onSurfaceInverse, fontWeight: "700", textAlign: "center", backgroundColor: c.scrim, padding: spacing.sm, borderRadius: radius.md, overflow: "hidden" },
  camError: { color: c.onError, backgroundColor: c.error, padding: spacing.sm, borderRadius: radius.md, textAlign: "center", fontWeight: "700", overflow: "hidden" },
  shutterRow: { alignItems: "center" },
  shutter: { width: 80, height: 80, borderRadius: 40, borderWidth: 5, borderColor: c.onSurfaceInverse, alignItems: "center", justifyContent: "center" },
  shutterInner: { width: 62, height: 62, borderRadius: 31, backgroundColor: c.brandPrimary },
  verifying: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: c.scrim, alignItems: "center", justifyContent: "center", gap: spacing.lg },
  verifyingText: { color: c.onSurfaceInverse, fontWeight: "800", fontSize: 18 },
}));
