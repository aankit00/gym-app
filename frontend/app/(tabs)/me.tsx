import React, { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
import { useUser } from "@clerk/expo";
import { useSession } from "@/src/auth/useSession";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useApi } from "@/src/api";
import { BigTitle, Card, PrimaryButton, SectionTitle } from "@/src/components/ui";
import { usesNativeTabs } from "@/src/navigation";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

type Profile = { name: string; age: number; height_cm: number; gender: string; goal: string; weekly_target: number; city: string; xp: number };
type Proof = { id: string; status: string; reason: string; local_date: string; counted: boolean; xp_awarded: number; created_at: string };

const GOAL_LABEL: Record<string, string> = { lean_muscle: "Lean muscle", fat_loss: "Fat loss", strength: "Strength", stay_fit: "Stay consistent" };

export default function Me() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { call } = useApi();
  const { signOut } = useSession();
  const [account, setAccount] = useState<{ email: string; provider: string } | null>(null);
  const { user } = useUser();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [proofs, setProofs] = useState<Proof[]>([]);
  const [saving, setSaving] = useState<number | null>(null);
  const [error, setError] = useState("");
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;

  const load = useCallback(async () => {
    try {
      setError("");
      const [me, p] = await Promise.all([call<{ profile: Profile; account: { email: string; provider: string } | null }>("/me"), call<Proof[]>("/proofs?limit=10")]);
      setProfile(me.profile);
      setAccount(me.account);
      setProofs(p);
    } catch (e: any) {
      setError(e.message);
    }
  }, [call]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const setTarget = async (n: number) => {
    setSaving(n);
    try {
      const r = await call<{ profile: Profile }>("/me", { method: "PATCH", body: { weekly_target: n } });
      setProfile(r.profile);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(null);
    }
  };

  return (
    <View style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.sm }]}>
        <BigTitle text="Me" testID="me-title" />
      </View>
      {!profile ? (
        <View style={styles.center}>
          {error ? <><Text style={styles.err}>{error}</Text><PrimaryButton testID="me-retry-button" label="Retry" onPress={load} /></>
            : <ActivityIndicator color={colors.brandPrimary} size="large" />}
        </View>
      ) : (
        <ScrollView contentContainerStyle={[styles.scroll, { paddingBottom: bottomChrome + spacing.xl }]}>
          <Card style={styles.profileCard} testID="profile-card">
            <View style={styles.avatar}><Text style={styles.avatarText}>{profile.name.slice(0, 1).toUpperCase()}</Text></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.name} testID="profile-name">{profile.name}</Text>
              <Text style={styles.meta}>{profile.city} · {account?.email ?? user?.primaryPhoneNumber?.phoneNumber ?? ""}</Text>
              <Text style={styles.meta}>{profile.age} yrs · {profile.height_cm} cm · {GOAL_LABEL[profile.goal]}</Text>
            </View>
            <View style={styles.xp}><Text style={styles.xpText} testID="profile-xp">{profile.xp}</Text><Text style={styles.xpLabel}>XP</Text></View>
          </Card>

          <SectionTitle text="Weekly Target" />
          <Text style={styles.hint}>Verified gym days needed each week to keep your streak.</Text>
          <View style={styles.targets}>
            {[2, 3, 4, 5].map((n) => (
              <Pressable key={n} testID={`target-option-${n}`} onPress={() => setTarget(n)}
                style={[styles.target, profile.weekly_target === n && styles.targetOn]}>
                {saving === n ? <ActivityIndicator color={colors.onSurface} /> : (
                  <>
                    <Text style={[styles.targetVal, profile.weekly_target === n && { color: colors.onSurfaceInverse }]}>{n}</Text>
                    <Text style={[styles.targetLabel, profile.weekly_target === n && { color: colors.onSurfaceInverse }]}>days</Text>
                  </>
                )}
              </Pressable>
            ))}
          </View>

          <SectionTitle text="Recent Proofs" />
          {proofs.length === 0 ? (
            <Card><Text style={styles.hint} testID="proofs-empty">No proofs yet. Hit the gym and snap your first one!</Text></Card>
          ) : (
            <View style={{ gap: spacing.sm }}>
              {proofs.map((p) => {
                const ok = p.status === "accepted";
                const tint = ok ? colors.success : p.status === "suspicious" ? colors.brandPrimary : colors.error;
                return (
                  <Card key={p.id} style={styles.proofRow} testID={`proof-row-${p.id}`}>
                    <Ionicons name={ok ? "checkmark-circle" : p.status === "suspicious" ? "alert-circle" : "close-circle"} size={28} color={tint} />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.proofTitle}>{p.local_date} · {p.status.toUpperCase()}</Text>
                      <Text style={styles.meta} numberOfLines={2}>{p.reason}</Text>
                    </View>
                    {p.xp_awarded > 0 && <Text style={styles.proofXp}>+{p.xp_awarded}</Text>}
                  </Card>
                );
              })}
            </View>
          )}

          <View style={{ height: spacing.xl }} />
          <PrimaryButton testID="sign-out-button" label="Sign out" variant="light" onPress={() => signOut()} />
          {!!error && <Text style={styles.err}>{error}</Text>}
        </ScrollView>
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  header: { paddingHorizontal: spacing.xl, paddingBottom: spacing.sm, backgroundColor: c.surface },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.lg, padding: spacing.xl },
  err: { color: c.error, fontWeight: "600", textAlign: "center", marginTop: spacing.md },
  scroll: { paddingHorizontal: spacing.xl, paddingTop: spacing.sm },
  profileCard: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  avatar: { width: 60, height: 60, borderRadius: 30, backgroundColor: c.brandSecondary, alignItems: "center", justifyContent: "center" },
  avatarText: { fontSize: 24, fontWeight: "900", color: c.onBrandSecondary },
  name: { fontSize: 20, fontWeight: "900", color: c.onSurface },
  meta: { fontSize: 13, fontWeight: "600", color: c.muted, marginTop: 2 },
  xp: { alignItems: "center" },
  xpText: { fontSize: 22, fontWeight: "900", color: c.brandPrimary },
  xpLabel: { fontSize: 12, fontWeight: "800", color: c.muted },
  hint: { fontSize: 14, color: c.muted, fontWeight: "600", marginBottom: spacing.md },
  targets: { flexDirection: "row", gap: spacing.sm },
  target: { flex: 1, height: 72, borderRadius: radius.lg, backgroundColor: c.surfaceSecondary, alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: c.surfaceSecondary },
  targetOn: { backgroundColor: c.surfaceInverse, borderColor: c.surfaceInverse },
  targetVal: { fontSize: 24, fontWeight: "900", color: c.onSurface },
  targetLabel: { fontSize: 12, fontWeight: "700", color: c.muted },
  proofRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.md },
  proofTitle: { fontSize: 14, fontWeight: "800", color: c.onSurface },
  proofXp: { fontWeight: "900", color: c.brandPrimary },
}));
