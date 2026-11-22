import { QueryClientProvider } from "@tanstack/react-query";
import { Redirect, Stack, usePathname } from "expo-router";
import { LogBox, StyleSheet } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { KeyboardProvider } from "react-native-keyboard-controller";
import { useAuth } from "@clerk/expo";

import { ErrorBoundary } from "@/src/components/error-boundary";
import { queryClient } from "@/src/query-client";
import ClerkAuthProvider from "@/src/auth/ClerkAuthProvider";

LogBox.ignoreAllLogs(true);

const PUBLIC_PATHS = ["/", "/sign-in"];

function AuthGate() {
  const { isLoaded, isSignedIn } = useAuth();
  const pathname = usePathname();
  if (!isLoaded) return null;
  if (!isSignedIn && !PUBLIC_PATHS.includes(pathname)) return <Redirect href="/" />;
  if (isSignedIn && PUBLIC_PATHS.includes(pathname)) return <Redirect href="/start" />;
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="prove" options={{ presentation: "fullScreenModal", animation: "slide_from_bottom" }} />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <ClerkAuthProvider>
      <GestureHandlerRootView style={styles.root}>
        <ErrorBoundary>
          <QueryClientProvider client={queryClient}>
            <KeyboardProvider>
              <AuthGate />
            </KeyboardProvider>
          </QueryClientProvider>
        </ErrorBoundary>
      </GestureHandlerRootView>
    </ClerkAuthProvider>
  );
}

const styles = StyleSheet.create({ root: { flex: 1 } });
