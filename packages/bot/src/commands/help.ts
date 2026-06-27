import type { Context } from "grammy";

export function helpCommand() {
  return async (ctx: Context) => {
    await ctx.reply(
      `Nudge — Personal Finance Tracker\n\n` +
        `*Logging expenses*\n` +
        `Just type any expense in plain English:\n` +
        `• "250 lunch with team"\n` +
        `• "Swiggy 480"\n` +
        `• "bought shoes 2999"\n\n` +
        `*Commands*\n` +
        `/recent — Last 10 expenses\n` +
        `/undo — Delete the last expense\n` +
        `/help — Show this message`,
      { parse_mode: "Markdown" },
    );
  };
}
