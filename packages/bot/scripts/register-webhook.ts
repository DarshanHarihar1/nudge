#!/usr/bin/env node
// Run after deploy: pnpm --filter @nudge/bot register-webhook
// Env vars required: TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, APP_URL

const token = process.env["TELEGRAM_BOT_TOKEN"];
const secret = process.env["TELEGRAM_WEBHOOK_SECRET"];
const appUrl = process.env["APP_URL"];

if (!token || !secret || !appUrl) {
  console.error(
    "Required: TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, APP_URL",
  );
  process.exit(1);
}

const webhookUrl = `${appUrl}/api/telegram/webhook`;

const res = await fetch(
  `https://api.telegram.org/bot${token}/setWebhook`,
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: webhookUrl,
      secret_token: secret,
      allowed_updates: ["message", "callback_query"],
    }),
  },
);

const json = await res.json();
if (json.ok) {
  console.log(`✅ Webhook registered: ${webhookUrl}`);
} else {
  console.error("❌ Failed:", json);
  process.exit(1);
}
