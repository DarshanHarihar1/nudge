import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

function createDb() {
  const url = process.env["DATABASE_URL"];
  if (!url) throw new Error("DATABASE_URL is not set");
  const client = postgres(url, { prepare: false });
  return drizzle(client, { schema });
}

export type Db = ReturnType<typeof createDb>;

// Singleton for use in long-running processes (Next.js dev HMR safe)
const globalDb = globalThis as typeof globalThis & { _nudgeDb?: Db };
export const db: Db = globalDb._nudgeDb ?? (globalDb._nudgeDb = createDb());
