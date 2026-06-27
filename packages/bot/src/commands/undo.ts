import type { Context } from "grammy";
import { getUser, getLastExpense, deleteExpense } from "@nudge/db";
import type { Db } from "@nudge/db";
import { formatAmount } from "../utils/format";

export function undoCommand(db: Db) {
  return async (ctx: Context) => {
    const user = await getUser(db, BigInt(ctx.from!.id));
    if (!user) return;

    const last = await getLastExpense(db, user.id);
    if (!last) {
      await ctx.reply("Nothing to undo.");
      return;
    }

    await deleteExpense(db, last.id);

    const cat = last.category;
    await ctx.reply(
      `🗑 Deleted: ${formatAmount(last.amount, last.currency)} → ${cat?.emoji ?? ""} ${cat?.name ?? "Misc"}`,
    );
  };
}
