import React, { useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAvoidingView } from "react-native-keyboard-controller";
import Animated, { FadeInRight } from "react-native-reanimated";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { tzOffsetMin, useApi } from "@/src/api";
import { PrimaryButton } from "@/src/components/ui";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

type Opt = { key: string; label: string; desc?: string; icon?: string };
const GENDERS: Opt[] = [{ key: "male", label: "Male", icon: "male" }, { key: "female", label: "Female", icon: "female" }, { key: "other", label: "Other", icon: "person" }];
const GOALS: Opt[] = [
  { key: "lean_muscle", label: "Lean muscle", desc: "Build muscle, stay lean", icon: "barbell" },
  { key: "fat_loss", label: "Fat loss", desc: "Burn fat, get lighter", icon: "flame" },
  { key: "strength", label: "Strength", desc: "Lift heavier over time", icon: "fitness" },
  { key: "stay_fit", label: "Stay consistent", desc: "Just keep showing up", icon: "heart" },
];
const TARGETS: Opt[] = [2, 3, 4, 5].map((n) => ({ key: String(n), label: `${n} days / week`, desc: n === 4 ? "Recommended" : undefined }));

const STEPS = ["name", "age", "height", "gender", "goal", "target", "city"] as const;
const TITLES: Record<string, [string, string]> = {
  name: ["What's your name?", "This shows on your city leaderboard."],
  age: ["How old are you?", "Helps us tailor your journey."],
  height: ["How tall are you?", "In centimetres."],
  gender: ["Your gender", "Pick what fits you."],
  goal: ["What's your goal?", "You can change this later."],
  target: ["Weekly target", "Hit this many verified gym days to keep your streak."],
  city: ["Your city or town", "Compete with people near you."],
};

export default function Onboarding() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { call } = useApi();
  const [step, setStep] = useState(0);
  const [v, setV] = useState({ name: "", age: "", height: "", gender: "", goal: "", target: "4", city: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const key = STEPS[step];

  const valid = (() => {
    switch (key) {
      case "name": return v.name.trim().length >= 1;
      case "age": return +v.age >= 13 && +v.age <= 100;
      case "height": return +v.height >= 100 && +v.height <= 250;
      case "city": return v.city.trim().length >= 1;
      default: return !!v[key];
    }
  })();

  const next = async () => {
    setError("");
    if (step < STEPS.length - 1) return setStep(step + 1);
    setSaving(true);
    try {
      await call("/me", { method: "POST", body: {
        name: v.name.trim(), age: +v.age, height_cm: +v.height, gender: v.gender, goal: v.goal,
        weekly_target: +v.target, city: v.city.trim(), tz_offset_min: tzOffsetMin(),
      } });
      router.replace("/home");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const input = (field: "name" | "age" | "height" | "city", props: any) => (
    <TextInput testID={`onboarding-${field}-input`} value={v[field]} onChangeText={(t) => setV({ ...v, [field]: t })}
      placeholderTextColor={colors.muted} style={styles.input} autoFocus returnKeyType="next"
      onSubmitEditing={() => valid && next()} {...props} />
  );

  const options = (field: "gender" | "goal" | "target", opts: Opt[]) => (
    <View style={{ gap: spacing.md }}>
      {opts.map((o) => {
        const sel = v[field] === o.key;
        return (
          <Pressable key={o.key} testID={`onboarding-${field}-${o.key}`} onPress={() => setV({ ...v, [field]: o.key })}
            style={[styles.opt, sel && styles.optSel]}>
            {o.icon && <View style={[styles.optIcon, sel && { backgroundColor: colors.brandSecondary }]}><Ionicons name={o.icon as any} size={20} color={colors.onSurface} /></View>}
            <View style={{ flex: 1 }}>
              <Text style={styles.optLabel}>{o.label}</Text>
              {o.desc && <Text style={styles.optDesc}>{o.desc}</Text>}
            </View>
            <Ionicons name={sel ? "checkmark-circle" : "ellipse-outline"} size={24} color={sel ? colors.brandPrimary : colors.borderStrong} />
          </Pressable>
        );
      })}
    </View>
  );

  return (
    <KeyboardAvoidingView behavior="padding" style={styles.root}>
      <View style={[styles.header, { paddingTop: insets.top + spacing.md }]}>
        <Pressable testID="onboarding-back-button" disabled={step === 0} onPress={() => setStep(step - 1)} style={[styles.back, step === 0 && { opacity: 0 }]}>
          <Ionicons name="arrow-back" size={24} color={colors.onSurface} />
        </Pressable>
        <View style={styles.progress}>
          <View style={[styles.progressFill, { width: `${((step + 1) / STEPS.length) * 100}%` }]} />
        </View>
        <Text testID="onboarding-step-label" style={styles.stepLabel}>{step + 1}/{STEPS.length}</Text>
      </View>
      <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
        <Animated.View key={key} entering={FadeInRight.duration(300)}>
          <Text testID="onboarding-title" style={styles.title}>{TITLES[key][0]}</Text>
          <Text style={styles.sub}>{TITLES[key][1]}</Text>
          {key === "name" && input("name", { placeholder: "Your name", autoCapitalize: "words", maxLength: 40 })}
          {key === "age" && input("age", { placeholder: "25", keyboardType: "number-pad", maxLength: 3 })}
          {key === "height" && input("height", { placeholder: "175", keyboardType: "number-pad", maxLength: 3 })}
          {key === "city" && input("city", { placeholder: "e.g. Mumbai", autoCapitalize: "words", maxLength: 60 })}
          {key === "gender" && options("gender", GENDERS)}
          {key === "goal" && options("goal", GOALS)}
          {key === "target" && options("target", TARGETS)}
          {!!error && <Text testID="onboarding-error" style={styles.error}>{error}</Text>}
        </Animated.View>
      </ScrollView>
      <View style={[styles.footer, { paddingBottom: insets.bottom + spacing.lg }]}>
        <PrimaryButton testID="onboarding-next-button" label={step === STEPS.length - 1 ? "Enter GymProof" : "Continue"}
          disabled={!valid} loading={saving} onPress={next} />
      </View>
    </KeyboardAvoidingView>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.lg, gap: spacing.md },
  back: { width: 44, height: 44, justifyContent: "center" },
  progress: { flex: 1, height: 8, borderRadius: 4, backgroundColor: c.surfaceTertiary, overflow: "hidden" },
  progressFill: { height: 8, backgroundColor: c.brandPrimary, borderRadius: 4 },
  stepLabel: { fontWeight: "800", color: c.muted, width: 32, textAlign: "right" },
  body: { padding: spacing.xl },
  title: { fontSize: 30, fontWeight: "900", color: c.onSurface },
  sub: { fontSize: 15, color: c.muted, fontWeight: "500", marginTop: spacing.sm, marginBottom: spacing.xl },
  input: { backgroundColor: c.surfaceSecondary, borderRadius: radius.md, height: 64, paddingHorizontal: spacing.lg, fontSize: 22, fontWeight: "800", color: c.onSurface, borderWidth: 1, borderColor: c.border },
  opt: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, minHeight: 64, borderWidth: 2, borderColor: c.surfaceSecondary },
  optSel: { borderColor: c.brandPrimary },
  optIcon: { width: 40, height: 40, borderRadius: 20, backgroundColor: c.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  optLabel: { fontSize: 17, fontWeight: "800", color: c.onSurface },
  optDesc: { fontSize: 13, color: c.muted, fontWeight: "600", marginTop: 2 },
  error: { color: c.error, fontWeight: "600", marginTop: spacing.md },
  footer: { paddingHorizontal: spacing.xl, paddingTop: spacing.md },
}));
