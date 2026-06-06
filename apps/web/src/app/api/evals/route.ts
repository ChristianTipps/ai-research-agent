import { listEvals } from "@/lib/backend";
import { NextResponse } from "next/server";

export async function GET() {
  const evals = await listEvals();
  return NextResponse.json(evals);
}
