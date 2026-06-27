import { generateObject } from "ai";
import { z } from "zod";
import { getGroqModel, getOpenRouterModel, isRateLimitError } from "./providers";

const CATEGORIES = [
  "Food",
  "Groceries",
  "Transport",
  "Rent",
  "Utilities",
  "Entertainment",
  "Shopping",
  "Health",
  "Subscriptions",
  "Education",
  "Misc",
] as const;

export const ClassifiedExpenseSchema = z.object({
  amount: z.number().positive(),
  currency: z.string().default("INR"),
  category: z.enum(CATEGORIES),
  merchant: z.string().nullable().default(null),
  note: z.string().nullable().default(null),
  confidence: z.number().min(0).max(1),
});

export type ClassifiedExpense = z.infer<typeof ClassifiedExpenseSchema>;

const SYSTEM_PROMPT = `You are an expense classifier for a personal finance tracker.
Extract structured data from a user's expense message.

Categories (pick exactly one): ${CATEGORIES.join(", ")}

Rules:
- amount: the numeric amount spent (required)
- currency: 3-letter currency code, default "INR" if not mentioned
- category: best matching category from the list
- merchant: the shop/service name if mentioned, otherwise null
- note: any extra context (e.g. "team lunch"), otherwise null
- confidence: your confidence score 0.0–1.0

Return JSON only. No prose.`;

type Provider = "groq" | "openrouter";

export async function classifyExpense(
  text: string,
): Promise<ClassifiedExpense & { provider: Provider }> {
  const providers: Array<{ name: Provider; getModel: () => ReturnType<typeof getGroqModel> }> = [
    { name: "groq", getModel: getGroqModel },
    { name: "openrouter", getModel: getOpenRouterModel },
  ];

  let lastError: unknown;

  for (const { name, getModel } of providers) {
    try {
      const { object } = await generateObject({
        model: getModel(),
        schema: ClassifiedExpenseSchema,
        system: SYSTEM_PROMPT,
        prompt: text,
      });
      return { ...object, provider: name };
    } catch (err) {
      lastError = err;
      if (!isRateLimitError(err)) throw err;
      // rate limited — try next provider
    }
  }

  throw new Error(`All LLM providers exhausted. Last error: ${String(lastError)}`);
}
