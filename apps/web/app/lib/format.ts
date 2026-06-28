export function fmtINR(n: number): string {
  const abs = Math.round(Math.abs(n));
  const s = String(abs);
  if (s.length <= 3) return "₹" + s;
  const last3 = s.slice(-3);
  const rest = s.slice(0, -3).replace(/\B(?=(\d\d)+$)/g, ",");
  return "₹" + rest + "," + last3;
}

export function fmtSigned(n: number): string {
  return (n < 0 ? "-" : "+") + fmtINR(Math.abs(n));
}

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

export function dateShort(iso: string, today = "2026-06-28"): string {
  if (iso === today) return "Today";
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const ys = yesterday.toISOString().slice(0, 10);
  if (iso === ys) return "Yesterday";
  const [, m, d] = iso.split("-");
  return parseInt(d, 10) + " " + MONTHS[parseInt(m, 10) - 1];
}

export function ordinal(d: number): string {
  const t = d % 100;
  if (t >= 11 && t <= 13) return d + "th";
  const u = d % 10;
  return d + (u === 1 ? "st" : u === 2 ? "nd" : u === 3 ? "rd" : "th");
}

export function pad2(n: number): string {
  return n < 10 ? "0" + n : "" + n;
}

export function isoDate(y: number, m: number, d: number): string {
  return y + "-" + pad2(m) + "-" + pad2(d);
}
