import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

const API_URL = process.env.API_URL ?? "https://nudge-api-va33.onrender.com";
const CRON_SECRET = process.env.CRON_SECRET!;
const ALLOWED_ID = Number(process.env.TELEGRAM_ALLOWED_ID!);
const SESSION_SECRET = process.env.CRON_SECRET!;

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

async function handle(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const session = req.cookies.get("nudge_session");
  if (!session)
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  const tid = verifySession(session.value);
  if (tid !== ALLOWED_ID)
    return NextResponse.json({ error: "Unauthorized" }, { status: 403 });

  const { path } = await params;
  const url = new URL(`${API_URL}/dashboard/${path.join("/")}`);
  req.nextUrl.searchParams.forEach((v, k) => url.searchParams.set(k, v));

  const hasBody = ["POST", "PUT", "PATCH"].includes(req.method);
  const body = hasBody ? await req.text() : undefined;

  const upstream = await fetch(url.toString(), {
    method: req.method,
    headers: {
      Authorization: `Bearer ${CRON_SECRET}`,
      "Content-Type": "application/json",
    },
    body,
  });

  if (upstream.status === 204) return new NextResponse(null, { status: 204 });

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const DELETE = handle;
