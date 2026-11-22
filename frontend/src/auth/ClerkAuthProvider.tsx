import React, { useEffect, useState } from "react";
import { Text, View } from "react-native";
import { ClerkProvider } from "@clerk/expo";
import { tokenCache } from "@clerk/expo/token-cache";

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

type ClerkConfig = { enabled: boolean; publishable_key: string; proxy_url: string };

// Must wrap the whole app (root layout): Clerk hooks crash if they ever render outside <ClerkProvider>.
export default function ClerkAuthProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<ClerkConfig | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async (attempt = 0) => {
      try {
        const cfg: ClerkConfig = await (await fetch(`${BACKEND_URL}/api/clerk/config`)).json();
        if (cfg.enabled) return cancelled || setConfig(cfg);
      } catch {}
      if (cancelled) return;
      if (attempt >= 20) return setUnavailable(true);
      setTimeout(() => load(attempt + 1), 1500);
    };
    load();
    return () => { cancelled = true; };
  }, []);

  if (unavailable) return <View style={{ padding: 24 }}><Text>Sign-in is unavailable right now. Close and reopen the app to try again.</Text></View>;
  if (!config) return null;
  return (
    <ClerkProvider
      publishableKey={config.publishable_key}
      proxyUrl={config.proxy_url ? `${BACKEND_URL}${config.proxy_url}` : undefined}
      tokenCache={tokenCache}
    >
      {children}
    </ClerkProvider>
  );
}
