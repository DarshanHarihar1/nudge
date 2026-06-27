import { webhookCallback, createBot } from "@nudge/bot";
import { db } from "@nudge/db";
import type { NextRequest } from "next/server";

// Singleton bot — recreated only on cold start
const bot = createBot(db);
const handleUpdate = webhookCallback(bot, "std/http");

export async function POST(req: NextRequest) {
  const secret = req.headers.get("x-telegram-bot-api-secret-token");
  const expected = process.env["TELEGRAM_WEBHOOK_SECRET"];

  if (!expected || secret !== expected) {
    return new Response("Forbidden", { status: 403 });
  }

  return handleUpdate(req);
}

// Required for streaming / raw body access in Next.js App Router
export const dynamic = "force-dynamic";
