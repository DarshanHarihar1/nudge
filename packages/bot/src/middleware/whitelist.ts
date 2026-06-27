import type { Context, NextFunction } from "grammy";
import { getUser } from "@nudge/db";
import type { Db } from "@nudge/db";

export function whitelistMiddleware(db: Db, allowedTelegramId: bigint) {
  return async (ctx: Context, next: NextFunction) => {
    const senderId = ctx.from?.id;
    if (!senderId || BigInt(senderId) !== allowedTelegramId) return;

    // Allow /start even before the user row exists
    if (ctx.message?.text?.startsWith("/start")) {
      await next();
      return;
    }

    const user = await getUser(db, BigInt(senderId));
    if (!user) return;

    await next();
  };
}
