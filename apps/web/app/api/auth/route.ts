import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN!;
const ALLOWED_ID = Number(process.env.TELEGRAM_ALLOWED_ID!);
const SESSION_SECRET = process.env.CRON_SECRET!;

function verifyTelegramAuth(data: Record<string, string>): boolean {
  const { hash, ...rest } = data;
  if (!hash) return false;
  const checkString = Object.keys(rest)
    .sort()
    .map((k) => `${k}=${rest[k]}`)
    .join("\n");
  const secretKey = crypto.createHash("sha256").update(BOT_TOKEN).digest();
  const hmac = crypto
    .createHmac("sha256", secretKey)
    .update(checkString)
    .digest("hex");
  try {
    return crypto.timingSafeEqual(Buffer.from(hmac), Buffer.from(hash));
  } catch {
    return false;
  }
}

function signSession(id: number): string {
  const data = String(id);
  const sig = crypto
    .createHmac("sha256", SESSION_SECRET)
    .update(data)
    .digest("hex");
  return `${data}.${sig}`;
}

function verifySession(value: string): number | null {
  const dot = value.lastIndexOf(".");
  if (dot === -1) return null;
  const data = value.slice(0, dot);
  const sig = value.slice(dot + 1);
  const expected = crypto
    .createHmac("sha256", SESSION_SECRET)
    .update(data)
    .digest("hex");
  try {
    if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected)))
      return null;
  } catch {
    return null;
  }
  const id = Number(data);
  return isNaN(id) ? null : id;
}

export async function POST(req: NextRequest) {
  const data = await req.json();
  if (!verifyTelegramAuth(data))
    return NextResponse.json({ error: "Invalid Telegram auth" }, { status: 401 });
  if (Number(data.id) !== ALLOWED_ID)
    return NextResponse.json({ error: "Not authorized" }, { status: 403 });

  const res = NextResponse.json({ ok: true });
  res.cookies.set("nudge_session", signSession(Number(data.id)), {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 86400,
    path: "/",
  });
  return res;
}

export async function GET(req: NextRequest) {
  const session = req.cookies.get("nudge_session");
  if (!session)
    return NextResponse.json({ authenticated: false }, { status: 401 });
  const tid = verifySession(session.value);
  if (tid !== ALLOWED_ID)
    return NextResponse.json({ authenticated: false }, { status: 401 });
  return NextResponse.json({ authenticated: true });
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.delete("nudge_session");
  return res;
}
