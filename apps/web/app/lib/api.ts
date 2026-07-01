import type { Txn, RecurringItem, CatKey } from "./demoData";

export interface ApiExpense {
  id: string;
  amount: number;
  category_name: string | null;
  category_emoji: string | null;
  merchant: string | null;
  note: string | null;
  source: string;
  spent_at: string | null;
}

export interface ApiRecurring {
  id: string;
  name: string;
  amount: number;
  category_id: string;
  category_name: string;
  category_emoji: string;
  direction: string;
  day_of_month: number;
  is_active: boolean;
}

export interface ApiCategory {
  id: string;
  name: string;
  emoji: string;
  monthly_budget: number | null;
}

export interface Analytics {
  totalSpend: number;
  byCategory: { name: string; emoji: string; amount: number; budget: number | null }[];
  spendOverTime: { date: string; amount: number }[];
}

const CAT_NAME_MAP: Record<string, CatKey> = {
  "food": "food", "groceries": "groceries", "transport": "transport",
  "rent": "rent", "entertainment": "entertainment", "shopping": "shopping",
  "health": "health", "subscriptions": "subscriptions", "investment": "investment",
  "credit card": "creditcard", "creditcard": "creditcard",
  "family": "family", "misc": "misc",
};

export function catKey(name: string | null): CatKey {
  if (!name) return "misc";
  return CAT_NAME_MAP[name.toLowerCase()] ?? "misc";
}

export function toTxn(e: ApiExpense, idx: number): Txn {
  const isCredit = e.source === "recurring_credit";
  return {
    id: idx + 1,
    date: e.spent_at
      ? e.spent_at.split("T")[0]
      : new Date().toISOString().split("T")[0],
    amount: isCredit ? e.amount : -e.amount,
    cat: catKey(e.category_name),
    merchant: e.merchant || e.note || e.category_name || "Unknown",
    note: e.note || "",
    source: e.source.startsWith("recurring")
      ? "recurring"
      : (e.source as "telegram" | "manual"),
  };
}

export function toRecurring(r: ApiRecurring, idx: number): RecurringItem {
  return {
    id: idx + 1,
    name: r.name,
    amount: Number(r.amount),
    cat: catKey(r.category_name),
    day: r.day_of_month,
    type: r.direction as "debit" | "credit",
    active: r.is_active,
  };
}

async function proxy(path: string, opts?: RequestInit) {
  return fetch(`/api/proxy/${path}`, opts);
}

export async function fetchExpenses(limit = 100): Promise<{ expenses: ApiExpense[]; total: number }> {
  // The API caps page size at 100 (returns 422 above that), so clamp here to
  // keep any caller safe regardless of the value it passes.
  const capped = Math.min(Math.max(1, limit), 100);
  const res = await proxy(`expenses?page=1&limit=${capped}`);
  if (!res.ok) throw new Error("expenses");
  return res.json();
}

export async function fetchRecurring(): Promise<{ items: ApiRecurring[] }> {
  const res = await proxy("recurring");
  if (!res.ok) throw new Error("recurring");
  return res.json();
}

export async function fetchCategories(): Promise<{ categories: ApiCategory[] }> {
  const res = await proxy("categories");
  if (!res.ok) throw new Error("categories");
  return res.json();
}

export async function fetchAnalytics(from: string, to: string): Promise<Analytics> {
  const res = await proxy(`analytics?from=${from}&to=${to}`);
  if (!res.ok) throw new Error("analytics");
  return res.json();
}

export async function apiDeleteRecurring(uuid: string): Promise<void> {
  await proxy(`recurring/${uuid}`, { method: "DELETE" });
}

export async function apiPatchRecurring(uuid: string, body: Record<string, unknown>): Promise<void> {
  await proxy(`recurring/${uuid}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function apiCreateRecurring(body: Record<string, unknown>): Promise<ApiRecurring> {
  const res = await proxy("recurring", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function apiPatchExpense(uuid: string, body: Record<string, unknown>): Promise<void> {
  await proxy(`expenses/${uuid}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
