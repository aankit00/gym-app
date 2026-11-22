import React, { useEffect, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { useSignIn, useSignUp } from "@clerk/expo";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { BigTitle, PrimaryButton } from "@/src/components/ui";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

const RESEND_SECONDS = 30;

export default function SignInScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { signIn, errors: signInErrors, fetchStatus } = useSignIn();
  const { signUp, errors: signUpErrors } = useSignUp();
  const [countryCode, setCountryCode] = useState("+91");
  const [localNumber, setLocalNumber] = useState("");
  const [code, setCode] = useState("");
  const [mode, setMode] = useState<"enter-phone" | "sign-in-code" | "sign-up-code">("enter-phone");
  const [message, setMessage] = useState("");
  const [resendIn, setResendIn] = useState(0);
  const busy = fetchStatus === "fetching";
  const phoneNumber = `${countryCode.startsWith("+") ? countryCode : "+" + countryCode}${localNumber.replace(/\D/g, "")}`;
  const goHome = () => router.replace("/start");

  useEffect(() => {
    if (resendIn <= 0) return;
    const t = setTimeout(() => setResendIn((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [resendIn]);

  const sendCode = async () => {
    setMessage("");
    const { error } = await signIn.create({ identifier: phoneNumber });
    if (!error) {
      await signIn.phoneCode.sendCode({ phoneNumber });
      setResendIn(RESEND_SECONDS);
      return setMode("sign-in-code");
    }
    if (error.errors?.[0]?.code === "form_identifier_not_found") {
      const up = await signUp.create({ phoneNumber });
      if (up.error) return setMessage(up.error.errors?.[0]?.longMessage ?? "Could not start sign-up.");
      await signUp.verifications.sendPhoneCode();
      setResendIn(RESEND_SECONDS);
      return setMode("sign-up-code");
    }
    setMessage(error.errors?.[0]?.longMessage ?? "Could not send a code to that number.");
  };

  const resendCode = async () => {
    if (resendIn > 0 || busy) return;
    setMessage("");
    const { error } =
      mode === "sign-in-code" ? await signIn.phoneCode.sendCode({ phoneNumber }) : await signUp.verifications.sendPhoneCode();
    if (error) return setMessage(error.errors?.[0]?.longMessage ?? "Could not send a new code yet. Try again shortly.");
    setResendIn(RESEND_SECONDS);
  };

  const verifyCode = async () => {
    setMessage("");
    if (mode === "sign-in-code") {
      const { error } = await signIn.phoneCode.verifyCode({ code });
      if (error) return setMessage(error.errors?.[0]?.longMessage ?? "That code is not right. Try again.");
      if (signIn.status === "complete") await signIn.finalize({ navigate: goHome });
      return;
    }
    const { error } = await signUp.verifications.verifyPhoneCode({ code });
    if (error) return setMessage(error.errors?.[0]?.longMessage ?? "That code is not right. Try again.");
    if (signUp.status === "complete") await signUp.finalize({ navigate: goHome });
  };

  const startOver = async () => {
    await signIn.reset();
    setCode("");
    setResendIn(0);
    setMode("enter-phone");
  };

  const err = mode === "enter-phone"
    ? signInErrors?.fields?.identifier?.message ?? message
    : signInErrors?.fields?.code?.message ?? signUpErrors?.fields?.code?.message ?? message;

  return (
    <View style={styles.root}>
      <KeyboardAwareScrollView bottomOffset={24} keyboardShouldPersistTaps="handled"
        contentContainerStyle={[styles.scroll, { paddingTop: insets.top + spacing.lg, paddingBottom: insets.bottom + spacing.xl }]}>
        <Pressable testID="sign-in-back-button" onPress={() => (mode === "enter-phone" ? router.back() : startOver())} style={styles.back} hitSlop={8}>
          <Ionicons name="arrow-back" size={24} color={colors.onSurface} />
        </Pressable>
        <BigTitle text={mode === "enter-phone" ? "Sign in" : "Verify"} testID="sign-in-title" />
        <Text style={styles.sub}>
          {mode === "enter-phone" ? "Enter your phone number. We'll text you a 6-digit code." : `Enter the code we sent to ${phoneNumber}`}
        </Text>

        {mode === "enter-phone" ? (
          <View style={styles.phoneRow}>
            <TextInput testID="country-code-input" value={countryCode} onChangeText={setCountryCode} keyboardType="phone-pad"
              style={[styles.input, styles.cc]} maxLength={5} />
            <TextInput testID="phone-input" value={localNumber} onChangeText={setLocalNumber} placeholder="98765 43210"
              placeholderTextColor={colors.muted} keyboardType="phone-pad" autoComplete="tel" textContentType="telephoneNumber"
              style={[styles.input, { flex: 1, minWidth: 0 }]} autoFocus />
          </View>
        ) : (
          <TextInput testID="code-input" value={code} onChangeText={setCode} placeholder="123456" placeholderTextColor={colors.muted}
            keyboardType="number-pad" autoComplete="sms-otp" textContentType="oneTimeCode" maxLength={6}
            style={[styles.input, styles.codeInput]} autoFocus />
        )}

        {!!err && <Text testID={mode === "enter-phone" ? "sign-in-error" : "code-error"} style={styles.error}>{err}</Text>}

        <View style={{ height: spacing.xl }} />
        {mode === "enter-phone" ? (
          <PrimaryButton testID="send-code-button" label={busy ? "Sending…" : "Send code"} disabled={localNumber.length < 6 || busy} onPress={sendCode} />
        ) : (
          <>
            <PrimaryButton testID="verify-code-button" label={busy ? "Checking…" : "Verify"} disabled={code.length < 6 || busy} onPress={verifyCode} />
            <Pressable testID="resend-code-button" disabled={busy || resendIn > 0} onPress={resendCode} style={[styles.link, { opacity: busy || resendIn > 0 ? 0.5 : 1 }]}>
              <Text style={styles.linkText}>{resendIn > 0 ? `Send a new code in ${resendIn}s` : "Send a new code"}</Text>
            </Pressable>
            <Pressable testID="start-over-button" onPress={startOver} style={styles.link}>
              <Text style={styles.linkText}>Use another number</Text>
            </Pressable>
          </>
        )}
      </KeyboardAwareScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  scroll: { paddingHorizontal: spacing.xl, flexGrow: 1 },
  back: { width: 44, height: 44, justifyContent: "center", marginBottom: spacing.lg },
  sub: { color: c.muted, fontSize: 16, fontWeight: "500", marginTop: spacing.sm, marginBottom: spacing.xl },
  phoneRow: { flexDirection: "row", gap: spacing.sm },
  input: { backgroundColor: c.surfaceSecondary, borderRadius: radius.md, height: 56, paddingHorizontal: spacing.lg, fontSize: 18, fontWeight: "700", color: c.onSurface, borderWidth: 1, borderColor: c.border },
  cc: { width: 80, textAlign: "center" },
  codeInput: { letterSpacing: 10, textAlign: "center", fontSize: 24 },
  error: { color: c.error, marginTop: spacing.md, fontWeight: "600" },
  link: { height: 44, alignItems: "center", justifyContent: "center", marginTop: spacing.sm },
  linkText: { color: c.onSurface, fontWeight: "700" },
}));
