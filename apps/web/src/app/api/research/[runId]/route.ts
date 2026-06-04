import { getResearchRun } from "@/lib/backend";
import { NextResponse } from "next/server";

export async function GET(_: Request, context: { params: Promise<{ runId: string }> }) {
  const { runId } = await context.params;
  const run = await getResearchRun(runId);
  return NextResponse.json(run);
}
