export function formatAmount(amount: string | number, currency = "INR"): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (currency === "INR") {
    return `₹${num.toLocaleString("en-IN")}`;
  }
  return `${num.toLocaleString("en-US")} ${currency}`;
}
