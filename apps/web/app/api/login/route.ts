import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

// Shared with the bot, which signs magic-link tokens with this secret.
const SECRET = process.env.CRON_SECRET!;
const ALLOWED_ID = Number(process.env.TELEGRAM_ALLOWED_ID!);

// Magic-link token format (issued by the Telegram bot's /login command):
//   "<telegramId>.<expEpochSeconds>.<hmacSha256(`<telegramId>.<expEpochSeconds>`, SECRET)>"
function verifyMagicToken(token: string): number | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [id, exp, sig] = parts;

  const payload = `${id}.${exp}`;
  const expected = crypto
    .createHmac("sha256", SECRET)
    .update(payload)
    .digest("hex");
  try {
    if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected)))
      return null;
  } catch {
    return null;
  }

  const expSec = Number(exp);
  if (isNaN(expSec) || expSec * 1000 < Date.now()) return null; // expired

  const tid = Number(id);
  return isNaN(tid) ? null : tid;
}

// Mirrors signSession() in /api/auth so the proxy + auth-check routes accept it.
function signSession(id: number): string {
  const data = String(id);
  const sig = crypto.createHmac("sha256", SECRET).update(data).digest("hex");
  return `${data}.${sig}`;
}

export async function GET(req: NextRequest) {
  const token = req.nextUrl.searchParams.get("token");
  if (!token)
    return NextResponse.json({ error: "Missing token" }, { status: 400 });

  const tid = verifyMagicToken(token);
  if (tid === null)
    return NextResponse.json(
      { error: "Invalid or expired login link" },
      { status: 401 }
    );
  if (tid !== ALLOWED_ID)
    return NextResponse.json({ error: "Not authorized" }, { status: 403 });

  const res = NextResponse.redirect(new URL("/", req.url));
  res.cookies.set("nudge_session", signSession(tid), {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 86400,
    path: "/",
  });
  return res;
}
