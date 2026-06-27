import { Bot } from "grammy";
import type { Db } from "@nudge/db";
import { whitelistMiddleware } from "./middleware/whitelist";
import { startCommand } from "./commands/start";
import { recentCommand } from "./commands/recent";
import { undoCommand } from "./commands/undo";
import { helpCommand } from "./commands/help";
import { expenseHandler, callbackHandler } from "./handlers/expense";

export function createBot(db: Db) {
  const token = process.env["TELEGRAM_BOT_TOKEN"];
  if (!token) throw new Error("TELEGRAM_BOT_TOKEN is not set");

  const allowedId = process.env["TELEGRAM_ALLOWED_ID"];
  if (!allowedId) throw new Error("TELEGRAM_ALLOWED_ID is not set");

  const bot = new Bot(token);

  bot.use(whitelistMiddleware(db, BigInt(allowedId)));

  bot.command("start", startCommand(db));
  bot.command("recent", recentCommand(db));
  bot.command("undo", undoCommand(db));
  bot.command("help", helpCommand());

  // Inline keyboard callbacks
  bot.on("callback_query:data", callbackHandler(db));

  // Free-text → expense (must be last, catches everything else)
  bot.on("message:text", expenseHandler(db));

  return bot;
}

export { webhookCallback } from "grammy";
