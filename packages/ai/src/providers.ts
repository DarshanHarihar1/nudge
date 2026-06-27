import { createGroq } from "@ai-sdk/groq";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";

export function getGroqModel() {
  const apiKey = process.env["GROQ_API_KEY"];
  if (!apiKey) throw new Error("GROQ_API_KEY is not set");
  const groq = createGroq({ apiKey });
  return groq("llama-3.1-8b-instant");
}

export function getOpenRouterModel() {
  const apiKey = process.env["OPENROUTER_API_KEY"];
  if (!apiKey) throw new Error("OPENROUTER_API_KEY is not set");
  const openrouter = createOpenRouter({ apiKey });
  return openrouter("meta-llama/llama-3.1-8b-instruct:free");
}

export function isRateLimitError(err: unknown): boolean {
  if (err instanceof Error) {
    const msg = err.message.toLowerCase();
    return (
      msg.includes("429") ||
      msg.includes("rate limit") ||
      msg.includes("quota") ||
      msg.includes("too many requests")
    );
  }
  return false;
}
