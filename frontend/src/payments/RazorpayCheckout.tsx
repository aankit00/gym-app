// Native: Razorpay Standard Checkout inside a WebView, so it runs in Expo Go and in store builds alike.
import React, { useMemo } from "react";
import { ActivityIndicator, Linking, Modal, Pressable, Text, View } from "react-native";
import { WebView } from "react-native-webview";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { BACKEND_URL } from "@/src/api";
import { makeStyles, spacing, useTheme } from "@/src/theme";
import type { CheckoutProps } from "./types";

const IN_PAGE = /^(https?:|about:|data:|blob:)/i;

function page(options: object) {
  const json = JSON.stringify(options).replace(/</g, "\\u003c");
  return `<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"></head><body>
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<script>
  var post = function (m) { window.ReactNativeWebView.postMessage(JSON.stringify(m)); };
  try {
    var o = ${json};
    o.handler = function (r) { post({ type: "success", result: r }); };
    o.modal = { ondismiss: function () { post({ type: "dismiss" }); }, escape: false };
    new Razorpay(o).open();
  } catch (e) { post({ type: "error", message: "Checkout couldn't load. Check your connection and try again." }); }
</script></body></html>`;
}

export default function RazorpayCheckout({ order, onSuccess, onDismiss, onError }: CheckoutProps) {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const html = useMemo(() => order && page({
    key: order.key_id, amount: order.amount, currency: order.currency, name: order.name, description: order.description,
    order_id: order.order_id, theme: { color: colors.brandPrimary }, webview_intent: true,
  }), [order, colors.brandPrimary]);

  return (
    <Modal visible={!!order} animationType="slide" presentationStyle="fullScreen" onRequestClose={onDismiss}>
      <View style={[styles.root, { paddingTop: insets.top, paddingBottom: insets.bottom }]} testID="razorpay-checkout">
        <View style={styles.bar}>
          <Pressable testID="checkout-close-button" onPress={onDismiss} style={styles.close} hitSlop={8}>
            <Ionicons name="close" size={26} color={colors.onSurface} />
          </Pressable>
          <Text style={styles.title}>Secure payment</Text>
          <View style={styles.close} />
        </View>
        {!!html && (
          <WebView
            source={{ html, baseUrl: BACKEND_URL }}
            originWhitelist={["*"]}
            javaScriptEnabled
            domStorageEnabled
            setSupportMultipleWindows={false}
            startInLoadingState
            renderLoading={() => <View style={styles.loading}><ActivityIndicator size="large" color={colors.brandPrimary} /></View>}
            onShouldStartLoadWithRequest={(req) => {
              if (IN_PAGE.test(req.url)) return true;
              Linking.openURL(req.url).catch(() => {}); // UPI apps (upi://, phonepe://, tez://, ...)
              return false;
            }}
            onError={() => onError("Checkout couldn't load. Check your connection and try again.")}
            onMessage={(e) => {
              let m: any;
              try { m = JSON.parse(e.nativeEvent.data); } catch { return; }
              if (m.type === "success") onSuccess(m.result);
              else if (m.type === "dismiss") onDismiss();
              else if (m.type === "error") onError(m.message);
            }}
          />
        )}
      </View>
    </Modal>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surfaceSecondary },
  bar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.md, height: 52, borderBottomWidth: 1, borderBottomColor: c.divider },
  close: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  title: { fontSize: 16, fontWeight: "800", color: c.onSurface },
  loading: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, alignItems: "center", justifyContent: "center", backgroundColor: c.surfaceSecondary },
}));
