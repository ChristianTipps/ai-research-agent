import { listUpdates } from "@/lib/backend";
import { NextResponse } from "next/server";

export async function GET() {
  const updates = await listUpdates();
  return NextResponse.json(updates);
}
