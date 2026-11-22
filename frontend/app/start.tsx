import React, { useEffect, useState } from "react";
import { ActivityIndicator, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useApi } from "@/src/api";
import { PrimaryButton } from "@/src/components/ui";
import { makeStyles, spacing, useTheme } from "@/src/theme";

export default function Start() {
  const styles = useStyles();
  const { colors } = useTheme();
  const { call } = useApi();
  const router = useRouter();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    call<{ onboarded: boolean }>("/me")
      .then((r) => router.replace(r.onboarded ? "/home" : "/onboarding"))
      .catch((e) => setError(e.message));
  }, [attempt, call, router]);

  return (
    <View style={styles.root} testID="start-screen">
      {error ? (
        <>
          <Text style={styles.err}>{error}</Text>
          <PrimaryButton testID="start-retry-button" label="Retry" onPress={() => { setError(""); setAttempt((a) => a + 1); }} />
        </>
      ) : <ActivityIndicator color={colors.brandPrimary} size="large" />}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.lg },
  err: { color: c.error, fontWeight: "600", textAlign: "center" },
}));
