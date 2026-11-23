import React, { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useAppSession } from "@/src/auth/AppSession";
import { BigTitle, PrimaryButton, Segmented } from "@/src/components/ui";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function EmailSignIn() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { setToken } = useAppSession();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const validEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const canSubmit = validEmail && password.length >= 8 && !busy;

  const submit = async () => {
    setError("");
    setBusy(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/${mode === "login" ? "login" : "register"}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const d = data.detail;
        throw new Error(typeof d === "string" ? d : Array.isArray(d) ? "Check your email address and password." : "Something went wrong. Try again.");
      }
      await setToken(data.token); // the root gate takes it from here
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.root}>
      <KeyboardAwareScrollView bottomOffset={24} keyboardShouldPersistTaps="handled"
        contentContainerStyle={[styles.scroll, { paddingTop: insets.top + spacing.lg, paddingBottom: insets.bottom + spacing.xl }]}>
        <Pressable testID="email-back-button" onPress={() => router.back()} style={styles.back} hitSlop={8}>
          <Ionicons name="arrow-back" size={24} color={colors.onSurface} />
        </Pressable>
        <BigTitle text={mode === "login" ? "Sign in" : "Create account"} testID="email-title" />
        <Text style={styles.sub}>Your email account is separate from phone and Google sign-in.</Text>
        <Segmented testIDPrefix="email-mode" value={mode} onChange={(m) => { setMode(m); setError(""); }}
          options={[{ key: "login", label: "Sign in" }, { key: "register", label: "New account" }]} />
        <Text style={styles.label}>Email</Text>
        <TextInput testID="email-input" value={email} onChangeText={setEmail} placeholder="you@example.com" placeholderTextColor={colors.muted}
          keyboardType="email-address" autoCapitalize="none" autoComplete="email" textContentType="emailAddress" autoCorrect={false} style={styles.input} />
        <Text style={styles.label}>Password</Text>
        <View style={styles.pwRow}>
          <TextInput testID="password-input" value={password} onChangeText={setPassword} placeholder="At least 8 characters" placeholderTextColor={colors.muted}
            secureTextEntry={!show} autoCapitalize="none" autoComplete={mode === "login" ? "password" : "new-password"}
            textContentType={mode === "login" ? "password" : "newPassword"} style={[styles.input, styles.pwInput]} onSubmitEditing={() => canSubmit && submit()} />
          <Pressable testID="password-toggle" onPress={() => setShow((v) => !v)} style={styles.eye} hitSlop={6}>
            <Ionicons name={show ? "eye-off" : "eye"} size={22} color={colors.muted} />
          </Pressable>
        </View>
        {!!error && <Text testID="email-error" style={styles.error}>{error}</Text>}
        <View style={{ height: spacing.xl }} />
        <PrimaryButton testID="email-submit-button" label={mode === "login" ? "Sign in" : "Create account"} loading={busy} disabled={!canSubmit} onPress={submit} />
      </KeyboardAwareScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  scroll: { paddingHorizontal: spacing.xl, flexGrow: 1 },
  back: { width: 44, height: 44, justifyContent: "center", marginBottom: spacing.lg },
  sub: { color: c.muted, fontSize: 15, fontWeight: "500", marginTop: spacing.sm, marginBottom: spacing.lg },
  label: { color: c.onSurface, fontWeight: "800", marginTop: spacing.lg, marginBottom: spacing.sm },
  input: { backgroundColor: c.surfaceSecondary, borderRadius: radius.md, height: 56, paddingHorizontal: spacing.lg, fontSize: 17, fontWeight: "600", color: c.onSurface, borderWidth: 1, borderColor: c.border },
  pwRow: { flexDirection: "row", alignItems: "center" },
  pwInput: { flex: 1, paddingRight: 56 },
  eye: { position: "absolute", right: spacing.md, width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  error: { color: c.error, marginTop: spacing.md, fontWeight: "600" },
}));
