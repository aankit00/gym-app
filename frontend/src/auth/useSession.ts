import { useCallback } from "react";
import { useAuth } from "@clerk/expo";
import { useAppSession } from "./AppSession";

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

// One view of "who is signed in" across phone (Clerk), email and Google accounts.
export function useSession() {
  // useAuth() returns a new object every render; depend on its (stable) functions only, otherwise
  // getToken/call change identity each render and every screen's load effect refetches in a loop.
  const clerk = useAuth();
  const { getToken: clerkGetToken, signOut: clerkSignOut } = clerk;
  const app = useAppSession();
  const { token, setToken } = app;
  const usingApp = !!token;

  const getToken = useCallback(async () => (token ? token : await clerkGetToken()), [token, clerkGetToken]);

  const signOut = useCallback(async () => {
    if (token) {
      await fetch(`${BACKEND_URL}/api/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
      await setToken(null);
    } else {
      await clerkSignOut();
    }
  }, [token, setToken, clerkSignOut]);

  return {
    isLoaded: clerk.isLoaded && app.ready,
    isSignedIn: usingApp || !!clerk.isSignedIn,
    provider: usingApp ? "app" : "phone",
    getToken,
    signOut,
    // a rejected email/Google token (expired, account gone) signs out locally so the gate shows sign-in again
    onUnauthorized: useCallback(() => { if (token) setToken(null); }, [token, setToken]),
  };
}
