import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";
import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import { storage } from "@/src/utils/storage";

WebBrowser.maybeCompleteAuthSession();

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const TOKEN_KEY = "app_auth_token";
const AUTH_URL = "https://auth.emergentagent.com/?redirect=";

type AppSession = {
  ready: boolean;
  token: string | null;
  setToken: (t: string | null) => Promise<void>;
  googleSignIn: () => Promise<void>;
  googleBusy: boolean;
  googleError: string;
};

const Ctx = createContext<AppSession | null>(null);

const sessionIdIn = (url: string | null) => url?.match(/[?#&]session_id=([^&#]+)/)?.[1] ?? null;

// Email and Google sign-ins (separate accounts from Clerk phone sign-in). Holds our own token, not Clerk's.
export function AppSessionProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [token, setTokenState] = useState<string | null>(null);
  const [googleBusy, setGoogleBusy] = useState(false);
  const [googleError, setGoogleError] = useState("");
  const sent = useRef(new Set<string>());

  const setToken = useCallback(async (t: string | null) => {
    if (t) await storage.secureSet(TOKEN_KEY, t);
    else await storage.secureRemove(TOKEN_KEY);
    setTokenState(t);
  }, []);

  // One-time Google session_id -> our session token. Guarded: several sources can deliver the same id.
  const exchange = useCallback(async (sessionId: string) => {
    if (sent.current.has(sessionId)) return false;
    sent.current.add(sessionId);
    setGoogleBusy(true);
    setGoogleError("");
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/session`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Google sign-in failed. Try again.");
      await setToken(data.token);
      return true;
    } catch (e: any) {
      setGoogleError(e.message);
      return false;
    } finally {
      setGoogleBusy(false);
    }
  }, [setToken]);

  useEffect(() => {
    (async () => {
      if (Platform.OS === "web") {
        const id = sessionIdIn(window.location.href);
        if (id && (await exchange(id))) {
          const url = new URL(window.location.href);
          url.searchParams.delete("session_id");
          url.hash = url.hash.replace(/session_id=[^&]+&?/, "").replace(/^#$/, "");
          window.history.replaceState(window.history.state, "", url.toString());
          return setReady(true);
        }
      } else {
        const id = sessionIdIn(await Linking.getInitialURL());
        if (id && (await exchange(id))) return setReady(true);
      }
      setTokenState(await storage.secureGet<string | null>(TOKEN_KEY, null));
      setReady(true);
    })();
  }, [exchange]);

  useEffect(() => {
    if (Platform.OS === "web") return;
    const sub = Linking.addEventListener("url", ({ url }) => { const id = sessionIdIn(url); if (id) exchange(id); });
    return () => sub.remove();
  }, [exchange]);

  const googleSignIn = useCallback(async () => {
    setGoogleError("");
    if (Platform.OS === "web") {
      window.location.href = AUTH_URL + encodeURIComponent(window.location.origin + "/");
      return;
    }
    const redirect = Linking.createURL("");
    let linked: string | null = null;
    const sub = Linking.addEventListener("url", ({ url }) => { linked = url; });
    try {
      const result = await WebBrowser.openAuthSessionAsync(AUTH_URL + encodeURIComponent(redirect), redirect);
      const id = sessionIdIn(result.type === "success" ? result.url : null) ?? sessionIdIn(linked) ?? sessionIdIn(await Linking.getInitialURL());
      if (id) await exchange(id);
    } finally {
      sub.remove();
    }
  }, [exchange]);

  return <Ctx.Provider value={{ ready, token, setToken, googleSignIn, googleBusy, googleError }}>{children}</Ctx.Provider>;
}

export function useAppSession() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAppSession must be used inside AppSessionProvider");
  return v;
}
