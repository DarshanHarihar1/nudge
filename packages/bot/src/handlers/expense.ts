import type { Context } from "grammy";
import { InlineKeyboard } from "grammy";
import { classifyExpense } from "@nudge/ai";
import {
  getUser,
  getCategoryByName,
  listCategories,
  createExpense,
  confirmExpense,
  recategorizeExpense,
  deleteExpense,
  getExpenseByUpdateId,
} from "@nudge/db";
import type { Db } from "@nudge/db";
import { formatAmount } from "../utils/format";

// Callback data prefixes
const CB_OK = "exp:ok:";
const CB_RECAT = "exp:recat:";
const CB_CAT = "exp:cat:";
const CB_DEL = "exp:del:";

function confirmKeyboard(expenseId: string) {
  return new InlineKeyboard()
    .text("✅ OK", `${CB_OK}${expenseId}`)
    .text("✏️ Recategorize", `${CB_RECAT}${expenseId}`)
    .text("🗑 Delete", `${CB_DEL}${expenseId}`);
}

export function expenseHandler(db: Db) {
  return async (ctx: Context) => {
    const text = ctx.message?.text;
    if (!text) return;

    const user = await getUser(db, BigInt(ctx.from!.id));
    if (!user) return;

    // Idempotency: don't double-log if Telegram retries the webhook
    const updateId = BigInt(ctx.update.update_id);
    const existing = await getExpenseByUpdateId(db, updateId);
    if (existing) return;

    const thinking = await ctx.reply("⏳ Logging…");

    let classified;
    try {
      classified = await classifyExpense(text);
    } catch {
      await ctx.api.editMessageText(
        ctx.chat!.id,
        thinking.message_id,
        "❌ Couldn't classify that. Try again or rephrase.",
      );
      return;
    }

    const category = await getCategoryByName(db, user.id, classified.category);
    if (!category) {
      await ctx.api.editMessageText(
        ctx.chat!.id,
        thinking.message_id,
        "❌ Internal error: category not found. Run /start to reset categories.",
      );
      return;
    }

    const expense = await createExpense(db, {
      userId: user.id,
      amount: String(classified.amount),
      currency: classified.currency,
      categoryId: category.id,
      merchant: classified.merchant ?? undefined,
      note: classified.note ?? undefined,
      rawText: text,
      source: "telegram",
      status: "pending",
      confidence: classified.confidence !== undefined ? String(classified.confidence) : undefined,
      llmProvider: classified.provider,
      telegramUpdateId: updateId,
    });

    const label = `${formatAmount(classified.amount, classified.currency)} → ${category.emoji} ${category.name}`;
    await ctx.api.editMessageText(
      ctx.chat!.id,
      thinking.message_id,
      `Logged ${label}`,
      { reply_markup: confirmKeyboard(expense.id) },
    );
  };
}

export function callbackHandler(db: Db) {
  return async (ctx: Context) => {
    const data = ctx.callbackQuery?.data;
    if (!data) return;

    await ctx.answerCallbackQuery();

    // ── OK ────────────────────────────────────────────────────────────
    if (data.startsWith(CB_OK)) {
      const expenseId = data.slice(CB_OK.length);
      await confirmExpense(db, expenseId);
      await ctx.editMessageReplyMarkup({ reply_markup: undefined });
      return;
    }

    // ── Delete ────────────────────────────────────────────────────────
    if (data.startsWith(CB_DEL)) {
      const expenseId = data.slice(CB_DEL.length);
      await deleteExpense(db, expenseId);
      await ctx.editMessageText("Deleted.");
      return;
    }

    // ── Recategorize — show category list ────────────────────────────
    if (data.startsWith(CB_RECAT)) {
      const expenseId = data.slice(CB_RECAT.length);
      const user = await getUser(db, BigInt(ctx.from!.id));
      if (!user) return;

      const cats = await listCategories(db, user.id);
      const kb = new InlineKeyboard();
      cats.forEach((c, i) => {
        kb.text(`${c.emoji} ${c.name}`, `${CB_CAT}${expenseId}:${c.id}`);
        if ((i + 1) % 3 === 0) kb.row();
      });

      await ctx.editMessageReplyMarkup({ reply_markup: kb });
      return;
    }

    // ── Category selected ─────────────────────────────────────────────
    if (data.startsWith(CB_CAT)) {
      const rest = data.slice(CB_CAT.length);
      const colonIdx = rest.indexOf(":");
      const expenseId = rest.slice(0, colonIdx);
      const categoryId = rest.slice(colonIdx + 1);

      await recategorizeExpense(db, expenseId, categoryId);
      await ctx.editMessageReplyMarkup({ reply_markup: undefined });
      await ctx.answerCallbackQuery("Category updated ✓");
      return;
    }
  };
}
