export type RazorpayOrder = { key_id: string; order_id: string; amount: number; currency: string; name: string; description: string };
export type RazorpayResult = { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string };

export type CheckoutProps = {
  order: RazorpayOrder | null; // set to open the checkout, null to keep it closed
  onSuccess: (result: RazorpayResult) => void;
  onDismiss: () => void;
  onError: (message: string) => void;
};
