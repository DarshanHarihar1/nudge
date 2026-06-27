import type { Context } from "grammy";
import { upsertUser, seedCategories } from "@nudge/db";
import type { Db } from "@nudge/db";

export function startCommand(db: Db) {
  return async (ctx: Context) => {
    const telegramId = BigInt(ctx.from!.id);
    const name = ctx.from!.first_name;

    const user = await upsertUser(db, { telegramId, name });
    await seedCategories(db, user.id);

    await ctx.reply(
      `👋 Hey ${name}! Nudge is ready.\n\nSend me any expense like:\n• "250 lunch"\n• "cab to airport 480"\n• "bought shoes 2999"\n\nI'll classify it and log it automatically.\n\nCommands: /recent /undo /help`,
    );
  };
}
