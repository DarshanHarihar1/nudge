import {
  pgTable,
  uuid,
  bigint,
  text,
  numeric,
  boolean,
  timestamp,
  uniqueIndex,
} from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";

export const users = pgTable("users", {
  id: uuid("id").primaryKey().defaultRandom(),
  telegramId: bigint("telegram_id", { mode: "bigint" }).notNull().unique(),
  name: text("name").notNull(),
  baseCurrency: text("base_currency").notNull().default("INR"),
  awaitingBalance: boolean("awaiting_balance").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const categories = pgTable(
  "categories",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    name: text("name").notNull(),
    emoji: text("emoji").notNull(),
    monthlyBudget: numeric("monthly_budget"),
    isActive: boolean("is_active").notNull().default(true),
  },
  (t) => [uniqueIndex("categories_user_name_idx").on(t.userId, t.name)],
);

export const categoriesRelations = relations(categories, ({ one, many }) => ({
  user: one(users, { fields: [categories.userId], references: [users.id] }),
  expenses: many(expenses),
}));

export const usersRelations = relations(users, ({ many }) => ({
  categories: many(categories),
  expenses: many(expenses),
}));

export const expenses = pgTable("expenses", {
  id: uuid("id").primaryKey().defaultRandom(),
  userId: uuid("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  amount: numeric("amount").notNull(),
  currency: text("currency").notNull().default("INR"),
  categoryId: uuid("category_id")
    .notNull()
    .references(() => categories.id),
  merchant: text("merchant"),
  note: text("note"),
  rawText: text("raw_text").notNull(),
  source: text("source").notNull().default("telegram"),
  status: text("status").notNull().default("confirmed"),
  confidence: numeric("confidence"),
  llmProvider: text("llm_provider"),
  spentAt: timestamp("spent_at", { withTimezone: true }).notNull().defaultNow(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  telegramUpdateId: bigint("telegram_update_id", { mode: "bigint" }).unique(),
});

export const expensesRelations = relations(expenses, ({ one }) => ({
  user: one(users, { fields: [expenses.userId], references: [users.id] }),
  category: one(categories, { fields: [expenses.categoryId], references: [categories.id] }),
}));
