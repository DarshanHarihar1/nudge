import { eq, desc, and, isNull } from "drizzle-orm";
import type { Db } from "./client";
import { users, categories, expenses } from "./schema";

// ── Users ────────────────────────────────────────────────────────────────────

export async function getUser(db: Db, telegramId: bigint) {
  return db.query.users.findFirst({
    where: eq(users.telegramId, telegramId),
  });
}

export async function upsertUser(
  db: Db,
  data: { telegramId: bigint; name: string },
) {
  const [user] = await db
    .insert(users)
    .values(data)
    .onConflictDoUpdate({
      target: users.telegramId,
      set: { name: data.name },
    })
    .returning();
  return user!;
}

export async function setAwaitingBalance(
  db: Db,
  userId: string,
  value: boolean,
) {
  await db
    .update(users)
    .set({ awaitingBalance: value })
    .where(eq(users.id, userId));
}

// ── Categories ───────────────────────────────────────────────────────────────

export const DEFAULT_CATEGORIES = [
  { name: "Food", emoji: "🍴" },
  { name: "Groceries", emoji: "🛒" },
  { name: "Transport", emoji: "🚗" },
  { name: "Rent", emoji: "🏠" },
  { name: "Utilities", emoji: "💡" },
  { name: "Entertainment", emoji: "🎬" },
  { name: "Shopping", emoji: "🛍️" },
  { name: "Health", emoji: "💊" },
  { name: "Subscriptions", emoji: "📱" },
  { name: "Education", emoji: "📚" },
  { name: "Misc", emoji: "📦" },
] as const;

export async function seedCategories(db: Db, userId: string) {
  await db
    .insert(categories)
    .values(DEFAULT_CATEGORIES.map((c) => ({ ...c, userId })))
    .onConflictDoNothing();
}

export async function listCategories(db: Db, userId: string) {
  return db.query.categories.findMany({
    where: and(eq(categories.userId, userId), eq(categories.isActive, true)),
    orderBy: categories.name,
  });
}

export async function getCategoryByName(
  db: Db,
  userId: string,
  name: string,
) {
  return db.query.categories.findFirst({
    where: and(
      eq(categories.userId, userId),
      eq(categories.name, name),
      eq(categories.isActive, true),
    ),
  });
}

// ── Expenses ─────────────────────────────────────────────────────────────────

export type NewExpense = typeof expenses.$inferInsert;

export async function createExpense(db: Db, data: NewExpense) {
  const [expense] = await db.insert(expenses).values(data).returning();
  return expense!;
}

export async function confirmExpense(db: Db, expenseId: string) {
  await db
    .update(expenses)
    .set({ status: "confirmed" })
    .where(eq(expenses.id, expenseId));
}

export async function recategorizeExpense(
  db: Db,
  expenseId: string,
  categoryId: string,
) {
  await db
    .update(expenses)
    .set({ categoryId, status: "confirmed" })
    .where(eq(expenses.id, expenseId));
}

export async function deleteExpense(db: Db, expenseId: string) {
  await db.delete(expenses).where(eq(expenses.id, expenseId));
}

export async function listRecentExpenses(
  db: Db,
  userId: string,
  limit = 10,
) {
  return db.query.expenses.findMany({
    where: eq(expenses.userId, userId),
    orderBy: desc(expenses.createdAt),
    limit,
    with: { category: true },
  });
}

export async function getLastExpense(db: Db, userId: string) {
  return db.query.expenses.findFirst({
    where: eq(expenses.userId, userId),
    orderBy: desc(expenses.createdAt),
    with: { category: true },
  });
}

export async function getExpenseByUpdateId(
  db: Db,
  updateId: bigint,
) {
  return db.query.expenses.findFirst({
    where: eq(expenses.telegramUpdateId, updateId),
  });
}
