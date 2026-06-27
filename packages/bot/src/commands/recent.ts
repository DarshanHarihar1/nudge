import type { Context } from "grammy";
import { getUser, listRecentExpenses } from "@nudge/db";
import type { Db } from "@nudge/db";
import { formatAmount } from "../utils/format";

export function recentCommand(db: Db) {
  return async (ctx: Context) => {
    const user = await getUser(db, BigInt(ctx.from!.id));
    if (!user) return;

    const items = await listRecentExpenses(db, user.id, 10);
    if (items.length === 0) {
      await ctx.reply("No expenses logged yet.");
      return;
    }

    const lines = items.map((e, i) => {
      const cat = e.category;
      const emoji = cat?.emoji ?? "📦";
      const name = cat?.name ?? "Misc";
      const date = e.spentAt.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
      });
      return `${i + 1}. ${emoji} ${formatAmount(e.amount, e.currency)} → ${name}  · ${date}${e.merchant ? `  (${e.merchant})` : ""}`;
    });

    await ctx.reply(`Recent expenses:\n\n${lines.join("\n")}`);
  };
}
