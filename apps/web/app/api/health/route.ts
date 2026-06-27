import { db, sql } from "@nudge/db";

export async function GET() {
  // Ping the DB so Supabase doesn't pause due to inactivity
  await db.execute(sql`SELECT 1`);
  return Response.json({ status: "ok", ts: new Date().toISOString() });
}

export const dynamic = "force-dynamic";
