import { useState } from "react";
import * as Haptics from "expo-haptics";
import { useApi } from "@/src/api";
import type { CheckoutProps, RazorpayOrder, RazorpayResult } from "./types";

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

// One Razorpay purchase: create the order at `orderPath`, open checkout, confirm with the server.
// `onSettled` runs after every attempt so the screen can reload what the user now owns.
export function usePurchase(orderPath: string, onSettled: (fulfilled: boolean) => Promise<void> | void) {
  const { call } = useApi();
  const [order, setOrder] = useState<RazorpayOrder | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const buy = async () => {
    setError("");
    setNotice("");
    setBusy(true);
    try {
      setOrder(await call<RazorpayOrder>(orderPath, { method: "POST" }));
    } catch (e: any) {
      setError(e.message);
      setBusy(false);
    }
  };

  const onSuccess = async (result: RazorpayResult) => {
    setOrder(null);
    let fulfilled = false;
    try {
      let state = "pending";
      for (let i = 0; i < 4 && state === "pending"; i++) {
        if (i > 0) await wait(2500);
        state = (await call<{ status: string }>("/payments/verify", { method: "POST", body: result })).status;
      }
      fulfilled = state === "fulfilled";
      if (fulfilled) Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      else setNotice("Payment received. It can take a moment to show up here, so check back shortly.");
    } catch (e: any) {
      setError(`${e.message} If you were charged, your purchase will appear here automatically.`);
    } finally {
      await onSettled(fulfilled);
      setBusy(false);
    }
  };

  const onDismiss = () => { setOrder(null); setBusy(false); };
  const checkout: CheckoutProps = { order, onSuccess, onDismiss, onError: (m) => { onDismiss(); setError(m); } };
  return { buy, busy, error, notice, checkout };
}
