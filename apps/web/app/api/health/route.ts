export async function GET() {
  return Response.json({ status: "ok", ts: new Date().toISOString() });
}

export const dynamic = "force-dynamic";
