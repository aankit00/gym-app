// Web: Razorpay Standard Checkout (checkout.js) opened over the page.
import { useEffect } from "react";
import { useTheme } from "@/src/theme";
import type { CheckoutProps } from "./types";

function loadScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if ((window as any).Razorpay) return resolve(true);
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });
}

export default function RazorpayCheckout({ order, onSuccess, onDismiss, onError }: CheckoutProps) {
  const { colors } = useTheme();
  useEffect(() => {
    if (!order) return;
    let cancelled = false;
    loadScript().then((ok) => {
      if (cancelled) return;
      if (!ok) return onError("Checkout couldn't load. Check your connection and try again.");
      const checkout = new (window as any).Razorpay({
        key: order.key_id, amount: order.amount, currency: order.currency, name: order.name,
        description: order.description, order_id: order.order_id, theme: { color: colors.brandPrimary },
        handler: onSuccess,
        modal: { ondismiss: onDismiss },
      });
      checkout.open();
    });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [order?.order_id]);
  return null;
}
